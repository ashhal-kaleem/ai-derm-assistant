"""Inference Service coordinating ONNX runtime, temperature calibration, and Grad-CAM."""

import time
from typing import Optional
import numpy as np
from PIL import Image

from src.core.calibration import apply_temperature_scaling
from src.core.explainability import (
    generate_gradcam_overlay,
    image_to_png_bytes,
)
from src.core.onnx_engine import ONNXInferenceEngine
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
        engine: Optional[ONNXInferenceEngine] = None,
        temperature: float = 1.25
    ):
        self.engine = engine or ONNXInferenceEngine()
        self.temperature = max(0.1, float(temperature))

    def predict(self, image: Image.Image) -> PredictionResult:
        """Execute full inference pipeline on a PIL RGB image."""
        start_time = time.perf_counter()
        
        # 1. Forward pass via ONNX engine
        raw_logits, activation_map = self.engine.run_inference(image)
        
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
        top_idx = CLASS_NAMES.index(top_prob.code)
        
        # 6. Generate Grad-CAM explainability heatmap overlay
        rgb_array = np.array(image.convert("RGB"), dtype=np.uint8)
        cam_2d = activation_map
            
        overlay_rgb = generate_gradcam_overlay(rgb_array, cam_2d)
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
            saliency_heatmap_bytes=heatmap_png,
            clinical_summary=None,
            gemini_summary=None
        )
