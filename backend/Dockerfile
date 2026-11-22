FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Runtime libraries for ONNX Runtime and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# The v3 .onnx files are Git LFS objects: fail the build if only LFS pointers were copied.
RUN python -c "import pathlib,sys; bad=[p.name for p in pathlib.Path('checkpoints/v3').glob('*.onnx') if p.stat().st_size < 1_000_000]; sys.exit('LFS pointer files, run git lfs pull: %s' % bad if bad else 0)"

# Run as an unprivileged user
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD sh -c 'python -c "import sys,urllib.request; urllib.request.urlopen(\"http://127.0.0.1:\" + sys.argv[1] + \"/health\", timeout=8)" "$PORT"' || exit 1

# Render and most hosts pass $PORT; default 8000 locally
CMD ["sh", "-c", "exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
