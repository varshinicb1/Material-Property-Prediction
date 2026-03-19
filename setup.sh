#!/usr/bin/env bash
# ============================================================
# material_ai — One-Command Setup Script (Linux / macOS)
# ============================================================
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# What this does:
#   1. Checks Python 3.11+
#   2. Creates virtual environment (.venv)
#   3. Upgrades pip + installs all dependencies
#   4. Generates synthetic dataset
#   5. Trains all models (GBM + FT-Transformer + CVAE)
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}   Material AI — TIG Weld Property Predictor Setup${NC}"
echo -e "${CYAN}============================================================${NC}"

# ── 1. Python version check ──────────────────────────────────────────────────
echo -e "\n${YELLOW}[1/5] Checking Python version...${NC}"

PYTHON_CMD=""
for cmd in python3.11 python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VERSION=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        MAJOR=$(echo "$VERSION" | cut -d. -f1)
        MINOR=$(echo "$VERSION" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON_CMD="$cmd"
            echo -e "  ${GREEN}✓ Found Python $VERSION at $(command -v $cmd)${NC}"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}ERROR: Python 3.11+ is required but not found.${NC}"
    echo "Please install Python 3.11 or higher from https://python.org"
    exit 1
fi

# ── 2. Virtual environment ───────────────────────────────────────────────────
echo -e "\n${YELLOW}[2/5] Creating virtual environment (.venv)...${NC}"
if [ -d ".venv" ]; then
    echo -e "  ${CYAN}Virtual environment already exists, reusing.${NC}"
else
    "$PYTHON_CMD" -m venv .venv
    echo -e "  ${GREEN}✓ Virtual environment created at .venv/${NC}"
fi

# Activate venv
source .venv/bin/activate
echo -e "  ${GREEN}✓ Activated: $(python --version)${NC}"

# ── 3. Install dependencies ──────────────────────────────────────────────────
echo -e "\n${YELLOW}[3/5] Installing dependencies...${NC}"
pip install --upgrade pip setuptools wheel --quiet
pip install -r requirements.txt --quiet
echo -e "  ${GREEN}✓ All dependencies installed${NC}"

# ── 4. Create required directories ──────────────────────────────────────────
echo -e "\n${YELLOW}[4/5] Setting up project directories...${NC}"
mkdir -p data models/saved results logs outputs
echo -e "  ${GREEN}✓ Directories ready${NC}"

# ── 5. Train models ──────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[5/5] Training models (this may take 5-15 minutes)...${NC}"
echo -e "  ${CYAN}Generating synthetic dataset + training GBM, FT-Transformer, CVAE${NC}"
python main.py train --force-regen
echo -e "  ${GREEN}✓ Training complete${NC}"

echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}   Setup Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e ""
echo -e "To launch the web app, run:"
echo -e "  ${CYAN}./run.sh${NC}"
echo -e ""
echo -e "Or use the CLI:"
echo -e "  ${CYAN}source .venv/bin/activate${NC}"
echo -e "  ${CYAN}python main.py predict --current 150 --voltage 15 --speed 150${NC}"
echo -e ""
