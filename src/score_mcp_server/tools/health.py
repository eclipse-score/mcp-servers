"""Health and environment diagnostic tools."""

from mcp.server.fastmcp import FastMCP

from score_mcp_server.manifest import parse_manifest
from score_mcp_server.tools.common import (
    command_path,
    extract_executable,
    resolve_repo_root,
    runtime_info,
)


def register_health_tools(mcp: FastMCP) -> None:
    """Register health and diagnostics tools on the MCP server."""

    @mcp.tool()
    async def server_health(repo_path: str = ".") -> dict:
        """Report server runtime information and required command availability."""
        repo_root = resolve_repo_root(repo_path)

        required_commands = {"bazel", "uv"}
        manifest_present = False

        try:
            manifest = parse_manifest(repo_root)
            manifest_present = True

            manifest_commands = [
                manifest.build.command,
                manifest.test.command,
                manifest.lint.command,
            ]
            if manifest.typecheck is not None:
                manifest_commands.append(manifest.typecheck.command)

            for command in manifest_commands:
                executable = extract_executable(command)
                if executable is not None:
                    required_commands.add(executable)
        except (FileNotFoundError, KeyError, ValueError):
            manifest_present = False

        checks = []
        missing_commands = []

        for command_name in sorted(required_commands):
            path = command_path(command_name)
            is_available = path is not None
            checks.append(
                {
                    "name": command_name,
                    "available": is_available,
                    "path": path,
                }
            )
            if not is_available:
                missing_commands.append(command_name)

        return {
            "status": "ok" if not missing_commands else "degraded",
            "runtime": runtime_info(),
            "repo": {
                "path": str(repo_root),
                "manifest_present": manifest_present,
            },
            "checks": checks,
            "missing_commands": missing_commands,
        }
