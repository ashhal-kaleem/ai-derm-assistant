"""Inference service coordinating ONNX runtime, calibration, and occlusion sensitivity."""

import time
from typing import Any, Dict, Optional
import numpy as np
from PIL import Image

from src.domain.calibration import apply_temperature_scaling
from src.infrastructure.explainability import (
    generate_occlusion_overlay,
    image_to_png_bytes,
)
from src.infrastructure.ensemble_engine import V3EnsembleEngine
from src.domain.models import (
    CLASS_NAMES,
    DIAGNOSIS_CATALOG,
    ClassProbability,
    PredictionResult,
)


class InferenceService:
    """Orchestrates image inference, calibration, and explainability overlay."""

    def __init__(
        self,
        engine: Optional[Any] = None,
        temperature: float = 1.0,
        mel_threshold: Optional[float] = None,
    ):
        self.engine = engine or V3EnsembleEngine()
        self.temperature = max(0.1, float(temperature))
        # Melanoma operating point chosen on the calibration split (v3: 0.34):
        # if calibrated P(mel) >= threshold, the prediction is melanoma.
        self.mel_threshold = float(mel_threshold) if mel_threshold is not None else None

    # Conservative provisional gates. These are engineering guardrails, not
    # clinically validated operating points; review/abstention is preferred to
    # false reassurance while external clinical validation is pending.
    MIN_ACTIONABLE_CONFIDENCE = 0.80
    MIN_ACTIONABLE_MARGIN = 0.20
    MAX_ACTIONABLE_UNCERTAINTY = 0.50
    MIN_GREEN_CONFIDENCE = 0.85
    MIN_GREEN_MARGIN = 0.25
    MAX_GREEN_UNCERTAINTY = 0.40
    BENIGN_CODES = frozenset({"bkl", "df", "nv", "vasc"})

    def predict(self, image: Image.Image, metadata: Optional[Dict[str, Any]] = None) -> PredictionResult:
        """Execute full inference pipeline on a PIL RGB image (+ optional age/sex/anatomical_site)."""
        start_time = time.perf_counter()

        # 1. Forward pass: v3 ensemble log-probabilities (image + patient metadata)
        raw_logits = self.engine.ensemble_logits(image, metadata)
        
        # 2. Raw softmax confidence
        raw_exp = np.exp(raw_logits - np.max(raw_logits))
        raw_probs = raw_exp / np.sum(raw_exp)
        
        # 3. Calibrated softmax probabilities via temperature scaling
        calibrated_probs = apply_temperature_scaling(raw_logits, self.temperature)
        
        # 4. Uncertainty score (Normalized Shannon Entropy: H(P) / log(K))
        num_classes = len(CLASS_NAMES)
        entropy = -np.sum(calibrated_probs * np.log(np.clip(calibrated_probs, 1e-12, 1.0)))
        max_entropy = np.log(num_classes)
        normalized_uncertainty = float(np.clip(entropy / max_entropy, 0.0, 1.0))
        
        # 5. Build sorted class probabilities
        class_prob_list = []
        for i, code in enumerate(CLASS_NAMES):
            meta = DIAGNOSIS_CATALOG[code]
            class_prob_list.append(
                ClassProbability(
                    code=code,
                    name=meta.name,
                    probability=float(calibrated_probs[i]),
                    risk_level=meta.risk_level
                )
            )
        
        class_prob_list.sort(key=lambda x: x.probability, reverse=True)
        top_prob = class_prob_list[0]
        mel_idx = CLASS_NAMES.index("mel")
        if (
            self.mel_threshold is not None
            and top_prob.code != "mel"
            and calibrated_probs[mel_idx] >= self.mel_threshold
        ):
            top_prob = next(p for p in class_prob_list if p.code == "mel")
        top_idx = CLASS_NAMES.index(top_prob.code)
        runner_up = max(p.probability for p in class_prob_list if p.code != top_prob.code)
        margin = top_prob.probability - runner_up

        abstention_reasons = []
        if top_prob.probability < self.MIN_ACTIONABLE_CONFIDENCE:
            abstention_reasons.append("calibrated confidence is below the safe threshold")
        if margin < self.MIN_ACTIONABLE_MARGIN:
            abstention_reasons.append("the leading lesion classes are too close to separate reliably")
        if normalized_uncertainty > self.MAX_ACTIONABLE_UNCERTAINTY:
            abstention_reasons.append("the model output is highly uncertain")

        # Routing is deliberately stricter than simply displaying the top
        # class: malignant and potentially malignant classes always require
        # clinician review, while only high-confidence benign outputs can be
        # routed green. Abstentions are never presented as benign/actionable.
        if top_prob.risk_level.value == "MALIGNANT":
            routing_zone = "red"
        elif top_prob.code == "akiec" or abstention_reasons:
            routing_zone = "yellow"
        elif (
            top_prob.code in self.BENIGN_CODES
            and top_prob.probability >= self.MIN_GREEN_CONFIDENCE
            and margin >= self.MIN_GREEN_MARGIN
            and normalized_uncertainty <= self.MAX_GREEN_UNCERTAINTY
        ):
            routing_zone = "green"
        else:
            routing_zone = "yellow"
        
        # 6. Generate occlusion-sensitivity explainability heatmap overlay
        rgb_array = np.array(image.convert("RGB"), dtype=np.uint8)
        activation_map = self.engine.occlusion_map(image, metadata, top_idx)
        overlay_rgb = generate_occlusion_overlay(rgb_array, activation_map)
        heatmap_png = image_to_png_bytes(overlay_rgb)
        
        return PredictionResult(
            top_class=top_prob.code,
            top_name=top_prob.name,
            risk_level=top_prob.risk_level,
            raw_confidence=float(raw_probs[top_idx]),
            calibrated_confidence=float(calibrated_probs[top_idx]),
            temperature=self.temperature,
            uncertainty_score=normalized_uncertainty,
            probabilities=class_prob_list,
            is_actionable=not abstention_reasons,
            abstention_reason="; ".join(abstention_reasons) if abstention_reasons else None,
            routing_zone=routing_zone,
            inference_ms=(time.perf_counter() - start_time) * 1000.0,
            saliency_heatmap_bytes=heatmap_png,
            clinical_summary=None,
        )
