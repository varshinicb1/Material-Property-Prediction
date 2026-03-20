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
        'current_A': 150.0,
        'voltage_V': 15.0,
        'speed_mm_per_min': 150.0,
        'filler_C': 0.03,
        'filler_Mn': 1.0,
        'filler_Si': 0.4,
        'filler_Cr': 18.0,
        'filler_Ni': 10.0,
        'filler_Mo': 2.0,
        'filler_Ti': 0.1,
        'haz_width_mm': 1.2,
        'haz_peak_temp_C': 1000.0,
        'haz_cooling_rate': 200.0,
        'grain_size_um': 20.0,
        'repair_stage': 0,
    }

params = st.session_state.params
batch_results = None

# ========== INPUT MODES ==========

if input_mode == "Sliders":
    st.sidebar.subheader("Welding Parameters")
    params['current_A'] = float(st.sidebar.slider("Current (A)", 80, 220, 150, 5))
    params['voltage_V'] = float(st.sidebar.slider("Voltage (V)", 10, 25, 15, 1))
    params['speed_mm_per_min'] = float(st.sidebar.slider("Travel Speed (mm/min)", 80, 300, 150, 10))
    
    heat_input = (params['current_A'] * params['voltage_V'] * 60.0) / (1000.0 * params['speed_mm_per_min'])
    st.sidebar.metric("Heat Input", f"{heat_input:.3f} kJ/mm")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filler Composition (wt%)")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        params['filler_C'] = st.slider("C", 0.01, 0.08, 0.03, 0.01, format="%.3f")
        params['filler_Mn'] = st.slider("Mn", 0.5, 2.0, 1.0, 0.1)
        params['filler_Si'] = st.slider("Si", 0.1, 0.8, 0.4, 0.05)
        params['filler_Cr'] = st.slider("Cr", 14.0, 25.0, 18.0, 0.5)
    with col2:
        params['filler_Ni'] = st.slider("Ni", 8.0, 20.0, 10.0, 0.5)
        params['filler_Mo'] = st.slider("Mo", 0.0, 4.0, 2.0, 0.1)
        params['filler_Ti'] = st.slider("Ti", 0.0, 0.5, 0.1, 0.01, format="%.3f")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("HAZ Characteristics")
    params['haz_width_mm'] = st.sidebar.slider("HAZ Width (mm)", 0.2, 3.5, 1.2, 0.1)
    params['haz_peak_temp_C'] = float(st.sidebar.slider("Peak Temperature (°C)", 600, 1400, 1000, 50))
    params['haz_cooling_rate'] = float(st.sidebar.slider("Cooling Rate (°C/s)", 10, 2000, 200, 10))
    params['grain_size_um'] = float(st.sidebar.slider("Grain Size (μm)", 2, 80, 20, 1))
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Repair Stage")
    params['repair_stage'] = st.sidebar.selectbox(
        "Stage",
        options=[0, 1, 2, 3],
        format_func=lambda x: f"R{x} - {'As-welded' if x == 0 else f'Repair {x}'}",
    )
    
    predict_btn = st.sidebar.button("Predict Properties", type="primary")

elif input_mode == "Manual Entry":
    st.sidebar.subheader("Enter Values Manually")
    
    with st.sidebar.expander("Welding Parameters", expanded=True):
        params['current_A'] = st.number_input("Current (A)", 80.0, 220.0, float(params['current_A']))
        params['voltage_V'] = st.number_input("Voltage (V)", 10.0, 25.0, float(params['voltage_V']))
        params['speed_mm_per_min'] = st.number_input("Travel Speed (mm/min)", 80.0, 300.0, float(params['speed_mm_per_min']))
    
    with st.sidebar.expander("Filler Composition (wt%)"):
        params['filler_C'] = st.number_input("C", 0.01, 0.08, float(params['filler_C']), format="%.3f")
        params['filler_Mn'] = st.number_input("Mn", 0.5, 2.0, float(params['filler_Mn']))
        params['filler_Si'] = st.number_input("Si", 0.1, 0.8, float(params['filler_Si']))
        params['filler_Cr'] = st.number_input("Cr", 14.0, 25.0, float(params['filler_Cr']))
        params['filler_Ni'] = st.number_input("Ni", 8.0, 20.0, float(params['filler_Ni']))
        params['filler_Mo'] = st.number_input("Mo", 0.0, 4.0, float(params['filler_Mo']))
        params['filler_Ti'] = st.number_input("Ti", 0.0, 0.5, float(params['filler_Ti']), format="%.3f")
    
    with st.sidebar.expander("HAZ Characteristics"):
        params['haz_width_mm'] = st.number_input("HAZ Width (mm)", 0.2, 3.5, float(params['haz_width_mm']))
        params['haz_peak_temp_C'] = st.number_input("Peak Temperature (°C)", 600.0, 1400.0, float(params['haz_peak_temp_C']))
        params['haz_cooling_rate'] = st.number_input("Cooling Rate (°C/s)", 10.0, 2000.0, float(params['haz_cooling_rate']))
        params['grain_size_um'] = st.number_input("Grain Size (μm)", 2.0, 80.0, float(params['grain_size_um']))
        params['repair_stage'] = st.selectbox("Repair Stage", [0, 1, 2, 3], index=int(params['repair_stage']))
    
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

# Auto-run prediction with default values or when button is clicked
should_predict = predict_btn or (input_mode != "File Upload" and 'last_prediction' not in st.session_state)

if input_mode != "File Upload" and should_predict:
    # Mark that we've done initial prediction
    if 'last_prediction' not in st.session_state:
        st.session_state.last_prediction = True
    
    # Convert speed from mm/min to mm/s for predictor
    speed_mm_s = params['speed_mm_per_min'] / 60.0
    
    try:
        input_features = predictor.build_input(
            current_A=params['current_A'],
            voltage_V=params['voltage_V'],
            speed_mm_per_min=params['speed_mm_per_min'],
            filler_C=params['filler_C'],
            filler_Mn=params['filler_Mn'],
            filler_Si=params['filler_Si'],
            filler_Cr=params['filler_Cr'],
            filler_Ni=params['filler_Ni'],
            filler_Mo=params['filler_Mo'],
            filler_Ti=params['filler_Ti'],
            haz_width_mm=params['haz_width_mm'],
            haz_peak_temp_C=params['haz_peak_temp_C'],
            haz_cooling_rate=params['haz_cooling_rate'],
            grain_size_um=params['grain_size_um'],
            repair_stage=params['repair_stage'],
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
    
    except Exception as e:
        st.error(f"Prediction failed: {e}")
        st.info("Please check that models are trained. Run: python main.py train")

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
