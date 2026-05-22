"""Project tools for manifest reading and repository discovery."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from score_mcp_server.manifest import parse_manifest
from score_mcp_server.tools.common import resolve_repo_root


def register_project_tools(mcp: FastMCP) -> None:
    """Register project tools on the MCP server."""

    @mcp.tool()
    async def project_manifest(repo_path: str) -> dict:
        """Read and return the parsed repo-manifest.json for a repository."""
        repo_root = resolve_repo_root(repo_path)
        manifest = parse_manifest(repo_root)
        return {
            "name": manifest.name,
            "language": manifest.language,
            "visibility": manifest.visibility,
            "tags": manifest.tags,
            "build": manifest.build.command,
            "test": manifest.test.command,
            "lint": manifest.lint.command,
            "typecheck": manifest.typecheck.command if manifest.typecheck else None,
        }

    @mcp.tool()
    async def project_discover(search_root: str = ".") -> list[dict]:
        """Discover repositories by scanning for SCORE manifest files."""
        root = Path(search_root).expanduser().resolve()
        results: list[dict] = []

        for manifest_file in root.rglob(".github/score/repo-manifest.json"):
            repo_root = manifest_file.parent.parent.parent
            try:
                manifest = parse_manifest(repo_root)
                results.append(
                    {
                        "path": str(repo_root),
                        "name": manifest.name,
                        "language": manifest.language,
                        "tags": manifest.tags,
                    }
                )
            except (KeyError, ValueError, FileNotFoundError):
                continue

        return results
