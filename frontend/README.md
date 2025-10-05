# PaperSort Frontend

Modern desktop application built with Tauri + React + TypeScript.

## Tech Stack

- **Tauri** - Lightweight desktop app framework
- **React 18** - UI framework
- **TypeScript** - Type safety
- **TailwindCSS** - Styling
- **Vite** - Build tool
- **Cytoscape.js** - Mind-map visualization

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- Rust (for Tauri)
- Backend server running on `http://127.0.0.1:8000`

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run tauri:dev
```

This will:
1. Start Vite dev server
2. Launch Tauri development window
3. Hot reload on file changes

## Project Structure

```
frontend/
├── src/
│   ├── components/      # React components
│   │   ├── PaperLibrary.tsx
│   │   ├── MindMapViewer.tsx
│   │   └── BibTeXExporter.tsx
│   ├── services/        # API clients
│   │   └── api.ts
│   ├── types/           # TypeScript types
│   ├── App.tsx          # Main app component
│   └── main.tsx         # Entry point
├── src-tauri/           # Tauri backend (Rust)
│   ├── src/
│   │   └── main.rs
│   ├── tauri.conf.json
│   └── Cargo.toml
├── public/              # Static assets
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Building for Production

```bash
npm run tauri:build
```

This creates installers in `src-tauri/target/release/bundle/`:
- macOS: `.app` and `.dmg`
- Windows: `.msi`
- Linux: `.deb`, `.AppImage`

## Features

- 📚 Paper library management
- 🔍 Full-text search
- 🗺️ Interactive mind-maps
- 📝 BibTeX export
- ⚡ Real-time progress updates (WebSocket)
- 🎨 Modern, responsive UI

## API Integration

The frontend communicates with the FastAPI backend via REST API:

- Papers: `http://127.0.0.1:8000/api/papers`
- Mind-maps: `http://127.0.0.1:8000/api/mindmap`
- Export: `http://127.0.0.1:8000/api/export`
- WebSocket: `ws://127.0.0.1:8000/ws/progress`
