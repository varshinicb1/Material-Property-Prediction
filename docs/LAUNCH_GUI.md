# Professional GUI Launch Guide

## Quick Start

Launch the professional Material AI interface:

```bash
streamlit run app/streamlit_app.py
```

The GUI will open in your browser at `http://localhost:8501`

## Professional Features

### Design Philosophy
- Clean, scientific aesthetic designed for engineers and materials scientists
- Professional color scheme (blues, grays, white backgrounds)
- Engineering-appropriate typography and spacing
- Industry-standard Plotly visualizations
- No emojis or casual elements

### Capabilities

1. **Material Property Prediction**
   - Input welding parameters via sliders
   - Real-time predictions for Yield Strength, UTS, Elongation
   - Physics validation (Yield < UTS)
   - Confidence intervals

2. **SHAP Explainability**
   - Feature importance analysis
   - Understand which parameters drive predictions
   - Professional bar charts with scientific notation

3. **Stress-Strain Visualization**
   - Ramberg-Osgood curve generation
   - Engineering stress-strain relationships
   - Professional plotting with proper units

4. **Model Comparison**
   - Performance metrics for all models
   - R² scores, MAE, RMSE
   - Training/validation/test results

5. **Data Export**
   - Download predictions as CSV
   - Export for further analysis
   - Integration with other tools

## System Requirements

- Python 3.8+
- All dependencies installed (see requirements.txt)
- Trained models in `models/saved/`

## Troubleshooting

If you see warnings about `use_container_width`, these are harmless deprecation notices and don't affect functionality.

If models fail to load, ensure you've trained them first:
```bash
python main.py train
```

## Performance

- Prediction latency: ~18ms
- Throughput: ~54 predictions/second
- Memory efficient caching for SHAP
- Responsive UI even with complex visualizations
