"""Preprocessing for the DermAssist v3 ensemble.

Must stay byte-for-byte equivalent to the Kaggle training pipeline
(work/kaggle/v3/dermassist-teachers-v3.py): resize to 448 (bicubic),
shades-of-gray colour constancy (p=6), resize to the member input size
(bilinear), ImageNet normalisation, plus a 19-dim metadata vector.
"""

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from PIL import Image

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Free-text anatomical site (as typed in the app) -> HAM10000 localization.
# Checked in order; first keyword match wins. Anything else maps to "unknown".
_SITE_KEYWORDS = [
    ("scalp", "scalp"), ("ear", "ear"), ("face", "face"), ("cheek", "face"), ("nose", "face"),
    ("forehead", "face"), ("lip", "face"), ("chin", "face"), ("eyelid", "face"),
    ("neck", "neck"), ("chest", "chest"), ("breast", "chest"), ("abdomen", "abdomen"),
    ("belly", "abdomen"), ("stomach", "abdomen"), ("back", "back"), ("trunk", "trunk"),
    ("torso", "trunk"), ("genital", "genital"), ("groin", "genital"),
    ("palm", "acral"), ("sole", "acral"), ("acral", "acral"), ("nail", "acral"),
    ("hand", "hand"), ("finger", "hand"), ("wrist", "hand"),
    ("foot", "foot"), ("feet", "foot"), ("toe", "foot"), ("ankle", "foot"),
    ("upper extremity", "upper extremity"), ("arm", "upper extremity"), ("shoulder", "upper extremity"),
    ("elbow", "upper extremity"),
    ("lower extremity", "lower extremity"), ("leg", "lower extremity"), ("thigh", "lower extremity"),
    ("knee", "lower extremity"), ("calf", "lower extremity"), ("shin", "lower extremity"),
]


def shades_of_gray(arr: np.ndarray, power: int = 6) -> np.ndarray:
    a = arr.astype(np.float32)
    ill = np.power(np.mean(np.power(a, power), axis=(0, 1)), 1.0 / power)
    ill = ill / (np.sqrt((ill ** 2).sum()) + 1e-6)
    return np.clip(a / (ill * np.sqrt(3.0) + 1e-6), 0, 255).astype(np.uint8)


def base_image(image: Image.Image, pre_size: int = 448, power: int = 6) -> np.ndarray:
    """RGB -> pre_size x pre_size (bicubic) -> shades-of-gray, uint8 HxWx3."""
    rgb = image.convert("RGB").resize((pre_size, pre_size), Image.BICUBIC)
    return shades_of_gray(np.asarray(rgb, dtype=np.uint8), power)


def to_tensor(base: np.ndarray, size: int) -> np.ndarray:
    """uint8 base image -> (1, 3, size, size) normalised float32."""
    a = np.asarray(Image.fromarray(base).resize((size, size), Image.BILINEAR), dtype=np.float32) / 255.0
    return ((a - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1)[None].astype(np.float32)


def tta_batch(tensor: np.ndarray, views: Sequence[str]) -> np.ndarray:
    """Stack the requested test-time views of a (1,3,H,W) tensor into (V,3,H,W)."""
    ops = {
        "identity": lambda x: x,
        "hflip": lambda x: x[..., ::-1],
        "vflip": lambda x: x[..., ::-1, :],
        "transpose": lambda x: x.transpose(0, 1, 3, 2),
    }
    return np.ascontiguousarray(np.concatenate([ops[v](tensor) for v in views], axis=0))


def map_site(site: Optional[str], localizations: List[str]) -> str:
    if not site or not isinstance(site, str):
        return "unknown"
    s = site.strip().lower()
    if s in localizations:
        return s
    for key, loc in _SITE_KEYWORDS:
        if key in s and loc in localizations:
            return loc
    return "unknown"


def meta_vector(metadata: Optional[Dict[str, Any]], schema: Dict[str, Any]) -> np.ndarray:
    """(1, meta_dim) float32: [age/90, age_missing, male, female, one-hot localization]."""
    md = metadata or {}
    locs = schema["localizations"]
    age = md.get("age")
    try:
        age = float(age) if age is not None else -1.0
    except (TypeError, ValueError):
        age = -1.0
    if not np.isfinite(age) or age <= 0:
        age = -1.0
    vec = [0.0 if age < 0 else age / float(schema.get("age_scale", 90.0)), 1.0 if age < 0 else 0.0]
    sex = str(md.get("sex") or "").strip().lower()
    vec += [float(sex == s) for s in schema.get("sex", ["male", "female"])]
    loc = map_site(md.get("anatomical_site"), locs)
    vec += [float(loc == l) for l in locs]
    out = np.asarray([vec], dtype=np.float32)
    assert out.shape[1] == schema["meta_dim"], (out.shape, schema["meta_dim"])
    return out
