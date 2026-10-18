import base64
import io
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from PIL import Image, ImageOps

from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from src.api.dependencies import (
    get_geolocation_service,
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
    categorize_uncertainty,
    map_risk_tier,
    CLASS_NAMES,
)

logger = logging.getLogger("dermassist.routes")
from src.services.geolocation_service import ClinicSearchError, GeolocationService
from src.services.groq_service import GroqService
from src.services.history_service import HistoryService
from src.services.inference_service import InferenceService
from src.services.report_service import ReportService

MAX_IMAGE_SIDE = 1024

router = APIRouter()

@router.api_route("/", methods=["GET", "HEAD"], tags=["Discovery"])
def api_root():
    """Canonical API Service Discovery Manifest for headless clients and developers."""
    return {
        "service": "DermAssist AI — Clinical Inference Engine",
        "version": "2.0.2",
        "status": "operational",
        "docs_url": "/docs",
        "endpoints": {
            "predict": "POST /predict",
            "report": "POST /report",
            "history": "POST /history",
            "lesion_timeline": "GET /history/{lesion_id}",
            "clinics": "GET /clinics",
            "health": "GET /health"
        },
        "compliance": "Educational & Clinical Triage Assistance (Non-FDA/CE Medical Device)"
    }


@router.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse, tags=["Monitoring"])
def health_check():
    """Liveness & Readiness probe for container orchestrators and monitoring."""
    onnx_loaded = False
    try:
        service = get_inference_service()
        onnx_loaded = service.engine is not None and service.engine.session is not None
    except Exception:
        onnx_loaded = False

    supabase_ok = False
    try:
        hist_service = get_history_service()
        supabase_ok = hist_service.client.check_connection()
    except Exception:
        supabase_ok = False

    return HealthResponse(
        status="healthy" if onnx_loaded else "degraded",
        onnx_model_loaded=onnx_loaded,
        groq_configured=bool(os.environ.get("GROQ_API_KEY")),
        supabase_configured=supabase_ok,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

@router.post("/predict", response_model=PredictionResponse, tags=["Inference"])
@router.post("/api/v1/predict", response_model=PredictionResponse, tags=["Inference"])
async def predict_lesion(
    file: UploadFile = File(..., description="Dermatoscopic skin lesion image file (JPEG/PNG)"),
    generate_summary: bool = Query(True, description="Whether to generate Groq LPU clinical advice"),
    save_to_cloud: bool = Query(True, description="Persist image and prediction to Supabase Cloud"),
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
        raw_img = Image.open(io.BytesIO(contents))
        # Let JPEG decode at reduced scale instead of full 12MP resolution.
        raw_img.draft("RGB", (MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        image = ImageOps.exif_transpose(raw_img).convert("RGB")
        # Phone photos (12MP+) blow past the 512 MB Render limit during the
        # full-resolution heatmap overlay. The model only sees 380x380, so
        # cap the working image size; predictions are unaffected.
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to decode image: {str(exc)}",
        )

    try:
        prediction = await run_in_threadpool(inference_service.predict, image)
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
            clinical_summary = await run_in_threadpool(groq_service.generate_clinical_summary, prediction)
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
            await run_in_threadpool(
                history_service.record_scan,
                prediction=prediction,
                image_bytes=contents,
                heatmap_bytes=prediction.saliency_heatmap_bytes,
            )
        except Exception as exc:
            logger.warning(f"Cloud persistence failed (non-fatal): {exc}")

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
    radius_km: float = Query(10.0, description="Search radius in kilometers (max 50)"),
    geo_service: GeolocationService = Depends(get_geolocation_service),
):
    """
    Fetch verified nearby dermatologists and medical centers via OpenStreetMap Overpass with fallback.
    """
    try:
        raw_clinics = geo_service.search_clinics(lat=lat, lon=lon, radius_km=radius_km)
    except ClinicSearchError as exc:
        logger.warning(f"Clinic search unavailable: {exc}")
        return ClinicSearchResponse(
            clinics=[],
            status="unavailable",
            message="Map data service is busy right now. Please try again in a minute.",
        )
    return ClinicSearchResponse(clinics=[ClinicItem(**c) for c in raw_clinics])


@router.post("/api/v1/clinical-summary", response_model=ClinicalSummaryResponse, tags=["Advisory"])
def generate_summary_endpoint(
    payload: ClinicalSummaryRequest,
    groq_service: GroqService = Depends(get_groq_service),
):
    """
    Generate real-time doctor-ready clinical interpretation using Groq LPU (llama-3.3-70b-versatile).
    """
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
    return ClinicalSummaryResponse(clinical_summary=summary_text, model=groq_service.model)
