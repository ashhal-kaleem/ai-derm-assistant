from functools import lru_cache
from typing import Any, List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized Application Configuration (Single Source of Truth)."""
    
    # Model & Inference
    # DermAssist v3 ensemble (ConvNeXt-V2-T + EfficientNetV2-S + EVA02-S).
    # checkpoints/v3/ holds model_v3.json (classes, preprocessing, temperature,
    # melanoma threshold) and the member .onnx files.
    MODEL_V3_DIR: Optional[str] = None  # default: backend/checkpoints/v3
    ONNX_THREADS: int = 2
    
    # Groq LPU Clinical Narrative (Secret masked in __repr__)
    GROQ_API_KEY: Optional[str] = Field(default=None, repr=False)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Supabase Persistence (Secret masked in __repr__)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = Field(default=None, repr=False)
    SUPABASE_BUCKET: str = "scans"
    
    # Security, Access Control & Hardening
    ALLOWED_ORIGINS: List[str] = ["*"]
    ENABLE_DOCS: bool = False  # Lock OpenAPI/Swagger docs in production unless explicitly enabled
    ADMIN_API_KEY: Optional[str] = Field(default=None, repr=False)  # Secret key for admin routes
    FORCE_HTTPS: bool = True  # Enforce HTTPS redirection in production behind proxies
    MAX_UPLOAD_SIZE_MB: int = 15  # Max upload size in megabytes (DoS guard)

    # Server / Runtime
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    ENVIRONMENT: str = "production"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
