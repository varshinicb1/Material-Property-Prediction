@echo off
REM Push Material AI to GitHub (Windows)

echo =========================================
echo Material AI - GitHub Release Script
echo =========================================
echo.

REM Check if git is initialized
if not exist ".git" (
    echo Initializing git repository...
    git init
    git branch -M main
)

REM Check for remote
git remote | findstr "origin" >nul
if errorlevel 1 (
    echo Adding GitHub remote...
    git remote add origin https://github.com/varshinicb1/Material-Property-Prediction.git
)

REM Stage all files
echo Staging files...
git add .

REM Show status
echo.
echo Git status:
git status --short

REM Commit
echo.
set /p commit_msg="Enter commit message (default: 'Release v1.0.0 - Production ready'): "
if "%commit_msg%"=="" set commit_msg=Release v1.0.0 - Production ready

echo Committing changes...
git commit -m "%commit_msg%"

REM Push
echo.
echo Pushing to GitHub...
git push -u origin main

REM Create tag
echo.
set /p create_tag="Create release tag v1.0.0? (y/n): "
if /i "%create_tag%"=="y" (
    git tag -a v1.0.0 -m "Release v1.0.0 - Production ready Material AI system"
    git push origin v1.0.0
    echo Tag v1.0.0 created and pushed
)

echo.
echo =========================================
echo Push complete!
echo =========================================
echo.
echo Next steps:
echo 1. Go to: https://github.com/varshinicb1/Material-Property-Prediction
echo 2. Click 'Releases' ^> 'Create a new release'
echo 3. Select tag v1.0.0
echo 4. Add release notes from CHANGELOG.md
echo 5. Publish release
echo.
pause
