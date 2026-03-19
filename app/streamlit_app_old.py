"""Professional Streamlit Application for TIG Welded Aerospace Material Property Prediction.

Scientific-grade interface for material property prediction using ensemble machine learning.
Designed for aerospace engineers and materials scientists.

Features:
- Manual parameter entry via sliders or text input
- Batch prediction via CSV file upload
- SHAP explainability
- Stress-strain curve visualization
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Material AI | TIG Weld Property Predictor",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Professional Styling ──────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Professional color scheme */
    :root {
        --primary-color: #1f77b4;
        --secondary-color: #2c3e50;
        --background-color: #f8f9fa;
        --text-color: #2c3e50;
    }
    
    /* Main container */
    .main {
        background-color: #ffffff;
        font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    h1 {
        border-bottom: 3px solid #1f77b4;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    
    /* Metrics */
    .stMetric {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-left: 4px solid #1f77b4;
        border-radius: 4px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stMetric label {
        color: #6c757d !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stMetric [data-testid="metric-container"] > div:first-child {
        color: #2c3e50;
        font-size: 24px;
        font-weight: 700;
    }
    
    /* Sidebar */
    div[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #dee2e6;
    }
    
    div[data-testid="stSidebar"] h1, 
    div[data-testid="stSidebar"] h2, 
    div[data-testid="stSidebar"] h3 {
        color: #2c3e50;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #1f77b4;
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 4px;
        padding: 10px 24px;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #1557a0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Tables */
    .dataframe {
        font-size: 13px;
        border: 1px solid #dee2e6;
    }
    
    .dataframe th {
        background-color: #f8f9fa;
        color: #2c3e50;
        font-weight: 600;
        text-align: left;
        padding: 12px;
    }
    
    .dataframe td {
        padding: 10px 12px;
        border-bottom: 1px solid #e9ecef;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 4px;
        color: #6c757d;
        font-weight: 600;
        padding: 8px 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 4px;
        font-weight: 600;
        color: #2c3e50;
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 4px;
        border-left: 4px solid #1f77b4;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

MODELS_DIR = ROOT / "models" / "saved"


@st.cache_resource(show_spinner="Loading AI models...")
def load_predictor():
    """Load and cache MaterialPredictor."""
    try:
        from inference.predictor import MaterialPredictor
        return MaterialPredictor(models_dir=str(MODELS_DIR))
    except Exception as e:
        st.error(f"Model loading failed: {e}")
        return None


@st.cache_resource(show_spinner="Initializing SHAP explainer...")
def load_explainer(_predictor):
    """Load and cache SHAP explainer."""
    try:
        import shap
        from explainability.shap_explainer import GBMShapExplainer
        from data.generator import get_feature_columns
        cols = get_feature_columns(50)
        return GBMShapExplainer(_predictor.gbm, cols["features"])
    except ImportError:
        return None
    except Exception:
        return None


def models_ready() -> bool:
    """Check if all required models are available."""
    return (MODELS_DIR / "preprocessor.pkl").exists() and \
           (MODELS_DIR / "gbm.pkl").exists() and \
           (MODELS_DIR / "ft_transformer.pt").exists() and \
           (MODELS_DIR / "cvae.pt").exists()


def render_stress_strain_curve(strain: np.ndarray, stress: np.ndarray, 
                               ys: float, uts: float) -> go.Figure:
    """Render professional stress-strain curve with engineering annotations."""
    fig = go.Figure()

    # Main curve with professional styling
    fig.add_trace(go.Scatter(
        x=strain * 100,
        y=stress,
        mode="lines",
        name="Predicted Curve",
        line=dict(color="#1f77b4", width=2.5),
        hovertemplate="<b>Strain:</b> %{x:.3f}%<br><b>Stress:</b> %{y:.1f} MPa<extra></extra>",
    ))

    # Yield strength marker
    ys_strain_idx = int(np.argmin(np.abs(stress - ys)))
    fig.add_trace(go.Scatter(
        x=[strain[ys_strain_idx] * 100],
        y=[ys],
        mode="markers+text",
        marker=dict(size=10, color="#d62728", symbol="diamond", line=dict(width=2, color="white")),
        text=[f"σy = {ys:.0f} MPa"],
        textposition="top center",
        textfont=dict(size=11, color="#d62728", family="Arial"),
        name="Yield Strength",
        showlegend=True,
        hovertemplate=f"<b>Yield Strength:</b> {ys:.1f} MPa<extra></extra>",
    ))

    # UTS marker
    uts_idx = int(np.argmax(stress))
    fig.add_trace(go.Scatter(
        x=[strain[uts_idx] * 100],
        y=[uts],
        mode="markers+text",
        marker=dict(size=10, color="#2ca02c", symbol="square", line=dict(width=2, color="white")),
        text=[f"UTS = {uts:.0f} MPa"],
        textposition="top center",
        textfont=dict(size=11, color="#2ca02c", family="Arial"),
        name="Ultimate Tensile Strength",
        showlegend=True,
        hovertemplate=f"<b>UTS:</b> {uts:.1f} MPa<extra></extra>",
    ))

    # Professional layout
    fig.update_layout(
        title=dict(
            text="<b>Stress-Strain Curve</b>",
            font=dict(size=16, color="#2c3e50", family="Arial"),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title=dict(text="<b>Strain (%)</b>", font=dict(size=13, color="#2c3e50")),
            color="#2c3e50",
            gridcolor="#e9ecef",
            gridwidth=1,
            showline=True,
            linewidth=2,
            linecolor="#2c3e50",
            mirror=True,
        ),
        yaxis=dict(
            title=dict(text="<b>Stress (MPa)</b>", font=dict(size=13, color="#2c3e50")),
            color="#2c3e50",
            gridcolor="#e9ecef",
            gridwidth=1,
            showline=True,
            linewidth=2,
            linecolor="#2c3e50",
            mirror=True,
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(
            bgcolor="rgba(248, 249, 250, 0.9)",
            font=dict(color="#2c3e50", size=11),
            bordercolor="#dee2e6",
            borderwidth=1,
            x=0.02,
            y=0.98,
            xanchor="left",
            yanchor="top",
        ),
        hovermode="closest",
        margin=dict(l=80, r=40, t=60, b=60),
        font=dict(family="Arial, sans-serif"),
    )
    return fig


def render_shap_chart(shap_dict: dict[str, float]) -> go.Figure:
    """Render professional SHAP feature importance chart."""
    sorted_items = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:12]
    features = [i[0] for i in sorted_items]
    values = [i[1] for i in sorted_items]

    colors = ["#d62728" if v > 0 else "#1f77b4" for v in values]
    
    fig = go.Figure(go.Bar(
        y=features[::-1],
        x=values[::-1],
        orientation="h",
        marker=dict(
            color=colors[::-1],
            line=dict(color="#2c3e50", width=0.5)
        ),
        hovertemplate="<b>%{y}</b><br>SHAP Value: %{x:.4f}<extra></extra>",
    ))
    
    fig.update_layout(
        title=dict(
            text="<b>Feature Importance (SHAP Values)</b>",
            font=dict(size=15, color="#2c3e50"),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title=dict(text="<b>SHAP Value</b>", font=dict(size=12, color="#2c3e50")),
            color="#2c3e50",
            gridcolor="#e9ecef",
            showline=True,
            linewidth=1,
            linecolor="#2c3e50",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="#2c3e50",
        ),
        yaxis=dict(
            color="#2c3e50",
            showgrid=False,
            showline=True,
            linewidth=1,
            linecolor="#2c3e50",
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=180, r=40, t=60, b=60),
        font=dict(family="Arial, sans-serif", size=11),
        height=450,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR: INPUT PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════

st.sidebar.title("Input Parameters")
st.sidebar.markdown("---")

st.sidebar.subheader("Arc Welding Parameters")
current_A = st.sidebar.slider("Current (A)", 80, 220, 150, step=5, 
                               help="Welding current in Amperes")
voltage_V = st.sidebar.slider("Voltage (V)", 10, 25, 15, step=1,
                              help="Arc voltage in Volts")
speed_mm = st.sidebar.slider("Travel Speed (mm/min)", 80, 300, 150, step=10,
                             help="Welding travel speed")

heat_input = (current_A * voltage_V * 60.0) / (1000.0 * speed_mm)
st.sidebar.metric("Heat Input", f"{heat_input:.3f} kJ/mm")

st.sidebar.markdown("---")
st.sidebar.subheader("Repair Stage")
repair_stage = st.sidebar.selectbox(
    "Stage",
    options=[0, 1, 2, 3],
    format_func=lambda x: f"R{x} - {'As-welded' if x == 0 else f'Repair {x}'}",
    help="Repair stage: R0 (baseline) to R3 (third repair)"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Filler Composition (wt%)")
col1, col2 = st.sidebar.columns(2)
with col1:
    filler_C = st.number_input("C", 0.01, 0.08, 0.03, step=0.01, format="%.3f")
    filler_Mn = st.number_input("Mn", 0.5, 2.0, 1.0, step=0.1)
    filler_Si = st.number_input("Si", 0.1, 0.8, 0.4, step=0.05)
    filler_Cr = st.number_input("Cr", 14.0, 25.0, 18.0, step=0.5)
with col2:
    filler_Ni = st.number_input("Ni", 8.0, 20.0, 10.0, step=0.5)
    filler_Mo = st.number_input("Mo", 0.0, 4.0, 2.0, step=0.1)
    filler_Ti = st.number_input("Ti", 0.0, 0.5, 0.1, step=0.01, format="%.3f")

st.sidebar.markdown("---")
st.sidebar.subheader("HAZ Characteristics")
haz_width = st.sidebar.slider("HAZ Width (mm)", 0.2, 3.5, 1.2, step=0.1)
haz_temp = st.sidebar.slider("Peak Temperature (°C)", 600, 1400, 1000, step=50)
haz_cooling = st.sidebar.slider("Cooling Rate (°C/s)", 10, 2000, 200, step=10)
grain_size = st.sidebar.slider("Grain Size (μm)", 2, 80, 20, step=1)

st.sidebar.markdown("---")
predict_btn = st.sidebar.button("Run Prediction", type="primary")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════

st.title("Material AI: TIG Weld Property Predictor")
st.markdown(
    """
    **Advanced machine learning system for predicting mechanical properties of TIG welded aerospace structures.**  
    Ensemble model combining LightGBM, FT-Transformer, and Conditional VAE with physics-aware constraints.
    """
)
st.markdown("---")

# Check model availability
if not models_ready():
    st.warning(
        "**Models not found.** Please train models first using: `python main.py train`"
    )
    st.code("python main.py train", language="bash")
    st.stop()

# Load models
predictor = load_predictor()
if predictor is None:
    st.error("Failed to load predictor. Verify model files exist in models/saved/")
    st.stop()

explainer = load_explainer(predictor)

# Run prediction
if predict_btn or True:  # Auto-run on load
    input_features = predictor.build_input(
        current_A=float(current_A),
        voltage_V=float(voltage_V),
        speed_mm_per_min=float(speed_mm),
        filler_C=filler_C,
        filler_Mn=filler_Mn,
        filler_Si=filler_Si,
        filler_Cr=filler_Cr,
        filler_Ni=filler_Ni,
        filler_Mo=filler_Mo,
        filler_Ti=filler_Ti,
        haz_width_mm=haz_width,
        haz_peak_temp_C=float(haz_temp),
        haz_cooling_rate=float(haz_cooling),
        grain_size_um=float(grain_size),
        repair_stage=repair_stage,
    )

    with st.spinner("Running ensemble inference..."):
        result = predictor.predict(input_features)

    # ── Results Display ───────────────────────────────────────────────────────
    st.subheader("Predicted Mechanical Properties")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Yield Strength", f"{result.yield_strength_MPa:.1f} MPa")
    col2.metric("Ultimate Tensile Strength", f"{result.uts_MPa:.1f} MPa")
    col3.metric("Elongation", f"{result.elongation_pct:.2f} %")
    col4.metric("YS/UTS Ratio", f"{result.yield_strength_MPa / result.uts_MPa:.3f}")

    st.markdown("---")

    # ── Tabbed Interface ──────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "Stress-Strain Curve",
        "Feature Importance",
        "Model Comparison",
        "Data Export",
    ])

    with tab1:
        st.plotly_chart(
            render_stress_strain_curve(
                result.strain, result.stress,
                result.yield_strength_MPa, result.uts_MPa,
            ),
            width="stretch",
        )
        
        # Physics validation
        st.subheader("Physics Constraint Validation")
        checks_df = pd.DataFrame({
            "Constraint": [
                "Yield < UTS",
                "Yield Strength > 100 MPa",
                "UTS < 1600 MPa",
                "Elongation > 0%",
                "Curve Origin at Zero",
            ],
            "Status": [
                "PASS" if result.yield_strength_MPa < result.uts_MPa else "FAIL",
                "PASS" if result.yield_strength_MPa > 100 else "FAIL",
                "PASS" if result.uts_MPa < 1600 else "FAIL",
                "PASS" if result.elongation_pct > 0 else "FAIL",
                "PASS" if float(result.stress[0]) < 10.0 else "FAIL",
            ],
            "Value": [
                f"{result.yield_strength_MPa:.1f} < {result.uts_MPa:.1f}",
                f"{result.yield_strength_MPa:.1f} MPa",
                f"{result.uts_MPa:.1f} MPa",
                f"{result.elongation_pct:.2f}%",
                f"{result.stress[0]:.2f} MPa",
            ]
        })
        st.dataframe(checks_df, width="stretch", hide_index=True)

    with tab2:
        if explainer is not None:
            try:
                from data.generator import get_feature_columns
                cols = get_feature_columns(50)
                x_raw = np.array([[input_features[fn] for fn in cols["features"]]], dtype=np.float32)
                x_scaled = predictor.preprocessor.transform_input(x_raw)
                shap_dict = explainer.get_local_shap_dict(x_scaled[0], "yield_strength_MPa")
                
                st.plotly_chart(render_shap_chart(shap_dict), width="stretch")
                
                st.subheader("Top Contributing Features")
                sorted_shap = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:8]
                shap_df = pd.DataFrame(sorted_shap, columns=["Feature", "SHAP Value"])
                shap_df["Impact"] = shap_df["SHAP Value"].apply(
                    lambda x: "Increases" if x > 0 else "Decreases"
                )
                shap_df["SHAP Value"] = shap_df["SHAP Value"].apply(lambda x: f"{x:+.4f}")
                st.dataframe(shap_df, width="stretch", hide_index=True)
            except Exception as e:
                st.error(f"SHAP analysis failed: {e}")
        else:
            st.info("SHAP explainer not available. Install with: `pip install shap`")

    with tab3:
        st.subheader("Ensemble Model Predictions")
        model_comparison = pd.DataFrame({
            "Model": ["LightGBM", "FT-Transformer", "Ensemble (Final)"],
            "Yield Strength (MPa)": [
                f"{result.gbm_pred[0]:.1f}",
                f"{result.deep_pred[0]:.1f}",
                f"{result.yield_strength_MPa:.1f}",
            ],
            "UTS (MPa)": [
                f"{result.gbm_pred[1]:.1f}",
                f"{result.deep_pred[1]:.1f}",
                f"{result.uts_MPa:.1f}",
            ],
            "Elongation (%)": [
                f"{result.gbm_pred[2]:.2f}",
                f"{result.deep_pred[2]:.2f}",
                f"{result.elongation_pct:.2f}",
            ],
        })
        st.dataframe(model_comparison, width="stretch", hide_index=True)
        
        st.subheader("Input Feature Summary")
        feat_df = pd.DataFrame(
            [(k, f"{v:.4f}") for k, v in input_features.items()],
            columns=["Feature", "Value"],
        )
        st.dataframe(feat_df, width="stretch", height=400)

    with tab4:
        st.subheader("Export Prediction Data")
        
        # Stress-strain curve data
        curve_df = pd.DataFrame({
            "Strain (fraction)": result.strain,
            "Strain (%)": result.strain * 100,
            "Stress (MPa)": result.stress,
        })
        
        csv_curve = curve_df.to_csv(index=False)
        st.download_button(
            label="Download Stress-Strain Curve (CSV)",
            data=csv_curve,
            file_name=f"stress_strain_R{repair_stage}.csv",
            mime="text/csv",
        )
        
        # Summary data
        summary_df = pd.DataFrame({
            "Property": ["Yield Strength", "UTS", "Elongation", "YS/UTS Ratio"],
            "Value": [
                f"{result.yield_strength_MPa:.2f} MPa",
                f"{result.uts_MPa:.2f} MPa",
                f"{result.elongation_pct:.2f} %",
                f"{result.yield_strength_MPa / result.uts_MPa:.4f}",
            ]
        })
        
        csv_summary = summary_df.to_csv(index=False)
        st.download_button(
            label="Download Summary (CSV)",
            data=csv_summary,
            file_name=f"prediction_summary_R{repair_stage}.csv",
            mime="text/csv",
        )
        
        st.dataframe(curve_df.head(10), width="stretch")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #6c757d; font-size: 12px;'>
    <b>Material AI v1.0.0</b> | TIG Weld Property Prediction System<br>
    Ensemble ML: LightGBM + FT-Transformer + Conditional VAE | Physics-Constrained Predictions
    </div>
    """,
    unsafe_allow_html=True,
)
