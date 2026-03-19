"""Synthetic dataset generator for TIG welded aerospace material properties.

Generates realistic synthetic data capturing the physics of TIG welding on
aerospace-grade alloys (Ti-6Al-4V, Inconel 718, Al 2024) including heat input
effects, HAZ softening/hardening, repair stage degradation, and stress-strain
curve shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import polars as pl
from scipy.interpolate import interp1d

from utils.logging import get_logger
from utils.seed import set_seed

logger = get_logger(__name__)


@dataclass
class DataConfig:
    """Configuration for synthetic data generation."""

    n_samples: int = 2000
    n_stress_strain_points: int = 50
    test_size: float = 0.2
    val_size: float = 0.1
    random_state: int = 42
    noise_level: float = 0.05
    output_dir: str = "data"


def _ramberg_osgood_curve(
    sigma_y: float,
    sigma_uts: float,
    elongation: float,
    n_points: int = 50,
    noise: float = 0.02,
    rng: Optional[np.random.Generator] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a stress-strain curve using modified Ramberg-Osgood model.

    Args:
        sigma_y: Yield strength in MPa.
        sigma_uts: Ultimate tensile strength in MPa.
        elongation: Total elongation as fraction.
        n_points: Number of discrete points.
        noise: Fractional noise level.
        rng: NumPy random generator.

    Returns:
        Tuple of (strain_array, stress_array) as 1D arrays.
        
    Raises:
        ValueError: If input parameters are invalid.
    """
    if rng is None:
        rng = np.random.default_rng(42)
    
    # Validate inputs
    if sigma_y <= 0 or sigma_uts <= 0:
        raise ValueError(f"Strengths must be positive: sigma_y={sigma_y}, sigma_uts={sigma_uts}")
    if sigma_uts <= sigma_y:
        raise ValueError(f"UTS must be > yield: sigma_y={sigma_y}, sigma_uts={sigma_uts}")
    if elongation <= 0 or elongation > 1.0:
        raise ValueError(f"Elongation must be in (0, 1]: {elongation}")
    if n_points < 10:
        raise ValueError(f"Need at least 10 points, got {n_points}")

    E = 110_000.0 + rng.normal(0, 2000)  # Young's modulus ~110 GPa Ti-alloys
    E = max(50_000.0, E)  # Ensure positive modulus
    
    # Safe calculation of strain hardening exponent
    eps_y_elastic = sigma_y / E
    eps_y_total = eps_y_elastic + 0.002
    
    if elongation <= eps_y_total:
        # Very low elongation, use linear approximation
        n = 10.0
    else:
        n = np.log(sigma_uts / sigma_y) / np.log(elongation / eps_y_total)
        n = np.clip(n, 3.0, 20.0)
    
    K = sigma_uts / (elongation**n)

    eps_max = elongation + rng.uniform(0.005, 0.02)
    strain = np.linspace(0.0, eps_max, n_points)

    stress = np.zeros(n_points)
    for i, eps in enumerate(strain):
        if eps <= eps_y_elastic:
            stress[i] = E * eps
        else:
            # Ramberg-Osgood plastic region with convergence check
            sigma = sigma_y
            converged = False
            for iter_count in range(50):  # Newton iterations
                f = sigma / E + (sigma / K) ** (1.0 / n) - eps
                df = 1.0 / E + (1.0 / (n * K)) * (sigma / K) ** (1.0 / n - 1.0)
                
                # Check for numerical issues
                if not np.isfinite(f) or not np.isfinite(df) or abs(df) < 1e-15:
                    break
                
                sigma_new = sigma - f / df
                sigma_new = max(sigma_y * 0.5, min(sigma_new, sigma_uts * 1.1))
                
                # Check convergence
                if abs(sigma_new - sigma) < 1e-3:
                    converged = True
                    sigma = sigma_new
                    break
                    
                sigma = sigma_new
            
            # Fallback if not converged: linear interpolation
            if not converged or not np.isfinite(sigma):
                sigma = sigma_y + (sigma_uts - sigma_y) * (eps - eps_y_elastic) / (elongation - eps_y_elastic)
            
            stress[i] = np.clip(sigma, 0.0, sigma_uts * 1.02)

    # Add realistic noise
    noise_array = rng.normal(0, noise * sigma_y, n_points)
    stress = stress + noise_array
    stress = np.clip(stress, 0.0, sigma_uts * 1.05)

    # Ensure elastic region is clean and monotonic
    elastic_end = int(n_points * 0.08)
    stress[:elastic_end] = E * strain[:elastic_end]
    
    # Ensure monotonicity in early plastic region
    for i in range(elastic_end, min(elastic_end + 10, n_points)):
        if i > 0 and stress[i] < stress[i-1]:
            stress[i] = stress[i-1]
    
    # Final validation
    if not np.all(np.isfinite(stress)):
        raise ValueError("Generated stress curve contains NaN or Inf")

    return strain, stress


def generate_dataset(cfg: DataConfig) -> pl.DataFrame:
    """Generate a synthetic TIG welding material properties dataset.

    The dataset captures:
    - Welding parameter effects on heat input
    - HAZ microstructure descriptors
    - Filler composition effects
    - Repair stage degradation (R0 → R3)
    - Realistic stress-strain curves (Ramberg-Osgood)

    Args:
        cfg: Data generation configuration.

    Returns:
        Polars DataFrame with all features and targets.
        
    Raises:
        ValueError: If configuration parameters are invalid.
    """
    # Validate configuration
    if cfg.n_samples <= 0:
        raise ValueError(f"n_samples must be positive, got {cfg.n_samples}")
    if cfg.n_stress_strain_points < 10:
        raise ValueError(f"n_stress_strain_points must be >= 10, got {cfg.n_stress_strain_points}")
    if not (0 <= cfg.noise_level <= 1):
        raise ValueError(f"noise_level must be in [0, 1], got {cfg.noise_level}")
    
    set_seed(cfg.random_state)
    rng = np.random.default_rng(cfg.random_state)
    n = cfg.n_samples

    logger.info(f"Generating {n} synthetic samples...")

    # ── Welding Parameters ──────────────────────────────────────────────────
    current_A = rng.uniform(80.0, 220.0, n)
    voltage_V = rng.uniform(10.0, 25.0, n)
    speed_mm_per_min = rng.uniform(80.0, 300.0, n)
    heat_input_kJ_per_mm = (current_A * voltage_V * 60.0) / (
        1000.0 * speed_mm_per_min
    ) + rng.normal(0, 0.02, n)
    heat_input_kJ_per_mm = np.clip(heat_input_kJ_per_mm, 0.05, 2.0)

    # ── Filler Composition (wt%) ────────────────────────────────────────────
    filler_C = rng.uniform(0.01, 0.08, n)
    filler_Mn = rng.uniform(0.5, 2.0, n)
    filler_Si = rng.uniform(0.1, 0.8, n)
    filler_Cr = rng.uniform(14.0, 25.0, n)
    filler_Ni = rng.uniform(8.0, 20.0, n)
    filler_Mo = rng.uniform(0.0, 4.0, n)
    filler_Ti = rng.uniform(0.0, 0.5, n)

    # ── HAZ Descriptors ──────────────────────────────────────────────────────
    haz_width_mm = 0.8 * heat_input_kJ_per_mm + rng.normal(0, 0.15, n)
    haz_width_mm = np.clip(haz_width_mm, 0.2, 3.5)
    haz_peak_temp_C = 800 + 600 * heat_input_kJ_per_mm + rng.normal(0, 50, n)
    haz_peak_temp_C = np.clip(haz_peak_temp_C, 600, 1400)
    haz_cooling_rate = 1000.0 / (heat_input_kJ_per_mm + 0.1) + rng.normal(0, 20, n)
    haz_cooling_rate = np.clip(haz_cooling_rate, 10, 2000)
    grain_size_um = 5.0 + 25.0 * heat_input_kJ_per_mm + rng.normal(0, 3, n)
    grain_size_um = np.clip(grain_size_um, 2, 80)

    # ── Repair Stage ─────────────────────────────────────────────────────────
    repair_stage = rng.integers(0, 4, n)

    # ── Physics-based property calculations ─────────────────────────────────
    # Base yield strength (Ti-6Al-4V class: ~900 MPa)
    ys_base = 900.0
    # Heat input softening
    ys_hi = -150.0 * heat_input_kJ_per_mm
    # Grain boundary strengthening (Hall-Petch like)
    ys_hp = 80.0 / np.sqrt(grain_size_um)
    # Cooling rate strengthening
    ys_cr = 5.0 * np.log1p(haz_cooling_rate)
    # Repair stage degradation
    ys_repair = -30.0 * repair_stage * (1 + 0.2 * repair_stage)
    # Filler contribution
    ys_filler = (
        20.0 * filler_Cr
        + 15.0 * filler_Ni
        + 30.0 * filler_Mo
        - 10.0 * filler_C
        + 5.0 * filler_Mn
    ) / 30.0
    # Interaction: high heat input + repair stage compound damage
    ys_interact = -20.0 * heat_input_kJ_per_mm * repair_stage

    yield_strength = (
        ys_base
        + ys_hi
        + ys_hp
        + ys_cr
        + ys_repair
        + ys_filler
        + ys_interact
        + rng.normal(0, cfg.noise_level * ys_base, n)
    )
    yield_strength = np.clip(yield_strength, 300.0, 1300.0)

    # UTS: always > yield by physical constraint
    uts_margin = rng.uniform(50.0, 200.0, n) + 10.0 * filler_Mo + 5.0 * filler_Cr
    uts = yield_strength + uts_margin + rng.normal(0, 20, n)
    uts = np.clip(uts, yield_strength + 20.0, 1600.0)

    # Elongation: inversely related to strength (ductility-strength tradeoff)
    elong_base = 18.0 - 0.008 * yield_strength + 2.0 * (4 - repair_stage)
    elongation = (
        elong_base
        + rng.normal(0, cfg.noise_level * 10, n)
        + 0.5 * heat_input_kJ_per_mm
    )
    elongation = np.clip(elongation, 2.0, 30.0)

    # ── Stress-Strain Curves ────────────────────────────────────────────────
    logger.info("Generating stress-strain curves...")
    all_strains: list[np.ndarray] = []
    all_stresses: list[np.ndarray] = []

    for i in range(n):
        eps_frac = elongation[i] / 100.0
        strain_arr, stress_arr = _ramberg_osgood_curve(
            sigma_y=float(yield_strength[i]),
            sigma_uts=float(uts[i]),
            elongation=eps_frac,
            n_points=cfg.n_stress_strain_points,
            noise=cfg.noise_level * 0.5,
            rng=rng,
        )
        all_strains.append(strain_arr)
        all_stresses.append(stress_arr)

    # ── Assemble DataFrame ──────────────────────────────────────────────────
    data: dict[str, list | np.ndarray] = {
        "current_A": current_A,
        "voltage_V": voltage_V,
        "speed_mm_per_min": speed_mm_per_min,
        "heat_input_kJ_per_mm": heat_input_kJ_per_mm,
        "filler_C": filler_C,
        "filler_Mn": filler_Mn,
        "filler_Si": filler_Si,
        "filler_Cr": filler_Cr,
        "filler_Ni": filler_Ni,
        "filler_Mo": filler_Mo,
        "filler_Ti": filler_Ti,
        "haz_width_mm": haz_width_mm,
        "haz_peak_temp_C": haz_peak_temp_C,
        "haz_cooling_rate": haz_cooling_rate,
        "grain_size_um": grain_size_um,
        "repair_stage": repair_stage.astype(np.float64),
        "yield_strength_MPa": yield_strength,
        "uts_MPa": uts,
        "elongation_pct": elongation,
    }

    # Add stress-strain columns
    for j in range(cfg.n_stress_strain_points):
        data[f"strain_{j:03d}"] = np.array([all_strains[i][j] for i in range(n)])
        data[f"stress_{j:03d}"] = np.array([all_stresses[i][j] for i in range(n)])

    df = pl.DataFrame(data)
    logger.info(f"[green]Dataset generated: {df.shape[0]} rows × {df.shape[1]} cols[/green]")
    return df


def save_dataset(df: pl.DataFrame, output_dir: str = "data") -> dict[str, Path]:
    """Split and save dataset to parquet files.

    Args:
        df: Full dataset as Polars DataFrame.
        output_dir: Directory to save splits.

    Returns:
        Dictionary mapping split name to file path.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    n = len(df)
    indices = np.random.permutation(n)
    n_test = int(n * 0.2)
    n_val = int(n * 0.1)

    test_idx = indices[:n_test]
    val_idx = indices[n_test : n_test + n_val]
    train_idx = indices[n_test + n_val :]

    splits = {
        "train": df[train_idx.tolist()],
        "val": df[val_idx.tolist()],
        "test": df[test_idx.tolist()],
    }

    paths: dict[str, Path] = {}
    for split_name, split_df in splits.items():
        path = out / f"{split_name}.parquet"
        split_df.write_parquet(path)
        paths[split_name] = path
        logger.info(f"Saved {split_name} split: {len(split_df)} rows → {path}")

    # Save full dataset too
    full_path = out / "full.parquet"
    df.write_parquet(full_path)
    paths["full"] = full_path

    return paths


def load_splits(data_dir: str = "data") -> dict[str, pl.DataFrame]:
    """Load train/val/test splits from parquet.

    Args:
        data_dir: Directory containing parquet files.

    Returns:
        Dictionary mapping split name to DataFrame.
    """
    data_dir = Path(data_dir)
    splits: dict[str, pl.DataFrame] = {}
    for split in ("train", "val", "test"):
        path = data_dir / f"{split}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Split file not found: {path}. Run data generation first.")
        splits[split] = pl.read_parquet(path)
        logger.debug(f"Loaded {split}: {splits[split].shape}")
    return splits


def get_feature_columns(n_stress_points: int = 50) -> dict[str, list[str]]:
    """Return column name lists for features and targets.

    Args:
        n_stress_points: Number of stress-strain curve points.

    Returns:
        Dictionary with 'features', 'scalar_targets', 'curve_strain', 'curve_stress'.
    """
    features = [
        "current_A",
        "voltage_V",
        "speed_mm_per_min",
        "heat_input_kJ_per_mm",
        "filler_C",
        "filler_Mn",
        "filler_Si",
        "filler_Cr",
        "filler_Ni",
        "filler_Mo",
        "filler_Ti",
        "haz_width_mm",
        "haz_peak_temp_C",
        "haz_cooling_rate",
        "grain_size_um",
        "repair_stage",
    ]
    scalar_targets = ["yield_strength_MPa", "uts_MPa", "elongation_pct"]
    curve_strain = [f"strain_{j:03d}" for j in range(n_stress_points)]
    curve_stress = [f"stress_{j:03d}" for j in range(n_stress_points)]

    return {
        "features": features,
        "scalar_targets": scalar_targets,
        "curve_strain": curve_strain,
        "curve_stress": curve_stress,
    }
