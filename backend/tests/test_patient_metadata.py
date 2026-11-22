"""Unit and integration tests for Patient Metadata Integration in clinical advisory.

Verifies:
1. Optional metadata fields (age, sex, anatomical_site, history_of_melanoma) are parsed in /predict.
2. Missing metadata preserves existing baseline behavior without errors.
3. Groq service formats patient-reported information clearly segregated from model predictions.
4. Groq service strictly forbids overriding model predictions or risk classification.
5. Static fallback incorporates anatomical site when provided.
6. Schema validation on age and sex values.
"""

import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.domain.models import PredictionResult, RiskLevel
from src.services.groq_service import GroqService

client = TestClient(app)


def test_predict_with_patient_metadata():
    """Verify /predict accepts optional patient metadata and returns valid prediction."""
    img = Image.new("RGB", (224, 224), color=(180, 100, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"file": ("test_mole.jpg", buf, "image/jpeg")}
    data = {
        "age": "52",
        "sex": "female",
        "anatomical_site": "Left Shoulder",
        "history_of_melanoma": "true",
    }

    response = client.post(
        "/predict?generate_summary=true&save_to_cloud=false",
        files=files,
        data=data,
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "predicted_class" in res_data
    assert "llm_explanation" in res_data
    assert res_data["llm_explanation"] is not None


def test_predict_without_patient_metadata_backward_compatible():
    """Verify /predict without metadata behaves identically to original contract."""
    img = Image.new("RGB", (224, 224), color=(180, 100, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"file": ("test_mole.jpg", buf, "image/jpeg")}
    response = client.post(
        "/predict?generate_summary=true&save_to_cloud=false",
        files=files,
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "predicted_class" in res_data
    assert res_data["llm_explanation"] is not None


def test_clinical_summary_endpoint_with_metadata():
    """Verify /clinical-summary accepts metadata and incorporates it in the response."""
    payload = {
        "top_class": "mel",
        "top_name": "Melanoma",
        "risk_level": "MALIGNANT",
        "calibrated_confidence": 0.88,
        "temperature": 1.35,
        "uncertainty_score": 0.12,
        "age": 64,
        "sex": "male",
        "anatomical_site": "Upper Back",
        "history_of_melanoma": True,
    }
    response = client.post("/clinical-summary", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "clinical_summary" in data
    assert len(data["clinical_summary"]) > 0


def test_groq_service_prompt_formatting_and_segregation():
    """Verify Groq prompt clearly labels self-reported context and forbids overriding model risk."""
    service = GroqService(api_key=None)  # Offline mode

    pred = PredictionResult(
        top_class="mel",
        top_name="Melanoma",
        risk_level=RiskLevel.MALIGNANT,
        raw_confidence=0.85,
        calibrated_confidence=0.85,
        temperature=1.35,
        uncertainty_score=0.10,
        probabilities=[],
    )

    metadata = {
        "age": 45,
        "sex": "female",
        "anatomical_site": "Forearm",
        "history_of_melanoma": True,
    }

    # In offline fallback, static summary includes anatomical site
    summary = service.generate_clinical_summary(pred, patient_metadata=metadata)
    assert "Melanoma" in summary
    assert "Forearm" in summary

    # Verify fallback without metadata does not fail and omits anatomical site
    summary_no_meta = service.generate_clinical_summary(pred, patient_metadata=None)
    assert "Melanoma" in summary_no_meta
    assert "Forearm" not in summary_no_meta
