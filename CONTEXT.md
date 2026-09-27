# CONTEXT.md — DermAssist AI

> **Living Workspace Memory & Execution Engine**  
> 1. Read this file FIRST at the start of every session to rehydrate state.  
> 2. Respect Active Task Scope: Modify ONLY targeted files for the current step.  
> 3. Never mark `[x]` without live verification (exit code 0).  
> 4. Keep this file lean (< 350 lines). Update as the FINAL step of every session.  

---

## 🧭 1. Project Snapshot & Runtime State
- **Core Purpose:** Calibrated, explainable, ultra-lightweight skin lesion diagnostic assistant with zero patient leakage and sub-250ms ONNX inference.
- **Current Honest State:** Phase 3 completed (Documentation SSOT Scaffolding finalized). Ready for Mode 2 Phase 4 (Foundations & Model Engine).
- **Active Working Branch:** `main`
- **Local Dev Environment:**
  | Service | Host / Port | Status | Verification Command |
  |---|---|---|---|
  | Streamlit Web App | `localhost:8501` | Stopped | `curl -sI http://localhost:8501/_stcore/health` |
  | Cloud DB | Supabase (PostgreSQL) | Remote Cloud | `curl -sI $SUPABASE_URL` |
| Cloud Storage | Supabase (`scans` bucket) | Remote Cloud | Supabase Storage API |
- **Live Production URL:** Not yet deployed (Target: HuggingFace Spaces)
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
- **Grad-CAM**: Gradient-weighted Class Activation Mapping saliency heatmap.

---

## ⚡ 3. Session Handover & State Rehydration (Pick Up Here)
- **Session Timestamp:** 2026-09-27 16:45
- **Verified Accomplishments (What Works):**
  - Phase 0 6-Sphere Research Dossier completed → Verified: `wc -l ~/agent-reach/Downloads/Research\ Engine/ai_dermatology_assistant_research_dossier.md` (216 lines, exit 0)
  - PRD and Architecture SSOT deployed → Verified: `docs/PRD.md` and `docs/architecture.md` exist and fully populated (exit 0)
  - AGENTS.md master handbook deployed → Verified: `AGENTS.md` exists (exit 0)
- **Recently Touched Files (Targeted Re-analysis):**
  - `docs/PRD.md` — Complete Product Requirements Document
  - `docs/architecture.md` — Complete System Blueprint & Schemas
  - `AGENTS.md` — Master Developer Handbook & Invariants
- **Active Blockers & Pending Decisions (Awaiting Human):**
  - None. Options 1 (ONNX Runtime) and 3 (Gemini 2.0 Flash API) approved by user.
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
- [ ] **1.1 Requirements & Python Environment** → verify: `pip check`
- [ ] **1.2 Supabase Cloud Connection & Storage** → verify: `python3 -c "import supabase; print(supabase.__name__)"`
- [ ] **1.3 Static Knowledge Cards JSON** → verify: `python3 -m json.tool app/knowledge_cards.json > /dev/null`

---

### Phase 2 — Core Algorithmic & ML Engine
- [ ] **2.1 Dataset Loader & StratifiedGroupKFold** → verify: `pytest tests/test_dataset_leakage.py -v`
- [ ] **2.2 Temperature Scaling & ECE Module** → verify: `pytest tests/test_calibration.py -v`
- [ ] **2.3 ONNX Inference Engine Wrapper** → verify: `pytest tests/test_onnx_engine.py -v`
- [ ] **2.4 Grad-CAM Heatmap Extraction** → verify: `pytest tests/test_explainability.py -v`

---

### Phase 3 — Service Layer & External Adapters
- [ ] **3.1 InferenceService Facade** → verify: `pytest tests/test_inference_service.py -v`
- [ ] **3.2 Gemini Clinical Advisor Adapter** → verify: `pytest tests/test_gemini_service.py -v`
- [ ] **3.3 History & Scan Repository** → verify: `pytest tests/test_history_service.py -v`

---

### Phase 4 — Presentation & Web Application (Streamlit)
- [ ] **4.1 Streamlit App Layout & Upload Component** → verify: `streamlit run app/app.py --server.headless true & sleep 3 && curl -sI http://localhost:8501/_stcore/health`
- [ ] **4.2 Heatmap Overlay & Confidence Visualizer** → verify: `python3 tests/smoke_ui_components.py`
- [ ] **4.3 Mandatory Medical Disclaimer Enforcement** → verify: `grep -rn "Disclaimer" app/app.py`

---

### Phase 5 — Quality Review, Testing & Release
- [ ] **5.1 Zero Patient Leakage Verification Gate** → verify: `pytest tests/test_dataset_leakage.py`
- [ ] **5.2 Calibration ECE Target Gate (< 5%)** → verify: `pytest tests/test_calibration.py`
