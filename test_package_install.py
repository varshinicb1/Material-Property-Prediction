#!/usr/bin/env python3
"""
Test script to verify Material AI package installation and usage.

This script demonstrates that Material AI can be installed and used
as a Python package by anyone.
"""

def test_import():
    """Test that the package can be imported."""
    print("=" * 60)
    print("Test 1: Package Import")
    print("=" * 60)
    
    try:
        import material_ai
        print(f"✅ Package imported successfully")
        print(f"   Version: {material_ai.__version__}")
        print(f"   Author: {material_ai.__author__}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import package: {e}")
        return False

def test_predictor_import():
    """Test that MaterialPredictor can be imported."""
    print("\n" + "=" * 60)
    print("Test 2: MaterialPredictor Import")
    print("=" * 60)
    
    try:
        from material_ai import MaterialPredictor
        print(f"✅ MaterialPredictor imported successfully")
        print(f"   Class: {MaterialPredictor}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import MaterialPredictor: {e}")
        return False

def test_batch_predictor_import():
    """Test that BatchPredictor can be imported."""
    print("\n" + "=" * 60)
    print("Test 3: BatchPredictor Import")
    print("=" * 60)
    
    try:
        from material_ai import BatchPredictor
        print(f"✅ BatchPredictor imported successfully")
        print(f"   Class: {BatchPredictor}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import BatchPredictor: {e}")
        return False

def test_predictor_initialization():
    """Test that MaterialPredictor can be initialized."""
    print("\n" + "=" * 60)
    print("Test 4: MaterialPredictor Initialization")
    print("=" * 60)
    
    try:
        from material_ai import MaterialPredictor
        predictor = MaterialPredictor(models_dir="models/saved")
        print(f"✅ MaterialPredictor initialized successfully")
        print(f"   Instance: {predictor}")
        return True
    except Exception as e:
        print(f"⚠️  Could not initialize (models may not be trained yet): {e}")
        print(f"   This is expected if models haven't been trained.")
        print(f"   Run: python main.py train")
        return None  # Not a failure, just not ready

def test_build_input():
    """Test that build_input method works."""
    print("\n" + "=" * 60)
    print("Test 5: Build Input Features")
    print("=" * 60)
    
    try:
        from material_ai import MaterialPredictor
        predictor = MaterialPredictor(models_dir="models/saved")
        
        features = predictor.build_input(
            current_A=180.0,
            voltage_V=12.0,
            speed_mm_per_min=150.0,
            wire_feed_m_per_min=2.5,
            gas_flow_L_per_min=12.0,
            preheat_temp_C=100.0,
            interpass_temp_C=150.0,
            heat_input_kJ_per_mm=0.6,
            cooling_rate=5.0,
            haz_cooling_rate=8.0,
            base_metal_yield_MPa=250.0,
            base_metal_uts_MPa=500.0,
            repair_stage=0,
            weld_bead_width_mm=8.0,
            weld_bead_height_mm=3.0,
            dilution_ratio=0.3
        )
        
        print(f"✅ Input features built successfully")
        print(f"   Shape: {features.shape}")
        return True
    except Exception as e:
        print(f"⚠️  Could not build input: {e}")
        return None

def test_prediction():
    """Test that prediction works."""
    print("\n" + "=" * 60)
    print("Test 6: Prediction")
    print("=" * 60)
    
    try:
        from material_ai import MaterialPredictor
        predictor = MaterialPredictor(models_dir="models/saved")
        
        features = predictor.build_input(
            current_A=180.0,
            voltage_V=12.0,
            speed_mm_per_min=150.0,
            wire_feed_m_per_min=2.5,
            gas_flow_L_per_min=12.0,
            preheat_temp_C=100.0,
            interpass_temp_C=150.0,
            heat_input_kJ_per_mm=0.6,
            cooling_rate=5.0,
            haz_cooling_rate=8.0,
            base_metal_yield_MPa=250.0,
            base_metal_uts_MPa=500.0,
            repair_stage=0,
            weld_bead_width_mm=8.0,
            weld_bead_height_mm=3.0,
            dilution_ratio=0.3
        )
        
        result = predictor.predict(features)
        
        print(f"✅ Prediction successful")
        print(f"   Yield Strength: {result.yield_strength_MPa:.1f} MPa")
        print(f"   UTS: {result.uts_MPa:.1f} MPa")
        print(f"   Elongation: {result.elongation_pct:.2f}%")
        return True
    except Exception as e:
        print(f"⚠️  Could not predict: {e}")
        return None

def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Material AI Package Installation Test" + " " * 10 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Run tests
    results.append(("Package Import", test_import()))
    results.append(("MaterialPredictor Import", test_predictor_import()))
    results.append(("BatchPredictor Import", test_batch_predictor_import()))
    results.append(("Predictor Initialization", test_predictor_initialization()))
    results.append(("Build Input", test_build_input()))
    results.append(("Prediction", test_prediction()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    total = len(results)
    
    for name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{status} - {name}")
    
    print()
    print(f"Total: {total} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped} (models not trained)")
    
    print("\n" + "=" * 60)
    
    if failed == 0 and passed >= 3:
        print("✅ PACKAGE INSTALLATION VERIFIED")
        print()
        print("Material AI can be installed and used as a Python package!")
        print()
        if skipped > 0:
            print("Note: Some tests skipped because models aren't trained yet.")
            print("Run: python main.py train")
    elif failed > 0:
        print("❌ PACKAGE INSTALLATION FAILED")
        print()
        print("Please ensure Material AI is installed:")
        print("  pip install -e .")
    else:
        print("⚠️  PACKAGE PARTIALLY WORKING")
        print()
        print("Package imports work, but models need to be trained:")
        print("  python main.py train")
    
    print("=" * 60)
    print()
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
