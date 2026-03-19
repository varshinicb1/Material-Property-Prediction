#!/bin/bash
# Material AI - Real Data Testing Script
# This script demonstrates the complete workflow

echo "========================================"
echo "Material AI - Real Data Testing"
echo "========================================"
echo ""

echo "[1/5] Generating synthetic data..."
python main.py generate --n-samples 1000 --seed 123
if [ $? -ne 0 ]; then
    echo "ERROR: Data generation failed!"
    exit 1
fi
echo ""

echo "[2/5] Training all models..."
python main.py train --seed 123
if [ $? -ne 0 ]; then
    echo "ERROR: Training failed!"
    exit 1
fi
echo ""

echo "[3/5] Testing single predictions..."
echo "Testing R0 (baseline):"
python main.py predict --current 200 --voltage 15 --speed 120 --repair 0
echo ""
echo "Testing R1:"
python main.py predict --current 180 --voltage 12.5 --speed 150 --repair 1
echo ""
echo "Testing R2:"
python main.py predict --current 160 --voltage 11 --speed 180 --repair 2
echo ""
echo "Testing R3:"
python main.py predict --current 190 --voltage 14 --speed 140 --repair 3
echo ""

echo "[4/5] Creating batch test file..."
python -c "import polars as pl; df = pl.read_parquet('data/test.parquet'); df.head(10).select(['current_A', 'voltage_V', 'speed_mm_per_min', 'repair_stage', 'heat_input_kJ_per_mm', 'filler_C', 'filler_Mn', 'filler_Si', 'filler_Cr', 'filler_Ni', 'filler_Mo', 'filler_Ti', 'haz_width_mm', 'haz_peak_temp_C', 'haz_cooling_rate', 'grain_size_um']).write_csv('data/test_batch_10.csv')"
echo ""

echo "[5/5] Testing batch predictions..."
python main.py batch-predict --input data/test_batch_10.csv --output data/batch_results.csv
if [ $? -ne 0 ]; then
    echo "ERROR: Batch prediction failed!"
    exit 1
fi
echo ""

echo "========================================"
echo "All tests completed successfully!"
echo "========================================"
echo ""
echo "Results saved to:"
echo "  - data/batch_results.csv"
echo "  - REAL_DATA_TEST_REPORT.md"
echo ""
echo "To launch the GUI, run:"
echo "  python main.py app"
echo ""
echo "To start the REST API, run:"
echo "  python main.py api"
echo ""
