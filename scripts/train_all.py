#!/usr/bin/env python3
"""Standalone script to run the full training pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    from training.pipeline import run_pipeline

    metrics = run_pipeline(
        cfg={},
        data_dir="data",
        models_dir="models/saved",
        results_dir="results",
        seed=42,
        force_regenerate=True,
    )
    print("\nFinal Metrics:")
    for model, m in metrics.items():
        print(f"  {model}:")
        for k, v in m.items():
            print(f"    {k}: {v:.4f}")
