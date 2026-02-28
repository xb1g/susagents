from mcp_server.neo4j_client import run_query

# TODO: Person 4 validates seriesCode prefix format
CYPHER = """
// Step 1: collect series codes for the target region matching the SDG prefix
MATCH (target:GeoArea)
WHERE target.EUcode = $geo_id OR target.ISOalpha3code = $geo_id
MATCH (target)<-[:REFERS_TO_AREA]-(o:Observation)<-[:HAS_OBSERVATION]-(sm:SeriesMetadata)
WHERE sm.seriesCode STARTS WITH $sdg_prefix
WITH collect(DISTINCT sm.seriesCode) AS target_series, $geo_id AS target_geo_id

// Step 2: find peers that share those series codes
MATCH (peer:GeoArea)
WHERE peer.EUcode <> target_geo_id AND peer.ISOalpha3code <> target_geo_id
MATCH (peer)<-[:REFERS_TO_AREA]-(:Observation)<-[:HAS_OBSERVATION]-(psm:SeriesMetadata)
WHERE psm.seriesCode IN target_series

WITH peer, count(DISTINCT psm.seriesCode) AS shared, size(target_series) AS total
WHERE shared >= 2
RETURN peer.name AS peer_name,
       peer.EUcode AS peer_geo_id,
       shared AS shared_indicators,
       total AS total_indicators
ORDER BY shared DESC
LIMIT 5
"""


def find_peer_regions(geo_id: str, sdg_id: str) -> dict:
    """Finds other regions that share SDG indicators with the target region.

    Args:
        geo_id: Region code e.g. "EL30"
        sdg_id: SDG identifier e.g. "SDG_7"
    Returns:
        {"result": [...], "cypher": "...", "metadata": {...}}
    """
    parts = sdg_id.lower().split("_")  # ["sdg", "7"]
    sdg_num = parts[-1].zfill(2)       # "07"
    sdg_prefix = f"sdg_{sdg_num}"      # "sdg_07"

    data = run_query(CYPHER, {"geo_id": geo_id, "sdg_prefix": sdg_prefix})
    data["metadata"] = {"nodes": ["GeoArea", "Observation", "SeriesMetadata"]}
    return data
