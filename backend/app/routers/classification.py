"""
Classification API router
Handles paper classification operations
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
import time

from app.models.schemas import ClassificationRequest, ClassificationResponse
from app.database.db import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/classify", response_model=ClassificationResponse)
async def classify_papers(request: ClassificationRequest):
    """
    Classify papers into topics

    Args:
        request: Classification request with paper IDs and options

    Returns:
        Classification results with topics and paper assignments
    """

    start_time = time.time()

    try:
        db = DatabaseManager()
        await db.initialize()

        # Get papers to classify
        if request.paper_ids:
            papers = []
            for paper_id in request.paper_ids:
                paper = await db.get_paper(paper_id)
                if paper:
                    papers.append(paper)
        else:
            papers = await db.get_all_papers(limit=10000)

        if not papers:
            await db.close()
            raise HTTPException(status_code=400, detail="No papers found to classify")

        # TODO: Implement actual classification using enhanced_classifier
        # For now, return mock results
        topics = {}

        if request.topics:
            # Custom topics
            for topic in request.topics:
                topics[topic] = []

            # Distribute papers (mock)
            for i, paper in enumerate(papers):
                topic = request.topics[i % len(request.topics)]
                topics[topic].append(paper['id'])
        else:
            # Auto-detect topics (mock)
            topics = {
                "Machine Learning": [p['id'] for p in papers[::3]],
                "Computer Vision": [p['id'] for p in papers[1::3]],
                "Natural Language Processing": [p['id'] for p in papers[2::3]]
            }

        await db.close()

        processing_time = time.time() - start_time

        return {
            'topics': topics,
            'processing_time': processing_time,
            'cached': False
        }

    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
