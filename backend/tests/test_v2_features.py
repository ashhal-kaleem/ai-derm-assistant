import io
from PIL import Image
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_predict_prd_v2_contract():
    img = Image.new("RGB", (224, 224), color=(200, 120, 90))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"file": ("test_mole.jpg", buf, "image/jpeg")}
    response = client.post("/predict?generate_summary=true&save_to_cloud=false", files=files)

    assert response.status_code == 200
    data = response.json()

    # PRD v2.0 Canonical Contract Verification
    assert "predicted_class" in data
    assert "class_name" in data
    assert "confidence" in data
    assert data["risk_level"] in ("green", "yellow", "red")
    assert data["risk_label"] in ("Benign", "Monitor", "See doctor urgently")
    assert isinstance(data["all_probs"], list)
    assert len(data["all_probs"]) == 7
    assert data["uncertainty"] in ("low", "medium", "high")
    assert data["heatmap_b64"] is not None
    assert "data:image/png;base64," in data["heatmap_b64"]
    assert data["llm_explanation"] is not None


def test_pdf_report_endpoint():
    payload = {
        "prediction": {
            "predicted_class": "mel",
            "class_name": "Melanoma",
            "confidence": 0.843,
            "risk_level": "red",
            "risk_label": "See doctor urgently",
            "uncertainty": "low",
            "llm_explanation": "Melanoma detected. Immediate in-person dermatologist evaluation recommended."
        },
        "history": [
            {
                "date": "2026-09-01T10:00:00Z",
                "class_name": "Melanoma",
                "confidence": 0.81,
                "risk_level": "red"
            }
        ]
    }
    response = client.post("/report", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "pdf_b64" in data
    assert len(data["pdf_b64"]) > 1000


def test_longitudinal_lesion_history():
    payload = {
        "lesion_name": "Back Shoulder Mole",
        "prediction": {
            "predicted_class": "nv",
            "class_name": "Melanocytic Nevus",
            "confidence": 0.94,
            "risk_level": "green",
            "risk_label": "Benign"
        },
        "notes": "Routine annual checkup"
    }
    create_res = client.post("/history", json=payload)
    assert create_res.status_code == 200
    res_data = create_res.json()
    assert "visit_id" in res_data
    assert "lesion_id" in res_data
    lesion_id = res_data["lesion_id"]

    # Retrieve timeline
    get_res = client.get(f"/history/{lesion_id}")
    assert get_res.status_code == 200
    timeline = get_res.json()
    assert timeline["lesion_name"] == "Back Shoulder Mole"
    assert len(timeline["visits"]) >= 1
    assert timeline["visits"][0]["risk_level"] == "green"


def test_nearby_clinics_endpoint():
    response = client.get("/clinics?lat=31.5204&lon=74.3587")
    assert response.status_code == 200
    data = response.json()
    assert "clinics" in data
    # Overpass API may return 0 results in CI/offline — only validate structure
    if len(data["clinics"]) > 0:
        assert "directions_url" in data["clinics"][0]
        assert "name" in data["clinics"][0]
        assert "distance_km" in data["clinics"][0]
