"""
Database manager with async support and full-text search
"""

import aiosqlite
import sqlite3
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Async database manager with FTS5 full-text search"""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Use default path in user's home directory
            home = Path.home()
            db_dir = home / ".papersort"
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / "papersort_v2.db"

        self.db_path = str(db_path)
        self.connection: Optional[aiosqlite.Connection] = None
        logger.info(f"Database initialized at: {self.db_path}")

    async def initialize(self):
        """Initialize database and create tables"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row

        await self._create_tables()
        await self._create_indexes()
        logger.info("Database tables and indexes created")

    async def _create_tables(self):
        """Create database tables"""
        await self.connection.executescript('''
            -- Main papers table
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                authors TEXT,  -- JSON array
                abstract TEXT,
                year INTEGER,
                month INTEGER,
                journal TEXT,
                conference TEXT,
                volume TEXT,
                number TEXT,
                pages TEXT,
                doi TEXT,
                arxiv_id TEXT,
                pmid TEXT,
                url TEXT,
                isbn TEXT,
                issn TEXT,
                publisher TEXT,
                document_type TEXT DEFAULT 'article',
                keywords TEXT,  -- JSON array
                categories TEXT,  -- JSON array
                tags TEXT,  -- JSON array
                file_path TEXT NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                full_text TEXT,
                note TEXT,
                language TEXT DEFAULT 'english',
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Full-text search table using FTS5
            CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
                title, authors, abstract, full_text, keywords,
                content='papers',
                content_rowid='id'
            );

            -- Triggers to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS papers_ai AFTER INSERT ON papers BEGIN
                INSERT INTO papers_fts(rowid, title, authors, abstract, full_text, keywords)
                VALUES (new.id, new.title, new.authors, new.abstract, new.full_text, new.keywords);
            END;

            CREATE TRIGGER IF NOT EXISTS papers_ad AFTER DELETE ON papers BEGIN
                DELETE FROM papers_fts WHERE rowid = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS papers_au AFTER UPDATE ON papers BEGIN
                UPDATE papers_fts SET
                    title = new.title,
                    authors = new.authors,
                    abstract = new.abstract,
                    full_text = new.full_text,
                    keywords = new.keywords
                WHERE rowid = new.id;
            END;

            -- Collections table
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Paper-Collection mapping
            CREATE TABLE IF NOT EXISTS paper_collections (
                paper_id INTEGER NOT NULL,
                collection_id INTEGER NOT NULL,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (paper_id, collection_id),
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
                FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
            );

            -- Annotations table
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                page_number INTEGER,
                content TEXT,
                comment TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            );

            -- Metadata cache table
            CREATE TABLE IF NOT EXISTS metadata_cache (
                file_hash TEXT PRIMARY KEY,
                metadata TEXT NOT NULL,  -- JSON
                cached_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Classification cache table
            CREATE TABLE IF NOT EXISTS classification_cache (
                cache_key TEXT PRIMARY KEY,
                topics TEXT NOT NULL,  -- JSON
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_date TIMESTAMP
            );
        ''')
        await self.connection.commit()

    async def _create_indexes(self):
        """Create database indexes for performance"""
        await self.connection.executescript('''
            CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
            CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
            CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id);
            CREATE INDEX IF NOT EXISTS idx_papers_file_hash ON papers(file_hash);
            CREATE INDEX IF NOT EXISTS idx_papers_added_date ON papers(added_date DESC);
            CREATE INDEX IF NOT EXISTS idx_annotations_paper ON annotations(paper_id);
            CREATE INDEX IF NOT EXISTS idx_metadata_cache_date ON metadata_cache(cached_date);
        ''')
        await self.connection.commit()

    async def add_paper(self, metadata: Dict[str, Any], file_path: Path,
                       full_text: str = "") -> int:
        """Add paper to database"""
        file_hash = self._calculate_file_hash(file_path)

        cursor = await self.connection.execute('''
            INSERT INTO papers (
                title, authors, abstract, year, month, journal, conference,
                volume, number, pages, doi, arxiv_id, pmid, url, isbn, issn,
                publisher, document_type, keywords, categories, tags,
                file_path, file_hash, full_text, note, language
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.get('title', 'Untitled'),
            json.dumps(metadata.get('authors', [])),
            metadata.get('abstract'),
            metadata.get('year'),
            metadata.get('month'),
            metadata.get('journal'),
            metadata.get('conference'),
            metadata.get('volume'),
            metadata.get('number'),
            metadata.get('pages'),
            metadata.get('doi'),
            metadata.get('arxiv_id'),
            metadata.get('pmid'),
            metadata.get('url'),
            metadata.get('isbn'),
            metadata.get('issn'),
            metadata.get('publisher'),
            metadata.get('document_type', 'article'),
            json.dumps(metadata.get('keywords', [])),
            json.dumps(metadata.get('categories', [])),
            json.dumps(metadata.get('tags', [])),
            str(file_path),
            file_hash,
            full_text,
            metadata.get('note'),
            metadata.get('language', 'english')
        ))

        await self.connection.commit()
        return cursor.lastrowid

    async def get_paper(self, paper_id: int) -> Optional[Dict]:
        """Get paper by ID"""
        cursor = await self.connection.execute(
            'SELECT * FROM papers WHERE id = ?', (paper_id,)
        )
        row = await cursor.fetchone()

        if row:
            return self._row_to_dict(row)
        return None

    async def get_paper_by_hash(self, file_hash: str) -> Optional[int]:
        """Get paper ID by file hash"""
        cursor = await self.connection.execute(
            'SELECT id FROM papers WHERE file_hash = ?', (file_hash,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    async def search_papers(self, query: str, limit: int = 50,
                           offset: int = 0) -> List[Dict]:
        """Full-text search using FTS5"""
        cursor = await self.connection.execute('''
            SELECT p.* FROM papers p
            JOIN papers_fts ON p.id = papers_fts.rowid
            WHERE papers_fts MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?
        ''', (query, limit, offset))

        rows = await cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    async def get_all_papers(self, limit: int = 1000,
                            offset: int = 0) -> List[Dict]:
        """Get all papers with pagination"""
        cursor = await self.connection.execute('''
            SELECT * FROM papers
            ORDER BY added_date DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))

        rows = await cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    async def update_paper(self, paper_id: int, updates: Dict[str, Any]):
        """Update paper metadata"""
        set_clauses = []
        values = []

        for key, value in updates.items():
            if key in ['authors', 'keywords', 'categories', 'tags'] and isinstance(value, list):
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            values.append(value)

        set_clauses.append("last_modified = ?")
        values.append(datetime.now().isoformat())
        values.append(paper_id)

        query = f"UPDATE papers SET {', '.join(set_clauses)} WHERE id = ?"
        await self.connection.execute(query, values)
        await self.connection.commit()

    async def delete_paper(self, paper_id: int):
        """Delete paper from database"""
        await self.connection.execute('DELETE FROM papers WHERE id = ?', (paper_id,))
        await self.connection.commit()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}

        # Total papers
        cursor = await self.connection.execute('SELECT COUNT(*) FROM papers')
        stats['total_papers'] = (await cursor.fetchone())[0]

        # Papers by year
        cursor = await self.connection.execute('''
            SELECT year, COUNT(*) as count
            FROM papers
            WHERE year IS NOT NULL
            GROUP BY year
            ORDER BY year DESC
        ''')
        stats['papers_by_year'] = {row[0]: row[1] for row in await cursor.fetchall()}

        # Papers by type
        cursor = await self.connection.execute('''
            SELECT document_type, COUNT(*) as count
            FROM papers
            GROUP BY document_type
        ''')
        stats['papers_by_type'] = {row[0]: row[1] for row in await cursor.fetchall()}

        stats['last_updated'] = datetime.now().isoformat()

        return stats

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _row_to_dict(self, row) -> Dict:
        """Convert database row to dictionary"""
        paper = dict(row)

        # Parse JSON fields
        for field in ['authors', 'keywords', 'categories', 'tags']:
            if paper.get(field):
                try:
                    paper[field] = json.loads(paper[field])
                except json.JSONDecodeError:
                    paper[field] = []
            else:
                paper[field] = []

        return paper

    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Always release the connection -- an open aiosqlite connection keeps a
        # background thread alive (leaks in the server, hangs the test process)
        await self.close()
