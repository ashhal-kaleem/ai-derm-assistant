from typing import List, Optional
from pydantic import BaseModel, Field


class ClassProbabilityResponse(BaseModel):
    class_code: str
    class_name: str
    probability: float
    risk_level: str


class PredictionResponse(BaseModel):
    top_class: str
    top_name: str
    risk_level: str
    raw_confidence: float
    calibrated_confidence: float
    temperature: float
    uncertainty_score: float
    probabilities: List[ClassProbabilityResponse]
    saliency_heatmap_base64: Optional[str] = None
    clinical_summary: Optional[str] = None


class ClinicalSummaryRequest(BaseModel):
    top_class: str
    top_name: str
    risk_level: str
    calibrated_confidence: float
    temperature: float = 1.0
    uncertainty_score: float = 0.0


class ClinicalSummaryResponse(BaseModel):
    clinical_summary: str
    model: str = "llama-3.3-70b-versatile"


class HealthResponse(BaseModel):
    status: str
    onnx_model_loaded: bool
    groq_configured: bool
    supabase_configured: bool
    timestamp: str
