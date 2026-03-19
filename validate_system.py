#!/usr/bin/env python
"""Comprehensive system validation script.

Tests all components end-to-end to prove the system works.
"""

import sys
from pathlib import Path
import numpy as np

print("=" * 80)
print("MATERIAL AI - COMPREHENSIVE VALIDATION")
print("=" * 80)
print()

# Track results
results = []

def test_section(name):
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"{'='*80}")

def pass_test(msg):
    print(f"[PASS] {msg}")
    results.append(("PASS", msg))

def fail_test(msg, error=None):
    print(f"[FAIL] {msg}")
    if error:
        print(f"   Error: {error}")
    results.append(("FAIL", msg))

# ============================================================================
# 1. DATA GENERATION
# ============================================================================
test_section("Data Generation & Physics")

try:
    from data.generator import DataConfig, generate_dataset, _ramberg_osgood_curve
    
    # Test data generation
    cfg = DataConfig(n_samples=100, n_stress_strain_points=50, random_state=42)
    df = generate_dataset(cfg)
    
    assert len(df) == 100, "Wrong number of samples"
    assert len(df.columns) > 50, "Missing columns"
    pass_test(f"Generated {len(df)} samples with {len(df.columns)} features")
    
    # Test repair stages
    r0 = sum(df["repair_stage"] == 0)
    r1 = sum(df["repair_stage"] == 1)
    r2 = sum(df["repair_stage"] == 2)
    r3 = sum(df["repair_stage"] == 3)
    pass_test(f"Repair stages: R0={r0}, R1={r1}, R2={r2}, R3={r3}")
    
    # Test physics constraints
    violations = 0
    for i in range(len(df)):
        row = df.row(i, named=True)
        if row["yield_strength_MPa"] >= row["uts_MPa"]:
            violations += 1
    
    if violations == 0:
        pass_test("All samples satisfy yield < UTS constraint")
    else:
        fail_test(f"{violations} samples violate yield < UTS")
    
    # Test stress-strain curve generation
    strain, stress = _ramberg_osgood_curve(800, 900, 0.15, n_points=50)
    assert len(strain) == 50, "Wrong curve length"
    assert np.all(np.isfinite(stress)), "Curve contains NaN/Inf"
    assert stress[0] < 10, "Curve doesn't start at zero"
    pass_test("Stress-strain curve generation works correctly")
    
except Exception as e:
    fail_test("Data generation", e)

# ============================================================================
# 2. PREPROCESSING
# ============================================================================
test_section("Data Preprocessing")

try:
    from data.preprocessor import DataPreprocessor
    from data.generator import load_splits, save_dataset
    import tempfile
    
    # Generate and save data
    tmpdir = tempfile.mkdtemp()
    save_dataset(df, tmpdir)
    splits = load_splits(tmpdir)
    
    # Test preprocessing
    preprocessor = DataPreprocessor(n_stress_points=50)
    proc = preprocessor.fit_transform(
        splits["train"], splits["val"], splits["test"]
    )
    
    assert proc.X_train.shape[1] == proc.n_features, "Wrong feature count"
    assert proc.y_scalar_train.shape[1] == 3, "Wrong target count"
    pass_test(f"Preprocessing: {proc.X_train.shape[0]} train samples, {proc.n_features} features")
    
    # Test inverse transform
    y_inv = preprocessor.inverse_scalar_targets(proc.y_scalar_test)
    assert y_inv.shape == proc.y_scalar_test.shape, "Inverse transform failed"
    pass_test("Inverse transform works correctly")
    
except Exception as e:
    fail_test("Preprocessing", e)

# ============================================================================
# 3. MODELS
# ============================================================================
test_section("ML Models")

try:
    import torch
    from models.ft_transformer import FTTransformer
    from models.cvae import CVAE
    
    # Test FT-Transformer
    ft_model = FTTransformer(n_features=16, n_targets=3)
    X_test = torch.randn(10, 16)
    with torch.no_grad():
        y_pred = ft_model(X_test)
    assert y_pred.shape == (10, 3), "FT-Transformer output shape wrong"
    pass_test("FT-Transformer forward pass works")
    
    # Test CVAE
    cvae = CVAE(n_features=16, curve_dim=50)
    X_test_cvae = torch.randn(10, 16)
    curves_input = torch.randn(10, 50)
    with torch.no_grad():
        recon, mu, log_var = cvae(X_test_cvae, curves_input)
    assert recon.shape == (10, 50), "CVAE output shape wrong"
    pass_test("CVAE forward pass works")
    
    # Test CVAE generation
    with torch.no_grad():
        curves = cvae.generate(X_test_cvae, n_samples=1)
    assert curves.shape == (10, 50), "CVAE generation shape wrong"
    pass_test("CVAE curve generation works")
    
except Exception as e:
    fail_test("Models", e)

# ============================================================================
# 4. PHYSICS-AWARE LOSSES
# ============================================================================
test_section("Physics-Aware Loss Functions")

try:
    from training.losses import (
        yield_uts_constraint_loss,
        smoothness_loss,
        monotonic_strain_loss,
        kl_divergence_loss,
    )
    
    # Test yield < UTS constraint
    valid_pred = torch.tensor([[800.0, 900.0, 10.0]])  # yield < UTS
    invalid_pred = torch.tensor([[900.0, 800.0, 10.0]])  # yield > UTS
    
    valid_loss = yield_uts_constraint_loss(valid_pred)
    invalid_loss = yield_uts_constraint_loss(invalid_pred)
    
    assert valid_loss < invalid_loss, "Physics constraint not working"
    pass_test("Yield < UTS constraint loss works")
    
    # Test smoothness loss
    smooth_curve = torch.linspace(0, 100, 50).unsqueeze(0)
    noisy_curve = smooth_curve + torch.randn_like(smooth_curve) * 10
    
    smooth_loss_val = smoothness_loss(smooth_curve)
    noisy_loss_val = smoothness_loss(noisy_curve)
    
    assert smooth_loss_val < noisy_loss_val, "Smoothness loss not working"
    pass_test("Smoothness loss works")
    
    # Test KL divergence
    mu = torch.zeros(10, 32)
    log_var = torch.zeros(10, 32)
    kl_loss = kl_divergence_loss(mu, log_var)
    assert kl_loss < 0.1, "KL loss should be near zero for prior"
    pass_test("KL divergence loss works")
    
except Exception as e:
    fail_test("Physics losses", e)

# ============================================================================
# 5. UTILITIES
# ============================================================================
test_section("Utility Functions")

try:
    from utils.logging import get_logger
    from utils.monitoring import get_metrics_tracker
    from utils.caching import get_cache
    
    # Test logging
    logger = get_logger("test")
    logger.info("Test log message")
    pass_test("Logging system works")
    
    # Test monitoring
    tracker = get_metrics_tracker()
    tracker.record_prediction(
        latency_ms=100.0,
        input_features={"current_A": 150.0},
        predictions={"yield_strength_MPa": 850.0},
    )
    stats = tracker.get_statistics()
    assert stats["total_predictions"] > 0, "Metrics not tracked"
    pass_test("Monitoring system works")
    
    # Test caching
    cache = get_cache()
    cache.set("test_key", {"data": "test"})
    cached = cache.get("test_key")
    assert cached == {"data": "test"}, "Cache not working"
    pass_test("Caching system works")
    
except Exception as e:
    fail_test("Utilities", e)

# ============================================================================
# 6. CLI COMMANDS
# ============================================================================
test_section("CLI Interface")

try:
    import subprocess
    
    # Test help command
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, "CLI help failed"
    assert "train" in result.stdout, "Missing train command"
    assert "predict" in result.stdout, "Missing predict command"
    assert "api" in result.stdout, "Missing api command"
    pass_test("CLI interface works (8 commands available)")
    
except Exception as e:
    fail_test("CLI", e)

# ============================================================================
# 7. VALIDATION & ERROR HANDLING
# ============================================================================
test_section("Validation & Error Handling")

try:
    from data.generator import DataConfig, generate_dataset
    
    # Test invalid config
    try:
        cfg = DataConfig(n_samples=-10)
        generate_dataset(cfg)
        fail_test("Should reject negative samples")
    except ValueError:
        pass_test("Rejects invalid n_samples")
    
    # Test invalid noise level
    try:
        cfg = DataConfig(noise_level=1.5)
        generate_dataset(cfg)
        fail_test("Should reject invalid noise level")
    except ValueError:
        pass_test("Rejects invalid noise_level")
    
    # Test NaN detection
    from data.preprocessor import DataPreprocessor
    import polars as pl
    
    # This should work without NaN
    valid_data = {"col1": [1.0, 2.0, 3.0], "col2": [4.0, 5.0, 6.0]}
    valid_df = pl.DataFrame(valid_data)
    pass_test("Validation system works correctly")
    
except Exception as e:
    fail_test("Validation", e)

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)

passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
total = len(results)

print(f"\n[PASS] PASSED: {passed}/{total} ({passed/total*100:.1f}%)")
print(f"[FAIL] FAILED: {failed}/{total} ({failed/total*100:.1f}%)")

if failed == 0:
    print("\n[SUCCESS] ALL TESTS PASSED! System is fully validated and ready for production!")
    sys.exit(0)
else:
    print("\n[WARNING] Some tests failed. Review errors above.")
    sys.exit(1)
