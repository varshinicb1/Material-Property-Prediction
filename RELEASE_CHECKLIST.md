# Release Checklist

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
