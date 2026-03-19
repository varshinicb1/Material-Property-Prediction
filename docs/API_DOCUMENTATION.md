# Material AI - API Documentation

## Overview

Material AI provides a production-ready REST API for material property prediction. The API is built with FastAPI and includes automatic documentation, validation, and monitoring.

## Quick Start

### Start the API Server

```bash
python main.py api --host 0.0.0.0 --port 8000
```

### Access Interactive Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### 1. Health Check

**GET** `/health`

Check if the API is running and models are loaded.

**Response:**
```json
{
  "status": "healthy",
  "models_loaded": true,
  "version": "1.0.0"
}
```

### 2. Single Prediction

**POST** `/predict`

Predict material properties for given welding parameters.

**Request Body:**
```json
{
  "current_A": 150.0,
  "voltage_V": 15.0,
  "speed_mm_per_min": 150.0,
  "filler_C": 0.03,
  "filler_Mn": 1.0,
  "filler_Si": 0.4,
  "filler_Cr": 18.0,
  "filler_Ni": 10.0,
  "filler_Mo": 2.0,
  "filler_Ti": 0.1,
  "haz_width_mm": 1.2,
  "haz_peak_temp_C": 1000.0,
  "haz_cooling_rate": 200.0,
  "grain_size_um": 20.0,
  "repair_stage": 0
}
```

**Response:**
```json
{
  "yield_strength_MPa": 850.5,
  "uts_MPa": 920.3,
  "elongation_pct": 12.5,
  "stress_strain_curve": {
    "strain": [0.0, 0.001, 0.002, ...],
    "stress": [0.0, 110.0, 220.0, ...]
  },
  "physics_checks": {
    "yield_less_than_uts": true,
    "positive_yield": true,
    "positive_uts": true,
    "positive_elongation": true,
    "curve_starts_at_zero": true
  },
  "latency_ms": 125.3
}
```

### 3. Get Metrics

**GET** `/metrics`

Get current prediction metrics and statistics.

**Response:**
```json
{
  "statistics": {
    "total_predictions": 1000,
    "successful_predictions": 995,
    "total_errors": 5,
    "error_rate": 0.005,
    "latency_stats": {
      "mean_ms": 120.5,
      "median_ms": 115.0,
      "p95_ms": 180.0,
      "p99_ms": 250.0,
      "min_ms": 80.0,
      "max_ms": 300.0
    }
  }
}
```

### 4. Save Metrics

**POST** `/metrics/save`

Save current metrics to file.

**Response:**
```json
{
  "message": "Metrics saved to logs/metrics/metrics_20240120_143022.json"
}
```

### 5. Clear Metrics

**POST** `/metrics/clear`

Clear all accumulated metrics.

**Response:**
```json
{
  "message": "Metrics cleared"
}
```

## Python Client Example

```python
import requests

# API endpoint
url = "http://localhost:8000/predict"

# Prediction request
data = {
    "current_A": 150.0,
    "voltage_V": 15.0,
    "speed_mm_per_min": 150.0,
    "repair_stage": 0,
}

# Make request
response = requests.post(url, json=data)

if response.status_code == 200:
    result = response.json()
    print(f"Yield Strength: {result['yield_strength_MPa']:.1f} MPa")
    print(f"UTS: {result['uts_MPa']:.1f} MPa")
    print(f"Elongation: {result['elongation_pct']:.1f} %")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## cURL Examples

### Health Check
```bash
curl -X GET http://localhost:8000/health
```

### Prediction
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "current_A": 150.0,
    "voltage_V": 15.0,
    "speed_mm_per_min": 150.0,
    "repair_stage": 0
  }'
```

### Get Metrics
```bash
curl -X GET http://localhost:8000/metrics
```

## Input Validation

All inputs are validated with the following constraints:

| Parameter | Min | Max | Default | Unit |
|-----------|-----|-----|---------|------|
| current_A | 80 | 220 | - | A |
| voltage_V | 10 | 25 | - | V |
| speed_mm_per_min | 80 | 300 | - | mm/min |
| filler_C | 0.01 | 0.08 | 0.03 | wt% |
| filler_Mn | 0.5 | 2.0 | 1.0 | wt% |
| filler_Si | 0.1 | 0.8 | 0.4 | wt% |
| filler_Cr | 14.0 | 25.0 | 18.0 | wt% |
| filler_Ni | 8.0 | 20.0 | 10.0 | wt% |
| filler_Mo | 0.0 | 4.0 | 2.0 | wt% |
| filler_Ti | 0.0 | 0.5 | 0.1 | wt% |
| haz_width_mm | 0.2 | 3.5 | 1.2 | mm |
| haz_peak_temp_C | 600 | 1400 | 1000 | °C |
| haz_cooling_rate | 10 | 2000 | 200 | °C/s |
| grain_size_um | 2 | 80 | 20 | μm |
| repair_stage | 0 | 3 | 0 | - |

## Error Handling

### 400 Bad Request
Invalid input parameters (out of range, wrong type, etc.)

```json
{
  "detail": [
    {
      "loc": ["body", "current_A"],
      "msg": "ensure this value is greater than or equal to 80",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### 500 Internal Server Error
Prediction failed due to internal error

```json
{
  "detail": "Prediction failed: <error message>"
}
```

### 503 Service Unavailable
Models not loaded

```json
{
  "detail": "Models not loaded"
}
```

## Performance

- **Latency**: 80-300ms per prediction (typical: ~120ms)
- **Throughput**: ~8-10 predictions/second (single worker)
- **Memory**: ~500MB for loaded models

## Production Deployment

### Using Uvicorn (Single Worker)
```bash
uvicorn api.rest_api:app --host 0.0.0.0 --port 8000
```

### Using Gunicorn (Multiple Workers)
```bash
gunicorn api.rest_api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker Deployment
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.rest_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Monitoring

The API automatically tracks:
- Total predictions
- Success/error rates
- Latency statistics (mean, median, P95, P99)
- Error messages

Access metrics via `/metrics` endpoint or save to file with `/metrics/save`.

## Security Considerations

1. **Input Validation**: All inputs validated with Pydantic
2. **CORS**: Configured for cross-origin requests
3. **Rate Limiting**: Consider adding rate limiting for production
4. **Authentication**: Add API keys or OAuth for production
5. **HTTPS**: Use HTTPS in production (configure reverse proxy)

## Rate Limiting (Recommended)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/predict")
@limiter.limit("10/minute")
async def predict(...):
    ...
```

## Load Testing

```bash
# Install Apache Bench
apt-get install apache2-utils

# Test with 1000 requests, 10 concurrent
ab -n 1000 -c 10 -p request.json -T application/json \
  http://localhost:8000/predict
```

## Troubleshooting

### Models Not Loading
- Ensure models are trained: `python main.py train`
- Check models directory exists: `models/saved/`
- Verify all model files present

### High Latency
- Check CPU/GPU usage
- Consider using GPU for inference
- Increase number of workers
- Enable model caching

### Memory Issues
- Reduce number of workers
- Use smaller batch sizes
- Monitor memory usage

## Support

For issues or questions:
- Check logs in `logs/material_ai.log`
- Review error logs in `logs/material_ai_errors.log`
- Check metrics for patterns
