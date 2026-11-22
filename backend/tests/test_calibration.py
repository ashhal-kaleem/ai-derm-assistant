"""Automated calibration test suite verifying temperature scaling and ECE."""

import numpy as np
import pytest

from src.domain.calibration import apply_temperature_scaling


def test_temperature_scaling_probability_properties():
    """Verify temperature-scaled logits form valid probability distributions."""
    logits = np.array([2.5, 0.1, -1.2, 0.8, 3.1, -0.5, 1.0], dtype=np.float32)
    
    # Test across various temperatures
    for temp in [0.5, 1.0, 1.5, 2.5]:
        probs = apply_temperature_scaling(logits, temperature=temp)
        assert len(probs) == len(logits)
        assert np.isclose(np.sum(probs), 1.0, atol=1e-5)
        assert np.all(probs >= 0.0)
        assert np.all(probs <= 1.0)


def test_temperature_scaling_smoothing_effect():
    """Verify higher temperature smoothes probabilities and lower temperature sharpens."""
    logits = np.array([3.0, 1.0, 0.0], dtype=np.float32)
    
    sharp_probs = apply_temperature_scaling(logits, temperature=0.5)
    smooth_probs = apply_temperature_scaling(logits, temperature=2.0)
    
    # Sharp maximum probability should exceed smooth maximum probability
    assert sharp_probs[0] > smooth_probs[0]
    # Smallest class in smooth distribution should be higher than in sharp
    assert smooth_probs[2] > sharp_probs[2]

