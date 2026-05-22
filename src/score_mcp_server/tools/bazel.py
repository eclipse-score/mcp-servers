"""Bazel tools for build, test, query, and coverage."""

from mcp.server.fastmcp import FastMCP

from score_mcp_server.manifest import parse_manifest
from score_mcp_server.tools.common import resolve_repo_root, run_command


def register_bazel_tools(mcp: FastMCP) -> None:
    """Register Bazel tools on the MCP server."""

    @mcp.tool()
    async def bazel_build(repo_path: str, target: str = "//...") -> dict:
        """Build a Bazel target from the manifest build command."""
        repo_root = resolve_repo_root(repo_path)
        manifest = parse_manifest(repo_root)
        command = manifest.build.command.replace("//...", target)
        return await run_command(command, cwd=repo_root)

    @mcp.tool()
    async def bazel_test(repo_path: str, target: str = "//...") -> dict:
        """Run tests for a Bazel target from the manifest test command."""
        repo_root = resolve_repo_root(repo_path)
        manifest = parse_manifest(repo_root)
        command = manifest.test.command.replace("//...", target)
        return await run_command(command, cwd=repo_root)

    @mcp.tool()
    async def bazel_query(repo_path: str, query: str) -> dict:
        """Run a Bazel query expression."""
        repo_root = resolve_repo_root(repo_path)
        command = f"bazel query {query}"
        return await run_command(command, cwd=repo_root)

    @mcp.tool()
    async def bazel_coverage(repo_path: str, target: str = "//...") -> dict:
        """Run Bazel coverage for a target."""
        repo_root = resolve_repo_root(repo_path)
        command = f"bazel coverage {target}"
        return await run_command(command, cwd=repo_root)
