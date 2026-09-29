# PaperSort frontend

React 18 + TypeScript UI, bundled with Vite and loaded by the Electron shell in [`../electron`](../electron).
It talks to the FastAPI backend on `http://127.0.0.1:8000` (REST, plus a WebSocket for organisation progress).

## Structure

```
src/
  App.tsx                 app state and layout
  components/
    FolderSelector.tsx    folder picker and organisation options
    ProgressTracker.tsx   live progress over WebSocket
    TopicList.tsx         organised topics and papers
    MindMapWindow.tsx     mind-map SVG and summary
    ReferenceManager.tsx  BibTeX export
  services/api.ts         backend API client
  types/                  shared types, incl. the window.electron bridge
  tests/                  Vitest + Testing Library unit tests
e2e/                      Playwright end-to-end tests
```

## Scripts

```bash
npm run dev        # Vite dev server on http://localhost:1420 (used by `npm run electron:dev` in the repo root)
npm run build      # type-check and production build to dist/
npx vitest run     # unit tests
npm run test:e2e   # Playwright tests (needs the backend running)
```

Outside Electron (plain browser), folder selection falls back to a text prompt for the path.
