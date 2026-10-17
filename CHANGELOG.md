# Changelog — DermAssist AI

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.2] - 2026-10-16

### Fixed
- `routes.py`: `save_scan()` call replaced with correct `record_scan()` — method name, parameter names, and parameter type were all mismatched; every cloud save was silently failing via bare `except: pass`. Added proper `logger.warning()` on failure.
- `routes.py`: Removed unused `ScanRecord` import; added `logging` import.
- `history_service.py`: `lesion_id` generation replaced `hash()` (non-deterministic across restarts in Python 3.3+) with `hashlib.sha256` — same lesion name now always maps to the same ID.
- `onnx_engine.py`: Fixed HuggingFace fallback — `resolved_path` was always truthy so the `if not resolved_path` guard never triggered. Rewritten as explicit 4-step resolution chain (caller path → alt path → default relative path → HF download).
- `models.py`: `vasc` (Vascular Lesions) moved from `yellow/Monitor` to `green/Benign` in `map_risk_tier()` — consistent with its `RiskLevel.BENIGN` catalog entry.
- `main.py`: FastAPI version bumped from `"1.0.0"` to `"2.0.1"` to match `api_root()` manifest.
- `schemas.py`: `ClinicalSummaryResponse.model` changed from hardcoded `"llama-3.3-70b-versatile"` to `Optional[str] = None`; actual model used is now returned from route.

## [2.0.1] - 2026-10-16

### Fixed
- `groq_service.py`: Replaced invalid model IDs (`qwen/qwen3.8-27b`, `openai/gpt-oss-120b`) with valid Groq model IDs (`llama-3.1-8b-instant`, `gemma2-9b-it`) in fallback chain.
- `groq_service.py`: Primary model now uses `self.model` (injected from `GROQ_MODEL` config) instead of hardcoded string; `DEFAULT_KEY` sentinel replaced with `Optional[str] = None`.
- `config.py`: `INPUT_SIZE` corrected from `224` to `380` to match EfficientNet-B4 native resolution used in `onnx_engine.py`.
- `inference_service.py`: Default temperature corrected from `1.25` to `1.0` to match `DEFAULT_TEMPERATURE` in config.
- `dependencies.py`: `get_groq_service()` now injects `GROQ_MODEL` setting into `GroqService`.
- `routes.py`: `/api/v1/clinical-summary` endpoint converted to use `Depends(get_groq_service)` for consistent dependency injection; removed duplicate inline `get_groq_service()` call.

## [Unreleased]

### Added
- Phase 0: Complete 6-Sphere Research Dossier covering HAM10000 benchmarks, patient-aware splitting, temperature scaling, and ONNX deployment.
- Phase 1 & 2: Architectural blueprint with decoupled layers, Pragmatic Balance topology, and 100% Stateless Cloud-First Supabase persistence (Database & Storage).
- Phase 3: Formal documentation SSOT scaffolding (`docs/PRD.md`, `docs/architecture.md`, `AGENTS.md`, `CONTEXT.md`).
- Phase 4: Production EfficientNet-B4 ONNX serving with Grad-CAM saliency heatmaps.
- Replaced Google Gemini with Groq LPU (llama-3.3-70b-versatile) for sub-250ms patient clinical advisory generation.
- Added comprehensive unit tests and automated fallback to static medical cards.
