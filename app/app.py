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

# Service Header
st.markdown('<div class="main-header">🔬 DermAssist AI — Clinical Inference Gateway</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Production Headless REST API Gateway & Mobile Inference Service (v2.0.0)</div>', unsafe_allow_html=True)

# Status Cards Row
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Inference Runtime", value="EfficientNet-B4", delta="ONNX CPU Loaded")
with col2:
    st.metric(label="Confidence Calibration", value="Temperature Scaled", delta="T* = 1.25")
with col3:
    st.metric(label="Clinical Advisory", value="Groq LPU Llama-3.3", delta="Operational")

st.divider()

# Registered Endpoints Directory
st.subheader("📡 Registered Production Endpoints")
endpoints_data = [
    {"Method": "POST", "Path": "/predict", "Description": "Dual-Output Inference + Grad-CAM Saliency Extraction (380x380)", "Status": "🟢 Operational"},
    {"Method": "POST", "Path": "/report", "Description": "Doctor-Ready Vector PDF Report Generation (ReportLab)", "Status": "🟢 Operational"},
    {"Method": "POST", "Path": "/history", "Description": "Longitudinal Lesion Visit Tracking & Baseline Record", "Status": "🟢 Operational"},
    {"Method": "GET", "Path": "/history/{id}", "Description": "Longitudinal Visit Timeline Retrieval", "Status": "🟢 Operational"},
    {"Method": "GET", "Path": "/clinics", "Description": "Dermatologist Geolocation Lookup (OpenStreetMap / Overpass)", "Status": "🟢 Operational"},
    {"Method": "GET", "Path": "/health", "Description": "Container Liveness & Readiness Probe (Model & Service Status)", "Status": "🟢 Operational"},
    {"Method": "GET", "Path": "/", "Description": "Canonical API Service Discovery Manifest (JSON)", "Status": "🟢 Operational"},
]
st.dataframe(pd.DataFrame(endpoints_data), use_container_width=True, hide_index=True)

st.divider()

# Quick Client Usage & Documentation
col_docs, col_curl = st.columns([1, 1])
with col_docs:
    st.subheader("📖 Interactive Documentation")
    st.markdown("Interactive OpenAPI / Swagger UI documentation is available for live testing and schema inspection:")
    st.markdown("🔗 **Swagger UI**: `/docs`")
    st.markdown("🔗 **ReDoc**: `/redoc`")
    st.markdown("🔗 **OpenAPI Schema**: `/openapi.json`")

with col_curl:
    st.subheader("💻 Quick Client Integration")
    st.code('''# Analyze skin lesion image via cURL
curl -X POST "https://<api-host>/predict" \\
     -F "file=@lesion_photo.jpg"
''', language="bash")

# Mandatory Medical Disclaimer Footer (Law #4)
st.divider()
st.markdown(f'<div class="disclaimer-box">{MANDATORY_MEDICAL_DISCLAIMER}</div>', unsafe_allow_html=True)
