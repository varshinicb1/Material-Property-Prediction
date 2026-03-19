"""End-to-end training pipeline: data → preprocessing → models → evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from data.generator import DataConfig, generate_dataset, save_dataset, load_splits
from data.preprocessor import DataPreprocessor, ProcessedData
from models.gbm import GBMEnsemble
from models.ft_transformer import FTTransformer
from models.cvae import CVAE
from training.trainer_deep import DeepTrainer
from training.trainer_cvae import CVAETrainer
from utils.io import save_json
from utils.logging import get_logger, log_section
from utils.seed import set_seed

logger = get_logger(__name__)


def run_pipeline(
    cfg: dict[str, Any],
    data_dir: str = "data",
    models_dir: str = "models/saved",
    results_dir: str = "results",
    seed: int = 42,
    force_regenerate: bool = False,
) -> dict[str, Any]:
    """Run the full training pipeline.

    Steps:
        1. Generate/load synthetic dataset
        2. Preprocess features and targets
        3. Train LightGBM ensemble
        4. Train FT-Transformer
        5. Train Conditional VAE
        6. Evaluate all models
        7. Save everything

    Args:
        cfg: Configuration dictionary.
        data_dir: Directory for dataset files.
        models_dir: Directory to save trained models.
        results_dir: Directory to save evaluation results.
        seed: Random seed.
        force_regenerate: If True, regenerate data even if it exists.

    Returns:
        Dictionary of evaluation metrics per model.
        
    Raises:
        ValueError: If configuration is invalid.
        RuntimeError: If training fails.
    """
    # Validate configuration structure
    if not isinstance(cfg, dict):
        raise ValueError(f"Configuration must be a dictionary, got {type(cfg)}")
    
    # Validate required sections exist
    required_sections = ["data", "model", "training"]
    for section in required_sections:
        if section not in cfg:
            logger.warning(f"Missing config section '{section}', using defaults")
            cfg[section] = {}
    
    set_seed(seed)
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    Path(results_dir).mkdir(parents=True, exist_ok=True)

    try:
        # ── Step 1: Data ──────────────────────────────────────────────────────
        log_section(logger, "Step 1: Data Generation")
        train_path = Path(data_dir) / "train.parquet"
        if force_regenerate or not train_path.exists():
            data_cfg = DataConfig(
                n_samples=cfg.get("data", {}).get("n_samples", 2000),
                n_stress_strain_points=cfg.get("data", {}).get("n_stress_strain_points", 50),
                noise_level=cfg.get("data", {}).get("noise_level", 0.05),
                random_state=seed,
            )
            df = generate_dataset(data_cfg)
            save_dataset(df, data_dir)
        else:
            logger.info(f"Dataset already exists at {data_dir}, loading...")

        splits = load_splits(data_dir)
        train_df, val_df, test_df = splits["train"], splits["val"], splits["test"]
        n_stress_points = cfg.get("data", {}).get("n_stress_strain_points", 50)

        # ── Step 2: Preprocessing ─────────────────────────────────────────────
        log_section(logger, "Step 2: Preprocessing")
        preprocessor = DataPreprocessor(n_stress_points=n_stress_points)
        proc = preprocessor.fit_transform(train_df, val_df, test_df)
        preprocessor.save(Path(models_dir) / "preprocessor.pkl")

        # Raw (unscaled) targets for GBM training
        from data.generator import get_feature_columns
        cols = get_feature_columns(n_stress_points)
        y_train_raw = train_df.select(cols["scalar_targets"]).to_numpy().astype(np.float32)
        y_val_raw = val_df.select(cols["scalar_targets"]).to_numpy().astype(np.float32)
        y_test_raw = test_df.select(cols["scalar_targets"]).to_numpy().astype(np.float32)

        metrics: dict[str, Any] = {}

        # ── Step 3: LightGBM ─────────────────────────────────────────────────
        log_section(logger, "Step 3: LightGBM Training")
        gbm_cfg = cfg.get("model", {}).get("gbm", {})
        gbm = GBMEnsemble(
            n_estimators=gbm_cfg.get("n_estimators", 500),
            learning_rate=gbm_cfg.get("learning_rate", 0.05),
            max_depth=gbm_cfg.get("max_depth", 7),
            num_leaves=gbm_cfg.get("num_leaves", 63),
            early_stopping_rounds=gbm_cfg.get("early_stopping_rounds", 50),
            random_state=seed,
        )
        gbm.fit(
            proc.X_train, y_train_raw,
            proc.X_val, y_val_raw,
            feature_names=proc.feature_names,
            target_names=proc.target_names,
        )
        gbm.save(Path(models_dir) / "gbm.pkl")
        gbm_test_pred = gbm.predict(proc.X_test)
        gbm_metrics = _eval_scalar(gbm_test_pred, y_test_raw, proc.target_names)
        metrics["gbm"] = gbm_metrics
        logger.info(f"GBM test metrics: {gbm_metrics}")

        # ── Step 4: FT-Transformer ─────────────────────────────────────────────
        log_section(logger, "Step 4: FT-Transformer Training")
        deep_cfg = cfg.get("model", {}).get("deep", {})
        train_cfg = cfg.get("training", {}).get("deep", {})
        ft_model = FTTransformer(
            n_features=proc.n_features,
            n_targets=len(proc.target_names),
            d_token=deep_cfg.get("d_token", 192),
            n_blocks=deep_cfg.get("n_blocks", 3),
            attention_n_heads=deep_cfg.get("attention_n_heads", 8),
            attention_dropout=deep_cfg.get("attention_dropout", 0.2),
            ffn_d_hidden=deep_cfg.get("ffn_d_hidden", 256),
            ffn_dropout=deep_cfg.get("ffn_dropout", 0.1),
        )
        deep_trainer = DeepTrainer(ft_model, use_compile=train_cfg.get("use_compile", False))
        deep_trainer.train(
            proc.X_train, proc.y_scalar_train,
            proc.X_val, proc.y_scalar_val,
            epochs=train_cfg.get("epochs", 100),
            batch_size=train_cfg.get("batch_size", 64),
            learning_rate=train_cfg.get("learning_rate", 1e-3),
            weight_decay=train_cfg.get("weight_decay", 1e-4),
            warmup_epochs=train_cfg.get("warmup_epochs", 5),
            patience=train_cfg.get("patience", 20),
            gradient_clip=train_cfg.get("gradient_clip", 1.0),
            save_path=Path(models_dir) / "ft_transformer.pt",
        )
        deep_pred_scaled = deep_trainer.predict(proc.X_test)
        deep_pred = preprocessor.inverse_scalar_targets(deep_pred_scaled)
        deep_metrics = _eval_scalar(deep_pred, y_test_raw, proc.target_names)
        metrics["deep"] = deep_metrics
        logger.info(f"Deep model test metrics: {deep_metrics}")

        # ── Step 5: CVAE ──────────────────────────────────────────────────────
        log_section(logger, "Step 5: CVAE Training")
        cvae_cfg = cfg.get("model", {}).get("cvae", {})
        cvae_train_cfg = cfg.get("training", {}).get("cvae", {})
        cvae_model = CVAE(
            n_features=proc.n_features,
            curve_dim=n_stress_points,
            latent_dim=cvae_cfg.get("latent_dim", 32),
            condition_dim=cvae_cfg.get("condition_dim", 64),
            encoder_hidden=cvae_cfg.get("encoder_hidden", [256, 128]),
            decoder_hidden=cvae_cfg.get("decoder_hidden", [128, 256]),
        )
        cvae_trainer = CVAETrainer(cvae_model)
        cvae_trainer.train(
            proc.X_train, proc.y_stress_train,
            proc.X_val, proc.y_stress_val,
            epochs=cvae_train_cfg.get("epochs", 150),
            batch_size=cvae_train_cfg.get("batch_size", 64),
            learning_rate=cvae_train_cfg.get("learning_rate", 1e-3),
            beta=cvae_cfg.get("beta", 1.0),
            kl_warmup_epochs=cvae_train_cfg.get("kl_warmup_epochs", 20),
            patience=cvae_train_cfg.get("patience", 30),
            save_path=Path(models_dir) / "cvae.pt",
        )
        curve_pred_scaled = cvae_trainer.generate_curves(proc.X_test)
        curve_pred = preprocessor.inverse_stress(curve_pred_scaled)
        y_stress_test_raw = preprocessor.inverse_stress(proc.y_stress_test)
        cvae_mse = float(np.mean((curve_pred - y_stress_test_raw) ** 2))
        metrics["cvae"] = {"curve_mse": cvae_mse}
        logger.info(f"CVAE curve MSE: {cvae_mse:.4f}")

        # ── Save metrics ──────────────────────────────────────────────────────
        save_json(metrics, Path(results_dir) / "metrics.json")
        log_section(logger, "Training Pipeline Complete")
        return metrics
        
    except Exception as e:
        logger.error(f"Training pipeline failed: {e}")
        raise RuntimeError(f"Training pipeline failed: {e}") from e


def _eval_scalar(
    pred: np.ndarray,
    true: np.ndarray,
    target_names: list[str],
) -> dict[str, float]:
    """Compute RMSE and R² per target.

    Args:
        pred: Predicted values, shape (N, T).
        true: Ground-truth values, shape (N, T).
        target_names: Names of each target.

    Returns:
        Flat metrics dictionary.
    """
    metrics: dict[str, float] = {}
    for i, name in enumerate(target_names):
        rmse = float(np.sqrt(np.mean((pred[:, i] - true[:, i]) ** 2)))
        ss_res = float(np.sum((pred[:, i] - true[:, i]) ** 2))
        ss_tot = float(np.sum((true[:, i] - true[:, i].mean()) ** 2))
        r2 = 1.0 - ss_res / (ss_tot + 1e-8)
        metrics[f"{name}_rmse"] = rmse
        metrics[f"{name}_r2"] = r2
    return metrics
