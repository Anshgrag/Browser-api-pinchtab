#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "🚀 Starting Pinchtab Gemini Jewelry Automation System..."

# Function to kill processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down processes..."
    # Kill the Gradio server (python) and Pinchtab bridge
    PIDS_GRADIO=$(lsof -t -i :7861)
    if [ ! -z "$PIDS_GRADIO" ]; then
        echo "Stopping Gradio server (PID: $PIDS_GRADIO)..."
        kill $PIDS_GRADIO 2>/dev/null
    fi
    PIDS_BRIDGE=$(lsof -t -i :9868)
    if [ ! -z "$PIDS_BRIDGE" ]; then
        echo "Stopping Pinchtab Bridge (PID: $PIDS_BRIDGE)..."
        kill $PIDS_BRIDGE 2>/dev/null
    fi
    echo "✅ Done. Have a great day!"
    exit
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# 1. Clear ports if already occupied
echo "🧹 Force cleaning previous sessions (Ports 7861, 9868)..."
PIDS_GRADIO=$(lsof -t -i :7861)
if [ ! -z "$PIDS_GRADIO" ]; then
    kill -9 $PIDS_GRADIO 2>/dev/null
fi
PIDS_BRIDGE=$(lsof -t -i :9868)
if [ ! -z "$PIDS_BRIDGE" ]; then
    kill -9 $PIDS_BRIDGE 2>/dev/null
fi
sleep 2

echo "🔓 Disabling Pinchtab security for local session..."
pinchtab security down >/dev/null 2>&1

# 2. Start Pinchtab Bridge on port 9868
echo "🌐 Starting Pinchtab Browser Bridge (Port 9868)..."
pinchtab bridge --port 9868 > pinchtab_bridge.log 2>&1 &
sleep 5

# Check if bridge started successfully
if ! lsof -i :9868 > /dev/null; then
    # Fallback to absolute binary path if needed
    /Users/applem1pro/.local/state/fnm_multishells/83177_1779390468267/bin/pinchtab bridge --port 9868 > pinchtab_bridge.log 2>&1 &
    sleep 5
fi

if ! lsof -i :9868 > /dev/null; then
    echo "❌ ERROR: Pinchtab bridge failed to start. Check pinchtab_bridge.log."
    exit 1
fi

echo "✅ Bridge is running!"

# 3. Start python automation script
echo "🐍 Starting Gradio Web App..."
python3 -u pinchtab_automation.py

# Final cleanup if exited normally
cleanup
