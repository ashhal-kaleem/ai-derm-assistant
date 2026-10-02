"""Domain entities and schemas for DermAssist AI."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import uuid


class RiskLevel(str, Enum):
    BENIGN = "BENIGN"
    POTENTIALLY_MALIGNANT = "POTENTIALLY_MALIGNANT"
    MALIGNANT = "MALIGNANT"


class FeedbackType(str, Enum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class DiagnosisMetadata:
    code: str
    name: str
    risk_level: RiskLevel
    clinical_description: str
    urgency_recommendation: str


DIAGNOSIS_CATALOG: Dict[str, DiagnosisMetadata] = {
    "akiec": DiagnosisMetadata(
        code="akiec",
        name="Actinic Keratoses / Bowen's Disease",
        risk_level=RiskLevel.POTENTIALLY_MALIGNANT,
        clinical_description="Pre-cancerous scaly or crusty growths caused by long-term ultraviolet damage. Can progress to squamous cell carcinoma if untreated.",
        urgency_recommendation="Schedule a non-emergency appointment with a licensed dermatologist within 2-4 weeks."
    ),
    "bcc": DiagnosisMetadata(
        code="bcc",
        name="Basal Cell Carcinoma",
        risk_level=RiskLevel.MALIGNANT,
        clinical_description="The most common type of skin cancer. Arises in basal cells of the epidermis; rarely metastasizes but is locally destructive.",
        urgency_recommendation="Consult a dermatologist promptly for surgical evaluation within 1-2 weeks."
    ),
    "bkl": DiagnosisMetadata(
        code="bkl",
        name="Benign Keratosis-like Lesions",
        risk_level=RiskLevel.BENIGN,
        clinical_description="Non-cancerous skin growths including seborrheic keratoses, solar lentigines, and lichen-planus like keratoses.",
        urgency_recommendation="Routine annual dermatological examination is sufficient unless the lesion bleeds, itches, or changes rapidly."
    ),
    "df": DiagnosisMetadata(
        code="df",
        name="Dermatofibroma",
        risk_level=RiskLevel.BENIGN,
        clinical_description="Common benign cutaneous fibrous histiocytomas, typically presenting as firm, small nodules on extremities.",
        urgency_recommendation="Benign lesion; no medical intervention required unless symptomatic or traumatized."
    ),
    "mel": DiagnosisMetadata(
        code="mel",
        name="Melanoma",
        risk_level=RiskLevel.MALIGNANT,
        clinical_description="The most lethal form of skin cancer, arising from melanocytes. Early diagnosis is critical; 5-year survival drops from 99% localized to 27% metastatic.",
        urgency_recommendation="CRITICAL: Seek immediate, urgent clinical evaluation and biopsy by a licensed dermatologist or oncology center."
    ),
    "nv": DiagnosisMetadata(
        code="nv",
        name="Melanocytic Nevi",
        risk_level=RiskLevel.BENIGN,
        clinical_description="Benign proliferations of melanocytes (commonly known as normal moles). The vast majority never undergo malignant transformation.",
        urgency_recommendation="Monitor periodically using ABCDE criteria (Asymmetry, Border, Color, Diameter, Evolving)."
    ),
    "vasc": DiagnosisMetadata(
        code="vasc",
        name="Vascular Lesions",
        risk_level=RiskLevel.BENIGN,
        clinical_description="Benign vascular anomalies such as cherry angiomas, angiokeratomas, and pyogenic granulomas formed from blood vessels.",
        urgency_recommendation="Benign vascular entity; consult a doctor if recurrent bleeding or rapid growth occurs."
    )
}

CLASS_NAMES: List[str] = ["akiec", "bcc", "bkl", "df", "mel", "nv", "vasc"]


@dataclass
class ClassProbability:
    code: str
    name: str
    probability: float
    risk_level: RiskLevel


@dataclass
class PredictionResult:
    top_class: str
    top_name: str
    risk_level: RiskLevel
    raw_confidence: float
    calibrated_confidence: float
    temperature: float
    uncertainty_score: float
    probabilities: List[ClassProbability]
    saliency_heatmap_bytes: Optional[bytes] = None
    clinical_summary: Optional[str] = None
    gemini_summary: Optional[str] = None


@dataclass
class ScanRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    image_url: str = ""
    heatmap_url: Optional[str] = None
    predicted_class: str = ""
    raw_confidence: float = 0.0
    calibrated_confidence: float = 0.0
    temperature: float = 1.0
    uncertainty_score: float = 0.0
    risk_level: str = "BENIGN"
    clinical_summary: Optional[str] = None
    gemini_summary: Optional[str] = None
    feedback: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
