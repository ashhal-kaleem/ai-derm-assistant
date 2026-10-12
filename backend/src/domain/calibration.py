"""Probability Calibration and Temperature Scaling Engine for DermAssist AI."""

from typing import Tuple
import numpy as np
from scipy.optimize import minimize_scalar


def softmax(logits: np.ndarray) -> np.ndarray:
    """Compute numerically stable softmax across the last dimension."""
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp_vals = np.exp(shifted)
    return exp_vals / np.sum(exp_vals, axis=-1, keepdims=True)


def apply_temperature_scaling(logits: np.ndarray, temperature: float = 1.35) -> np.ndarray:
    """Scale raw model logits by temperature T and compute calibrated probabilities."""
    T = max(0.01, float(temperature))
    scaled_logits = logits / T
    return softmax(scaled_logits)


def negative_log_likelihood(T: float, logits: np.ndarray, labels: np.ndarray) -> float:
    """Compute cross-entropy NLL loss for a given temperature scalar T."""
    probs = apply_temperature_scaling(logits, temperature=T)
    eps = 1e-12
    probs = np.clip(probs, eps, 1.0 - eps)
    n_samples = logits.shape[0]
    log_likelihood = -np.sum(np.log(probs[np.arange(n_samples), labels]))
    return float(log_likelihood / n_samples)


def optimize_temperature(logits: np.ndarray, labels: np.ndarray, bounds: Tuple[float, float] = (0.1, 10.0)) -> float:
    """Find the optimal temperature scalar T* that minimizes validation NLL loss."""
    res = minimize_scalar(
        lambda T: negative_log_likelihood(T, logits, labels),
        bounds=bounds,
        method="bounded"
    )
    return float(res.x)


def compute_ece(probabilities: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE) across confidence bins."""
    confidences = np.max(probabilities, axis=1)
    predictions = np.argmax(probabilities, axis=1)
    accuracies = predictions == labels

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n_samples = len(labels)

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        bin_size = np.sum(in_bin)

        if bin_size > 0:
            bin_acc = np.mean(accuracies[in_bin])
            bin_conf = np.mean(confidences[in_bin])
            ece += (bin_size / n_samples) * np.abs(bin_acc - bin_conf)

    return float(ece)
