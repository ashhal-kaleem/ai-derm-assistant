from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClassProbabilityResponse(BaseModel):
    class_code: str
    class_name: str
    probability: float
    risk_level: str


class PredictionResponse(BaseModel):
    # PRD v2.0 Canonical Contract
    predicted_class: str
    class_name: str
    confidence: float
    risk_level: str                      # "green" | "yellow" | "red"
    risk_label: str                      # "Benign" | "Monitor" | "See doctor urgently"
    all_probs: List[float] = Field(default_factory=list)
    uncertainty: str = "low"             # "low" | "medium" | "high"
    heatmap_b64: Optional[str] = None
    llm_explanation: Optional[str] = None

    # Backward-compatible v1.0 Fields
    top_class: Optional[str] = None
    top_name: Optional[str] = None
    raw_confidence: Optional[float] = None
    calibrated_confidence: Optional[float] = None
    temperature: Optional[float] = 1.0
    uncertainty_score: Optional[float] = 0.0
    probabilities: Optional[List[ClassProbabilityResponse]] = None
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
    model: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    onnx_model_loaded: bool
    groq_configured: bool
    supabase_configured: bool
    timestamp: str


class PDFReportRequest(BaseModel):
    prediction: Dict[str, Any]
    history: Optional[List[Dict[str, Any]]] = None


class PDFReportResponse(BaseModel):
    pdf_b64: str


class CreateHistoryRequest(BaseModel):
    lesion_name: str
    prediction: Dict[str, Any]
    image_b64: Optional[str] = None
    notes: Optional[str] = None


class CreateHistoryResponse(BaseModel):
    visit_id: str
    lesion_id: str


class LesionVisitItem(BaseModel):
    visit_id: str
    date: str
    predicted_class: str
    class_name: str
    confidence: float
    risk_level: str
    risk_label: str
    image_thumb: Optional[str] = None
    llm_explanation: Optional[str] = None


class LesionHistoryResponse(BaseModel):
    lesion_id: str
    lesion_name: str
    visits: List[LesionVisitItem]


class ClinicItem(BaseModel):
    name: str
    lat: float
    lon: float
    distance_km: Optional[float] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[str] = None
    is_dermatology: bool = False
    directions_url: str


class ClinicSearchResponse(BaseModel):
    clinics: List[ClinicItem]
    status: str = "ok"
    message: Optional[str] = None
