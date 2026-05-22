"""SCORE MCP server entry point and lifecycle."""

from mcp.server.fastmcp import FastMCP

from score_mcp_server.config import DEFAULT_CONFIG
from score_mcp_server.tools.bazel import register_bazel_tools
from score_mcp_server.tools.health import register_health_tools
from score_mcp_server.tools.lint import register_lint_tools
from score_mcp_server.tools.project import register_project_tools


def create_server() -> FastMCP:
    """Create and configure the SCORE MCP server."""
    mcp = FastMCP(DEFAULT_CONFIG.server_name)
    register_project_tools(mcp)
    register_bazel_tools(mcp)
    register_lint_tools(mcp)
    register_health_tools(mcp)
    return mcp


def main() -> None:
    """Run the SCORE MCP server."""
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
