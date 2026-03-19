"""Enhanced Professional GUI with Manual Entry and File Upload.

Features:
- Slider input (default)
- Manual text entry mode
- CSV file upload for batch predictions
- Export results
"""

from __future__ import annotations

import sys
from pathlib import Path
from io import StringIO

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Material AI | TIG Weld Property Predictor",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional styling
st.markdown("""
<style>
.main { background-color: #ffffff; font-family: 'Segoe UI', Arial, sans-serif; }
h1, h2, h3 { color: #2c3e50; font-weight: 600; }
h1 { border-bottom: 3px solid #1f77b4; padding-bottom: 10px; }
.stMetric { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
            border-left: 4px solid #1f77b4; padding: 15px; }
</style>
""", unsafe_allow_html=True)

MODELS_DIR = ROOT / "models" / "saved"

@st.cache_resource
def load_predictor():
    from inference.predictor import MaterialPredictor
    return MaterialPredictor(models_dir=str(MODELS_DIR))

@st.cache_resource
def load_explainer(_predictor):
    try:
        from explainability.shap_explainer import GBMShapExplainer
        from data.generator import get_feature_columns
        cols = get_feature_columns(50)
        return GBMShapExplainer(_predictor.gbm, cols["features"])
    except:
        return None

def render_stress_strain_curve(strain, stress, ys, uts):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=strain * 100, y=stress, mode="lines",
        name="Stress-Strain", line=dict(color="#1f77b4", width=2.5)
    ))
    ys_idx = int(np.argmin(np.abs(stress - ys)))
    fig.add_trace(go.Scatter(
        x=[strain[ys_idx] * 100], y=[ys],
        mode="markers+text", marker=dict(size=10, color="#d62728"),
        text=[f"Yield: {ys:.0f} MPa"], textposition="top center"
    ))
    uts_idx = int(np.argmax(stress))
    fig.add_trace(go.Scatter(
        x=[strain[uts_idx] * 100], y=[uts],
        mode="markers+text", marker=dict(size=10, color="#2ca02c"),
        text=[f"UTS: {uts:.0f} MPa"], textposition="top center"
    ))
    fig.update_layout(
        title="Engineering Stress-Strain Curve",
        xaxis_title="Strain (%)", yaxis_title="Stress (MPa)",
        height=500, template="plotly_white"
    )
    return fig

# Main title
st.title("Material AI: TIG Weld Property Predictor")
st.markdown("**Professional machine learning system for aerospace material property prediction**")
st.markdown("---")

# Check models
if not (MODELS_DIR / "preprocessor.pkl").exists():
    st.error("Models not found. Run: `python main.py train`")
    st.stop()

predictor = load_predictor()
explainer = load_explainer(predictor)

# Input mode selection
st.sidebar.title("Input Mode")
input_mode = st.sidebar.radio(
    "Select input method:",
    ["Sliders", "Manual Entry", "File Upload"],
    help="Choose how to provide welding parameters"
)

st.sidebar.markdown("---")

# Initialize session state for manual entry
if 'params' not in st.session_state:
    st.session_state.params = {
        'current_A': 150.0, 'voltage_V': 12.0, 'speed_mm_per_min': 150.0,
        'wire_feed_m_per_min': 2.5, 'gas_flow_L_per_min': 12.0,
        'preheat_temp_C': 100.0, 'interpass_temp_C': 150.0,
        'heat_input_kJ_per_mm': 0.6, 'cooling_rate': 5.0,
        'haz_cooling_rate': 8.0, 'base_metal_yield_MPa': 250.0,
        'base_metal_uts_MPa': 500.0, 'repair_stage': 0,
        'weld_bead_width_mm': 8.0, 'weld_bead_height_mm': 3.0,
        'dilution_ratio': 0.3
    }

params = st.session_state.params
batch_results = None

# ========== INPUT MODES ==========

if input_mode == "Sliders":
    st.sidebar.subheader("Welding Parameters")
    params['current_A'] = st.sidebar.slider("Current (A)", 80, 300, 150, 5)
    params['voltage_V'] = st.sidebar.slider("Voltage (V)", 8, 20, 12, 1)
    params['speed_mm_per_min'] = st.sidebar.slider("Travel Speed (mm/min)", 80, 300, 150, 10)
    params['wire_feed_m_per_min'] = st.sidebar.slider("Wire Feed (m/min)", 1.0, 5.0, 2.5, 0.1)
    params['gas_flow_L_per_min'] = st.sidebar.slider("Gas Flow (L/min)", 8.0, 25.0, 12.0, 0.5)
    
    st.sidebar.subheader("Thermal Parameters")
    params['preheat_temp_C'] = st.sidebar.slider("Preheat Temp (°C)", 20, 400, 100, 10)
    params['interpass_temp_C'] = st.sidebar.slider("Interpass Temp (°C)", 50, 450, 150, 10)
    params['heat_input_kJ_per_mm'] = st.sidebar.slider("Heat Input (kJ/mm)", 0.2, 4.0, 0.6, 0.1)
    params['cooling_rate'] = st.sidebar.slider("Cooling Rate (°C/s)", 1.0, 30.0, 5.0, 0.5)
    params['haz_cooling_rate'] = st.sidebar.slider("HAZ Cooling Rate (°C/s)", 2.0, 40.0, 8.0, 1.0)
    
    st.sidebar.subheader("Base Material")
    params['base_metal_yield_MPa'] = st.sidebar.slider("Base Yield (MPa)", 150, 400, 250, 10)
    params['base_metal_uts_MPa'] = st.sidebar.slider("Base UTS (MPa)", 400, 800, 500, 10)
    params['repair_stage'] = st.sidebar.selectbox("Repair Stage", [0, 1, 2, 3, 4, 5])
    
    st.sidebar.subheader("Weld Geometry")
    params['weld_bead_width_mm'] = st.sidebar.slider("Bead Width (mm)", 4.0, 15.0, 8.0, 0.5)
    params['weld_bead_height_mm'] = st.sidebar.slider("Bead Height (mm)", 1.5, 6.0, 3.0, 0.1)
    params['dilution_ratio'] = st.sidebar.slider("Dilution Ratio", 0.1, 0.6, 0.3, 0.05)
    
    predict_btn = st.sidebar.button("Predict Properties", type="primary")

elif input_mode == "Manual Entry":
    st.sidebar.subheader("Enter Values Manually")
    
    with st.sidebar.expander("Welding Parameters", expanded=True):
        params['current_A'] = st.number_input("Current (A)", 80.0, 300.0, params['current_A'])
        params['voltage_V'] = st.number_input("Voltage (V)", 8.0, 20.0, params['voltage_V'])
        params['speed_mm_per_min'] = st.number_input("Travel Speed (mm/min)", 80.0, 300.0, params['speed_mm_per_min'])
        params['wire_feed_m_per_min'] = st.number_input("Wire Feed (m/min)", 1.0, 5.0, params['wire_feed_m_per_min'])
        params['gas_flow_L_per_min'] = st.number_input("Gas Flow (L/min)", 8.0, 25.0, params['gas_flow_L_per_min'])
    
    with st.sidebar.expander("Thermal Parameters"):
        params['preheat_temp_C'] = st.number_input("Preheat Temp (°C)", 20.0, 400.0, params['preheat_temp_C'])
        params['interpass_temp_C'] = st.number_input("Interpass Temp (°C)", 50.0, 450.0, params['interpass_temp_C'])
        params['heat_input_kJ_per_mm'] = st.number_input("Heat Input (kJ/mm)", 0.2, 4.0, params['heat_input_kJ_per_mm'])
        params['cooling_rate'] = st.number_input("Cooling Rate (°C/s)", 1.0, 30.0, params['cooling_rate'])
        params['haz_cooling_rate'] = st.number_input("HAZ Cooling Rate (°C/s)", 2.0, 40.0, params['haz_cooling_rate'])
    
    with st.sidebar.expander("Base Material & Geometry"):
        params['base_metal_yield_MPa'] = st.number_input("Base Yield (MPa)", 150.0, 400.0, params['base_metal_yield_MPa'])
        params['base_metal_uts_MPa'] = st.number_input("Base UTS (MPa)", 400.0, 800.0, params['base_metal_uts_MPa'])
        params['repair_stage'] = st.selectbox("Repair Stage", [0, 1, 2, 3, 4, 5], index=params['repair_stage'])
        params['weld_bead_width_mm'] = st.number_input("Bead Width (mm)", 4.0, 15.0, params['weld_bead_width_mm'])
        params['weld_bead_height_mm'] = st.number_input("Bead Height (mm)", 1.5, 6.0, params['weld_bead_height_mm'])
        params['dilution_ratio'] = st.number_input("Dilution Ratio", 0.1, 0.6, params['dilution_ratio'])
    
    predict_btn = st.sidebar.button("Predict Properties", type="primary")

else:  # File Upload
    st.sidebar.subheader("Upload CSV File")
    st.sidebar.markdown("""
    Upload a CSV file with columns:
    - current_A, voltage_V, speed_mm_per_min
    - wire_feed_m_per_min, gas_flow_L_per_min
    - preheat_temp_C, interpass_temp_C
    - heat_input_kJ_per_mm, cooling_rate
    - haz_cooling_rate, base_metal_yield_MPa
    - base_metal_uts_MPa, repair_stage
    - weld_bead_width_mm, weld_bead_height_mm
    - dilution_ratio
    """)
    
    uploaded_file = st.sidebar.file_uploader("Choose CSV file", type=['csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.sidebar.success(f"Loaded {len(df)} samples")
            
            if st.sidebar.button("Run Batch Prediction", type="primary"):
                from inference.batch_predictor import BatchPredictor
                batch_predictor = BatchPredictor(predictor)
                
                with st.spinner(f"Processing {len(df)} samples..."):
                    batch_results = batch_predictor.predict_batch(df)
                
                st.success(f"Predicted {len(batch_results)} samples")
        except Exception as e:
            st.sidebar.error(f"Error loading file: {e}")
    
    predict_btn = False

# ========== PREDICTION ==========

if input_mode != "File Upload" and predict_btn:
    # Convert speed from mm/min to mm/s for predictor
    speed_mm_s = params['speed_mm_per_min'] / 60.0
    
    input_features = predictor.build_input(
        current_A=params['current_A'],
        voltage_V=params['voltage_V'],
        speed_mm_per_min=params['speed_mm_per_min'],
        wire_feed_m_per_min=params['wire_feed_m_per_min'],
        gas_flow_L_per_min=params['gas_flow_L_per_min'],
        preheat_temp_C=params['preheat_temp_C'],
        interpass_temp_C=params['interpass_temp_C'],
        heat_input_kJ_per_mm=params['heat_input_kJ_per_mm'],
        cooling_rate=params['cooling_rate'],
        haz_cooling_rate=params['haz_cooling_rate'],
        base_metal_yield_MPa=params['base_metal_yield_MPa'],
        base_metal_uts_MPa=params['base_metal_uts_MPa'],
        repair_stage=params['repair_stage'],
        weld_bead_width_mm=params['weld_bead_width_mm'],
        weld_bead_height_mm=params['weld_bead_height_mm'],
        dilution_ratio=params['dilution_ratio'],
    )
    
    with st.spinner("Running prediction..."):
        result = predictor.predict(input_features)
    
    # Display results
    st.subheader("Predicted Mechanical Properties")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Yield Strength", f"{result.yield_strength_MPa:.1f} MPa")
    col2.metric("UTS", f"{result.uts_MPa:.1f} MPa")
    col3.metric("Elongation", f"{result.elongation_pct:.2f} %")
    col4.metric("YS/UTS Ratio", f"{result.yield_strength_MPa / result.uts_MPa:.3f}")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["Stress-Strain Curve", "Feature Importance", "Export Data"])
    
    with tab1:
        fig = render_stress_strain_curve(result.strain, result.stress, 
                                        result.yield_strength_MPa, result.uts_MPa)
        st.plotly_chart(fig, use_container_width=True)
        
        # Physics validation
        st.subheader("Physics Validation")
        col1, col2, col3 = st.columns(3)
        col1.metric("Yield < UTS", "PASS" if result.yield_strength_MPa < result.uts_MPa else "FAIL")
        col2.metric("Elongation > 0", "PASS" if result.elongation_pct > 0 else "FAIL")
        col3.metric("UTS < 1600 MPa", "PASS" if result.uts_MPa < 1600 else "FAIL")
    
    with tab2:
        if explainer:
            try:
                shap_values = explainer.explain(input_features)
                importance_df = pd.DataFrame({
                    'Feature': explainer.feature_names,
                    'SHAP Value': shap_values[0]
                }).sort_values('SHAP Value', key=abs, ascending=False).head(10)
                
                fig = go.Figure(go.Bar(
                    x=importance_df['SHAP Value'],
                    y=importance_df['Feature'],
                    orientation='h',
                    marker=dict(color='#1f77b4')
                ))
                fig.update_layout(
                    title="Top 10 Feature Importance (SHAP)",
                    xaxis_title="SHAP Value",
                    yaxis_title="Feature",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.info("SHAP explainability not available")
        else:
            st.info("SHAP explainability not available")
    
    with tab3:
        export_df = pd.DataFrame([{
            **params,
            'predicted_yield_MPa': result.yield_strength_MPa,
            'predicted_uts_MPa': result.uts_MPa,
            'predicted_elongation_pct': result.elongation_pct
        }])
        
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="Download Prediction as CSV",
            data=csv,
            file_name="material_prediction.csv",
            mime="text/csv"
        )
        
        st.dataframe(export_df, use_container_width=True)

# ========== BATCH RESULTS ==========

if batch_results is not None:
    st.subheader(f"Batch Prediction Results ({len(batch_results)} samples)")
    
    # Summary statistics
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Yield", f"{batch_results['predicted_yield_MPa'].mean():.1f} MPa")
    col2.metric("Avg UTS", f"{batch_results['predicted_uts_MPa'].mean():.1f} MPa")
    col3.metric("Avg Elongation", f"{batch_results['predicted_elongation_pct'].mean():.2f} %")
    
    st.markdown("---")
    
    # Display table
    st.dataframe(batch_results, use_container_width=True, height=400)
    
    # Download button
    csv = batch_results.to_csv(index=False)
    st.download_button(
        label="Download Batch Results as CSV",
        data=csv,
        file_name="batch_predictions.csv",
        mime="text/csv"
    )
