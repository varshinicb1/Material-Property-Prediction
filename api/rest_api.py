"""REST API for Material AI predictions.

Provides FastAPI endpoints for model inference and monitoring.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from inference.predictor import MaterialPredictor
from inference.batch_predictor import BatchPredictor
from utils.monitoring import get_metrics_tracker
from utils.logging import get_logger

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Material AI API",
    description="AI-powered material property prediction for TIG welded aerospace structures",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global predictor instance
predictor: Optional[MaterialPredictor] = None


class PredictionRequest(BaseModel):
    """Request model for single prediction."""
    
    current_A: float = Field(..., ge=80, le=220, description="Welding current (A)")
    voltage_V: float = Field(..., ge=10, le=25, description="Arc voltage (V)")
    speed_mm_per_min: float = Field(..., ge=80, le=300, description="Travel speed (mm/min)")
    filler_C: float = Field(0.03, ge=0.01, le=0.08, description="Carbon content (wt%)")
    filler_Mn: float = Field(1.0, ge=0.5, le=2.0, description="Manganese content (wt%)")
    filler_Si: float = Field(0.4, ge=0.1, le=0.8, description="Silicon content (wt%)")
    filler_Cr: float = Field(18.0, ge=14.0, le=25.0, description="Chromium content (wt%)")
    filler_Ni: float = Field(10.0, ge=8.0, le=20.0, description="Nickel content (wt%)")
    filler_Mo: float = Field(2.0, ge=0.0, le=4.0, description="Molybdenum content (wt%)")
    filler_Ti: float = Field(0.1, ge=0.0, le=0.5, description="Titanium content (wt%)")
    haz_width_mm: float = Field(1.2, ge=0.2, le=3.5, description="HAZ width (mm)")
    haz_peak_temp_C: float = Field(1000.0, ge=600, le=1400, description="Peak HAZ temperature (°C)")
    haz_cooling_rate: float = Field(200.0, ge=10, le=2000, description="HAZ cooling rate (°C/s)")
    grain_size_um: float = Field(20.0, ge=2, le=80, description="Grain size (μm)")
    repair_stage: int = Field(0, ge=0, le=3, description="Repair stage (0-3)")


class PredictionResponse(BaseModel):
    """Response model for single prediction."""
    
    yield_strength_MPa: float
    uts_MPa: float
    elongation_pct: float
    stress_strain_curve: dict[str, list[float]]
    physics_checks: dict[str, bool]
    latency_ms: float


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str
    models_loaded: bool
    version: str


class MetricsResponse(BaseModel):
    """Response model for metrics."""
    
    statistics: dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Initialize models on startup."""
    global predictor
    try:
        predictor = MaterialPredictor(models_dir="models/saved")
        logger.info("API started successfully")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        predictor = None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if predictor is not None else "unhealthy",
        models_loaded=predictor is not None,
        version="1.0.0",
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, background_tasks: BackgroundTasks):
    """Predict material properties for given welding parameters."""
    if predictor is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        # Build input dictionary
        input_dict = predictor.build_input(
            current_A=request.current_A,
            voltage_V=request.voltage_V,
            speed_mm_per_min=request.speed_mm_per_min,
            filler_C=request.filler_C,
            filler_Mn=request.filler_Mn,
            filler_Si=request.filler_Si,
            filler_Cr=request.filler_Cr,
            filler_Ni=request.filler_Ni,
            filler_Mo=request.filler_Mo,
            filler_Ti=request.filler_Ti,
            haz_width_mm=request.haz_width_mm,
            haz_peak_temp_C=request.haz_peak_temp_C,
            haz_cooling_rate=request.haz_cooling_rate,
            grain_size_um=request.grain_size_um,
            repair_stage=request.repair_stage,
        )
        
        # Make prediction
        import time
        start_time = time.time()
        result = predictor.predict(input_dict)
        latency_ms = (time.time() - start_time) * 1000
        
        # Physics checks
        physics_checks = {
            "yield_less_than_uts": result.yield_strength_MPa < result.uts_MPa,
            "positive_yield": result.yield_strength_MPa > 0,
            "positive_uts": result.uts_MPa > 0,
            "positive_elongation": result.elongation_pct > 0,
            "curve_starts_at_zero": float(result.stress[0]) < 10.0,
        }
        
        return PredictionResponse(
            yield_strength_MPa=result.yield_strength_MPa,
            uts_MPa=result.uts_MPa,
            elongation_pct=result.elongation_pct,
            stress_strain_curve={
                "strain": result.strain.tolist(),
                "stress": result.stress.tolist(),
            },
            physics_checks=physics_checks,
            latency_ms=latency_ms,
        )
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get current metrics and statistics."""
    tracker = get_metrics_tracker()
    return MetricsResponse(statistics=tracker.get_statistics())


@app.post("/metrics/save")
async def save_metrics():
    """Save current metrics to file."""
    tracker = get_metrics_tracker()
    filepath = tracker.save_metrics()
    return {"message": f"Metrics saved to {filepath}"}


@app.post("/metrics/clear")
async def clear_metrics():
    """Clear all metrics."""
    tracker = get_metrics_tracker()
    tracker.clear()
    return {"message": "Metrics cleared"}


def start_api(host: str = "0.0.0.0", port: int = 8000):
    """Start the API server.
    
    Args:
        host: Host to bind to.
        port: Port to bind to.
    """
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_api()
