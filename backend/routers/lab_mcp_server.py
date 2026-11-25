from mcp.server.fastmcp import FastMCP
server = FastMCP("ossiemate-sample")
@server.tool()
def lookup_policy(topic: str) -> str:
    """Return a fictional training policy for a given topic."""
    return "Sample policy: all migration changes require peer review and rollback testing. Topic: " + topic[:200]
if __name__ == "__main__":
    server.run(transport="stdio")
