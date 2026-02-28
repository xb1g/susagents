from mcp_server.neo4j_client import run_query

CYPHER = """
MATCH (ga:GeoArea)
WHERE ga.EUcode = $geo_id OR ga.ISOalpha3code = $geo_id
MATCH (ga)<-[:REFERS_TO_AREA]-(o:Observation)<-[:HAS_OBSERVATION]-(sm:SeriesMetadata {seriesCode: $indicator_id})
RETURN o.time AS time, o.value AS value
ORDER BY o.time ASC
"""


def get_indicator_trend(indicator_id: str, geo_id: str) -> dict:
    """Gets year-by-year values for one indicator in one region.

    Args:
        indicator_id: Series code e.g. "sdg_07_40"
        geo_id: Region code e.g. "EL30"
    Returns:
        {"result": [...], "cypher": "...", "metadata": {...}}
    """
    data = run_query(CYPHER, {"geo_id": geo_id, "indicator_id": indicator_id})
    data["metadata"] = {"nodes": ["GeoArea", "Observation", "SeriesMetadata"]}
    return data
