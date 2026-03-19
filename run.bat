@echo off
:: ============================================================
:: material_ai — Launch Streamlit App (Windows)
:: ============================================================
cd /d "%~dp0"

if not exist ".venv\" (
    echo ERROR: Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

set PORT=8501
echo Launching Material AI on http://localhost:%PORT%
streamlit run app\streamlit_app.py ^
    --server.port %PORT% ^
    --server.headless false ^
    --browser.gatherUsageStats false
