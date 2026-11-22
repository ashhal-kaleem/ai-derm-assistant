import io
from PIL import Image
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "onnx_model_loaded" in data
    assert "groq_configured" in data


def test_predict_endpoint_valid_image():
    # Create synthetic test image
    img = Image.new("RGB", (224, 224), color=(180, 100, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"file": ("test_lesion.jpg", buf, "image/jpeg")}
    response = client.post("/predict?generate_summary=false&save_to_cloud=false", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "predicted_class" in data
    assert "class_name" in data
    assert "confidence" in data
    assert len(data["probabilities"]) == 7
    assert len(data["all_probs"]) == 7
    assert data["heatmap_b64"].startswith("data:image/png;base64,")
    for legacy in ("top_class", "saliency_heatmap_base64", "calibrated_confidence"):
        assert legacy not in data


def test_predict_endpoint_invalid_file_type():
    buf = io.BytesIO(b"Not an image")
    files = {"file": ("document.pdf", buf, "application/pdf")}
    response = client.post("/predict", files=files)
    assert response.status_code == 400


def test_clinical_summary_endpoint():
    payload = {
        "top_class": "mel",
        "top_name": "Melanoma",
        "risk_level": "MALIGNANT",
        "calibrated_confidence": 0.85,
        "temperature": 1.2,
        "uncertainty_score": 0.15,
    }
    response = client.post("/clinical-summary", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "clinical_summary" in data
    assert len(data["clinical_summary"]) > 0


def test_history_endpoint():
    response = client.get("/history?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_legacy_api_v1_routes_removed():
    assert client.post("/api/v1/predict").status_code == 404
