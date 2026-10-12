"""Automated tests for GroqService and HistoryService."""

from PIL import Image
import numpy as np
import pytest

from src.domain.models import DiagnosisMetadata, PredictionResult, RiskLevel, ScanRecord
from src.services.groq_service import GroqService
from src.services.history_service import HistoryService


def test_groq_service_static_fallback():
    """Verify GroqService produces structured clinical card when API key is missing."""
    service = GroqService(api_key=None)
    pred = PredictionResult(
        top_class="mel",
        top_name="Melanoma",
        risk_level=RiskLevel.MALIGNANT,
        raw_confidence=0.88,
        calibrated_confidence=0.82,
        temperature=1.25,
        uncertainty_score=0.18,
        probabilities=[]
    )
    summary = service.generate_clinical_summary(pred)
    assert "Melanoma" in summary
    assert "MALIGNANT" in summary
    assert "82.0%" in summary
    assert "CRITICAL" in summary or "Clinical Understanding" in summary


def test_history_service_offline_fallback():
    """Verify HistoryService safely records scans and retrieves them in fallback mode."""
    service = HistoryService()
    pred = PredictionResult(
        top_class="nv",
        top_name="Melanocytic Nevi",
        risk_level=RiskLevel.BENIGN,
        raw_confidence=0.92,
        calibrated_confidence=0.90,
        temperature=1.25,
        uncertainty_score=0.08,
        probabilities=[]
    )
    
    img_bytes = b"fake_jpeg_image_content"
    heatmap_bytes = b"fake_heatmap_png_content"
    
    record = service.record_scan(pred, img_bytes, heatmap_bytes)
    assert record.id is not None
    assert record.predicted_class == "nv"
    assert record.risk_level == "BENIGN"
    assert "scans" in record.image_url
    assert "scans" in record.heatmap_url
    
    recent = service.get_recent_scans(limit=5)
    assert len(recent) >= 1
    assert recent[0].predicted_class == "nv"
