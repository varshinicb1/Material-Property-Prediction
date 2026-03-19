#!/usr/bin/env python3
"""Prepare repository for GitHub release.

This script:
1. Moves development/testing docs to docs/ folder
2. Keeps only essential docs in root
3. Creates clean directory structure
4. Generates release checklist
"""

import shutil
from pathlib import Path

# Files to keep in root
KEEP_IN_ROOT = {
    "README.md",
    "LICENSE",
}

# Files to move to docs/
MOVE_TO_DOCS = {
    "ACHIEVEMENT_SUMMARY.md",
    "API_DOCUMENTATION.md",
    "BUG_FIXES_FINAL.md",
    "BUG_FIXES_SUMMARY.md",
    "COMPREHENSIVE_TEST_SUMMARY.md",
    "DEPLOYMENT_GUIDE.md",
    "FINAL_VALIDATION_REPORT.md",
    "GUI_PROFESSIONAL_UPGRADE.md",
    "GUI_TESTING_GUIDE.md",
    "LAUNCH_GUI.md",
    "PRODUCTION_CHECKLIST.md",
    "QUICK_START_GUIDE.md",
    "README_WORLD_CLASS.md",
    "REAL_DATA_TEST_REPORT.md",
    "REAL_DATA_TESTING_SUMMARY.md",
    "RELEASE_NOTES.md",
    "SHIP_IT.md",
    "SHIPPING_MANIFEST.md",
    "test_gui_quick.md",
    "TESTING_GUIDE.md",
    "VALIDATION_REPORT.md",
    "WORLD_CLASS_FEATURES.md",
}

# Files to delete (temporary/redundant)
DELETE_FILES = set()

def main():
    root = Path(".")
    docs_dir = root / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("Preparing Release")
    print("=" * 60)
    
    # Move files to docs/
    print("\nMoving documentation files to docs/...")
    moved = 0
    for filename in MOVE_TO_DOCS:
        filepath = root / filename
        if filepath.exists():
            dest = docs_dir / filename
            shutil.move(str(filepath), str(dest))
            print(f"  Moved: {filename}")
            moved += 1
    
    print(f"\nMoved {moved} files to docs/")
    
    # Delete temporary files
    if DELETE_FILES:
        print("\nDeleting temporary files...")
        deleted = 0
        for filename in DELETE_FILES:
            filepath = root / filename
            if filepath.exists():
                filepath.unlink()
                print(f"  Deleted: {filename}")
                deleted += 1
        print(f"\nDeleted {deleted} files")
    
    # Create docs index
    print("\nCreating docs/INDEX.md...")
    index_content = """# Documentation Index

## User Documentation
- [Quick Start Guide](QUICK_START_GUIDE.md) - Get started quickly
- [API Documentation](API_DOCUMENTATION.md) - REST API reference
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment
- [GUI Testing Guide](GUI_TESTING_GUIDE.md) - How to test the GUI
- [Launch GUI](LAUNCH_GUI.md) - GUI launch instructions

## Development Documentation
- [Testing Guide](TESTING_GUIDE.md) - Running tests
- [Production Checklist](PRODUCTION_CHECKLIST.md) - Pre-release checklist

## Reports and Summaries
- [Achievement Summary](ACHIEVEMENT_SUMMARY.md) - Project achievements
- [Comprehensive Test Summary](COMPREHENSIVE_TEST_SUMMARY.md) - Test results
- [Final Validation Report](FINAL_VALIDATION_REPORT.md) - Validation results
- [Real Data Test Report](REAL_DATA_TEST_REPORT.md) - Real data testing
- [Release Notes](RELEASE_NOTES.md) - Version history

## Technical Details
- [World Class Features](WORLD_CLASS_FEATURES.md) - Advanced features
- [GUI Professional Upgrade](GUI_PROFESSIONAL_UPGRADE.md) - GUI improvements
- [Bug Fixes Summary](BUG_FIXES_SUMMARY.md) - Fixed issues
"""
    
    (docs_dir / "INDEX.md").write_text(index_content)
    print("  Created docs/INDEX.md")
    
    # Create .gitignore if not exists
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        print("\nCreating .gitignore...")
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Jupyter
.ipynb_checkpoints/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Logs
logs/*.log
*.log

# Models (large files)
models/saved/*.pt
models/saved/*.pkl

# Data (large files)
data/*.parquet
data/*.csv
!data/real_tig_welding_data.csv

# OS
.DS_Store
Thumbs.db

# Temporary
*.tmp
*.bak
.cache/
"""
        gitignore_path.write_text(gitignore_content)
        print("  Created .gitignore")
    
    # Create release checklist
    print("\nCreating RELEASE_CHECKLIST.md...")
    checklist_content = """# Release Checklist

## Pre-Release

- [ ] All tests passing (`pytest`)
- [ ] Code formatted (`black .`)
- [ ] No linting errors (`flake8 .`)
- [ ] Documentation updated
- [ ] README.md reviewed
- [ ] Version bumped in setup.py and __init__.py
- [ ] CHANGELOG.md updated
- [ ] Models trained and saved
- [ ] Example data included

## Git Preparation

- [ ] All changes committed
- [ ] Branch is clean (`git status`)
- [ ] Pushed to GitHub
- [ ] No sensitive data in commits

## GitHub Release

- [ ] Create release tag (v1.0.0)
- [ ] Write release notes
- [ ] Upload trained models (if applicable)
- [ ] Verify download links work

## Post-Release

- [ ] Test installation from GitHub
- [ ] Verify GUI launches
- [ ] Verify API works
- [ ] Check documentation links
- [ ] Announce release

## Commands

```bash
# Run tests
pytest

# Format code
black .

# Check git status
git status

# Create tag
git tag -a v1.0.0 -m "Release v1.0.0"

# Push tag
git push origin v1.0.0

# Test installation
pip install git+https://github.com/varshinicb1/Material-Property-Prediction.git
```
"""
    
    (root / "RELEASE_CHECKLIST.md").write_text(checklist_content)
    print("  Created RELEASE_CHECKLIST.md")
    
    print("\n" + "=" * 60)
    print("Release Preparation Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review README.md")
    print("2. Check RELEASE_CHECKLIST.md")
    print("3. Run: git add .")
    print("4. Run: git commit -m 'Prepare v1.0.0 release'")
    print("5. Run: git push origin main")
    print("6. Create GitHub release")

if __name__ == "__main__":
    main()
