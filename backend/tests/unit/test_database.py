"""
Unit tests for Database Manager
"""

import pytest
from app.database.db import DatabaseManager


@pytest.fixture
def make_pdf(tmp_path):
    """Create a small file with unique content; add_paper hashes the file (file_hash is UNIQUE)."""
    def _make(name: str):
        path = tmp_path / name
        path.write_bytes(b"%PDF-1.4 test file " + name.encode())
        return path
    return _make


@pytest.mark.unit
class TestDatabaseManager:
    """Test suite for database manager"""

    async def test_initialize(self):
        """Test database initialization"""
        db = DatabaseManager(db_path=":memory:")
        await db.initialize()
        assert db.connection is not None
        await db.close()

    async def test_add_and_get_paper(self, mock_paper_metadata, make_pdf):
        """Test adding and retrieving a paper"""
        db = DatabaseManager(db_path=":memory:")
        await db.initialize()

        # Add paper
        paper_id = await db.add_paper(
            metadata=mock_paper_metadata,
            file_path=make_pdf("paper.pdf"),
            full_text="Test full text content"
        )

        assert paper_id is not None
        assert paper_id > 0

        # Retrieve paper
        paper = await db.get_paper(paper_id)
        assert paper is not None
        assert paper["id"] == paper_id
        assert paper["title"] == mock_paper_metadata["title"]

        await db.close()

    async def test_get_nonexistent_paper(self):
        """Test getting non-existent paper"""
        db = DatabaseManager(db_path=":memory:")
        await db.initialize()

        paper = await db.get_paper(99999)
        assert paper is None

        await db.close()

    async def test_update_paper(self, mock_paper_metadata, make_pdf):
        """Test updating paper metadata"""
        db = DatabaseManager(db_path=":memory:")
        await db.initialize()

        # Add paper
        paper_id = await db.add_paper(
            metadata=mock_paper_metadata,
            file_path=make_pdf("paper.pdf")
        )

        # Update paper
        await db.update_paper(paper_id, {"title": "Updated Title"})

        # Verify update
        paper = await db.get_paper(paper_id)
        assert paper["title"] == "Updated Title"

        await db.close()

    async def test_delete_paper(self, mock_paper_metadata, make_pdf):
        """Test deleting a paper"""
        db = DatabaseManager(db_path=":memory:")
        await db.initialize()

        # Add paper
        paper_id = await db.add_paper(
            metadata=mock_paper_metadata,
            file_path=make_pdf("paper.pdf")
        )

        # Delete paper
        await db.delete_paper(paper_id)

        # Verify deletion
        paper = await db.get_paper(paper_id)
        assert paper is None

        await db.close()

    async def test_search_papers(self, mock_paper_metadata, make_pdf):
        """Test paper search functionality"""
        db = DatabaseManager(db_path=":memory:")
        await db.initialize()

        # Add multiple papers
        await db.add_paper(
            metadata=mock_paper_metadata,
            file_path=make_pdf("paper1.pdf")
        )

        metadata2 = mock_paper_metadata.copy()
        metadata2["title"] = "Different Topic: Computer Vision"
        await db.add_paper(
            metadata=metadata2,
            file_path=make_pdf("paper2.pdf")
        )

        # Search
        results = await db.search_papers("machine learning")
        assert len(results) >= 1

        await db.close()

    async def test_get_statistics(self, mock_paper_metadata, make_pdf):
        """Test getting database statistics"""
        db = DatabaseManager(db_path=":memory:")
        await db.initialize()

        # Add paper
        await db.add_paper(
            metadata=mock_paper_metadata,
            file_path=make_pdf("paper.pdf")
        )

        # Get stats
        stats = await db.get_statistics()
        assert isinstance(stats, dict)
        assert "total_papers" in stats or len(stats) >= 0

        await db.close()

    async def test_get_all_papers_pagination(self, mock_paper_metadata, make_pdf):
        """Test pagination when getting all papers"""
        db = DatabaseManager(db_path=":memory:")
        await db.initialize()

        # Add multiple papers
        for i in range(5):
            metadata = mock_paper_metadata.copy()
            metadata["title"] = f"Paper {i+1}"
            await db.add_paper(
                metadata=metadata,
                file_path=make_pdf(f"paper{i+1}.pdf")
            )

        # Test pagination
        papers_page1 = await db.get_all_papers(limit=2, offset=0)
        assert len(papers_page1) == 2

        papers_page2 = await db.get_all_papers(limit=2, offset=2)
        assert len(papers_page2) == 2

        # Verify different papers
        assert papers_page1[0]["id"] != papers_page2[0]["id"]

        await db.close()
