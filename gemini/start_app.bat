@echo off
title Pinchtab Gemini Jewelry Automation System
echo 🚀 Starting Pinchtab Gemini Jewelry Automation System (Clean Slate Mode)...

echo 🧹 Force cleaning ports 7861 and 9868...
:: Kill any process on 7861 (Gradio)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
:: Kill any process on 9868 (Bridge)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
timeout /t 2 >nul

echo 🔓 Disabling Pinchtab security for local session...
:: This prevents 401 Unauthorized errors by allowing local requests without a token
cmd /c pinchtab security down >nul 2>&1

echo 🌐 Starting Pinchtab Browser Bridge (Port 9868)...
:: Start the bridge with -y (guards down) just to be safe
start /b cmd /c pinchtab bridge --port 9868 -y > pinchtab_bridge.log 2>&1

echo ⏳ Waiting for bridge to warm up...
timeout /t 8 >nul

:: Final check if bridge is alive
netstat -aon | findstr ":9868" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo ❌ ERROR: Pinchtab Bridge failed to start.
    echo 📖 Please check 'pinchtab_bridge.log' for details.
    pause
    exit /b
)

echo ✅ Bridge is running!

echo 🐍 Starting Gradio Web App...
python -u pinchtab_automation.py

echo 🛑 Shutting down...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
pause
