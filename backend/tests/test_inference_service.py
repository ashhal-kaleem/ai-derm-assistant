"""Automated integration test suite for InferenceService."""

import numpy as np
from PIL import Image
import pytest

from src.domain.models import CLASS_NAMES, RiskLevel
from src.services.inference_service import InferenceService


class _FixedEngine:
    def __init__(self, probabilities):
        self.logits = np.log(np.asarray(probabilities, dtype=np.float32))

    def ensemble_logits(self, image, metadata=None):
        return self.logits

    def occlusion_map(self, image, metadata, target_idx):
        return np.zeros((4, 4), dtype=np.float32)


def _predict_with_probabilities(probabilities):
    image = Image.fromarray(np.full((128, 128, 3), 180, dtype=np.uint8))
    service = InferenceService(engine=_FixedEngine(probabilities), temperature=1.0)
    return service.predict(image)


def test_inference_service_full_pipeline():
    """Verify inference pipeline produces a calibrated prediction and occlusion overlay."""
    # Create synthetic lesion image (RGB 128x128)
    img_data = np.full((128, 128, 3), 180, dtype=np.uint8)
    # Add darker lesion center
    img_data[40:88, 40:88, :] = [100, 50, 40]
    pil_image = Image.fromarray(img_data)

    service = InferenceService(temperature=1.25)
    result = service.predict(pil_image)

    # Assert basic structure
    assert result.top_class in CLASS_NAMES
    assert isinstance(result.top_name, str)
    assert isinstance(result.risk_level, RiskLevel)
    assert 0.0 <= result.raw_confidence <= 1.0
    assert 0.0 <= result.calibrated_confidence <= 1.0
    assert result.temperature == 1.25
    assert 0.0 <= result.uncertainty_score <= 1.0

    # Assert 7 classes sorted descending
    assert len(result.probabilities) == 7
    probs = [p.probability for p in result.probabilities]
    assert np.isclose(sum(probs), 1.0, atol=1e-4)
    assert probs == sorted(probs, reverse=True)

    # Assert heatmap overlay bytes generated
    assert result.saliency_heatmap_bytes is not None
    assert len(result.saliency_heatmap_bytes) > 100


def test_conservative_benign_green_gate_requires_high_confidence():
    result = _predict_with_probabilities([0.01, 0.01, 0.03, 0.01, 0.01, 0.90, 0.03])

    assert result.is_actionable is True
    assert result.routing_zone == "green"


def test_low_confidence_prediction_abstains_and_routes_yellow():
    result = _predict_with_probabilities([0.12, 0.08, 0.18, 0.08, 0.16, 0.30, 0.08])

    assert result.is_actionable is False
    assert result.routing_zone == "yellow"
    assert result.abstention_reason


def test_malignant_prediction_always_routes_red_for_review():
    result = _predict_with_probabilities([0.01, 0.01, 0.01, 0.01, 0.90, 0.05, 0.01])

    assert result.routing_zone == "red"
    assert result.risk_level == RiskLevel.MALIGNANT
