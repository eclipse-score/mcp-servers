"""Unit tests for server creation."""

from score_mcp_server.server import create_server


def test_create_server() -> None:
    """Create a server instance successfully."""
    server = create_server()
    assert server is not None
