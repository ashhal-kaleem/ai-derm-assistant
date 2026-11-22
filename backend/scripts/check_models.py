"""Build guard: the v3 ONNX models must be real files, not Git LFS pointers."""
import pathlib
import sys

EXPECTED = ("convnextv2_tiny.onnx", "effnetv2_s.onnx", "eva02_small_int8.onnx")
root = pathlib.Path(__file__).resolve().parent.parent / "checkpoints" / "v3"
bad = [n for n in EXPECTED if not (root / n).is_file() or (root / n).stat().st_size < 1_000_000]
if bad:
    sys.exit(f"Model files missing or Git LFS pointers (enable Git LFS on the host): {bad}")
print("v3 model files OK")
