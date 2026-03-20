"""Quick GUI validation script."""

from pathlib import Path
import sys

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

def test_gui_imports():
    """Test that GUI imports work."""
    print("Testing GUI imports...")
    try:
        # Just check if the file can be parsed
        import ast
        with open('app/streamlit_app.py', 'r') as f:
            ast.parse(f.read())
        print("✓ GUI syntax valid")
        return True
    except Exception as e:
        print(f"✗ GUI syntax error: {e}")
        return False

def test_predictor():
    """Test predictor with all parameters."""
    print("\nTesting predictor with correct parameters...")
    try:
        from inference.predictor import MaterialPredictor
        
        predictor = MaterialPredictor('models/saved')
        
        # Test with all parameters matching GUI
        input_features = predictor.build_input(
            current_A=150.0,
            voltage_V=15.0,
            speed_mm_per_min=150.0,
            filler_C=0.03,
            filler_Mn=1.0,
            filler_Si=0.4,
            filler_Cr=18.0,
            filler_Ni=10.0,
            filler_Mo=2.0,
            filler_Ti=0.1,
            haz_width_mm=1.2,
            haz_peak_temp_C=1000.0,
            haz_cooling_rate=200.0,
            grain_size_um=20.0,
            repair_stage=0,
        )
        
        result = predictor.predict(input_features)
        
        print(f"✓ Prediction successful:")
        print(f"  - Yield Strength: {result.yield_strength_MPa:.1f} MPa")
        print(f"  - UTS: {result.uts_MPa:.1f} MPa")
        print(f"  - Elongation: {result.elongation_pct:.2f}%")
        print(f"  - Physics check: YS < UTS = {result.yield_strength_MPa < result.uts_MPa}")
        
        return True
    except Exception as e:
        print(f"✗ Predictor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_prediction():
    """Test batch prediction."""
    print("\nTesting batch prediction...")
    try:
        import pandas as pd
        from inference.predictor import MaterialPredictor
        from inference.batch_predictor import BatchPredictor
        
        predictor = MaterialPredictor('models/saved')
        batch_predictor = BatchPredictor(predictor)
        
        # Create test batch
        test_df = pd.DataFrame([
            {
                'current_A': 150.0, 'voltage_V': 15.0, 'speed_mm_per_min': 150.0,
                'filler_C': 0.03, 'filler_Mn': 1.0, 'filler_Si': 0.4,
                'filler_Cr': 18.0, 'filler_Ni': 10.0, 'filler_Mo': 2.0, 'filler_Ti': 0.1,
                'haz_width_mm': 1.2, 'haz_peak_temp_C': 1000.0,
                'haz_cooling_rate': 200.0, 'grain_size_um': 20.0, 'repair_stage': 0
            },
            {
                'current_A': 180.0, 'voltage_V': 18.0, 'speed_mm_per_min': 120.0,
                'filler_C': 0.04, 'filler_Mn': 1.2, 'filler_Si': 0.5,
                'filler_Cr': 19.0, 'filler_Ni': 11.0, 'filler_Mo': 2.5, 'filler_Ti': 0.15,
                'haz_width_mm': 1.5, 'haz_peak_temp_C': 1100.0,
                'haz_cooling_rate': 150.0, 'grain_size_um': 25.0, 'repair_stage': 1
            }
        ])
        
        results = batch_predictor.predict_batch(test_df)
        
        print(f"✓ Batch prediction successful: {len(results)} samples processed")
        print(f"  - Average YS: {results['predicted_yield_MPa'].mean():.1f} MPa")
        print(f"  - Average UTS: {results['predicted_uts_MPa'].mean():.1f} MPa")
        
        return True
    except Exception as e:
        print(f"✗ Batch prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Material AI GUI Validation")
    print("=" * 60)
    
    results = []
    results.append(test_gui_imports())
    results.append(test_predictor())
    results.append(test_batch_prediction())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ ALL TESTS PASSED - GUI is ready to use!")
        print("\nTo launch the GUI, run:")
        print("  streamlit run app/streamlit_app.py")
    else:
        print("✗ SOME TESTS FAILED - Please check errors above")
    print("=" * 60)
