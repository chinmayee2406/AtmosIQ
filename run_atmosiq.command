#!/bin/bash
# ==============================================================================
# AtmosIQ macOS Launcher
# Launches the AtmosIQ Streamlit Application using the project's .venv
# Double-click from Finder or execute from Terminal
# ==============================================================================

# Resolve the project root directory
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$PROJECT_DIR" || exit 1

echo "============================================================"
echo "          🌍 AtmosIQ - Climate Intelligence Platform        "
echo "============================================================"
echo " Project Directory: $PROJECT_DIR"

# Verify virtual environment
if [ ! -f "$PROJECT_DIR/.venv/bin/python" ]; then
    echo "❌ Error: Virtual environment (.venv) not found!"
    echo "Please ensure the project setup has been completed."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "✅ Virtual environment verified: $PROJECT_DIR/.venv"
echo "🚀 Starting Streamlit application on http://127.0.0.1:8501..."
echo "------------------------------------------------------------"

# Set non-intrusive environment variables
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
export MPLCONFIGDIR="/tmp"
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Automatically open default browser after a short pause
(sleep 2 && open "http://127.0.0.1:8501") &

# Launch Streamlit with .venv python
exec "$PROJECT_DIR/.venv/bin/streamlit" run "$PROJECT_DIR/streamlit_app.py" --server.port 8501 --server.address 127.0.0.1
