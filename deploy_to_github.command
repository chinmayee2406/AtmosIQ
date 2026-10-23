#!/bin/bash
# ==============================================================================
# AtmosIQ GitHub Deployment Script
# Pushes the local AtmosIQ repository to your GitHub account (chinmayee2406)
# ==============================================================================

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$PROJECT_DIR" || exit 1

echo "============================================================"
echo "           🚀 AtmosIQ — GitHub Deployment Helper            "
echo "============================================================"
echo "Project Directory: $PROJECT_DIR"
echo "Target Remote:     https://github.com/chinmayee2406/AtmosIQ.git"
echo "Branch:            main"
echo "------------------------------------------------------------"
echo "Pushing code, datasets, models, and configuration to GitHub..."

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ Successfully pushed AtmosIQ to GitHub!"
    echo "Repository: https://github.com/chinmayee2406/AtmosIQ"
    echo "============================================================"
    echo ""
    echo "Next step: Deploy to Streamlit Community Cloud"
    echo "1. In your browser at http://127.0.0.1:8501, click the 'Deploy' button in the top right corner."
    echo "   OR go to https://share.streamlit.io and select 'chinmayee2406/AtmosIQ'."
    echo "2. App file: app/main.py"
    echo "3. Click 'Deploy!'."
else
    echo ""
    echo "============================================================"
    echo "⚠️ Push encountered an issue."
    echo "Please ensure you have created an empty repository named 'AtmosIQ'"
    echo "on your GitHub account at: https://github.com/new"
    echo "============================================================"
fi

read -p "Press Enter to exit..."
