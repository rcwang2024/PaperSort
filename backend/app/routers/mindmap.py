"""
Mind-map API router
Handles mind-map generation for papers
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import logging
import time

from app.models.schemas import MindMapRequest, MindMapResponse
from app.database.db import DatabaseManager
from app.services.mindmap_generator import PaperMindMapGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=MindMapResponse)
async def generate_mindmap(request: MindMapRequest):
    """Generate mind-map for a paper"""

    start_time = time.time()

    try:
        # Prioritize database lookup if paper_id is provided
        if request.paper_id is not None:
            async with DatabaseManager() as db:
                paper = await db.get_paper(request.paper_id)
            if not paper:
                raise HTTPException(status_code=404, detail="Paper not found")

            title = paper.get('title', 'Untitled')
            abstract = paper.get('abstract', '')
            full_text = paper.get('full_text', '')
        # Fallback to direct paper data (for organized papers not in database)
        elif request.paper_title:
            title = request.paper_title
            abstract = request.abstract or ''
            full_text = request.full_text or ''
        else:
            raise HTTPException(status_code=400, detail="Either paper_id or paper_title required")

        # Validate we have enough content
        total_text_length = len(title) + len(abstract) + len(full_text)
        if total_text_length < 100:
            raise HTTPException(
                status_code=400,
                detail="Insufficient text content for mind-map generation. PDF might be scanned image or empty."
            )

        logger.info(f"Generating mind-map for: {title[:50]}... (text length: {total_text_length})")

        # Generate mind-map
        generator = PaperMindMapGenerator()
        mindmap_data = await generator.generate_mindmap(
            paper_id=request.paper_id,
            paper_title=title,
            abstract=abstract,
            full_text=full_text,
            include_methodology=request.include_methodology,
            include_results=request.include_results,
            include_contributions=request.include_contributions,
            max_depth=request.max_depth
        )

        generation_time = time.time() - start_time

        return {
            'paper_id': request.paper_id,
            'paper_title': title,
            'root_node': mindmap_data['root_node'],
            'svg_data': mindmap_data.get('svg_data'),
            'summary': mindmap_data.get('summary', ''),
            'generation_time': generation_time
        }

    except HTTPException:
        # Deliberate 4xx/5xx responses raised above must not be turned into 500s
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Mind-map generation error: {error_msg}", exc_info=True)

        # Provide user-friendly error messages
        if "timeout" in error_msg.lower():
            detail = "Mind-map generation timed out. This paper might be too complex. Try again or contact support."
        elif "json" in error_msg.lower() or "parse" in error_msg.lower():
            detail = "Failed to parse AI response. The model might be overloaded. Please try again."
        elif "ollama" in error_msg.lower() or "connection" in error_msg.lower():
            detail = "Cannot connect to Ollama. Please ensure Ollama is running (http://localhost:11434)"
        elif "no text" in error_msg.lower() or "insufficient" in error_msg.lower():
            detail = "Could not extract enough text from this PDF. It might be a scanned image or corrupted."
        else:
            detail = f"Mind-map generation failed: {error_msg}"

        raise HTTPException(status_code=500, detail=detail)


@router.get("/{paper_id}/svg")
async def get_mindmap_svg(
    paper_id: int,
    include_methodology: bool = True,
    include_results: bool = True,
    include_contributions: bool = True
):
    """Get mind-map as SVG image"""

    try:
        async with DatabaseManager() as db:
            paper = await db.get_paper(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        title = paper.get('title', 'Untitled')
        abstract = paper.get('abstract', '')
        full_text = paper.get('full_text', '')

        # Generate mind-map
        generator = PaperMindMapGenerator()
        mindmap_data = await generator.generate_mindmap(
            paper_id=paper_id,
            paper_title=title,
            abstract=abstract,
            full_text=full_text,
            include_methodology=include_methodology,
            include_results=include_results,
            include_contributions=include_contributions
        )

        svg_data = mindmap_data.get('svg_data', '')
        if not svg_data:
            raise HTTPException(status_code=500, detail="Failed to generate SVG")

        return Response(content=svg_data, media_type="image/svg+xml")

    except HTTPException:
        # Deliberate 4xx/5xx responses raised above must not be turned into 500s
        raise
    except Exception as e:
        logger.error(f"SVG generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
