# GUI Launch Guide

## Quick Start

Launch the professional Material AI GUI:

```bash
streamlit run app/streamlit_app.py
```

The GUI will open in your browser at `http://localhost:8501`

## Features

### Three Input Modes

1. **Sliders** (Default)
   - Interactive sliders for all parameters
   - Real-time heat input calculation
   - Best for exploration and sensitivity analysis

2. **Manual Entry**
   - Precise numeric input fields
   - Expandable sections for organization
   - Best for specific known values

3. **File Upload**
   - Batch prediction from CSV files
   - Process multiple samples at once
   - Download results as CSV

### What You'll See

- **Predicted Properties**: Yield Strength, UTS, Elongation, YS/UTS Ratio
- **Stress-Strain Curve**: Interactive Plotly visualization with marked yield and UTS points
- **Feature Importance**: SHAP values showing which parameters matter most
- **Physics Validation**: Automatic checks (YS < UTS, Elongation > 0, etc.)
- **Export**: Download predictions as CSV

## Default Parameters

The GUI loads with sensible defaults for 316L stainless steel TIG welding:

```
Welding Parameters:
- Current: 150 A
- Voltage: 15 V
- Travel Speed: 150 mm/min
- Heat Input: ~0.9 kJ/mm

Filler Composition (wt%):
- C: 0.03%, Mn: 1.0%, Si: 0.4%
- Cr: 18.0%, Ni: 10.0%, Mo: 2.0%
- Ti: 0.1%

HAZ Characteristics:
- Width: 1.2 mm
- Peak Temperature: 1000°C
- Cooling Rate: 200°C/s
- Grain Size: 20 μm

Repair Stage: R0 (As-welded)
```

## Expected Results (Default Parameters)

With default parameters, you should see approximately:

- **Yield Strength**: ~800 MPa
- **UTS**: ~1050 MPa
- **Elongation**: ~19%
- **YS/UTS Ratio**: ~0.76

## Testing Different Scenarios

### High Heat Input (Softer Material)
- Current: 200 A
- Voltage: 20 V
- Speed: 100 mm/min
- Expected: Lower strength, higher ductility

### Low Heat Input (Harder Material)
- Current: 100 A
- Voltage: 12 V
- Speed: 200 mm/min
- Expected: Higher strength, lower ductility

### Repair Stages
- R0: As-welded baseline
- R1-R3: Progressive repair stages (typically show degradation)

## Batch Prediction

### CSV Format

Create a CSV file with these columns:

```csv
current_A,voltage_V,speed_mm_per_min,filler_C,filler_Mn,filler_Si,filler_Cr,filler_Ni,filler_Mo,filler_Ti,haz_width_mm,haz_peak_temp_C,haz_cooling_rate,grain_size_um,repair_stage
150,15,150,0.03,1.0,0.4,18.0,10.0,2.0,0.1,1.2,1000,200,20,0
180,18,120,0.04,1.2,0.5,19.0,11.0,2.5,0.15,1.5,1100,150,25,1
```

### Steps

1. Select "File Upload" mode
2. Click "Choose CSV file"
3. Upload your CSV
4. Click "Run Batch Prediction"
5. Download results with predictions added

## Validation Test

Before launching the GUI, you can run the validation test:

```bash
python test_gui.py
```

This checks:
- GUI syntax is valid
- Predictor works with correct parameters
- Batch prediction functions properly

## Troubleshooting

### Models Not Found

If you see "Models not found", train them first:

```bash
python main.py train
```

This takes ~5-10 minutes and generates:
- Training data (5000 samples)
- Trained GBM, FT-Transformer, and CVAE models
- Preprocessor for feature scaling

### SHAP Explainability Unavailable

If SHAP doesn't work, install it:

```bash
pip install shap
```

### Port Already in Use

If port 8501 is busy, specify a different port:

```bash
streamlit run app/streamlit_app.py --server.port 8502
```

## Performance

- **Single Prediction**: ~18ms
- **Batch (100 samples)**: ~2 seconds
- **Model Loading**: ~1 second (cached after first load)

## Browser Compatibility

Tested and working on:
- Chrome/Edge (recommended)
- Firefox
- Safari

## Next Steps

After testing the GUI:

1. Try different parameter combinations
2. Upload your own welding data
3. Export predictions for further analysis
4. Share the GitHub repo: https://github.com/varshinicb1/Material-Property-Prediction

---

**Material AI v1.0.0** | Professional ML for TIG Weld Property Prediction
