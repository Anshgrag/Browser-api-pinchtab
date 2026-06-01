========================================================================
💍 GEMINI JEWELRY AUTOMATION - CLIENT SETUP & RUN GUIDE 💍
========================================================================

This system automates gemstone replacement in ring designs using your 
browser, avoiding expensive developers' API keys.

------------------------------------------------------------------------
STEP 1: INSTALL PRE-REQUISITES (ONE-TIME SETUP)
------------------------------------------------------------------------

--- FOR MAC USERS ---
1. Install Google Chrome: https://www.google.com/chrome/
2. Open Terminal and run this command to install Homebrew:
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
3. Install Python, Node.js, and Pinchtab:
   brew install python node
   pip3 install gradio pillow requests
   npm install -g pinchtab

--- FOR WINDOWS USERS ---
1. Install Google Chrome: https://www.google.com/chrome/
2. Install Python 3.12 (Check the box "Add Python to PATH" during setup):
   https://www.python.org/downloads/
3. Install Node.js (LTS version):
   https://nodejs.org/
4. Open Command Prompt (Cmd) as Administrator and install dependencies:
   pip install gradio pillow requests
   npm install -g pinchtab

------------------------------------------------------------------------
STEP 2: GOOGLE GEMINI SIGN-IN (ONE-TIME SETUP)
------------------------------------------------------------------------
Because this automation runs inside the standard Gemini web interface, 
you must log in to your Google Account once so your session is saved:

1. Open Terminal (Mac) or Command Prompt (Windows) and run:
   
   pinchtab open "https://gemini.google.com/app"

2. A special Google Chrome window will open. Log into your Google account 
   that has access to Gemini.
3. Once logged in, close the browser window. The system will remember 
   your account session from now on!

------------------------------------------------------------------------
STEP 3: RUNNING THE APPLICATION
------------------------------------------------------------------------
The system is now split into two optimized versions:

--- FOR WINDOWS USERS ---
1. Open the folder: `gemini/windows/`
2. Double-click `run_windows.bat`.
   (This version is optimized for Windows PATH and security settings)

--- FOR MAC USERS ---
1. Open the folder: `gemini/mac/`
2. Double-click `run_mac.command`.
   (This version is optimized for Mac's Unix-based bridge handling)

--- FOR BOTH ---
3. Open your browser and navigate to the printed links:
   - Local Link:  http://127.0.0.1:7861
   - Public Link: https://50eca349adc0ca6b59.gradio.live
   
   (Note: The public link can be opened on your iPad or phone to run
   generations remotely!)

------------------------------------------------------------------------
STEP 4: SHUTTING DOWN
------------------------------------------------------------------------
- To shut down the servers, simply press "Ctrl + C" inside the Terminal/
  Cmd window or close it. It will clean up all background processes 
  automatically.

========================================================================
✨ Enjoy your automated gemstone designer! ✨
========================================================================
