"""Data preprocessing: scaling, splitting, and numpy conversion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import polars as pl
from sklearn.preprocessing import StandardScaler, MinMaxScaler

from data.generator import get_feature_columns
from utils.io import save_pickle, load_pickle
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessedData:
    """Container for preprocessed numpy arrays."""

    X_train: np.ndarray
    X_val: np.ndarray
    X_test: np.ndarray
    y_scalar_train: np.ndarray
    y_scalar_val: np.ndarray
    y_scalar_test: np.ndarray
    y_stress_train: np.ndarray
    y_stress_val: np.ndarray
    y_stress_test: np.ndarray
    y_strain_train: np.ndarray
    y_strain_val: np.ndarray
    y_strain_test: np.ndarray
    feature_names: list[str]
    target_names: list[str]
    n_features: int
    n_curve_points: int


class DataPreprocessor:
    """Fit and apply feature/target scalers for material property data.

    Attributes:
        feature_scaler: StandardScaler fitted on training features.
        target_scaler: StandardScaler fitted on scalar targets.
        stress_scaler: MinMaxScaler fitted on stress values.
        strain_scaler: MinMaxScaler fitted on strain values.
    """

    def __init__(self, n_stress_points: int = 50, scaler_type: str = "standard") -> None:
        """Initialize the preprocessor.

        Args:
            n_stress_points: Number of stress-strain curve points.
            scaler_type: 'standard' or 'minmax'.
        """
        self.n_stress_points = n_stress_points
        self.scaler_type = scaler_type
        ScalerCls = StandardScaler if scaler_type == "standard" else MinMaxScaler
        self.feature_scaler = ScalerCls()
        self.target_scaler = StandardScaler()
        self.stress_scaler = MinMaxScaler()
        self.strain_scaler = MinMaxScaler()
        self._fitted = False

        self.columns = get_feature_columns(n_stress_points)

    def fit_transform(
        self,
        train_df: pl.DataFrame,
        val_df: pl.DataFrame,
        test_df: pl.DataFrame,
    ) -> ProcessedData:
        """Fit scalers on train set and transform all splits.

        Args:
            train_df: Training split DataFrame.
            val_df: Validation split DataFrame.
            test_df: Test split DataFrame.

        Returns:
            ProcessedData container with all numpy arrays.
            
        Raises:
            ValueError: If DataFrames are invalid or contain NaN/Inf.
        """
        # Validate DataFrames
        if len(train_df) == 0:
            raise ValueError("Training DataFrame is empty")
        if len(val_df) == 0:
            raise ValueError("Validation DataFrame is empty")
        if len(test_df) == 0:
            raise ValueError("Test DataFrame is empty")
        
        feature_cols = self.columns["features"]
        scalar_cols = self.columns["scalar_targets"]
        strain_cols = self.columns["curve_strain"]
        stress_cols = self.columns["curve_stress"]
        
        # Validate columns exist
        for df_name, df in [("train", train_df), ("val", val_df), ("test", test_df)]:
            missing_features = [c for c in feature_cols if c not in df.columns]
            if missing_features:
                raise ValueError(f"{df_name} DataFrame missing features: {missing_features}")
            missing_targets = [c for c in scalar_cols if c not in df.columns]
            if missing_targets:
                raise ValueError(f"{df_name} DataFrame missing targets: {missing_targets}")

        X_train = train_df.select(feature_cols).to_numpy().astype(np.float32)
        X_val = val_df.select(feature_cols).to_numpy().astype(np.float32)
        X_test = test_df.select(feature_cols).to_numpy().astype(np.float32)
        
        # Check for NaN/Inf in features
        for name, X in [("train", X_train), ("val", X_val), ("test", X_test)]:
            if not np.all(np.isfinite(X)):
                raise ValueError(f"{name} features contain NaN or Inf values")

        y_s_train = train_df.select(scalar_cols).to_numpy().astype(np.float32)
        y_s_val = val_df.select(scalar_cols).to_numpy().astype(np.float32)
        y_s_test = test_df.select(scalar_cols).to_numpy().astype(np.float32)
        
        # Check for NaN/Inf in targets
        for name, y in [("train", y_s_train), ("val", y_s_val), ("test", y_s_test)]:
            if not np.all(np.isfinite(y)):
                raise ValueError(f"{name} scalar targets contain NaN or Inf values")

        y_stress_train = train_df.select(stress_cols).to_numpy().astype(np.float32)
        y_stress_val = val_df.select(stress_cols).to_numpy().astype(np.float32)
        y_stress_test = test_df.select(stress_cols).to_numpy().astype(np.float32)
        
        # Check stress curves
        for name, y in [("train", y_stress_train), ("val", y_stress_val), ("test", y_stress_test)]:
            if not np.all(np.isfinite(y)):
                raise ValueError(f"{name} stress curves contain NaN or Inf values")

        y_strain_train = train_df.select(strain_cols).to_numpy().astype(np.float32)
        y_strain_val = val_df.select(strain_cols).to_numpy().astype(np.float32)
        y_strain_test = test_df.select(strain_cols).to_numpy().astype(np.float32)
        
        # Check strain curves
        for name, y in [("train", y_strain_train), ("val", y_strain_val), ("test", y_strain_test)]:
            if not np.all(np.isfinite(y)):
                raise ValueError(f"{name} strain curves contain NaN or Inf values")

        # Fit on train, transform all
        X_train_s = self.feature_scaler.fit_transform(X_train).astype(np.float32)
        X_val_s = self.feature_scaler.transform(X_val).astype(np.float32)
        X_test_s = self.feature_scaler.transform(X_test).astype(np.float32)

        y_scalar_train_s = self.target_scaler.fit_transform(y_s_train).astype(np.float32)
        y_scalar_val_s = self.target_scaler.transform(y_s_val).astype(np.float32)
        y_scalar_test_s = self.target_scaler.transform(y_s_test).astype(np.float32)

        # Flatten stress for scaler fit
        stress_flat_train = y_stress_train.reshape(-1, 1)
        self.stress_scaler.fit(stress_flat_train)
        y_stress_train_s = self.stress_scaler.transform(
            y_stress_train.reshape(-1, 1)
        ).reshape(y_stress_train.shape).astype(np.float32)
        y_stress_val_s = self.stress_scaler.transform(
            y_stress_val.reshape(-1, 1)
        ).reshape(y_stress_val.shape).astype(np.float32)
        y_stress_test_s = self.stress_scaler.transform(
            y_stress_test.reshape(-1, 1)
        ).reshape(y_stress_test.shape).astype(np.float32)

        strain_flat_train = y_strain_train.reshape(-1, 1)
        self.strain_scaler.fit(strain_flat_train)
        y_strain_train_s = self.strain_scaler.transform(
            y_strain_train.reshape(-1, 1)
        ).reshape(y_strain_train.shape).astype(np.float32)
        y_strain_val_s = self.strain_scaler.transform(
            y_strain_val.reshape(-1, 1)
        ).reshape(y_strain_val.shape).astype(np.float32)
        y_strain_test_s = self.strain_scaler.transform(
            y_strain_test.reshape(-1, 1)
        ).reshape(y_strain_test.shape).astype(np.float32)

        self._fitted = True
        logger.info(
            f"[green]Preprocessor fitted: "
            f"X={X_train_s.shape}, y_scalar={y_scalar_train_s.shape}, "
            f"y_stress={y_stress_train_s.shape}[/green]"
        )

        return ProcessedData(
            X_train=X_train_s,
            X_val=X_val_s,
            X_test=X_test_s,
            y_scalar_train=y_scalar_train_s,
            y_scalar_val=y_scalar_val_s,
            y_scalar_test=y_scalar_test_s,
            y_stress_train=y_stress_train_s,
            y_stress_val=y_stress_val_s,
            y_stress_test=y_stress_test_s,
            y_strain_train=y_strain_train_s,
            y_strain_val=y_strain_val_s,
            y_strain_test=y_strain_test_s,
            feature_names=feature_cols,
            target_names=scalar_cols,
            n_features=X_train_s.shape[1],
            n_curve_points=self.n_stress_points,
        )

    def inverse_scalar_targets(self, y_scaled: np.ndarray) -> np.ndarray:
        """Inverse transform scaled scalar targets.

        Args:
            y_scaled: Scaled target array, shape (N, 3).

        Returns:
            Original-scale target array.
        """
        return self.target_scaler.inverse_transform(y_scaled).astype(np.float32)

    def inverse_stress(self, stress_scaled: np.ndarray) -> np.ndarray:
        """Inverse transform scaled stress values.

        Args:
            stress_scaled: Scaled stress array.

        Returns:
            Original-scale stress array.
        """
        orig_shape = stress_scaled.shape
        return self.stress_scaler.inverse_transform(
            stress_scaled.reshape(-1, 1)
        ).reshape(orig_shape).astype(np.float32)

    def inverse_strain(self, strain_scaled: np.ndarray) -> np.ndarray:
        """Inverse transform scaled strain values.

        Args:
            strain_scaled: Scaled strain array.

        Returns:
            Original-scale strain array.
        """
        orig_shape = strain_scaled.shape
        return self.strain_scaler.inverse_transform(
            strain_scaled.reshape(-1, 1)
        ).reshape(orig_shape).astype(np.float32)

    def transform_input(self, X: np.ndarray) -> np.ndarray:
        """Transform raw input features.

        Args:
            X: Raw feature array.

        Returns:
            Scaled feature array.
        """
        if not self._fitted:
            raise RuntimeError("Preprocessor must be fitted before transforming.")
        return self.feature_scaler.transform(X).astype(np.float32)

    def save(self, path: Path) -> None:
        """Serialize preprocessor to disk.

        Args:
            path: Destination file path.
        """
        save_pickle(self, path)
        logger.info(f"Preprocessor saved: {path}")

    @classmethod
    def load(cls, path: Path) -> "DataPreprocessor":
        """Load a serialized preprocessor.

        Args:
            path: Source file path.

        Returns:
            Loaded DataPreprocessor instance.
        """
        obj = load_pickle(path)
        logger.info(f"Preprocessor loaded: {path}")
        return obj
