# PaperSort Architecture

## Overview
PaperSort is an Electron desktop app with a FastAPI Python backend that organizes academic papers using ML-based clustering.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron Main Process                     │
│  - Window management                                         │
│  - Backend process spawning (run_backend.sh)                │
│  - Dependency checking (Python, pip, Ollama)                │
│  - Port conflict resolution (kill port 8000)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  React Frontend (Vite + TS)                  │
│  - FolderSelector component                                  │
│  - WebSocket progress updates                                │
│  - API client (PaperSortAPI)                                │
│  URL: http://localhost:5173 (dev) / local files (prod)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Python 3.8+)                   │
│  - URL: http://127.0.0.1:8000                               │
│  - Launched by: bash run_backend.sh                         │
│  - Key Routes:                                               │
│    • POST /api/organize/async - Start paper organization    │
│    • GET /api/organize/status/{task_id} - Check progress   │
│    • WS /api/organize/progress/{task_id} - Live updates    │
│    • POST /api/mindmap/generate - Generate mind maps        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Services                             │
│  1. PaperOrganizer - Main organization logic                │
│  2. EnhancedPDFExtractor - PDF metadata extraction          │
│  3. MetadataEnhancer - CrossRef/PubMed API calls           │
│  4. DatabaseManager - SQLite paper storage                  │
│  5. RecommendationService - Paper recommendations           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 ML Clustering Pipeline                       │
│  1. TF-IDF Vectorization (sklearn)                          │
│     - Converts paper text to numerical vectors              │
│     - Filters stop words, captures n-grams                  │
│  2. K-Means Clustering                                       │
│     - Groups similar papers                                  │
│     - Auto-determines optimal cluster count                  │
│     - Rebalances if one cluster >40% of papers             │
│  3. Topic Naming                                             │
│     - Extracts top TF-IDF terms                             │
│     - Multi-strategy naming (phrases → keywords → titles)   │
│     - Optional LLM refinement (Ollama)                      │
│  4. Paper Classification                                     │
│     - Assigns papers to topics                              │
│     - Renames files: [Year] Title - Author.pdf             │
│     - Moves/copies to topic folders                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   File System Output                         │
│  Organized_Papers/                                           │
│  ├── Deep Learning Models/ (87 papers)                      │
│  ├── Cancer Genomics/ (95 papers)                           │
│  ├── Type 2 Diabetes/ (73 papers)                           │
│  └── ... (max 15 topics)                                    │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Backend Launch Strategy
**Current:** Always use `run_backend.sh` (Python script)
**Reason:** PyInstaller bundled executables don't work properly with uvicorn on macOS when launched by Electron - stdio doesn't attach correctly causing server hangs.

**Code:** `electron/main.js:125-159`
```javascript
// DISABLED: PyInstaller bundled exe doesn't work
// Always use run_backend.sh which runs Python directly
const launcherScript = path.join(backendPath, 'run_backend.sh');
backendProcess = spawn('bash', [launcherScript], {
  cwd: backendPath,
  stdio: 'pipe',
  env: { ...process.env }
});
```

### 2. Port Conflict Resolution
**Problem:** Backend fails if port 8000 already in use
**Solution:** Kill existing process before starting

**Code:** `electron/main.js:43-91`
```javascript
async function killExistingBackend() {
  return new Promise((resolve) => {
    exec('lsof -ti :8000', (error, stdout) => {
      if (!error && stdout.trim()) {
        const pid = stdout.trim();
        exec(`kill -9 ${pid}`, (killError) => {
          // Verify port is free
          setTimeout(() => verifyPortFree(resolve), 1000);
        });
      } else {
        resolve();
      }
    });
  });
}
```

### 3. Dependency Check Flow
**Problem:** Endless loop asking to install dependencies on every launch
**Solution:** Marker files to track verification state

**Files:**
- `~/.papersort/.deps_verified` - Dependencies checked
- `~/.papersort/.ollama_asked` - Ollama prompt shown

**Code:** `electron/main.js:300-450`
```javascript
const markerFile = path.join(os.homedir(), '.papersort', '.deps_verified');
const depsAlreadyVerified = fs.existsSync(markerFile);

if (!depsAlreadyVerified) {
  // Run check
  if (checkResult.allRequired) {
    fs.writeFileSync(markerFile, new Date().toISOString());
  }
}
```

### 4. ML Clustering Algorithm
**Current:** TF-IDF + K-Means with auto-balancing
**Parameters:**
- Max topics: 15 (prevent folder clutter)
- Min papers per topic: 2
- Rebalance trigger: Any cluster >40% of papers
- TF-IDF: min_df=2, max_df=0.8, ngram_range=(1,3)
- K-Means: init='k-means++', n_init=20, max_iter=500

**Code:** `backend/app/services/paper_organizer.py:463-605`

**Topic Count Auto-Detection:**
- <50 papers → 3 topics
- 50-200 papers → 5 topics
- 200-500 papers → 8 topics
- 500+ papers → ~1 topic per 80 papers (max 15)

### 5. Topic Naming Strategy
**Priority (first match wins):**
1. Multi-word phrases from TF-IDF (e.g., "deep learning")
2. Combine top 2 single words
3. Extract from paper keywords
4. Extract from paper titles
5. Single filtered term
6. Fallback: "Research Topic N"

**Extended stopwords** filter out nonsense names:
- "untitled", "unknown", "this", "that", "random", "single"
- "using", "based", "study", "analysis", "method"

**Code:** `backend/app/services/paper_organizer.py:607-730`

## Data Flow: Organization Request

1. **User selects folder** → Frontend `FolderSelector` component
2. **POST /api/organize/async** → Backend creates task ID
3. **Background task starts:**
   - Scan folder for PDFs
   - Remove duplicates (hash-based)
   - Extract metadata (PyMuPDF + CrossRef)
   - Cluster papers (TF-IDF + K-Means)
   - Generate topic names (TF-IDF → LLM optional)
   - Classify papers to topics
   - Rename & move/copy files
4. **WebSocket updates** → Frontend shows progress bar
5. **Task completes** → Results shown to user

## Database Schema

**papers table:**
- id (INTEGER PRIMARY KEY)
- title, authors, year, doi, abstract
- file_path, file_hash (UNIQUE)
- keywords, journal, citations
- added_date, last_modified

**Indexes:**
- file_hash (prevent duplicates)
- title (search)
- year (sorting)

**Location:** `~/.papersort/papersort_v2.db`

## Configuration & State

**User data directory:**
- Development: `~/Library/Application Support/papersort/`
- Production: Same

**Persistent state:**
- `~/.papersort/.deps_verified` - Skip dependency check
- `~/.papersort/.ollama_asked` - Skip Ollama prompt
- `~/.papersort/papersort_v2.db` - Paper database
- `~/.papersort/logs/` - Backend logs (if implemented)

## Performance Characteristics

**Clustering performance (TF-IDF + K-Means):**
- 100 papers: ~2-3 seconds
- 500 papers: ~5-8 seconds
- 1000 papers: ~10-15 seconds
- LLM refinement: +1-2 seconds per topic (optional)

**PDF processing:**
- Parallel processing: 4 workers
- ~1-2 seconds per PDF for metadata extraction

## Known Limitations

1. **Backend bundling:** PyInstaller doesn't work, must use Python script
2. **Max topics:** Hard-capped at 15 to prevent folder clutter
3. **Ollama optional:** App works without it, but topic names less refined
4. **macOS only:** Dependency checking assumes macOS commands (lsof, etc.)

## Critical Files

**DO NOT MODIFY without understanding:**
1. `electron/main.js:43-91` - Port conflict resolution
2. `electron/main.js:125-159` - Backend launching
3. `electron/main.js:300-450` - Dependency checking with markers
4. `backend/app/services/paper_organizer.py:463-605` - Clustering algorithm
5. `backend/app/services/paper_organizer.py:607-730` - Topic naming

## Testing Requirements

**Before deploying ANY change, run:**
```bash
# Backend tests
cd backend && pytest -v

# Frontend tests
cd frontend && npm test

# E2E tests
cd frontend && npm run test:e2e

# Full test suite
npm run test:all
```

**See TESTING.md for details.**
