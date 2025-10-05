"""
API-enhanced metadata extraction
Queries external APIs (CrossRef, arXiv, Semantic Scholar) to enhance paper metadata
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Optional, List, Any
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)


class MetadataEnhancer:
    """Enhance paper metadata using external APIs"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache = {}  # Simple in-memory cache

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def enhance_metadata(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance paper metadata by querying external APIs

        Priority:
        1. DOI lookup via CrossRef (most reliable)
        2. arXiv ID lookup
        3. Title search on Semantic Scholar
        4. Title search on arXiv

        Args:
            paper: Paper metadata dictionary

        Returns:
            Enhanced metadata dictionary
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

        enhanced = paper.copy()

        try:
            # 1. Try DOI lookup
            if paper.get('doi'):
                logger.info(f"Querying CrossRef for DOI: {paper['doi']}")
                crossref_data = await self.query_crossref_doi(paper['doi'])
                if crossref_data:
                    enhanced = self.merge_metadata(enhanced, crossref_data)
                    logger.info("Successfully enhanced with CrossRef data")
                    return enhanced

            # 2. Try arXiv ID lookup
            if paper.get('arxiv_id'):
                logger.info(f"Querying arXiv for ID: {paper['arxiv_id']}")
                arxiv_data = await self.query_arxiv_id(paper['arxiv_id'])
                if arxiv_data:
                    enhanced = self.merge_metadata(enhanced, arxiv_data)
                    logger.info("Successfully enhanced with arXiv data")
                    return enhanced

            # 3. Try Semantic Scholar by title
            if paper.get('title') and len(paper['title']) > 10:
                logger.info(f"Querying Semantic Scholar for title: {paper['title'][:50]}...")
                s2_data = await self.query_semantic_scholar_title(paper['title'])
                if s2_data:
                    enhanced = self.merge_metadata(enhanced, s2_data)
                    logger.info("Successfully enhanced with Semantic Scholar data")
                    return enhanced

            # 4. Try arXiv by title
            if paper.get('title') and len(paper['title']) > 10:
                logger.info(f"Querying arXiv for title: {paper['title'][:50]}...")
                arxiv_data = await self.query_arxiv_title(paper['title'])
                if arxiv_data:
                    enhanced = self.merge_metadata(enhanced, arxiv_data)
                    logger.info("Successfully enhanced with arXiv data")
                    return enhanced

        except Exception as e:
            logger.error(f"Error enhancing metadata: {e}")

        return enhanced

    async def query_crossref_doi(self, doi: str) -> Optional[Dict]:
        """Query CrossRef API by DOI"""
        try:
            url = f"https://api.crossref.org/works/{doi}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_crossref_response(data)
        except Exception as e:
            logger.warning(f"CrossRef query failed: {e}")
        return None

    async def query_arxiv_id(self, arxiv_id: str) -> Optional[Dict]:
        """Query arXiv API by arXiv ID"""
        try:
            # Clean arXiv ID
            arxiv_id = arxiv_id.replace('arXiv:', '').strip()

            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    xml_data = await response.text()
                    return self._parse_arxiv_response(xml_data)
        except Exception as e:
            logger.warning(f"arXiv ID query failed: {e}")
        return None

    async def query_arxiv_title(self, title: str) -> Optional[Dict]:
        """Query arXiv API by title"""
        try:
            search_query = f'ti:"{title}"'
            url = f"http://export.arxiv.org/api/query?search_query={quote(search_query)}&max_results=1"

            async with self.session.get(url) as response:
                if response.status == 200:
                    xml_data = await response.text()
                    return self._parse_arxiv_response(xml_data)
        except Exception as e:
            logger.warning(f"arXiv title query failed: {e}")
        return None

    async def query_semantic_scholar_title(self, title: str) -> Optional[Dict]:
        """Query Semantic Scholar API by title"""
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote(title)}&limit=1&fields=title,authors,year,abstract,venue,citationCount,referenceCount,fieldsOfStudy,externalIds"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data') and len(data['data']) > 0:
                        return self._parse_semantic_scholar_response(data['data'][0])
        except Exception as e:
            logger.warning(f"Semantic Scholar query failed: {e}")
        return None

    def _parse_crossref_response(self, data: Dict) -> Dict:
        """Parse CrossRef API response"""
        if 'message' not in data:
            return {}

        message = data['message']
        metadata = {}

        # Title
        if 'title' in message and message['title']:
            metadata['title'] = message['title'][0]

        # Authors
        if 'author' in message:
            authors = []
            for author in message['author']:
                name_parts = []
                if 'given' in author:
                    name_parts.append(author['given'])
                if 'family' in author:
                    name_parts.append(author['family'])
                if name_parts:
                    authors.append(' '.join(name_parts))
            metadata['authors'] = authors

        # Year
        if 'published' in message:
            date_parts = message['published'].get('date-parts', [[]])
            if date_parts and date_parts[0]:
                metadata['year'] = date_parts[0][0]

        # Journal
        if 'container-title' in message and message['container-title']:
            metadata['journal'] = message['container-title'][0]

        # Volume, issue, pages
        if 'volume' in message:
            metadata['volume'] = message['volume']
        if 'issue' in message:
            metadata['number'] = message['issue']
        if 'page' in message:
            metadata['pages'] = message['page']

        # Publisher
        if 'publisher' in message:
            metadata['publisher'] = message['publisher']

        # DOI
        if 'DOI' in message:
            metadata['doi'] = message['DOI']

        # URL
        if 'URL' in message:
            metadata['url'] = message['URL']

        # Type
        if 'type' in message:
            type_map = {
                'journal-article': 'article',
                'proceedings-article': 'inproceedings',
                'book': 'book',
                'book-chapter': 'incollection'
            }
            metadata['document_type'] = type_map.get(message['type'], 'article')

        return metadata

    def _parse_arxiv_response(self, xml_data: str) -> Dict:
        """Parse arXiv API response (XML)"""
        import xml.etree.ElementTree as ET

        metadata = {}

        try:
            root = ET.fromstring(xml_data)
            ns = {'atom': 'http://www.w3.org/2005/Atom',
                  'arxiv': 'http://arxiv.org/schemas/atom'}

            entry = root.find('atom:entry', ns)
            if entry is None:
                return {}

            # Title
            title_elem = entry.find('atom:title', ns)
            if title_elem is not None:
                metadata['title'] = title_elem.text.strip()

            # Authors
            authors = []
            for author in entry.findall('atom:author', ns):
                name_elem = author.find('atom:name', ns)
                if name_elem is not None:
                    authors.append(name_elem.text.strip())
            metadata['authors'] = authors

            # Abstract
            summary_elem = entry.find('atom:summary', ns)
            if summary_elem is not None:
                metadata['abstract'] = summary_elem.text.strip()

            # Published date
            published_elem = entry.find('atom:published', ns)
            if published_elem is not None:
                date_str = published_elem.text
                year_match = re.search(r'(\d{4})', date_str)
                if year_match:
                    metadata['year'] = int(year_match.group(1))

            # arXiv ID
            id_elem = entry.find('atom:id', ns)
            if id_elem is not None:
                arxiv_url = id_elem.text
                arxiv_id = arxiv_url.split('/')[-1]
                metadata['arxiv_id'] = arxiv_id
                metadata['url'] = arxiv_url

            # Categories
            categories = []
            for cat in entry.findall('atom:category', ns):
                term = cat.get('term')
                if term:
                    categories.append(term)
            metadata['categories'] = categories

            # DOI (if available)
            doi_elem = entry.find('arxiv:doi', ns)
            if doi_elem is not None:
                metadata['doi'] = doi_elem.text.strip()

            metadata['document_type'] = 'article'

        except Exception as e:
            logger.error(f"Error parsing arXiv response: {e}")

        return metadata

    def _parse_semantic_scholar_response(self, data: Dict) -> Dict:
        """Parse Semantic Scholar API response"""
        metadata = {}

        if 'title' in data:
            metadata['title'] = data['title']

        if 'authors' in data:
            metadata['authors'] = [author['name'] for author in data['authors']]

        if 'year' in data:
            metadata['year'] = data['year']

        if 'abstract' in data:
            metadata['abstract'] = data['abstract']

        if 'venue' in data:
            metadata['journal'] = data['venue']

        if 'externalIds' in data:
            ext_ids = data['externalIds']
            if 'DOI' in ext_ids:
                metadata['doi'] = ext_ids['DOI']
            if 'ArXiv' in ext_ids:
                metadata['arxiv_id'] = ext_ids['ArXiv']

        if 'fieldsOfStudy' in data:
            metadata['keywords'] = data['fieldsOfStudy']

        metadata['document_type'] = 'article'

        return metadata

    def merge_metadata(self, original: Dict, new: Dict) -> Dict:
        """
        Merge new metadata with original, preferring non-empty values

        Priority: new data fills in missing fields, doesn't overwrite
        """
        merged = original.copy()

        for key, value in new.items():
            # Skip if value is empty
            if not value:
                continue

            # If original doesn't have this field or it's empty, use new value
            if key not in merged or not merged[key]:
                merged[key] = value
            # For lists, merge and deduplicate
            elif isinstance(value, list) and isinstance(merged[key], list):
                merged[key] = list(set(merged[key] + value))
            # For strings, prefer longer/more complete version
            elif isinstance(value, str) and isinstance(merged[key], str):
                if len(value) > len(merged[key]):
                    merged[key] = value

        return merged
