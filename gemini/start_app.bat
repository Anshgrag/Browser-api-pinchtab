@echo off
title Pinchtab Gemini Jewelry Automation System
echo 🚀 Starting Pinchtab Gemini Jewelry Automation System...

echo 🧹 Cleaning up any previous server sessions on ports 7861 and 9868...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul

echo 🌐 Starting Pinchtab Browser Bridge (Port 9868)...
:: Use cmd /c to ensure npm-installed pinchtab is found correctly
start /b cmd /c pinchtab bridge --port 9868 > pinchtab_bridge.log 2>&1

:: Give it time to initialize
echo ⏳ Waiting for bridge to initialize...
timeout /t 8 >nul

:: Check if port 9868 is actually listening
netstat -aon | findstr ":9868" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo ❌ ERROR: Pinchtab Bridge failed to start on port 9868.
    echo 📖 Check 'pinchtab_bridge.log' for the error message.
    echo 💡 Tip: Try running 'pinchtab bridge --port 9868' manually in a new CMD window to see what happens.
    pause
    exit /b
)

echo ✅ Bridge is running!

echo 🔑 Retrieving Pinchtab security token...
for /f "tokens=2" %%a in ('cmd /c pinchtab config show ^| findstr "Token:"') do set PINCHTAB_TOKEN=%%a

if "%PINCHTAB_TOKEN%"=="" (
    echo ⚠️ Could not find token. 
    echo ⚠️ If you get 401 errors, run 'pinchtab security down' once.
) else (
    echo ✅ Token loaded!
)

echo 🐍 Starting Gradio Web App...
python -u pinchtab_automation.py

echo 🛑 Shutting down...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9868" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
pause
