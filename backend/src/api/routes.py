import base64
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from PIL import Image, ImageOps

from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from src.api.dependencies import (
    get_geolocation_service,
    get_groq_service,
    get_history_service,
    get_inference_service,
    get_report_service,
    get_feedback_service,
    verify_admin_access,
)
from src.core.config import APP_VERSION, get_settings
from src.core.rate_limit import enforce_rate_limit, prediction_slot
from src.core.security import validate_image_payload
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
    FeedbackRequest,
    FeedbackResponse,
)
from src.domain.models import (
    PredictionResult,
    RiskLevel,
    categorize_uncertainty,
    map_risk_tier,
    CLASS_NAMES,
)
from src.services.geolocation_service import ClinicSearchError, GeolocationService
from src.services.groq_service import GroqService
from src.services.history_service import HistoryService
from src.services.inference_service import InferenceService
from src.services.report_service import ReportService
from src.services.feedback_service import FeedbackService
from src.services.quality_service import assess_image_quality

logger = logging.getLogger("dermassist.routes")

MAX_IMAGE_SIDE = 1024
ALLOWED_SEXES = ("male", "female", "other")

router = APIRouter()


def build_patient_metadata(
    age: Optional[int],
    sex: Optional[str],
    anatomical_site: Optional[str],
    history_of_melanoma: Optional[bool] = None,
) -> Dict[str, Any]:
    """Validated, PII-safe patient context (never logged). Unknown values are dropped."""
    meta: Dict[str, Any] = {}
    if age is not None and 1 <= age <= 120:
        meta["age"] = age
    if sex:
        norm_sex = sex.strip().lower()
        if norm_sex in ALLOWED_SEXES:
            meta["sex"] = norm_sex
    if anatomical_site:
        clean_site = anatomical_site.strip()
        if clean_site:
            meta["anatomical_site"] = clean_site[:64]
    if history_of_melanoma is not None:
        meta["history_of_melanoma"] = bool(history_of_melanoma)
    return meta

@router.api_route("/", methods=["GET", "HEAD"], tags=["Discovery"])
def api_root():
    """Canonical API Service Discovery Manifest for headless clients and developers."""
    settings = get_settings()
    docs_status = "/docs" if (settings.ENABLE_DOCS or settings.ENVIRONMENT != "production") else "disabled_in_production"
    return {
        "service": "DermAssist AI — Clinical Inference Engine",
        "version": APP_VERSION,
        "status": "operational",
        "docs_url": docs_status,
        "endpoints": {
            "predict": "POST /predict",
            "feedback": "POST /feedback",
            "clinical_summary": "POST /clinical-summary",
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
        groq_configured=bool(get_settings().GROQ_API_KEY),
        supabase_configured=supabase_ok,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

@router.post("/predict", response_model=PredictionResponse, tags=["Inference"], dependencies=[Depends(enforce_rate_limit)])
async def predict_lesion(
    file: UploadFile = File(..., description="Dermatoscopic skin lesion image file (JPEG/PNG)"),
    generate_summary: bool = Query(True, description="Whether to generate Groq LPU clinical advice"),
    save_to_cloud: bool = Query(True, description="Persist image and prediction to Supabase Cloud"),
    age: Optional[int] = Form(None, ge=1, le=120, description="Optional patient age (1-120)"),
    sex: Optional[str] = Form(None, description="Optional patient biological sex ('male', 'female', 'other')"),
    anatomical_site: Optional[str] = Form(None, max_length=64, description="Optional lesion anatomical location"),
    history_of_melanoma: Optional[bool] = Form(None, description="Optional personal or familial history of melanoma"),
    inference_service: InferenceService = Depends(get_inference_service),
    groq_service: GroqService = Depends(get_groq_service),
    history_service: HistoryService = Depends(get_history_service),
):
    """
        Run DermAssist v3 ensemble ONNX inference (image + age/sex/site), temperature calibration, melanoma threshold, and occlusion-sensitivity visualization.
    Conforms directly to PRD v2.0 mobile contract.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a valid image (JPEG/PNG).",
        )

    # Read at most limit+1 bytes so an oversized upload is never fully loaded.
    max_bytes = get_settings().MAX_UPLOAD_SIZE_MB * 1024 * 1024
    contents = await file.read(max_bytes + 1)
    is_valid, validation_err = validate_image_payload(contents, max_bytes=max_bytes)
    if not is_valid:
        err_msg = validation_err or "Invalid image payload."
        if "exceeds" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )

    try:
        raw_img = Image.open(io.BytesIO(contents))
        # Let JPEG decode at reduced scale instead of full 12MP resolution.
        raw_img.draft("RGB", (MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        image = ImageOps.exif_transpose(raw_img)
        # Phone photos (12MP+) blow past the 512 MB Render limit during the
        # full-resolution heatmap overlay. The v3 models resize to 448 first, so
        # cap the working image size; predictions are unaffected.
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.BILINEAR)
    except Exception as exc:
        logger.error(f"Failed to decode image: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode image. Please ensure it is a valid, uncorrupted JPEG/PNG image.",
        )

    quality = assess_image_quality(image)
    if not quality.acceptable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "IMAGE_QUALITY_INSUFFICIENT",
                "message": quality.reason,
                "sharpness": quality.sharpness,
                "contrast": quality.contrast,
            },
        )

    # Patient metadata feeds the v3 model (age, sex, anatomical site); missing
    # values are encoded exactly like missing values in training.
    patient_meta = build_patient_metadata(age, sex, anatomical_site, history_of_melanoma)
    model_metadata: Dict[str, Any] = {
        "age": patient_meta.get("age"),
        "sex": patient_meta.get("sex"),
        "anatomical_site": patient_meta.get("anatomical_site"),
    }

    try:
        # One model run at a time keeps the instance inside its memory limit.
        async with prediction_slot():
            prediction = await run_in_threadpool(inference_service.predict, image, model_metadata)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Inference failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image analysis failed. Please try again later.",
        )

    # 1. Map to PRD v2.0 3-Tier Risk Badge (green / yellow / red)
    v2_risk_level, v2_risk_label = map_risk_tier(prediction.top_class)
    if not prediction.is_actionable:
        v2_risk_level, v2_risk_label = "yellow", "Monitor"
    if prediction.routing_zone == "red" and prediction.risk_level.value == "MALIGNANT":
        v2_risk_level, v2_risk_label = "red", "See doctor urgently"
    # Sync routing_zone back: a benign class routed yellow (moderate confidence)
    # must not display a green badge — that would mislead the user.
    if prediction.routing_zone == "yellow" and v2_risk_level == "green":
        v2_risk_level, v2_risk_label = "yellow", "Monitor"
    v2_uncertainty = categorize_uncertainty(prediction.uncertainty_score)
    probs_by_code = {p.code: float(p.probability) for p in prediction.probabilities}
    all_probs = [probs_by_code.get(c, 0.0) for c in CLASS_NAMES]

    # 2. Generate Groq clinical advisory summary
    clinical_summary = None
    if generate_summary:
        if prediction.is_actionable:
            try:
                clinical_summary = await run_in_threadpool(
                    groq_service.generate_clinical_summary,
                    prediction,
                    patient_metadata=patient_meta if patient_meta else None,
                )
                prediction.clinical_summary = clinical_summary
            except Exception:
                clinical_summary = None
        else:
            clinical_summary = (
                "This image was inconclusive and no lesion type was assigned. "
                "Please retake the photo in focus with the lesion filling the frame and "
                "have any persistent, changing, bleeding, or suspicious lesion examined "
                "by a dermatologist."
            )

    # 3. Base64 encode occlusion-sensitivity heatmap
    heatmap_b64 = None
    if prediction.saliency_heatmap_bytes:
        heatmap_b64 = base64.b64encode(prediction.saliency_heatmap_bytes).decode("utf-8")

    # 4. Optional cloud persistence
    saved_record = None
    if save_to_cloud:
        try:
            saved_record = await run_in_threadpool(
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
        is_actionable=prediction.is_actionable,
        abstention_reason=prediction.abstention_reason,
        routing_zone=prediction.routing_zone,
        scan_id=saved_record.id if saved_record else None,
        quality={
            "acceptable": quality.acceptable,
            "sharpness": quality.sharpness,
            "contrast": quality.contrast,
            "skin_detected": quality.skin_detected,
            "skin_fraction": quality.skin_fraction,
        },
        probabilities=probs_response,
    )


@router.post("/feedback", response_model=FeedbackResponse, tags=["Monitoring"])
def submit_feedback(
    payload: FeedbackRequest,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    try:
        return feedback_service.record(payload.feedback, payload.predicted_class, payload.corrected_class)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/feedback/summary", response_model=FeedbackResponse, tags=["Monitoring"])
def feedback_summary(
    feedback_service: FeedbackService = Depends(get_feedback_service),
    _admin_verified: bool = Depends(verify_admin_access),
):
    return feedback_service.summary()


@router.post("/report", response_model=PDFReportResponse, tags=["Reports"])
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
        logger.error(f"PDF generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation failed. Please try again later.",
        )


@router.get("/history", tags=["History"])
def get_scan_history(
    limit: int = Query(10, ge=1, le=100),
    history_service: HistoryService = Depends(get_history_service),
):
    """Fetch recent skin lesion scans and clinical metadata from Supabase Cloud."""
    return history_service.get_recent_scans(limit=limit)


@router.post("/history", response_model=CreateHistoryResponse, tags=["History"])
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
def find_nearby_clinics(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    radius_km: float = Query(10.0, le=50.0, description="Search radius in kilometers (max 50)"),
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


@router.post("/clinical-summary", response_model=ClinicalSummaryResponse, tags=["Advisory"], dependencies=[Depends(enforce_rate_limit)])
async def generate_summary_endpoint(
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

    patient_meta = build_patient_metadata(
        payload.age, payload.sex, payload.anatomical_site, payload.history_of_melanoma
    )

    summary_text = await run_in_threadpool(
        groq_service.generate_clinical_summary,
        dummy_pred,
        patient_metadata=patient_meta if patient_meta else None,
    )
    return ClinicalSummaryResponse(clinical_summary=summary_text, model=groq_service.model)
