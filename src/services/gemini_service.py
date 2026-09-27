"""Gemini Clinical Advisory Service with Static Fallback."""

import os
from typing import Optional
from src.domain.knowledge_cards import get_knowledge_card
from src.domain.models import PredictionResult

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class GeminiService:
    """Provides patient-friendly clinical educational summaries using Gemini 2.0 Flash."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key and genai is not None:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    def generate_clinical_summary(self, prediction: PredictionResult) -> str:
        """Generate patient educational narrative, falling back to static card if needed."""
        card = get_knowledge_card(prediction.top_class)
        
        if not self.client:
            return self._build_static_summary(prediction, card)

        system_instruction = (
            "You are DermAssist AI, an educational clinical communication assistant. "
            "You provide clear, empathetic, and medically grounded explanations for skin lesion "
            "classification results. You never diagnose definitively, and you always advocate for "
            "in-person evaluation by a board-certified dermatologist."
        )

        prompt = (
            f"Please generate a concise, structured educational report for this skin lesion analysis:\n\n"
            f"- Primary Finding: {prediction.top_name} ({prediction.top_class})\n"
            f"- Risk Tier: {prediction.risk_level.value}\n"
            f"- Calibrated Model Confidence: {prediction.calibrated_confidence * 100:.1f}%\n"
            f"- Uncertainty Index: {prediction.uncertainty_score:.2f} (0=certain, 1=uncertain)\n"
            f"- Clinical Ground Truth Context: {card['description']}\n"
            f"- Urgency Guidance: {card['urgency']}\n\n"
            f"Provide a 3-part structured breakdown:\n"
            f"1. **Clinical Understanding**: What this classification means in accessible patient language.\n"
            f"2. **Visual/Dermoscopic Indicators**: Why the model and clinicians look closely at this lesion type.\n"
            f"3. **Recommended Next Steps**: Clear guidance on clinical consultation timeframe."
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                    max_output_tokens=500
                )
            )
            if response and response.text:
                return response.text.strip()
            return self._build_static_summary(prediction, card)
        except Exception:
            return self._build_static_summary(prediction, card)

    def _build_static_summary(self, prediction: PredictionResult, card: dict) -> str:
        """Structured fallback narrative built from static clinical knowledge cards."""
        return (
            f"### 📋 Clinical Summary: {card['common_name']}\n\n"
            f"**Risk Level:** `{prediction.risk_level.value}` | "
            f"**Calibrated Confidence:** `{prediction.calibrated_confidence * 100:.1f}%`\n\n"
            f"#### 1. Clinical Understanding\n"
            f"{card['description']}\n\n"
            f"#### 2. Visual & Dermoscopic Features\n"
            f"- **Typical Appearance**: {card['typical_appearance']}\n"
            f"- **ABCDE Dermatological Relevance**: {card['abcde_relevance']}\n\n"
            f"#### 3. Recommended Next Steps\n"
            f"{card['urgency']}\n\n"
            f"*(Generated from verified clinical reference card)*"
        )
