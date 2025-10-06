"""
Folder Organization API Router
Main workflow endpoint for organizing paper folders
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import logging
import asyncio

from app.services.paper_organizer import PaperOrganizer

logger = logging.getLogger(__name__)

router = APIRouter()


class OrganizeFolderRequest(BaseModel):
    """Request to organize a folder"""
    folder_path: str
    num_topics: Optional[int] = None
    custom_topics: Optional[List[str]] = None
    copy_mode: bool = True  # True = copy, False = move
    enhance_metadata: bool = False  # Skip API calls for speed

    def model_post_init(self, __context):
        """Validate topic limits"""
        MAX_TOPICS = 15

        # Limit num_topics to maximum
        if self.num_topics is not None and self.num_topics > MAX_TOPICS:
            logger.warning(f"num_topics={self.num_topics} exceeds maximum of {MAX_TOPICS}, limiting to {MAX_TOPICS}")
            self.num_topics = MAX_TOPICS

        # Limit custom_topics length
        if self.custom_topics is not None and len(self.custom_topics) > MAX_TOPICS:
            logger.warning(f"custom_topics count={len(self.custom_topics)} exceeds maximum of {MAX_TOPICS}, truncating")
            self.custom_topics = self.custom_topics[:MAX_TOPICS]


class OrganizeFolderResponse(BaseModel):
    """Response from folder organization"""
    success: bool
    input_folder: str
    total_papers: int
    processed_papers: int
    topics: dict
    bibtex_file: Optional[str]
    errors: List[str] = []


# Store active organization tasks
active_tasks = {}


@router.post("/organize", response_model=OrganizeFolderResponse)
async def organize_folder(request: OrganizeFolderRequest):
    """
    Organize a folder of papers

    This is the main workflow endpoint that:
    1. Scans folder for PDFs
    2. Extracts and enhances metadata
    3. Classifies into topics
    4. Renames and organizes into subfolders
    5. Downloads recommendations
    6. Generates BibTeX file

    Returns structured view of organized papers
    """

    folder_path = Path(request.folder_path)

    if not folder_path.exists():
        raise HTTPException(status_code=400, detail="Folder does not exist")

    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    try:
        organizer = PaperOrganizer()

        # Run organization
        results = await organizer.organize_folder(
            folder_path=folder_path,
            num_topics=request.num_topics,
            custom_topics=request.custom_topics,
            copy_mode=request.copy_mode,
            enhance_metadata=request.enhance_metadata
        )

        # Get structured view for UI
        structure = organizer.get_paper_structure(results)

        return {
            'success': True,
            'input_folder': results['input_folder'],
            'total_papers': results['total_papers'],
            'processed_papers': results['processed_papers'],
            'topics': structure,
            'bibtex_file': results['bibtex_file'],
            'errors': results['errors']
        }

    except Exception as e:
        logger.error(f"Error organizing folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organize/async")
async def organize_folder_async(request: OrganizeFolderRequest):
    """
    Start folder organization as background task

    Returns task ID for progress tracking via WebSocket
    """

    folder_path = Path(request.folder_path)

    if not folder_path.exists():
        raise HTTPException(status_code=400, detail="Folder does not exist")

    # Generate task ID
    import uuid
    task_id = str(uuid.uuid4())

    # Store task
    active_tasks[task_id] = {
        'status': 'starting',
        'progress': 0,
        'message': 'Initializing...'
    }

    # Start background task
    asyncio.create_task(_run_organization_task(task_id, request))

    return {
        'task_id': task_id,
        'message': 'Organization started. Connect to WebSocket for progress updates.'
    }


async def _run_organization_task(task_id: str, request: OrganizeFolderRequest):
    """Background task for folder organization"""

    try:
        folder_path = Path(request.folder_path)
        organizer = PaperOrganizer()

        async def update_progress(progress: float, message: str):
            active_tasks[task_id] = {
                'status': 'processing',
                'progress': progress,
                'message': message
            }
            logger.info(f"Task {task_id} progress: {progress}% - {message}")
            # Small delay to allow WebSocket to catch updates
            await asyncio.sleep(0.1)

        results = await organizer.organize_folder(
            folder_path=folder_path,
            num_topics=request.num_topics,
            custom_topics=request.custom_topics,
            copy_mode=request.copy_mode,
            enhance_metadata=request.enhance_metadata,
            progress_callback=update_progress
        )

        # Mark complete
        structure = organizer.get_paper_structure(results)
        active_tasks[task_id] = {
            'status': 'completed',
            'progress': 100,
            'message': 'Organization complete!',
            'results': structure
        }

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        active_tasks[task_id] = {
            'status': 'failed',
            'progress': 0,
            'message': str(e)
        }


@router.get("/organize/status/{task_id}")
async def get_task_status(task_id: str):
    """Get status of organization task"""

    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    return active_tasks[task_id]


@router.websocket("/ws/organize/{task_id}")
async def websocket_organize_progress(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time progress updates"""

    await websocket.accept()

    try:
        while True:
            if task_id in active_tasks:
                task_info = active_tasks[task_id]
                await websocket.send_json(task_info)

                # If completed or failed, close connection
                if task_info['status'] in ['completed', 'failed']:
                    break

            await asyncio.sleep(0.5)  # Update every 500ms

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")


@router.get("/structure/{folder_path:path}")
async def get_folder_structure(folder_path: str):
    """
    Get structured view of already organized folder

    Useful for loading existing organized folders in the UI
    """

    path = Path(folder_path)

    if not path.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    try:
        # Scan organized folder structure
        topics = {}

        for topic_folder in path.iterdir():
            if topic_folder.is_dir() and not topic_folder.name.startswith('.'):
                papers = []

                for pdf_file in topic_folder.glob("*.pdf"):
                    # Extract info from filename: [Year] Title - Author.pdf
                    import re
                    match = re.match(r'\[(\d+)\]\s+(.+?)\s+-\s+(.+)\.pdf', pdf_file.name)

                    if match:
                        year, title, author = match.groups()
                        papers.append({
                            'title': title,
                            'authors': [author],
                            'year': int(year),
                            'path': str(pdf_file)
                        })
                    else:
                        papers.append({
                            'title': pdf_file.stem,
                            'path': str(pdf_file)
                        })

                if papers:
                    topics[topic_folder.name] = papers

        return {
            'folder': str(path),
            'topics': topics,
            'total_papers': sum(len(papers) for papers in topics.values())
        }

    except Exception as e:
        logger.error(f"Error reading folder structure: {e}")
        raise HTTPException(status_code=500, detail=str(e))
