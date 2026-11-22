# CONTEXT.md — DermAssist AI

> **Living Workspace Memory & Execution Engine**  
> 1. Read this file FIRST at the start of every session to rehydrate state.  
> 2. Respect Active Task Scope: Modify ONLY targeted files for the current step.  
> 3. Never mark `[x]` without live verification (exit code 0).  
> 4. Keep this file lean (< 350 lines). Update as the FINAL step of every session.  

---

## 🧭 1. Project Snapshot & Runtime State
- **Core Purpose:** Calibrated, explainable, ultra-lightweight skin lesion diagnostic assistant with zero patient leakage and sub-250ms ONNX inference.
- **Current Honest State:** Phase 4 completed (Decoupled Vercel Frontend + Render Backend, 19 tests verified exit code 0).
- **Active Working Branch:** `Dev` (contributions go via fork + PR to `main`)
- **Local Dev Environment:**
  | Service | Host / Port | Status | Verification Command |
  |---|---|---|---|
  | FastAPI REST API | `localhost:8000` | Ready | `curl -sI http://localhost:8000/health` |
  | Cloud DB | Supabase (PostgreSQL) | Remote Cloud | `curl -sI $SUPABASE_URL` |
| Cloud Storage | Supabase (`scans` bucket) | Remote Cloud | Supabase Storage API |
- **Live Production URL:** Not yet deployed (Target: Render (Backend) & Vercel (Frontend))
- **Primary Specifications:**
  - Product Specs & PRD: [`docs/PRD.md`](docs/PRD.md)
  - Architecture & Blueprint: [`docs/architecture.md`](docs/architecture.md)
  - Developer Handbooks: [`AGENTS.md`](AGENTS.md)
  - Ratchet Invariants: [`decisions.log`](decisions.log)

---

## 🗣️ 2. Canonical Domain Vocabulary & Invariants
Canonical project nouns to eliminate semantic drift, schema naming bugs, and LLM synonyms:
- **Lesion**: Unique physical cutaneous anomaly identified by `lesion_id`.
- **Image**: Specific photographic record identified by `image_id` (a single lesion can have multiple images).
- **Diagnosis**: 7 canonical classes (`akiec`, `bcc`, `bkl`, `df`, `mel`, `nv`, `vasc`).
- **Temperature ($T^*$)**: Scalar parameter for probability calibration.
- **Occlusion map**: saliency heatmap from masking 4x4 image patches on the EfficientNetV2-S member.
- **v3 ensemble**: production model (ConvNeXt-V2-T, EfficientNetV2-S, EVA02-S) with metadata, T=0.5973, melanoma threshold 0.34.

---

## ⚡ 3. Session Handover & State Rehydration (Pick Up Here)
- **Session Timestamp:** 2026-10-12 14:41
- **Session Timestamp:** 2026-10-15 13:05
  - Supabase Cloud Project (dhdwcpatbsipfheuwolo) restored and verified ACTIVE_HEALTHY.
  - Created public.lesion_visits table with RLS policies in remote PostgreSQL.
  - Connected HistoryService to persist both scans and longitudinal lesion visits directly to cloud database.
  - Upgraded GeolocationService to live OpenStreetMap Nominatim search (genuine clinics, exact Haversine distance, zero dummy clinics).
  - Eliminated hardcoded Delhi fallback clinics from ClinicFinderScreen.jsx offline catch block.
  - Full backend test suite passing 100% (19/19 pytest tests, exit 0).
  - Integrated React Bits <TechText /> component into ScanScreen.jsx heading with interactive pointer physics, specks, and responsive scaling.
  - Updated /health endpoint with active database ping probe (real liveness).
  - All 19 pytest tests and 13 live local server end-to-end HTTP tests passing 100% (exit 0).
- **Verified Accomplishments (What Works):**
  - Real-time Geolocation Service configured via OpenStreetMap Overpass API - **Session Timestamp:** 2026-10-02 17:35 exact Haversine distance formula.
  - Resilient fallback implemented for high-load / rate-limiting conditions without 500 errors.
  - Clean API Gateway deployed and live test suite passes 100% (19/19 pytest tests passed exit code 0).
- **Verified Accomplishments (What Works):**
  - Phase 0 6-Sphere Research Dossier completed → Verified: `wc -l ~/agent-reach/Downloads/Research\ Engine/ai_dermatology_assistant_research_dossier.md` (216 lines, exit 0)
  - PRD and Architecture SSOT deployed → Verified: `docs/PRD.md` and `docs/architecture.md` exist and fully populated (exit 0)
  - AGENTS.md master handbook deployed → Verified: `AGENTS.md` exists (exit 0)
- **Recently Touched Files (Targeted Re-analysis):**
  - `docs/PRD.md` — Complete Product Requirements Document
  - `docs/architecture.md` — Complete System Blueprint & Schemas
  - `AGENTS.md` — Master Developer Handbook & Invariants
- **Active Blockers & Pending Decisions (Awaiting Human):**
  - None. Options 1 (ONNX Runtime) and 3 (Groq LPU (llama-3.3-70b-versatile)) approved by user.
- **Active Gotchas & Undocumented Quirks:**
  - Model training conducted offline on Kaggle T4 GPU; local application environment strictly runs `onnxruntime` on CPU.
- **Immediate Next Step & Scope Bounding:**
  - **Task:** Finalize Phase 3 initialization (`CHANGELOG.md`, `decisions.log`, `requirements.txt`).
  - **Target Files (In-Scope):** `CHANGELOG.md`, `decisions.log`, `requirements.txt`
  - **Prohibited Files (Do Not Touch):** `docs/*`, raw data files.

---

## 🔁 4. The Per-Change Atomic Loop

Every task follows a strict 4-step atomic verification cycle:
1. **Scope**: Identify and touch ONLY the target files listed in Section 3.
2. **Write**: Implement the smallest isolated increment of functionality.
3. **Verify Locally**: Run targeted terminal command (`pytest ...`, `curl ...`).
4. **Sync State**: Mark item `[x]` ONLY after exit code `0`, and update Handover & Touched Files above.

---

## 📋 5. Phased Build Roadmap & Verification Checklist

### Phase 1 — Foundations & External Dependency Verification
- [x] **1.1 Requirements & Python Environment** → verify: `pip check`
- [x] **1.2 Supabase Cloud Connection & Storage** → verify: `python3 -c "import supabase; print(supabase.__name__)"`
- [x] **1.3 Static Knowledge Cards JSON** → verify: `python3 -m json.tool app/knowledge_cards.json > /dev/null`

---

### Phase 2 — Core Algorithmic & ML Engine
- [x] **2.1 Dataset Loader & StratifiedGroupKFold** → verify: `pytest tests/test_dataset_leakage.py -v`
- [x] **2.2 Temperature Scaling & ECE Module** → verify: `pytest tests/test_calibration.py -v`
- [x] **2.3 ONNX Inference Engine Wrapper** → verify: `pytest tests/test_onnx_engine.py -v`
- [x] **2.4 Grad-CAM Heatmap Extraction** → verify: `pytest tests/test_explainability.py -v`

---

### Phase 3 — Service Layer & External Adapters
- [x] **3.1 InferenceService Facade** → verify: `pytest tests/test_inference_service.py -v`
- [x] **3.2 Groq Clinical Advisor Adapter** → verify: `pytest tests/test_services.py -v`
- [x] **3.3 History & Scan Repository** → verify: `pytest tests/test_history_service.py -v`
- [x] **3.4 FastAPI Production REST API Layer** → verify: `pytest tests/test_api.py -v`
- [x] **3.5 PRD v2.0 Backend Upgrades (/report, /history/{id}, /clinics, canonical /predict)** → verify: `pytest tests/test_v2_features.py -v`

---

### Phase 4 — Presentation & Web Application (Vercel Frontend + Render Backend)
- [x] **4.1 Production Multi-Screen Vite React UI** → verified: `cd frontend && npm run build` (Exit Code 0)
- [x] **4.2 Screen 1: Scan & Upload Engine** → verified: Aceternity FileUpload, ImageScanLoader laser, BlurText, SoftAurora, Stepper
- [x] **4.3 Screen 2: Diagnosis, Compare & PDF Export** → verified: Aceternity Compare Grad-CAM slider, 3-tier Risk Badge, Probability distribution, PDF generation
- [x] **4.4 Screen 3: Longitudinal Lesion History** → verified: Aceternity Timeline, risk escalation flags, scan timeline
- [x] **4.5 Screen 4: Geolocation Clinic Finder** → verified: 3D Pin, GPS acquisition, radius filter, Google Maps navigation
- [x] **4.6 Permanent Medical Disclaimer & Governance Footer** → verified: Regulatory notice, data sovereignty commitment
---

### Phase 5 — Quality Review, Testing & Release
- [x] **5.5 Cloud Deployment Blueprint (Render Free Tier & Docker)** → verified: `render.yaml` & `Dockerfile` pushed to main (Exit Code 0)
- [x] **5.1 Zero Patient Leakage Verification Gate** → verify: `pytest tests/test_dataset_leakage.py`
- [x] **5.2 Calibration ECE Target Gate (< 5%)** → verify: `pytest tests/test_calibration.py`
- [x] **5.3 Real Live Backend Verification Gate** → verified: `scratch/test_live_backend.py` with real lesion image (Exit Code 0)
- [x] **5.4 Production API Root Manifest Gate** → verified: GET / manifest - [x] **5.4 Production Hardening Gate (SQLite WAL, EXIF, Groq Fallback)** → verified: `data/dermassist.db` - [x] **5.3 Real Live Backend Verification Gate** → verified: `scratch/test_live_backend.py` with real lesion image (Exit Code 0) live Groq LPU (Exit Code 0) 19 passing tests (Exit Code 0)
- [x] **5.6 Live Production Deployment on Render** → verified: https://ai-derm-assistant-api.onrender.com/health (ONNX, Groq, Supabase operational, Exit Code 0)


## 2026-11-14 Safety and Robustness Batch
- Implemented conservative image-quality gating (minimum dimensions, Laplacian sharpness, contrast) with structured 422 responses for unusable uploads.
- Added three-zone routing (`green`, `yellow`, `red`), bounded original/horizontal/vertical flip TTA, and measured `inference_ms` metadata. Malignant and abstained outputs are never treated as green/actionable.
- Added malignant-result acknowledgment UI, model/head/image audit metadata, additive Supabase migration fields, and longitudinal class/risk/confidence change detection with dermatologist-review messaging.
- Added feedback submission and in-process aggregation endpoints with class-pair counts plus frontend controls.
- Verification: `python3 -m compileall -q backend/src` passed; `PYTHONPATH=backend pytest backend/tests -q` passed 21 tests; `cd frontend && npm run build` passed; `npm run lint` passed with 0 errors and 10 pre-existing warnings; `git diff --check` passed.
- Known limitation: feedback aggregation is process-local until a durable feedback table/RLS policy is deployed; the existing seven-class taxonomy is unchanged; no new validated temperature value was claimed.

## 2026-11-16 Candidate Artifact Safety
- Downloaded Kaggle Version 12 candidate artifacts to `/home/ubuntu/Downloads/kaggle_v12/`; production `backend/checkpoints/` was not modified.
- Candidate validation: lesion-disjoint final-test accuracy 0.8580, balanced accuracy 0.7000, macro F1 0.7116; BCC recall 0.7500; MEL recall 0.6190. Independent calibration reduced ECE 0.0832 → 0.0351 with temperature 1.5698.
- ONNX Runtime smoke test passed with input `1x3x380x380`, `features` `1x1792x12x12`, and seven-class head shape `[7,1792]`.
- Fixed the safe Kaggle notebook builder packaging cell to require and include `.onnx.data` plus matching `head_v2.json`, with ZIP completeness assertions. Existing Version 12 ZIP was intentionally not treated as deployable because it omitted `.onnx.data`.
- Verification: `PYTHONPATH=backend pytest backend/tests -q` passed 21 tests; `cd frontend && npm run build` passed; notebook builder syntax and packaging checks passed.

## 2026-11-16 Conservative Inference Guardrails
- Added provisional abstention gates in `backend/src/services/inference_service.py`: calibrated top probability must be at least 0.80, top-two margin at least 0.20, and normalized entropy at most 0.50 for an actionable result.
- Green routing is stricter and limited to benign classes (`bkl`, `df`, `nv`, `vasc`): confidence >= 0.85, margin >= 0.25, and normalized entropy <= 0.40. `akiec` routes yellow; `bcc` and `mel` route red for clinician review.
- Added deterministic threshold regression tests. Verification: compileall passed, targeted inference tests 4/4 passed, full backend suite 24/24 passed, and `git diff --check` passed.
- These are explicitly provisional engineering guardrails, not clinically validated operating points; production model weights remain unchanged.

## 2026-11-16 Comprehensive Security Hardening & Lockdown
- Secret & Key Protection: Hardened root and frontend `.gitignore` for `.env*`, `*.key`, `*.pem`, `*.db`, and credentials. Masked secret attributes (`GROQ_API_KEY`, `SUPABASE_KEY`, `ADMIN_API_KEY`) from Pydantic `Settings` repr and adapter `__repr__` to prevent accidental logging.
- Transport & HTTPS Everywhere: Added `security_headers_and_https_middleware` enforcing HSTS (2 years, subdomains, preload), X-Content-Type-Options `nosniff`, X-Frame-Options `DENY`, Referrer-Policy, CSP, and automated 301 HTTPS redirection for `x-forwarded-proto: http`. Configured edge security headers in `frontend/vercel.json`.
- CORS Hardening: Disallowed `allow_credentials=True` when wildcard `*` origins are used to comply with W3C/Fetch standards and prevent CSRF/credential leakage.
- Admin Surface & Docs Lockdown: Confirmed zero rogue admin pages; locked `/docs`, `/redoc`, and `/openapi.json` in production unless explicitly enabled via `ENABLE_DOCS`. Gated administrative endpoints (`/feedback/summary`) behind `X-Admin-Key` with constant-time verification.
- Password Hashing Utility: Implemented OWASP-compliant `scrypt` salted password hashing with `hmac.compare_digest` in `backend/src/core/security.py`.
- Database Lockdown: Fixed `docs/supabase_schema.sql` by dropping dangerous public UPDATE and DELETE policies. Created `docs/security_lock_database.sql` for live RLS lockdown and restricted Storage buckets to validated image MIME types (15MB cap).
- Daily Backup System: Created `scripts/backup_supabase.py` with 30-day retention pruning and `.github/workflows/daily_backup.yml` running every midnight UTC (`0 0 * * *`).
- Upload Security: Added magic byte verification and 15MB file cap with Pillow decompression bomb protection (`MAX_IMAGE_PIXELS <= 25,000,000`). Sanitized API error outputs.
- Verification: `python scripts/security_audit.py` passed 35/35 checks (exit code 0); `pytest backend/tests/ -v` passed 31/31 tests (exit code 0); `cd frontend && npm run build` passed (exit code 0).

## 2026-11-16 Tier 1 Clinical & Quality Improvements
- Feature 1 (Skin Detection in Monitoring Mode): Implemented multi-phototype (Fitzpatrick I-VI) YCrCb + HSV skin chromophore detection in `quality_service.py`. Records `skin_detected` and `skin_fraction` in quality telemetry without altering image acceptance decisions (zero false rejections).
- Feature 2 (Patient Metadata Integration): Added optional clinical context fields (`age`, `sex`, `anatomical_site`, `history_of_melanoma`) in `/predict`, request schemas, and frontend `ScanScreen.jsx` collapsible accordion. Formatted into Groq prompt under segregated `Patient-Reported Context` with explicit rule forbidding model risk/prediction overrides. Missing metadata preserves baseline behavior with zero PII logging or persistence.
- Verification: Added `test_skin_detection.py` (5 tests) and `test_patient_metadata.py` (4 tests); full test suite passed 40/40 tests (exit code 0); frontend lint passed with 0 errors; production build succeeded in 1.13s (exit code 0).

## 2026-11-21 v3 Ensemble Rebuild (branch Dev)
- Replaced the EfficientNet-B4 model with the v3 three-model ensemble (ConvNeXt-V2-T@384, EfficientNetV2-S@384, EVA02-S@336), each using image + 19 metadata features. Weights in `backend/checkpoints/v3/` (Git LFS), config `model_v3.json`, training/export code in `training/v3/`.
- v3 test split (1,975 images, lesion-disjoint): accuracy 85.6%, balanced accuracy 75.8%, macro F1 0.772, melanoma recall 85.3% at threshold 0.34, ECE 2.9%, malignant AUC 0.950.
- Removed the legacy engine, `efficientnet_b4_ham10000.onnx`, `head_v2.json`, old training notebooks and core re-export shims.
- Verification: backend output matches training logits on 21 test images (21/21 same class, max logit diff 0.005).
- Known gap: ~7.4 s per prediction on 2 CPU cores and ~795 MB peak RAM (Render limit 512 MB). Speed/RAM work in progress.
