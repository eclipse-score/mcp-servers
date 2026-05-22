"""Parser for SCORE repo-manifest.json files."""

import json
from dataclasses import dataclass
from pathlib import Path

from score_mcp_server.config import DEFAULT_CONFIG, ServerConfig


@dataclass(frozen=True)
class ExecutionCommand:
    """A single execution command from the manifest."""

    command: str
    working_directory: str | None = None


@dataclass(frozen=True)
class RepoManifest:
    """Parsed repo-manifest.json data."""

    name: str
    language: str
    visibility: str
    tags: list[str]
    build: ExecutionCommand
    test: ExecutionCommand
    lint: ExecutionCommand
    typecheck: ExecutionCommand | None = None


def parse_manifest(repo_root: Path, config: ServerConfig = DEFAULT_CONFIG) -> RepoManifest:
    """Parse a repository manifest from a repository root path."""
    manifest_path = config.manifest_file(repo_root)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    repository = data["repository"]
    execution = data["execution"]

    typecheck_data = execution.get("typecheck")
    typecheck = ExecutionCommand(**typecheck_data) if typecheck_data is not None else None

    return RepoManifest(
        name=repository["name"],
        language=repository["language"],
        visibility=repository["visibility"],
        tags=repository.get("tags", []),
        build=ExecutionCommand(**execution["build"]),
        test=ExecutionCommand(**execution["test"]),
        lint=ExecutionCommand(**execution["lint"]),
        typecheck=typecheck,
    )
