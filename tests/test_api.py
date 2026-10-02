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
    response = client.post("/api/v1/predict?generate_summary=false&save_to_cloud=false", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "top_class" in data
    assert "top_name" in data
    assert "calibrated_confidence" in data
    assert "probabilities" in data
    assert len(data["probabilities"]) == 7
    assert data["saliency_heatmap_base64"] is not None


def test_predict_endpoint_invalid_file_type():
    buf = io.BytesIO(b"Not an image")
    files = {"file": ("document.pdf", buf, "application/pdf")}
    response = client.post("/api/v1/predict", files=files)
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
    response = client.post("/api/v1/clinical-summary", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "clinical_summary" in data
    assert len(data["clinical_summary"]) > 0


def test_history_endpoint():
    response = client.get("/api/v1/history?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
