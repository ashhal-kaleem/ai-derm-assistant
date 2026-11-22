"""Explainable AI renderer for occlusion-sensitivity maps."""

import io
from typing import Optional
import cv2
cv2.setNumThreads(1)
import numpy as np
from PIL import Image


def normalize_saliency_map(saliency: np.ndarray) -> np.ndarray:
    """Normalize a 2D occlusion-sensitivity map to range [0.0, 1.0]."""
    saliency = np.maximum(saliency, 0)
    max_val = np.max(saliency)
    if max_val > 1e-7:
        saliency = saliency / max_val
    else:
        saliency = np.zeros_like(saliency)
    return saliency


def generate_occlusion_overlay(
    image_rgb: np.ndarray,
    saliency_2d: np.ndarray,
    alpha: float = 0.45,
    colormap: int = cv2.COLORMAP_JET
) -> np.ndarray:
    """Overlay a 2D occlusion-sensitivity map onto an RGB image using OpenCV.
    
    Args:
        image_rgb: Source image array of shape (H, W, 3) with values in [0, 255].
        saliency_2d: 2D occlusion-sensitivity map of shape (h, w).
        alpha: Blending weight for heatmap overlay (0.0 to 1.0).
        colormap: OpenCV colormap constant (default: COLORMAP_JET).
        
    Returns:
        Blended RGB uint8 image array of shape (H, W, 3).
    """
    h, w = image_rgb.shape[:2]
    norm_cam = normalize_saliency_map(saliency_2d)
    
    # Resize saliency map to full image resolution with bicubic interpolation
    resized_cam = cv2.resize(norm_cam, (w, h), interpolation=cv2.INTER_CUBIC)
    resized_cam = np.clip(resized_cam, 0.0, 1.0)
    
    # Convert to 8-bit grayscale for colormap application
    cam_uint8 = np.uint8(255 * resized_cam)
    heatmap_bgr = cv2.applyColorMap(cam_uint8, colormap)
    heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)
    
    # Alpha blend original image and heatmap
    image_float = image_rgb.astype(np.float32)
    heatmap_float = heatmap_rgb.astype(np.float32)
    blended = alpha * heatmap_float + (1.0 - alpha) * image_float
    return np.clip(blended, 0, 255).astype(np.uint8)



def image_to_png_bytes(image_np: np.ndarray) -> bytes:
    """Encode an RGB uint8 image array to PNG byte stream."""
    pil_img = Image.fromarray(image_np)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()
