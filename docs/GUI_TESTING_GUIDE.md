# GUI Testing Guide - Realistic Parameter Values

## How to Launch

```bash
streamlit run app/streamlit_app.py
```

The GUI will open at `http://localhost:8501`

## Realistic Test Cases

### Test Case 1: Standard TIG Welding (Baseline)
**Scenario:** Typical TIG weld on stainless steel, no repair

```
Current (A): 150
Voltage (V): 12
Travel Speed (mm/s): 3
Wire Feed Rate (m/min): 2.5
Shielding Gas Flow (L/min): 12
Preheat Temperature (°C): 100
Interpass Temperature (°C): 150
Heat Input (kJ/mm): 0.6
Cooling Rate (°C/s): 5
HAZ Cooling Rate (°C/s): 8
Base Metal Yield (MPa): 250
Base Metal UTS (MPa): 500
Repair Stage: 0 (no repair)
Weld Bead Width (mm): 8
Weld Bead Height (mm): 3
Dilution Ratio: 0.3
```

**Expected Results:**
- Yield: ~600-800 MPa
- UTS: ~900-1100 MPa
- Elongation: ~15-20%

---

### Test Case 2: High-Strength Weld (Aggressive Parameters)
**Scenario:** Fast cooling, high heat input for strength

```
Current (A): 200
Voltage (V): 15
Travel Speed (mm/s): 2
Wire Feed Rate (m/min): 3.5
Shielding Gas Flow (L/min): 15
Preheat Temperature (°C): 50
Interpass Temperature (°C): 100
Heat Input (kJ/mm): 1.5
Cooling Rate (°C/s): 15
HAZ Cooling Rate (°C/s): 20
Base Metal Yield (MPa): 300
Base Metal UTS (MPa): 600
Repair Stage: 0
Weld Bead Width (mm): 10
Weld Bead Height (mm): 4
Dilution Ratio: 0.4
```

**Expected Results:**
- Yield: ~700-900 MPa
- UTS: ~1000-1200 MPa
- Elongation: ~12-18%

---

### Test Case 3: Ductile Weld (Low Cooling Rate)
**Scenario:** Slow cooling for maximum ductility

```
Current (A): 120
Voltage (V): 10
Travel Speed (mm/s): 4
Wire Feed Rate (m/min): 2.0
Shielding Gas Flow (L/min): 10
Preheat Temperature (°C): 200
Interpass Temperature (°C): 250
Heat Input (kJ/mm): 0.3
Cooling Rate (°C/s): 2
HAZ Cooling Rate (°C/s): 3
Base Metal Yield (MPa): 200
Base Metal UTS (MPa): 450
Repair Stage: 0
Weld Bead Width (mm): 6
Weld Bead Height (mm): 2.5
Dilution Ratio: 0.25
```

**Expected Results:**
- Yield: ~500-700 MPa
- UTS: ~800-1000 MPa
- Elongation: ~18-25%

---

### Test Case 4: Repair Weld (2nd Stage)
**Scenario:** Second repair on existing weld

```
Current (A): 140
Voltage (V): 11
Travel Speed (mm/s): 3.5
Wire Feed Rate (m/min): 2.2
Shielding Gas Flow (L/min): 12
Preheat Temperature (°C): 150
Interpass Temperature (°C): 180
Heat Input (kJ/mm): 0.44
Cooling Rate (°C/s): 6
HAZ Cooling Rate (°C/s): 10
Base Metal Yield (MPa): 280
Base Metal UTS (MPa): 550
Repair Stage: 2
Weld Bead Width (mm): 7
Weld Bead Height (mm): 3
Dilution Ratio: 0.35
```

**Expected Results:**
- Yield: ~650-850 MPa (higher due to repair hardening)
- UTS: ~950-1150 MPa
- Elongation: ~14-19%

---

### Test Case 5: Extreme Parameters (Edge Case)
**Scenario:** Testing model limits

```
Current (A): 250
Voltage (V): 18
Travel Speed (mm/s): 1.5
Wire Feed Rate (m/min): 4.5
Shielding Gas Flow (L/min): 20
Preheat Temperature (°C): 300
Interpass Temperature (°C): 350
Heat Input (kJ/mm): 3.0
Cooling Rate (°C/s): 25
HAZ Cooling Rate (°C/s): 35
Base Metal Yield (MPa): 350
Base Metal UTS (MPa): 700
Repair Stage: 3
Weld Bead Width (mm): 12
Weld Bead Height (mm): 5
Dilution Ratio: 0.5
```

**Expected Results:**
- Yield: ~800-1000 MPa
- UTS: ~1100-1300 MPa
- Elongation: ~10-16%

---

## What to Check

### 1. Physics Validation
- **Yield < UTS**: Always true (model enforces this)
- **Reasonable Elongation**: 10-30% typical for welds

### 2. SHAP Explanations
Look at which features are most important:
- `haz_cooling_rate` - Usually high impact
- `repair_stage` - Significant for repairs
- `heat_input_kJ_per_mm` - Major influence
- `base_metal_yield_MPa` - Foundation property

### 3. Stress-Strain Curve
- Should show smooth curve
- Yield point visible
- UTS at peak
- Elongation at failure

### 4. Model Comparison
- Check R² scores (should be 0.6-0.8)
- Compare predictions across models
- Ensemble should be most reliable

---

## Parameter Ranges (Valid Inputs)

```
Current: 80-300 A
Voltage: 8-20 V
Travel Speed: 1-6 mm/s
Wire Feed Rate: 1-5 m/min
Shielding Gas Flow: 8-25 L/min
Preheat Temperature: 20-400°C
Interpass Temperature: 50-450°C
Heat Input: 0.2-4.0 kJ/mm
Cooling Rate: 1-30°C/s
HAZ Cooling Rate: 2-40°C/s
Base Metal Yield: 150-400 MPa
Base Metal UTS: 400-800 MPa
Repair Stage: 0-5
Weld Bead Width: 4-15 mm
Weld Bead Height: 1.5-6 mm
Dilution Ratio: 0.1-0.6
```

---

## Quick Test Workflow

1. **Launch GUI**: `streamlit run app/streamlit_app.py`
2. **Use Test Case 1** (baseline values above)
3. **Click "Predict Properties"**
4. **Check results**:
   - Predictions appear
   - SHAP chart shows
   - Stress-strain curve renders
   - No errors in console
5. **Try adjusting one parameter** (e.g., increase cooling rate)
6. **Observe changes** in predictions and explanations
7. **Export data** using download button

---

## Troubleshooting

**Models not loading?**
```bash
python main.py train
```

**SHAP not working?**
```bash
pip install shap
```

**Slow predictions?**
- First prediction is slower (model loading)
- Subsequent predictions are fast (~18ms)

**Unrealistic results?**
- Check parameter ranges above
- Extreme combinations may give unexpected results
- Model trained on realistic welding data
