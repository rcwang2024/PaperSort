# PaperSort - Quick Start Guide

Welcome to **PaperSort v2.0**! 🎉

An AI-powered tool to organize your research papers and generate insightful mind-maps.

---

## First Time Setup (5 minutes)

### Step 1: Install PaperSort
1. Open `PaperSort-2.0.0-arm64.dmg`
2. Drag **PaperSort** to your **Applications** folder
3. Close the installer window

### Step 2: Install Dependencies

**Option A - Automated (Recommended)**:
```bash
curl -o ~/Downloads/install-papersort.sh https://raw.githubusercontent.com/rcwang2024/PaperSort/main/install-dependencies.sh
bash ~/Downloads/install-papersort.sh
```

**Option B - Manual**:
Open Terminal and run:
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 graphviz
pip3 install fastapi uvicorn pydantic aiosqlite httpx graphviz

# Optional: AI features
brew install ollama
ollama pull llama3.2:3b
```

### Step 3: Launch!
Open **PaperSort** from your Applications folder.

---

## Features

### 📁 Smart Organization
- Automatically categorize papers by topic
- Uses AI to understand paper content
- Creates organized folder structure

### 🧠 Mind-Maps
- Visual representation of paper structure
- Shows methodology, contributions, results
- AI-generated insights (with Ollama)

### 📝 Intelligent Summaries
- Comprehensive paper analysis
- Explains WHY and HOW, not just WHAT
- Highlights key contributions and findings

---

## Usage

1. **Organize Papers**:
   - Click "Choose Folder" and select your papers folder
   - PaperSort will analyze and organize them by topic
   - Check "Copy Mode" to keep originals intact

2. **View Mind-Maps**:
   - Click the 🧠 icon next to any paper
   - Interactive visualization of paper structure
   - AI-generated summary with insights

---

## Troubleshooting

### App won't start / Backend error
```bash
# Kill any stuck processes
lsof -ti:8000 | xargs kill -9

# Restart the app
```

### Mind-maps not showing
Make sure Graphviz is installed:
```bash
brew install graphviz
```

### Want AI-powered summaries?
Install Ollama:
```bash
brew install ollama
brew services start ollama
ollama pull llama3.2:3b
```

---

## System Requirements

- **macOS**: 10.12 or later (Apple Silicon)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 10GB free space (for AI models)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/rcwang2024/PaperSort/issues)
- **Documentation**: See `DISTRIBUTION.md` for advanced setup

---

**Happy researching!** 📚✨
