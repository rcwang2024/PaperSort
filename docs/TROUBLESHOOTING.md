# Troubleshooting Guide

## Issues We've Solved (Don't Let These Happen Again)

### 1. Backend Won't Start: "Could not connect to backend server"

**Symptoms:**
- Error dialog on app launch
- "No output captured"
- Backend path shown but no logs

**Root Causes & Solutions:**

#### Cause A: PyInstaller Bundle with --noconsole
**Problem:** Backend bundled with `--noconsole` flag doesn't attach stdio properly, causing uvicorn server to hang.

**Solution:** Changed `build-backend.sh` line 26 from `--noconsole` to `--console`

**Files Changed:**
- `build-backend.sh:26`
- `backend/papersort-backend.spec:32` (console=True)

**Prevention:**
- NEVER use `--noconsole` for server applications
- Always test bundled executables before deploying

#### Cause B: Electron Launching Bundled Exe
**Problem:** PyInstaller bundled executables don't work when spawned by Electron on macOS - stdio doesn't attach correctly.

**Solution:** Always use `run_backend.sh` (Python script) instead of bundled exe

**Files Changed:**
- `electron/main.js:125-159` - Disabled bundled exe path, always use script

**Prevention:**
- Stick with `run_backend.sh` approach
- Don't try to "optimize" by using bundled exe

#### Cause C: Port 8000 Already in Use
**Problem:** Previous backend process not killed, port remains occupied.

**Solution:** Kill existing process before starting new one

**Code:** `electron/main.js:43-91`
```javascript
async function killExistingBackend() {
  // Uses lsof -ti :8000 to find PID
  // Kills with kill -9
  // Verifies port is free
}
```

**Prevention:**
- Always call `killExistingBackend()` before starting backend
- This is already implemented, don't remove it

---

### 2. Endless Dependency Check Loop

**Symptoms:**
- Every app launch shows "Install dependencies" dialog
- User clicks install/continue but dialog appears again
- Never gets past dependency check

**Root Cause:** Marker file only created if ALL dependencies pass, but after installation app re-checks and may fail for different dependency.

**Solution:** Create marker file IMMEDIATELY when user clicks install/continue

**Files Changed:**
- `electron/main.js:300-450` - Added marker file logic

**Code:**
```javascript
const markerFile = path.join(os.homedir(), '.papersort', '.deps_verified');

// Create marker when user takes action
if (installResult.action === 'restart') {
  fs.writeFileSync(markerFile, new Date().toISOString());
  app.relaunch();
  app.quit();
} else if (installResult.action === 'continue') {
  fs.writeFileSync(markerFile, new Date().toISOString());
}
```

**Prevention:**
- NEVER remove marker file logic
- If modifying dependency checking, TEST thoroughly with fresh install
- Add "Reset Dependency Check" in Help menu for debugging

**User Reset:**
```bash
rm ~/.papersort/.deps_verified
rm ~/.papersort/.ollama_asked
```

---

### 3. Nonsense Topic Names: "This", "Random", "Single"

**Symptoms:**
- Paper organization creates folders named "This", "Random", "Untitled"
- Topic names don't describe paper content
- Happens with large datasets (1000+ papers)

**Root Cause:** Simple keyword matching extracting random capitalized words from titles

**Solution:** ML-based clustering with TF-IDF + K-Means

**Files Changed:**
- `backend/app/services/paper_organizer.py:463-730`

**Key Improvements:**
1. TF-IDF vectorization filters stop words automatically
2. Extended stopwords list filters nonsense:
   ```python
   stopwords = {
       'untitled', 'unknown', 'this', 'that', 'random', 'single',
       'using', 'based', 'study', 'analysis', ...
   }
   ```
3. Multi-strategy naming (phrases → keywords → titles → fallback)
4. LLM refinement (optional with Ollama)

**Prevention:**
- DON'T revert to keyword matching
- Always test clustering with large datasets (500-1000 papers)
- Check `CLUSTERING_IMPROVEMENTS.md` for details

---

### 4. Imbalanced Clustering: One Huge Folder

**Symptoms:**
- Most papers (>50%) in one topic folder
- Other folders have very few papers
- Defeats purpose of organization

**Root Cause:** K-Means can produce imbalanced clusters, rebalancing threshold too high (60%)

**Solution:** Lower threshold to 40%, add automatic rebalancing

**Files Changed:**
- `backend/app/services/paper_organizer.py:549` - Threshold 60% → 40%
- `backend/app/services/paper_organizer.py:408` - Max papers per topic 50% → 40%

**Code:**
```python
# Detect imbalance
if max_cluster_size > len(papers_metadata) * 0.4:  # 40% threshold
    logger.warning("Imbalanced clustering detected")
    # Increase topics and retry
    num_topics = min(num_topics + 3, MAX_TOPICS)
    # Re-cluster
```

**Prevention:**
- Monitor cluster distribution in logs
- Test with real datasets (826 papers)
- If changing threshold, test thoroughly

---

### 5. Organization Crashes: "await outside async function"

**Symptoms:**
- Organization starts, runs for 1-2 seconds, returns to main page
- No output, no error dialog
- Papers not organized

**Root Cause:** Function `_auto_detect_topics` used `await` but wasn't declared `async`

**Solution:** Made function async

**Files Changed:**
- `backend/app/services/paper_organizer.py:463`

**Before:**
```python
def _auto_detect_topics(...):  # NOT async
    await self._refine_topic_names_with_llm()  # ERROR
```

**After:**
```python
async def _auto_detect_topics(...):  # async
    await self._refine_topic_names_with_llm()  # Works
```

**Prevention:**
- If function uses `await`, it MUST be `async`
- Run `python3 -m py_compile` to catch syntax errors
- Run unit tests before committing

---

### 6. TypeScript Build Errors: Test Files Included

**Symptoms:**
- `npm run build:frontend` fails
- Errors about missing 'vitest' or '@testing-library/react'
- Build worked before, now broken

**Root Cause:** Test files included in TypeScript compilation, but test dependencies not installed

**Solution:** Exclude test files from tsconfig

**Files Changed:**
- `frontend/tsconfig.json:24`

**Code:**
```json
{
  "include": ["src"],
  "exclude": ["src/tests/**/*", "**/*.test.ts", "**/*.test.tsx"]
}
```

**Prevention:**
- Test files should never be included in production builds
- Keep `exclude` in tsconfig.json

---

### 7. Missing numpy Import

**Symptoms:**
- `NameError: name 'np' is not defined`
- Crashes when clustering papers

**Root Cause:** Used `np.ndarray` type hint without importing numpy at module level

**Solution:** Added import at top of file

**Files Changed:**
- `backend/app/services/paper_organizer.py:13` - Added `import numpy as np`

**Prevention:**
- Import ALL dependencies at module level
- Run type checker / linter
- Run tests before committing

---

## Quick Diagnostic Commands

### Is backend running?
```bash
curl -s http://127.0.0.1:8000/health
# Should return: {"status":"healthy"}
```

### What's on port 8000?
```bash
lsof -ti :8000
ps aux | grep <pid>
```

### Kill port 8000
```bash
lsof -ti :8000 | xargs kill -9
```

### Check Python syntax
```bash
cd backend
python3 -m py_compile app/services/paper_organizer.py
```

### Test backend directly
```bash
cd backend
python3 -m app.main
# Should start server on http://127.0.0.1:8000
```

### Test clustering directly
```bash
cd backend
python3 -c "
import asyncio
from app.services.paper_organizer import PaperOrganizer

async def test():
    org = PaperOrganizer()
    result = await org.organize_folder(
        '/path/to/papers',
        num_topics=None,
        copy_mode=True
    )
    print(result)

asyncio.run(test())
"
```

### Check app resources
```bash
ls -la /Applications/PaperSort.app/Contents/Resources/backend/
ls -la /Applications/PaperSort.app/Contents/Resources/frontend/dist/
```

### Reset dependency checks
```bash
rm ~/.papersort/.deps_verified
rm ~/.papersort/.ollama_asked
```

### View database
```bash
sqlite3 ~/.papersort/papersort_v2.db
.tables
.schema papers
SELECT COUNT(*) FROM papers;
.quit
```

## Common Error Messages & Solutions

### "Address already in use" (Errno 48)
**Solution:** Kill port 8000
```bash
lsof -ti :8000 | xargs kill -9
```

### "UNIQUE constraint failed: papers.file_hash"
**Not an error!** Just means paper already exists in database. Organization continues normally.

### "Imbalanced clustering detected"
**Expected behavior.** Backend will automatically retry with more topics. Check final distribution in logs.

### "Duplicate error but can't find paper"
**Harmless.** Duplicate detection working correctly, just verbose logging.

### "Backend failed to start (exit code: 1)"
**Check:** Port 8000 available? Python installed? Dependencies installed?
```bash
lsof -ti :8000 | xargs kill -9
python3 --version  # Should be 3.8+
cd backend && pip list | grep fastapi
```

## Testing Before Release

**Minimum testing checklist:**

```bash
# 1. All tests pass
npm run test:all

# 2. Backend starts
cd backend && python3 -m app.main &
curl http://127.0.0.1:8000/health
pkill -f "app.main"

# 3. Frontend builds
cd frontend && npm run build

# 4. Electron builds
npm run build

# 5. Manual testing
# - Install DMG
# - Launch app
# - Select folder with 100+ papers
# - Run organization
# - Check topic distribution
# - Verify renamed files
```

## When to Ask for Help

**Try these first:**
1. Read this guide
2. Check `ARCHITECTURE.md` for system design
3. Check `DEVELOPMENT.md` for workflow
4. Run tests to identify broken component
5. Check git log for recent changes
6. Try reverting recent commits

**Ask for help if:**
- Tests fail and you don't understand why
- Error messages are cryptic
- System behavior doesn't match documentation
- You need to modify core clustering logic
- You need to change backend launch mechanism
- You want to add new dependencies

## Prevention is Better than Cure

**ALWAYS:**
- Run tests before committing
- Test in both dev and production mode
- Test with real data (not just toy examples)
- Document WHY you made changes
- Keep tests up to date
- Follow the development workflow

**NEVER:**
- Commit with failing tests
- Skip manual testing for UI changes
- Modify clustering without testing on 500+ papers
- Change backend launch without understanding stdio
- Remove marker file logic
- Revert to keyword matching
- Use `--noconsole` for servers

---

## Backend fails to start: wrong Python environment

**Symptom:** the packaged app fails to start the backend.

**Cause:**

The previous build failed because:
- The packaged app was using **system Python 3.9** (from Command Line Tools)
- The development environment used **Anaconda Python 3.13**
- System Python had incompatible or missing packages for uvicorn/FastAPI

**Fix:**

`backend/run_backend.sh` now:

1. **Smart Python Detection**
   - Tries multiple Python versions: 3.13, 3.12, 3.11, 3.10, 3.9, 3.8
   - Picks the first one that's version 3.8 or higher
   - Shows exactly which Python it selected

2. **Virtual Environment Creation**
   - Creates `.venv` inside the app's backend folder
   - Completely isolated from system Python
   - Avoids conflicts with existing installations

3. **Automatic Dependency Installation**
   - On first launch, installs all required packages in the venv
   - Takes ~2-3 minutes initially
   - Subsequent launches are instant (packages already installed)

4. **Comprehensive Logging**
   - Shows every step in DevTools Console
   - Displays Python version and path
   - Shows package installation progress
   - Reports any errors with full details

The launcher checks that *all* backend packages import (not just FastAPI/Uvicorn) and installs `backend/requirements.txt` if any is missing.
