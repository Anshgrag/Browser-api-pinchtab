@echo off
setlocal enabledelayedexpansion
title 💍 Pinchtab Gemini Bulletproof Setup (Windows)

:: ======================================================================
::  PHASE 1: INITIALIZATION
:: ======================================================================
echo 🚀 PHASE 1: Initializing environment...
cd /d "%~dp0"
echo 📂 Working directory: %CD%

:: Check for Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Node.js not found. Please install it from nodejs.org
    pause
    exit /b
)

:: Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ ERROR: Python not found. Please install Python 3.10+
        pause
        exit /b
    )
)

:: ======================================================================
::  PHASE 2: CLEANUP
:: ======================================================================
echo 🧹 PHASE 2: Cleaning up previous sessions...
:: Kill any existing processes on relevant ports
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
ping -n 2 127.0.0.1 >nul

:: ======================================================================
::  PHASE 3: PINCHTAB SETUP
:: ======================================================================
echo 🔓 PHASE 3: Setting up Pinchtab...

:: Check if pinchtab is installed, otherwise use npx
set "PINCHTAB_CMD=pinchtab"
where pinchtab >nul 2>&1
if %errorlevel% neq 0 (
    echo 💡 pinchtab not found globally, using npx...
    set "PINCHTAB_CMD=npx -y pinchtab"
)

echo 🔑 Disabling Pinchtab security (so no token is needed)...
call %PINCHTAB_CMD% security down
if %errorlevel% neq 0 (
    echo ⚠️ WARNING: Security down failed. Attempting to continue anyway.
)

:: ======================================================================
::  PHASE 4: BRIDGE STARTUP
:: ======================================================================
echo 🌐 PHASE 4: Starting Browser Bridge...
set "LOG_FILE=%~dp0pinchtab_bridge.log"
echo Starting bridge... > "%LOG_FILE%"

:: Start the bridge in the background
start /b cmd /c "call %PINCHTAB_CMD% bridge --port 9868 >> "%LOG_FILE%" 2>&1"

echo ⏳ Waiting for bridge to warm up...
set "READY=0"
for /L %%i in (1,1,15) do (
    ping -n 3 127.0.0.1 >nul
    netstat -aon | findstr ":9868" | findstr "LISTENING" >nul
    if !errorlevel! equ 0 (
        set "READY=1"
        goto :BRIDGE_READY
    )
    echo ... checking (attempt %%i/15) ...
)

:BRIDGE_READY
if "%READY%"=="0" (
    echo ❌ ERROR: Bridge failed to start. See %LOG_FILE% for details.
    pause
    exit /b
)
echo ✅ Bridge is online!

:: ======================================================================
::  PHASE 5: CREDENTIALS & LOGIN
:: ======================================================================
echo 👤 PHASE 5: Browser Authentication
echo.
echo ⚠️  IMPORTANT: For automation to work, you MUST be logged in to Gemini.
echo 1. A Chrome window will open shortly.
echo 2. If you are NOT logged in to Google/Gemini, please LOG IN MANUALLY.
echo 3. Once you see the Gemini chat interface, come back here.
echo.
echo 🚀 Opening Gemini for verification...
:: We can use pinchtab to navigate to Gemini to trigger the window
call %PINCHTAB_CMD% navigate "https://gemini.google.com/app" --port 9868
echo.
echo 🕒 Waiting for you to verify/login... (Press any key once you are at the Gemini chat screen)
pause

:: ======================================================================
::  PHASE 6: START AUTOMATION
:: ======================================================================
echo 🐍 PHASE 6: Launching Gradio UI...
set "PYTHON_CMD=python"
where python >nul 2>&1
if %errorlevel% neq 0 set "PYTHON_CMD=py"

%PYTHON_CMD% -u pinchtab_automation.py

echo.
echo 🛑 Shutting down...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
pause
