"""SHAP-based global and local explainability for material property models.

Supports:
  - TreeExplainer for GBM models (fast, exact)
  - KernelExplainer / DeepExplainer for deep models (approximate)
  - Global feature importance bar charts
  - Local waterfall / force plots
  - Summary plots
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shap

from utils.logging import get_logger

logger = get_logger(__name__)


class GBMShapExplainer:
    """SHAP TreeExplainer for LightGBM GBMEnsemble.

    Attributes:
        explainers: Dict mapping target name to shap.TreeExplainer.
        feature_names: Input feature names.
    """

    def __init__(self, gbm_ensemble: Any, feature_names: list[str]) -> None:
        """Initialize TreeExplainers for each sub-model.

        Args:
            gbm_ensemble: Fitted GBMEnsemble instance.
            feature_names: Input feature names.
        """
        self.feature_names = feature_names
        self.explainers: dict[str, shap.TreeExplainer] = {}
        self.target_names: list[str] = gbm_ensemble.target_names

        for tname in gbm_ensemble.target_names:
            self.explainers[tname] = shap.TreeExplainer(gbm_ensemble.models[tname])
            logger.debug(f"TreeExplainer created for: {tname}")

    def explain_global(
        self,
        X: np.ndarray,
        target: Optional[str] = None,
    ) -> dict[str, np.ndarray]:
        """Compute SHAP values for a dataset.

        Args:
            X: Feature array, shape (N, F).
            target: Specific target name, or None for all.

        Returns:
            Dictionary mapping target name to SHAP values array (N, F).
        """
        targets = [target] if target else self.target_names
        result: dict[str, np.ndarray] = {}
        for tname in targets:
            shap_vals = self.explainers[tname].shap_values(X)
            result[tname] = shap_vals
        return result

    def explain_local(self, x: np.ndarray, target: str) -> np.ndarray:
        """Compute SHAP values for a single sample.

        Args:
            x: Single sample, shape (1, F) or (F,).
            target: Target name.

        Returns:
            SHAP values array, shape (F,).
        """
        x = x.reshape(1, -1)
        shap_vals = self.explainers[target].shap_values(x)
        return shap_vals[0] if shap_vals.ndim == 2 else shap_vals

    def plot_global_importance(
        self,
        X: np.ndarray,
        target: str,
        top_k: int = 10,
        save_path: Optional[Path] = None,
    ) -> plt.Figure:
        """Plot global SHAP feature importance bar chart.

        Args:
            X: Feature array for SHAP computation.
            target: Target name to explain.
            top_k: Show top-k features.
            save_path: Optional path to save figure.

        Returns:
            Matplotlib figure.
        """
        shap_vals = self.explain_global(X, target)[target]
        mean_abs_shap = np.abs(shap_vals).mean(axis=0)
        sorted_idx = np.argsort(mean_abs_shap)[::-1][:top_k]
        top_features = [self.feature_names[i] for i in sorted_idx]
        top_importance = mean_abs_shap[sorted_idx]

        fig, ax = plt.subplots(figsize=(10, 6))
        colors = plt.cm.viridis(np.linspace(0.2, 0.8, top_k))
        bars = ax.barh(range(top_k), top_importance[::-1], color=colors[::-1])
        ax.set_yticks(range(top_k))
        ax.set_yticklabels(top_features[::-1], fontsize=11)
        ax.set_xlabel("Mean |SHAP Value|", fontsize=12)
        ax.set_title(f"Global Feature Importance — {target}", fontsize=14, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"Global importance plot saved: {save_path}")
        return fig

    def plot_local_waterfall(
        self,
        x: np.ndarray,
        target: str,
        save_path: Optional[Path] = None,
    ) -> plt.Figure:
        """Plot local SHAP waterfall explanation for a single sample.

        Args:
            x: Single feature vector, shape (F,).
            target: Target name.
            save_path: Optional save path.

        Returns:
            Matplotlib figure.
        """
        x = x.reshape(1, -1)
        explainer = self.explainers[target]
        expected_val = float(explainer.expected_value)
        shap_vals = self.explain_local(x, target)

        # Sort by absolute contribution
        sorted_idx = np.argsort(np.abs(shap_vals))[::-1][:12]
        features = [self.feature_names[i] for i in sorted_idx]
        values = shap_vals[sorted_idx]
        feature_values = x[0, sorted_idx]

        fig, ax = plt.subplots(figsize=(10, 7))
        colors = ["#e74c3c" if v > 0 else "#3498db" for v in values]
        labels = [f"{f}={v:.3g}" for f, v in zip(features, feature_values)]
        ax.barh(range(len(values)), values, color=colors)
        ax.set_yticks(range(len(values)))
        ax.set_yticklabels(labels, fontsize=10)
        ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
        ax.set_xlabel("SHAP Value", fontsize=12)
        ax.set_title(
            f"Local Explanation — {target}\n(Base value: {expected_val:.2f})",
            fontsize=13,
            fontweight="bold",
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        return fig

    def get_local_shap_dict(
        self,
        x: np.ndarray,
        target: str,
    ) -> dict[str, float]:
        """Return SHAP values as a feature-name → value dictionary.

        Args:
            x: Single feature vector, shape (F,).
            target: Target name.

        Returns:
            Dictionary mapping feature name to SHAP value.
        """
        shap_vals = self.explain_local(x.reshape(1, -1), target)
        return {name: float(val) for name, val in zip(self.feature_names, shap_vals)}
