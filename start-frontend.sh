#!/bin/bash

# Start/Restart Frontend Server Script
# This script starts or restarts the frontend server with visible logs

cd "$(dirname "$0")"

echo "=========================================="
echo "Starting/Restarting Frontend Server"
echo "=========================================="
echo "Location: $(pwd)"
echo ""

# Find and stop existing Vite processes for this project
VITE_PIDS=$(ps aux | grep "Multi-Agent-Program-Manager.*vite" | grep -v grep | awk '{print $2}')
if [ ! -z "$VITE_PIDS" ]; then
    echo "⚠️  Found existing Vite server(s). Stopping..."
    echo "$VITE_PIDS" | xargs kill -9 2>/dev/null
    sleep 2
    echo "✅ Existing server(s) stopped"
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo ""
echo "Starting Vite dev server..."
echo "The frontend will be available at the URL shown below"
echo "Press Ctrl+C to stop the server"
echo ""
echo "=========================================="
echo ""

# Start the server
npm run dev

