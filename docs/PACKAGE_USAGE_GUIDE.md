# Material AI - Python Package Usage Guide

## Yes! Anyone Can Install It

Material AI is a proper Python package that can be installed and used by anyone, anywhere.

## Installation Methods

### Method 1: Install from GitHub (Recommended)

```bash
pip install git+https://github.com/varshinicb1/Material-Property-Prediction.git
```

This installs the latest version directly from GitHub.

### Method 2: Clone and Install Locally

```bash
# Clone repository
git clone https://github.com/varshinicb1/Material-Property-Prediction.git
cd Material-Property-Prediction

# Install in development mode
pip install -e .

# Or install with optional features
pip install -e .[gui,api]
```

### Method 3: Install Specific Version

```bash
# Install specific release
pip install git+https://github.com/varshinicb1/Material-Property-Prediction.git@v1.0.0
```

## What Gets Installed

When you install Material AI, you get:

1. **Core Package**: `material_ai` module
2. **Command-line tool**: `material-ai` command
3. **All dependencies**: Automatically installed
4. **Optional features**: GUI, API (if specified)

## Basic Usage

### 1. Import and Use in Python

```python
# Import the package
from material_ai import MaterialPredictor

# Initialize predictor
predictor = MaterialPredictor(models_dir="models/saved")

# Build input features
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

# Predict properties
result = predictor.predict(features)

# Access results
print(f"Yield Strength: {result.yield_strength_MPa:.1f} MPa")
print(f"UTS: {result.uts_MPa:.1f} MPa")
print(f"Elongation: {result.elongation_pct:.2f}%")

# Access stress-strain curve
print(f"Strain values: {result.strain}")
print(f"Stress values: {result.stress}")
```

### 2. Batch Prediction

```python
from material_ai import BatchPredictor
import pandas as pd

# Load your data
df = pd.read_csv("welding_parameters.csv")

# Initialize batch predictor
batch_predictor = BatchPredictor(predictor)

# Predict for all samples
results = batch_predictor.predict_batch(df)

# Save results
results.to_csv("predictions.csv", index=False)
```

### 3. Use in Your Own Application

```python
# Example: Flask web app
from flask import Flask, request, jsonify
from material_ai import MaterialPredictor

app = Flask(__name__)
predictor = MaterialPredictor()

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    features = predictor.build_input(**data)
    result = predictor.predict(features)
    
    return jsonify({
        'yield_strength_MPa': result.yield_strength_MPa,
        'uts_MPa': result.uts_MPa,
        'elongation_pct': result.elongation_pct
    })

if __name__ == '__main__':
    app.run()
```

### 4. Use in Jupyter Notebook

```python
# Install in notebook
!pip install git+https://github.com/varshinicb1/Material-Property-Prediction.git

# Import and use
from material_ai import MaterialPredictor
import matplotlib.pyplot as plt

predictor = MaterialPredictor()

# Make prediction
features = predictor.build_input(
    current_A=180, voltage_V=12, speed_mm_per_min=150,
    # ... other parameters
)
result = predictor.predict(features)

# Plot stress-strain curve
plt.figure(figsize=(10, 6))
plt.plot(result.strain * 100, result.stress)
plt.xlabel('Strain (%)')
plt.ylabel('Stress (MPa)')
plt.title('Predicted Stress-Strain Curve')
plt.grid(True)
plt.show()
```

### 5. Use in Data Science Pipeline

```python
from material_ai import MaterialPredictor
import pandas as pd
from sklearn.model_selection import train_test_split

# Load experimental data
data = pd.read_csv("experiments.csv")

# Initialize predictor
predictor = MaterialPredictor()

# Predict for all experiments
predictions = []
for _, row in data.iterrows():
    features = predictor.build_input(**row.to_dict())
    result = predictor.predict(features)
    predictions.append({
        'predicted_yield': result.yield_strength_MPa,
        'predicted_uts': result.uts_MPa,
        'predicted_elongation': result.elongation_pct
    })

# Compare with actual values
pred_df = pd.DataFrame(predictions)
comparison = pd.concat([data, pred_df], axis=1)
comparison.to_csv("prediction_comparison.csv")
```

## Command-Line Usage

After installation, you can use the `material-ai` command:

```bash
# Train models
material-ai train

# Make prediction
material-ai predict --current 180 --voltage 12 --speed 150

# Batch prediction
material-ai batch-predict --input data.csv --output results.csv

# Start API server
material-ai api

# View metrics
material-ai metrics
```

## Integration Examples

### Example 1: Custom GUI with Tkinter

```python
import tkinter as tk
from material_ai import MaterialPredictor

class MaterialAIApp:
    def __init__(self, root):
        self.root = root
        self.predictor = MaterialPredictor()
        
        # Create input fields
        tk.Label(root, text="Current (A):").grid(row=0, column=0)
        self.current = tk.Entry(root)
        self.current.grid(row=0, column=1)
        
        # ... more fields
        
        # Predict button
        tk.Button(root, text="Predict", command=self.predict).grid(row=10, column=0)
        
        # Results
        self.result_label = tk.Label(root, text="")
        self.result_label.grid(row=11, column=0, columnspan=2)
    
    def predict(self):
        features = self.predictor.build_input(
            current_A=float(self.current.get()),
            # ... other parameters
        )
        result = self.predictor.predict(features)
        self.result_label.config(
            text=f"Yield: {result.yield_strength_MPa:.1f} MPa, "
                 f"UTS: {result.uts_MPa:.1f} MPa"
        )

root = tk.Tk()
app = MaterialAIApp(root)
root.mainloop()
```

### Example 2: REST API with FastAPI

```python
from fastapi import FastAPI
from pydantic import BaseModel
from material_ai import MaterialPredictor

app = FastAPI()
predictor = MaterialPredictor()

class WeldingParams(BaseModel):
    current_A: float
    voltage_V: float
    speed_mm_per_min: float
    # ... other fields

@app.post("/predict")
def predict(params: WeldingParams):
    features = predictor.build_input(**params.dict())
    result = predictor.predict(features)
    return {
        "yield_strength_MPa": result.yield_strength_MPa,
        "uts_MPa": result.uts_MPa,
        "elongation_pct": result.elongation_pct
    }
```

### Example 3: Optimization Loop

```python
from material_ai import MaterialPredictor
from scipy.optimize import minimize
import numpy as np

predictor = MaterialPredictor()

def objective(params):
    """Maximize UTS while maintaining yield > 600 MPa"""
    current, voltage, speed = params
    
    features = predictor.build_input(
        current_A=current,
        voltage_V=voltage,
        speed_mm_per_min=speed,
        # ... fixed parameters
    )
    result = predictor.predict(features)
    
    # Penalty if yield too low
    penalty = 0 if result.yield_strength_MPa > 600 else 1000
    
    # Maximize UTS (minimize negative UTS)
    return -result.uts_MPa + penalty

# Optimize
initial = [180, 12, 150]
bounds = [(80, 300), (8, 20), (80, 300)]
result = minimize(objective, initial, bounds=bounds)

print(f"Optimal parameters: Current={result.x[0]:.1f}A, "
      f"Voltage={result.x[1]:.1f}V, Speed={result.x[2]:.1f}mm/min")
```

## Requirements

### Minimum Requirements
- Python 3.8 or higher
- 2GB RAM
- Internet connection (for installation)

### Dependencies (Automatically Installed)
- numpy
- pandas
- scikit-learn
- lightgbm
- torch
- pyyaml
- joblib

### Optional Dependencies
```bash
# For GUI
pip install material-ai[gui]

# For API
pip install material-ai[api]

# For development
pip install material-ai[dev]

# All features
pip install material-ai[gui,api,dev]
```

## First-Time Setup

After installation, you need to train the models:

```bash
# Clone repository (if not already done)
git clone https://github.com/varshinicb1/Material-Property-Prediction.git
cd Material-Property-Prediction

# Train models
python main.py train

# Or use command-line tool
material-ai train
```

This creates trained models in `models/saved/` directory.

## Verification

Test your installation:

```python
# Test import
import material_ai
print(f"Material AI version: {material_ai.__version__}")

# Test predictor
from material_ai import MaterialPredictor
predictor = MaterialPredictor()
print("Installation successful!")
```

## Troubleshooting

### Issue: ModuleNotFoundError

```bash
# Ensure package is installed
pip install git+https://github.com/varshinicb1/Material-Property-Prediction.git
```

### Issue: Models not found

```bash
# Train models first
cd Material-Property-Prediction
python main.py train
```

### Issue: Import errors

```bash
# Reinstall with dependencies
pip install --upgrade git+https://github.com/varshinicb1/Material-Property-Prediction.git
```

## Use Cases

### 1. Research
```python
# Use in research paper
from material_ai import MaterialPredictor

predictor = MaterialPredictor()
# Run experiments, generate figures
```

### 2. Manufacturing
```python
# Quality control system
from material_ai import MaterialPredictor

def check_weld_quality(params):
    predictor = MaterialPredictor()
    features = predictor.build_input(**params)
    result = predictor.predict(features)
    
    # Check if meets specifications
    if result.yield_strength_MPa < 600:
        return "REJECT"
    return "ACCEPT"
```

### 3. Education
```python
# Teaching tool
from material_ai import MaterialPredictor

def demonstrate_welding_effects():
    predictor = MaterialPredictor()
    
    # Show effect of current
    for current in [100, 150, 200, 250]:
        features = predictor.build_input(current_A=current, ...)
        result = predictor.predict(features)
        print(f"Current {current}A: Yield={result.yield_strength_MPa:.1f} MPa")
```

### 4. Process Optimization
```python
# Automated parameter tuning
from material_ai import MaterialPredictor
import optuna

predictor = MaterialPredictor()

def optimize_welding(trial):
    current = trial.suggest_float('current', 80, 300)
    voltage = trial.suggest_float('voltage', 8, 20)
    speed = trial.suggest_float('speed', 80, 300)
    
    features = predictor.build_input(
        current_A=current, voltage_V=voltage, 
        speed_mm_per_min=speed, ...
    )
    result = predictor.predict(features)
    
    # Optimize for high UTS
    return result.uts_MPa

study = optuna.create_study(direction='maximize')
study.optimize(optimize_welding, n_trials=100)
```

## Distribution

You can also distribute your own applications that use Material AI:

```python
# In your setup.py
setup(
    name="my-welding-app",
    install_requires=[
        "material-ai @ git+https://github.com/varshinicb1/Material-Property-Prediction.git",
        # ... other dependencies
    ]
)
```

## Summary

**Yes, anyone can install Material AI as a Python package!**

- ✅ Install with one command: `pip install git+https://github.com/...`
- ✅ Use in any Python application
- ✅ Import like any other package: `from material_ai import MaterialPredictor`
- ✅ Works in Jupyter, scripts, web apps, GUIs, etc.
- ✅ No license restrictions (MIT license)
- ✅ Free forever
- ✅ Open source

**Installation is as simple as:**
```bash
pip install git+https://github.com/varshinicb1/Material-Property-Prediction.git
```

**Usage is as simple as:**
```python
from material_ai import MaterialPredictor
predictor = MaterialPredictor()
result = predictor.predict(features)
```

That's it! Anyone, anywhere can use it.
