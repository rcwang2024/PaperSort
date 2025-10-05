"""
Recommendation Service
Fetches recommended papers from arXiv and Semantic Scholar
"""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Optional
from urllib.parse import quote
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class RecommendationService:
    """Get paper recommendations from external sources"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_recommendations(
        self,
        topic: str,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Get recommended papers for a topic

        Args:
            topic: Research topic
            max_results: Maximum number of papers to return

        Returns:
            List of recommended papers with metadata
        """
        recommendations = []

        # Try arXiv first
        arxiv_papers = await self._query_arxiv(topic, max_results)
        recommendations.extend(arxiv_papers)

        # If not enough, try Semantic Scholar
        if len(recommendations) < max_results:
            remaining = max_results - len(recommendations)
            s2_papers = await self._query_semantic_scholar(topic, remaining)
            recommendations.extend(s2_papers)

        return recommendations[:max_results]

    async def _query_arxiv(self, topic: str, max_results: int) -> List[Dict]:
        """Query arXiv for recent papers on topic"""

        papers = []

        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30)
                )

            # Construct arXiv query
            query = f'all:"{topic}"'
            url = (
                f"http://export.arxiv.org/api/query?"
                f"search_query={quote(query)}&"
                f"start=0&"
                f"max_results={max_results}&"
                f"sortBy=submittedDate&"
                f"sortOrder=descending"
            )

            logger.info(f"Querying arXiv for: {topic}")

            async with self.session.get(url) as response:
                if response.status == 200:
                    xml_data = await response.text()
                    papers = self._parse_arxiv_response(xml_data)
                    logger.info(f"Found {len(papers)} papers on arXiv")

        except Exception as e:
            logger.error(f"arXiv query error: {e}")

        return papers

    def _parse_arxiv_response(self, xml_data: str) -> List[Dict]:
        """Parse arXiv XML response"""

        papers = []

        try:
            root = ET.fromstring(xml_data)
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }

            for entry in root.findall('atom:entry', ns):
                paper = {}

                # Title
                title_elem = entry.find('atom:title', ns)
                if title_elem is not None:
                    paper['title'] = title_elem.text.strip()

                # Authors
                authors = []
                for author in entry.findall('atom:author', ns):
                    name_elem = author.find('atom:name', ns)
                    if name_elem is not None:
                        authors.append(name_elem.text.strip())
                paper['authors'] = authors

                # Abstract
                summary_elem = entry.find('atom:summary', ns)
                if summary_elem is not None:
                    paper['abstract'] = summary_elem.text.strip()

                # Published date
                published_elem = entry.find('atom:published', ns)
                if published_elem is not None:
                    date_str = published_elem.text
                    # Extract year
                    import re
                    year_match = re.search(r'(\d{4})', date_str)
                    if year_match:
                        paper['year'] = int(year_match.group(1))

                # arXiv ID and URL
                id_elem = entry.find('atom:id', ns)
                if id_elem is not None:
                    arxiv_url = id_elem.text
                    paper['url'] = arxiv_url
                    paper['arxiv_id'] = arxiv_url.split('/')[-1]

                    # PDF URL
                    paper['pdf_url'] = f"https://arxiv.org/pdf/{paper['arxiv_id']}.pdf"

                # Categories
                categories = []
                for cat in entry.findall('atom:category', ns):
                    term = cat.get('term')
                    if term:
                        categories.append(term)
                paper['categories'] = categories
                paper['keywords'] = categories

                paper['document_type'] = 'article'
                paper['source'] = 'arXiv'

                if paper.get('title'):
                    papers.append(paper)

        except Exception as e:
            logger.error(f"Error parsing arXiv response: {e}")

        return papers

    async def _query_semantic_scholar(
        self,
        topic: str,
        max_results: int
    ) -> List[Dict]:
        """Query Semantic Scholar for papers"""

        papers = []

        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30)
                )

            url = (
                f"https://api.semanticscholar.org/graph/v1/paper/search?"
                f"query={quote(topic)}&"
                f"limit={max_results}&"
                f"fields=title,authors,year,abstract,venue,citationCount,url,externalIds"
            )

            logger.info(f"Querying Semantic Scholar for: {topic}")

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'data' in data:
                        for item in data['data']:
                            paper = {
                                'title': item.get('title'),
                                'authors': [a['name'] for a in item.get('authors', [])],
                                'year': item.get('year'),
                                'abstract': item.get('abstract'),
                                'journal': item.get('venue'),
                                'url': item.get('url'),
                                'document_type': 'article',
                                'source': 'Semantic Scholar'
                            }

                            # Extract DOI if available
                            ext_ids = item.get('externalIds', {})
                            if 'DOI' in ext_ids:
                                paper['doi'] = ext_ids['DOI']
                            if 'ArXiv' in ext_ids:
                                paper['arxiv_id'] = ext_ids['ArXiv']
                                paper['pdf_url'] = f"https://arxiv.org/pdf/{paper['arxiv_id']}.pdf"

                            if paper['title']:
                                papers.append(paper)

                        logger.info(f"Found {len(papers)} papers on Semantic Scholar")

        except Exception as e:
            logger.error(f"Semantic Scholar query error: {e}")

        return papers

    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
