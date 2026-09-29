"""
PaperSort v2.0 - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.routers import papers, classification, mindmap, export_router, organize
from app.database.db import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting PaperSort v2.0 Backend")

    # Initialize database
    db = DatabaseManager()
    await db.initialize()
    app.state.db = db

    # Initialize services
    logger.info("Initializing services...")

    yield

    # Shutdown
    logger.info("Shutting down PaperSort Backend")
    await db.close()


# Create FastAPI app
app = FastAPI(
    title="PaperSort API",
    description="High-performance API for academic paper management",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",   # Vite dev server (npm run electron:dev)
        "http://127.0.0.1:1420",
        "http://localhost:3000",
        # The packaged app loads the UI from file://, which Chromium sends as
        # Origin "null"; without it every POST preflight is rejected (400).
        # Safe here because the backend only listens on 127.0.0.1.
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(classification.router, prefix="/api/classification", tags=["classification"])
app.include_router(mindmap.router, prefix="/api/mindmap", tags=["mindmap"])
app.include_router(export_router.router, prefix="/api/export", tags=["export"])
app.include_router(organize.router, prefix="/api", tags=["organize"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "PaperSort API",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# WebSocket for real-time progress updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now
            await websocket.send_json({"message": "Connected"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
