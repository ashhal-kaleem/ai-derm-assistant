import base64
import io
import os
from datetime import datetime, timezone
from typing import List, Optional
from PIL import Image

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from src.api.schemas import (
    ClassProbabilityResponse,
    ClinicalSummaryRequest,
    ClinicalSummaryResponse,
    HealthResponse,
    PredictionResponse,
)
from src.domain.models import FeedbackType, PredictionResult, RiskLevel, ScanRecord
from src.services.groq_service import GroqService
from src.services.history_service import HistoryService
from src.services.inference_service import InferenceService

router = APIRouter()

# Singletons for services
_inference_service: Optional[InferenceService] = None
_groq_service: Optional[GroqService] = None
_history_service: Optional[HistoryService] = None


def get_inference_service() -> InferenceService:
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service


def get_groq_service() -> GroqService:
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqService()
    return _groq_service


def get_history_service() -> HistoryService:
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service


@router.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check():
    """Liveness & Readiness probe for container orchestrators and monitoring."""
    onnx_loaded = False
    try:
        service = get_inference_service()
        onnx_loaded = service.engine is not None and service.engine.session is not None
    except Exception:
        onnx_loaded = False

    return HealthResponse(
        status="healthy" if onnx_loaded else "degraded",
        onnx_model_loaded=onnx_loaded,
        groq_configured=bool(os.environ.get("GROQ_API_KEY")),
        supabase_configured=bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY")),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/api/v1/predict", response_model=PredictionResponse, tags=["Inference"])
async def predict_lesion(
    file: UploadFile = File(..., description="Dermatoscopic skin lesion image file (JPEG/PNG)"),
    generate_summary: bool = Query(True, description="Whether to generate Groq LPU clinical advice"),
    save_to_cloud: bool = Query(False, description="Persist image and prediction to Supabase Cloud"),
):
    """
    Run EfficientNet-B4 ONNX inference, temperature calibration, and Grad-CAM saliency extraction.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a valid image (JPEG/PNG).",
        )

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to decode image: {str(exc)}",
        )

    inference_service = get_inference_service()
    try:
        prediction = inference_service.predict(image)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference execution failed: {str(exc)}",
        )

    # Generate Groq clinical advisory summary
    clinical_summary = None
    if generate_summary:
        try:
            groq_service = get_groq_service()
            clinical_summary = groq_service.generate_clinical_summary(prediction)
            prediction.clinical_summary = clinical_summary
        except Exception:
            clinical_summary = None

    # Base64 encode Grad-CAM saliency heatmap
    heatmap_b64 = None
    if prediction.saliency_heatmap_bytes:
        heatmap_b64 = base64.b64encode(prediction.saliency_heatmap_bytes).decode("utf-8")

    # Optional cloud persistence
    if save_to_cloud:
        try:
            history_service = get_history_service()
            record = ScanRecord(
                predicted_class=prediction.top_class,
                raw_confidence=prediction.raw_confidence,
                calibrated_confidence=prediction.calibrated_confidence,
                uncertainty_score=prediction.uncertainty_score,
                risk_level=prediction.risk_level.value,
                clinical_summary=clinical_summary,
            )
            history_service.save_scan(
                record=record,
                raw_image_bytes=contents,
                heatmap_bytes=prediction.saliency_heatmap_bytes,
            )
        except Exception:
            pass  # Non-blocking fail-open for telemetry/history

    probs_response = [
        ClassProbabilityResponse(
            class_code=p.code,
            class_name=p.name,
            probability=p.probability,
            risk_level=p.risk_level.value,
        )
        for p in prediction.probabilities
    ]

    return PredictionResponse(
        top_class=prediction.top_class,
        top_name=prediction.top_name,
        risk_level=prediction.risk_level.value,
        raw_confidence=prediction.raw_confidence,
        calibrated_confidence=prediction.calibrated_confidence,
        temperature=prediction.temperature,
        uncertainty_score=prediction.uncertainty_score,
        probabilities=probs_response,
        saliency_heatmap_base64=heatmap_b64,
        clinical_summary=clinical_summary,
    )


@router.post("/api/v1/clinical-summary", response_model=ClinicalSummaryResponse, tags=["Advisory"])
def generate_summary_endpoint(payload: ClinicalSummaryRequest):
    """
    Generate real-time doctor-ready clinical interpretation using Groq LPU (llama-3.3-70b-versatile).
    """
    groq_service = get_groq_service()
    try:
        risk_level_enum = RiskLevel(payload.risk_level)
    except ValueError:
        risk_level_enum = RiskLevel.BENIGN

    dummy_pred = PredictionResult(
        top_class=payload.top_class,
        top_name=payload.top_name,
        risk_level=risk_level_enum,
        raw_confidence=payload.calibrated_confidence,
        calibrated_confidence=payload.calibrated_confidence,
        temperature=payload.temperature,
        uncertainty_score=payload.uncertainty_score,
        probabilities=[],
    )

    summary_text = groq_service.generate_clinical_summary(dummy_pred)
    return ClinicalSummaryResponse(clinical_summary=summary_text)


@router.get("/api/v1/history", tags=["History"])
def get_scan_history(limit: int = Query(10, ge=1, le=100)):
    """Fetch recent skin lesion scans and clinical metadata from Supabase Cloud."""
    history_service = get_history_service()
    records = history_service.get_recent_scans(limit=limit)
    return records
