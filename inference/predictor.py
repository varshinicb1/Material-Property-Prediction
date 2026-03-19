"""Unified inference interface for all trained models.

Loads GBM, FT-Transformer, and CVAE from disk and provides a single
predict() call that returns scalar properties + stress-strain curves
with ensemble averaging.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch

from data.generator import get_feature_columns
from data.preprocessor import DataPreprocessor
from models.gbm import GBMEnsemble
from models.ft_transformer import FTTransformer
from models.cvae import CVAE
from utils.logging import get_logger
from utils.monitoring import get_metrics_tracker

logger = get_logger(__name__)

FEATURE_NAMES = get_feature_columns(50)["features"]


@dataclass
class PredictionResult:
    """Container for a single prediction result.

    Attributes:
        yield_strength_MPa: Predicted yield strength.
        uts_MPa: Predicted ultimate tensile strength.
        elongation_pct: Predicted elongation percentage.
        strain: Strain axis for stress-strain curve.
        stress: Predicted stress-strain curve.
        gbm_pred: Raw GBM scalar predictions.
        deep_pred: Raw deep model scalar predictions.
        ensemble_pred: Weighted ensemble scalar predictions.
        n_curve_points: Number of points in stress-strain curve.
    """

    yield_strength_MPa: float
    uts_MPa: float
    elongation_pct: float
    strain: np.ndarray
    stress: np.ndarray
    gbm_pred: np.ndarray
    deep_pred: np.ndarray
    ensemble_pred: np.ndarray
    n_curve_points: int = 50


class MaterialPredictor:
    """Loads all trained models and runs ensemble inference.

    Attributes:
        gbm: Fitted GBMEnsemble.
        ft_model: Fitted FTTransformer.
        cvae: Fitted CVAE.
        preprocessor: Fitted DataPreprocessor.
        device: Torch inference device.
    """

    def __init__(self, models_dir: str = "models/saved") -> None:
        """Load all trained models from directory.

        Args:
            models_dir: Directory containing saved model files.
            
        Raises:
            FileNotFoundError: If required model files are missing.
            RuntimeError: If model loading fails.
        """
        mdir = Path(models_dir)
        
        # Validate directory exists
        if not mdir.exists():
            raise FileNotFoundError(f"Models directory not found: {mdir}")
        
        # Check all required files exist
        required_files = {
            "preprocessor.pkl": "Preprocessor",
            "gbm.pkl": "GBM model",
            "ft_transformer.pt": "FT-Transformer",
            "cvae.pt": "CVAE model"
        }
        
        missing = []
        for fname, desc in required_files.items():
            if not (mdir / fname).exists():
                missing.append(f"{desc} ({fname})")
        
        if missing:
            raise FileNotFoundError(
                f"Missing required model files: {', '.join(missing)}. "
                "Run 'python main.py train' first."
            )
        
        try:
            # Setup device with error handling
            if torch.cuda.is_available():
                try:
                    self.device = torch.device("cuda")
                    # Test CUDA availability
                    torch.zeros(1).to(self.device)
                except RuntimeError:
                    logger.warning("CUDA available but failed to initialize, falling back to CPU")
                    self.device = torch.device("cpu")
            else:
                self.device = torch.device("cpu")
            
            self.n_stress_points = 50
            self.n_features = len(FEATURE_NAMES)

            logger.info(f"Loading models from: {mdir} (device: {self.device})")

            # Load preprocessor
            self.preprocessor: DataPreprocessor = DataPreprocessor.load(mdir / "preprocessor.pkl")
            logger.info("✓ Preprocessor loaded")

            # Load GBM
            self.gbm: GBMEnsemble = GBMEnsemble.load(mdir / "gbm.pkl")
            logger.info("✓ GBM loaded")

            # Load FT-Transformer
            ft_path = mdir / "ft_transformer.pt"
            self.ft_model = FTTransformer(
                n_features=self.n_features,
                n_targets=3,
                d_token=192,
                n_blocks=3,
                attention_n_heads=8,
                attention_dropout=0.2,
                ffn_d_hidden=256,
                ffn_dropout=0.1,
            )
            ckpt = torch.load(ft_path, map_location="cpu", weights_only=True)
            self.ft_model.load_state_dict(ckpt["state_dict"])
            self.ft_model.eval().to(self.device)
            logger.info("✓ FT-Transformer loaded")

            # Load CVAE
            cvae_path = mdir / "cvae.pt"
            self.cvae = CVAE(
                n_features=self.n_features,
                curve_dim=self.n_stress_points,
                latent_dim=32,
                condition_dim=64,
                encoder_hidden=[256, 128],
                decoder_hidden=[128, 256],
            )
            cvae_ckpt = torch.load(cvae_path, map_location="cpu", weights_only=True)
            self.cvae.load_state_dict(cvae_ckpt["state_dict"])
            self.cvae.eval().to(self.device)
            logger.info("✓ CVAE loaded")

            logger.info("[green]All models loaded successfully.[/green]")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load models: {e}") from e

    def predict(
        self,
        input_dict: dict[str, float],
        gbm_weight: float = 0.45,
        deep_weight: float = 0.55,
        n_curve_samples: int = 5,
        track_metrics: bool = True,
    ) -> PredictionResult:
        """Run ensemble inference for a single sample.

        Args:
            input_dict: Dictionary mapping feature names to float values.
                Required keys match FEATURE_NAMES.
            gbm_weight: Weight for GBM predictions in ensemble.
            deep_weight: Weight for deep model predictions in ensemble.
            n_curve_samples: Number of CVAE samples for curve uncertainty.
            track_metrics: Whether to track prediction metrics.

        Returns:
            PredictionResult with all predicted quantities.
            
        Raises:
            ValueError: If input validation fails.
        """
        start_time = time.time()
        error_msg = None
        
        try:
            # Validate input dictionary
            missing_keys = [k for k in FEATURE_NAMES if k not in input_dict]
            if missing_keys:
                raise ValueError(f"Missing required features: {missing_keys}")
            
            # Validate ensemble weights
            if not np.isclose(gbm_weight + deep_weight, 1.0):
                raise ValueError(f"Ensemble weights must sum to 1.0, got {gbm_weight + deep_weight}")
            
            # Build raw feature vector
            X_raw = np.array(
                [[input_dict[fn] for fn in FEATURE_NAMES]], dtype=np.float32
            )
            
            # Check for NaN/Inf in inputs
            if not np.all(np.isfinite(X_raw)):
                raise ValueError("Input features contain NaN or Inf values")

            # Scale features
            X_scaled = self.preprocessor.transform_input(X_raw)

            # GBM prediction (raw scale)
            gbm_pred = self.gbm.predict(X_raw)[0]  # shape (3,)

            # Deep model prediction (scaled → inverse)
            with torch.no_grad():
                x_t = torch.from_numpy(X_scaled).float().to(self.device)
                deep_scaled = self.ft_model(x_t).cpu().numpy()  # shape (1, 3)
            deep_pred = self.preprocessor.inverse_scalar_targets(deep_scaled)[0]  # shape (3,)

            # Ensemble scalar predictions
            ensemble_pred = gbm_weight * gbm_pred + deep_weight * deep_pred

            # Enforce physics: yield < UTS
            ensemble_pred[0] = min(ensemble_pred[0], ensemble_pred[1] * 0.97)
            ensemble_pred[1] = max(ensemble_pred[1], ensemble_pred[0] * 1.03)
            ensemble_pred[2] = float(np.clip(ensemble_pred[2], 1.0, 40.0))

            # CVAE curve generation (average over samples)
            curves_scaled = []
            with torch.no_grad():
                for _ in range(n_curve_samples):
                    z = torch.randn(1, self.cvae.latent_dim, device=self.device)
                    cond = self.cvae.condition_encoder(x_t)
                    c = self.cvae.decoder(z, cond).cpu().numpy()  # (1, C)
                    curves_scaled.append(c)
            mean_curve_scaled = np.mean(curves_scaled, axis=0)  # (1, C)
            stress_pred = self.preprocessor.inverse_stress(mean_curve_scaled)[0]  # (C,)

            # Generate strain axis from elongation
            elong_frac = float(ensemble_pred[2]) / 100.0
            strain_axis = np.linspace(0.0, elong_frac * 1.05, self.n_stress_points)

            # Post-process: ensure physical plausibility of curve
            stress_pred = np.clip(stress_pred, 0.0, float(ensemble_pred[1]) * 1.1)
            stress_pred[0] = 0.0  # Start at zero

            result = PredictionResult(
                yield_strength_MPa=float(ensemble_pred[0]),
                uts_MPa=float(ensemble_pred[1]),
                elongation_pct=float(ensemble_pred[2]),
                strain=strain_axis,
                stress=stress_pred,
                gbm_pred=gbm_pred,
                deep_pred=deep_pred,
                ensemble_pred=ensemble_pred,
                n_curve_points=self.n_stress_points,
            )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            # Track metrics
            if track_metrics:
                latency_ms = (time.time() - start_time) * 1000
                predictions_dict = {}
                
                if error_msg is None:
                    predictions_dict = {
                        "yield_strength_MPa": result.yield_strength_MPa,
                        "uts_MPa": result.uts_MPa,
                        "elongation_pct": result.elongation_pct,
                    }
                
                tracker = get_metrics_tracker()
                tracker.record_prediction(
                    latency_ms=latency_ms,
                    input_features=input_dict,
                    predictions=predictions_dict,
                    error=error_msg,
                )

    @staticmethod
    def build_input(
        current_A: float = 150.0,
        voltage_V: float = 15.0,
        speed_mm_per_min: float = 150.0,
        filler_C: float = 0.03,
        filler_Mn: float = 1.0,
        filler_Si: float = 0.4,
        filler_Cr: float = 18.0,
        filler_Ni: float = 10.0,
        filler_Mo: float = 2.0,
        filler_Ti: float = 0.1,
        haz_width_mm: float = 1.2,
        haz_peak_temp_C: float = 1000.0,
        haz_cooling_rate: float = 200.0,
        grain_size_um: float = 20.0,
        repair_stage: int = 0,
    ) -> dict[str, float]:
        """Build a feature dictionary from individual parameters.

        Args:
            current_A: Welding current in Amperes.
            voltage_V: Arc voltage in Volts.
            speed_mm_per_min: Travel speed in mm/min.
            filler_C: Carbon content in filler (wt%).
            filler_Mn: Manganese content (wt%).
            filler_Si: Silicon content (wt%).
            filler_Cr: Chromium content (wt%).
            filler_Ni: Nickel content (wt%).
            filler_Mo: Molybdenum content (wt%).
            filler_Ti: Titanium content (wt%).
            haz_width_mm: HAZ width in mm.
            haz_peak_temp_C: Peak HAZ temperature in Celsius.
            haz_cooling_rate: HAZ cooling rate in C/s.
            grain_size_um: Average grain size in micrometers.
            repair_stage: Repair stage (0=R0, 1=R1, 2=R2, 3=R3).

        Returns:
            Feature dictionary compatible with predict().
        """
        heat_input = (current_A * voltage_V * 60.0) / (1000.0 * speed_mm_per_min)
        return {
            "current_A": current_A,
            "voltage_V": voltage_V,
            "speed_mm_per_min": speed_mm_per_min,
            "heat_input_kJ_per_mm": heat_input,
            "filler_C": filler_C,
            "filler_Mn": filler_Mn,
            "filler_Si": filler_Si,
            "filler_Cr": filler_Cr,
            "filler_Ni": filler_Ni,
            "filler_Mo": filler_Mo,
            "filler_Ti": filler_Ti,
            "haz_width_mm": haz_width_mm,
            "haz_peak_temp_C": haz_peak_temp_C,
            "haz_cooling_rate": haz_cooling_rate,
            "grain_size_um": grain_size_um,
            "repair_stage": float(repair_stage),
        }
