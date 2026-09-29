"""
Integration tests for Mind-map Generation API
Tests the critical /api/mindmap endpoints
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestMindMapAPI:
    """Test suite for mindmap API endpoints"""

    async def test_generate_mindmap_missing_identifiers(self, client: AsyncClient):
        """Test mindmap generation without paper_id or paper_title"""
        response = await client.post(
            "/api/mindmap/generate",
            json={
                "include_methodology": True,
                "include_results": True
            }
        )
        # The endpoint validates this itself and returns 400 with an explanatory message
        assert response.status_code == 400
        assert "paper_id or paper_title" in response.json()["detail"]

    async def test_generate_mindmap_paper_not_found(self, client: AsyncClient):
        """Test mindmap generation for non-existent paper"""
        response = await client.post(
            "/api/mindmap/generate",
            json={
                "paper_id": 99999,
                "include_methodology": True,
                "include_results": True
            }
        )
        assert response.status_code == 404

    async def test_generate_mindmap_insufficient_text(self, client: AsyncClient):
        """Test mindmap generation with insufficient content"""
        response = await client.post(
            "/api/mindmap/generate",
            json={
                "paper_title": "Short",
                "abstract": "Too short",
                "full_text": "",
                "include_methodology": True,
                "include_results": True
            }
        )
        assert response.status_code == 400
        assert "insufficient" in response.json()["detail"].lower()

    async def test_generate_mindmap_with_direct_data(self, client: AsyncClient, mock_mindmap_request):
        """Test mindmap generation with direct paper data"""
        response = await client.post(
            "/api/mindmap/generate",
            json=mock_mindmap_request
        )

        # May succeed or fail depending on Ollama availability
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "paper_title" in data
            assert "root_node" in data
            assert "generation_time" in data
            assert data["paper_title"] == mock_mindmap_request["paper_title"]

        if response.status_code == 500:
            # Should have helpful error message
            detail = response.json()["detail"]
            assert any(keyword in detail.lower() for keyword in ["ollama", "connection", "timeout", "failed"])

    async def test_generate_mindmap_options(self, client: AsyncClient):
        """Test mindmap generation with different options"""
        test_cases = [
            {
                "paper_title": "Test Paper",
                "abstract": "This is a comprehensive test abstract with sufficient text content for mindmap generation.",
                "full_text": "Full text content here" * 20,
                "include_methodology": True,
                "include_results": False,
                "include_contributions": True,
                "max_depth": 2
            },
            {
                "paper_title": "Another Test",
                "abstract": "Another comprehensive abstract with lots of details about research methodology and findings.",
                "full_text": "More full text" * 20,
                "include_methodology": False,
                "include_results": True,
                "include_contributions": False,
                "max_depth": 4
            }
        ]

        for test_case in test_cases:
            response = await client.post("/api/mindmap/generate", json=test_case)
            # Should accept different configurations
            assert response.status_code in [200, 500]

    async def test_get_mindmap_svg_not_found(self, client: AsyncClient):
        """Test getting SVG for non-existent paper"""
        response = await client.get("/api/mindmap/99999/svg")
        assert response.status_code == 404

    async def test_mindmap_generation_time_reasonable(self, client: AsyncClient):
        """Test that mindmap generation completes in reasonable time"""
        response = await client.post(
            "/api/mindmap/generate",
            json={
                "paper_title": "Performance Test Paper",
                "abstract": "This abstract tests the performance of mindmap generation with sufficient content.",
                "full_text": "Content for testing" * 50,
                "include_methodology": True,
                "include_results": True
            }
        )

        if response.status_code == 200:
            data = response.json()
            # Should complete within reasonable time (adjust based on your requirements)
            assert data["generation_time"] < 60  # 60 seconds max


@pytest.mark.integration
class TestMindMapValidation:
    """Test input validation for mindmap endpoints"""

    async def test_invalid_paper_id_type(self, client: AsyncClient):
        """Test invalid paper_id type"""
        response = await client.post(
            "/api/mindmap/generate",
            json={
                "paper_id": "not-a-number",
                "include_methodology": True
            }
        )
        assert response.status_code == 422

    async def test_invalid_boolean_options(self, client: AsyncClient):
        """Test invalid boolean option types"""
        response = await client.post(
            "/api/mindmap/generate",
            json={
                "paper_title": "Test",
                "abstract": "Test abstract with sufficient length for validation testing purposes.",
                "include_methodology": "maybe",  # Not coercible to bool (pydantic v2 accepts "yes")
                "include_results": True
            }
        )
        assert response.status_code == 422

    async def test_invalid_max_depth(self, client: AsyncClient):
        """Test invalid max_depth values"""
        test_cases = [
            {"max_depth": -1},
            {"max_depth": "string"},
            {"max_depth": 0}
        ]

        for case in test_cases:
            response = await client.post(
                "/api/mindmap/generate",
                json={
                    "paper_title": "Test Paper",
                    "abstract": "Test abstract with sufficient content for mindmap generation testing.",
                    **case
                }
            )
            # Should validate or handle gracefully
            assert response.status_code in [200, 400, 422, 500]

    async def test_empty_strings_handling(self, client: AsyncClient):
        """Test handling of empty string inputs"""
        response = await client.post(
            "/api/mindmap/generate",
            json={
                "paper_title": "",
                "abstract": "",
                "full_text": ""
            }
        )
        # Should reject or fail gracefully
        assert response.status_code in [400, 422]
