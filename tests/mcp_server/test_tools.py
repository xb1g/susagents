"""
MCP Server tool tests.
Requires Neo4j running at bolt://localhost:7687 (docker compose up -d).
"""
import pytest


def test_run_query_returns_result_and_cypher():
    """neo4j_client.run_query returns the expected dict shape."""
    pytest.importorskip("neo4j")
    from mcp_server.neo4j_client import run_query
    result = run_query("RETURN 1 AS n", {})
    assert "result" in result
    assert "cypher" in result
    assert result["result"][0]["n"] == 1


def test_get_regional_sdg_profile_returns_shape():
    from mcp_server.tools.regional_profile import get_regional_sdg_profile
    result = get_regional_sdg_profile(geo_id="EL30", sdg_id="SDG_7")
    assert "result" in result
    assert "cypher" in result
    assert isinstance(result["result"], list)


def test_find_peer_regions_returns_shape():
    from mcp_server.tools.peer_regions import find_peer_regions
    result = find_peer_regions(geo_id="EL30", sdg_id="SDG_7")
    assert "result" in result
    assert "cypher" in result
    assert isinstance(result["result"], list)


def test_get_indicator_trend_returns_shape():
    from mcp_server.tools.indicator_trend import get_indicator_trend
    result = get_indicator_trend(indicator_id="sdg_07_40", geo_id="EL30")
    assert "result" in result
    assert "cypher" in result
    assert isinstance(result["result"], list)


def test_map_sdg_to_policy_returns_shape():
    from mcp_server.tools.policy_mapping import map_sdg_to_policy
    result = map_sdg_to_policy(sdg_id="SDG_7", geo_id="EL30")
    assert "result" in result
    assert "cypher" in result
    assert isinstance(result["result"], list)
