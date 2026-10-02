# Product Requirements Document (PRD) — DermAssist AI

> **Status**: Approved  
> **Target Release**: v1.0 MVP  
> **Technical Architecture**: Defined in [`architecture.md`](./architecture.md) | Repo Rules in [`../AGENTS.md`](../AGENTS.md)  
> **Last Updated**: 2026-09-27  

---

## 1. Executive Summary & Problem Framing

### 1.1 One-Line Value Proposition
DermAssist AI is a calibrated, explainable, and ultra-lightweight skin lesion diagnostic assistant that empowers patients and triage clinicians to analyze dermoscopic images in under 250 milliseconds with zero patient-data leakage and explicit uncertainty warnings.

### 1.2 Problem Statement & Pain Points
Skin cancers (melanoma, basal cell carcinoma) are among the most common malignancies globally, where early detection increases 5-year survival rates from 27% to over 99%. However:
1. **Academic Leakage & False Confidence**: Existing open-source ML models report 88–92% accuracy on HAM10000 by splitting datasets randomly, failing to realize that multiple images share the same lesion ID. In production, these models collapse to ~76% on new patients.
2. **Lethal Class Imbalance**: Benign nevi account for 67% of data, while melanomas account for 11% and vascular lesions 1.4%. Naive classifiers prioritize benign predictions to maximize raw accuracy, missing life-threatening melanomas.
3. **Deceptive Overconfidence**: Standard deep learning softmax outputs uncalibrated probabilities (e.g. 99% confident on ambiguous inputs), misleading non-expert users.
4. **Black-Box Saliency**: Users and doctors cannot verify whether an algorithm is looking at genuine cellular morphology or dermatoscope lens vignetting and hair artifacts.

### 1.3 Target Audience & Primary ICP
- **Primary ICP**: Triage medical students, general practitioners, teledermatology clinics, and health-conscious individuals seeking educational pre-screening.
- **Core Value Differentiator**: Patient-aware honesty (leakage-free evaluation), calibrated probabilities via Temperature Scaling, epistemic uncertainty flagging via Monte Carlo Dropout, visual Grad-CAM transparency, and dynamic Gemini-powered patient reports—running on ultra-fast ONNX runtime with zero infrastructure costs.

### 1.4 Goals & Measurable Success Metrics (KPIs)

| Metric / KPI | Current Baseline | Success Target | Measurement Source |
|---|---|---|---|
| **Melanoma Sensitivity (Recall)** | ~55% (unweighted CE) | > 84.0% | Held-out Patient-Aware Test Split |
| **Macro F1 Score** | ~0.65 | > 0.78 | 7-Class Balanced Evaluation |
| **Expected Calibration Error (ECE)** | ~14.2% (uncalibrated) | < 5.0% | Reliability Diagram & ECE Metric |
| **Inference Latency (p95)** | > 1,000 ms (Unoptimized Baseline) | < 250 ms | ONNX Runtime Benchmark |
| **Deployment Footprint** | Heavy DL Framework (>1 GB)| < 100 MB | Clean Container / Environment Audit |

### 1.5 Positive Non-Goals (Explicitly Out of Scope)

> **Anti-Scope-Creep Law**: Positively stated boundaries.
- **Do NOT provide definitive medical diagnoses**: The system is strictly educational and advisory; it must mandate licensed dermatologist follow-up.
- **Do NOT process non-skin medical imagery**: The system rejects non-dermoscopic or non-cutaneous images (radiology, fundus, pathology slides).
- **Do NOT build a native iOS/Android binary in v1.0**: Focus exclusively on a responsive Web / Streamlit interface with optional REST API hooks.
- **Do NOT execute real-time multi-pass MC Dropout in production web UI**: Restrict web UI to single-pass calibrated ONNX inference with static/Gemini explanations to preserve sub-300ms responsiveness; MC Dropout is reserved for offline/batch evaluation.
- **Do NOT implement complex multi-tenant billing or paid paywalls**: The application runs 100% free-tier and open-source.

---

## 2. Product Boundaries & User Prerequisites

### 2.1 User Environment & Platform Constraints
- **Client Environment**: Modern evergreen web browsers (Chrome, Safari, Firefox, Edge) on desktop and mobile.
- **Input Image Formats**: JPG, JPEG, PNG format up to 10 MB per image.
- **Hardware Footprint**: Operable on low-power CPU environments (2 vCPU, 1GB RAM) without requiring a local GPU.

### 2.2 Operational Assumptions & Prerequisites
- **Input Nature**: For optimal reliability, images should be close-up dermatoscopic or macro-lens photographs. Regular mobile camera photos are accepted but trigger explicit low-fidelity warnings.
- **External API Keys**: Optional Google Gemini API key provided via environment variable (`GEMINI_API_KEY`) for dynamic clinical reports. If absent, system gracefully falls back to verified static knowledge cards.

---

## 3. Prioritized Feature Requirements (P0 / P1 / P2)

- **🌟 Priority P0: Mandatory Core MVP** (Ship Blocker — non-functional without these).
- **🚀 Priority P1: Key Enhancements** (Expands adoption, intelligence, and history).
- **🎨 Priority P2: Future Polish & Delighters** (Extended clinical tools).

| Feature ID | Feature Name | Priority | User Story Summary | Acceptance Test Status |
|---|---|---|---|---|
| **F-01** | Image Ingestion & Validation | `P0` | User uploads a skin lesion image (drag-and-drop or file selector) with dimension and format validation. | `[ ] Unverified` |
| **F-02** | Calibrated 7-Class Prediction | `P0` | System returns primary diagnostic prediction with temperature-calibrated confidence score. | `[ ] Unverified` |
| **F-03** | Grad-CAM Saliency Overlay | `P0` | User views side-by-side original image and Grad-CAM attention heatmap highlighting active regions. | `[ ] Unverified` |
| **F-04** | Static Knowledge Card & Disclaimer | `P0` | System displays permanent, unclosable medical disclaimer and structured clinical overview for predicted class. | `[ ] Unverified` |
| **F-05** | ONNX Runtime Acceleration | `P0` | Inference executes in < 250ms on CPU using quantized/optimized ONNX model weights. | `[ ] Unverified` |
| **F-06** | Gemini Clinical Advisory Report | `P1` | System generates a structured patient summary and recommended next steps via Gemini 2.0 Flash API. | `[ ] Unverified` |
| **F-07** | Scan History & Persistent Logging | `P1` | Scans and heatmaps are persisted to Supabase Cloud DB & Storage with zero local disk footprint. | `[ ] Unverified` |
| **F-08** | Batch Evaluation & ECE Reporting | `P1` | Researcher / student runs evaluation suite verifying zero data leakage and post-temperature ECE. | `[ ] Unverified` |
| **F-09** | Fitzpatrick Skin-Type Bias Audit | `P2` | System warns on extreme phototypes or logs subgroup error disparities. | `[ ] Unverified` |

---

## 4. User Journeys & Testable Acceptance Scenarios

### 🌟 Journey 1 (P0): Single Lesion Scan & Visual Explanation
- **Actor**: General user / Triage clinician
- **Preconditions**: Web app is running; model weights are loaded.
- **Step-by-Step Flow**:
  1. User navigates to application and uploads `ISIC_0024306.jpg`.
  2. System validates format, rescales image to 380×380, and runs ONNX inference pipeline.
  3. System generates Grad-CAM heatmap from final convolutional features.
  4. UI renders:
     - Predicted Condition with Risk Badge (e.g., "Melanoma — MALIGNANT").
     - Calibrated Confidence Bar (e.g., "87.4%").
     - Side-by-side Original vs Heatmap view.
     - Mandatory Medical Disclaimer.
- **Acceptance Criteria (Gherkin Format)**:
  - **Scenario A (Happy Path)**:
    - **Given** a valid JPG dermoscopic image under 10 MB,
    - **When** the user submits the image for analysis,
    - **Then** the prediction, calibrated confidence, Grad-CAM overlay, and medical disclaimer are displayed in under 500 ms total render time.
  - **Scenario B (Corrupted / Invalid Input)**:
    - **Given** an invalid text file renamed to `.jpg` or corrupted image binary,
    - **When** the user attempts upload,
    - **Then** the system catches the format error, returns an inline user-friendly alert, logs zero crash, and maintains UI stability.

### 🚀 Journey 2 (P1): Gemini-Enhanced Doctor-Ready Clinical Summary
- **Actor**: Patient / Clinician wanting actionable interpretation
- **Preconditions**: Valid prediction computed; `GEMINI_API_KEY` configured.
- **Step-by-Step Flow**:
  1. Prediction completes with class `bcc` (Basal Cell Carcinoma) at 91% confidence.
  2. System packages prediction, risk tier, and visual description into a structured prompt.
  3. Gemini 2.0 Flash streams a formatted report: Overview, ABCDE characteristics, What to Ask Your Doctor, Urgency Level.
- **Acceptance Criteria**:
  - **Given** an active Gemini API connection and a completed prediction,
  - **When** the summary generator runs,
  - **Then** a structured report appears containing urgent clinical disclaimer and next steps.
  - **Given** no Gemini API key or network timeout (429/503),
  - **When** generation fails,
  - **Then** the system gracefully falls back to the local static knowledge card without interrupting the user.

---

## 5. Edge Cases & Degraded UX Contracts

| Degraded State | Trigger Condition | System Behavior & User Contract |
|---|---|---|
| **Empty State** | Application initialized with no image uploaded | Display clean upload zone with sample lesion buttons (`Load Sample Melanoma`, `Load Sample Nevus`). |
| **High Uncertainty / Out-of-Distribution** | Calibrated top-1 confidence < 50% or ambiguous entropy | Display warning banner: *"Ambiguous Lesion Detected — Inconclusive AI Analysis. Immediate in-person dermatologist evaluation strongly advised."* |
| **Gemini API Outage / 429** | Google Gemini rate limit or network failure | Silently fallback to built-in static medical knowledge cards with zero UI freeze. |
| **Non-Dermoscopic Phone Photo** | Blurry or low-resolution image uploaded | Display warning notice: *"Non-standard dermoscopy detected. Photographic artifacts may degrade accuracy."* |
| **Database Connection Failure** | Database host unreachable during scan log save | Log warning to server log, complete UI scan seamlessly (read/inference remains unaffected). |

---

## 6. Non-Functional Requirements & Open Product Questions

### 6.1 Non-Functional Requirements (NFRs)
- **Latency**: p95 inference latency < 250ms on CPU.
- **Portability**: Production image runs in standard Python 3.10+ container requiring < 1GB RAM.
- **Reliability**: 100% crash-free exception handling on invalid images.
- **Privacy & Safety**: Zero patient images stored publicly or transmitted to third parties without user knowledge. Permanent disclaimer visible on all screens.

### 6.2 Open Product Questions
- **Q-01**: Should patient scan history retain full raw image files or only compressed thumbnails + hashes to preserve disk space? *(Resolved: Store 128x128 thumbnail + SHA256 hash).*
- **Q-02**: Should MC Dropout be exposed as an optional "Deep Scan (Slow)" checkbox in the UI? *(Resolved: Added as optional user toggle; default is fast single-pass ONNX).*
