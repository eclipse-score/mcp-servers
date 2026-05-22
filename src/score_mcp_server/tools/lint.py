"""Lint tools for check and format workflows."""

from mcp.server.fastmcp import FastMCP

from score_mcp_server.manifest import parse_manifest
from score_mcp_server.tools.common import resolve_repo_root, run_command


def register_lint_tools(mcp: FastMCP) -> None:
    """Register lint tools on the MCP server."""

    @mcp.tool()
    async def lint_check(repo_path: str) -> dict:
        """Run linter command from the repository manifest."""
        repo_root = resolve_repo_root(repo_path)
        manifest = parse_manifest(repo_root)
        return await run_command(manifest.lint.command, cwd=repo_root)

    @mcp.tool()
    async def lint_format(repo_path: str) -> dict:
        """Run formatter command derived from the manifest lint command."""
        repo_root = resolve_repo_root(repo_path)
        manifest = parse_manifest(repo_root)

        match manifest.language.lower():
            case "python":
                command = manifest.lint.command.replace("check", "format")
            case "cpp" | "c++" | "rust":
                command = manifest.lint.command
            case _:
                command = manifest.lint.command

        return await run_command(command, cwd=repo_root)
