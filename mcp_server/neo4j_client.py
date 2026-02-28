from neo4j import GraphDatabase
from mcp_server.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def run_query(cypher: str, params: dict) -> dict:
    """Execute a Cypher query and return result + the query itself."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher, params).data()
    return {
        "result": result,
        "cypher": cypher,
        "metadata": {}
    }
