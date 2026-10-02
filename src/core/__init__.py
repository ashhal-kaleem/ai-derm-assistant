# Core cross-cutting configuration & re-exports
from src.core.config import Settings, get_settings
from src.core.exceptions import (
    DermAssistException,
    ModelInferenceError,
    InvalidImageError,
    ResourceNotFoundError,
    register_exception_handlers,
)

# Backward-compatibility aliases for domain & infrastructure
from src.domain.calibration import (
    compute_ece,
    optimize_temperature,
    apply_temperature_scaling,
)
from src.domain.dataset import create_patient_aware_split, verify_zero_patient_leakage
from src.infrastructure.onnx_engine import ONNXInferenceEngine
from src.infrastructure.explainability import generate_gradcam_overlay, image_to_png_bytes
