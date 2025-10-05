# PaperSort Distribution Guide

## For Users (Installing on a Mac without Python)

### Option 1: Quick Install Script (Recommended)

1. **Install PaperSort**:
   - Download and install `PaperSort-2.0.0-arm64.dmg`
   - Drag PaperSort to Applications folder

2. **Install Dependencies** (one-time setup):
   ```bash
   # Install Homebrew (if not already installed)
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   # Install Python 3
   brew install python@3.11

   # Install Python dependencies for PaperSort
   pip3 install fastapi uvicorn pydantic aiosqlite httpx graphviz

   # Install Graphviz (for mind-map visualizations)
   brew install graphviz

   # OPTIONAL: Install Ollama (for AI-powered summaries & mind-maps)
   brew install ollama
   ollama pull llama3.2:3b
   ```

3. **Launch PaperSort** from Applications folder

### Option 2: Automated Setup Script

We've created an automated installer script. After installing the DMG:

```bash
curl -o ~/Downloads/install-papersort-deps.sh https://your-url/install-papersort-deps.sh
bash ~/Downloads/install-papersort-deps.sh
```

---

## For Developers (Building Distributable DMG)

### Current Build (Requires Python on target Mac)

```bash
npm run build
```

This creates: `dist-installer/PaperSort-2.0.0-arm64.dmg`

**Note**: Users need to install Python dependencies separately (see Option 1 above).

### Future: Fully Bundled Build (No Python Required)

To create a fully self-contained app:

1. Create a minimal Python environment:
   ```bash
   python3 -m venv backend/venv-minimal
   source backend/venv-minimal/bin/activate
   pip install fastapi uvicorn pydantic aiosqlite httpx graphviz pyinstaller
   ```

2. Bundle backend:
   ```bash
   npm run build:backend
   ```

3. Build app:
   ```bash
   npm run build
   ```

This is not yet implemented due to large Anaconda environment.

---

## What Each Component Does

- **Python 3.11+**: Runs the FastAPI backend server
- **FastAPI/Uvicorn**: Web framework for backend API
- **Graphviz**: Generates mind-map SVG visualizations
- **Ollama** (Optional): Local LLM for intelligent summaries
  - Without Ollama: Basic rule-based organization
  - With Ollama: AI-powered summaries and mind-maps

---

## Troubleshooting

### "Backend server failed to start (port 8000 in use)"
```bash
lsof -ti:8000 | xargs kill -9
```

### "Graphviz not found"
```bash
brew install graphviz
```

### "Mind-maps showing basic structure only"
Install Ollama for AI-powered analysis:
```bash
brew install ollama
ollama serve &
ollama pull llama3.2:3b
```

---

## System Requirements

- macOS 10.12+ (Apple Silicon arm64)
- 4GB RAM minimum, 8GB recommended
- 10GB free disk space (for Ollama models)
