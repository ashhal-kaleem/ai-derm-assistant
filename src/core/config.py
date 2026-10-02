from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized Application Configuration (Single Source of Truth)."""
    
    # Model & Inference
    MODEL_PATH: str = "checkpoints/efficientnet_b4_ham10000.onnx"
    DEFAULT_TEMPERATURE: float = 1.0
    INPUT_SIZE: int = 224
    
    # Groq LPU Clinical Narrative
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Supabase Persistence
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_BUCKET: str = "scans"
    
    # Server / Runtime
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    ENVIRONMENT: str = "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
