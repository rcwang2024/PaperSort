#!/bin/bash

echo "🔨 Building standalone Python backend..."

cd backend

# Clean previous builds
rm -rf build dist *.spec 2>/dev/null

# Build with PyInstaller
pyinstaller --clean --noconfirm \
    --onefile \
    --name papersort-backend \
    --hidden-import=uvicorn.logging \
    --hidden-import=uvicorn.loops \
    --hidden-import=uvicorn.loops.auto \
    --hidden-import=uvicorn.protocols \
    --hidden-import=uvicorn.protocols.http \
    --hidden-import=uvicorn.protocols.http.auto \
    --hidden-import=uvicorn.protocols.websockets \
    --hidden-import=uvicorn.protocols.websockets.auto \
    --hidden-import=uvicorn.lifespan \
    --hidden-import=uvicorn.lifespan.on \
    --add-data "app:app" \
    --target-arch arm64 \
    --noconsole \
    app/main.py

if [ $? -eq 0 ]; then
    echo "✅ Backend bundled successfully: backend/dist/papersort-backend"
else
    echo "❌ Backend bundling failed"
    exit 1
fi
