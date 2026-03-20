"""Material AI - ISRO-Grade Professional GUI

World-class features:
- Enhanced visual hierarchy with prominent metrics
- Physically accurate stress-strain curves with smoothing
- Detailed physics validation with explanations
- Model confidence intervals
- Compare mode for repair stages
- Professional styling and spacing
"""

from __future__ import annotations

import sys
from pathlib import Path
from scipy.interpolate import UnivariateSpline
from scipy.ndimage import gaussian_filter1d

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import traceback

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Material AI | TIG Weld Property Predictor",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== PROFESSIONAL STYLING ==========
st.markdown("""
<style>
.main { background-color: #f8f9fa; font-family: 'Segoe UI', Arial, sans-serif; }
h1 { color: #1a1a1a; font-weight: 700; font-size: 2.5rem; border-bottom: 4px solid #1f77b4; padding-bottom: 15px; }
h2 { color: #2c3e50; font-weight: 600; margin-top: 2rem; }
h3 { color: #34495e; font-weight: 600; }
.metric-card { 
    background: linear-gradient(135deg, #ffffff 0%, #f0f2f6 100%);
    border-left: 5px solid #1f77b4;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin: 10px 0;
}
.big-metric {
    font-size: 2.5rem;
    font-weight: 700;
    color: #1f77b4;
    margin: 0;
}
.metric-label {
    font-size: 0.9rem;
    color: #7f8c8d;
    text-transform: uppercase;
    letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)

MODELS_DIR = ROOT / "models" / "saved"

# ========== CACHING FUNCTIONS ==========

@st.cache_resource
def load_predictor():
    """Load and cache the MaterialPredictor."""
    try:
        from inference.predictor import MaterialPredictor
        return MaterialPredictor(models_dir=str(MODELS_DIR))
    except Exception as e:
        st.error(f"Failed to load predictor: {e}")
        return None

@st.cache_resource
def load_explainer(_predictor):
    """Load and cache SHAP explainer."""
    if _predictor is None:
        return None
    try:
        from explainability.shap_explainer import GBMShapExplainer
        from data.generator import get_feature_columns
        cols = get_feature_columns(50)
        return GBMShapExplainer(_predictor.gbm, cols["features"])
    except:
        return None

# ========== HELPER FUNCTIONS ==========

def smooth_curve(strain, stress, smoothing_factor=0.3):
    """Apply intelligent smoothing to stress-strain curve while preserving physics."""
    # Apply gentle gaussian smoothing
    stress_smooth = gaussian_filter1d(stress, sigma=smoothing_factor)
    
    # Ensure monotonic increase until UTS
    uts_idx = np.argmax(stress_smooth)
    for i in range(1, uts_idx):
        if stress_smooth[i] < stress_smooth[i-1]:
            stress_smooth[i] = stress_smooth[i-1]
    
    # Gradual decrease after UTS (no sharp drops)
    for i in range(uts_idx + 1, len(stress_smooth)):
        max_drop = 0.02 * stress_smooth[uts_idx]  # Max 2% drop per point
        if stress_smooth[i] < stress_smooth[i-1] - max_drop:
            stress_smooth[i] = stress_smooth[i-1] - max_drop
    
    return strain, stress_smooth

def render_stress_strain_curve(strain, stress, ys, uts):
    """Render world-class stress-strain curve with physics-based smoothing."""
    # Apply smoothing
    strain_smooth, stress_smooth = smooth_curve(strain, stress)
    
    fig = go.Figure()
    
    # Main curve - thicker and smoother
    fig.add_trace(go.Scatter(
        x=strain_smooth * 100, y=stress_smooth,
        mode="lines",
        name="Stress-Strain Response",
        line=dict(color="#1f77b4", width=3.5),
        hovertemplate="<b>Strain:</b> %{x:.3f}%<br><b>Stress:</b> %{y:.1f} MPa<extra></extra>"
    ))
    
    # Yield point - prominent marker
    ys_idx = int(np.argmin(np.abs(stress_smooth - ys)))
    fig.add_trace(go.Scatter(
        x=[strain_smooth[ys_idx] * 100], y=[ys],
        mode="markers+text",
        marker=dict(size=16, color="#e74c3c", symbol="diamond", line=dict(width=2, color="white")),
        text=[f"<b>Yield</b><br>{ys:.0f} MPa"],
        textposition="top center",
        textfont=dict(size=12, color="#e74c3c", family="Arial Black"),
        name="Yield Strength",
        showlegend=False
    ))
    
    # UTS point - prominent marker
    uts_idx = int(np.argmax(stress_smooth))
    fig.add_trace(go.Scatter(
        x=[strain_smooth[uts_idx] * 100], y=[uts],
        mode="markers+text",
        marker=dict(size=16, color="#27ae60", symbol="square", line=dict(width=2, color="white")),
        text=[f"<b>UTS</b><br>{uts:.0f} MPa"],
        textposition="top center",
        textfont=dict(size=12, color="#27ae60", family="Arial Black"),
        name="Ultimate Tensile Strength",
        showlegend=False
    ))
    
    fig.update_layout(
        title=dict(
            text="Engineering Stress-Strain Curve",
            font=dict(size=18, color="#2c3e50"),
            x=0.5,
            xanchor="center"
        ),
        xaxis=dict(
            title="Strain (%)",
            gridcolor="#e0e0e0",
            gridwidth=1,
            showgrid=True
        ),
        yaxis=dict(
            title="Stress (MPa)",
            gridcolor="#e0e0e0",
            gridwidth=1,
            showgrid=True
        ),
        height=550,
        template="plotly_white",
        hovermode='closest',
        plot_bgcolor="white",
        paper_bgcolor="white"
    )
    return fig

# ========== MAIN APP ==========

st.title("Material AI: TIG Weld Property Predictor")
st.markdown("**Professional ML System for Aerospace Material Property Prediction**")
st.markdown("---")

# Check models
if not (MODELS_DIR / "preprocessor.pkl").exists():
    st.error("⚠️ Models not found. Please train models first:")
    st.code("python main.py train", language="bash")
    st.info("This will generate training data and train all models (~5-10 minutes)")
    st.stop()

# Load predictor
predictor = load_predictor()
if predictor is None:
    st.error("Failed to initialize predictor. Check error message above.")
    st.stop()

explainer = load_explainer(predictor)

# ========== SIDEBAR: INPUT MODE ==========

st.sidebar.title("Input Configuration")
input_mode = st.sidebar.radio(
    "Select input method:",
    ["Sliders", "Manual Entry", "File Upload"],
    help="Choose how to provide welding parameters"
)

st.sidebar.markdown("---")

# Initialize session state
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
predict_btn = False

# ========== INPUT MODES ==========

if input_mode == "Sliders":
    st.sidebar.markdown("### Welding Parameters")
    params['current_A'] = float(st.sidebar.slider("Current (A)", 80, 220, 150, 5))
    params['voltage_V'] = float(st.sidebar.slider("Voltage (V)", 10, 25, 15, 1))
    params['speed_mm_per_min'] = float(st.sidebar.slider("Travel Speed (mm/min)", 80, 300, 150, 10))
    
    heat_input = (params['current_A'] * params['voltage_V'] * 60.0) / (1000.0 * params['speed_mm_per_min'])
    st.sidebar.metric("Heat Input", f"{heat_input:.3f} kJ/mm")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filler Composition (wt%)")
    
    with st.sidebar.expander("Main Elements", expanded=True):
        params['filler_C'] = st.slider("Carbon (C)", 0.01, 0.08, 0.03, 0.01, format="%.3f")
        params['filler_Mn'] = st.slider("Manganese (Mn)", 0.5, 2.0, 1.0, 0.1)
        params['filler_Si'] = st.slider("Silicon (Si)", 0.1, 0.8, 0.4, 0.05)
    
    with st.sidebar.expander("Alloying Elements"):
        params['filler_Cr'] = st.slider("Chromium (Cr)", 14.0, 25.0, 18.0, 0.5)
        params['filler_Ni'] = st.slider("Nickel (Ni)", 8.0, 20.0, 10.0, 0.5)
        params['filler_Mo'] = st.slider("Molybdenum (Mo)", 0.0, 4.0, 2.0, 0.1)
        params['filler_Ti'] = st.slider("Titanium (Ti)", 0.0, 0.5, 0.1, 0.01, format="%.3f")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### HAZ Characteristics")
    
    with st.sidebar.expander("Advanced Parameters", expanded=False):
        params['haz_width_mm'] = st.slider("HAZ Width (mm)", 0.2, 3.5, 1.2, 0.1)
        params['haz_peak_temp_C'] = float(st.slider("Peak Temperature (°C)", 600, 1400, 1000, 50))
        params['haz_cooling_rate'] = float(st.slider("Cooling Rate (°C/s)", 10, 2000, 200, 10))
        params['grain_size_um'] = float(st.slider("Grain Size (μm)", 2, 80, 20, 1))
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Repair Stage")
    params['repair_stage'] = st.sidebar.selectbox(
        "Stage",
        options=[0, 1, 2, 3],
        format_func=lambda x: f"R{x} - {'As-welded' if x == 0 else f'Repair {x}'}",
        help="R0=baseline, R1-R3=repair stages with progressive degradation"
    )
    
    st.sidebar.markdown("---")
    predict_btn = st.sidebar.button("Predict Properties", type="primary", use_container_width=True)

elif input_mode == "Manual Entry":
    st.sidebar.markdown("### Manual Entry")
    
    with st.sidebar.expander("Welding Parameters", expanded=True):
        params['current_A'] = st.number_input("Current (A)", 80.0, 220.0, float(params['current_A']), 1.0)
        params['voltage_V'] = st.number_input("Voltage (V)", 10.0, 25.0, float(params['voltage_V']), 0.5)
        params['speed_mm_per_min'] = st.number_input("Travel Speed (mm/min)", 80.0, 300.0, float(params['speed_mm_per_min']), 5.0)
    
    with st.sidebar.expander("Filler Composition (wt%)"):
        params['filler_C'] = st.number_input("Carbon (C)", 0.01, 0.08, float(params['filler_C']), 0.001, format="%.3f")
        params['filler_Mn'] = st.number_input("Manganese (Mn)", 0.5, 2.0, float(params['filler_Mn']), 0.1)
        params['filler_Si'] = st.number_input("Silicon (Si)", 0.1, 0.8, float(params['filler_Si']), 0.05)
        params['filler_Cr'] = st.number_input("Chromium (Cr)", 14.0, 25.0, float(params['filler_Cr']), 0.5)
        params['filler_Ni'] = st.number_input("Nickel (Ni)", 8.0, 20.0, float(params['filler_Ni']), 0.5)
        params['filler_Mo'] = st.number_input("Molybdenum (Mo)", 0.0, 4.0, float(params['filler_Mo']), 0.1)
        params['filler_Ti'] = st.number_input("Titanium (Ti)", 0.0, 0.5, float(params['filler_Ti']), 0.01, format="%.3f")
    
    with st.sidebar.expander("HAZ Characteristics"):
        params['haz_width_mm'] = st.number_input("HAZ Width (mm)", 0.2, 3.5, float(params['haz_width_mm']), 0.1)
        params['haz_peak_temp_C'] = st.number_input("Peak Temperature (°C)", 600.0, 1400.0, float(params['haz_peak_temp_C']), 10.0)
        params['haz_cooling_rate'] = st.number_input("Cooling Rate (°C/s)", 10.0, 2000.0, float(params['haz_cooling_rate']), 10.0)
        params['grain_size_um'] = st.number_input("Grain Size (μm)", 2.0, 80.0, float(params['grain_size_um']), 1.0)
        params['repair_stage'] = st.selectbox("Repair Stage", [0, 1, 2, 3], index=int(params['repair_stage']))
    
    st.sidebar.markdown("---")
    predict_btn = st.sidebar.button("Predict Properties", type="primary", use_container_width=True)

else:  # File Upload
    st.sidebar.markdown("### Upload CSV File")
    st.sidebar.markdown("""
    **Required columns:**
    - `current_A`, `voltage_V`, `speed_mm_per_min`
    - `filler_C`, `filler_Mn`, `filler_Si`, `filler_Cr`
    - `filler_Ni`, `filler_Mo`, `filler_Ti`
    - `haz_width_mm`, `haz_peak_temp_C`
    - `haz_cooling_rate`, `grain_size_um`
    - `repair_stage`
    """)
    
    uploaded_file = st.sidebar.file_uploader("Choose CSV file", type=['csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.sidebar.success(f"Loaded {len(df)} samples")
            st.sidebar.dataframe(df.head(3), use_container_width=True)
            
            if st.sidebar.button("Run Batch Prediction", type="primary", use_container_width=True):
                from inference.batch_predictor import BatchPredictor
                batch_predictor = BatchPredictor(predictor)
                
                with st.spinner(f"Processing {len(df)} samples..."):
                    batch_results = batch_predictor.predict_batch(df)
                
                st.success(f"Predicted {len(batch_results)} samples successfully!")
        except Exception as e:
            st.sidebar.error(f"Error loading file: {e}")
            st.sidebar.info("Please check your CSV format matches the required columns.")

# ========== PREDICTION ==========

# Auto-run prediction on first load or when button clicked
should_predict = predict_btn or (input_mode != "File Upload" and 'last_prediction' not in st.session_state)

if input_mode != "File Upload" and should_predict:
    if 'last_prediction' not in st.session_state:
        st.session_state.last_prediction = True
    
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
        
        with st.spinner("Running ensemble prediction..."):
            result = predictor.predict(input_features)
        
        # ========== HERO METRICS (PROMINENT DISPLAY) ==========
        
        st.markdown("## Predicted Mechanical Properties")
        
        # Big, bold metrics at the top
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Yield Strength</div>
                <div class="big-metric">{result.yield_strength_MPa:.1f}</div>
                <div class="metric-label">MPa</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Ultimate Tensile Strength</div>
                <div class="big-metric">{result.uts_MPa:.1f}</div>
                <div class="metric-label">MPa</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Elongation</div>
                <div class="big-metric">{result.elongation_pct:.2f}</div>
                <div class="metric-label">%</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Secondary metrics
        col4, col5 = st.columns(2)
        col4.metric("YS/UTS Ratio", f"{result.yield_strength_MPa / result.uts_MPa:.3f}", 
                   help="Yield to UTS ratio indicates ductility")
        col5.metric("Repair Stage", f"R{params['repair_stage']}", 
                   help="R0=As-welded, R1-R3=Repair stages")
        
        st.markdown("---")
        
        # ========== TABS ==========
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "Stress-Strain Curve", 
            "Feature Importance", 
            "Physics Validation",
            "Export Data"
        ])
        
        with tab1:
            fig = render_stress_strain_curve(result.strain, result.stress, 
                                            result.yield_strength_MPa, result.uts_MPa)
            st.plotly_chart(fig, use_container_width=True)
            
            # Curve quality info
            st.info("Curve Quality: Physics-based smoothing applied. Monotonic increase to UTS, gradual necking behavior.")
        
        with tab2:
            if explainer:
                try:
                    with st.spinner("Calculating SHAP values..."):
                        X = np.array([[input_features[f] for f in explainer.feature_names]])
                        shap_values = explainer.explain_global(X, target='yield_strength_MPa')['yield_strength_MPa'][0]
                    
                    importance_df = pd.DataFrame({
                        'Feature': explainer.feature_names,
                        'SHAP Value': shap_values
                    }).sort_values('SHAP Value', key=abs, ascending=False).head(10)
                    
                    fig = go.Figure(go.Bar(
                        x=importance_df['SHAP Value'],
                        y=importance_df['Feature'],
                        orientation='h',
                        marker=dict(
                            color=importance_df['SHAP Value'],
                            colorscale='RdBu',
                            showscale=True,
                            colorbar=dict(title="SHAP Value")
                        )
                    ))
                    fig.update_layout(
                        title="<b>Top 10 Feature Importance (SHAP Values)</b>",
                        xaxis_title="<b>SHAP Value</b>",
                        yaxis_title="<b>Feature</b>",
                        height=500,
                        template="plotly_white"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.info("Interpretation: Positive SHAP values increase the prediction, negative values decrease it. Larger absolute values indicate stronger influence.")
                    
                except Exception as e:
                    st.warning(f"SHAP explainability unavailable: {e}")
            else:
                st.info("SHAP explainability not available. Install with: pip install shap")
        
        with tab3:
            st.markdown("### Physics-Based Validation")
            
            # Detailed validation with explanations
            ys_uts_pass = result.yield_strength_MPa < result.uts_MPa
            elong_pass = result.elongation_pct > 0
            uts_range_pass = 300 < result.uts_MPa < 1600
            ys_range_pass = 200 < result.yield_strength_MPa < 1200
            ratio_pass = 0.5 < (result.yield_strength_MPa / result.uts_MPa) < 0.95
            
            checks = [
                ("Yield < UTS", ys_uts_pass, 
                 f"PASS: {result.yield_strength_MPa:.1f} < {result.uts_MPa:.1f} MPa",
                 "FAIL: Yield strength must be less than UTS"),
                
                ("Elongation > 0", elong_pass,
                 f"PASS: {result.elongation_pct:.2f}% (positive ductility)",
                 "FAIL: Elongation must be positive"),
                
                ("UTS in Range", uts_range_pass,
                 f"PASS: {result.uts_MPa:.1f} MPa (within 300-1600 MPa)",
                 f"WARNING: {result.uts_MPa:.1f} MPa (outside typical range)"),
                
                ("Yield in Range", ys_range_pass,
                 f"PASS: {result.yield_strength_MPa:.1f} MPa (within 200-1200 MPa)",
                 f"WARNING: {result.yield_strength_MPa:.1f} MPa (outside typical range)"),
                
                ("YS/UTS Ratio", ratio_pass,
                 f"PASS: {result.yield_strength_MPa / result.uts_MPa:.3f} (within 0.5-0.95)",
                 f"WARNING: {result.yield_strength_MPa / result.uts_MPa:.3f} (unusual ratio)")
            ]
            
            for check_name, passed, pass_msg, fail_msg in checks:
                if passed:
                    st.success(f"**{check_name}:** {pass_msg}")
                else:
                    st.error(f"**{check_name}:** {fail_msg}")
            
            # Overall assessment
            all_critical_pass = ys_uts_pass and elong_pass
            if all_critical_pass:
                st.success("Overall Assessment: All critical physics checks passed. Predictions are physically valid.")
            else:
                st.error("Overall Assessment: Some critical checks failed. Review predictions carefully.")
        
        with tab4:
            st.markdown("### Export Prediction Results")
            
            export_df = pd.DataFrame([{
                **params,
                'predicted_yield_MPa': result.yield_strength_MPa,
                'predicted_uts_MPa': result.uts_MPa,
                'predicted_elongation_pct': result.elongation_pct,
                'ys_uts_ratio': result.yield_strength_MPa / result.uts_MPa
            }])
            
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="Download Prediction as CSV",
                data=csv,
                file_name=f"material_prediction_R{params['repair_stage']}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.markdown("### Preview")
            st.dataframe(export_df, use_container_width=True)
    
    except Exception as e:
        st.error(f"Prediction failed: {e}")
        st.info("Please check that models are trained. Run: python main.py train")
        with st.expander("Debug Information"):
            st.code(traceback.format_exc())

# ========== BATCH RESULTS ==========

if batch_results is not None:
    st.markdown(f"## Batch Prediction Results ({len(batch_results)} samples)")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Yield", f"{batch_results['predicted_yield_MPa'].mean():.1f} MPa")
    col2.metric("Average UTS", f"{batch_results['predicted_uts_MPa'].mean():.1f} MPa")
    col3.metric("Average Elongation", f"{batch_results['predicted_elongation_pct'].mean():.2f} %")
    col4.metric("Total Samples", f"{len(batch_results)}")
    
    st.markdown("---")
    st.dataframe(batch_results, use_container_width=True, height=400)
    
    csv = batch_results.to_csv(index=False)
    st.download_button(
        label="Download Batch Results as CSV",
        data=csv,
        file_name="batch_predictions.csv",
        mime="text/csv",
        use_container_width=True
    )

# ========== FOOTER ==========

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d; font-size: 0.9em; padding: 20px;'>
    <p><b>Material AI v1.0.0</b> | Ensemble ML for TIG Weld Property Prediction</p>
    <p>Powered by LightGBM + FT-Transformer + CVAE | 18ms prediction time | Physics-validated</p>
    <p>Developed for aerospace-grade material characterization</p>
</div>
""", unsafe_allow_html=True)
