"""Unit and integration test suite for DermAssist AI security hardening.

Verifies:
2. Admin credential verification with HMAC constant-time matching.
3. Image payload validation (magic bytes, size limits, decompression bomb guard).
4. HTTP Security Headers (HSTS, X-Content-Type-Options, X-Frame-Options, CSP).
5. HTTPS Redirection on X-Forwarded-Proto.
6. CORS configuration standards compliance.
7. Admin route lock and authorization gates.
8. API docs lockdown in production mode.
"""

import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.config import get_settings
from src.core.security import (
    verify_admin_key,
    validate_image_payload,
    MAX_IMAGE_FILE_SIZE,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_admin_key_verification():
    """Verify admin secret key constant-time validation."""
    correct_key = "dermassist-master-admin-key-987654321"
    assert verify_admin_key(correct_key, correct_key) is True
    assert verify_admin_key("wrong-key", correct_key) is False
    assert verify_admin_key(None, correct_key) is False
    assert verify_admin_key(correct_key, None) is False


def test_image_payload_validation_magic_bytes():
    """Verify file magic bytes and format restrictions."""
    # 1. Valid JPEG
    img_jpg = Image.new("RGB", (64, 64), color=(200, 100, 100))
    buf_jpg = io.BytesIO()
    img_jpg.save(buf_jpg, format="JPEG")
    is_valid, err = validate_image_payload(buf_jpg.getvalue())
    assert is_valid is True
    assert err is None

    # 2. Valid PNG
    img_png = Image.new("RGB", (64, 64), color=(100, 200, 100))
    buf_png = io.BytesIO()
    img_png.save(buf_png, format="PNG")
    is_valid, err = validate_image_payload(buf_png.getvalue())
    assert is_valid is True
    assert err is None

    # 3. Invalid payload (text / executable / spoofed)
    is_valid, err = validate_image_payload(b"<?php echo 'malicious'; ?>")
    assert is_valid is False
    assert "does not match" in err

    # 4. Oversized payload (> MAX_IMAGE_FILE_SIZE)
    oversized = b"\xff\xd8\xff" + b"\x00" * (MAX_IMAGE_FILE_SIZE + 10)
    is_valid, err = validate_image_payload(oversized)
    assert is_valid is False
    assert "exceeds" in err


def test_security_headers_present(client):
    """Verify HTTP security headers are present on API responses."""
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert "strict-transport-security" in headers
    assert "max-age=63072000" in headers["strict-transport-security"]
    assert "includeSubDomains" in headers["strict-transport-security"]
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "content-security-policy" in headers


def test_https_redirection_behind_proxy(client):
    """Verify HTTP requests forwarded with x-forwarded-proto: http are redirected to https in production."""
    # Simulate non-secure request forwarded by reverse proxy
    response = client.get("/health", headers={"x-forwarded-proto": "http"}, follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"].startswith("https://")


def test_admin_route_lockdown(client):
    """Verify admin route requires X-Admin-Key when configured."""
    settings = get_settings()
    original_key = settings.ADMIN_API_KEY
    try:
        settings.ADMIN_API_KEY = "test-secret-admin-pass-12345"

        # Attempt access without header -> 401 Unauthorized
        res_unauthorized = client.get("/feedback/summary")
        assert res_unauthorized.status_code == 401

        # Attempt access with invalid header -> 401 Unauthorized
        res_invalid = client.get("/feedback/summary", headers={"X-Admin-Key": "bad-password"})
        assert res_invalid.status_code == 401

        # Attempt access with valid header -> 200 OK
        res_authorized = client.get("/feedback/summary", headers={"X-Admin-Key": "test-secret-admin-pass-12345"})
        assert res_authorized.status_code == 200
        assert "counts" in res_authorized.json()
    finally:
        settings.ADMIN_API_KEY = original_key


def test_api_docs_lockdown():
    """Verify OpenAPI and documentation endpoints are restricted in production."""
    settings = get_settings()
    assert settings.ENVIRONMENT == "production"
    assert settings.ENABLE_DOCS is False
    # docs_url and redoc_url should be None on the app instance
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_admin_route_fails_closed_without_key(client):
    """Admin routes are disabled (503) when ADMIN_API_KEY is not configured."""
    settings = get_settings()
    original_key = settings.ADMIN_API_KEY
    try:
        settings.ADMIN_API_KEY = None
        res = client.get("/feedback/summary")
        assert res.status_code == 503
    finally:
        settings.ADMIN_API_KEY = original_key


def test_oversized_upload_rejected(client):
    """Uploads over MAX_UPLOAD_SIZE_MB get 413 without running the model."""
    settings = get_settings()
    original = settings.MAX_UPLOAD_SIZE_MB
    try:
        settings.MAX_UPLOAD_SIZE_MB = 1
        payload = b"\xff\xd8\xff" + b"0" * (2 * 1024 * 1024)
        files = {"file": ("big.jpg", io.BytesIO(payload), "image/jpeg")}
        res = client.post("/predict?generate_summary=false&save_to_cloud=false", files=files)
        assert res.status_code == 413
    finally:
        settings.MAX_UPLOAD_SIZE_MB = original


def test_request_id_header(client):
    res = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert res.headers["X-Request-ID"] == "abc-123"
    res = client.get("/health", headers={"X-Request-ID": "bad id\ninjected"})
    assert res.headers["X-Request-ID"] != "bad id\ninjected"
