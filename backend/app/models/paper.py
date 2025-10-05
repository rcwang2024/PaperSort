"""
Data models for papers and related entities
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class Paper:
    """Paper data model"""
    id: Optional[int] = None
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    journal: Optional[str] = None
    conference: Optional[str] = None
    volume: Optional[str] = None
    number: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    isbn: Optional[str] = None
    issn: Optional[str] = None
    publisher: Optional[str] = None
    document_type: str = "article"
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    full_text: Optional[str] = None
    note: Optional[str] = None
    language: str = "english"
    added_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'year': self.year,
            'month': self.month,
            'journal': self.journal,
            'conference': self.conference,
            'volume': self.volume,
            'number': self.number,
            'pages': self.pages,
            'doi': self.doi,
            'arxiv_id': self.arxiv_id,
            'pmid': self.pmid,
            'url': self.url,
            'isbn': self.isbn,
            'issn': self.issn,
            'publisher': self.publisher,
            'document_type': self.document_type,
            'keywords': self.keywords,
            'categories': self.categories,
            'tags': self.tags,
            'file_path': self.file_path,
            'file_hash': self.file_hash,
            'note': self.note,
            'language': self.language,
            'added_date': self.added_date,
            'last_modified': self.last_modified
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Paper':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class Collection:
    """Collection of papers"""
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    created_date: Optional[datetime] = None
    paper_count: int = 0


@dataclass
class Annotation:
    """Paper annotation"""
    id: Optional[int] = None
    paper_id: int = 0
    type: str = "highlight"  # highlight, note, bookmark
    page_number: int = 1
    content: str = ""
    comment: Optional[str] = None
    created_date: Optional[datetime] = None


@dataclass
class MindMapNode:
    """Node in a mind-map"""
    id: str
    label: str
    node_type: str  # root, section, subsection, item, technique, result
    content: Optional[str] = None
    children: List['MindMapNode'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'label': self.label,
            'type': self.node_type,
            'content': self.content,
            'children': [child.to_dict() for child in self.children],
            'metadata': self.metadata
        }
