@echo off
setlocal enabledelayedexpansion
title Pinchtab Gemini Jewelry Automation System
echo 🚀 Starting Pinchtab Gemini Jewelry Automation System (Bulletproof Mode)...

:: Change to the directory where this script is located
echo 📂 Navigating to script directory...
cd /d "%~dp0"
if %errorlevel% neq 0 (
    echo ❌ ERROR: Failed to change directory to "%~dp0"
    pause
    exit /b
)
echo 📂 Working directory: %CD%

:: Check for Node.js
echo 🔍 Checking for Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Node.js is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b
)

:: Force cleaning ports 7861 and 9868
echo 🧹 Cleaning ports 7861 and 9868...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do (
    echo 🔪 Killing process on 7861 (PID %%a)...
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do (
    echo 🔪 Killing process on 9868 (PID %%a)...
    taskkill /F /PID %%a 2>nul
)

:: Replacing timeout /t 2 >nul with ping for better portability
echo ⏳ Cooling down...
ping -n 3 127.0.0.1 >nul

:: Detect if pinchtab is installed globally
set "PINCHTAB_EXEC=pinchtab"
where pinchtab >nul 2>&1
if %errorlevel% neq 0 (
    echo 💡 pinchtab command not found globally, falling back to npx...
    set "PINCHTAB_EXEC=npx -y pinchtab"
)

echo 🔓 Disabling Pinchtab security...
call %PINCHTAB_EXEC% security down
if %errorlevel% neq 0 echo ⚠️ Warning: Security down command failed, continuing...

echo 🌐 Starting Pinchtab Browser Bridge (Port 9868)...
:: Create an empty log file with absolute path to avoid 'file not found' errors
set "LOG_FILE=%~dp0pinchtab_bridge.log"
echo [%DATE% %TIME%] Starting bridge... > "%LOG_FILE%"
if %errorlevel% neq 0 (
    echo ⚠️ WARNING: Could not create log file at "%LOG_FILE%"
)

echo 🚀 Launching bridge process in background...
:: Use double quotes for the command string to be safe
start /b cmd /c "call %PINCHTAB_EXEC% bridge --port 9868 >> "%LOG_FILE%" 2>&1"

echo ⏳ Waiting for bridge to warm up (this may take 30-60s if using npx for the first time)...
set SUCCESS=0
:: Try for up to 60 seconds (30 iterations of ~2 seconds)
for /L %%i in (1,1,30) do (
    :: Replacing timeout with ping for delay
    ping -n 3 127.0.0.1 >nul
    
    echo ... checking bridge (attempt %%i/30) ...
    netstat -aon | findstr ":9868" | findstr "LISTENING" >nul
    if !errorlevel! equ 0 (
        set SUCCESS=1
        goto :BRIDGE_UP
    )
    
    :: Check if the bridge process recorded any errors
    if exist "%LOG_FILE%" (
        findstr /i "error" "%LOG_FILE%" >nul
        if !errorlevel! equ 0 (
            echo ⚠️ Potential error detected in bridge logs...
        )
    )
)

:BRIDGE_UP
if !SUCCESS! equ 0 (
    echo ❌ ERROR: Pinchtab Bridge failed to start after 60 seconds.
    echo.
    echo --- BRIDGE LOGS ("%LOG_FILE%") ---
    if exist "%LOG_FILE%" (
        type "%LOG_FILE%"
    ) else (
        echo Log file not found.
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

:: Check for Python
echo 🔍 Checking for Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ ERROR: Python or 'py' launcher not found.
        pause
        exit /b
    )
)

echo 🐍 Starting Gradio Web App...
set "SCRIPT_FILE=%~dp0pinchtab_automation.py"
python -u "%SCRIPT_FILE%"
if %errorlevel% neq 0 (
    echo 💡 'python' command failed, trying 'py'...
    py -u "%SCRIPT_FILE%"
)

echo 🛑 Shutting down...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
echo 👋 Done.
pause
