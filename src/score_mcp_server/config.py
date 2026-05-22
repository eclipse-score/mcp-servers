"""Server configuration and defaults."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    """Configuration for the SCORE MCP server."""

    server_name: str = "score-mcp-server"
    server_version: str = "0.1.0"
    manifest_filename: str = "repo-manifest.json"
    manifest_path: str = ".github/score"

    def manifest_file(self, repo_root: Path) -> Path:
        """Return the full manifest path for a repository root."""
        return repo_root / self.manifest_path / self.manifest_filename


DEFAULT_CONFIG = ServerConfig()
