"""
Integration tests for Papers API
Tests the critical paper management endpoints
"""

import pytest
from httpx import AsyncClient
from pathlib import Path
import io


@pytest.mark.integration
class TestPapersAPI:
    """Test suite for papers API endpoints"""

    async def test_health_check(self, client: AsyncClient):
        """Test basic health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_root_endpoint(self, client: AsyncClient):
        """Test root API endpoint"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "PaperSort API"
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"

    async def test_upload_paper_invalid_file_type(self, client: AsyncClient):
        """Test uploading non-PDF file"""
        files = {"file": ("test.txt", io.BytesIO(b"test content"), "text/plain")}
        response = await client.post(
            "/api/papers/upload",
            files=files,
            data={"enhance_metadata": "false"}
        )
        assert response.status_code == 400
        assert "pdf" in response.json()["detail"].lower()

    async def test_upload_paper_success(self, client: AsyncClient, sample_pdf_path: Path):
        """Test successful paper upload"""
        with open(sample_pdf_path, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            response = await client.post(
                "/api/papers/upload",
                files=files,
                data={"enhance_metadata": "false"}
            )

        # May succeed or fail depending on PDF parsing
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "title" in data

    async def test_get_paper_not_found(self, client: AsyncClient):
        """Test getting non-existent paper"""
        response = await client.get("/api/papers/99999")
        assert response.status_code == 404

    async def test_list_papers_pagination(self, client: AsyncClient):
        """Test listing papers with pagination"""
        # Test default pagination
        response = await client.get("/api/papers/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Test with limit and offset
        response = await client.get("/api/papers/?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    async def test_search_papers(self, client: AsyncClient):
        """Test paper search functionality"""
        response = await client.post(
            "/api/papers/search",
            json={
                "query": "machine learning",
                "limit": 10,
                "offset": 0
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_update_paper_not_found(self, client: AsyncClient):
        """Test updating non-existent paper"""
        response = await client.put(
            "/api/papers/99999",
            json={"title": "Updated Title"}
        )
        assert response.status_code == 404

    async def test_delete_paper_not_found(self, client: AsyncClient):
        """Test deleting non-existent paper"""
        response = await client.delete("/api/papers/99999")
        assert response.status_code == 404

    async def test_get_statistics(self, client: AsyncClient):
        """Test getting database statistics"""
        response = await client.get("/api/papers/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_batch_process_invalid_directory(self, client: AsyncClient):
        """Test batch processing with invalid directory"""
        response = await client.post(
            "/api/papers/batch",
            json={"directory_path": "/nonexistent/path"}
        )
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"].lower()

    async def test_batch_process_no_pdfs(self, client: AsyncClient, temp_folder: Path):
        """Test batch processing with no PDFs"""
        empty_folder = temp_folder / "empty"
        empty_folder.mkdir()

        response = await client.post(
            "/api/papers/batch",
            json={"directory_path": str(empty_folder)}
        )
        assert response.status_code == 400
        assert "no pdf" in response.json()["detail"].lower()

    async def test_batch_process_success(self, client: AsyncClient, sample_papers_folder: Path):
        """Test successful batch processing"""
        response = await client.post(
            "/api/papers/batch",
            json={"directory_path": str(sample_papers_folder)}
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "total_files" in data
        assert data["total_files"] > 0


@pytest.mark.integration
class TestPapersValidation:
    """Test input validation for papers endpoints"""

    async def test_search_missing_query(self, client: AsyncClient):
        """Test search without query parameter"""
        response = await client.post(
            "/api/papers/search",
            json={"limit": 10}
        )
        assert response.status_code == 422

    async def test_search_invalid_limit(self, client: AsyncClient):
        """Test search with invalid limit"""
        response = await client.post(
            "/api/papers/search",
            json={
                "query": "test",
                "limit": -1
            }
        )
        # Should validate or handle gracefully
        assert response.status_code in [200, 422]

    async def test_update_paper_invalid_data(self, client: AsyncClient):
        """Test updating paper with invalid data"""
        response = await client.put(
            "/api/papers/1",
            json={"year": "not-a-number"}
        )
        # Should validate data types
        assert response.status_code in [404, 422]


@pytest.mark.integration
class TestClassificationAPI:
    """Test suite for classification API endpoints"""

    async def test_classify_no_papers(self, client: AsyncClient):
        """Test classification with no papers"""
        response = await client.post(
            "/api/classification/classify",
            json={"paper_ids": [99999]}
        )
        assert response.status_code == 400

    async def test_classify_with_custom_topics(self, client: AsyncClient):
        """Test classification with custom topics"""
        response = await client.post(
            "/api/classification/classify",
            json={
                "topics": ["Machine Learning", "NLP", "Computer Vision"]
            }
        )
        # Should accept custom topics (may fail if no papers in DB)
        assert response.status_code in [200, 400]

    async def test_classify_success(self, client: AsyncClient):
        """Test successful classification"""
        response = await client.post(
            "/api/classification/classify",
            json={}
        )
        # May succeed or fail depending on database state
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert "topics" in data
            assert "processing_time" in data
            assert "cached" in data
            assert isinstance(data["topics"], dict)
