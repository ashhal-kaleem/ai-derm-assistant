"""ONNX Runtime engine for the DermAssist v3 ensemble (ConvNeXt-V2-T, EfficientNetV2-S, EVA02-S).

Each member takes an image tensor and a 19-dim metadata vector. Ensemble logits
are log(mean softmax over members, each averaged over the TTA views), exactly as
in training. Calibration (temperature) and the melanoma threshold live in
model_v3.json and are applied by InferenceService.
"""

import hashlib
import json
import os
from typing import Any, Dict, Optional, Tuple

import numpy as np
from PIL import Image

from src.infrastructure.v3_preprocess import base_image, meta_vector, tta_batch, to_tensor

try:
    import onnxruntime as ort
except ImportError:  # pragma: no cover
    ort = None

DEFAULT_V3_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "checkpoints", "v3"))
CONFIG_NAME = "model_v3.json"


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


class V3EnsembleEngine:
    """Loads all v3 members and runs calibrated-ready ensemble inference on CPU."""

    def __init__(self, model_dir: Optional[str] = None, threads: int = 2):
        self.model_dir = model_dir or DEFAULT_V3_DIR
        self.sessions: Dict[str, Any] = {}
        self.session = None  # health-check compatibility: set when every member loaded
        self.config: Dict[str, Any] = {}
        self.calibration_temperature: Optional[float] = None
        self.mel_threshold: Optional[float] = None
        self.model_version = "unknown"
        self.head_version = "unknown"
        self._load(threads)

    def _load(self, threads: int) -> None:
        cfg_path = os.path.join(self.model_dir, CONFIG_NAME)
        if not os.path.exists(cfg_path) or ort is None:
            return
        with open(cfg_path, "rb") as fh:
            raw = fh.read()
        self.config = json.loads(raw)
        self.head_version = hashlib.sha256(raw).hexdigest()[:16]
        self.model_version = self.config.get("model_version", "dermassist-v3-ensemble")
        self.calibration_temperature = float(self.config["temperature"])
        self.mel_threshold = self.config.get("mel_threshold")

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.enable_cpu_mem_arena = False
        opts.enable_mem_pattern = False  # lower peak RAM (Render 512 MB)
        for member in self.config["members"]:
            path = os.path.join(self.model_dir, member["file"])
            if not os.path.exists(path):
                self.sessions = {}
                return
            self.sessions[member["name"]] = ort.InferenceSession(path, sess_options=opts, providers=["CPUExecutionProvider"])
        self.session = self.sessions  # truthy only when all members are loaded

    @property
    def loaded(self) -> bool:
        return bool(self.sessions) and len(self.sessions) == len(self.config.get("members", []))

    def _member_logits(self, name: str, image_batch: np.ndarray, meta: np.ndarray) -> np.ndarray:
        # One image per run: same logits as a batched run, but far lower peak RAM
        # (measured 626 MB -> 399 MB for the 3 members with 4 TTA views).
        session = self.sessions[name]
        out = [
            session.run(None, {"image": np.ascontiguousarray(image_batch[i:i + 1]), "meta": meta})[0]
            for i in range(image_batch.shape[0])
        ]
        return np.concatenate(out, axis=0)

    def ensemble_logits(self, image: Image.Image, metadata: Optional[Dict[str, Any]] = None) -> np.ndarray:
        if not self.loaded:
            raise RuntimeError("v3 ensemble not loaded. Ensure checkpoints/v3/ holds model_v3.json and all member .onnx files.")
        pp = self.config["preprocess"]
        base = base_image(image, pp.get("pre_resize", 448), pp.get("sog_power", 6))
        meta = meta_vector(metadata, self.config["meta_schema"])
        views = self.config.get("tta", ["identity"])
        probs = []
        for member in self.config["members"]:
            batch = tta_batch(to_tensor(base, member["input_size"]), views)
            logits = self._member_logits(member["name"], batch, meta).mean(axis=0)  # average logits over views
            probs.append(_softmax(logits))
        return np.log(np.clip(np.mean(probs, axis=0), 1e-8, 1.0)).astype(np.float32)

    def occlusion_map(self, image: Image.Image, metadata: Optional[Dict[str, Any]], target_idx: int) -> np.ndarray:
        """Occlusion sensitivity on one member, single view: confidence drop per hidden patch."""
        occ = self.config.get("occlusion", {})
        name = occ.get("member", self.config["members"][0]["name"])
        grid = int(occ.get("grid", 4))
        member = next(m for m in self.config["members"] if m["name"] == name)
        pp = self.config["preprocess"]
        tensor = to_tensor(base_image(image, pp.get("pre_resize", 448), pp.get("sog_power", 6)), member["input_size"])
        meta = meta_vector(metadata, self.config["meta_schema"])
        size = tensor.shape[2]
        ph = size // grid
        batch = [tensor[0]]
        for r in range(grid):
            for c in range(grid):
                t = tensor[0].copy()
                t[:, r * ph:(r + 1) * ph, c * ph:(c + 1) * ph] = 0.0  # ImageNet mean in normalised space
                batch.append(t)
        probs = _softmax(self._member_logits(name, np.ascontiguousarray(np.stack(batch)), meta))
        base_p = probs[0, target_idx]
        return (base_p - probs[1:, target_idx]).reshape(grid, grid).astype(np.float32)

    def run_inference(self, image: Image.Image, metadata: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Return (ensemble_logits (7,), occlusion map (grid, grid))."""
        logits = self.ensemble_logits(image, metadata)
        saliency = self.occlusion_map(image, metadata, int(np.argmax(logits)))
        return logits, saliency
