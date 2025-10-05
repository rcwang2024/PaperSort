#!/bin/bash

# PaperSort Dependency Installer
# Installs all required dependencies for PaperSort to run

set -e

echo "========================================"
echo "   PaperSort Dependency Installer"
echo "========================================"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is for macOS only"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Install Homebrew if needed
echo "📦 Checking for Homebrew..."
if ! command_exists brew; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✅ Homebrew already installed"
fi

# 2. Install Python 3.11 if needed
echo ""
echo "🐍 Checking for Python 3..."
if ! command_exists python3; then
    echo "Installing Python 3.11..."
    brew install python@3.11
else
    python_version=$(python3 --version | cut -d' ' -f2)
    echo "✅ Python $python_version already installed"
fi

# 3. Install Python packages
echo ""
echo "📚 Installing Python packages..."
pip3 install --upgrade pip
pip3 install fastapi uvicorn pydantic aiosqlite httpx graphviz

# 4. Install Graphviz
echo ""
echo "🎨 Installing Graphviz..."
if ! command_exists dot; then
    brew install graphviz
    echo "✅ Graphviz installed"
else
    echo "✅ Graphviz already installed"
fi

# 5. Optional: Install Ollama
echo ""
echo "🤖 Ollama (AI Features - Optional)"
read -p "Install Ollama for AI-powered summaries? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if ! command_exists ollama; then
        echo "Installing Ollama..."
        brew install ollama

        # Start Ollama service
        brew services start ollama
        sleep 3

        # Pull the model
        echo "Downloading llama3.2:3b model (this may take a few minutes)..."
        ollama pull llama3.2:3b

        echo "✅ Ollama installed and model downloaded"
    else
        echo "✅ Ollama already installed"

        # Check if model exists
        if ! ollama list | grep -q "llama3.2:3b"; then
            echo "Downloading llama3.2:3b model..."
            ollama pull llama3.2:3b
        fi
    fi
else
    echo "⏭️  Skipping Ollama (you can install it later with: brew install ollama)"
fi

echo ""
echo "========================================"
echo "   ✅ Installation Complete!"
echo "========================================"
echo ""
echo "You can now launch PaperSort from your Applications folder."
echo ""
echo "Optional next steps:"
echo "  • To enable AI features, make sure Ollama is running:"
echo "    $ brew services start ollama"
echo ""
echo "Happy organizing! 📚"
