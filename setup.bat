@echo off
:: ============================================================
:: material_ai — One-Command Setup Script (Windows)
:: ============================================================
:: Usage:
::   setup.bat
::
:: Requirements: Python 3.11+ must be installed and on PATH
:: ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo    Material AI -- TIG Weld Property Predictor Setup
echo ============================================================

:: ── 1. Python check ──────────────────────────────────────────────────────────
echo.
echo [1/5] Checking Python version...

set PYTHON_CMD=
for %%P in (python3.11 python3.12 python python3) do (
    where %%P >nul 2>&1
    if !errorlevel! == 0 (
        for /f "tokens=2 delims= " %%V in ('%%P --version 2^>^&1') do (
            set PYVER=%%V
        )
        echo   Found: !PYVER! at %%P
        set PYTHON_CMD=%%P
        goto :python_found
    )
)

echo ERROR: Python 3.11+ not found on PATH.
echo Please install Python 3.11+ from https://python.org
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:python_found

:: ── 2. Virtual environment ────────────────────────────────────────────────────
echo.
echo [2/5] Creating virtual environment (.venv)...

if exist ".venv\" (
    echo   Virtual environment already exists, reusing.
) else (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo   Virtual environment created.
)

:: Activate
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo   Activated virtual environment.

:: ── 3. Install dependencies ───────────────────────────────────────────────────
echo.
echo [3/5] Installing dependencies (this may take a few minutes)...
pip install --upgrade pip setuptools wheel --quiet
if errorlevel 1 (
    echo ERROR: pip upgrade failed.
    pause
    exit /b 1
)

pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Dependency installation failed. Check requirements.txt.
    pause
    exit /b 1
)
echo   All dependencies installed.

:: ── 4. Create directories ─────────────────────────────────────────────────────
echo.
echo [4/5] Setting up project directories...
if not exist "data\" mkdir data
if not exist "models\saved\" mkdir models\saved
if not exist "results\" mkdir results
if not exist "logs\" mkdir logs
if not exist "outputs\" mkdir outputs
echo   Directories ready.

:: ── 5. Train models ───────────────────────────────────────────────────────────
echo.
echo [5/5] Training models (this may take 5-15 minutes)...
echo   Generating synthetic dataset + training GBM, FT-Transformer, CVAE
python main.py train --force-regen
if errorlevel 1 (
    echo ERROR: Training failed. See error output above.
    pause
    exit /b 1
)
echo   Training complete.

echo.
echo ============================================================
echo    Setup Complete!
echo ============================================================
echo.
echo To launch the web app, run:
echo   run.bat
echo.
echo Or use the CLI:
echo   .venv\Scripts\activate.bat
echo   python main.py predict --current 150 --voltage 15 --speed 150
echo.
pause
