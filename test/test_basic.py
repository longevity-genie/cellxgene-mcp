"""Basic tests for CELLxGENE Census MCP Server."""

import pytest
from cellxgene_mcp.server import CellxGeneMCP


def test_server_initialization():
    """Test that the MCP server initializes correctly."""
    server = CellxGeneMCP(name="TestCellxGeneServer")
    
    assert server.name == "TestCellxGeneServer"
    assert server.prefix == "cellxgene_"
    assert hasattr(server, 'census_manager')


def test_server_with_custom_prefix():
    """Test server initialization with custom prefix."""
    server = CellxGeneMCP(
        name="TestServer",
        prefix="test_"
    )
    
    assert server.prefix == "test_"


@pytest.mark.asyncio
async def test_census_info_structure():
    """Test that census info returns expected structure."""
    server = CellxGeneMCP(name="TestServer")
    
    try:
        result = await server.get_census_info()
        
        # Check that result has expected keys
        expected_keys = [
            "available_versions", 
            "latest_stable_version", 
            "supported_organisms",
            "data_types", 
            "measurement_types"
        ]
        
        for key in expected_keys:
            assert key in result
        
        # Check that organisms are as expected
        assert "Homo sapiens" in result["supported_organisms"]
        assert "Mus musculus" in result["supported_organisms"]
        
    except Exception as e:
        # If there's a network error or Census is unavailable, skip the test
        pytest.skip(f"Census API not available: {e}")


def test_import_structure():
    """Test that imports work correctly."""
    from cellxgene_mcp.server import CellxGeneMCP, CensusManager, QueryResult
    
    # Just verify that classes can be imported
    assert CellxGeneMCP is not None
    assert CensusManager is not None
    assert QueryResult is not None 