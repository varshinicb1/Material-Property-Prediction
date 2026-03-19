"""Monitoring and metrics tracking for production deployments.

Tracks prediction metrics, latency, errors, and model performance.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import json
import threading

import numpy as np


@dataclass
class PredictionMetrics:
    """Metrics for a single prediction."""
    
    timestamp: str
    latency_ms: float
    input_features: dict[str, float]
    predictions: dict[str, float]
    model_versions: dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None


class MetricsTracker:
    """Thread-safe metrics tracking for production monitoring."""
    
    def __init__(self, metrics_dir: str = "logs/metrics"):
        """Initialize metrics tracker.
        
        Args:
            metrics_dir: Directory to store metrics files.
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.predictions: list[PredictionMetrics] = []
        self.errors: list[dict[str, Any]] = []
        self.latencies: list[float] = []
        
        self._lock = threading.Lock()
        
    def record_prediction(
        self,
        latency_ms: float,
        input_features: dict[str, float],
        predictions: dict[str, float],
        model_versions: Optional[dict[str, str]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record a prediction event.
        
        Args:
            latency_ms: Prediction latency in milliseconds.
            input_features: Input feature dictionary.
            predictions: Prediction results.
            model_versions: Model version information.
            error: Error message if prediction failed.
        """
        with self._lock:
            metric = PredictionMetrics(
                timestamp=datetime.now().isoformat(),
                latency_ms=latency_ms,
                input_features=input_features,
                predictions=predictions,
                model_versions=model_versions or {},
                error=error,
            )
            self.predictions.append(metric)
            
            if error is None:
                self.latencies.append(latency_ms)
            else:
                self.errors.append({
                    "timestamp": metric.timestamp,
                    "error": error,
                    "inputs": input_features,
                })
    
    def get_statistics(self) -> dict[str, Any]:
        """Get current statistics.
        
        Returns:
            Dictionary with statistics.
        """
        with self._lock:
            if not self.latencies:
                return {
                    "total_predictions": 0,
                    "total_errors": len(self.errors),
                    "error_rate": 0.0,
                }
            
            return {
                "total_predictions": len(self.predictions),
                "successful_predictions": len(self.latencies),
                "total_errors": len(self.errors),
                "error_rate": len(self.errors) / len(self.predictions),
                "latency_stats": {
                    "mean_ms": float(np.mean(self.latencies)),
                    "median_ms": float(np.median(self.latencies)),
                    "p95_ms": float(np.percentile(self.latencies, 95)),
                    "p99_ms": float(np.percentile(self.latencies, 99)),
                    "min_ms": float(np.min(self.latencies)),
                    "max_ms": float(np.max(self.latencies)),
                },
            }
    
    def save_metrics(self, filename: Optional[str] = None) -> Path:
        """Save metrics to file.
        
        Args:
            filename: Optional filename. If None, uses timestamp.
            
        Returns:
            Path to saved metrics file.
        """
        if filename is None:
            filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.metrics_dir / filename
        
        with self._lock:
            data = {
                "statistics": self.get_statistics(),
                "predictions": [
                    {
                        "timestamp": p.timestamp,
                        "latency_ms": p.latency_ms,
                        "predictions": p.predictions,
                        "error": p.error,
                    }
                    for p in self.predictions
                ],
                "errors": self.errors,
            }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def clear(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self.predictions.clear()
            self.errors.clear()
            self.latencies.clear()


# Global metrics tracker instance
_global_tracker: Optional[MetricsTracker] = None


def get_metrics_tracker() -> MetricsTracker:
    """Get or create global metrics tracker.
    
    Returns:
        Global MetricsTracker instance.
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = MetricsTracker()
    return _global_tracker
