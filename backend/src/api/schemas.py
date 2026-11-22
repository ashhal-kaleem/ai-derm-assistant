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
    is_actionable: bool = True
    abstention_reason: Optional[str] = None
    routing_zone: str = "yellow"
    scan_id: Optional[str] = None
    quality: Optional[Dict[str, Any]] = None

    probabilities: List[ClassProbabilityResponse] = Field(default_factory=list)


class ClinicalSummaryRequest(BaseModel):
    top_class: str
    top_name: str
    risk_level: str
    calibrated_confidence: float
    temperature: float = 1.0
    uncertainty_score: float = 0.0
    age: Optional[int] = Field(None, ge=1, le=120, description="Optional patient age in years")
    sex: Optional[str] = Field(None, description="Optional patient biological sex ('male', 'female', 'other')")
    anatomical_site: Optional[str] = Field(None, max_length=64, description="Optional lesion anatomical site")
    history_of_melanoma: Optional[bool] = Field(None, description="Optional personal or familial history of melanoma")


class ClinicalSummaryResponse(BaseModel):
    clinical_summary: str
    model: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    onnx_model_loaded: bool
    groq_configured: bool
    supabase_configured: bool
    timestamp: str


class FeedbackRequest(BaseModel):
    feedback: str
    predicted_class: str
    corrected_class: Optional[str] = None


class FeedbackResponse(BaseModel):
    counts: Dict[str, int]
    incorrect_class_pairs: Dict[str, int]
    total: int


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
    change_detected: bool = False
    change_reasons: List[str] = Field(default_factory=list)


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
