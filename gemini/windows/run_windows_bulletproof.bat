@echo off
setlocal enabledelayedexpansion
title 💍 Pinchtab Gemini Bulletproof Setup (Windows)

:: ======================================================================
::  PHASE 0: ENVIRONMENT DIAGNOSTIC
:: ======================================================================
echo 🔍 PHASE 0: Environment Diagnostic...

:: Check for Chrome in common locations
set "CHROME_FOUND=0"
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME_FOUND=1"
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME_FOUND=1"
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME_FOUND=1"

if "%CHROME_FOUND%"=="0" (
    echo ⚠️ WARNING: Could not find Google Chrome in standard locations.
    echo Automation might fail if Chrome is not in your PATH.
) else (
    echo ✅ Google Chrome found.
)

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

:: Simplified port cleaning (Flat commands, no loops)
echo   - Checking Port 7861...
netstat -ano | findstr ":7861" | findstr "LISTENING" > port_7861.tmp
if %errorlevel% equ 0 (
    for /f "tokens=5" %%a in (port_7861.tmp) do (
        echo     🔪 Killing process %%a on 7861
        taskkill /F /PID %%a 2>nul
    )
)
del port_7861.tmp 2>nul

echo   - Checking Port 9868...
netstat -ano | findstr ":9868" | findstr "LISTENING" > port_9868.tmp
if %errorlevel% equ 0 (
    for /f "tokens=5" %%a in (port_9868.tmp) do (
        echo     🔪 Killing process %%a on 9868
        taskkill /F /PID %%a 2>nul
    )
)
del port_9868.tmp 2>nul

ping -n 2 127.0.0.1 >nul

:: ======================================================================
::  PHASE 3: PINCHTAB SETUP
:: ======================================================================
echo 🔓 PHASE 3: Setting up Pinchtab...

set "PINCHTAB_CMD=pinchtab"
where pinchtab >nul 2>&1
if %errorlevel% neq 0 (
    echo 💡 pinchtab not found globally, using npx...
    set "PINCHTAB_CMD=npx -y pinchtab"
)

echo 🔑 Disabling Pinchtab security...
call %PINCHTAB_CMD% security down
if %errorlevel% neq 0 echo ⚠️ Warning: Security down failed, continuing...

:: ======================================================================
::  PHASE 4: BRIDGE STARTUP
:: ======================================================================
echo 🌐 PHASE 4: Starting Browser Bridge...
set "LOG_FILE=%~dp0pinchtab_bridge.log"
echo [%DATE% %TIME%] Starting bridge... > "%LOG_FILE%"

:: Start the bridge in a NEW VISIBLE WINDOW for better reliability and visibility
echo   - Launching bridge in a separate terminal...
start "Pinchtab Bridge Server" cmd /c "call %PINCHTAB_CMD% bridge --port 9868"

echo ⏳ Waiting for bridge to warm up...
set /a "counter=1"

:BRIDGE_CHECK_LOOP
ping -n 3 127.0.0.1 >nul
echo ... checking (attempt %counter%/15) ...

netstat -ano | findstr ":9868" | findstr "LISTENING" >nul
if %errorlevel% equ 0 goto :BRIDGE_READY

set /a "counter+=1"
if %counter% leq 15 goto :BRIDGE_CHECK_LOOP

:BRIDGE_FAIL
echo ❌ ERROR: Bridge failed to start after 45 seconds.
echo 💡 Check the separate "Pinchtab Bridge Server" window for errors.
pause
exit /b

:BRIDGE_READY
echo ✅ Bridge is online!

:: ======================================================================
::  PHASE 5: CREDENTIALS & LOGIN
:: ======================================================================
echo 👤 PHASE 5: Browser Authentication
echo.
echo ⚠️  IMPORTANT: For automation to work, you MUST be logged in to Gemini.
echo 1. A Chrome window should open automatically to Gemini.
echo 2. If it DOES NOT open, please open your browser to:
echo    https://gemini.google.com/app
echo.
echo 🚀 Attempting to open Gemini via Bridge API...
ping -n 5 127.0.0.1 >nul

:: Use curl to talk directly to the bridge API (more reliable than CLI flags)
curl -X POST http://localhost:9868/navigate -H "Content-Type: application/json" -d "{\"url\":\"https://gemini.google.com/app\",\"newTab\":true}" >nul 2>&1

if %errorlevel% neq 0 (
    echo ⚠️  API Navigation failed. Trying CLI fallback...
    call %PINCHTAB_CMD% navigate "https://gemini.google.com/app"
)

echo.
echo 🕒 Waiting for you to verify/login...
echo (Press any key once you are at the Gemini chat screen)
pause

:: ======================================================================
::  PHASE 6: START AUTOMATION
:: ======================================================================
echo 🐍 PHASE 6: Launching Gradio UI...
set "PYTHON_CMD=python"
where python >nul 2>&1
if %errorlevel% neq 0 set "PYTHON_CMD=py"

echo 🎨 Starting Gradio (Port 7861)...
%PYTHON_CMD% -u pinchtab_automation.py

echo.
echo 🛑 Shutting down...
:: Final cleanup
netstat -ano | findstr ":7861" | findstr "LISTENING" > port_7861.tmp
for /f "tokens=5" %%a in (port_7861.tmp) do taskkill /F /PID %%a 2>nul
netstat -ano | findstr ":9868" | findstr "LISTENING" > port_9868.tmp
for /f "tokens=5" %%a in (port_9868.tmp) do taskkill /F /PID %%a 2>nul
del *.tmp 2>nul
pause
