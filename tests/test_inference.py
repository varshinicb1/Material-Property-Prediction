"""Tests for inference pipeline (end-to-end with tiny models)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_predictor_build_input():
    from inference.predictor import MaterialPredictor

    d = MaterialPredictor.build_input(
        current_A=150.0,
        voltage_V=15.0,
        speed_mm_per_min=150.0,
        repair_stage=1,
    )
    assert "current_A" in d
    assert "heat_input_kJ_per_mm" in d
    assert d["repair_stage"] == 1.0
    assert abs(d["heat_input_kJ_per_mm"] - (150 * 15 * 60) / (1000 * 150)) < 1e-6


def test_full_pipeline_tiny(tmp_path):
    from training.pipeline import run_pipeline

    cfg = {
        "data": {"n_samples": 120, "n_stress_strain_points": 50, "noise_level": 0.05},
        "model": {
            "gbm": {"n_estimators": 10, "learning_rate": 0.1, "early_stopping_rounds": 3},
            "deep": {"d_token": 32, "n_blocks": 1, "attention_n_heads": 2,
                     "attention_dropout": 0.1, "ffn_d_hidden": 64, "ffn_dropout": 0.1},
            "cvae": {"latent_dim": 8, "condition_dim": 16,
                     "encoder_hidden": [32, 16], "decoder_hidden": [16, 32], "beta": 1.0},
        },
        "training": {
            "deep": {"epochs": 3, "batch_size": 16, "learning_rate": 1e-3,
                     "weight_decay": 1e-4, "warmup_epochs": 1, "patience": 5,
                     "gradient_clip": 1.0, "use_compile": False},
            "cvae": {"epochs": 3, "batch_size": 16, "learning_rate": 1e-3,
                     "kl_warmup_epochs": 1, "patience": 5},
        },
    }

    metrics = run_pipeline(
        cfg=cfg,
        data_dir=str(tmp_path / "data"),
        models_dir=str(tmp_path / "models"),
        results_dir=str(tmp_path / "results"),
        seed=42,
        force_regenerate=True,
    )

    assert "gbm" in metrics
    assert "deep" in metrics
    assert "cvae" in metrics
    assert "yield_strength_MPa_r2" in metrics["gbm"]


def test_predictor_inference(tmp_path):
    from training.pipeline import run_pipeline
    from inference.predictor import MaterialPredictor

    cfg = {
        "data": {"n_samples": 120, "n_stress_strain_points": 50, "noise_level": 0.05},
        "model": {
            "gbm": {"n_estimators": 10, "learning_rate": 0.1, "early_stopping_rounds": 3},
            "deep": {"d_token": 32, "n_blocks": 1, "attention_n_heads": 2,
                     "attention_dropout": 0.1, "ffn_d_hidden": 64, "ffn_dropout": 0.1},
            "cvae": {"latent_dim": 8, "condition_dim": 16,
                     "encoder_hidden": [32, 16], "decoder_hidden": [16, 32], "beta": 1.0},
        },
        "training": {
            "deep": {"epochs": 2, "batch_size": 16, "learning_rate": 1e-3,
                     "weight_decay": 1e-4, "warmup_epochs": 1, "patience": 5,
                     "gradient_clip": 1.0, "use_compile": False},
            "cvae": {"epochs": 2, "batch_size": 16, "learning_rate": 1e-3,
                     "kl_warmup_epochs": 1, "patience": 5},
        },
    }

    models_dir = str(tmp_path / "models")
    run_pipeline(cfg=cfg, data_dir=str(tmp_path / "data"),
                 models_dir=models_dir, results_dir=str(tmp_path / "results"),
                 seed=42, force_regenerate=True)

    predictor = MaterialPredictor(models_dir=models_dir)
    input_dict = predictor.build_input(current_A=150.0, voltage_V=15.0,
                                        speed_mm_per_min=150.0, repair_stage=0)
    result = predictor.predict(input_dict)

    assert result.yield_strength_MPa > 0
    assert result.uts_MPa > result.yield_strength_MPa
    assert result.elongation_pct > 0
    assert len(result.strain) == 50
    assert len(result.stress) == 50
    assert result.stress[0] < 10.0
