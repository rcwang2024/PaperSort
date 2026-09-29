# PaperSort

**A desktop app that organises a folder of research PDFs into topics, renames them consistently, and generates
mind-maps, summaries and BibTeX — with a local LLM, so your papers never leave your machine.**

![Electron](https://img.shields.io/badge/Electron-28-47848F?logo=electron&logoColor=white)
![React](https://img.shields.io/badge/React-18%20%2B%20TypeScript-61DAFB?logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-Python%203.11-009688?logo=fastapi&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-TF--IDF%20%2B%20K--Means-F7931E?logo=scikitlearn&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-000000)
![License](https://img.shields.io/badge/license-MIT-blue)

![PaperSort organising 12 papers into 3 topics](docs/screenshot.png)

## Features

- **Topic organisation** — clusters papers by content (TF-IDF + K-Means) and copies or moves them into topic folders (max 15 topics, auto-balanced).
- **Consistent file names** — `[Year] Title - FirstAuthor.pdf`, from metadata extracted with PyMuPDF.
- **Mind-maps & summaries** — a local LLM (Ollama, `llama3.2:3b`) extracts problem, method, results and contributions; rendered as SVG with Graphviz.
- **BibTeX export** — validated entries, with optional metadata enrichment from CrossRef, arXiv and Semantic Scholar.
- **Full-text search** — papers are stored in SQLite with an FTS5 index.

**Privacy:** PDF parsing, clustering and the LLM all run locally. The only network access is the optional
*Enhance metadata* step of the BibTeX export, which sends titles/DOIs to the services above — untick it to stay fully offline.

## How it works

```
Electron shell ──► React + TypeScript UI (Vite)
      │                    │  REST + WebSocket progress
      │ starts             ▼
      └──────────► FastAPI backend (127.0.0.1:8000)
                     ├─ PDF extraction ........ PyMuPDF / PyPDF2
                     ├─ Topic clustering ...... TF-IDF (1–3-grams) + K-Means, topic naming from top terms
                     ├─ Mind-maps ............. Ollama (optional) → Graphviz SVG
                     ├─ BibTeX export ......... CrossRef / arXiv / Semantic Scholar (optional)
                     └─ Storage ............... SQLite + FTS5 (~/.papersort)
```

Details: [architecture](docs/ARCHITECTURE.md) · [clustering](docs/CLUSTERING_IMPROVEMENTS.md) · [how the app starts its backend](docs/HOW_IT_WORKS.md)

## Getting started

Prebuilt installers are not published yet — build from source (macOS, Apple Silicon is the packaged target;
the backend and UI also run on Linux and Windows for development).

**Requirements:** Node.js 18+, Python 3.11, [Graphviz](https://graphviz.org/download/), and optionally [Ollama](https://ollama.com) for AI mind-maps.

```bash
git clone https://github.com/rcwang2024/PaperSort.git
cd PaperSort

# Backend
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd ..

# Frontend + Electron (also installs frontend/ via postinstall)
npm install

# Optional: local LLM for mind-maps
ollama pull llama3.2:3b

# Run in development mode
npm run electron:dev
```

Build a macOS installer with `npm run build` (output: `dist-installer/PaperSort-2.0.0-arm64.dmg`).
See the [user guide](docs/USER_GUIDE.md) and [install notes](docs/INSTALL.md).

## Tests

```bash
npm test                 # backend (pytest) + frontend (Vitest)
npm run test:e2e         # Playwright end-to-end tests
```

50 backend tests (unit + API integration) and 20 frontend tests. See [docs/TESTING.md](docs/TESTING.md).

## Documentation

| For developers | For users |
|---|---|
| [Development workflow](docs/DEVELOPMENT.md) | [User guide](docs/USER_GUIDE.md) |
| [Architecture](docs/ARCHITECTURE.md) | [Installation](docs/INSTALL.md) |
| [Testing](docs/TESTING.md) | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| [Clustering](docs/CLUSTERING_IMPROVEMENTS.md) · [Distribution](docs/DISTRIBUTION.md) | [How it works](docs/HOW_IT_WORKS.md) |

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE). Built with Ollama, Graphviz, FastAPI, Electron and React.
