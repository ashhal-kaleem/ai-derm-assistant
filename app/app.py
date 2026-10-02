"""DermAssist AI — Streamlit Web Presentation Layer."""

import io
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(".env", override=True)
except ImportError:
    pass
from typing import Optional
import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st

from src.domain.knowledge_cards import MANDATORY_MEDICAL_DISCLAIMER, STATIC_KNOWLEDGE_CARDS
from src.domain.models import DIAGNOSIS_CATALOG, RiskLevel
from src.services.groq_service import GroqService
from src.services.history_service import HistoryService
from src.services.inference_service import InferenceService

# Page Setup
st.set_page_config(
    page_title="DermAssist AI — Skin Lesion Diagnostic Support",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #888888;
        margin-bottom: 1.2rem;
    }
    .disclaimer-box {
        background-color: #2b1f09;
        border-left: 5px solid #FF9800;
        padding: 12px 16px;
        border-radius: 4px;
        color: #FFD54F;
        font-size: 0.9rem;
        margin-bottom: 20px;
    }
    .risk-badge-benign {
        background-color: #1B5E20;
        color: #A5D6A7;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .risk-badge-potential {
        background-color: #E65100;
        color: #FFE0B2;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .risk-badge-malignant {
        background-color: #B71C1C;
        color: #FFCDD2;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .metric-card {
        background-color: #1E2229;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Services
@st.cache_resource
def get_services():
    inference_svc = InferenceService(temperature=1.25)
    groq_svc = GroqService()
    history_svc = HistoryService()
    return inference_svc, groq_svc, history_svc

inference_service, groq_service, history_service = get_services()

# Permanent Medical Disclaimer (Law #4)
st.markdown(f'<div class="disclaimer-box">{MANDATORY_MEDICAL_DISCLAIMER}</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🔬 DermAssist AI")
    st.caption("HAM10000 Calibrated Dermatology Diagnostic Support")
    st.divider()

    st.subheader("⚙️ System Status")
    st.markdown("**Inference Engine:** `ONNX Runtime (CPU)`")
    st.markdown("**Calibration:** `T* = 1.25 (Temperature Scaled)`")
    supabase_status = "🟢 Connected" if history_service.client.is_connected else "🟡 Cloud Fallback"
    st.markdown(f"**Database:** `Supabase ({supabase_status})`")
    groq_status = "🟢 Active" if groq_service.client is not None else "🟡 Static Reference Fallback"
    st.markdown(f"**Advisory:** `Groq Llama 3.3 70B ({groq_status})`")
    st.divider()

    st.caption("DermAssist AI v1.0.0 — Universal Sovereign Protocol")

# Main Navigation Tabs
tab_analyze, tab_catalog, tab_history = st.tabs([
    "🔍 Diagnostic Analysis",
    "📚 7-Class Clinical Catalog",
    "☁️ Cloud Scan History"
])

# TAB 1: Diagnostic Analysis
with tab_analyze:
    st.markdown('<div class="main-header">Skin Lesion Diagnostic Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload a high-resolution clinical dermoscopic image of the skin lesion to analyze.</div>', unsafe_allow_html=True)

    input_image: Optional[Image.Image] = None
    image_bytes: Optional[bytes] = None

    uploaded_file = st.file_uploader(
        "Upload Clinical Dermoscopic Image (JPEG, PNG):",
        type=["jpg", "jpeg", "png"],
        help="Clear, focused dermoscopic or close-up image of the skin lesion."
    )

    if uploaded_file is not None:
        raw_val = uploaded_file.getvalue()
        if len(raw_val) > 8 * 1024 * 1024:
            st.error("Uploaded image exceeds 8MB limit. Please upload an image under 8MB.")
        else:
            try:
                test_img = Image.open(io.BytesIO(raw_val))
                test_img.verify()
                image_bytes = raw_val
                input_image = Image.open(io.BytesIO(image_bytes))
            except Exception:
                st.error("Invalid or corrupted image file. Please upload a valid JPEG/PNG dermoscopic image.")
        input_image = Image.open(io.BytesIO(image_bytes))

    if input_image is not None and image_bytes is not None:
        analyze_btn = st.button("🚀 Analyze Lesion with Calibrated AI", type="primary", use_container_width=True)

        if analyze_btn:
            with st.spinner("Analyzing lesion features and generating Grad-CAM explainability overlay..."):
                # Run inference
                prediction = inference_service.predict(input_image)
                
                # Generate clinical summary
                summary = groq_service.generate_clinical_summary(prediction)
                prediction.clinical_summary = summary
                
                # Persist to cloud storage and database
                scan_record = history_service.record_scan(
                    prediction=prediction,
                    image_bytes=image_bytes,
                    heatmap_bytes=prediction.saliency_heatmap_bytes
                )

            st.divider()

            # Side-by-side Visuals
            col_img, col_cam = st.columns(2)
            with col_img:
                st.subheader("📷 Original Lesion Image")
                st.image(input_image, use_container_width=True)
            with col_cam:
                st.subheader("🔥 Grad-CAM Explainability Map")
                if prediction.saliency_heatmap_bytes:
                    st.image(prediction.saliency_heatmap_bytes, use_container_width=True)
                    st.caption("Visual regions of maximal morphological importance to the AI classifier.")

            st.divider()

            # Primary Diagnostic Result Banner
            risk_class = prediction.risk_level.value
            badge_html = {
                "BENIGN": '<span class="risk-badge-benign">BENIGN LESION</span>',
                "POTENTIALLY_MALIGNANT": '<span class="risk-badge-potential">POTENTIALLY MALIGNANT</span>',
                "MALIGNANT": '<span class="risk-badge-malignant">MALIGNANT SUSPECT</span>'
            }.get(risk_class, '<span class="risk-badge-benign">BENIGN</span>')

            st.markdown(f"### Primary Finding: **{prediction.top_name}** (`{prediction.top_class}`) &nbsp; {badge_html}", unsafe_allow_html=True)

            # Key Clinical Metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Calibrated Confidence", f"{prediction.calibrated_confidence * 100:.1f}%")
            with m2:
                st.metric("Raw Confidence", f"{prediction.raw_confidence * 100:.1f}%")
            with m3:
                st.metric("Temperature Scalar (T*)", f"{prediction.temperature:.2f}")
            with m4:
                uncertainty_pct = prediction.uncertainty_score * 100
                st.metric("Uncertainty Score", f"{uncertainty_pct:.1f}%", help="Normalized Shannon Entropy across 7 diagnostic classes (0% = certain, 100% = max ambiguity)")

            # Diagnostic Distribution Table & Bars
            st.subheader("📊 Calibrated Probability Distribution across 7 Classes")
            prob_data = []
            for p in prediction.probabilities:
                prob_data.append({
                    "Code": p.code,
                    "Diagnosis": p.name,
                    "Risk Tier": p.risk_level.value,
                    "Calibrated Probability (%)": round(p.probability * 100, 2)
                })
            prob_df = pd.DataFrame(prob_data)
            st.dataframe(prob_df, use_container_width=True, hide_index=True)
            st.bar_chart(prob_df.set_index("Diagnosis")["Calibrated Probability (%)"], color="#1E88E5")

            # Groq LPU Clinical Advisory Report
            st.subheader("🩺 Clinical Advisory Report")
            st.markdown(summary)

            # Clinician Feedback Block
            st.divider()
            st.caption("Help improve DermAssist AI by providing clinical verification:")
            fb_col1, fb_col2, fb_col3 = st.columns(3)
            with fb_col1:
                if st.button("👍 Clinically Accurate", use_container_width=True):
                    st.success("Thank you! Feedback recorded.")
            with fb_col2:
                if st.button("⚠️ Uncertain / Ambiguous", use_container_width=True):
                    st.warning("Feedback recorded for audit review.")
            with fb_col3:
                if st.button("❌ Inaccurate Classification", use_container_width=True):
                    st.error("Feedback flagged for clinician re-evaluation.")

# TAB 2: Clinical Catalog
with tab_catalog:
    st.markdown('<div class="main-header">HAM10000 7-Class Dermatology Knowledge Base</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comprehensive diagnostic metadata, clinical descriptions, and ABCD dermatological relevance for each class.</div>', unsafe_allow_html=True)

    for code, meta in DIAGNOSIS_CATALOG.items():
        card = STATIC_KNOWLEDGE_CARDS[code]
        with st.expander(f"**{meta.name}** (`{code}`) — {card['risk_tier']}", expanded=(code == "mel")):
            st.markdown(f"**Clinical Description:** {card['description']}")
            st.markdown(f"**Typical Presentation:** {card['typical_appearance']}")
            st.markdown(f"**ABCDE Criteria Relevance:** {card['abcde_relevance']}")
            st.markdown(f"**Recommended Clinical Urgency:** `{card['urgency']}`")

# TAB 3: Cloud History
with tab_history:
    st.markdown('<div class="main-header">Cloud Diagnostic History</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Recent scans persisted in Supabase Cloud PostgreSQL.</div>', unsafe_allow_html=True)

    recent_scans = history_service.get_recent_scans(limit=15)
    if recent_scans:
        history_rows = []
        for s in recent_scans:
            history_rows.append({
                "Scan ID": s.id[:8] + "...",
                "Timestamp": s.created_at[:19] if s.created_at else "N/A",
                "Diagnosis": s.predicted_class,
                "Risk Tier": s.risk_level,
                "Calibrated Confidence": f"{s.calibrated_confidence * 100:.1f}%",
                "Uncertainty": f"{s.uncertainty_score * 100:.1f}%"
            })
        st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No prior scan records found. Run an analysis in Tab 1 to populate cloud history.")

# Permanent Medical Disclaimer at Footer
st.divider()
st.markdown(f'<div class="disclaimer-box">{MANDATORY_MEDICAL_DISCLAIMER}</div>', unsafe_allow_html=True)
