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
import base64
import streamlit.components.v1 as components
from src.services.report_service import ReportService

# Page Setup
st.set_page_config(
    page_title="DermAssist AI — Skin Lesion Diagnostic Support",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

HTML_TEMPLATE_PATH = PROJECT_ROOT / "app" / "stitch_screen.html"
with open(HTML_TEMPLATE_PATH, "r", encoding="utf-8") as f:
    template_html = f.read()

st.sidebar.markdown("### 🔬 Clinical Ingestion Controls")
patient_id = st.sidebar.text_input("Patient Reference ID", value="PT-10492")
uploaded_file = st.sidebar.file_uploader("Upload Skin Lesion Image", type=["jpg", "png", "jpeg"])

final_html = template_html

if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file).convert("RGB")
        inference_service = InferenceService()
        result = inference_service.predict(image)

        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        orig_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"

        cam_b64 = orig_b64
        if result.gradcam_heatmap_bytes:
            cam_b64 = f"data:image/png;base64,{base64.b64encode(result.gradcam_heatmap_bytes).decode()}"

        final_html = final_html.replace("Likely Benign Atypical Nevus", result.predicted_label)
        final_html = final_html.replace("94.2% Benign Probability", f"{result.confidence * 100:.1f}% Calibrated Probability")
        final_html = final_html.replace("Minimal Concern (Grade 1)", f"{result.risk_level.value.upper()} Risk Tier")
        final_html = final_html.replace("https://lh3.googleusercontent.com/aida/AEtjO1WHXddFF76k1EGLi1zhbSmEOVDT5AXrY9RqlsXrvM0lHTuh68wnvwkcGK4gRkMJADmwy3dQV6_iCZZ0Xw0dooo3WkQgjXjYXrUy6F5iRfddpf1biMy1SxuxKrBqXA7l66e8KqVR0CBfD0TVxWURMkm_nVYfRL0SjWczEV6btUy0L5cB6V-Psd65jtRxbnruU3RMWbqLvGKw3CgmE684ChO1Jv0czZpGCS0Wp7Haryf6Wa-6wwn-1hniiWY", cam_b64)

        report_service = ReportService()
        pdf_bytes = report_service.generate_pdf_report(
            patient_id=patient_id,
            diagnosis=result.predicted_label,
            confidence=result.confidence,
            risk_level=result.risk_level.value,
            clinical_notes=f"Calculated calibrated probability: {result.confidence*100:.1f}%."
        )
        st.sidebar.success(f"Analysis Complete: {result.predicted_label}")
        st.sidebar.download_button(
            label="📥 Download Clinical PDF Report",
            data=pdf_bytes,
            file_name=f"clinical_report_{patient_id}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.sidebar.error(f"Inference error: {str(e)}")

components.html(final_html, height=2250, scrolling=True)

# Mandatory Medical Disclaimer Footer (Law #4)
st.divider()
st.warning(MANDATORY_MEDICAL_DISCLAIMER)
