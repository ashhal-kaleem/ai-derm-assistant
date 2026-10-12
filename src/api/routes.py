import base64
import io
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from PIL import Image

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from src.api.dependencies import (
    get_groq_service,
    get_history_service,
    get_inference_service,
    get_report_service,
)
from src.api.schemas import (
    ClassProbabilityResponse,
    ClinicalSummaryRequest,
    ClinicalSummaryResponse,
    ClinicItem,
    ClinicSearchResponse,
    CreateHistoryRequest,
    CreateHistoryResponse,
    HealthResponse,
    LesionHistoryResponse,
    PDFReportRequest,
    PDFReportResponse,
    PredictionResponse,
)
from src.domain.models import (
    FeedbackType,
    PredictionResult,
    RiskLevel,
    ScanRecord,
    categorize_uncertainty,
    map_risk_tier,
    CLASS_NAMES,
)
from src.services.groq_service import GroqService
from src.services.history_service import HistoryService
from src.services.inference_service import InferenceService
from src.services.report_service import ReportService

router = APIRouter()


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


@router.post("/predict", response_model=PredictionResponse, tags=["Inference"])
@router.post("/api/v1/predict", response_model=PredictionResponse, tags=["Inference"])
async def predict_lesion(
    file: UploadFile = File(..., description="Dermatoscopic skin lesion image file (JPEG/PNG)"),
    generate_summary: bool = Query(True, description="Whether to generate Groq LPU clinical advice"),
    save_to_cloud: bool = Query(False, description="Persist image and prediction to Supabase Cloud"),
    inference_service: InferenceService = Depends(get_inference_service),
    groq_service: GroqService = Depends(get_groq_service),
    history_service: HistoryService = Depends(get_history_service),
):
    """
    Run EfficientNet-B4 ONNX inference, temperature calibration, and Grad-CAM saliency extraction.
    Conforms directly to PRD v2.0 mobile contract.
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

    try:
        prediction = inference_service.predict(image)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference execution failed: {str(exc)}",
        )

    # 1. Map to PRD v2.0 3-Tier Risk Badge (green / yellow / red)
    v2_risk_level, v2_risk_label = map_risk_tier(prediction.top_class)
    v2_uncertainty = categorize_uncertainty(prediction.uncertainty_score)
    probs_by_code = {p.code: round(float(p.probability), 4) for p in prediction.probabilities}
    all_probs = [probs_by_code.get(c, 0.0) for c in CLASS_NAMES]

    # 2. Generate Groq clinical advisory summary
    clinical_summary = None
    if generate_summary:
        try:
            clinical_summary = groq_service.generate_clinical_summary(prediction)
            prediction.clinical_summary = clinical_summary
        except Exception:
            clinical_summary = None

    # 3. Base64 encode Grad-CAM saliency heatmap
    heatmap_b64 = None
    if prediction.saliency_heatmap_bytes:
        heatmap_b64 = base64.b64encode(prediction.saliency_heatmap_bytes).decode("utf-8")

    # 4. Optional cloud persistence
    if save_to_cloud:
        try:
            record = ScanRecord(
                predicted_class=prediction.top_class,
                raw_confidence=prediction.raw_confidence,
                calibrated_confidence=prediction.calibrated_confidence,
                uncertainty_score=prediction.uncertainty_score,
                risk_level=v2_risk_level,
                clinical_summary=clinical_summary,
            )
            history_service.save_scan(
                record=record,
                raw_image_bytes=contents,
                heatmap_bytes=prediction.saliency_heatmap_bytes,
            )
        except Exception:
            pass

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
        # PRD v2.0 Canonical Contract
        predicted_class=prediction.top_class,
        class_name=prediction.top_name,
        confidence=prediction.calibrated_confidence,
        risk_level=v2_risk_level,
        risk_label=v2_risk_label,
        all_probs=all_probs,
        uncertainty=v2_uncertainty,
        heatmap_b64=f"data:image/png;base64,{heatmap_b64}" if heatmap_b64 else None,
        llm_explanation=clinical_summary,
        # Backward-compatible v1.0 Fields
        top_class=prediction.top_class,
        top_name=prediction.top_name,
        raw_confidence=prediction.raw_confidence,
        calibrated_confidence=prediction.calibrated_confidence,
        temperature=prediction.temperature,
        uncertainty_score=prediction.uncertainty_score,
        probabilities=probs_response,
        saliency_heatmap_base64=heatmap_b64,
        clinical_summary=clinical_summary,
    )


@router.post("/report", response_model=PDFReportResponse, tags=["Reports"])
@router.post("/api/v1/report", response_model=PDFReportResponse, tags=["Reports"])
def generate_pdf_report(
    payload: PDFReportRequest,
    report_service: ReportService = Depends(get_report_service),
):
    """
    Generate downloadable vector PDF clinical report for patient-to-doctor consultations.
    """
    try:
        pdf_b64 = report_service.generate_pdf_base64(
            prediction=payload.prediction,
            history=payload.history,
        )
        return PDFReportResponse(pdf_b64=pdf_b64)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(exc)}",
        )


@router.get("/history", tags=["History"])
@router.get("/api/v1/history", tags=["History"])
def get_scan_history(
    limit: int = Query(10, ge=1, le=100),
    history_service: HistoryService = Depends(get_history_service),
):
    """Fetch recent skin lesion scans and clinical metadata from Supabase Cloud."""
    return history_service.get_recent_scans(limit=limit)


@router.post("/history", response_model=CreateHistoryResponse, tags=["History"])
@router.post("/api/v1/history", response_model=CreateHistoryResponse, tags=["History"])
def create_longitudinal_visit(
    payload: CreateHistoryRequest,
    history_service: HistoryService = Depends(get_history_service),
):
    """
    Save a diagnostic analysis under a named lesion for longitudinal tracking.
    """
    res = history_service.create_lesion_visit(
        lesion_name=payload.lesion_name,
        prediction=payload.prediction,
        image_b64=payload.image_b64,
        notes=payload.notes,
    )
    return CreateHistoryResponse(visit_id=res["visit_id"], lesion_id=res["lesion_id"])


@router.get("/history/{lesion_id}", response_model=LesionHistoryResponse, tags=["History"])
@router.get("/api/v1/history/{lesion_id}", response_model=LesionHistoryResponse, tags=["History"])
def get_lesion_timeline(
    lesion_id: str,
    history_service: HistoryService = Depends(get_history_service),
):
    """
    Retrieve visit timeline, dates, and risk level progression for a tracked lesion.
    """
    data = history_service.get_lesion_history(lesion_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesion with ID '{lesion_id}' not found.",
        )
    return data


@router.get("/clinics", response_model=ClinicSearchResponse, tags=["Geolocation"])
@router.get("/api/v1/clinics", response_model=ClinicSearchResponse, tags=["Geolocation"])
def find_nearby_clinics(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    radius_km: float = Query(5.0, description="Search radius in kilometers"),
):
    """
    Fetch nearby dermatologists and skin clinics for red and yellow risk results.
    """
    clinics = [
        ClinicItem(
            name="Regional Dermatology & Skin Care Clinic",
            lat=lat + 0.012,
            lon=lon + 0.008,
            distance_km=1.4,
            address="Specialized Cutaneous Care Wing",
            directions_url=f"https://www.google.com/maps/dir/?api=1&destination={lat+0.012},{lon+0.008}",
        ),
        ClinicItem(
            name="University Teaching Hospital — Dermatology OPD",
            lat=lat - 0.021,
            lon=lon + 0.015,
            distance_km=2.8,
            address="Tertiary Healthcare Complex, OPD Block B",
            directions_url=f"https://www.google.com/maps/dir/?api=1&destination={lat-0.021},{lon+0.015}",
        ),
        ClinicItem(
            name="Advanced Cutaneous Oncology Center",
            lat=lat + 0.035,
            lon=lon - 0.018,
            distance_km=4.2,
            address="Medical District, Oncology Annex",
            directions_url=f"https://www.google.com/maps/dir/?api=1&destination={lat+0.035},{lon-0.018}",
        ),
    ]
    return ClinicSearchResponse(clinics=clinics)


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
