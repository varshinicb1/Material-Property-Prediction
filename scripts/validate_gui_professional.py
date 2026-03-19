#!/usr/bin/env python3
"""
Validate Professional GUI - Quick Check
Tests that the professional GUI can be imported and has no syntax errors.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_gui_import():
    """Test that the GUI module can be imported without errors."""
    try:
        # This will catch any syntax errors or import issues
        import app.streamlit_app
        print("✅ GUI module imports successfully")
        return True
    except Exception as e:
        print(f"❌ GUI import failed: {e}")
        return False

def test_plotly_compatibility():
    """Test that Plotly code is compatible."""
    try:
        import plotly.graph_objects as go
        
        # Test the new title format (should work)
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(
                title=dict(text="Test", font=dict(size=12))
            )
        )
        print("✅ Plotly title format is correct")
        return True
    except Exception as e:
        print(f"❌ Plotly compatibility issue: {e}")
        return False

def main():
    print("=" * 60)
    print("Professional GUI Validation")
    print("=" * 60)
    
    tests = [
        ("GUI Import", test_gui_import),
        ("Plotly Compatibility", test_plotly_compatibility),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nTest: {name}")
        results.append(test_func())
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 GUI is ready for professional use!")
        return 0
    else:
        print("\n⚠️ Some issues detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())
