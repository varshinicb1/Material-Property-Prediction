"""Training loop for FT-Transformer deep learning model."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
from torch.utils.data import DataLoader, TensorDataset

from models.ft_transformer import FTTransformer
from training.losses import DeepRegressionLoss
from utils.logging import get_logger

logger = get_logger(__name__)


def _make_loader(
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    shuffle: bool = True,
) -> DataLoader:
    dataset = TensorDataset(
        torch.from_numpy(X).float(),
        torch.from_numpy(y).float(),
    )
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )


class DeepTrainer:
    """Trains the FT-Transformer model with early stopping.

    Attributes:
        model: FTTransformer instance.
        device: torch.device to use.
        best_val_loss: Best validation loss seen so far.
    """

    def __init__(
        self,
        model: FTTransformer,
        device: Optional[torch.device] = None,
        use_compile: bool = False,
    ) -> None:
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model = model.to(self.device)
        if use_compile:
            try:
                self.model = torch.compile(self.model)
                logger.info("torch.compile enabled for FT-Transformer")
            except Exception as e:
                logger.warning(f"torch.compile failed: {e}")
        self.best_val_loss = float("inf")
        self.best_state: Optional[dict] = None

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = 100,
        batch_size: int = 64,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        warmup_epochs: int = 5,
        patience: int = 20,
        gradient_clip: float = 1.0,
        physics_weight: float = 0.1,
        save_path: Optional[Path] = None,
    ) -> dict[str, list[float]]:
        """Run full training loop.

        Args:
            X_train: Training features array.
            y_train: Training targets array (scaled).
            X_val: Validation features array.
            y_val: Validation targets array (scaled).
            epochs: Maximum training epochs.
            batch_size: Mini-batch size.
            learning_rate: Peak learning rate.
            weight_decay: AdamW weight decay.
            warmup_epochs: Linear warmup duration.
            patience: Early stopping patience.
            gradient_clip: Max gradient norm.
            physics_weight: Weight for physics constraint loss.
            save_path: Optional path to save best model.

        Returns:
            History dict with 'train_loss' and 'val_loss' lists.
        """
        train_loader = _make_loader(X_train, y_train, batch_size, shuffle=True)
        val_loader = _make_loader(X_val, y_val, batch_size, shuffle=False)

        optimizer = AdamW(self.model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        criterion = DeepRegressionLoss(physics_weight=physics_weight)

        warmup_scheduler = LinearLR(optimizer, start_factor=0.1, total_iters=warmup_epochs)
        cosine_scheduler = CosineAnnealingLR(optimizer, T_max=epochs - warmup_epochs, eta_min=1e-6)
        scheduler = SequentialLR(
            optimizer, schedulers=[warmup_scheduler, cosine_scheduler], milestones=[warmup_epochs]
        )

        history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}
        no_improve = 0

        for epoch in range(1, epochs + 1):
            # ── Training ──────────────────────────────────────────────────
            self.model.train()
            train_losses: list[float] = []
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                optimizer.zero_grad(set_to_none=True)
                pred = self.model(X_batch)
                loss_dict = criterion(pred, y_batch)
                loss_dict["total"].backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), gradient_clip)
                optimizer.step()
                train_losses.append(loss_dict["total"].item())

            scheduler.step()
            train_loss = float(np.mean(train_losses))

            # ── Validation ────────────────────────────────────────────────
            self.model.eval()
            val_losses: list[float] = []
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    pred = self.model(X_batch)
                    loss_dict = criterion(pred, y_batch)
                    val_losses.append(loss_dict["total"].item())
            val_loss = float(np.mean(val_losses))

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)

            if epoch % 10 == 0 or epoch == 1:
                logger.info(
                    f"[deep] Epoch {epoch:4d}/{epochs} | "
                    f"Train: {train_loss:.5f} | Val: {val_loss:.5f} | "
                    f"LR: {scheduler.get_last_lr()[0]:.6f}"
                )

            # ── Early stopping ────────────────────────────────────────────
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                no_improve = 0
                if save_path is not None:
                    self.model.save(save_path)
            else:
                no_improve += 1
                if no_improve >= patience:
                    logger.info(f"Early stopping at epoch {epoch} (patience={patience})")
                    break

        # Restore best weights
        if self.best_state is not None:
            self.model.load_state_dict(self.best_state)
        self.model.eval()
        logger.info(f"[green]Deep training complete. Best val loss: {self.best_val_loss:.5f}[/green]")
        return history

    def predict(self, X: np.ndarray, batch_size: int = 256) -> np.ndarray:
        """Run inference on the trained model.

        Args:
            X: Feature array (scaled), shape (N, F).
            batch_size: Inference batch size.

        Returns:
            Prediction array, shape (N, n_targets).
        """
        self.model.eval()
        loader = _make_loader(X, np.zeros((len(X), 1)), batch_size, shuffle=False)
        preds: list[np.ndarray] = []
        with torch.no_grad():
            for X_batch, _ in loader:
                X_batch = X_batch.to(self.device)
                out = self.model(X_batch).cpu().numpy()
                preds.append(out)
        return np.vstack(preds).astype(np.float32)
