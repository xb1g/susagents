from fastmcp import FastMCP
from mcp_server.tools.regional_profile import get_regional_sdg_profile
from mcp_server.tools.peer_regions import find_peer_regions
from mcp_server.tools.indicator_trend import get_indicator_trend
from mcp_server.tools.policy_mapping import map_sdg_to_policy

mcp = FastMCP("SustainGraph")

mcp.tool()(get_regional_sdg_profile)
mcp.tool()(find_peer_regions)
mcp.tool()(get_indicator_trend)
mcp.tool()(map_sdg_to_policy)

if __name__ == "__main__":
    mcp.run()
