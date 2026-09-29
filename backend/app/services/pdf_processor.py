"""
Parallel PDF processing with multiprocessing
High-performance PDF metadata extraction
"""

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
import hashlib
import json

import fitz  # PyMuPDF
import PyPDF2
import re

logger = logging.getLogger(__name__)


def extract_pdf_metadata_worker(pdf_path: str) -> Dict[str, Any]:
    """
    Worker function for parallel processing (must be at module level for pickling)
    Extracts metadata from a single PDF file
    """
    try:
        pdf_path = Path(pdf_path)
        metadata = {
            'file_path': str(pdf_path),
            'file_name': pdf_path.name,
            'title': '',
            'authors': [],
            'abstract': '',
            'year': None,
            'doi': None,
            'full_text': '',
            'pages': 0
        }

        # Try PyMuPDF first (fastest)
        try:
            doc = fitz.open(pdf_path)
            metadata['pages'] = len(doc)

            # Extract metadata
            pdf_metadata = doc.metadata
            if pdf_metadata.get('title'):
                metadata['title'] = pdf_metadata['title'].strip()
            if pdf_metadata.get('author'):
                authors = pdf_metadata['author'].split(',')
                metadata['authors'] = [a.strip() for a in authors if a.strip()]

            # Extract text from first few pages for analysis
            text_parts = []
            for page_num in range(min(5, len(doc))):  # First 5 pages
                page = doc[page_num]
                text_parts.append(page.get_text())

            first_pages_text = '\n'.join(text_parts)

            # Extract full text (limited to first 50 pages for performance)
            full_text_parts = []
            for page_num in range(min(50, len(doc))):
                page = doc[page_num]
                full_text_parts.append(page.get_text())
            metadata['full_text'] = '\n'.join(full_text_parts)

            doc.close()

        except Exception as e:
            logger.warning(f"PyMuPDF failed for {pdf_path.name}: {e}, trying PyPDF2")
            first_pages_text = ""

        # Extract title from first page if not in metadata
        if not metadata['title'] and first_pages_text:
            title = extract_title_from_text(first_pages_text)
            if title:
                metadata['title'] = title

        # Extract abstract
        if first_pages_text:
            abstract = extract_abstract_from_text(first_pages_text)
            if abstract:
                metadata['abstract'] = abstract

        # Extract DOI
        if first_pages_text:
            doi = extract_doi_from_text(first_pages_text)
            if doi:
                metadata['doi'] = doi

        # Extract year
        if first_pages_text:
            year = extract_year_from_text(first_pages_text)
            if year:
                metadata['year'] = year

        # Extract authors if not found
        if not metadata['authors'] and first_pages_text:
            authors = extract_authors_from_text(first_pages_text)
            if authors:
                metadata['authors'] = authors

        # Fallback: use filename as title if still empty
        if not metadata['title']:
            metadata['title'] = pdf_path.stem.replace('_', ' ').replace('-', ' ')

        return metadata

    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {e}")
        return {
            'file_path': str(pdf_path),
            'file_name': pdf_path.name,
            'title': pdf_path.stem,
            'error': str(e)
        }


def extract_title_from_text(text: str) -> Optional[str]:
    """Extract paper title from text"""
    lines = text.split('\n')
    # Look for title in first 20 lines
    for i, line in enumerate(lines[:20]):
        line = line.strip()
        # Title is usually one of the first non-empty lines with reasonable length
        if 20 < len(line) < 300 and not line.isupper():
            # Check if it looks like a title (not a header/footer)
            if not re.match(r'^\d+$', line) and not re.match(r'^page\s+\d+', line.lower()):
                return line
    return None


def extract_abstract_from_text(text: str) -> Optional[str]:
    """Extract abstract from text - improved robustness"""

    # Multiple patterns to catch different abstract formats
    patterns = [
        # Standard: "Abstract" followed by text
        r'(?:abstract|ABSTRACT)[:\s\n]+(.*?)(?:\n\n\n|\nIntroduction|\n1\.|1\s+Introduction|\nKeywords:)',
        # With header: "Abstract" on its own line
        r'(?:abstract|ABSTRACT)\s*\n+(.*?)(?:\n\n\n|\nIntroduction|\n1\.|1\s+Introduction|\nKeywords:)',
        # Summary variant
        r'(?:summary|SUMMARY)[:\s\n]+(.*?)(?:\n\n|\nIntroduction|\n1\.)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text[:5000], re.IGNORECASE | re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            # Clean up: remove extra whitespace and newlines
            abstract = re.sub(r'\s+', ' ', abstract)
            abstract = re.sub(r'\n+', ' ', abstract)
            # Remove page numbers and other artifacts
            abstract = re.sub(r'\d+\s*$', '', abstract)

            # Validate: should be at least 50 chars and less than 2000
            if 50 < len(abstract) < 2000:
                return abstract

    return None


def extract_doi_from_text(text: str) -> Optional[str]:
    """Extract DOI from text"""
    doi_pattern = r'(?:doi|DOI)[:\s]*(10\.\d{4,}/[^\s]+)'
    match = re.search(doi_pattern, text)
    if match:
        doi = match.group(1).strip()
        # Clean up
        doi = doi.rstrip('.,;')
        return doi
    return None


def extract_year_from_text(text: str) -> Optional[int]:
    """Extract publication year from text"""
    # Look for year patterns (1900-2099)
    year_patterns = [
        r'\b(19\d{2}|20\d{2})\b',  # Standard year
        r'©\s*(19\d{2}|20\d{2})',   # Copyright year
    ]

    first_page = '\n'.join(text.split('\n')[:50])  # First page only

    for pattern in year_patterns:
        matches = re.findall(pattern, first_page)
        if matches:
            # Return most recent valid year
            years = [int(y) for y in matches if 1900 <= int(y) <= 2099]
            if years:
                return max(years)
    return None


def extract_authors_from_text(text: str) -> List[str]:
    """Extract author names from text"""
    # This is a simplified extraction - real implementation would be more sophisticated
    lines = text.split('\n')

    # Look for author lines (usually after title, before abstract)
    for i, line in enumerate(lines[:30]):
        line = line.strip()
        # Check if line looks like author names
        if re.match(r'^[A-Z][a-z]+\s+[A-Z]', line):
            # Split by common separators
            authors = re.split(r'[,;]|\sand\s', line)
            authors = [a.strip() for a in authors if a.strip() and len(a.strip()) > 3]
            if 1 <= len(authors) <= 10:  # Reasonable number of authors
                return authors

    return []


class ParallelPDFProcessor:
    """High-performance parallel PDF processor"""

    def __init__(self, max_workers: int = 4):
        """
        Initialize processor

        Args:
            max_workers: Number of parallel processes (default: 4)
        """
        self.max_workers = max_workers
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        logger.info(f"Initialized PDF processor with {max_workers} workers")

    async def process_batch(
        self,
        pdf_paths: List[Path],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple PDFs in parallel

        Args:
            pdf_paths: List of PDF file paths
            progress_callback: Callback(processed, total, current_file)

        Returns:
            List of metadata dictionaries
        """
        total = len(pdf_paths)
        results = []

        logger.info(f"Processing {total} PDFs with {self.max_workers} workers")

        # Submit all tasks to executor
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(
                self.executor,
                extract_pdf_metadata_worker,
                str(pdf_path)
            )
            for pdf_path in pdf_paths
        ]

        # Process results as they complete
        for i, future in enumerate(asyncio.as_completed(futures)):
            try:
                result = await future
                results.append(result)

                if progress_callback:
                    progress_callback(i + 1, total, result.get('file_name', ''))

            except Exception as e:
                logger.error(f"Error in batch processing: {e}")
                results.append({'error': str(e)})

        logger.info(f"Completed processing {len(results)} PDFs")
        return results

    async def process_single(self, pdf_path: Path) -> Dict[str, Any]:
        """Process a single PDF asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            extract_pdf_metadata_worker,
            str(pdf_path)
        )

    def shutdown(self):
        """Shutdown the executor"""
        self.executor.shutdown(wait=True)
        logger.info("PDF processor shut down")


class EnhancedPDFExtractor:
    """Enhanced PDF extractor with metadata extraction"""

    def __init__(self):
        self.processor = ParallelPDFProcessor()

    async def extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract enhanced metadata from PDF"""
        return await self.processor.process_single(pdf_path)

    async def extract_batch(
        self,
        pdf_paths: List[Path],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """Extract metadata from multiple PDFs"""
        return await self.processor.process_batch(pdf_paths, progress_callback)

    def shutdown(self):
        """Cleanup resources"""
        self.processor.shutdown()
