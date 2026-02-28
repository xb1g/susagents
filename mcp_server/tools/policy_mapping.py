from mcp_server.neo4j_client import run_query

# TODO: Person 4 confirms PolicyFramework → SDG relationship by running:
# MATCH (pf:PolicyFramework)-[r]-(s:SDG) RETURN type(r), s.code LIMIT 10
# Then add: OPTIONAL MATCH (s:SDG {code: $sdg_id})-[*1..2]-(pf) to filter by SDG
CYPHER = """
MATCH (pf:PolicyFramework)
OPTIONAL MATCH (pf)-[:HAS_SUBPART]->(pa)
RETURN pf.name AS framework_name,
       pf.description AS description,
       collect(DISTINCT pa.name)[0..3] AS policy_areas
LIMIT 10
"""


def map_sdg_to_policy(sdg_id: str, geo_id: str) -> dict:
    """Returns PolicyFramework nodes related to the SDG.

    Args:
        sdg_id: SDG identifier e.g. "SDG_7"
        geo_id: Region code e.g. "EL30" (currently unused, reserved for future filtering)
    Returns:
        {"result": [...], "cypher": "...", "metadata": {...}}
    """
    data = run_query(CYPHER, {"sdg_id": sdg_id, "geo_id": geo_id})
    data["metadata"] = {"nodes": ["SDG", "PolicyFramework"]}
    return data
