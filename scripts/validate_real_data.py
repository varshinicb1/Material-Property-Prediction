"""Validate trained models against real TIG welding experimental data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from inference.predictor import MaterialPredictor

console = Console()


def load_real_data(csv_path: str = "data/real_tig_welding_data.csv") -> pd.DataFrame:
    """Load real experimental data."""
    df = pd.read_csv(csv_path)
    console.print(f"[green]Loaded {len(df)} real experimental samples[/green]")
    return df


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Calculate regression metrics."""
    mse = np.mean((y_true - y_pred) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(y_true - y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return {
        "RMSE": rmse,
        "MAE": mae,
        "MAPE": mape,
        "R²": r2,
    }


def validate_on_real_data():
    """Validate models on real experimental data."""
    console.rule("[bold cyan]Validating on Real TIG Welding Data[/bold cyan]")
    
    # Load real data
    df = load_real_data()
    
    # Load predictor
    console.print("\n[yellow]Loading trained models...[/yellow]")
    try:
        predictor = MaterialPredictor(models_dir="models/saved")
    except Exception as e:
        console.print(f"[red]Error loading models: {e}[/red]")
        console.print("[yellow]Please train models first: python main.py train[/yellow]")
        return
    
    # Make predictions
    console.print("\n[yellow]Making predictions on real data...[/yellow]")
    predictions = []
    
    for idx, row in df.iterrows():
        # Build input (we only have basic parameters, need to estimate others)
        input_dict = predictor.build_input(
            current_A=row['current_A'],
            voltage_V=row['voltage_V'],
            speed_mm_per_min=row['speed_mm_per_min'],
            repair_stage=row['repair_stage'],
        )
        
        result = predictor.predict(input_dict)
        predictions.append({
            'sample_id': row['sample_id'],
            'repair_stage': row['repair_stage'],
            'true_yield': row['yield_strength_MPa'],
            'pred_yield': result.yield_strength_MPa,
            'true_uts': row['uts_MPa'],
            'pred_uts': result.uts_MPa,
            'true_elong': row['elongation_pct'],
            'pred_elong': result.elongation_pct,
        })
    
    pred_df = pd.DataFrame(predictions)
    
    # Calculate metrics
    console.print("\n[bold green]Validation Results[/bold green]\n")
    
    # Yield Strength
    yield_metrics = calculate_metrics(
        pred_df['true_yield'].values,
        pred_df['pred_yield'].values
    )
    
    # UTS
    uts_metrics = calculate_metrics(
        pred_df['true_uts'].values,
        pred_df['pred_uts'].values
    )
    
    # Elongation
    elong_metrics = calculate_metrics(
        pred_df['true_elong'].values,
        pred_df['pred_elong'].values
    )
    
    # Display metrics table
    table = Table(title="Validation Metrics on Real Data", show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("RMSE", style="yellow")
    table.add_column("MAE", style="yellow")
    table.add_column("MAPE (%)", style="yellow")
    table.add_column("R²", style="green")
    
    table.add_row(
        "Yield Strength (MPa)",
        f"{yield_metrics['RMSE']:.2f}",
        f"{yield_metrics['MAE']:.2f}",
        f"{yield_metrics['MAPE']:.2f}",
        f"{yield_metrics['R²']:.4f}",
    )
    table.add_row(
        "UTS (MPa)",
        f"{uts_metrics['RMSE']:.2f}",
        f"{uts_metrics['MAE']:.2f}",
        f"{uts_metrics['MAPE']:.2f}",
        f"{uts_metrics['R²']:.4f}",
    )
    table.add_row(
        "Elongation (%)",
        f"{elong_metrics['RMSE']:.2f}",
        f"{elong_metrics['MAE']:.2f}",
        f"{elong_metrics['MAPE']:.2f}",
        f"{elong_metrics['R²']:.4f}",
    )
    
    console.print(table)
    
    # Per repair stage analysis
    console.print("\n[bold]Performance by Repair Stage:[/bold]\n")
    
    for stage in sorted(pred_df['repair_stage'].unique()):
        stage_df = pred_df[pred_df['repair_stage'] == stage]
        
        stage_yield_metrics = calculate_metrics(
            stage_df['true_yield'].values,
            stage_df['pred_yield'].values
        )
        
        console.print(f"[cyan]R{stage}:[/cyan] "
                     f"Yield RMSE={stage_yield_metrics['RMSE']:.1f} MPa, "
                     f"R²={stage_yield_metrics['R²']:.3f}")
    
    # Sample predictions
    console.print("\n[bold]Sample Predictions vs Actual:[/bold]\n")
    
    sample_table = Table(show_header=True)
    sample_table.add_column("Sample", style="cyan")
    sample_table.add_column("Stage", style="white")
    sample_table.add_column("True Yield", style="green")
    sample_table.add_column("Pred Yield", style="yellow")
    sample_table.add_column("Error", style="red")
    
    for idx in [0, 5, 10, 15, 19]:  # Show one from each stage + last
        row = pred_df.iloc[idx]
        error = row['pred_yield'] - row['true_yield']
        sample_table.add_row(
            row['sample_id'],
            f"R{int(row['repair_stage'])}",
            f"{row['true_yield']:.1f}",
            f"{row['pred_yield']:.1f}",
            f"{error:+.1f}",
        )
    
    console.print(sample_table)
    
    # Save results
    output_path = "results/real_data_validation.csv"
    pred_df.to_csv(output_path, index=False)
    console.print(f"\n[green]Results saved to: {output_path}[/green]")
    
    # Summary
    console.print("\n[bold green]Summary:[/bold green]")
    console.print(f"  • Validated on {len(df)} real experimental samples")
    console.print(f"  • Yield Strength R²: {yield_metrics['R²']:.3f}")
    console.print(f"  • UTS R²: {uts_metrics['R²']:.3f}")
    console.print(f"  • Elongation R²: {elong_metrics['R²']:.3f}")
    
    if yield_metrics['R²'] > 0.7 and uts_metrics['R²'] > 0.6:
        console.print("\n[bold green]✅ Model performs well on real data![/bold green]")
    elif yield_metrics['R²'] > 0.5:
        console.print("\n[bold yellow]⚠️  Model shows moderate performance. Consider retraining with more data.[/bold yellow]")
    else:
        console.print("\n[bold red]❌ Model needs improvement. Retrain with real data or adjust parameters.[/bold red]")


if __name__ == "__main__":
    validate_on_real_data()
