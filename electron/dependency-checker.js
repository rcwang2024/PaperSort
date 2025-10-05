/**
 * Dependency Checker for PaperSort
 * Checks if all required dependencies are installed
 */

const { execSync, exec } = require('child_process');
const { dialog, shell } = require('electron');
const fs = require('fs');
const path = require('path');
const os = require('os');

class DependencyChecker {
  constructor() {
    this.results = {
      python: false,
      pip: false,
      fastapi: false,
      uvicorn: false,
      graphviz: false,
      ollama: false,
      homebrew: false
    };
    this.missing = [];
  }

  /**
   * Check if a command exists
   */
  commandExists(command) {
    try {
      execSync(`which ${command}`, { stdio: 'ignore' });
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Check if a Python package is installed
   */
  pythonPackageExists(packageName) {
    try {
      execSync(`python3 -c "import ${packageName}"`, { stdio: 'ignore' });
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Run all dependency checks
   */
  async checkAll() {
    console.log('🔍 Checking dependencies...');

    // Check Homebrew
    this.results.homebrew = this.commandExists('brew');
    if (!this.results.homebrew) {
      this.missing.push({
        name: 'Homebrew',
        required: true,
        description: 'Package manager for macOS (needed to install other dependencies)',
        install: '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
      });
    }

    // Check Python
    this.results.python = this.commandExists('python3');
    if (!this.results.python) {
      this.missing.push({
        name: 'Python 3',
        required: true,
        description: 'Python 3.11 or later',
        install: 'brew install python@3.11'
      });
    }

    // Check pip (if Python exists)
    if (this.results.python) {
      this.results.pip = this.commandExists('pip3');
    }

    // Check Python packages (if Python exists)
    if (this.results.python) {
      this.results.fastapi = this.pythonPackageExists('fastapi');
      this.results.uvicorn = this.pythonPackageExists('uvicorn');

      if (!this.results.fastapi || !this.results.uvicorn) {
        this.missing.push({
          name: 'Python Packages',
          required: true,
          description: 'FastAPI, Uvicorn, and other Python dependencies',
          install: 'pip3 install fastapi uvicorn pydantic aiosqlite httpx graphviz'
        });
      }
    }

    // Check Graphviz
    this.results.graphviz = this.commandExists('dot');
    if (!this.results.graphviz) {
      this.missing.push({
        name: 'Graphviz',
        required: true,
        description: 'Required for mind-map visualization',
        install: 'brew install graphviz'
      });
    }

    // Check Ollama (optional)
    this.results.ollama = this.commandExists('ollama');
    if (!this.results.ollama) {
      this.missing.push({
        name: 'Ollama (Optional)',
        required: false,
        description: 'AI-powered summaries and mind-maps',
        install: 'brew install ollama && ollama pull llama3.2:3b'
      });
    }

    console.log('✅ Dependency check complete:', this.results);
    console.log('Missing dependencies:', this.missing);

    return {
      allRequired: this.missing.filter(d => d.required).length === 0,
      results: this.results,
      missing: this.missing
    };
  }

  /**
   * Create automated install script
   */
  createInstallScript() {
    const scriptPath = path.join(os.tmpdir(), 'install-papersort-deps.sh');

    const scriptContent = `#!/bin/bash
set -e

echo "======================================"
echo "  PaperSort Dependency Installer"
echo "======================================"
echo ""

# Install Homebrew if needed
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add to PATH
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✅ Homebrew already installed"
fi

# Install Python
if ! command -v python3 &> /dev/null; then
    echo "🐍 Installing Python 3.11..."
    brew install python@3.11
else
    echo "✅ Python already installed"
fi

# Install Python packages
echo "📚 Installing Python packages..."
pip3 install --quiet fastapi uvicorn pydantic aiosqlite httpx graphviz

# Install Graphviz
if ! command -v dot &> /dev/null; then
    echo "🎨 Installing Graphviz..."
    brew install graphviz
else
    echo "✅ Graphviz already installed"
fi

echo ""
echo "======================================"
echo "  ✅ Installation Complete!"
echo "======================================"
echo ""
echo "You can now restart PaperSort."
echo ""

# Optional: Install Ollama
echo "Optional: Install Ollama for AI features?"
read -p "Install Ollama? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    brew install ollama
    brew services start ollama
    sleep 3
    ollama pull llama3.2:3b
    echo "✅ Ollama installed!"
fi

read -p "Press Enter to close..."
`;

    fs.writeFileSync(scriptPath, scriptContent, { mode: 0o755 });
    return scriptPath;
  }

  /**
   * Show dependency installation dialog
   */
  async showInstallDialog(mainWindow) {
    const requiredMissing = this.missing.filter(d => d.required);
    const optionalMissing = this.missing.filter(d => !d.required);

    if (requiredMissing.length === 0 && optionalMissing.length === 0) {
      return { action: 'continue' };
    }

    // Create message
    let message = 'PaperSort needs some dependencies to run.\n\n';

    if (requiredMissing.length > 0) {
      message += '⚠️  Required:\n';
      requiredMissing.forEach(dep => {
        message += `  • ${dep.name}: ${dep.description}\n`;
      });
      message += '\n';
    }

    if (optionalMissing.length > 0) {
      message += '💡 Optional (recommended):\n';
      optionalMissing.forEach(dep => {
        message += `  • ${dep.name}: ${dep.description}\n`;
      });
    }

    // Show dialog with options
    const response = await dialog.showMessageBox(mainWindow, {
      type: 'warning',
      title: 'Dependencies Required',
      message: 'PaperSort Setup Required',
      detail: message,
      buttons: ['Auto Install', 'Manual Instructions', 'Quit'],
      defaultId: 0,
      cancelId: 2
    });

    if (response.response === 0) {
      // Auto install
      return await this.autoInstall(mainWindow);
    } else if (response.response === 1) {
      // Show manual instructions
      return await this.showManualInstructions(mainWindow);
    } else {
      // Quit
      return { action: 'quit' };
    }
  }

  /**
   * Auto install dependencies
   */
  async autoInstall(mainWindow) {
    const scriptPath = this.createInstallScript();

    dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Installing Dependencies',
      message: 'Opening Terminal to install dependencies...',
      detail: 'A Terminal window will open. Please follow the prompts.\n\nThis is a one-time setup and will take about 5 minutes.\n\nYou may be asked for your password to install Homebrew.',
      buttons: ['OK']
    });

    // Open Terminal with the script
    exec(`open -a Terminal.app "${scriptPath}"`);

    // Ask user to restart when done
    const restartResponse = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Installation Started',
      message: 'Dependencies are being installed in Terminal',
      detail: 'Once the installation completes:\n1. Close the Terminal window\n2. Click "Restart PaperSort" below',
      buttons: ['Restart PaperSort', 'I\'ll Restart Later'],
      defaultId: 0
    });

    if (restartResponse.response === 0) {
      return { action: 'restart' };
    } else {
      return { action: 'quit' };
    }
  }

  /**
   * Show manual installation instructions
   */
  async showManualInstructions(mainWindow) {
    let instructions = 'Open Terminal and run these commands:\n\n';

    this.missing.filter(d => d.required).forEach(dep => {
      instructions += `# Install ${dep.name}\n${dep.install}\n\n`;
    });

    instructions += '\nAfter installation, restart PaperSort.';

    const response = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Installation Instructions',
      message: 'Manual Installation',
      detail: instructions,
      buttons: ['Copy Commands', 'Open Terminal', 'Close'],
      defaultId: 0
    });

    if (response.response === 0) {
      // Copy to clipboard
      const { clipboard } = require('electron');
      const commands = this.missing
        .filter(d => d.required)
        .map(d => d.install)
        .join('\n');
      clipboard.writeText(commands);

      dialog.showMessageBox(mainWindow, {
        type: 'info',
        message: 'Commands copied to clipboard!',
        detail: 'Paste them into Terminal to install.',
        buttons: ['OK']
      });
    } else if (response.response === 1) {
      // Open Terminal
      exec('open -a Terminal.app');
    }

    return { action: 'quit' };
  }
}

module.exports = DependencyChecker;
