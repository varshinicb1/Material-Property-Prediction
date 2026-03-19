"""Tests for model architectures."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_ft_transformer_forward():
    from models.ft_transformer import FTTransformer

    model = FTTransformer(n_features=16, n_targets=3, d_token=64, n_blocks=2,
                          attention_n_heads=4, ffn_d_hidden=128)
    model.eval()
    x = torch.randn(8, 16)
    with torch.no_grad():
        out = model(x)
    assert out.shape == (8, 3)


def test_cvae_forward():
    from models.cvae import CVAE

    model = CVAE(n_features=16, curve_dim=50, latent_dim=16,
                 condition_dim=32, encoder_hidden=[64, 32], decoder_hidden=[32, 64])
    model.train()
    x = torch.randn(4, 16)
    curve = torch.randn(4, 50)
    recon, mu, log_var = model(curve, x)
    assert recon.shape == (4, 50)
    assert mu.shape == (4, 16)
    assert log_var.shape == (4, 16)


def test_cvae_generate():
    from models.cvae import CVAE

    model = CVAE(n_features=16, curve_dim=50, latent_dim=16,
                 condition_dim=32, encoder_hidden=[64, 32], decoder_hidden=[32, 64])
    model.eval()
    x = torch.randn(3, 16)
    curves = model.generate(x, n_samples=1)
    assert curves.shape == (3, 50)

    curves_multi = model.generate(x, n_samples=5)
    assert curves_multi.shape == (3, 5, 50)


def test_gbm_ensemble():
    from data.generator import DataConfig, generate_dataset, get_feature_columns
    from models.gbm import GBMEnsemble

    cfg = DataConfig(n_samples=200, random_state=3)
    df = generate_dataset(cfg)
    cols = get_feature_columns(50)

    X = df.select(cols["features"]).to_numpy().astype(np.float32)
    y = df.select(cols["scalar_targets"]).to_numpy().astype(np.float32)

    split = 160
    gbm = GBMEnsemble(n_estimators=20, learning_rate=0.1, early_stopping_rounds=5)
    gbm.fit(X[:split], y[:split], X[split:], y[split:],
            feature_names=cols["features"], target_names=cols["scalar_targets"])
    pred = gbm.predict(X[split:])
    assert pred.shape == (40, 3)


def test_physics_loss():
    from training.losses import yield_uts_constraint_loss, smoothness_loss

    pred_valid = torch.tensor([[800.0, 1000.0, 12.0]])
    loss_valid = yield_uts_constraint_loss(pred_valid)
    assert loss_valid.item() < 1e-3

    pred_invalid = torch.tensor([[1100.0, 1000.0, 12.0]])
    loss_invalid = yield_uts_constraint_loss(pred_invalid)
    assert loss_invalid.item() > 0

    smooth_curve = torch.linspace(0, 1, 50).unsqueeze(0)
    assert smoothness_loss(smooth_curve).item() < 1e-4


def test_ft_transformer_save_load(tmp_path):
    from models.ft_transformer import FTTransformer

    model = FTTransformer(n_features=16, n_targets=3, d_token=64, n_blocks=2,
                          attention_n_heads=4, ffn_d_hidden=128)
    save_path = tmp_path / "ft.pt"
    model.save(save_path)

    loaded = FTTransformer.load(save_path, n_features=16, n_targets=3, d_token=64,
                                n_blocks=2, attention_n_heads=4,
                                attention_dropout=0.2, ffn_d_hidden=128, ffn_dropout=0.1)
    x = torch.randn(4, 16)
    model.eval()
    loaded.eval()
    with torch.no_grad():
        assert torch.allclose(model(x), loaded(x), atol=1e-5)
