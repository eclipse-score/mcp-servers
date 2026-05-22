"""Unit tests for the manifest parser."""

import json
from pathlib import Path

import pytest

from score_mcp_server.manifest import ExecutionCommand, parse_manifest


@pytest.fixture()
def sample_manifest(tmp_path: Path) -> Path:
    """Create a temporary repository with a valid manifest."""
    manifest_dir = tmp_path / ".github" / "score"
    manifest_dir.mkdir(parents=True)

    manifest_data = {
        "version": 1,
        "repository": {
            "name": "test-repo",
            "language": "python",
            "visibility": "public",
            "tags": ["test"],
        },
        "bootstrap": {"contract_version": "v0.1.0"},
        "execution": {
            "build": {"command": "uv build"},
            "test": {"command": "uv run pytest"},
            "lint": {"command": "uv run ruff check src/"},
            "typecheck": {"command": "uv run basedpyright src/"},
        },
    }

    manifest_file = manifest_dir / "repo-manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
    return tmp_path


def test_parse_manifest(sample_manifest: Path) -> None:
    """Parse a valid manifest successfully."""
    result = parse_manifest(sample_manifest)

    assert result.name == "test-repo"
    assert result.language == "python"
    assert result.visibility == "public"
    assert result.tags == ["test"]
    assert result.build == ExecutionCommand(command="uv build")
    assert result.test == ExecutionCommand(command="uv run pytest")
    assert result.lint == ExecutionCommand(command="uv run ruff check src/")
    assert result.typecheck == ExecutionCommand(command="uv run basedpyright src/")


def test_parse_manifest_without_typecheck(tmp_path: Path) -> None:
    """Parse a manifest that does not define typecheck."""
    manifest_dir = tmp_path / ".github" / "score"
    manifest_dir.mkdir(parents=True)

    manifest_data = {
        "version": 1,
        "repository": {
            "name": "minimal-repo",
            "language": "cpp",
            "visibility": "public",
        },
        "bootstrap": {"contract_version": "v0.1.0"},
        "execution": {
            "build": {"command": "bazel build //..."},
            "test": {"command": "bazel test //..."},
            "lint": {"command": "bazel run //:lint"},
        },
    }

    manifest_file = manifest_dir / "repo-manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    result = parse_manifest(tmp_path)

    assert result.name == "minimal-repo"
    assert result.language == "cpp"
    assert result.typecheck is None
    assert result.tags == []


def test_parse_manifest_file_not_found(tmp_path: Path) -> None:
    """Raise FileNotFoundError when manifest file is missing."""
    with pytest.raises(FileNotFoundError):
        parse_manifest(tmp_path)


def test_parse_manifest_invalid_json(tmp_path: Path) -> None:
    """Raise JSONDecodeError when manifest file content is invalid."""
    manifest_dir = tmp_path / ".github" / "score"
    manifest_dir.mkdir(parents=True)
    manifest_file = manifest_dir / "repo-manifest.json"
    manifest_file.write_text("not valid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        parse_manifest(tmp_path)
