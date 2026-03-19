"""Physics-aware loss functions for material property prediction.

Enforces:
  - Yield strength < UTS (physical monotonicity)
  - Smooth stress-strain curves (gradient-based smoothness penalty)
  - Monotonic stress increase in elastic region
  - KL divergence with optional annealing (for CVAE)
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


def mse_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return F.mse_loss(pred, target)


def yield_uts_constraint_loss(
    pred_scalar: torch.Tensor,
    margin: float = 0.02,
) -> torch.Tensor:
    """Penalize predictions where yield >= UTS.

    Args:
        pred_scalar: Predicted (yield, uts, elongation), shape (B, 3).
        margin: Minimum fractional gap required (yield * (1+margin) <= uts).

    Returns:
        Scalar penalty loss.
    """
    yield_pred = pred_scalar[:, 0]
    uts_pred = pred_scalar[:, 1]
    violation = F.relu(yield_pred * (1.0 + margin) - uts_pred)
    return violation.mean()


def smoothness_loss(stress_curve: torch.Tensor) -> torch.Tensor:
    """Penalize non-smooth stress-strain curves via second-order differences.

    Args:
        stress_curve: Stress values, shape (B, N).

    Returns:
        Scalar smoothness penalty.
    """
    d1 = stress_curve[:, 1:] - stress_curve[:, :-1]
    d2 = d1[:, 1:] - d1[:, :-1]
    return (d2 ** 2).mean()


def monotonic_strain_loss(stress_curve: torch.Tensor) -> torch.Tensor:
    """Penalize non-monotonic stress increase in the elastic portion.

    Applies only to the first 20% of the curve where we expect elastic loading.

    Args:
        stress_curve: Stress values, shape (B, N).

    Returns:
        Scalar monotonicity penalty.
    """
    n = stress_curve.shape[1]
    elastic_end = max(2, int(n * 0.2))
    elastic = stress_curve[:, :elastic_end]
    diffs = elastic[:, 1:] - elastic[:, :-1]
    violation = F.relu(-diffs)
    return violation.mean()


def kl_divergence_loss(
    mu: torch.Tensor,
    log_var: torch.Tensor,
    beta: float = 1.0,
    annealing_weight: float = 1.0,
) -> torch.Tensor:
    """KL divergence loss with beta weighting and annealing.

    KL(q(z|x) || p(z)) = -0.5 * sum(1 + log_var - mu^2 - exp(log_var))

    Args:
        mu: Latent mean, shape (B, latent_dim).
        log_var: Latent log variance, shape (B, latent_dim).
        beta: Beta-VAE weight for KL term.
        annealing_weight: Warmup annealing factor in [0, 1].

    Returns:
        Scalar KL loss.
    """
    kl = -0.5 * torch.mean(1 + log_var - mu.pow(2) - log_var.exp())
    return beta * annealing_weight * kl


class CVAELoss(nn.Module):
    """Combined CVAE loss: reconstruction + KL + physics constraints.

    Attributes:
        beta: KL weight.
        physics_weight: Weight for physics constraint terms.
        smoothness_weight: Weight for smoothness penalty.
    """

    def __init__(
        self,
        beta: float = 1.0,
        physics_weight: float = 0.1,
        smoothness_weight: float = 0.05,
    ) -> None:
        super().__init__()
        self.beta = beta
        self.physics_weight = physics_weight
        self.smoothness_weight = smoothness_weight

    def forward(
        self,
        recon: torch.Tensor,
        target: torch.Tensor,
        mu: torch.Tensor,
        log_var: torch.Tensor,
        pred_scalar: torch.Tensor | None = None,
        annealing_weight: float = 1.0,
    ) -> dict[str, torch.Tensor]:
        """Compute total CVAE loss with all components.

        Args:
            recon: Reconstructed stress curve, shape (B, N).
            target: Ground-truth stress curve, shape (B, N).
            mu: Latent mean.
            log_var: Latent log variance.
            pred_scalar: Optional scalar predictions for physics constraints.
            annealing_weight: KL annealing factor.

        Returns:
            Dictionary with 'total', 'recon', 'kl', 'physics', 'smooth' losses.
        """
        recon_l = F.mse_loss(recon, target)
        kl_l = kl_divergence_loss(mu, log_var, self.beta, annealing_weight)
        smooth_l = smoothness_loss(recon) * self.smoothness_weight
        mono_l = monotonic_strain_loss(recon) * self.physics_weight

        total = recon_l + kl_l + smooth_l + mono_l

        if pred_scalar is not None:
            phys_l = yield_uts_constraint_loss(pred_scalar) * self.physics_weight
            total = total + phys_l
        else:
            phys_l = torch.tensor(0.0)

        return {
            "total": total,
            "recon": recon_l,
            "kl": kl_l,
            "physics": phys_l,
            "smooth": smooth_l,
            "monotonic": mono_l,
        }


class DeepRegressionLoss(nn.Module):
    """Combined loss for deep scalar regression with physics constraints."""

    def __init__(self, physics_weight: float = 0.1) -> None:
        super().__init__()
        self.physics_weight = physics_weight

    def forward(
        self,
        pred: torch.Tensor,
        target: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Compute regression loss + physics constraints.

        Args:
            pred: Predicted scalars (yield, uts, elongation), shape (B, 3).
            target: Ground-truth scalars, shape (B, 3).

        Returns:
            Dictionary with 'total', 'mse', 'physics' losses.
        """
        mse_l = F.mse_loss(pred, target)
        phys_l = yield_uts_constraint_loss(pred) * self.physics_weight
        total = mse_l + phys_l
        return {"total": total, "mse": mse_l, "physics": phys_l}
