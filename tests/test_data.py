"""Tests for data generation and preprocessing."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_dataset_generation():
    from data.generator import DataConfig, generate_dataset, get_feature_columns

    cfg = DataConfig(n_samples=100, random_state=0)
    df = generate_dataset(cfg)

    assert len(df) == 100
    cols = get_feature_columns(50)
    for col in cols["features"] + cols["scalar_targets"]:
        assert col in df.columns, f"Missing column: {col}"


def test_physics_constraints():
    from data.generator import DataConfig, generate_dataset

    cfg = DataConfig(n_samples=500, random_state=1)
    df = generate_dataset(cfg)

    ys = df["yield_strength_MPa"].to_numpy()
    uts = df["uts_MPa"].to_numpy()

    # Yield must be < UTS for all samples
    assert np.all(ys < uts), "Physics violation: yield >= UTS found"
    # Reasonable bounds
    assert np.all(ys > 100), "Yield strength too low"
    assert np.all(uts < 2000), "UTS unrealistically high"


def test_preprocessor_roundtrip():
    import polars as pl
    from data.generator import DataConfig, generate_dataset
    from data.preprocessor import DataPreprocessor

    cfg = DataConfig(n_samples=200, random_state=2)
    df = generate_dataset(cfg)

    n = len(df)
    train_df = df[:int(n * 0.7)]
    val_df = df[int(n * 0.7):int(n * 0.85)]
    test_df = df[int(n * 0.85):]

    prep = DataPreprocessor(n_stress_points=50)
    proc = prep.fit_transform(train_df, val_df, test_df)

    assert proc.X_train.dtype == np.float32
    assert proc.y_scalar_train.shape[1] == 3
    assert proc.y_stress_train.shape[1] == 50


def test_ramberg_osgood_curve():
    from data.generator import _ramberg_osgood_curve

    rng = np.random.default_rng(42)
    strain, stress = _ramberg_osgood_curve(
        sigma_y=800.0, sigma_uts=1000.0, elongation=0.12, n_points=50, rng=rng
    )
    assert len(strain) == 50
    assert len(stress) == 50
    assert strain[0] == pytest.approx(0.0, abs=1e-10)
    assert stress.max() <= 1100.0  # within 10% of UTS


def test_feature_columns():
    from data.generator import get_feature_columns

    cols = get_feature_columns(50)
    assert len(cols["features"]) == 16
    assert len(cols["scalar_targets"]) == 3
    assert len(cols["curve_strain"]) == 50
    assert len(cols["curve_stress"]) == 50
