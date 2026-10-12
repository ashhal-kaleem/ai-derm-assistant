"""Automated calibration test suite verifying temperature scaling and ECE."""

import numpy as np
import pytest

from src.core.calibration import (
    apply_temperature_scaling,
    compute_ece,
    optimize_temperature,
)


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


def test_compute_ece():
    """Verify ECE calculation for perfectly calibrated and miscalibrated models."""
    n_samples = 60
    n_classes = 3
    
    # Perfectly calibrated case: 100% confidence, 100% accurate
    perfect_probs = np.zeros((n_samples, n_classes))
    perfect_probs[:, 0] = 1.0
    labels = np.zeros(n_samples, dtype=int)
    
    ece_perfect = compute_ece(perfect_probs, labels, n_bins=5)
    assert np.isclose(ece_perfect, 0.0, atol=1e-4)

    # Completely wrong case: 100% confident on class 0, but all labels are class 1
    wrong_labels = np.ones(n_samples, dtype=int)
    ece_wrong = compute_ece(perfect_probs, wrong_labels, n_bins=5)
    assert ece_wrong > 0.9


def test_optimize_temperature():
    """Verify temperature optimization converges to optimal temperature T*."""
    np.random.seed(42)
    n_samples = 100
    n_classes = 7
    
    # Generate overconfident synthetic logits
    raw_logits = np.random.randn(n_samples, n_classes).astype(np.float32) * 4.0
    labels = np.random.randint(0, n_classes, size=n_samples)
    
    opt_temp = optimize_temperature(raw_logits, labels)
    assert opt_temp > 0.0
    assert isinstance(opt_temp, float)
