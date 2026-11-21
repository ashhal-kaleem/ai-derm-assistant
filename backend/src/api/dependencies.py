from functools import lru_cache
from typing import Optional
from fastapi import Header, HTTPException, status
from src.core.config import get_settings
from src.core.security import verify_admin_key
from src.infrastructure.onnx_engine import ONNXInferenceEngine
from src.infrastructure.ensemble_engine import V3EnsembleEngine
from src.infrastructure.supabase_client import SupabaseCloudClient
from src.services.feedback_service import FeedbackService
from src.services.geolocation_service import GeolocationService
from src.services.groq_service import GroqService
from src.services.history_service import HistoryService
from src.services.inference_service import InferenceService
from src.services.report_service import ReportService


def verify_admin_access(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")) -> bool:
    """Validate administrator key header (X-Admin-Key) against configured secret."""
    settings = get_settings()
    if settings.ADMIN_API_KEY:
        if not x_admin_key or not verify_admin_key(x_admin_key, settings.ADMIN_API_KEY):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing administrator key.",
            )
    return True


@lru_cache()
def get_onnx_engine():
    """v3 ensemble when its files are present (default), else the legacy EfficientNet-B4."""
    settings = get_settings()
    if settings.USE_V3_ENSEMBLE:
        engine = V3EnsembleEngine(model_dir=settings.MODEL_V3_DIR, threads=settings.ONNX_THREADS)
        if engine.loaded:
            return engine
    return ONNXInferenceEngine(model_path=settings.MODEL_PATH)


def get_model_version() -> str:
    engine = get_onnx_engine()
    return getattr(engine, "model_version", None) or get_settings().MODEL_VERSION


@lru_cache()
def get_inference_service() -> InferenceService:
    settings = get_settings()
    engine = get_onnx_engine()
    temperature = engine.calibration_temperature or settings.DEFAULT_TEMPERATURE
    return InferenceService(
        engine=engine,
        temperature=temperature,
        mel_threshold=getattr(engine, "mel_threshold", None),
    )


@lru_cache()
def get_groq_service() -> GroqService:
    settings = get_settings()
    return GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)


@lru_cache()
def get_history_service() -> HistoryService:
    settings = get_settings()
    repo = SupabaseCloudClient(url=settings.SUPABASE_URL, key=settings.SUPABASE_KEY)
    return HistoryService(client=repo)


@lru_cache()
def get_feedback_service() -> FeedbackService:
    return FeedbackService()


@lru_cache()
def get_report_service() -> ReportService:
    return ReportService()


@lru_cache()
def get_geolocation_service() -> GeolocationService:
    return GeolocationService()
