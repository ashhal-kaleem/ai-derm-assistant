"""Temperature-scaled softmax used at inference (T is fitted offline, see training/v3)."""

import numpy as np


def softmax(logits: np.ndarray) -> np.ndarray:
    """Compute numerically stable softmax across the last dimension."""
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp_vals = np.exp(shifted)
    return exp_vals / np.sum(exp_vals, axis=-1, keepdims=True)


def apply_temperature_scaling(logits: np.ndarray, temperature: float) -> np.ndarray:
    """Scale raw model logits by temperature T and compute calibrated probabilities."""
    T = max(0.01, float(temperature))
    scaled_logits = logits / T
    return softmax(scaled_logits)
