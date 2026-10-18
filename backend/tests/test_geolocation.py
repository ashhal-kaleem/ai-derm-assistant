from src.services.geolocation_service import ClinicSearchError, GeolocationService


def _fake(elements):
    svc = GeolocationService()
    svc._query = lambda q: {"elements": elements}
    return svc


def test_dermatology_first_then_nearest():
    els = [
        {"type": "node", "lat": 31.521, "lon": 74.359, "tags": {"amenity": "hospital", "name": "Near Hospital"}},
        {"type": "way", "center": {"lat": 31.60, "lon": 74.40}, "tags": {"amenity": "clinic", "name": "Far Skin Clinic"}},
        {"type": "node", "lat": 31.55, "lon": 74.36, "tags": {"healthcare": "doctor", "healthcare:speciality": "dermatology", "name": "Dr Derm"}},
        {"type": "node", "lat": 31.53, "lon": 74.36, "tags": {"amenity": "clinic"}},  # unnamed -> dropped
    ]
    out = _fake(els).search_clinics(31.5204, 74.3587, 10)
    assert [c["name"] for c in out] == ["Dr Derm", "Far Skin Clinic", "Near Hospital"]
    assert out[0]["is_dermatology"] and not out[2]["is_dermatology"]
    assert "destination=31.55,74.36" in out[0]["directions_url"]


def test_unavailable_returns_status(monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.api import dependencies

    def boom(self, *a, **k):
        raise ClinicSearchError("down")

    monkeypatch.setattr(GeolocationService, "search_clinics", boom)
    with TestClient(app) as c:
        r = c.get("/clinics?lat=31.52&lon=74.35")
    assert r.status_code == 200
    assert r.json()["status"] == "unavailable"
    assert r.json()["clinics"] == []
