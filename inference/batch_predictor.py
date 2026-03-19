"""Batch prediction interface for efficient inference on multiple samples.

Provides optimized batch processing with progress tracking and error handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import polars as pl
from tqdm import tqdm

from inference.predictor import MaterialPredictor, PredictionResult, FEATURE_NAMES
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BatchPredictionResult:
    """Results from batch prediction.
    
    Attributes:
        predictions: List of PredictionResult objects.
        errors: List of (index, error_message) tuples for failed predictions.
        success_rate: Fraction of successful predictions.
        total_samples: Total number of samples processed.
    """
    
    predictions: list[PredictionResult]
    errors: list[tuple[int, str]]
    success_rate: float
    total_samples: int


class BatchPredictor:
    """Efficient batch prediction interface."""
    
    def __init__(self, models_dir: str = "models/saved"):
        """Initialize batch predictor.
        
        Args:
            models_dir: Directory containing trained models.
        """
        self.predictor = MaterialPredictor(models_dir=models_dir)
        logger.info("BatchPredictor initialized")
    
    def predict_dataframe(
        self,
        df: pl.DataFrame,
        show_progress: bool = True,
        continue_on_error: bool = True,
    ) -> BatchPredictionResult:
        """Predict on a Polars DataFrame.
        
        Args:
            df: DataFrame with feature columns.
            show_progress: Whether to show progress bar.
            continue_on_error: Whether to continue on individual prediction errors.
            
        Returns:
            BatchPredictionResult with all predictions and errors.
        """
        predictions: list[PredictionResult] = []
        errors: list[tuple[int, str]] = []
        
        # Validate columns
        missing_cols = [col for col in FEATURE_NAMES if col not in df.columns]
        if missing_cols:
            raise ValueError(f"DataFrame missing required columns: {missing_cols}")
        
        iterator = tqdm(range(len(df)), desc="Predicting") if show_progress else range(len(df))
        
        for i in iterator:
            try:
                row = df.row(i, named=True)
                input_dict = {col: row[col] for col in FEATURE_NAMES}
                result = self.predictor.predict(input_dict)
                predictions.append(result)
            except Exception as e:
                error_msg = str(e)
                errors.append((i, error_msg))
                logger.warning(f"Prediction failed for row {i}: {error_msg}")
                
                if not continue_on_error:
                    raise
        
        success_rate = len(predictions) / len(df) if len(df) > 0 else 0.0
        
        logger.info(
            f"Batch prediction complete: {len(predictions)}/{len(df)} successful "
            f"({success_rate:.1%})"
        )
        
        return BatchPredictionResult(
            predictions=predictions,
            errors=errors,
            success_rate=success_rate,
            total_samples=len(df),
        )
    
    def predict_csv(
        self,
        csv_path: str,
        output_path: Optional[str] = None,
        show_progress: bool = True,
    ) -> BatchPredictionResult:
        """Predict on a CSV file.
        
        Args:
            csv_path: Path to input CSV file.
            output_path: Optional path to save predictions CSV.
            show_progress: Whether to show progress bar.
            
        Returns:
            BatchPredictionResult with all predictions.
        """
        logger.info(f"Loading data from {csv_path}")
        df = pl.read_csv(csv_path)
        
        result = self.predict_dataframe(df, show_progress=show_progress)
        
        if output_path is not None:
            self.save_predictions(result, output_path)
        
        return result
    
    def save_predictions(
        self,
        result: BatchPredictionResult,
        output_path: str,
    ) -> None:
        """Save predictions to CSV file.
        
        Args:
            result: BatchPredictionResult to save.
            output_path: Path to output CSV file.
        """
        # Create DataFrame from predictions
        data = {
            "yield_strength_MPa": [p.yield_strength_MPa for p in result.predictions],
            "uts_MPa": [p.uts_MPa for p in result.predictions],
            "elongation_pct": [p.elongation_pct for p in result.predictions],
        }
        
        # Add stress-strain curves
        for i in range(result.predictions[0].n_curve_points):
            data[f"strain_{i:03d}"] = [p.strain[i] for p in result.predictions]
            data[f"stress_{i:03d}"] = [p.stress[i] for p in result.predictions]
        
        df = pl.DataFrame(data)
        df.write_csv(output_path)
        
        logger.info(f"Predictions saved to {output_path}")
    
    def predict_batch_optimized(
        self,
        X: np.ndarray,
        batch_size: int = 32,
        show_progress: bool = True,
    ) -> list[PredictionResult]:
        """Optimized batch prediction using vectorized operations.
        
        Args:
            X: Feature array of shape (N, n_features).
            batch_size: Batch size for processing.
            show_progress: Whether to show progress bar.
            
        Returns:
            List of PredictionResult objects.
        """
        n_samples = X.shape[0]
        predictions: list[PredictionResult] = []
        
        iterator = range(0, n_samples, batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="Batch prediction", total=(n_samples + batch_size - 1) // batch_size)
        
        for start_idx in iterator:
            end_idx = min(start_idx + batch_size, n_samples)
            batch_X = X[start_idx:end_idx]
            
            # Process batch
            for i in range(len(batch_X)):
                input_dict = {
                    name: float(batch_X[i, j])
                    for j, name in enumerate(FEATURE_NAMES)
                }
                result = self.predictor.predict(input_dict)
                predictions.append(result)
        
        return predictions
