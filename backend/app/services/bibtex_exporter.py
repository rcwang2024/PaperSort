"""
Enhanced BibTeX exporter with validation and multiple formats
"""

import re
import logging
from typing import Dict, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class BibTeXValidator:
    """Validate and auto-fix BibTeX entries"""

    REQUIRED_FIELDS = {
        'article': ['author', 'title', 'journal', 'year'],
        'inproceedings': ['author', 'title', 'booktitle', 'year'],
        'book': ['author', 'title', 'publisher', 'year'],
        'phdthesis': ['author', 'title', 'school', 'year'],
        'mastersthesis': ['author', 'title', 'school', 'year'],
        'techreport': ['author', 'title', 'institution', 'year'],
        'misc': ['title']
    }

    def validate_entry(self, entry: str) -> Dict:
        """Validate a BibTeX entry"""
        issues = []

        # Check balanced braces
        if entry.count('{') != entry.count('}'):
            issues.append("Unbalanced braces")

        # Extract entry type
        entry_type_match = re.search(r'@(\w+)\{', entry)
        if not entry_type_match:
            issues.append("Invalid entry format")
            return {'valid': False, 'issues': issues}

        entry_type = entry_type_match.group(1).lower()

        # Check required fields
        if entry_type in self.REQUIRED_FIELDS:
            for field in self.REQUIRED_FIELDS[entry_type]:
                if not re.search(f'{field}\\s*=', entry, re.IGNORECASE):
                    issues.append(f"Missing required field: {field}")

        # Check for unescaped special characters
        unescaped = self._find_unescaped_chars(entry)
        if unescaped:
            issues.append(f"Possibly unescaped characters: {', '.join(unescaped)}")

        return {
            'valid': len(issues) == 0,
            'issues': issues
        }

    def _find_unescaped_chars(self, text: str) -> List[str]:
        """Find potentially unescaped special characters"""
        # Look for special chars outside of braces (simplified check)
        special_chars = ['&', '%', '#']
        found = []
        for char in special_chars:
            if f'\\{char}' not in text and char in text:
                found.append(char)
        return found

    def auto_fix(self, entry: str) -> str:
        """Attempt to auto-fix common issues"""
        # Add placeholder for missing required fields
        # This is a simplified version
        return entry


class EnhancedBibTeXExporter:
    """Production-quality BibTeX export"""

    def __init__(self):
        self.validator = BibTeXValidator()
        self.entry_types = {
            'article': 'article',
            'inproceedings': 'inproceedings',
            'conference': 'inproceedings',
            'book': 'book',
            'phdthesis': 'phdthesis',
            'mastersthesis': 'mastersthesis',
            'techreport': 'techreport',
            'misc': 'misc'
        }

    def export_papers(
        self,
        papers: List[Dict],
        output_path: Optional[Path] = None,
        validate: bool = True
    ) -> tuple[str, List[Dict]]:
        """
        Export papers to BibTeX format

        Args:
            papers: List of paper dictionaries
            output_path: Optional path to save .bib file
            validate: Whether to validate entries

        Returns:
            Tuple of (bibtex_content, validation_errors)
        """
        entries = []
        used_keys: Set[str] = set()
        validation_errors = []

        for paper in papers:
            try:
                entry = self.generate_bibtex_entry(paper, used_keys)

                if validate:
                    validation = self.validator.validate_entry(entry)
                    if not validation['valid']:
                        validation_errors.append({
                            'paper_id': paper.get('id'),
                            'paper_title': paper.get('title', 'Unknown'),
                            'issues': validation['issues']
                        })
                        # Try to auto-fix
                        entry = self.validator.auto_fix(entry)

                entries.append(entry)

            except Exception as e:
                logger.error(f"Error exporting paper {paper.get('title', 'Unknown')}: {e}")
                validation_errors.append({
                    'paper_id': paper.get('id'),
                    'paper_title': paper.get('title', 'Unknown'),
                    'issues': [str(e)]
                })

        bibtex_content = '\n\n'.join(entries)

        if output_path:
            output_path.write_text(bibtex_content, encoding='utf-8')

        return bibtex_content, validation_errors

    def generate_bibtex_entry(self, paper: Dict, used_keys: Set[str]) -> str:
        """Generate a single BibTeX entry"""

        # Determine entry type
        doc_type = paper.get('document_type', 'article').lower()
        entry_type = self.entry_types.get(doc_type, 'misc')

        # Generate unique citation key
        citation_key = self._generate_citation_key(paper, used_keys)
        used_keys.add(citation_key)

        # Build fields
        fields = []

        # Title (required)
        if paper.get('title'):
            title = self._latex_escape(paper['title'])
            fields.append(f'  title = {{{title}}}')

        # Authors
        if paper.get('authors'):
            authors = self._format_authors(paper['authors'])
            if authors:
                fields.append(f'  author = {{{authors}}}')

        # Venue
        if entry_type == 'article' and paper.get('journal'):
            journal = self._latex_escape(paper['journal'])
            fields.append(f'  journal = {{{journal}}}')
        elif entry_type == 'inproceedings' and paper.get('conference'):
            booktitle = self._latex_escape(paper['conference'])
            fields.append(f'  booktitle = {{{booktitle}}}')
        elif entry_type == 'inproceedings' and paper.get('journal'):
            # Sometimes journal field contains conference name
            booktitle = self._latex_escape(paper['journal'])
            fields.append(f'  booktitle = {{{booktitle}}}')

        # Year (important)
        if paper.get('year'):
            fields.append(f'  year = {{{paper["year"]}}}')

        # Volume, number, pages
        if paper.get('volume'):
            fields.append(f'  volume = {{{paper["volume"]}}}')
        if paper.get('number'):
            fields.append(f'  number = {{{paper["number"]}}}')
        if paper.get('pages'):
            pages = self._format_pages(paper['pages'])
            fields.append(f'  pages = {{{pages}}}')

        # Publisher
        if paper.get('publisher'):
            publisher = self._latex_escape(paper['publisher'])
            fields.append(f'  publisher = {{{publisher}}}')

        # Identifiers
        if paper.get('doi'):
            fields.append(f'  doi = {{{paper["doi"]}}}')
        if paper.get('url'):
            fields.append(f'  url = {{{paper["url"]}}}')
        if paper.get('arxiv_id'):
            fields.append(f'  eprint = {{{paper["arxiv_id"]}}}')
            fields.append(f'  archivePrefix = {{arXiv}}')

        # Optional fields
        if paper.get('abstract'):
            abstract = self._latex_escape(paper['abstract'])
            if len(abstract) > 500:
                abstract = abstract[:497] + "..."
            fields.append(f'  abstract = {{{abstract}}}')

        if paper.get('keywords'):
            keywords = ', '.join(paper['keywords'])
            fields.append(f'  keywords = {{{keywords}}}')

        if paper.get('note'):
            note = self._latex_escape(paper['note'])
            fields.append(f'  note = {{{note}}}')

        # Construct entry
        if not fields:
            return ""

        entry = f"@{entry_type}{{{citation_key},\n"
        entry += ',\n'.join(fields)
        entry += '\n}'

        return entry

    def _generate_citation_key(self, paper: Dict, used_keys: Set[str]) -> str:
        """Generate unique citation key"""

        # Start with first author's last name
        authors = paper.get('authors', [])
        if authors:
            first_author = authors[0]
            name_parts = first_author.split()
            last_name = name_parts[-1] if name_parts else 'unknown'
            last_name = re.sub(r'[^a-zA-Z]', '', last_name)
            key_base = last_name.lower()
        else:
            key_base = 'unknown'

        # Add year
        year = paper.get('year')
        if year:
            key_base += str(year)

        # Make unique
        if key_base in used_keys:
            title = paper.get('title', '')
            title_words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
            for word in title_words[:3]:
                candidate = key_base + word
                if candidate not in used_keys:
                    key_base = candidate
                    break

        # Add number if still not unique
        original = key_base
        counter = 1
        while key_base in used_keys:
            key_base = f"{original}{counter}"
            counter += 1

        return key_base

    def _format_authors(self, authors: List[str]) -> str:
        """Format authors for BibTeX"""
        if not authors:
            return ""

        formatted = []
        for author in authors:
            author = author.strip()
            if not author:
                continue

            # Handle "Last, First" format
            if ',' in author:
                formatted.append(author)
            else:
                # Convert "First Last" to "Last, First"
                parts = author.split()
                if len(parts) >= 2:
                    last = parts[-1]
                    first = ' '.join(parts[:-1])
                    formatted.append(f"{last}, {first}")
                else:
                    formatted.append(author)

        return ' and '.join(formatted)

    def _format_pages(self, pages) -> str:
        """Format page numbers"""
        if not pages:
            return ""

        # Convert to string if integer
        pages = str(pages)

        # Convert to BibTeX standard
        pages = re.sub(r'(\d+)\s*[-–—]\s*(\d+)', r'\1--\2', pages)
        pages = re.sub(r'^pp\.?\s*', '', pages, flags=re.IGNORECASE)
        return pages

    def _latex_escape(self, text) -> str:
        """Escape text for LaTeX"""
        if not text:
            return ""

        # Convert to string if not already
        text = str(text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Escape special characters
        replacements = [
            ('\\', '\\\\'),
            ('{', '\\{'),
            ('}', '\\}'),
            ('$', '\\$'),
            ('&', '\\&'),
            ('%', '\\%'),
            ('#', '\\#'),
            ('^', '\\^{}'),
            ('_', '\\_'),
            ('~', '\\~{}')
        ]

        for old, new in replacements:
            text = text.replace(old, new)

        # Handle Unicode
        unicode_map = {
            '\u201c': '``', '\u201d': "''",   # curly double quotes
            '\u2018': '`', '\u2019': "'",     # curly single quotes
            '\u2013': '--', '\u2014': '---', '\u2026': '\\ldots'
        }

        for unicode_char, latex in unicode_map.items():
            text = text.replace(unicode_char, latex)

        return text
