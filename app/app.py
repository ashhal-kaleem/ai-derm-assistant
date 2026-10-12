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

# Mandatory Medical Disclaimer Footer (Law #4)
st.divider()
st.warning(MANDATORY_MEDICAL_DISCLAIMER)
