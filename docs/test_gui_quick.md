# Quick GUI Test - Copy & Paste Values

## Step 1: Launch GUI
```bash
streamlit run app/streamlit_app.py
```

## Step 2: Use These Values (Copy & Paste)

### Simple Test - Good Quality Weld
Just adjust the sliders to match these values:

```
Current: 180 A
Voltage: 12 V
Travel Speed: 2.5 mm/s  (note: GUI uses mm/s, data shows 150 mm/min = 2.5 mm/s)
Wire Feed Rate: 2.5 m/min
Shielding Gas Flow: 12 L/min
Preheat Temperature: 100°C
Interpass Temperature: 150°C
Heat Input: 0.86 kJ/mm
Cooling Rate: 5°C/s
HAZ Cooling Rate: 8°C/s
Base Metal Yield: 250 MPa
Base Metal UTS: 500 MPa
Repair Stage: 0
Weld Bead Width: 8 mm
Weld Bead Height: 3 mm
Dilution Ratio: 0.3
```

**Expected Output:**
- Yield Strength: ~700-750 MPa
- UTS: ~1000-1100 MPa
- Elongation: ~17-19%

---

## Step 3: Try a Repair Weld
Change only these values:

```
Repair Stage: 2  (second repair)
```

**Expected Changes:**
- Yield: slightly lower (~650-700 MPa)
- UTS: slightly lower (~950-1050 MPa)
- Elongation: slightly lower (~15-17%)

---

## Step 4: Try High Strength
Reset and use:

```
Current: 200 A
Voltage: 14 V
Travel Speed: 2.0 mm/s
Cooling Rate: 15°C/s
HAZ Cooling Rate: 20°C/s
Base Metal Yield: 300 MPa
Base Metal UTS: 600 MPa
(keep other values similar)
```

**Expected Output:**
- Higher strength (Yield ~750-850 MPa)
- Higher UTS (~1050-1150 MPa)
- Slightly lower elongation (~16-18%)

---

## What to Look For

1. **Predictions appear** within 1-2 seconds
2. **SHAP chart shows** which parameters matter most
3. **Stress-strain curve** displays smoothly
4. **Physics check passes**: Yield < UTS always
5. **No error messages** in the GUI or terminal

---

## Real Data Examples

These are actual values from the test dataset:

| Sample | Current | Voltage | Speed (mm/min) | Repair | Yield | UTS | Elongation |
|--------|---------|---------|----------------|--------|-------|-----|------------|
| LSLF_001 | 180 | 12.0 | 150 | 0 | 720 | 1050 | 18.5% |
| LSLF_002 | 200 | 14.0 | 120 | 0 | 750 | 1080 | 19.2% |
| LSLF_011 | 180 | 12.0 | 150 | 2 | 650 | 980 | 16.1% |
| LSLF_016 | 180 | 12.0 | 150 | 3 | 580 | 920 | 14.8% |

Notice how repair stage degrades properties even with same welding parameters!

---

## Quick Troubleshooting

**GUI won't start?**
```bash
pip install streamlit plotly shap
```

**Models not found?**
```bash
python main.py train
```

**Want to see all features?**
- Click through all tabs: Prediction, Explainability, Visualization, Model Info
- Try the "Export Data" button to download results
