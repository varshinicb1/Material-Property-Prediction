"""Comprehensive testing of Material AI system on massive dataset."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import polars as pl
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.progress import track
import time

from inference.predictor import MaterialPredictor

console = Console()


def test_comprehensive():
    """Run comprehensive tests on the system."""
    console.rule("[bold cyan]Material AI - Comprehensive Testing[/bold cyan]")
    
    # Load test data
    console.print("\n[yellow]Loading test dataset (1000 samples)...[/yellow]")
    df = pl.read_parquet("data/test.parquet")
    console.print(f"[green]✓ Loaded {len(df)} test samples[/green]")
    
    # Load predictor
    console.print("\n[yellow]Loading trained models...[/yellow]")
    predictor = MaterialPredictor(models_dir="models/saved")
    console.print("[green]✓ Models loaded successfully[/green]")
    
    # Test 1: Accuracy on test set
    console.print("\n[bold]Test 1: Model Accuracy on 1000 Samples[/bold]")
    
    y_true_yield = []
    y_pred_yield = []
    y_true_uts = []
    y_pred_uts = []
    y_true_elong = []
    y_pred_elong = []
    
    latencies = []
    
    for row in track(df.iter_rows(named=True), total=len(df), description="Predicting"):
        start = time.time()
        
        input_dict = {
            'current_A': row['current_A'],
            'voltage_V': row['voltage_V'],
            'speed_mm_per_min': row['speed_mm_per_min'],
            'repair_stage': row['repair_stage'],
            'heat_input_kJ_per_mm': row['heat_input_kJ_per_mm'],
            'filler_C': row['filler_C'],
            'filler_Mn': row['filler_Mn'],
            'filler_Si': row['filler_Si'],
            'filler_Cr': row['filler_Cr'],
            'filler_Ni': row['filler_Ni'],
            'filler_Mo': row['filler_Mo'],
            'filler_Ti': row['filler_Ti'],
            'haz_width_mm': row['haz_width_mm'],
            'haz_peak_temp_C': row['haz_peak_temp_C'],
            'haz_cooling_rate': row['haz_cooling_rate'],
            'grain_size_um': row['grain_size_um'],
        }
        
        result = predictor.predict(input_dict, track_metrics=False)
        
        latencies.append((time.time() - start) * 1000)  # ms
        
        y_true_yield.append(row['yield_strength_MPa'])
        y_pred_yield.append(result.yield_strength_MPa)
        y_true_uts.append(row['uts_MPa'])
        y_pred_uts.append(result.uts_MPa)
        y_true_elong.append(row['elongation_pct'])
        y_pred_elong.append(result.elongation_pct)
    
    # Calculate metrics
    def calc_metrics(y_true, y_pred):
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        mae = np.mean(np.abs(y_true - y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot)
        return rmse, mae, mape, r2
    
    yield_rmse, yield_mae, yield_mape, yield_r2 = calc_metrics(y_true_yield, y_pred_yield)
    uts_rmse, uts_mae, uts_mape, uts_r2 = calc_metrics(y_true_uts, y_pred_uts)
    elong_rmse, elong_mae, elong_mape, elong_r2 = calc_metrics(y_true_elong, y_pred_elong)
    
    table = Table(title="Accuracy Metrics (1000 Test Samples)")
    table.add_column("Property", style="cyan")
    table.add_column("RMSE", style="yellow")
    table.add_column("MAE", style="yellow")
    table.add_column("MAPE (%)", style="yellow")
    table.add_column("R²", style="green bold")
    
    table.add_row("Yield Strength (MPa)", f"{yield_rmse:.2f}", f"{yield_mae:.2f}", f"{yield_mape:.2f}", f"{yield_r2:.4f}")
    table.add_row("UTS (MPa)", f"{uts_rmse:.2f}", f"{uts_mae:.2f}", f"{uts_mape:.2f}", f"{uts_r2:.4f}")
    table.add_row("Elongation (%)", f"{elong_rmse:.2f}", f"{elong_mae:.2f}", f"{elong_mape:.2f}", f"{elong_r2:.4f}")
    
    console.print(table)
    
    # Test 2: Performance metrics
    console.print("\n[bold]Test 2: Performance Metrics[/bold]")
    
    latencies = np.array(latencies)
    perf_table = Table(title="Inference Performance")
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Value", style="green")
    
    perf_table.add_row("Total Predictions", f"{len(latencies)}")
    perf_table.add_row("Mean Latency", f"{np.mean(latencies):.2f} ms")
    perf_table.add_row("Median Latency", f"{np.median(latencies):.2f} ms")
    perf_table.add_row("P95 Latency", f"{np.percentile(latencies, 95):.2f} ms")
    perf_table.add_row("P99 Latency", f"{np.percentile(latencies, 99):.2f} ms")
    perf_table.add_row("Throughput", f"{1000 / np.mean(latencies):.1f} predictions/sec")
    
    console.print(perf_table)
    
    # Test 3: Physics validation
    console.print("\n[bold]Test 3: Physics Constraints Validation[/bold]")
    
    physics_violations = 0
    for yt, pt, yu, pu in zip(y_true_yield, y_pred_yield, y_true_uts, y_pred_uts):
        if pt >= pu:  # Yield should be < UTS
            physics_violations += 1
    
    physics_table = Table(title="Physics Validation")
    physics_table.add_column("Check", style="cyan")
    physics_table.add_column("Result", style="green")
    
    physics_table.add_row("Total Predictions", f"{len(y_pred_yield)}")
    physics_table.add_row("Physics Violations (Yield ≥ UTS)", f"{physics_violations}")
    physics_table.add_row("Compliance Rate", f"{(1 - physics_violations/len(y_pred_yield))*100:.2f}%")
    
    console.print(physics_table)
    
    # Test 4: Per repair stage analysis
    console.print("\n[bold]Test 4: Performance by Repair Stage[/bold]")
    
    stage_table = Table(title="Metrics by Repair Stage")
    stage_table.add_column("Stage", style="cyan")
    stage_table.add_column("Samples", style="white")
    stage_table.add_column("Yield R²", style="green")
    stage_table.add_column("UTS R²", style="green")
    stage_table.add_column("Elong R²", style="green")
    
    for stage in [0, 1, 2, 3]:
        stage_df = df.filter(pl.col('repair_stage') == stage)
        stage_indices = [i for i, row in enumerate(df.iter_rows(named=True)) if row['repair_stage'] == stage]
        
        if len(stage_indices) > 0:
            stage_y_true_yield = [y_true_yield[i] for i in stage_indices]
            stage_y_pred_yield = [y_pred_yield[i] for i in stage_indices]
            stage_y_true_uts = [y_true_uts[i] for i in stage_indices]
            stage_y_pred_uts = [y_pred_uts[i] for i in stage_indices]
            stage_y_true_elong = [y_true_elong[i] for i in stage_indices]
            stage_y_pred_elong = [y_pred_elong[i] for i in stage_indices]
            
            _, _, _, stage_yield_r2 = calc_metrics(stage_y_true_yield, stage_y_pred_yield)
            _, _, _, stage_uts_r2 = calc_metrics(stage_y_true_uts, stage_y_pred_uts)
            _, _, _, stage_elong_r2 = calc_metrics(stage_y_true_elong, stage_y_pred_elong)
            
            stage_table.add_row(
                f"R{stage}",
                f"{len(stage_indices)}",
                f"{stage_yield_r2:.4f}",
                f"{stage_uts_r2:.4f}",
                f"{stage_elong_r2:.4f}"
            )
    
    console.print(stage_table)
    
    # Test 5: Error distribution
    console.print("\n[bold]Test 5: Error Distribution Analysis[/bold]")
    
    yield_errors = np.array(y_pred_yield) - np.array(y_true_yield)
    uts_errors = np.array(y_pred_uts) - np.array(y_true_uts)
    elong_errors = np.array(y_pred_elong) - np.array(y_true_elong)
    
    error_table = Table(title="Error Distribution")
    error_table.add_column("Property", style="cyan")
    error_table.add_column("Mean Error", style="yellow")
    error_table.add_column("Std Error", style="yellow")
    error_table.add_column("Max |Error|", style="red")
    
    error_table.add_row(
        "Yield Strength (MPa)",
        f"{np.mean(yield_errors):+.2f}",
        f"{np.std(yield_errors):.2f}",
        f"{np.max(np.abs(yield_errors)):.2f}"
    )
    error_table.add_row(
        "UTS (MPa)",
        f"{np.mean(uts_errors):+.2f}",
        f"{np.std(uts_errors):.2f}",
        f"{np.max(np.abs(uts_errors)):.2f}"
    )
    error_table.add_row(
        "Elongation (%)",
        f"{np.mean(elong_errors):+.2f}",
        f"{np.std(elong_errors):.2f}",
        f"{np.max(np.abs(elong_errors)):.2f}"
    )
    
    console.print(error_table)
    
    # Final summary
    console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
    console.print("[bold green]         COMPREHENSIVE TEST SUMMARY         [/bold green]")
    console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
    
    console.print(f"✓ Dataset Size: [bold]{len(df)}[/bold] samples")
    console.print(f"✓ Yield Strength R²: [bold]{yield_r2:.4f}[/bold]")
    console.print(f"✓ UTS R²: [bold]{uts_r2:.4f}[/bold]")
    console.print(f"✓ Elongation R²: [bold]{elong_r2:.4f}[/bold]")
    console.print(f"✓ Mean Latency: [bold]{np.mean(latencies):.2f} ms[/bold]")
    console.print(f"✓ Physics Compliance: [bold]{(1 - physics_violations/len(y_pred_yield))*100:.2f}%[/bold]")
    
    if yield_r2 > 0.80 and uts_r2 > 0.70 and elong_r2 > 0.85:
        console.print("\n[bold green]🎉 EXCELLENT PERFORMANCE - PRODUCTION READY![/bold green]")
    elif yield_r2 > 0.70 and uts_r2 > 0.60:
        console.print("\n[bold yellow]✓ GOOD PERFORMANCE - ACCEPTABLE FOR DEPLOYMENT[/bold yellow]")
    else:
        console.print("\n[bold red]⚠ NEEDS IMPROVEMENT[/bold red]")


if __name__ == "__main__":
    test_comprehensive()
