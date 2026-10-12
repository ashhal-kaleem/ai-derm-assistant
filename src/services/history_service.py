"""History Service managing Supabase Cloud scans persistence and media storage."""

from typing import Any, Dict, List, Optional
from src.domain.models import PredictionResult, ScanRecord
from src.infrastructure.supabase_client import SupabaseCloudClient


class HistoryService:
    """Orchestrates cloud scan record storage and retrieval."""

    def __init__(self, client: Optional[SupabaseCloudClient] = None):
        self.client = client or SupabaseCloudClient()

    def record_scan(
        self,
        prediction: PredictionResult,
        image_bytes: bytes,
        heatmap_bytes: Optional[bytes] = None
    ) -> ScanRecord:
        """Upload media to Supabase storage and persist scan record in PostgreSQL."""
        record = ScanRecord(
            predicted_class=prediction.top_class,
            raw_confidence=prediction.raw_confidence,
            calibrated_confidence=prediction.calibrated_confidence,
            temperature=prediction.temperature,
            uncertainty_score=prediction.uncertainty_score,
            risk_level=prediction.risk_level.value,
            clinical_summary=prediction.clinical_summary or prediction.gemini_summary,
            gemini_summary=prediction.clinical_summary or prediction.gemini_summary
        )

        # 1. Upload original lesion image to Supabase Storage
        image_url = self.client.upload_media(
            file_bytes=image_bytes,
            file_name=f"{record.id}_lesion.jpg",
            bucket="scans",
            content_type="image/jpeg"
        )
        record.image_url = image_url

        # 2. Upload Grad-CAM heatmap if present
        if heatmap_bytes:
            heatmap_url = self.client.upload_media(
                file_bytes=heatmap_bytes,
                file_name=f"{record.id}_heatmap.png",
                bucket="scans",
                content_type="image/png"
            )
            record.heatmap_url = heatmap_url

        # 3. Insert structured row into Supabase 'scans' table
        payload: Dict[str, Any] = {
            "id": record.id,
            "image_url": record.image_url,
            "heatmap_url": record.heatmap_url,
            "predicted_class": record.predicted_class,
            "raw_confidence": record.raw_confidence,
            "calibrated_confidence": record.calibrated_confidence,
            "temperature": record.temperature,
            "uncertainty_score": record.uncertainty_score,
            "risk_level": record.risk_level,
            "gemini_summary": record.gemini_summary,
            "feedback": record.feedback,
            "created_at": record.created_at
        }
        self.client.insert_scan(payload)
        return record

    def get_recent_scans(self, limit: int = 10) -> List[ScanRecord]:
        """Fetch latest scan records from Supabase."""
        rows = self.client.fetch_recent_scans(limit=limit)
        records: List[ScanRecord] = []
        for r in rows:
            records.append(
                ScanRecord(
                    id=r.get("id", ""),
                    image_url=r.get("image_url", ""),
                    heatmap_url=r.get("heatmap_url"),
                    predicted_class=r.get("predicted_class", ""),
                    raw_confidence=float(r.get("raw_confidence", 0.0)),
                    calibrated_confidence=float(r.get("calibrated_confidence", 0.0)),
                    temperature=float(r.get("temperature", 1.0)),
                    uncertainty_score=float(r.get("uncertainty_score", 0.0)),
                    risk_level=r.get("risk_level", "BENIGN"),
                    gemini_summary=r.get("gemini_summary"),
                    feedback=r.get("feedback"),
                    created_at=r.get("created_at", "")
                )
            )
        return records

    def create_lesion_visit(
        self,
        lesion_name: str,
        prediction: Dict[str, Any],
        image_b64: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, str]:
        """Record a new longitudinal visit for a named lesion."""
        import uuid
        from datetime import datetime, timezone
        
        visit_id = str(uuid.uuid4())
        lesion_id = f"lesion_{abs(hash(lesion_name.lower().strip())) % 1000000}"
        
        visit_row = {
            "visit_id": visit_id,
            "lesion_id": lesion_id,
            "lesion_name": lesion_name,
            "date": datetime.now(timezone.utc).isoformat(),
            "predicted_class": prediction.get("predicted_class") or prediction.get("top_class", ""),
            "class_name": prediction.get("class_name") or prediction.get("top_name", ""),
            "confidence": float(prediction.get("confidence") or prediction.get("calibrated_confidence", 0.0)),
            "risk_level": prediction.get("risk_level", "green"),
            "risk_label": prediction.get("risk_label", "Benign"),
            "image_thumb": image_b64[:120] if image_b64 else None,
            "llm_explanation": prediction.get("llm_explanation") or prediction.get("clinical_summary"),
            "notes": notes
        }
        
        if not hasattr(self, "_lesion_store"):
            self._lesion_store = {}
            
        if lesion_id not in self._lesion_store:
            self._lesion_store[lesion_id] = {
                "lesion_id": lesion_id,
                "lesion_name": lesion_name,
                "visits": []
            }
        self._lesion_store[lesion_id]["visits"].insert(0, visit_row)
        return {"visit_id": visit_id, "lesion_id": lesion_id}

    def get_lesion_history(self, lesion_id: str) -> Optional[Dict[str, Any]]:
        """Fetch visit timeline for a named lesion."""
        if not hasattr(self, "_lesion_store"):
            self._lesion_store = {}
        return self._lesion_store.get(lesion_id)
