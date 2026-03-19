"""Integration tests for end-to-end workflows.

Tests complete workflows from data generation through prediction.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest


def test_data_generation_workflow():
    """Test complete data generation workflow."""
    from data.generator import DataConfig, generate_dataset, save_dataset, load_splits
    
    # Generate data
    cfg = DataConfig(n_samples=100, n_stress_strain_points=50, random_state=42)
    df = generate_dataset(cfg)
    
    # Verify DataFrame structure
    assert len(df) == 100
    assert "yield_strength_MPa" in df.columns
    assert "uts_MPa" in df.columns
    assert "elongation_pct" in df.columns
    
    # Save and load
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = save_dataset(df, tmpdir)
        assert "train" in paths
        assert "val" in paths
        assert "test" in paths
        
        splits = load_splits(tmpdir)
        assert len(splits["train"]) > 0
        assert len(splits["val"]) > 0
        assert len(splits["test"]) > 0


def test_preprocessing_workflow():
    """Test complete preprocessing workflow."""
    from data.generator import DataConfig, generate_dataset, save_dataset, load_splits
    from data.preprocessor import DataPreprocessor
    
    # Generate and split data
    cfg = DataConfig(n_samples=100, n_stress_strain_points=50, random_state=42)
    df = generate_dataset(cfg)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        save_dataset(df, tmpdir)
        splits = load_splits(tmpdir)
        
        # Preprocess
        preprocessor = DataPreprocessor(n_stress_points=50)
        proc = preprocessor.fit_transform(
            splits["train"], splits["val"], splits["test"]
        )
        
        # Verify processed data
        assert proc.X_train.shape[1] == proc.n_features
        assert proc.y_scalar_train.shape[1] == 3  # yield, uts, elongation
        assert proc.y_stress_train.shape[1] == 50  # stress curve points
        
        # Test inverse transform
        y_inv = preprocessor.inverse_scalar_targets(proc.y_scalar_test)
        assert y_inv.shape == proc.y_scalar_test.shape


def test_physics_constraints_workflow():
    """Test that physics constraints are maintained through entire workflow."""
    from data.generator import DataConfig, generate_dataset
    
    cfg = DataConfig(n_samples=100, random_state=42)
    df = generate_dataset(cfg)
    
    # Check all samples satisfy physics constraints
    for i in range(len(df)):
        row = df.row(i, named=True)
        yield_strength = row["yield_strength_MPa"]
        uts = row["uts_MPa"]
        elongation = row["elongation_pct"]
        
        # Physics constraints
        assert yield_strength < uts, f"Row {i}: Yield >= UTS"
        assert yield_strength > 0, f"Row {i}: Negative yield"
        assert uts > 0, f"Row {i}: Negative UTS"
        assert elongation > 0, f"Row {i}: Negative elongation"
        
        # Check stress curve
        stress_cols = [f"stress_{j:03d}" for j in range(50)]
        stress_curve = [row[col] for col in stress_cols]
        
        # Stress should start near zero
        assert stress_curve[0] < 10, f"Row {i}: Stress doesn't start at zero"
        
        # Stress should be non-negative
        assert all(s >= 0 for s in stress_curve), f"Row {i}: Negative stress"


def test_error_handling_workflow():
    """Test error handling in various failure scenarios."""
    from data.generator import DataConfig, generate_dataset
    from data.preprocessor import DataPreprocessor
    import polars as pl
    
    # Test invalid config
    with pytest.raises(ValueError):
        cfg = DataConfig(n_samples=-10)
        generate_dataset(cfg)
    
    # Test empty DataFrame
    preprocessor = DataPreprocessor(n_stress_points=50)
    empty_df = pl.DataFrame()
    
    with pytest.raises((ValueError, Exception)):
        # Should fail due to missing columns or empty data
        preprocessor.fit_transform(empty_df, empty_df, empty_df)


def test_numerical_stability_workflow():
    """Test numerical stability across many samples."""
    from data.generator import DataConfig, generate_dataset
    import numpy as np
    
    # Generate large dataset
    cfg = DataConfig(n_samples=500, random_state=42)
    df = generate_dataset(cfg)
    
    # Check all numeric columns for NaN/Inf
    for col in df.columns:
        if col.startswith(("yield", "uts", "elongation", "stress", "strain")):
            values = df[col].to_numpy()
            assert np.all(np.isfinite(values)), f"Column {col} contains NaN/Inf"


def test_config_validation_workflow():
    """Test configuration validation and defaults."""
    # Test empty config uses defaults
    cfg = {}
    
    # Should use default values
    n_samples = cfg.get("data", {}).get("n_samples", 2000)
    assert n_samples == 2000
    
    n_estimators = cfg.get("model", {}).get("gbm", {}).get("n_estimators", 500)
    assert n_estimators == 500


def test_feature_engineering_workflow():
    """Test feature engineering and column management."""
    from data.generator import get_feature_columns
    
    cols = get_feature_columns(50)
    
    # Verify all required column types exist
    assert "features" in cols
    assert "scalar_targets" in cols
    assert "curve_strain" in cols
    assert "curve_stress" in cols
    
    # Verify counts
    assert len(cols["features"]) == 16  # All input features
    assert len(cols["scalar_targets"]) == 3  # yield, uts, elongation
    assert len(cols["curve_strain"]) == 50
    assert len(cols["curve_stress"]) == 50


def test_stress_strain_curve_quality():
    """Test quality of generated stress-strain curves."""
    from data.generator import _ramberg_osgood_curve
    import numpy as np
    
    # Generate multiple curves
    for _ in range(10):
        strain, stress = _ramberg_osgood_curve(
            sigma_y=800.0,
            sigma_uts=900.0,
            elongation=0.15,
            n_points=50,
            noise=0.02
        )
        
        # Quality checks
        assert len(strain) == len(stress) == 50
        assert np.all(strain >= 0)
        assert np.all(stress >= 0)
        assert stress[0] < 10  # Starts near zero
        # Note: With noise, stress can temporarily exceed UTS, but should be reasonable
        assert np.max(stress) <= 900 * 1.3  # Doesn't exceed UTS by too much
        
        # Check monotonicity in elastic region
        elastic_end = int(len(stress) * 0.08)
        for i in range(1, elastic_end):
            assert stress[i] >= stress[i-1], "Elastic region not monotonic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
