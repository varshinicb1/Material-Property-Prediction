"""Tests for physics-aware loss functions."""

from __future__ import annotations

import sys
from pathlib import Path
import torch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_yield_uts_loss_valid():
    from training.losses import yield_uts_constraint_loss
    pred = torch.tensor([[800.0, 1000.0, 12.0]])
    assert yield_uts_constraint_loss(pred).item() < 1e-6


def test_yield_uts_loss_violation():
    from training.losses import yield_uts_constraint_loss
    pred = torch.tensor([[1050.0, 1000.0, 12.0]])
    assert yield_uts_constraint_loss(pred).item() > 0


def test_smoothness_loss_flat():
    from training.losses import smoothness_loss
    flat = torch.ones(4, 50)
    assert smoothness_loss(flat).item() < 1e-8


def test_smoothness_loss_noisy():
    from training.losses import smoothness_loss
    torch.manual_seed(0)
    noisy = torch.randn(4, 50)
    assert smoothness_loss(noisy).item() > 0


def test_kl_loss_zero_at_prior():
    from training.losses import kl_divergence_loss
    mu = torch.zeros(8, 32)
    log_var = torch.zeros(8, 32)
    kl = kl_divergence_loss(mu, log_var)
    assert abs(kl.item()) < 1e-5


def test_cvae_loss_forward():
    from training.losses import CVAELoss
    criterion = CVAELoss(beta=1.0, physics_weight=0.1, smoothness_weight=0.05)
    recon = torch.randn(8, 50)
    target = torch.randn(8, 50)
    mu = torch.zeros(8, 32)
    log_var = torch.zeros(8, 32)
    losses = criterion(recon, target, mu, log_var)
    assert "total" in losses
    assert "recon" in losses
    assert "kl" in losses
    assert losses["total"].item() > 0


def test_deep_regression_loss():
    from training.losses import DeepRegressionLoss
    criterion = DeepRegressionLoss(physics_weight=0.1)
    pred = torch.tensor([[800.0, 1000.0, 12.0],
                          [700.0, 900.0, 15.0]])
    target = torch.tensor([[810.0, 1010.0, 11.5],
                            [690.0, 890.0, 14.0]])
    losses = criterion(pred, target)
    assert "total" in losses
    assert losses["mse"].item() > 0
