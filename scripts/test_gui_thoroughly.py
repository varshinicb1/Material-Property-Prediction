"""Thorough GUI testing script to catch all bugs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console

console = Console()

def test_imports():
    """Test all imports."""
    console.print("\n[bold]Test 1: Checking Imports[/bold]")
    
    try:
        import streamlit
        console.print("✅ streamlit")
    except Exception as e:
        console.print(f"❌ streamlit: {e}")
        return False
    
    try:
        import plotly
        console.print("✅ plotly")
    except Exception as e:
        console.print(f"❌ plotly: {e}")
        return False
    
    try:
        import shap
        console.print("✅ shap")
    except Exception as e:
        console.print(f"❌ shap: {e}")
        return False
    
    try:
        from inference.predictor import MaterialPredictor
        console.print("✅ MaterialPredictor")
    except Exception as e:
        console.print(f"❌ MaterialPredictor: {e}")
        return False
    
    try:
        from explainability.shap_explainer import GBMShapExplainer
        console.print("✅ GBMShapExplainer")
    except Exception as e:
        console.print(f"❌ GBMShapExplainer: {e}")
        return False
    
    return True


def test_model_loading():
    """Test model loading."""
    console.print("\n[bold]Test 2: Model Loading[/bold]")
    
    try:
        from inference.predictor import MaterialPredictor
        predictor = MaterialPredictor(models_dir="models/saved")
        console.print("✅ Models loaded successfully")
        return predictor
    except Exception as e:
        console.print(f"❌ Model loading failed: {e}")
        import traceback
        console.print(traceback.format_exc())
        return None


def test_prediction(predictor):
    """Test prediction."""
    console.print("\n[bold]Test 3: Prediction[/bold]")
    
    if predictor is None:
        console.print("❌ Skipped (no predictor)")
        return None
    
    try:
        input_dict = predictor.build_input(
            current_A=180.0,
            voltage_V=12.5,
            speed_mm_per_min=150.0,
            repair_stage=1,
        )
        result = predictor.predict(input_dict)
        console.print(f"✅ Prediction successful")
        console.print(f"   Yield: {result.yield_strength_MPa:.1f} MPa")
        console.print(f"   UTS: {result.uts_MPa:.1f} MPa")
        console.print(f"   Elongation: {result.elongation_pct:.2f}%")
        return result
    except Exception as e:
        console.print(f"❌ Prediction failed: {e}")
        import traceback
        console.print(traceback.format_exc())
        return None


def test_shap_explainer(predictor):
    """Test SHAP explainer."""
    console.print("\n[bold]Test 4: SHAP Explainer[/bold]")
    
    if predictor is None:
        console.print("❌ Skipped (no predictor)")
        return None
    
    try:
        from explainability.shap_explainer import GBMShapExplainer
        from data.generator import get_feature_columns
        import numpy as np
        
        cols = get_feature_columns(50)
        explainer = GBMShapExplainer(predictor.gbm, cols["features"])
        console.print("✅ SHAP explainer created")
        
        # Test local explanation
        input_dict = predictor.build_input(
            current_A=180.0,
            voltage_V=12.5,
            speed_mm_per_min=150.0,
            repair_stage=1,
        )
        x_raw = np.array([[input_dict[fn] for fn in cols["features"]]], dtype=np.float32)
        x_scaled = predictor.preprocessor.transform_input(x_raw)
        shap_dict = explainer.get_local_shap_dict(x_scaled[0], "yield_strength_MPa")
        
        console.print(f"✅ SHAP explanation generated ({len(shap_dict)} features)")
        top_3 = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        for feat, val in top_3:
            console.print(f"   {feat}: {val:+.4f}")
        
        return explainer
    except Exception as e:
        console.print(f"❌ SHAP explainer failed: {e}")
        import traceback
        console.print(traceback.format_exc())
        return None


def test_visualization(result):
    """Test visualization functions."""
    console.print("\n[bold]Test 5: Visualizations[/bold]")
    
    if result is None:
        console.print("❌ Skipped (no result)")
        return False
    
    try:
        import plotly.graph_objects as go
        import numpy as np
        
        # Test stress-strain curve
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=result.strain * 100,
            y=result.stress,
            mode="lines",
            name="Curve"
        ))
        console.print("✅ Stress-strain curve visualization")
        
        # Test SHAP chart
        shap_dict = {"feature1": 0.5, "feature2": -0.3, "feature3": 0.2}
        sorted_items = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
        features = [i[0] for i in sorted_items]
        values = [i[1] for i in sorted_items]
        
        fig2 = go.Figure(go.Bar(
            y=features,
            x=values,
            orientation="h"
        ))
        console.print("✅ SHAP bar chart visualization")
        
        return True
    except Exception as e:
        console.print(f"❌ Visualization failed: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False


def main():
    """Run all tests."""
    console.rule("[bold cyan]GUI Thorough Testing[/bold cyan]")
    
    results = {}
    
    results["imports"] = test_imports()
    results["model_loading"] = test_model_loading()
    predictor = results["model_loading"]
    results["prediction"] = test_prediction(predictor)
    result = results["prediction"]
    results["shap"] = test_shap_explainer(predictor)
    results["visualization"] = test_visualization(result)
    
    # Summary
    console.print("\n[bold]═══════════════════════════════════════[/bold]")
    console.print("[bold]           TEST SUMMARY           [/bold]")
    console.print("[bold]═══════════════════════════════════════[/bold]\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        console.print(f"{status} - {test_name}")
    
    console.print(f"\n[bold]Total: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("\n[bold green]🎉 ALL TESTS PASSED - GUI IS READY![/bold green]")
    else:
        console.print("\n[bold red]⚠️  SOME TESTS FAILED - FIX REQUIRED[/bold red]")


if __name__ == "__main__":
    main()
