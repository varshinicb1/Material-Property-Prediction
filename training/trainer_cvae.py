"""Training loop for Conditional VAE stress-strain curve generation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, TensorDataset

from models.cvae import CVAE
from training.losses import CVAELoss
from utils.logging import get_logger

logger = get_logger(__name__)


def _make_loader(
    X: np.ndarray,
    y_stress: np.ndarray,
    batch_size: int,
    shuffle: bool = True,
) -> DataLoader:
    dataset = TensorDataset(
        torch.from_numpy(X).float(),
        torch.from_numpy(y_stress).float(),
    )
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )


class CVAETrainer:
    """Trains the Conditional VAE for stress-strain curve generation.

    Uses beta-VAE loss with KL annealing and physics-aware regularization.

    Attributes:
        model: CVAE instance.
        device: Computation device.
    """

    def __init__(
        self,
        model: CVAE,
        device: Optional[torch.device] = None,
    ) -> None:
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model = model.to(self.device)
        self.best_val_loss = float("inf")
        self.best_state: Optional[dict] = None

    def train(
        self,
        X_train: np.ndarray,
        y_stress_train: np.ndarray,
        X_val: np.ndarray,
        y_stress_val: np.ndarray,
        epochs: int = 150,
        batch_size: int = 64,
        learning_rate: float = 1e-3,
        beta: float = 1.0,
        kl_warmup_epochs: int = 20,
        physics_weight: float = 0.1,
        smoothness_weight: float = 0.05,
        patience: int = 30,
        save_path: Optional[Path] = None,
    ) -> dict[str, list[float]]:
        """Run CVAE training loop with KL annealing.

        Args:
            X_train: Training features (scaled), shape (N, F).
            y_stress_train: Training stress curves (scaled), shape (N, C).
            X_val: Validation features.
            y_stress_val: Validation stress curves.
            epochs: Maximum epochs.
            batch_size: Batch size.
            learning_rate: Initial learning rate.
            beta: Beta weight for KL divergence.
            kl_warmup_epochs: Epochs over which KL weight is annealed from 0 to 1.
            physics_weight: Physics constraint loss weight.
            smoothness_weight: Curve smoothness penalty weight.
            patience: Early stopping patience.
            save_path: Path to save best model.

        Returns:
            Training history dictionary.
        """
        train_loader = _make_loader(X_train, y_stress_train, batch_size, shuffle=True)
        val_loader = _make_loader(X_val, y_stress_val, batch_size, shuffle=False)

        optimizer = AdamW(self.model.parameters(), lr=learning_rate, weight_decay=1e-4)
        scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=10, min_lr=1e-6)
        criterion = CVAELoss(
            beta=beta,
            physics_weight=physics_weight,
            smoothness_weight=smoothness_weight,
        )

        history: dict[str, list[float]] = {
            "train_loss": [],
            "val_loss": [],
            "recon_loss": [],
            "kl_loss": [],
        }
        no_improve = 0

        for epoch in range(1, epochs + 1):
            # KL annealing: linearly increase from 0 to 1 over warmup_epochs
            kl_weight = min(1.0, epoch / max(1, kl_warmup_epochs))

            # ── Training ──────────────────────────────────────────────────
            self.model.train()
            train_metrics: dict[str, list[float]] = {
                "total": [], "recon": [], "kl": []
            }
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)

                optimizer.zero_grad(set_to_none=True)
                recon, mu, log_var = self.model(y_batch, X_batch)
                loss_dict = criterion(recon, y_batch, mu, log_var, annealing_weight=kl_weight)
                loss_dict["total"].backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()

                for k in ["total", "recon", "kl"]:
                    train_metrics[k].append(loss_dict[k].item())

            train_total = float(np.mean(train_metrics["total"]))
            train_recon = float(np.mean(train_metrics["recon"]))
            train_kl = float(np.mean(train_metrics["kl"]))

            # ── Validation ────────────────────────────────────────────────
            self.model.eval()
            val_losses: list[float] = []
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    recon, mu, log_var = self.model(y_batch, X_batch)
                    loss_dict = criterion(recon, y_batch, mu, log_var, annealing_weight=1.0)
                    val_losses.append(loss_dict["total"].item())
            val_loss = float(np.mean(val_losses))

            scheduler.step(val_loss)

            history["train_loss"].append(train_total)
            history["val_loss"].append(val_loss)
            history["recon_loss"].append(train_recon)
            history["kl_loss"].append(train_kl)

            if epoch % 10 == 0 or epoch == 1:
                logger.info(
                    f"[cvae] Epoch {epoch:4d}/{epochs} | "
                    f"Train: {train_total:.5f} (recon={train_recon:.4f}, kl={train_kl:.4f}) | "
                    f"Val: {val_loss:.5f} | KL_w: {kl_weight:.3f}"
                )

            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                no_improve = 0
                if save_path is not None:
                    self.model.save(save_path)
            else:
                no_improve += 1
                if no_improve >= patience:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break

        if self.best_state is not None:
            self.model.load_state_dict(self.best_state)
        self.model.eval()
        logger.info(f"[green]CVAE training complete. Best val loss: {self.best_val_loss:.5f}[/green]")
        return history

    def generate_curves(
        self,
        X: np.ndarray,
        n_samples: int = 1,
        batch_size: int = 256,
    ) -> np.ndarray:
        """Generate stress-strain curves for input features.

        Args:
            X: Input features (scaled), shape (N, F).
            n_samples: Stochastic samples per input.
            batch_size: Inference batch size.

        Returns:
            Generated curves, shape (N, C) if n_samples==1 else (N, n_samples, C).
        """
        self.model.eval()
        all_curves: list[np.ndarray] = []

        for start in range(0, len(X), batch_size):
            X_batch = torch.from_numpy(X[start : start + batch_size]).float().to(self.device)
            curves = self.model.generate(X_batch, n_samples=n_samples)
            all_curves.append(curves.cpu().numpy())

        result = np.vstack(all_curves)
        return result.astype(np.float32)
