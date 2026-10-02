# AGENTS.md

> **Master Developer Handbook & Operational Standards for DermAssist AI**  
> Built on the Universal Sovereign Developer Protocol & AGENTS.md Open Standard.  
> Read this file before every task. Working code only. Finish the job.

<!-- Cross-Tool Portability: Symlinks:
     ln -s AGENTS.md CLAUDE.md
     ln -s AGENTS.md GEMINI.md -->

---

## 0. Non-Negotiable Operating Laws

1. **Direct Technical Communication**: Skip sycophantic openers. Start directly with findings, diffs, or verified actions.
2. **Disagree Directly**: If a technical assumption or architecture proposal is flawed, state the friction immediately with tradeoffs.
3. **Never Fabricate**: Never invent file paths, accuracy scores, commit hashes, or test results. Always inspect via Linux terminal commands.
4. **Touch Only What You Must (Surgical Changes)**: Every changed line must trace directly to the request. Zero drive-by refactoring or unrequested reformatting.
5. **Simplicity First (Anti-Slop)**: Write the minimum code that solves the problem. Zero speculative abstractions, zero unrequested configurability.
6. **Compounding Memory (The Ratchet Protocol)**: Inspect `./decisions.log` before making architectural decisions. Append resolved invariants to `decisions.log` with user approval.

---

## ⚡ Quick Commands

| Action | Command | Notes |
|---|---|---|
| **Install Dependencies** | `pip install -r requirements.txt` | Locked virtual environment |
| **Run Dev / Local App** | `streamlit run app/app.py` | Local Streamlit UI on :8501 |
| **Run All Tests** | `pytest tests/ -v` | Full test suite verification |
| **Run Leakage Test** | `pytest tests/test_dataset_leakage.py -v` | Validates 0 patient overlap |
| **Run Calibration Test** | `pytest tests/test_calibration.py -v` | Validates ECE optimization |
| **Typecheck** | `mypy src/ --ignore-missing-imports` | 0 errors required |
| **Lint & Format** | `ruff check src/ app/ tests/` | Enforce code style |
| **Healthcheck / Smoke** | `curl -sI http://localhost:8501/_stcore/health` | Live Streamlit server probe |

---

## 🧭 System Overview & Architecture Summary
- **Domain**: AI Dermatology Assistant & Skin Lesion Diagnostic Support (HAM10000 benchmark)
- **Target Archetype**: Web / Machine Learning Inference System (Archetypes 5 & 6)
- **Core Architecture**: Modular Clean Architecture (`src/` domain engine, ONNX inference runtime, Groq LPU clinical adapter, Streamlit UI)
- **Primary Specifications**: Read `docs/architecture.md` and `docs/PRD.md` before making architectural decisions.
- **Living Memory**: Read `CONTEXT.md` at the start of every session; update it before completing work.
- **Decisions Memory**: Inspect `decisions.log` for past project invariants.

---

## 📁 Universal Repository Root & Forbidden Zones

```text
ai-derm-assistant/
├── docs/                      # Architectural specifications & PRD (SSOT)
│   ├── PRD.md                 # Product & Business SSOT
│   └── architecture.md        # Technical SSOT: topology, schemas, runbook
├── src/                       # Core ML Engine, domain entities & services
│   ├── domain/                # Pure business logic & clinical schemas
│   ├── core/                  # ONNX engine, calibration, Grad-CAM, dataset
│   ├── services/              # InferenceService, GroqService, HistoryService
│   └── infrastructure/        # Supabase Cloud Client & Repositories
├── app/                       # Streamlit Web Presentation Layer
├── notebooks/                 # EDA, training, and ablation analysis
├── tests/                     # Automated test gates (leakage, calibration, inference)
├── checkpoints/               # Trained model weights (ONNX format)
├── CONTEXT.md                 # Living workspace memory & active task state
├── AGENTS.md                  # Developer guidelines & architectural invariants
├── CHANGELOG.md               # Versioning & release history
├── decisions.log              # Local Ratchet invariants (append-only)
└── requirements.txt           # Version-pinned runtime dependencies
```

### 🚫 Forbidden Zones (Off-Limits Files — Hook Enforced)
1. **Auto-Generated & Build Artifacts**: Never touch compiled outputs or caches (`__pycache__/`, `.pytest_cache/`, `checkpoints/*.pt` raw gigabyte weights).
2. **Lockfiles & Environments**: Never edit `requirements.lock` manually.
3. **Private Credentials & Secrets**: Never commit `.env`, `*credentials*.json`, or API keys.

---

## 🏛️ Core Architectural Invariants (The Sovereign Law)

1. **Strict One-Way Dependency Flow**:
   $$\text{Streamlit UI} \longrightarrow \text{Services} \longrightarrow \text{Core Domain Engine} \longrightarrow \text{Infrastructure / Adapters}$$
   Presentation components are strictly forbidden from directly querying raw database tables or executing low-level tensor transforms.
2. **Zero Patient-Level Data Leakage**:
   All dataset splitting must group by `lesion_id` using `StratifiedGroupKFold`. Train and validation sets must have zero lesion intersection.
3. **Calibrated Confidence Law**:
   All confidence percentages displayed to users must be temperature-scaled ($T^*$). Uncalibrated raw softmax scores are prohibited in the UI.
4. **Permanent Medical Disclaimer**:
   The educational disclaimer cannot be hidden, dismissed, or disabled.
5. **The Evidence Contract (Hook Enforced)**:
   Never mark an item complete without a terminal command running with exit code `0`.
6. **Zero Stubs Law**:
   All production code must be fully implemented. Stubs, incomplete implementations, or mock placeholders in production code are strictly forbidden.

---

## ⚖️ Autonomous Boundary & Escalation Gate

**Proceed autonomously when:**
- Adding modular services, unit tests, or domain logic conforming to `docs/architecture.md`.
- Improving UI performance, styling, or error handling.
- Fixing test regressions or adding verified calibration mathematics.

**Stop and ask the user when:**
- Proposing changes that alter the 7-class diagnostic schema.
- Switching away from ONNX Runtime or introducing paid external cloud infrastructure.
- Altering core medical disclaimers or clinical warning thresholds.
