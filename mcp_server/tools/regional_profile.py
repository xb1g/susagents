from mcp_server.neo4j_client import run_query

# TODO: Person 4 validates the sdg_prefix format against live graph
# Run in Neo4j Browser: MATCH (sm:SeriesMetadata) RETURN sm.seriesCode LIMIT 20
CYPHER = """
MATCH (ga:GeoArea)
WHERE ga.EUcode = $geo_id OR ga.ISOalpha3code = $geo_id
MATCH (ga)<-[:REFERS_TO_AREA]-(o:Observation)<-[:HAS_OBSERVATION]-(sm:SeriesMetadata)
MATCH (sm)<-[:HAS_METADATA]-(s:Series)<-[:HAS_SERIES]-(i:Indicator)
WHERE sm.seriesCode STARTS WITH $sdg_prefix
RETURN ga.name AS region, i.code AS indicator_code, i.description AS indicator_desc,
       o.value AS value, o.time AS time
ORDER BY o.time DESC
LIMIT 30
"""


def get_regional_sdg_profile(geo_id: str, sdg_id: str) -> dict:
    """Gets all SDG indicator observations for a region.

    Args:
        geo_id: Region code e.g. "EL30" (Attica) or "EL" (Greece)
        sdg_id: SDG identifier e.g. "SDG_7"
    Returns:
        {"result": [...], "cypher": "...", "metadata": {...}}
    """
    # "SDG_7" → "sdg_07" (zero-padded prefix)
    parts = sdg_id.lower().split("_")  # ["sdg", "7"]
    sdg_num = parts[-1].zfill(2)       # "07"
    sdg_prefix = f"sdg_{sdg_num}"      # "sdg_07"

    data = run_query(CYPHER, {"geo_id": geo_id, "sdg_prefix": sdg_prefix})
    data["metadata"] = {"nodes": ["GeoArea", "Observation", "SeriesMetadata", "Indicator"]}
    return data
