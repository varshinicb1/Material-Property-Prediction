#!/bin/bash
# Push Material AI to GitHub

echo "========================================="
echo "Material AI - GitHub Release Script"
echo "========================================="
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    git branch -M main
fi

# Check for remote
if ! git remote | grep -q "origin"; then
    echo "Adding GitHub remote..."
    git remote add origin https://github.com/varshinicb1/Material-Property-Prediction.git
fi

# Stage all files
echo "Staging files..."
git add .

# Show status
echo ""
echo "Git status:"
git status --short

# Commit
echo ""
read -p "Enter commit message (default: 'Release v1.0.0 - Production ready'): " commit_msg
commit_msg=${commit_msg:-"Release v1.0.0 - Production ready"}

echo "Committing changes..."
git commit -m "$commit_msg"

# Push
echo ""
echo "Pushing to GitHub..."
git push -u origin main

# Create tag
echo ""
read -p "Create release tag v1.0.0? (y/n): " create_tag
if [ "$create_tag" = "y" ]; then
    git tag -a v1.0.0 -m "Release v1.0.0 - Production ready Material AI system"
    git push origin v1.0.0
    echo "Tag v1.0.0 created and pushed"
fi

echo ""
echo "========================================="
echo "Push complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Go to: https://github.com/varshinicb1/Material-Property-Prediction"
echo "2. Click 'Releases' > 'Create a new release'"
echo "3. Select tag v1.0.0"
echo "4. Add release notes from CHANGELOG.md"
echo "5. Publish release"
