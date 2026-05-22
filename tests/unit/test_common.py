"""Unit tests for common tool helpers."""

from pathlib import Path

import pytest

from score_mcp_server.tools.common import extract_executable, run_command, runtime_info


def test_extract_executable_valid_command() -> None:
    """Extract executable from a simple command."""
    assert extract_executable("uv run pytest") == "uv"


def test_extract_executable_empty_command() -> None:
    """Return None for empty commands."""
    assert extract_executable("   ") is None


@pytest.mark.asyncio
async def test_run_command_missing_executable(tmp_path: Path) -> None:
    """Return a clear error payload when executable is unavailable."""
    result = await run_command("command-that-should-not-exist-12345", cwd=tmp_path)

    assert result["returncode"] == 127
    assert "Required command is not available" in result["stderr"]


def test_runtime_info_has_expected_fields() -> None:
    """Expose stable runtime metadata fields for diagnostics."""
    result = runtime_info()

    assert "python_version" in result
    assert "platform" in result
    assert "in_devcontainer" in result
