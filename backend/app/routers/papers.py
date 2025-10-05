"""
Papers API router
Handles paper management operations
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Optional
from pathlib import Path
import logging
import shutil

from app.models.schemas import (
    PaperCreate, PaperUpdate, PaperResponse,
    PaperSearchRequest, BatchProcessRequest, BatchProcessResponse
)
from app.database.db import DatabaseManager
from app.services.pdf_processor import EnhancedPDFExtractor
from app.services.api_enhancer import MetadataEnhancer

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=PaperResponse)
async def upload_paper(
    file: UploadFile = File(...),
    enhance_metadata: bool = Form(True)
):
    """Upload a single PDF paper"""

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save uploaded file temporarily
    temp_dir = Path.home() / ".papersort" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / file.filename

    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)

        # Extract metadata
        pdf_extractor = EnhancedPDFExtractor()
        metadata = await pdf_extractor.extract_metadata(temp_path)
        pdf_extractor.shutdown()

        # Enhance metadata if requested
        if enhance_metadata:
            async with MetadataEnhancer() as enhancer:
                metadata = await enhancer.enhance_metadata(metadata)

        # Add to database
        db = DatabaseManager()
        await db.initialize()
        paper_id = await db.add_paper(
            metadata=metadata,
            file_path=temp_path,
            full_text=metadata.get('full_text', '')
        )

        paper = await db.get_paper(paper_id)
        await db.close()

        return paper

    except Exception as e:
        logger.error(f"Error uploading paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()


@router.post("/batch", response_model=BatchProcessResponse)
async def batch_process(request: BatchProcessRequest):
    """Process multiple PDFs from a directory"""

    directory = Path(request.directory_path)
    if not directory.exists():
        raise HTTPException(status_code=400, detail="Directory does not exist")

    pdf_files = list(directory.rglob("*.pdf"))
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No PDF files found in directory")

    # TODO: Implement background task processing
    # For now, return task info
    return {
        'task_id': 'task_' + str(hash(str(directory))),
        'total_files': len(pdf_files),
        'message': f"Processing {len(pdf_files)} PDF files"
    }


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: int):
    """Get paper by ID"""

    db = DatabaseManager()
    await db.initialize()
    paper = await db.get_paper(paper_id)
    await db.close()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return paper


@router.get("/", response_model=List[PaperResponse])
async def list_papers(limit: int = 100, offset: int = 0):
    """List all papers with pagination"""

    db = DatabaseManager()
    await db.initialize()
    papers = await db.get_all_papers(limit=limit, offset=offset)
    await db.close()

    return papers


@router.post("/search", response_model=List[PaperResponse])
async def search_papers(request: PaperSearchRequest):
    """Search papers using full-text search"""

    db = DatabaseManager()
    await db.initialize()
    papers = await db.search_papers(
        query=request.query,
        limit=request.limit,
        offset=request.offset
    )
    await db.close()

    return papers


@router.put("/{paper_id}", response_model=PaperResponse)
async def update_paper(paper_id: int, updates: PaperUpdate):
    """Update paper metadata"""

    db = DatabaseManager()
    await db.initialize()

    # Check if paper exists
    paper = await db.get_paper(paper_id)
    if not paper:
        await db.close()
        raise HTTPException(status_code=404, detail="Paper not found")

    # Update
    update_dict = updates.model_dump(exclude_unset=True)
    await db.update_paper(paper_id, update_dict)

    # Get updated paper
    paper = await db.get_paper(paper_id)
    await db.close()

    return paper


@router.delete("/{paper_id}")
async def delete_paper(paper_id: int):
    """Delete a paper"""

    db = DatabaseManager()
    await db.initialize()

    paper = await db.get_paper(paper_id)
    if not paper:
        await db.close()
        raise HTTPException(status_code=404, detail="Paper not found")

    await db.delete_paper(paper_id)
    await db.close()

    return {"message": "Paper deleted successfully"}


@router.get("/stats/overview")
async def get_statistics():
    """Get database statistics"""

    db = DatabaseManager()
    await db.initialize()
    stats = await db.get_statistics()
    await db.close()

    return stats
