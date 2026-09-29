"""
Export API router
Handles BibTeX and other export formats
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import logging
from pathlib import Path

from app.models.schemas import BibTeXExportRequest, BibTeXExportResponse
from app.database.db import DatabaseManager
from app.services.bibtex_exporter import EnhancedBibTeXExporter
from app.services.api_enhancer import MetadataEnhancer

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/bibtex", response_model=BibTeXExportResponse)
async def export_bibtex(request: BibTeXExportRequest):
    """Export papers to BibTeX format"""

    try:
        # Get papers
        async with DatabaseManager() as db:
            if request.paper_ids:
                papers = []
                for paper_id in request.paper_ids:
                    paper = await db.get_paper(paper_id)
                    if paper:
                        papers.append(paper)
            else:
                papers = await db.get_all_papers(limit=10000)

        if not papers:
            raise HTTPException(status_code=400, detail="No papers found to export")

        # Enhance metadata if requested
        enhanced_count = 0
        if request.enhance_online:
            logger.info(f"Enhancing metadata for {len(papers)} papers...")
            async with MetadataEnhancer() as enhancer:
                enhanced_papers = []
                for paper in papers:
                    enhanced = await enhancer.enhance_metadata(paper)
                    enhanced_papers.append(enhanced)
                    if enhanced != paper:
                        enhanced_count += 1
                papers = enhanced_papers

        # Export to BibTeX
        exporter = EnhancedBibTeXExporter()
        bibtex_content, validation_errors = exporter.export_papers(
            papers,
            validate=request.validate_entries
        )

        return {
            'content': bibtex_content,
            'paper_count': len(papers),
            'format': request.format,
            'enhanced_count': enhanced_count,
            'validation_errors': validation_errors
        }

    except HTTPException:
        # Deliberate 4xx/5xx responses raised above must not be turned into 500s
        raise
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bibtex/download")
async def download_bibtex(paper_ids: str = None, enhance: bool = False):
    """Download BibTeX file"""

    try:
        # Parse paper IDs if provided
        async with DatabaseManager() as db:
            if paper_ids:
                ids = [int(id.strip()) for id in paper_ids.split(',') if id.strip()]
                papers = []
                for paper_id in ids:
                    paper = await db.get_paper(paper_id)
                    if paper:
                        papers.append(paper)
            else:
                papers = await db.get_all_papers(limit=10000)

        if not papers:
            raise HTTPException(status_code=400, detail="No papers found")

        # Enhance if requested
        if enhance:
            async with MetadataEnhancer() as enhancer:
                enhanced_papers = []
                for paper in papers:
                    enhanced = await enhancer.enhance_metadata(paper)
                    enhanced_papers.append(enhanced)
                papers = enhanced_papers

        # Export
        exporter = EnhancedBibTeXExporter()
        bibtex_content, _ = exporter.export_papers(papers)

        # Return as downloadable file
        return Response(
            content=bibtex_content,
            media_type="application/x-bibtex",
            headers={
                "Content-Disposition": "attachment; filename=references.bib"
            }
        )

    except HTTPException:
        # Deliberate 4xx/5xx responses raised above must not be turned into 500s
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
