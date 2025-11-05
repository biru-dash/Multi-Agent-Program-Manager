#!/bin/bash

# Start/Restart Backend Server Script
# This script starts or restarts the backend server with visible logs

cd "$(dirname "$0")/backend"

echo "=========================================="
echo "Starting/Restarting Backend Server"
echo "=========================================="
echo "Location: $(pwd)"
echo ""

# Check if port 8000 is already in use and stop existing server
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use. Stopping existing server..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 2
    echo "✅ Existing server stopped"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "Starting FastAPI server on http://localhost:8000"
echo "API docs available at http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server"
echo ""
echo "=========================================="
echo ""

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

