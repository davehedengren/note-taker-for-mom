#!/bin/bash
# Double-click this file to launch Session Notes.
# First run will set up a Python environment and download models (~5 GB).

set -e

# Navigate to the app directory (wherever this script lives)
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Also export for pyannote (it checks HF_TOKEN)
if [ -n "$HUGGING_FACE_API_KEY" ]; then
    export HF_TOKEN="$HUGGING_FACE_API_KEY"
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "============================================"
    echo "  Python 3 is required but not installed."
    echo "  Download it from: https://www.python.org/downloads/"
    echo "============================================"
    echo ""
    open "https://www.python.org/downloads/"
    read -p "Press Enter after installing Python 3..."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Found Python $PYTHON_VERSION"

# First-run: create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "============================================"
    echo "  First-time setup"
    echo "  Creating Python environment..."
    echo "============================================"
    echo ""
    python3 -m venv venv
    echo "Installing dependencies (this takes a few minutes)..."
    ./venv/bin/pip install --upgrade pip -q
    ./venv/bin/pip install -r requirements.txt
    echo ""
    echo "Dependencies installed. Launching setup wizard..."
fi

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "⚠  ffmpeg not found. It's needed for audio file conversion."
    echo "   Install with: brew install ffmpeg"
    echo "   (The app will still launch, but m4a/mp3 files won't work.)"
    echo ""
fi

# Launch the app
echo "Starting Session Notes..."
./venv/bin/python app.py
