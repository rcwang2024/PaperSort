#!/bin/bash

# Script to run the PaperSort backend
# This script is used by the Electron app to start the backend server

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "========================================="
echo "PaperSort Backend Launcher"
echo "Script directory: $SCRIPT_DIR"
echo "========================================="

# Find the best Python installation
PYTHON_CMD=""

# First, try to find Anaconda/Conda Python (usually more complete)
ANACONDA_PATHS=(
    "$HOME/anaconda3/bin/python"
    "$HOME/anaconda/bin/python"
    "$HOME/opt/anaconda3/bin/python"
    "$HOME/miniconda3/bin/python"
    "/usr/local/anaconda3/bin/python"
    "/opt/anaconda3/bin/python"
)

echo "Searching for Python installations..."
for anaconda_py in "${ANACONDA_PATHS[@]}"; do
    if [ -f "$anaconda_py" ]; then
        VERSION=$($anaconda_py -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}")' 2>/dev/null || echo "0.0")
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)

        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 8 ]; then
            PYTHON_CMD=$anaconda_py
            echo "Found Anaconda Python: $anaconda_py (version $VERSION)"
            break
        fi
    fi
done

# If no Anaconda Python found, search for version-specific commands
if [ -z "$PYTHON_CMD" ]; then
    for py in python3.13 python3.12 python3.11 python3.10 python3.9 python3.8 python3 python; do
        if command -v $py &> /dev/null; then
            # Check if it's actually Python 3.8+
            VERSION=$($py -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}")' 2>/dev/null || echo "0.0")
            MAJOR=$(echo $VERSION | cut -d. -f1)
            MINOR=$(echo $VERSION | cut -d. -f2)

            if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 8 ]; then
                PYTHON_CMD=$py
                echo "Found system Python: $py (version $VERSION)"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3.8 or higher is required but not found"
    echo "Please install Python 3.8+ from https://www.python.org/downloads/"
    exit 1
fi

# Get full Python info
echo "Python executable: $(which $PYTHON_CMD)"
$PYTHON_CMD --version
echo ""

# Check if this is an Anaconda/Conda installation
IS_ANACONDA=0
if [[ "$PYTHON_CMD" == *"anaconda"* ]] || [[ "$PYTHON_CMD" == *"conda"* ]]; then
    IS_ANACONDA=1
    echo "✓ Detected Anaconda/Conda Python installation"
    echo "  Skipping venv creation (using Anaconda environment directly)"
    echo ""
fi

# Only create venv for system Python installations
if [ $IS_ANACONDA -eq 0 ]; then
    VENV_DIR="$SCRIPT_DIR/.venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        CREATE_STATUS=$?
        if [ $CREATE_STATUS -ne 0 ]; then
            echo "WARNING: Failed to create virtual environment (exit code: $CREATE_STATUS)"
            echo "Will try to use system Python directly..."
        else
            echo "Virtual environment created successfully"
        fi
    fi

    # Activate virtual environment if it exists
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        echo "Activating virtual environment..."
        source "$VENV_DIR/bin/activate"
        PYTHON_CMD="$VENV_DIR/bin/python"
        echo "Using virtual environment: $VENV_DIR"
        echo ""
    else
        echo "Using system Python (no venv)"
        echo ""
    fi
else
    echo "Using Anaconda Python: $PYTHON_CMD"
    echo ""
fi

# Check if required packages are installed
echo ""
echo "Checking dependencies..."
$PYTHON_CMD -c "import fastapi, uvicorn" 2>/dev/null
DEPS_CHECK=$?

if [ $DEPS_CHECK -ne 0 ]; then
    echo "Dependencies not found. Installing..."
    echo "This may take a few minutes on first run..."
    echo ""

    # Upgrade pip first
    echo "Upgrading pip..."
    $PYTHON_CMD -m pip install --upgrade pip
    PIP_UPGRADE=$?
    if [ $PIP_UPGRADE -ne 0 ]; then
        echo "WARNING: pip upgrade failed, continuing anyway..."
    fi

    # Install requirements
    echo "Installing requirements..."
    $PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt"
    INSTALL_STATUS=$?

    if [ $INSTALL_STATUS -ne 0 ]; then
        echo ""
        echo "ERROR: Failed to install dependencies (exit code: $INSTALL_STATUS)"
        echo "Requirements file: $SCRIPT_DIR/requirements.txt"
        echo ""
        echo "Please try manually:"
        echo "  cd $SCRIPT_DIR"
        echo "  $PYTHON_CMD -m pip install -r requirements.txt"
        exit 1
    fi

    echo ""
    echo "Dependencies installed successfully!"
else
    echo "All dependencies are installed ✓"
fi

# Verify dependencies one more time
echo ""
echo "Verifying installation..."
$PYTHON_CMD -c "import fastapi, uvicorn, pydantic, sqlalchemy" 2>&1
VERIFY_STATUS=$?

if [ $VERIFY_STATUS -ne 0 ]; then
    echo "ERROR: Dependency verification failed!"
    echo "Some packages may not have installed correctly."
    exit 1
fi

echo "Verification passed ✓"

# Start the backend server
echo ""
echo "Starting FastAPI server..."
echo "Backend will be available at http://127.0.0.1:8000"
echo "========================================="
echo ""

cd "$SCRIPT_DIR"
exec $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 8000
