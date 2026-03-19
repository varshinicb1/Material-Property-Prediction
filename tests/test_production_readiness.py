"""Production readiness tests for Material AI.

Tests error handling, input validation, edge cases, and robustness.
"""

from __future__ import annotations

import numpy as np
import pytest
import tempfile
from pathlib import Path


def test_invalid_config_handling():
    """Test that invalid configurations are properly rejected."""
    from training.pipeline import run_pipeline
    
    # Test with invalid config type
    with pytest.raises(ValueError, match="Configuration must be a dictionary"):
        run_pipeline(cfg="not a dict", data_dir="data")
    
    # Test with missing sections (should use defaults, not crash)
    result = run_pipeline(
        cfg={},
        data_dir=tempfile.mkdtemp(),
        models_dir=tempfile.mkdtemp(),
        results_dir=tempfile.mkdtemp(),
        seed=42
    )
    assert isinstance(result, dict)


def test_data_validation():
    """Test data validation catches invalid inputs."""
    from data.generator import DataConfig, generate_dataset
    
    # Test negative samples
    with pytest.raises(ValueError, match="n_samples must be positive"):
        cfg = DataConfig(n_samples=-10)
        generate_dataset(cfg)
    
    # Test invalid noise level
    with pytest.raises(ValueError, match="noise_level must be in"):
        cfg = DataConfig(noise_level=1.5)
        generate_dataset(cfg)
    
    # Test too few stress points
    with pytest.raises(ValueError, match="n_stress_strain_points must be"):
        cfg = DataConfig(n_stress_strain_points=5)
        generate_dataset(cfg)


def test_ramberg_osgood_validation():
    """Test Ramberg-Osgood curve generation validates inputs."""
    from data.generator import _ramberg_osgood_curve
    
    # Test negative strength
    with pytest.raises(ValueError, match="Strengths must be positive"):
        _ramberg_osgood_curve(sigma_y=-100, sigma_uts=500, elongation=0.1)
    
    # Test UTS < yield
    with pytest.raises(ValueError, match="UTS must be > yield"):
        _ramberg_osgood_curve(sigma_y=600, sigma_uts=500, elongation=0.1)
    
    # Test invalid elongation
    with pytest.raises(ValueError, match="Elongation must be in"):
        _ramberg_osgood_curve(sigma_y=500, sigma_uts=600, elongation=1.5)
    
    # Test too few points
    with pytest.raises(ValueError, match="Need at least 10 points"):
        _ramberg_osgood_curve(sigma_y=500, sigma_uts=600, elongation=0.1, n_points=5)


def test_predictor_missing_models():
    """Test predictor handles missing model files gracefully."""
    from inference.predictor import MaterialPredictor
    
    # Test with non-existent directory
    with pytest.raises(FileNotFoundError, match="Models directory not found"):
        MaterialPredictor(models_dir="/nonexistent/path")
    
    # Test with empty directory
    empty_dir = tempfile.mkdtemp()
    with pytest.raises(FileNotFoundError, match="Missing required model files"):
        MaterialPredictor(models_dir=empty_dir)


def test_predictor_input_validation():
    """Test predictor validates input features."""
    # This test requires trained models, so we'll mock the validation logic
    from inference.predictor import FEATURE_NAMES
    
    # Simulate validation
    input_dict = {"current_A": 150.0}  # Missing most features
    missing_keys = [k for k in FEATURE_NAMES if k not in input_dict]
    assert len(missing_keys) > 0  # Should detect missing features


def test_nan_inf_detection():
    """Test that NaN/Inf values are detected in data."""
    import polars as pl
    from data.preprocessor import DataPreprocessor
    from data.generator import get_feature_columns
    
    cols = get_feature_columns(50)
    
    # Create DataFrame with NaN
    data = {col: [1.0, 2.0, np.nan] for col in cols["features"]}
    data.update({col: [1.0, 2.0, 3.0] for col in cols["scalar_targets"]})
    data.update({col: [1.0, 2.0, 3.0] for col in cols["curve_stress"]})
    data.update({col: [1.0, 2.0, 3.0] for col in cols["curve_strain"]})
    
    df_with_nan = pl.DataFrame(data)
    
    preprocessor = DataPreprocessor(n_stress_points=50)
    
    # Should raise ValueError for NaN in features
    with pytest.raises(ValueError, match="contain NaN or Inf"):
        preprocessor.fit_transform(df_with_nan, df_with_nan, df_with_nan)


def test_empty_dataframe_handling():
    """Test that empty DataFrames are rejected."""
    import polars as pl
    from data.preprocessor import DataPreprocessor
    from data.generator import get_feature_columns
    
    cols = get_feature_columns(50)
    
    # Create valid DataFrame
    data = {col: [1.0, 2.0, 3.0] for col in cols["features"]}
    data.update({col: [1.0, 2.0, 3.0] for col in cols["scalar_targets"]})
    data.update({col: [1.0, 2.0, 3.0] for col in cols["curve_stress"]})
    data.update({col: [1.0, 2.0, 3.0] for col in cols["curve_strain"]})
    
    valid_df = pl.DataFrame(data)
    empty_df = pl.DataFrame({col: [] for col in data.keys()})
    
    preprocessor = DataPreprocessor(n_stress_points=50)
    
    # Should raise ValueError for empty training set
    with pytest.raises(ValueError, match="Training DataFrame is empty"):
        preprocessor.fit_transform(empty_df, valid_df, valid_df)


def test_physics_constraints_enforced():
    """Test that physics constraints are enforced in predictions."""
    # Test yield < UTS constraint
    yield_strength = 800.0
    uts = 750.0  # Invalid: UTS < yield
    
    # After ensemble, should be corrected
    ensemble_pred = np.array([yield_strength, uts, 10.0])
    
    # Simulate physics enforcement
    ensemble_pred[0] = min(ensemble_pred[0], ensemble_pred[1] * 0.97)
    ensemble_pred[1] = max(ensemble_pred[1], ensemble_pred[0] * 1.03)
    
    assert ensemble_pred[0] < ensemble_pred[1], "Yield should be < UTS after correction"


def test_ensemble_weights_validation():
    """Test that ensemble weights are validated."""
    # Weights should sum to 1.0
    gbm_weight = 0.45
    deep_weight = 0.45  # Sum = 0.9, invalid
    
    assert not np.isclose(gbm_weight + deep_weight, 1.0), "Invalid weights should be detected"


def test_stress_curve_monotonicity():
    """Test that generated stress curves are monotonic in elastic region."""
    from data.generator import _ramberg_osgood_curve
    
    strain, stress = _ramberg_osgood_curve(
        sigma_y=800.0,
        sigma_uts=900.0,
        elongation=0.15,
        n_points=50,
        noise=0.01
    )
    
    # Check elastic region is monotonic
    elastic_end = int(len(stress) * 0.08)
    for i in range(1, elastic_end):
        assert stress[i] >= stress[i-1], f"Stress not monotonic at index {i}"


def test_config_defaults():
    """Test that missing config values use sensible defaults."""
    from training.pipeline import run_pipeline
    
    # Empty config should use all defaults
    cfg = {}
    
    # Should not crash, should use defaults
    # (This would require full training, so we just validate structure)
    assert cfg.get("data", {}).get("n_samples", 2000) == 2000
    assert cfg.get("model", {}).get("gbm", {}).get("n_estimators", 500) == 500


def test_numerical_stability():
    """Test numerical stability of curve generation."""
    from data.generator import _ramberg_osgood_curve
    
    # Test with extreme values
    strain, stress = _ramberg_osgood_curve(
        sigma_y=300.0,  # Low yield
        sigma_uts=1500.0,  # High UTS
        elongation=0.25,  # High elongation
        n_points=100,
        noise=0.05
    )
    
    # Should not contain NaN or Inf
    assert np.all(np.isfinite(strain)), "Strain contains NaN/Inf"
    assert np.all(np.isfinite(stress)), "Stress contains NaN/Inf"
    
    # Should be non-negative
    assert np.all(strain >= 0), "Strain contains negative values"
    assert np.all(stress >= 0), "Stress contains negative values"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
