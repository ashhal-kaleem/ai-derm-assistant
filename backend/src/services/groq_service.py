"""Groq Clinical Advisory Service with Static Fallback."""

import os
from typing import Any, Optional
from src.domain.knowledge_cards import get_knowledge_card
from src.domain.models import PredictionResult

try:
    from groq import Groq
except ImportError:
    Groq = None


class GroqService:
    """Provides patient-friendly clinical educational summaries using Groq (Llama 3.3 70B)."""

    def __init__(self, api_key: Any = "DEFAULT_KEY"):
        if api_key == "DEFAULT_KEY":
            self.api_key = os.getenv("GROQ_API_KEY")
        else:
            self.api_key = api_key
        self.client = None
        if self.api_key and Groq is not None:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception:
                self.client = None

    def generate_clinical_summary(self, prediction: PredictionResult) -> str:
        """Generate patient educational narrative, falling back to static card if needed."""
        card = get_knowledge_card(prediction.top_class)

        if not self.client:
            return self._build_static_summary(prediction, card)

        system_instruction = (
            "You are a board-certified dermatologist writing a concise clinical chart note for a patient. "
            "Write in a natural, authoritative, physician-grade clinical voice. "
            "RULES: "
            "1. Strictly 2 to 3 sentences total (under 75 words). "
            "2. NEVER use markdown tables, bullet points, headers, asterisks, or pipe characters. "
            "3. NEVER use AI meta-intros, conversational preamble, or disclaimers (e.g. no 'As an AI', 'What the model saw'). "
            "4. Cover: 1) What the lesion is in plain terms, 2) Why its features indicate its risk tier, and 3) Recommended clinical step."
        )

        prompt = (
            f"Patient Lesion Assessment:\n"
            f"- Clinical Classification: {prediction.top_name} ({prediction.top_class})\n"
            f"- Risk Tier: {prediction.risk_level.value}\n"
            f"- Calibrated Confidence: {prediction.calibrated_confidence * 100:.1f}%\n"
            f"- Clinical Ground Truth: {card['description']}\n"
            f"- Recommended Action: {card['urgency']}\n\n"
            f"Write the concise 2-to-3 sentence clinical note."
        )

        fallback_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
        for model_name in fallback_models:
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model=model_name,
                    temperature=0.1,
                    max_tokens=100
                )
                content = chat_completion.choices[0].message.content
                if content:
                    return content.strip()
            except Exception:
                continue
        return self._build_static_summary(prediction, card)

    def _build_static_summary(self, prediction: PredictionResult, card: dict) -> str:
        """Concise physician-grade fallback narrative built from static clinical knowledge cards."""
        return (
            f"Clinical impression is consistent with {card['common_name']}. Classification triage: {prediction.risk_level.value} with {prediction.calibrated_confidence * 100:.1f}% confidence. "
            f"{card['description'].split('.')[0]}. "
            f"{card['urgency']}"
        )
