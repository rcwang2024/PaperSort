# Development Workflow

## DO NOT BREAK THE APP: Mandatory Process

**ALWAYS follow this process before committing ANY code:**

### 1. Before Making Changes
```bash
# Run existing tests to establish baseline
npm run test:all

# If tests fail, FIX THEM FIRST before making your changes
```

### 2. Make Your Changes
- Modify code
- Update tests if needed
- Add new tests for new features

### 3. Test Your Changes
```bash
# Run full test suite
npm run test:all

# If any test fails, FIX IT before committing
# Do NOT commit broken tests
```

### 4. Manual Testing (Required for UI changes)
```bash
# Run in development mode
npm run electron:dev

# Test the specific feature you changed
# Test edge cases
# Try to break it
```

### 5. Build and Test Production Build
```bash
# Build the app
npm run build

# Install and test the DMG
open dist-installer/PaperSort-2.0.0-arm64.dmg

# Test the feature in production mode
```

### 6. Commit ONLY if all tests pass
```bash
# Stage your changes
git add <files>

# Commit with clear message
git commit -m "feat: <description>

- What changed
- Why it changed
- What tests were added/updated

Tested:
- All unit tests passing
- Integration tests passing
- Manually tested in dev and production"

# Push
git push
```

## Common Breaking Changes to AVOID

### ❌ DON'T: Change backend launch without testing
**Bad:**
```javascript
// Switching between bundled exe and script without testing both
if (someCondition) {
  spawn(bundledExe, ...);
} else {
  spawn('bash', [script], ...);
}
```

**Good:**
```javascript
// Always use the proven approach
const launcherScript = path.join(backendPath, 'run_backend.sh');
backendProcess = spawn('bash', [launcherScript], ...);
```

### ❌ DON'T: Add PyInstaller flags without understanding
**Bad:**
```bash
pyinstaller --noconsole  # Breaks uvicorn servers
pyinstaller --onefile --windowed  # Creates .app bundle that doesn't work
```

**Good:**
```bash
pyinstaller --console --onefile  # Works for servers
```

### ❌ DON'T: Modify clustering without testing on real data
**Bad:**
```python
# Changing threshold without testing
if max_cluster_size > len(papers) * 0.9:  # Too high, won't trigger
```

**Good:**
```python
# Test with actual datasets first
if max_cluster_size > len(papers) * 0.4:  # Tested with 826 papers
    # Rebalance logic
```

### ❌ DON'T: Change async/await patterns without checking
**Bad:**
```python
def _auto_detect_topics(...):  # Not async
    await self._refine_topic_names_with_llm()  # Breaks!
```

**Good:**
```python
async def _auto_detect_topics(...):  # Async
    await self._refine_topic_names_with_llm()  # Works
```

### ❌ DON'T: Modify dependency checks without marker file logic
**Bad:**
```python
# Always check on every launch
if not check_dependencies():
    show_install_dialog()
```

**Good:**
```python
# Use marker files to avoid endless loops
if not fs.existsSync(markerFile):
    if check_dependencies():
        fs.writeFileSync(markerFile, ...)
```

## Development Commands

### Backend Development
```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # or . venv/bin/activate

# Run backend directly
python3 -m app.main

# Run with auto-reload
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Run tests
pytest -v
pytest tests/unit -v
pytest tests/integration -v
pytest --cov=app --cov-report=html

# Check for import errors
python3 -m py_compile app/services/paper_organizer.py
```

### Frontend Development
```bash
cd frontend

# Run dev server
npm run dev

# Run tests
npm test
npm run test:ui  # Interactive UI
npm run test:coverage

# Type check
npm run build  # TypeScript will validate
```

### Electron Development
```bash
# Run in development mode (with hot reload)
npm run electron:dev

# Build for production
npm run build  # Backend + Frontend + Electron

# Build without backend bundling (faster)
npm run build:no-backend
```

### Full Stack Testing
```bash
# From project root
npm run test:all  # Backend + Frontend + E2E

# Run E2E tests
cd frontend && npm run test:e2e
```

## Debugging

### Backend Issues

**Check if backend is running:**
```bash
curl http://127.0.0.1:8000/health
# Should return: {"status":"healthy"}
```

**Check what's on port 8000:**
```bash
lsof -ti :8000
ps aux | grep <pid>
```

**Kill port 8000:**
```bash
lsof -ti :8000 | xargs kill -9
```

**View backend logs (if app is running):**
```bash
# Electron console output
# Or check:
tail -f ~/.papersort/logs/backend.log  # If log file exists
```

**Test backend manually:**
```bash
cd backend
python3 -m app.main

# In another terminal:
curl -X POST http://127.0.0.1:8000/api/organize/async \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "/path/to/papers", "copy_mode": true}'
```

### Frontend Issues

**Check API connection:**
```bash
# Frontend should connect to http://127.0.0.1:8000
# Check browser console for CORS/connection errors
```

**Rebuild frontend:**
```bash
cd frontend
rm -rf dist node_modules
npm install
npm run build
```

### Electron Issues

**View Electron console:**
```bash
# Run in dev mode and check terminal output
npm run electron:dev
```

**Check app resources:**
```bash
ls -la /Applications/PaperSort.app/Contents/Resources/backend/
ls -la /Applications/PaperSort.app/Contents/Resources/frontend/dist/
```

**Reset dependency checks:**
```bash
rm ~/.papersort/.deps_verified
rm ~/.papersort/.ollama_asked
```

### Clustering Issues

**Test clustering with real data:**
```bash
cd backend
python3 << 'EOF'
import asyncio
from app.services.paper_organizer import PaperOrganizer

async def test():
    organizer = PaperOrganizer()
    # Test with your papers
    await organizer.organize_folder(
        folder_path="/path/to/papers",
        num_topics=None,  # Auto-detect
        copy_mode=True
    )

asyncio.run(test())
EOF
```

**Check cluster distribution:**
```python
# Add logging in paper_organizer.py:545
logger.info(f"Cluster sizes: {dict(zip(unique, counts))}")
# Should show balanced distribution, no cluster >40%
```

## Git Workflow

### Branch Strategy
```bash
# Main branch: stable, tested code
# Feature branches: new features

# Create feature branch
git checkout -b feature/my-new-feature

# Make changes, test thoroughly
# ... make changes ...
npm run test:all  # MUST PASS

# Commit
git add <files>
git commit -m "feat: description"

# Push
git push origin feature/my-new-feature

# Merge to main after testing
git checkout main
git merge feature/my-new-feature
git push origin main
```

### Commit Message Format
```
<type>: <short summary>

<detailed description>

- What changed
- Why it changed
- How it was tested

Tested:
- Unit tests: passing
- Integration tests: passing
- Manual testing: completed
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code restructuring
- `test:` Adding/updating tests
- `docs:` Documentation
- `chore:` Maintenance

## Pre-Commit Checklist

- [ ] All tests pass (`npm run test:all`)
- [ ] No TypeScript errors (`cd frontend && npm run build`)
- [ ] No Python syntax errors (`cd backend && python3 -m py_compile app/**/*.py`)
- [ ] Manual testing in dev mode completed
- [ ] Production build tested (if changing build process)
- [ ] Documentation updated (if needed)
- [ ] No debug code left (console.log, print statements)
- [ ] Code is formatted and readable

## Production Build Checklist

Before releasing a new version:

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] E2E tests passing
- [ ] Manual testing with real datasets (small, medium, large)
- [ ] Test on clean install (no existing database/config)
- [ ] Test dependency checking flow
- [ ] Test with and without Ollama
- [ ] Build completes without errors
- [ ] DMG installs correctly
- [ ] App launches without errors
- [ ] Backend connects successfully
- [ ] Organization workflow completes
- [ ] Clustering produces reasonable results
- [ ] Mind map generation works (if tested)
- [ ] Update version number
- [ ] Tag release in git

## When Things Break

**Step 1: Don't panic, check tests**
```bash
npm run test:all
# What tests are failing? This tells you what broke.
```

**Step 2: Check recent changes**
```bash
git log --oneline -10
git diff HEAD~1  # What changed in last commit?
```

**Step 3: Isolate the problem**
- Backend issue? Test backend directly
- Frontend issue? Check browser console
- Electron issue? Check Electron console
- Clustering issue? Test PaperOrganizer directly

**Step 4: Revert if needed**
```bash
git revert <commit-hash>
# Or
git reset --hard HEAD~1  # DANGEROUS: loses uncommitted changes
```

**Step 5: Fix properly**
- Write a failing test that reproduces the bug
- Fix the code
- Verify test passes
- Run full test suite
- Commit with clear message

## Performance Optimization

**Profile clustering:**
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Run clustering
await organizer._auto_detect_topics(papers, num_topics)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

**Profile frontend:**
```javascript
// Use React DevTools Profiler
// Or browser Performance tab
```

## Environment Setup

**Required:**
- Python 3.8+
- Node.js 18+
- macOS (for full functionality)

**Optional:**
- Ollama (for LLM-enhanced topic names)

**Install dependencies:**
```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install

# Root (for Electron)
npm install
```

## Architecture Diagram

See `ARCHITECTURE.md` for full system diagram and component descriptions.

## Common Pitfalls

1. **Forgetting to kill port 8000** before testing
2. **Not running tests** before committing
3. **Testing only in dev mode** (prod mode can behave differently)
4. **Changing clustering logic** without testing on real data
5. **Modifying async functions** without testing thoroughly
6. **Breaking dependency check** (causing endless loops)
7. **Changing backend launch** without understanding stdio issues
8. **Committing with failing tests** (NEVER do this)
