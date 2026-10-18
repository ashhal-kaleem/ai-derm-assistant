"""ONNX Runtime Inference Engine with Dynamic HuggingFace Hub Streaming."""

import os
from typing import Optional, Tuple
import numpy as np
from PIL import Image

try:
    import onnxruntime as ort
except ImportError:
    ort = None

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    hf_hub_download = None

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess_image(image: Image.Image, target_size: Tuple[int, int] = (380, 380)) -> np.ndarray:
    """Preprocess PIL RGB image into standardized (1, 3, H, W) NCHW float32 tensor."""
    rgb_image = image.convert("RGB").resize(target_size, Image.Resampling.BILINEAR)
    np_img = np.array(rgb_image, dtype=np.float32) / 255.0
    norm_img = (np_img - IMAGENET_MEAN) / IMAGENET_STD
    chw_img = np.transpose(norm_img, (2, 0, 1))
    return np.expand_dims(chw_img, axis=0).astype(np.float32)


class ONNXInferenceEngine:
    """Ultra-fast CPU inference runner using ONNX Runtime with sub-250ms target."""

    def __init__(self, model_path: Optional[str] = None, hf_repo_id: Optional[str] = None):
        self.session = None
        self.input_name = "input"
        self.output_name = "output"
        self.model_path = model_path
        self._initialize_session(model_path, hf_repo_id)

    def _initialize_session(self, model_path: Optional[str], hf_repo_id: Optional[str]) -> None:
        """Initialize ONNX session from local file, alt path, or HuggingFace Hub."""
        # 1. Try caller-supplied path
        resolved_path: Optional[str] = model_path if model_path and os.path.exists(model_path) else None

        # 2. Try sibling checkpoints/ path relative to this file
        if resolved_path is None:
            alt_path = os.path.join(os.path.dirname(__file__), "..", "..", "checkpoints", "efficientnet_b4_ham10000.onnx")
            alt_path = os.path.normpath(alt_path)
            if os.path.exists(alt_path):
                resolved_path = alt_path

        # 3. Fall back to default relative path (works when CWD is backend/)
        if resolved_path is None:
            default_path = "checkpoints/efficientnet_b4_ham10000.onnx"
            if os.path.exists(default_path):
                resolved_path = default_path

        # 4. Stream from HuggingFace Hub as last resort
        if resolved_path is None and hf_repo_id and hf_hub_download is not None:
            try:
                resolved_path = hf_hub_download(
                    repo_id=hf_repo_id,
                    filename="efficientnet_b4_ham10000.onnx"
                )
            except Exception:
                resolved_path = None

        if resolved_path and os.path.exists(resolved_path) and ort is not None:
            self.model_path = resolved_path
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 2
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            # Return memory to the OS after each run instead of keeping a growing arena (fits Render's 512 MB)
            sess_options.enable_cpu_mem_arena = False
            self.session = ort.InferenceSession(
                resolved_path,
                sess_options=sess_options,
                providers=["CPUExecutionProvider"]
            )
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name

    def run_inference(self, image: Image.Image) -> Tuple[np.ndarray, np.ndarray]:
        """Execute forward pass and return (raw_logits, activation_map).

        Returns:
            Tuple containing:
                - raw_logits: Array of shape (7,)
                - activation_map: 2D occlusion-saliency map of shape (GRID, GRID)
        """
        if self.session is None:
            raise RuntimeError("Production ONNX session not loaded. Ensure checkpoints/efficientnet_b4_ham10000.onnx exists.")

        tensor = preprocess_image(image)
        baseline_outputs = self.session.run(None, {self.input_name: tensor})
        logits = baseline_outputs[0][0]

        # Softmax of baseline
        exp_logits = np.exp(logits - np.max(logits))
        baseline_probs = exp_logits / np.sum(exp_logits)
        top_class_idx = int(np.argmax(baseline_probs))

        # Occlusion sensitivity: 6x6 grid of non-overlapping patches
        # Each patch replaced with ImageNet mean; confidence drop = saliency
        GRID = 6
        h, w = tensor.shape[2], tensor.shape[3]
        ph, pw = h // GRID, w // GRID
        saliency = np.zeros((GRID, GRID), dtype=np.float32)

        for row in range(GRID):
            for col in range(GRID):
                occluded = tensor.copy()
                r0, r1 = row * ph, (row + 1) * ph
                c0, c1 = col * pw, (col + 1) * pw
                # Replace patch with ImageNet channel means (already normalized space: mean=0)
                occluded[0, :, r0:r1, c0:c1] = 0.0
                occ_out = self.session.run(None, {self.input_name: occluded})
                occ_exp = np.exp(occ_out[0][0] - np.max(occ_out[0][0]))
                occ_probs = occ_exp / np.sum(occ_exp)
                # Saliency = how much confidence dropped when this patch was hidden
                saliency[row, col] = float(baseline_probs[top_class_idx] - occ_probs[top_class_idx])

        return logits, saliency
