"""LightGBM gradient boosting models for scalar material property prediction."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import lightgbm as lgb
import numpy as np
from sklearn.multioutput import MultiOutputRegressor

from utils.io import save_pickle, load_pickle
from utils.logging import get_logger

logger = get_logger(__name__)


class GBMEnsemble:
    """Multi-output LightGBM ensemble for scalar property prediction.

    Trains three separate LightGBM regressors (one per target: yield strength,
    UTS, elongation) with early stopping and feature importance tracking.

    Attributes:
        models: Dictionary mapping target name to fitted LGB model.
        feature_importance: Dictionary mapping target name to importance array.
        feature_names: List of input feature names.
    """

    def __init__(
        self,
        n_estimators: int = 500,
        learning_rate: float = 0.05,
        max_depth: int = 7,
        num_leaves: int = 63,
        min_child_samples: int = 20,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.1,
        reg_lambda: float = 0.1,
        n_jobs: int = -1,
        early_stopping_rounds: int = 50,
        verbose: int = -1,
        random_state: int = 42,
    ) -> None:
        """Initialize GBM configuration.

        Args:
            n_estimators: Number of boosting rounds.
            learning_rate: Shrinkage rate.
            max_depth: Maximum tree depth.
            num_leaves: Maximum number of leaves per tree.
            min_child_samples: Minimum samples per leaf.
            subsample: Row subsampling ratio.
            colsample_bytree: Column subsampling ratio.
            reg_alpha: L1 regularization.
            reg_lambda: L2 regularization.
            n_jobs: Number of parallel threads.
            early_stopping_rounds: Rounds for early stopping.
            verbose: Verbosity level.
            random_state: Random seed.
        """
        self.params = {
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "num_leaves": num_leaves,
            "min_child_samples": min_child_samples,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "n_jobs": n_jobs,
            "verbose": verbose,
            "random_state": random_state,
            "objective": "regression",
            "metric": "rmse",
        }
        self.early_stopping_rounds = early_stopping_rounds
        self.models: dict[str, lgb.LGBMRegressor] = {}
        self.feature_importance: dict[str, np.ndarray] = {}
        self.feature_names: list[str] = []
        self.target_names: list[str] = []

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: list[str],
        target_names: list[str],
    ) -> None:
        """Train individual LightGBM models per target.

        Args:
            X_train: Training features, shape (N, F).
            y_train: Training targets (raw scale), shape (N, 3).
            X_val: Validation features.
            y_val: Validation targets.
            feature_names: Feature column names.
            target_names: Target column names.
        """
        self.feature_names = feature_names
        self.target_names = target_names

        for i, tname in enumerate(target_names):
            logger.info(f"Training LightGBM for target: [cyan]{tname}[/cyan]")
            model = lgb.LGBMRegressor(**self.params)
            model.fit(
                X_train,
                y_train[:, i],
                eval_set=[(X_val, y_val[:, i])],
                callbacks=[
                    lgb.early_stopping(self.early_stopping_rounds, verbose=False),
                    lgb.log_evaluation(period=-1),
                ],
                feature_name=feature_names,
            )
            self.models[tname] = model
            self.feature_importance[tname] = model.feature_importances_
            logger.info(
                f"  Best iter: {model.best_iteration_}, "
                f"Val RMSE: {model.best_score_['valid_0']['rmse']:.4f}"
            )

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict scalar properties for input features.

        Args:
            X: Feature array, shape (N, F).

        Returns:
            Prediction array, shape (N, 3).
        """
        preds = []
        for tname in self.target_names:
            preds.append(self.models[tname].predict(X))
        return np.column_stack(preds).astype(np.float32)

    def get_feature_importance(self, target: Optional[str] = None) -> dict[str, np.ndarray]:
        """Return feature importances.

        Args:
            target: Specific target name, or None for all.

        Returns:
            Dictionary mapping target name to importance array.
        """
        if target is not None:
            return {target: self.feature_importance[target]}
        return self.feature_importance

    def save(self, path: Path) -> None:
        """Save the GBM ensemble.

        Args:
            path: Destination pickle path.
        """
        save_pickle(self, path)
        logger.info(f"GBM ensemble saved: {path}")

    @classmethod
    def load(cls, path: Path) -> "GBMEnsemble":
        """Load a saved GBM ensemble.

        Args:
            path: Source pickle path.

        Returns:
            Loaded GBMEnsemble instance.
        """
        obj = load_pickle(path)
        logger.info(f"GBM ensemble loaded: {path}")
        return obj
