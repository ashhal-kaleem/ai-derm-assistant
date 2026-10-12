import logging
from contextlib import asynccontextmanager
from PIL import Image
from fastapi import FastAPI

from src.api.dependencies import get_inference_service
from src.core.config import get_settings

logger = logging.getLogger("dermassist.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: pre-warms ONNX inference engine and logs config."""
    settings = get_settings()
    logger.info("Initializing DermAssist AI Engine...")
    
    # Warmup ONNX engine with synthetic 224x224 input
    try:
        service = get_inference_service()
        dummy_img = Image.new("RGB", (settings.INPUT_SIZE, settings.INPUT_SIZE), color=(128, 128, 128))
        service.predict(dummy_img)
        logger.info(f"ONNX Model pre-warmed successfully: {settings.MODEL_PATH}")
    except Exception as exc:
        logger.warning(f"ONNX Model pre-warmup warning (non-fatal): {exc}")
    
    yield
    
    logger.info("DermAssist AI Engine shutdown complete.")
