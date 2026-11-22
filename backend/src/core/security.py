"""Security utilities for DermAssist AI.

Provides:
1. Admin credential verification (constant-time).
2. Image file payload validation (size capping & magic bytes verification).
"""

import hmac
from typing import Optional, Tuple
from PIL import Image

# 4 MB maximum upload size: fits Vercel's 4.5 MB request body limit and guards memory
MAX_IMAGE_FILE_SIZE = 4 * 1024 * 1024

# Pillow Decompression Bomb protection cap
Image.MAX_IMAGE_PIXELS = 25_000_000

# Permitted dermatoscopic image formats
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def verify_admin_key(provided_key: Optional[str], expected_key: Optional[str]) -> bool:
    """Verify admin secret key using constant-time comparison to prevent timing attacks."""
    if not provided_key or not expected_key:
        return False
    return hmac.compare_digest(provided_key.encode("utf-8"), expected_key.encode("utf-8"))


def validate_image_payload(file_bytes: bytes, max_bytes: int = MAX_IMAGE_FILE_SIZE) -> Tuple[bool, Optional[str]]:
    """Validate image payload size and magic bytes against permitted image types."""
    if not file_bytes:
        return False, "Empty file uploaded."
    
    if len(file_bytes) > max_bytes:
        return False, f"File size ({len(file_bytes)} bytes) exceeds the maximum allowed limit ({max_bytes} bytes)."

    # Magic byte checks:
    # JPEG: FF D8 FF
    # PNG:  89 50 4E 47 0D 0A 1A 0A
    # WEBP: 52 49 46 46 (RIFF) ... 57 45 42 50 (WEBP)
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return True, None
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return True, None
    if file_bytes.startswith(b"RIFF") and len(file_bytes) > 12 and file_bytes[8:12] == b"WEBP":
        return True, None

    return False, "File content does not match allowed image formats (JPEG, PNG, WEBP)."
