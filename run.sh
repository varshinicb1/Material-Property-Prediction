#!/usr/bin/env bash
# ============================================================
# material_ai — Launch Streamlit App (Linux / macOS)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found. Run setup.sh first."
    exit 1
fi

source .venv/bin/activate

PORT=${PORT:-8501}
echo "Launching Material AI on http://localhost:${PORT}"
streamlit run app/streamlit_app.py \
    --server.port "$PORT" \
    --server.headless false \
    --browser.gatherUsageStats false
