"""Material AI: Machine Learning for TIG Welded Aerospace Material Property Prediction.

This package provides:
- Ensemble ML models (LightGBM, FT-Transformer, CVAE)
- Material property prediction (Yield, UTS, Elongation)
- SHAP explainability
- REST API and GUI interfaces
- Batch prediction capabilities
"""

__version__ = "1.0.0"
__author__ = "Varshini CB"

from inference.predictor import MaterialPredictor
from inference.batch_predictor import BatchPredictor

__all__ = [
    "MaterialPredictor",
    "BatchPredictor",
]
