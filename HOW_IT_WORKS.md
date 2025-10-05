# How PaperSort Distribution Works

## The Smart Dependency System

PaperSort now has an **intelligent dependency checker** that runs automatically on first launch!

---

## User Experience Flow

### 1. User Downloads DMG
- Single file: `PaperSort-2.0.0-arm64.dmg` (~50MB)
- No other files needed

### 2. User Installs App
- Drag to Applications folder
- Double-click to launch

### 3. First Launch - Automatic Check ✨

When PaperSort launches for the first time, it automatically checks for:

**Required Dependencies:**
- ✅ Homebrew (macOS package manager)
- ✅ Python 3.11+
- ✅ Python packages (FastAPI, Uvicorn, etc.)
- ✅ Graphviz (for mind-map SVGs)

**Optional Dependencies:**
- 💡 Ollama (for AI-powered features)

### 4. If Dependencies Missing

The app shows a friendly dialog with **3 options**:

#### Option A: "Auto Install" (Recommended)
- Opens Terminal with automated install script
- User just follows the prompts
- Takes ~5 minutes
- Installs everything needed
- User clicks "Restart PaperSort" when done

#### Option B: "Manual Instructions"
- Shows copy-paste commands
- Option to copy to clipboard
- Option to open Terminal
- User installs manually

#### Option C: "Quit"
- User can install later and come back

### 5. Ollama Check (Optional)

Even if all required dependencies are installed, the app offers to install Ollama:

```
┌──────────────────────────────────────┐
│ Enable AI-powered features?          │
│                                       │
│ Ollama provides:                      │
│  • Intelligent paper summaries        │
│  • Analytical mind-maps               │
│  • Better topic classification        │
│                                       │
│ Without Ollama, basic features work.  │
│                                       │
│  [Continue Without AI]  [Install]    │
└──────────────────────────────────────┘
```

### 6. App Launches Normally

Once dependencies are installed (one-time setup), the app launches instantly on future runs.

---

## Technical Implementation

### Dependency Checker (`electron/dependency-checker.js`)

```javascript
class DependencyChecker {
  async checkAll() {
    // Checks:
    // - Homebrew installed?
    // - Python3 available?
    // - pip3 available?
    // - Python packages installed?
    // - Graphviz installed?
    // - Ollama installed?

    return {
      allRequired: boolean,
      results: {...},
      missing: [...]
    }
  }

  async showInstallDialog() {
    // Shows dialog with options
    // Returns: 'quit', 'restart', or 'continue'
  }

  async autoInstall() {
    // Creates temporary install script
    // Opens Terminal to run it
    // Prompts for restart when done
  }
}
```

### Integration (`electron/main.js`)

```javascript
async function createWindow() {
  // 1. Check dependencies
  const checker = new DependencyChecker();
  const result = await checker.checkAll();

  // 2. Handle missing dependencies
  if (!result.allRequired) {
    const action = await checker.showInstallDialog();
    if (action === 'quit') return;
    if (action === 'restart') { app.relaunch(); return; }
  }

  // 3. Start backend & launch app
  await startBackend();
  createMainWindow();
}
```

---

## What Gets Installed

### Required (Auto-installed)

```bash
# Homebrew (if not present)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.11
brew install python@3.11

# Python packages
pip3 install fastapi uvicorn pydantic aiosqlite httpx graphviz

# Graphviz
brew install graphviz
```

### Optional (User choice)

```bash
# Ollama (for AI features)
brew install ollama
ollama pull llama3.2:3b
```

**Total size**: ~500MB for all dependencies
**Install time**: ~5 minutes (one-time)

---

## Distribution Checklist

When sharing PaperSort:

1. ✅ Build the DMG: `npm run build`
2. ✅ Share only the DMG file: `dist-installer/PaperSort-2.0.0-arm64.dmg`
3. ✅ **That's it!** The app handles the rest.

### Optional: Include Documentation

You can also share:
- `README_FOR_USERS.md` - Quick start guide
- `install-dependencies.sh` - Standalone installer (if user prefers manual)

But the DMG alone is enough - the app guides users through everything!

---

## Benefits of This Approach

✅ **Single File Distribution** - Just share the DMG
✅ **Smart First Run** - Automatically detects what's needed
✅ **User-Friendly** - Clear dialogs, no technical knowledge required
✅ **Flexible** - Auto-install OR manual instructions
✅ **Fast Updates** - Small DMG, quick downloads
✅ **One-Time Setup** - Dependencies persist, future launches are instant

---

## Future Enhancement

To make it **zero-setup**, we could:
- Bundle Python interpreter (~100MB)
- Use PyInstaller to create standalone backend
- Include Graphviz binaries
- Result: 200-300MB DMG, no external dependencies

**Trade-off**: Larger file size vs. simpler distribution

**Current approach**: Smaller DMG, one-time 5-min setup, easier to maintain
