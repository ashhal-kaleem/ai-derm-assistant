"""Automated integration test suite for InferenceService."""

import numpy as np
from PIL import Image
import pytest

from src.core.onnx_engine import ONNXInferenceEngine
from src.domain.models import CLASS_NAMES, RiskLevel
from src.services.inference_service import InferenceService


def test_inference_service_full_pipeline():
    """Verify inference pipeline produces valid calibrated prediction and Grad-CAM overlay."""
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
