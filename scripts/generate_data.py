#!/usr/bin/env python3
"""Standalone script to generate and save the synthetic dataset."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.generator import DataConfig, generate_dataset, save_dataset
from utils.seed import set_seed

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic TIG weld dataset")
    parser.add_argument("--n-samples", type=int, default=2000)
    parser.add_argument("--output-dir", type=str, default="data")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    cfg = DataConfig(n_samples=args.n_samples, random_state=args.seed)
    df = generate_dataset(cfg)
    paths = save_dataset(df, args.output_dir)
    print(f"Dataset saved: {len(df)} rows")
    for split, path in paths.items():
        print(f"  {split}: {path}")
