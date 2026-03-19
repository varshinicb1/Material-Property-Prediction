"""CLI entry point for material_ai using Typer.

Commands:
  train    — run full training pipeline
  evaluate — evaluate trained models on test set
  predict  — run inference on a single sample
  generate — generate and save a dataset
  app      — launch Streamlit app
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="material-ai",
    help="AI Framework for Material Property Prediction of TIG Welded Aerospace Structures",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def _load_default_cfg() -> dict:
    """Load default configuration from YAML files."""
    try:
        from omegaconf import OmegaConf

        base = OmegaConf.load("configs/config.yaml")
        data_cfg = OmegaConf.load("configs/data/default.yaml")
        model_cfg = OmegaConf.load("configs/model/default.yaml")
        train_cfg = OmegaConf.load("configs/training/default.yaml")

        merged = OmegaConf.merge(base, {"data": data_cfg, "model": model_cfg, "training": train_cfg})
        return OmegaConf.to_container(merged, resolve=True)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load configs: {e}. Using defaults.[/yellow]")
        return {}


@app.command()
def train(
    data_dir: str = typer.Option("data", "--data-dir", "-d", help="Dataset directory"),
    models_dir: str = typer.Option("models/saved", "--models-dir", "-m", help="Model save directory"),
    results_dir: str = typer.Option("results", "--results-dir", "-r", help="Results directory"),
    seed: int = typer.Option(42, "--seed", "-s", help="Random seed"),
    force_regen: bool = typer.Option(False, "--force-regen", help="Force data regeneration"),
) -> None:
    """[bold green]Train all models[/bold green]: GBM + FT-Transformer + CVAE."""
    console.rule("[bold cyan]Material AI — Training Pipeline[/bold cyan]")
    cfg = _load_default_cfg()

    from training.pipeline import run_pipeline
    metrics = run_pipeline(
        cfg=cfg,
        data_dir=data_dir,
        models_dir=models_dir,
        results_dir=results_dir,
        seed=seed,
        force_regenerate=force_regen,
    )

    console.print("\n[bold green]✅ Training Complete![/bold green]")

    table = Table(title="Test Set Metrics", show_header=True, header_style="bold magenta")
    table.add_column("Model", style="cyan")
    table.add_column("Metric", style="white")
    table.add_column("Value", style="green")

    for model_name, model_metrics in metrics.items():
        for metric_name, value in model_metrics.items():
            table.add_row(model_name, metric_name, f"{value:.4f}")

    console.print(table)


@app.command()
def evaluate(
    data_dir: str = typer.Option("data", "--data-dir"),
    models_dir: str = typer.Option("models/saved", "--models-dir"),
    results_dir: str = typer.Option("results", "--results-dir"),
) -> None:
    """[bold yellow]Evaluate[/bold yellow] trained models on the test split."""
    console.rule("[bold cyan]Material AI — Evaluation[/bold cyan]")

    try:
        import numpy as np
        import polars as pl
        import torch

        from data.generator import get_feature_columns
        from data.preprocessor import DataPreprocessor
        from models.gbm import GBMEnsemble
        from models.ft_transformer import FTTransformer
        from training.pipeline import _eval_scalar
        from utils.io import save_json

        # Validate paths
        splits_path = Path(data_dir) / "test.parquet"
        if not splits_path.exists():
            console.print("[red]Test set not found. Run 'train' first.[/red]")
            raise typer.Exit(1)

        models_path = Path(models_dir)
        required_files = ["preprocessor.pkl", "gbm.pkl", "ft_transformer.pt"]
        missing_files = [f for f in required_files if not (models_path / f).exists()]
        if missing_files:
            console.print(f"[red]Missing model files: {', '.join(missing_files)}[/red]")
            console.print("[yellow]Run 'python main.py train' first.[/yellow]")
            raise typer.Exit(1)

        # Load data
        test_df = pl.read_parquet(splits_path)
        cols = get_feature_columns(50)
        
        # Validate columns exist
        missing_cols = [c for c in cols["features"] if c not in test_df.columns]
        if missing_cols:
            console.print(f"[red]Missing columns in test data: {missing_cols}[/red]")
            raise typer.Exit(1)

        X_test = test_df.select(cols["features"]).to_numpy().astype("float32")
        y_test = test_df.select(cols["scalar_targets"]).to_numpy().astype("float32")

        # Check for NaN/Inf
        if np.any(~np.isfinite(X_test)) or np.any(~np.isfinite(y_test)):
            console.print("[red]Test data contains NaN or Inf values[/red]")
            raise typer.Exit(1)

        # Load preprocessor
        preprocessor = DataPreprocessor.load(models_path / "preprocessor.pkl")
        X_test_s = preprocessor.transform_input(X_test)

        # Load and evaluate GBM
        console.print("[cyan]Loading GBM model...[/cyan]")
        gbm = GBMEnsemble.load(models_path / "gbm.pkl")
        gbm_pred = gbm.predict(X_test)
        gbm_metrics = _eval_scalar(gbm_pred, y_test, cols["scalar_targets"])

        # Load and evaluate FT-Transformer
        console.print("[cyan]Loading FT-Transformer model...[/cyan]")
        ft_model = FTTransformer(
            n_features=len(cols["features"]), 
            n_targets=3,
            d_token=192, 
            n_blocks=3, 
            attention_n_heads=8,
            attention_dropout=0.2, 
            ffn_d_hidden=256, 
            ffn_dropout=0.1
        )
        ckpt = torch.load(models_path / "ft_transformer.pt", map_location="cpu", weights_only=True)
        ft_model.load_state_dict(ckpt["state_dict"])
        ft_model.eval()
        
        with torch.no_grad():
            deep_scaled = ft_model(torch.from_numpy(X_test_s)).numpy()
        deep_pred = preprocessor.inverse_scalar_targets(deep_scaled)
        deep_metrics = _eval_scalar(deep_pred, y_test, cols["scalar_targets"])

        # Save and display results
        Path(results_dir).mkdir(parents=True, exist_ok=True)
        all_metrics = {"gbm": gbm_metrics, "deep": deep_metrics}
        save_json(all_metrics, Path(results_dir) / "eval_metrics.json")

        table = Table(title="Evaluation Results", header_style="bold magenta")
        table.add_column("Model", style="cyan")
        table.add_column("Metric", style="white")
        table.add_column("Value", style="green")
        for model_name, m in all_metrics.items():
            for k, v in m.items():
                table.add_row(model_name, k, f"{v:.4f}")
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Evaluation failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def predict(
    current: float = typer.Option(150.0, "--current", help="Welding current (A)"),
    voltage: float = typer.Option(15.0, "--voltage", help="Arc voltage (V)"),
    speed: float = typer.Option(150.0, "--speed", help="Travel speed (mm/min)"),
    repair: int = typer.Option(0, "--repair", help="Repair stage (0-3)"),
    models_dir: str = typer.Option("models/saved", "--models-dir"),
) -> None:
    """[bold blue]Predict[/bold blue] material properties for given welding parameters."""
    console.rule("[bold cyan]Material AI — Inference[/bold cyan]")

    try:
        # Validate inputs
        if not (80 <= current <= 220):
            console.print("[yellow]Warning: Current outside typical range (80-220 A)[/yellow]")
        if not (10 <= voltage <= 25):
            console.print("[yellow]Warning: Voltage outside typical range (10-25 V)[/yellow]")
        if not (80 <= speed <= 300):
            console.print("[yellow]Warning: Speed outside typical range (80-300 mm/min)[/yellow]")
        if repair not in [0, 1, 2, 3]:
            console.print("[red]Error: Repair stage must be 0, 1, 2, or 3[/red]")
            raise typer.Exit(1)

        from inference.predictor import MaterialPredictor

        predictor = MaterialPredictor(models_dir=models_dir)
        input_dict = predictor.build_input(
            current_A=current,
            voltage_V=voltage,
            speed_mm_per_min=speed,
            repair_stage=repair,
        )
        result = predictor.predict(input_dict)

        table = Table(title="Prediction Results", header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Predicted Value", style="green bold")
        table.add_row("Yield Strength", f"{result.yield_strength_MPa:.1f} MPa")
        table.add_row("Ultimate Tensile Strength", f"{result.uts_MPa:.1f} MPa")
        table.add_row("Elongation", f"{result.elongation_pct:.2f} %")
        table.add_row("YS/UTS Ratio", f"{result.yield_strength_MPa / result.uts_MPa:.4f}")
        console.print(table)

        console.print(f"\n[dim]Stress-strain curve: {result.n_curve_points} points generated[/dim]")
        console.print(f"[dim]Physics check — Yield < UTS: {result.yield_strength_MPa < result.uts_MPa}[/dim]")
        
    except FileNotFoundError as e:
        console.print(f"[red]Model files not found: {e}[/red]")
        console.print("[yellow]Run 'python main.py train' first.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Prediction failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def generate(
    n_samples: int = typer.Option(2000, "--n-samples", help="Number of samples"),
    output_dir: str = typer.Option("data", "--output-dir"),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    """[bold]Generate[/bold] a synthetic training dataset."""
    from data.generator import DataConfig, generate_dataset, save_dataset

    cfg = DataConfig(n_samples=n_samples, random_state=seed)
    df = generate_dataset(cfg)
    paths = save_dataset(df, output_dir)
    console.print(f"[green]Dataset saved to:[/green]")
    for split, path in paths.items():
        console.print(f"  {split}: {path}")


@app.command()
def launch_app(
    port: int = typer.Option(8501, "--port", help="Streamlit port"),
) -> None:
    """[bold magenta]Launch[/bold magenta] the Streamlit web application."""
    import subprocess

    app_path = Path(__file__).parent / "app" / "streamlit_app.py"
    console.print(f"[cyan]Launching Streamlit app on port {port}...[/cyan]")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
        check=True,
    )


@app.command()
def api(
    host: str = typer.Option("0.0.0.0", "--host", help="API host"),
    port: int = typer.Option(8000, "--port", help="API port"),
) -> None:
    """[bold magenta]Start[/bold magenta] the REST API server."""
    console.print(f"[cyan]Starting API server on {host}:{port}...[/cyan]")
    
    try:
        from api.rest_api import start_api
        start_api(host=host, port=port)
    except ImportError:
        console.print("[red]FastAPI not installed. Install with: pip install fastapi uvicorn[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed to start API: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def batch_predict(
    input_csv: str = typer.Option(..., "--input", help="Input CSV file"),
    output_csv: str = typer.Option(..., "--output", help="Output CSV file"),
    models_dir: str = typer.Option("models/saved", "--models-dir"),
) -> None:
    """[bold blue]Batch predict[/bold blue] on CSV file."""
    console.rule("[bold cyan]Material AI — Batch Prediction[/bold cyan]")
    
    try:
        from inference.batch_predictor import BatchPredictor
        
        predictor = BatchPredictor(models_dir=models_dir)
        result = predictor.predict_csv(input_csv, output_csv, show_progress=True)
        
        console.print(f"\n[green]✅ Batch prediction complete![/green]")
        console.print(f"  Total samples: {result.total_samples}")
        console.print(f"  Successful: {len(result.predictions)}")
        console.print(f"  Errors: {len(result.errors)}")
        console.print(f"  Success rate: {result.success_rate:.1%}")
        console.print(f"  Output saved to: {output_csv}")
        
    except Exception as e:
        console.print(f"[red]Batch prediction failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def metrics(
    action: str = typer.Argument(..., help="Action: show, save, or clear"),
) -> None:
    """[bold yellow]Manage[/bold yellow] prediction metrics."""
    from utils.monitoring import get_metrics_tracker
    
    tracker = get_metrics_tracker()
    
    if action == "show":
        stats = tracker.get_statistics()
        
        table = Table(title="Prediction Metrics", header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Predictions", str(stats["total_predictions"]))
        table.add_row("Successful", str(stats.get("successful_predictions", 0)))
        table.add_row("Errors", str(stats["total_errors"]))
        table.add_row("Error Rate", f"{stats['error_rate']:.2%}")
        
        if "latency_stats" in stats:
            lat = stats["latency_stats"]
            table.add_row("Mean Latency", f"{lat['mean_ms']:.1f} ms")
            table.add_row("P95 Latency", f"{lat['p95_ms']:.1f} ms")
            table.add_row("P99 Latency", f"{lat['p99_ms']:.1f} ms")
        
        console.print(table)
        
    elif action == "save":
        filepath = tracker.save_metrics()
        console.print(f"[green]Metrics saved to: {filepath}[/green]")
        
    elif action == "clear":
        tracker.clear()
        console.print("[green]Metrics cleared[/green]")
        
    else:
        console.print(f"[red]Unknown action: {action}. Use: show, save, or clear[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
