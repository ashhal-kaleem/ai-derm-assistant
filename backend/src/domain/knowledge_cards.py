"""Static Clinical Knowledge Cards and Safety Disclaimers for DermAssist AI."""

from typing import Any, Dict

MANDATORY_MEDICAL_DISCLAIMER: str = (
    "⚠️ MEDICAL DISCLAIMER: This application is strictly an educational and triage assistance tool. "
    "It is NOT a medical device, is NOT approved by the FDA or CE for clinical diagnosis, and cannot "
    "replace professional judgment. Skin lesions must be evaluated by a board-certified dermatologist "
    "or qualified healthcare provider. Never delay seeking medical advice based on these AI outputs."
)

STATIC_KNOWLEDGE_CARDS: Dict[str, Dict[str, Any]] = {
    "akiec": {
        "code": "akiec",
        "common_name": "Actinic Keratosis / Bowen's Disease",
        "risk_tier": "POTENTIALLY_MALIGNANT",
        "badge_color": "#FFA500",
        "description": (
            "Actinic keratoses are rough, scaly patches caused by chronic ultraviolet (UV) radiation damage. "
            "They represent intraepidermal dysplasia and are considered pre-cancerous, with approximately 10% "
            "transforming into invasive squamous cell carcinoma (SCC) if left untreated."
        ),
        "typical_appearance": "Dry, scaly, erythematous or brown gritty macules/papules, often felt before seen.",
        "abcde_relevance": "Typically exhibits irregular borders and surface erythema on sun-exposed skin (face, scalp, arms).",
        "urgency": "Consult a dermatologist within 2-4 weeks for cryotherapy, topical 5-FU, or photodynamic therapy.",
        "urgency_level": "MODERATE"
    },
    "bcc": {
        "code": "bcc",
        "common_name": "Basal Cell Carcinoma",
        "risk_tier": "MALIGNANT",
        "badge_color": "#FF4B4B",
        "description": (
            "Basal cell carcinoma is the most common cutaneous malignancy. It originates in basal cells of the "
            "deepest epidermal layer. While BCC rarely metastasizes to distant organs, it is locally invasive "
            "and can cause extensive structural destruction if ignored."
        ),
        "typical_appearance": "Pearly or waxy papules with central ulceration, rolled translucent borders, and telangiectatic vessels.",
        "abcde_relevance": "Shows border irregularity, localized ulceration, and arborizing telangiectasia under dermoscopy.",
        "urgency": "Prompt dermatological or Mohs micrographic surgery evaluation recommended within 1-2 weeks.",
        "urgency_level": "HIGH"
    },
    "bkl": {
        "code": "bkl",
        "common_name": "Benign Keratosis (Seborrheic Keratosis / Solar Lentigo)",
        "risk_tier": "BENIGN",
        "badge_color": "#28A745",
        "description": (
            "Benign keratosis-like lesions comprise harmless epidermal proliferations, including seborrheic "
            "keratoses and solar lentigines. They are entirely benign and carry zero risk of malignant transformation."
        ),
        "typical_appearance": "Well-demarcated, 'stuck-on' waxy, brown, yellow, or black verrucous plaques with keratin pseudocysts.",
        "abcde_relevance": "May appear dark or heterogeneous, frequently mimicking melanoma to the untrained eye, but features distinctive comedo-like openings under dermoscopy.",
        "urgency": "Routine clinical observation. No excision needed unless irritated or cosmetically desired.",
        "urgency_level": "LOW"
    },
    "df": {
        "code": "df",
        "common_name": "Dermatofibroma",
        "risk_tier": "BENIGN",
        "badge_color": "#28A745",
        "description": (
            "Dermatofibroma is a harmless, slow-growing benign cutaneous fibrous histiocytoma formed by a mixture "
            "of fibroblasts, macrophages, and capillaries, often triggered by minor trauma such as an insect bite."
        ),
        "typical_appearance": "Firm, hyperpigmented reddish-brown nodule, typically on lower limbs. Exhibits the classic 'dimple sign' (pinching causes inward retraction).",
        "abcde_relevance": "Central white patch surrounded by a delicate pigment network under dermatoscopy.",
        "urgency": "Benign entity; treatment is unnecessary unless painful or continually irritated.",
        "urgency_level": "LOW"
    },
    "mel": {
        "code": "mel",
        "common_name": "Melanoma",
        "risk_tier": "MALIGNANT",
        "badge_color": "#D32F2F",
        "description": (
            "Melanoma is the most aggressive and life-threatening skin cancer. It develops from melanocytes and "
            "can rapidly invade lymphatic and vascular networks. When detected at an early localized stage, "
            "5-year survival exceeds 99%, but drops sharply once metastatic."
        ),
        "typical_appearance": "Asymmetric, irregular border, variegated shades of dark brown/black/blue/red, diameter > 6mm, or rapidly evolving.",
        "abcde_relevance": "Exhibits all classical ABCDE criteria: atypical pigment networks, regression structures, blue-white veils, and pseudopods.",
        "urgency": "CRITICAL: Urgent dermatological consultation and excisional biopsy required immediately. Do not delay.",
        "urgency_level": "CRITICAL"
    },
    "nv": {
        "code": "nv",
        "common_name": "Melanocytic Nevus (Normal Mole)",
        "risk_tier": "BENIGN",
        "badge_color": "#28A745",
        "description": (
            "Common melanocytic nevi are benign clusters of normal melanocytes. They constitute over 67% of skin "
            "lesions in clinical presentations and the overwhelming majority remain completely benign throughout a lifetime."
        ),
        "typical_appearance": "Symmetric, uniform tan/brown macule or papule with smooth, regular borders.",
        "abcde_relevance": "Symmetric distribution of pigment with uniform network or globular patterns.",
        "urgency": "Self-monitor monthly using ABCDE guidelines. Consult a clinician if change in size, shape, or color is noticed.",
        "urgency_level": "LOW"
    },
    "vasc": {
        "code": "vasc",
        "common_name": "Vascular Lesion (Angioma / Pyogenic Granuloma)",
        "risk_tier": "BENIGN",
        "badge_color": "#28A745",
        "description": (
            "Cutaneous vascular lesions consist of dilated blood vessels and endothelial cells. Common types include "
            "cherry angiomas, venous lakes, and pyogenic granulomas. They are benign and non-cancerous."
        ),
        "typical_appearance": "Bright red to purple macules, papules, or nodules that may blanch under pressure.",
        "abcde_relevance": "Dermoscopy shows red, purple, or blue-black lacunae/clods without a melanocytic pigment network.",
        "urgency": "Routine checkup unless sudden bleeding or rapid ulceration occurs.",
        "urgency_level": "LOW"
    }
}


def get_knowledge_card(class_code: str) -> Dict[str, Any]:
    """Retrieve verified static clinical knowledge card by class code."""
    code = class_code.lower().strip()
    return STATIC_KNOWLEDGE_CARDS.get(code, STATIC_KNOWLEDGE_CARDS["nv"])
