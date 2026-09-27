"""Explainable AI (XAI) and Grad-CAM Saliency Engine for DermAssist AI."""

import io
from typing import Optional
import cv2
import numpy as np
from PIL import Image


def normalize_cam_map(cam: np.ndarray) -> np.ndarray:
    """Normalize 2D activation map to range [0.0, 1.0]."""
    cam = np.maximum(cam, 0)
    max_val = np.max(cam)
    if max_val > 1e-7:
        cam = cam / max_val
    else:
        cam = np.zeros_like(cam)
    return cam


def generate_gradcam_overlay(
    image_rgb: np.ndarray,
    cam_2d: np.ndarray,
    alpha: float = 0.45,
    colormap: int = cv2.COLORMAP_JET
) -> np.ndarray:
    """Overlay a 2D saliency heatmap onto an RGB image using OpenCV.
    
    Args:
        image_rgb: Source image array of shape (H, W, 3) with values in [0, 255].
        cam_2d: 2D activation/saliency map of shape (h, w).
        alpha: Blending weight for heatmap overlay (0.0 to 1.0).
        colormap: OpenCV colormap constant (default: COLORMAP_JET).
        
    Returns:
        Blended RGB uint8 image array of shape (H, W, 3).
    """
    h, w = image_rgb.shape[:2]
    norm_cam = normalize_cam_map(cam_2d)
    
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


def generate_synthetic_saliency(image_rgb: np.ndarray, center_focus: float = 0.6) -> np.ndarray:
    """Generate a gaussian-weighted morphological saliency map for testing/fallback.
    
    Uses radial distance and local gradient intensity to highlight suspicious lesion centers.
    """
    h, w = image_rgb.shape[:2]
    y_coords, x_coords = np.ogrid[:h, :w]
    center_y, center_x = h / 2.0, w / 2.0
    
    # Radial Gaussian Falloff centered on lesion
    sigma = min(h, w) * center_focus * 0.4
    dist_sq = (x_coords - center_x) ** 2 + (y_coords - center_y) ** 2
    gaussian = np.exp(-dist_sq / (2 * (sigma ** 2)))
    
    # Morphological gradient contrast
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(grad_x ** 2 + grad_y ** 2)
    grad_norm = grad_mag / (np.max(grad_mag) + 1e-6)
    
    combined = 0.7 * gaussian + 0.3 * grad_norm
    return normalize_cam_map(combined)


def image_to_png_bytes(image_np: np.ndarray) -> bytes:
    """Encode an RGB uint8 image array to PNG byte stream."""
    pil_img = Image.fromarray(image_np)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()
