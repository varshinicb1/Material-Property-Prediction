# Material AI - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install (1 minute)
```bash
pip install -r requirements.txt
```

### Step 2: Train Models (2 minutes)
```bash
python main.py train
```

### Step 3: Make Prediction (30 seconds)
```bash
python main.py predict --current 150 --voltage 15 --speed 150 --repair 0
```

### Step 4: Launch GUI (30 seconds)
```bash
python main.py launch-app
```

**Done!** Visit http://localhost:8501

---

## 📋 All Available Commands

```bash
# Training
python main.py train                    # Train all models
python main.py evaluate                 # Evaluate on test set
python main.py generate --n-samples 2000  # Generate data

# Prediction
python main.py predict --current 150 --voltage 15 --speed 150 --repair 0
python main.py batch-predict --input data.csv --output predictions.csv

# Interfaces
python main.py launch-app               # Streamlit GUI
python main.py api                      # REST API server

# Monitoring
python main.py metrics show             # View metrics
python main.py metrics save             # Save metrics
python main.py metrics clear            # Clear metrics
```

---

## 🎯 Common Use Cases

### Use Case 1: Predict Properties for New Weld
```bash
python main.py predict \
  --current 180 \
  --voltage 18 \
  --speed 120 \
  --repair 1
```

### Use Case 2: Batch Process Multiple Samples
```bash
# Create input CSV with columns: current_A, voltage_V, speed_mm_per_min, repair_stage
python main.py batch-predict \
  --input my_samples.csv \
  --output predictions.csv
```

### Use Case 3: Interactive Exploration
```bash
python main.py launch-app
# Adjust sliders, see real-time predictions, view SHAP explanations
```

### Use Case 4: API Integration
```bash
# Start API
python main.py api

# In another terminal or application:
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"current_A": 150, "voltage_V": 15, "speed_mm_per_min": 150, "repair_stage": 0}'
```

---

## 📊 Understanding Results

### Prediction Output
```
Yield Strength: 850.5 MPa
UTS: 920.3 MPa
Elongation: 12.5 %
YS/UTS Ratio: 0.9242
```

### What Each Means
- **Yield Strength**: Stress at which permanent deformation begins
- **UTS**: Maximum stress before failure
- **Elongation**: Total strain at break (%)
- **YS/UTS Ratio**: Lower = more ductile, Higher = more brittle

### Physics Checks
- ✅ Yield < UTS (always enforced)
- ✅ Positive values (always enforced)
- ✅ Realistic ranges (validated)

---

## 🔧 Troubleshooting

### Problem: Models not found
**Solution:**
```bash
python main.py train
```

### Problem: Import errors
**Solution:**
```bash
pip install -r requirements.txt
```

### Problem: Slow predictions
**Solution:**
- Use batch mode for multiple samples
- Enable caching (automatic)
- Use GPU if available

### Problem: API not starting
**Solution:**
```bash
# Check if port is in use
python main.py api --port 8001
```

---

## 📚 Next Steps

1. **Read Documentation**
   - `README_WORLD_CLASS.md` - Overview
   - `API_DOCUMENTATION.md` - API reference
   - `DEPLOYMENT_GUIDE.md` - Production deployment

2. **Run Tests**
   ```bash
   pytest tests/ -v
   python validate_system.py
   ```

3. **Explore Features**
   - Try different repair stages (0-3)
   - Adjust welding parameters
   - View SHAP explanations
   - Check metrics

4. **Deploy**
   - See `DEPLOYMENT_GUIDE.md`
   - Choose: Docker, K8s, or Cloud

---

## 💡 Tips & Tricks

### Tip 1: Use Repair Stages
```bash
# R0 (as-welded)
python main.py predict --repair 0

# R1 (first repair)
python main.py predict --repair 1

# R2 (second repair)
python main.py predict --repair 2

# R3 (third repair)
python main.py predict --repair 3
```

### Tip 2: Monitor Performance
```bash
# After making predictions
python main.py metrics show

# Output:
# Total Predictions: 100
# Success Rate: 99.5%
# P95 Latency: 180ms
```

### Tip 3: Save Results
In Streamlit app:
1. Make prediction
2. Go to "Stress-Strain Curve" tab
3. Click "Download CSV"

### Tip 4: Batch Processing
```python
# Create input CSV
import pandas as pd

data = {
    'current_A': [150, 160, 170],
    'voltage_V': [15, 16, 17],
    'speed_mm_per_min': [150, 140, 130],
    'repair_stage': [0, 1, 2]
}
df = pd.DataFrame(data)
df.to_csv('input.csv', index=False)

# Process
python main.py batch-predict --input input.csv --output output.csv
```

---

## 🎓 Learning Path

### Beginner (Day 1)
1. Install and train models
2. Make single predictions
3. Explore Streamlit GUI

### Intermediate (Week 1)
1. Use batch processing
2. Understand SHAP explanations
3. Try API endpoints

### Advanced (Month 1)
1. Deploy to production
2. Integrate with workflows
3. Customize and extend

---

## 📞 Getting Help

1. **Check Logs**: `logs/material_ai.log`
2. **View Metrics**: `python main.py metrics show`
3. **Read Docs**: See documentation files
4. **Run Tests**: `pytest tests/ -v`

---

## ✅ Validation Checklist

Before using in production:
- [ ] Models trained successfully
- [ ] Test prediction works
- [ ] GUI launches correctly
- [ ] API responds to requests
- [ ] Metrics tracking works
- [ ] Logs being written
- [ ] Tests passing

---

**You're ready to use Material AI!** 🚀

For detailed information, see:
- `README_WORLD_CLASS.md` - Complete overview
- `FINAL_VALIDATION_REPORT.md` - Validation results
- `DEPLOYMENT_GUIDE.md` - Production deployment
