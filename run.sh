#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Fix for macOS Homebrew library path issues with WeasyPrint
if [ "$(uname)" == "Darwin" ] && [ -d "/opt/homebrew/lib" ]; then
    export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH"
fi

# Run the FastAPI app using Uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
