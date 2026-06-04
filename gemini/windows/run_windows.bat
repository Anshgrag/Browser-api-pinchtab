@echo off
setlocal enabledelayedexpansion
title Pinchtab Gemini Jewelry Automation System

echo 🔍 STEP 1: Starting...
pause

:: Change to the directory where this script is located
echo 📂 STEP 2: Navigating to script directory...
cd /d "%~dp0"
echo Working directory is: %CD%
pause

:: Check for Node.js
echo 🔍 STEP 3: Checking for Node.js...
where node
if %errorlevel% neq 0 (
    echo ❌ ERROR: Node.js not found.
    pause
    exit /b
)
pause

:: Force cleaning ports (Simplified)
echo 🧹 STEP 4: Cleaning ports...
echo Checking 7861...
netstat -ano | findstr :7861
echo Checking 9868...
netstat -ano | findstr :9868
pause

:: Detect pinchtab
echo 🔍 STEP 5: Checking pinchtab...
set "PINCHTAB_EXEC=pinchtab"
where pinchtab >nul 2>&1
if %errorlevel% neq 0 (
    echo Falling back to npx...
    set "PINCHTAB_EXEC=npx -y pinchtab"
)
echo PINCHTAB_EXEC is: %PINCHTAB_EXEC%
pause

echo 🔓 STEP 6: Security down...
call %PINCHTAB_EXEC% security down
pause

echo 🌐 STEP 7: Starting bridge...
set "LOG_FILE=%~dp0pinchtab_bridge.log"
echo Starting bridge... > "%LOG_FILE%"
start /b cmd /c "call %PINCHTAB_EXEC% bridge --port 9868 >> "%LOG_FILE%" 2>&1"
pause

echo ✅ If you reached here, the bridge is starting in background.
echo 🐍 STEP 8: Starting Python...
set "SCRIPT_FILE=%~dp0pinchtab_automation.py"
python -u "%SCRIPT_FILE%"
if %errorlevel% neq 0 (
    echo 💡 trying 'py'...
    py -u "%SCRIPT_FILE%"
)
pause
