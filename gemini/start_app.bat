@echo off
setlocal enabledelayedexpansion
title Pinchtab Gemini Jewelry Automation System
echo 🚀 Starting Pinchtab Gemini Jewelry Automation System (Bulletproof Mode)...

:: Change to the directory where this script is located
cd /d "%~dp0"
echo 📂 Working directory: %CD%

:: Check for Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Node.js is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b
)

:: Force cleaning ports 7861 and 9868
echo 🧹 Cleaning ports 7861 and 9868...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
timeout /t 2 >nul

:: Detect if pinchtab is installed globally
set PINCHTAB_EXEC=pinchtab
where pinchtab >nul 2>&1
if %errorlevel% neq 0 (
    echo 💡 pinchtab command not found globally, falling back to npx...
    set PINCHTAB_EXEC=npx -y pinchtab
)

echo 🔓 Disabling Pinchtab security...
call %PINCHTAB_EXEC% security down

echo 🌐 Starting Pinchtab Browser Bridge (Port 9868)...
:: Create an empty log file to avoid 'file not found' errors
echo [%DATE% %TIME%] Starting bridge... > pinchtab_bridge.log
start /b cmd /c "call %PINCHTAB_EXEC% bridge --port 9868 >> pinchtab_bridge.log 2>&1"

echo ⏳ Waiting for bridge to warm up (this may take 30-60s if using npx for the first time)...
set SUCCESS=0
:: Try for up to 60 seconds (30 iterations of 2 seconds)
for /L %%i in (1,1,30) do (
    timeout /t 2 >nul
    netstat -aon | findstr ":9868" | findstr "LISTENING" >nul
    if !errorlevel! equ 0 (
        set SUCCESS=1
        goto :BRIDGE_UP
    )
    
    :: Check if the bridge process is actually still "running" or if it crashed early
    :: (We can't easily check background process status in batch, but we can check the log)
    findstr /i "error" pinchtab_bridge.log >nul
    if !errorlevel! equ 0 (
        echo ⚠️ Potential error detected in logs...
    )
    
    echo ... checking bridge (attempt %%i/30) ...
)

:BRIDGE_UP
if !SUCCESS! equ 0 (
    echo ❌ ERROR: Pinchtab Bridge failed to start after 60 seconds.
    echo.
    echo --- BRIDGE LOGS (pinchtab_bridge.log) ---
    if exist pinchtab_bridge.log (
        type pinchtab_bridge.log
    ) else (
        echo Log file 'pinchtab_bridge.log' not found.
    )
    echo ------------------------------------------
    echo.
    echo Troubleshooting:
    echo 1. Run this manually: npx -y pinchtab bridge --port 9868
    echo 2. Check if another browser instance is conflicting.
    echo 3. Ensure you have internet access (needed for npx fallback).
    pause
    exit /b
)

echo ✅ Bridge is running!

echo 🐍 Starting Gradio Web App...
python -u pinchtab_automation.py
if %errorlevel% neq 0 (
    echo 💡 'python' command failed, trying 'py'...
    py -u pinchtab_automation.py
)

echo 🛑 Shutting down...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
pause
