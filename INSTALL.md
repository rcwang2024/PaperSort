# Installation Instructions

## Latest Build - Now with Virtual Environment!

The app has been rebuilt with:
- **Automatic virtual environment creation** - Isolates dependencies
- **Smart Python detection** - Finds the best Python 3.8+ installation
- **Detailed error logging** - Shows exactly what's happening
- **First-run dependency installation** - Installs packages automatically

## Installation Steps

1. **Open the DMG:**
   ```bash
   open dist-installer/PaperSort-2.0.0-arm64.dmg
   ```

2. **Drag PaperSort to Applications**

3. **Launch the app:**
   - Open from Applications folder
   - Or right-click → Open (first time only, to bypass Gatekeeper)

4. **First Launch:**
   - The app will create a virtual environment
   - It will automatically install all required packages (takes ~2-3 minutes)
   - DevTools will show progress in the Console tab
   - Once you see "Backend started successfully!", it's ready!

## What to Look For

The DevTools Console will show:
- Backend path being used
- Whether the launcher script exists
- Python version detection
- Backend startup output
- Any errors with full details

## What Happens on First Launch

You'll see these messages in the DevTools Console:

```
=========================================
PaperSort Backend Launcher
=========================================
Found suitable Python: python3.9 (version 3.9)
Python executable: /usr/bin/python3
Creating virtual environment...
Virtual environment created successfully
Installing required packages...
This may take a few minutes on first run...
[pip install output...]
Dependencies installed successfully
Starting FastAPI server...
Backend will be available at http://127.0.0.1:8000
=========================================
[Backend startup logs...]
Backend started successfully!
```

## If Backend Fails

The error dialog will show:
- Exact Python version being used
- Virtual environment creation status
- Package installation output
- Any specific errors with full details

## Prerequisites

Make sure these are installed:
- **Python 3.8+**: `python3 --version`
- **Ollama**: `ollama list` (should show available models)
- **llama3.2:3b**: `ollama pull llama3.2:3b`

## Testing Ollama

Before launching the app:
```bash
# Check Ollama is running
ollama list

# Test the model
ollama run llama3.2:3b "Hello"
```

## Manual Dependency Install

If the app says packages are missing:
```bash
cd /Applications/PaperSort.app/Contents/Resources/backend
pip3 install -r requirements.txt
```

## Reporting Issues

When reporting errors, please include:
1. Screenshot of the error dialog
2. Screenshot of the DevTools Console
3. Your Python version: `python3 --version`
4. Ollama status: `ollama list`
