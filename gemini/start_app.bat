@echo off
title Pinchtab Gemini Jewelry Automation System
echo 🚀 Starting Pinchtab Gemini Jewelry Automation System...

echo 🧹 Cleaning up any previous server sessions on ports 7861 and 9868...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul

echo 🌐 Starting Pinchtab Browser Bridge (Port 9868)...
start /b pinchtab bridge --port 9868 > pinchtab_bridge.log 2>&1
timeout /t 5 >nul

echo 🐍 Starting Gradio Web App...
python -u pinchtab_automation.py

echo 🛑 Shutting down...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
pause
