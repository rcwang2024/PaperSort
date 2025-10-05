"""
Pydantic models for API request/response schemas
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Document types for papers"""
    ARTICLE = "article"
    INPROCEEDINGS = "inproceedings"
    BOOK = "book"
    PHDTHESIS = "phdthesis"
    TECHREPORT = "techreport"
    MISC = "misc"


class PaperBase(BaseModel):
    """Base paper model"""
    title: str
    authors: List[str] = []
    abstract: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    keywords: List[str] = []
    document_type: DocumentType = DocumentType.ARTICLE


class PaperCreate(PaperBase):
    """Model for creating a new paper"""
    file_path: str


class PaperUpdate(BaseModel):
    """Model for updating paper metadata"""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    keywords: Optional[List[str]] = None
    note: Optional[str] = None
    tags: Optional[List[str]] = None


class PaperResponse(PaperBase):
    """Model for paper response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    file_hash: str
    added_date: datetime
    last_modified: datetime
    tags: List[str] = []
    note: Optional[str] = None


class PaperSearchRequest(BaseModel):
    """Model for paper search request"""
    query: str
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class ClassificationRequest(BaseModel):
    """Model for paper classification request"""
    paper_ids: Optional[List[int]] = None  # None = all papers
    topics: Optional[List[str]] = None  # None = auto-detect
    num_topics: Optional[int] = Field(default=None, ge=2, le=20)
    use_cache: bool = True


class ClassificationResponse(BaseModel):
    """Model for classification response"""
    topics: Dict[str, List[int]]  # topic_name -> [paper_ids]
    processing_time: float
    cached: bool = False


class MindMapRequest(BaseModel):
    """Model for mind-map generation request"""
    paper_id: Optional[int] = None
    paper_title: Optional[str] = None
    abstract: Optional[str] = None
    full_text: Optional[str] = None
    include_methodology: bool = True
    include_results: bool = True
    include_contributions: bool = True
    max_depth: int = Field(default=3, ge=1, le=5)


class MindMapNode(BaseModel):
    """Model for mind-map node"""
    id: str
    label: str
    type: str  # root, section, subsection, item
    children: List['MindMapNode'] = []


class MindMapResponse(BaseModel):
    """Model for mind-map response"""
    paper_id: Optional[int] = None
    paper_title: str
    root_node: MindMapNode
    svg_data: Optional[str] = None
    summary: Optional[str] = None
    generation_time: float


class BibTeXExportRequest(BaseModel):
    """Model for BibTeX export request"""
    paper_ids: Optional[List[int]] = None  # None = all papers
    enhance_online: bool = True  # Query APIs for missing metadata
    validate_entries: bool = True  # Renamed from 'validate' to avoid shadowing
    format: str = "bibtex"  # bibtex, biblatex, ris


class BibTeXExportResponse(BaseModel):
    """Model for BibTeX export response"""
    content: str
    paper_count: int
    format: str
    enhanced_count: int = 0
    validation_errors: List[Dict[str, Any]] = []


class ProcessingProgress(BaseModel):
    """Model for processing progress updates"""
    task_id: str
    task_type: str  # pdf_processing, classification, export, etc.
    progress: float = Field(ge=0, le=100)
    current_item: Optional[str] = None
    total_items: int
    processed_items: int
    status: str  # pending, processing, completed, failed
    message: Optional[str] = None


class BatchProcessRequest(BaseModel):
    """Model for batch PDF processing request"""
    directory_path: str
    add_to_library: bool = True
    classify: bool = False
    topics: Optional[List[str]] = None


class BatchProcessResponse(BaseModel):
    """Model for batch processing response"""
    task_id: str
    total_files: int
    message: str


class APIError(BaseModel):
    """Model for API error responses"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None


class DatabaseStats(BaseModel):
    """Model for database statistics"""
    total_papers: int
    total_authors: int
    total_topics: int
    papers_by_year: Dict[int, int]
    papers_by_type: Dict[str, int]
    storage_size_mb: float
    last_updated: datetime
