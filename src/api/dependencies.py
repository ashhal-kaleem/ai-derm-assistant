from functools import lru_cache
from src.core.config import get_settings
from src.infrastructure.onnx_engine import ONNXInferenceEngine
from src.infrastructure.supabase_client import SupabaseCloudClient
from src.services.groq_service import GroqService
from src.services.history_service import HistoryService
from src.services.inference_service import InferenceService


@lru_cache()
def get_onnx_engine() -> ONNXInferenceEngine:
    settings = get_settings()
    return ONNXInferenceEngine(model_path=settings.MODEL_PATH)


@lru_cache()
def get_inference_service() -> InferenceService:
    settings = get_settings()
    engine = get_onnx_engine()
    return InferenceService(engine=engine, temperature=settings.DEFAULT_TEMPERATURE)


@lru_cache()
def get_groq_service() -> GroqService:
    settings = get_settings()
    return GroqService(api_key=settings.GROQ_API_KEY)


@lru_cache()
def get_history_service() -> HistoryService:
    settings = get_settings()
    repo = SupabaseCloudClient(url=settings.SUPABASE_URL, key=settings.SUPABASE_KEY)
    return HistoryService(client=repo)
