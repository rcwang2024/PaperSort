"""
Shared pytest fixtures and configuration
"""

import pytest
import asyncio
from pathlib import Path
from httpx import AsyncClient
from typing import AsyncGenerator
import tempfile
import shutil

from app.main import app
from app.database.db import DatabaseManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Create a test database instance"""
    db = DatabaseManager(db_path=":memory:")  # Use in-memory SQLite for tests
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def temp_folder():
    """Create a temporary folder for testing"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_pdf_path(temp_folder):
    """Create a sample PDF file for testing"""
    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Paper) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF"""

    pdf_path = temp_folder / "test_paper.pdf"
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def sample_papers_folder(temp_folder):
    """Create a folder with multiple sample PDFs"""
    papers_folder = temp_folder / "papers"
    papers_folder.mkdir()

    # Create multiple test PDFs
    for i in range(3):
        pdf_path = papers_folder / f"paper_{i+1}.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%Test PDF")

    return papers_folder


@pytest.fixture
def mock_paper_metadata():
    """Mock paper metadata for testing"""
    return {
        "title": "Test Paper: Machine Learning Approaches",
        "authors": ["John Doe", "Jane Smith"],
        "year": 2024,
        "abstract": "This is a test abstract about machine learning and neural networks.",
        "keywords": ["machine learning", "neural networks", "AI"],
        "venue": "Test Conference 2024",
        "doi": "10.1234/test.2024.001"
    }


@pytest.fixture
def mock_mindmap_request():
    """Mock mindmap generation request"""
    return {
        "paper_title": "Test Paper on Neural Networks",
        "abstract": "This paper explores deep learning architectures for computer vision tasks.",
        "full_text": "Introduction: Deep learning has revolutionized computer vision...",
        "include_methodology": True,
        "include_results": True,
        "include_contributions": True,
        "max_depth": 3
    }
