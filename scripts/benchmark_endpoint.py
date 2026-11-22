"""Latency + peak-RAM benchmark for the v3 ensemble: engine-level and end-to-end /predict."""
import io
import os
import resource
import sys
import time

import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from src.api.dependencies import get_inference_service  # noqa: E402
from src.api.main import app  # noqa: E402

META = {"age": 50, "sex": "male", "anatomical_site": "back"}


def peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def stats(name, xs):
    print(f"{name} (ms): median={np.median(xs):.0f} p95={np.percentile(xs, 95):.0f} min={np.min(xs):.0f}")


def run_benchmark(runs: int = 5):
    service = get_inference_service()
    print(f"engine={type(service.engine).__name__} model={service.engine.model_version} peak RAM after load={peak_mb():.0f} MB")
    img = Image.new("RGB", (600, 450), color=(180, 110, 80))
    service.predict(img, META)  # warm-up

    t_model, t_full = [], []
    for _ in range(runs):
        t0 = time.perf_counter()
        service.engine.ensemble_logits(img, META)
        t_model.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        service.predict(img, META)
        t_full.append((time.perf_counter() - t0) * 1000)

    client = TestClient(app)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    t_api, status = [], None
    for _ in range(runs):
        t0 = time.perf_counter()
        r = client.post(
            "/predict?generate_summary=false&save_to_cloud=false",
            files={"file": ("lesion.jpg", io.BytesIO(buf.getvalue()), "image/jpeg")},
        )
        t_api.append((time.perf_counter() - t0) * 1000)
        status = r.status_code

    print("=== BENCHMARK (v3 ensemble) ===")
    stats("ensemble logits only", t_model)
    stats("predict() incl. heatmap", t_full)
    stats("API /predict end-to-end", t_api)
    print(f"HTTP status: {status} | peak RAM: {peak_mb():.0f} MB")


if __name__ == "__main__":
    run_benchmark()
