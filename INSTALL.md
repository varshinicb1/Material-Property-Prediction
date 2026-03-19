# Installation Guide

## System Requirements

- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended)
- 2GB disk space for models and data
- Windows, Linux, or macOS

## Quick Installation

### Option 1: From GitHub (Recommended)

```bash
# Clone repository
git clone https://github.com/varshinicb1/Material-Property-Prediction.git
cd Material-Property-Prediction

# Install package
pip install -e .

# Install optional dependencies
pip install -e .[gui,api]
```

### Option 2: Direct Install

```bash
pip install git+https://github.com/varshinicb1/Material-Property-Prediction.git
```

## Detailed Installation

### 1. Prerequisites

#### Python
Ensure Python 3.8+ is installed:
```bash
python --version
```

If not installed, download from [python.org](https://www.python.org/downloads/)

#### Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### 2. Clone Repository

```bash
git clone https://github.com/varshinicb1/Material-Property-Prediction.git
cd Material-Property-Prediction
```

### 3. Install Dependencies

#### Core Package
```bash
pip install -e .
```

#### With GUI Support
```bash
pip install -e .[gui]
```

#### With API Support
```bash
pip install -e .[api]
```

#### All Features
```bash
pip install -e .[gui,api,dev]
```

#### Manual Installation
```bash
pip install -r requirements.txt
```

### 4. Train Models

Before first use, train the models:

```bash
python main.py train
```

This will:
- Generate training data
- Train LightGBM, FT-Transformer, and CVAE models
- Save models to `models/saved/`
- Take approximately 5-10 minutes

### 5. Verify Installation

```bash
# Run tests
pytest

# Check CLI
python main.py --help

# Test prediction
python main.py predict --current 180 --voltage 12 --speed 150
```

## Platform-Specific Instructions

### Windows

```cmd
# Install
pip install -e .

# Train models
python main.py train

# Launch GUI
streamlit run app/streamlit_app.py

# Start API
python main.py api
```

### Linux/Mac

```bash
# Install
pip install -e .

# Train models
python main.py train

# Launch GUI
streamlit run app/streamlit_app.py

# Start API
python main.py api
```

### Docker (Optional)

```bash
# Build image
docker build -t material-ai .

# Run container
docker run -p 8501:8501 -p 8000:8000 material-ai
```

## Troubleshooting

### Issue: ModuleNotFoundError

**Solution:** Ensure package is installed
```bash
pip install -e .
```

### Issue: Models not found

**Solution:** Train models first
```bash
python main.py train
```

### Issue: CUDA/GPU errors

**Solution:** Install CPU-only PyTorch
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Issue: Streamlit not found

**Solution:** Install GUI dependencies
```bash
pip install -e .[gui]
```

### Issue: Permission denied

**Solution:** Use user install
```bash
pip install --user -e .
```

### Issue: Out of memory during training

**Solution:** Reduce batch size in `configs/training/default.yaml`
```yaml
batch_size: 32  # Reduce from 64
```

## Updating

### Update from GitHub

```bash
cd Material-Property-Prediction
git pull origin main
pip install -e . --upgrade
```

### Retrain Models

After updating, retrain models:
```bash
python main.py train
```

## Uninstallation

```bash
pip uninstall material-ai
```

## Development Installation

For contributing:

```bash
# Clone repository
git clone https://github.com/varshinicb1/Material-Property-Prediction.git
cd Material-Property-Prediction

# Install with dev dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Format code
black .

# Lint
flake8 .
```

## Verification Checklist

After installation, verify:

- [ ] Package imports: `python -c "import material_ai"`
- [ ] CLI works: `python main.py --help`
- [ ] Models exist: `ls models/saved/`
- [ ] Tests pass: `pytest`
- [ ] GUI launches: `streamlit run app/streamlit_app.py`
- [ ] API works: `python main.py api`

## Getting Help

- Documentation: [docs/INDEX.md](docs/INDEX.md)
- Issues: https://github.com/varshinicb1/Material-Property-Prediction/issues
- Quick Start: [docs/QUICK_START_GUIDE.md](docs/QUICK_START_GUIDE.md)

## Next Steps

After installation:

1. Read [README.md](README.md) for overview
2. Follow [docs/QUICK_START_GUIDE.md](docs/QUICK_START_GUIDE.md)
3. Try the GUI: `streamlit run app/streamlit_app.py`
4. Explore API: `python main.py api` then visit http://localhost:8000/docs
5. Run examples in [examples/](examples/) directory
