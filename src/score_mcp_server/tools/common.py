"""Common helpers for tool modules."""

import asyncio
import platform
import shlex
import shutil
import sys
from pathlib import Path


def resolve_repo_root(repo_path: str) -> Path:
    """Resolve and validate a repository root path."""
    repo_root = Path(repo_path).expanduser().resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_root}")
    if not repo_root.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repo_root}")
    return repo_root


async def run_command(command: str, cwd: Path) -> dict:
    """Run a command without shell expansion and return structured output."""
    command_parts = shlex.split(command)
    if not command_parts:
        return {
            "command": command,
            "stdout": "",
            "stderr": "Command is empty.",
            "returncode": 2,
        }

    executable = command_parts[0]
    if shutil.which(executable) is None:
        return {
            "command": command,
            "stdout": "",
            "stderr": f"Required command is not available: {executable}",
            "returncode": 127,
        }

    process = await asyncio.create_subprocess_exec(
        *command_parts,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return {
        "command": command,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
        "returncode": process.returncode,
    }


def extract_executable(command: str) -> str | None:
    """Extract the executable token from a shell-like command string."""
    command_parts = shlex.split(command)
    if not command_parts:
        return None
    return command_parts[0]


def command_path(command_name: str) -> str | None:
    """Return the absolute path for a command if available."""
    return shutil.which(command_name)


def runtime_info() -> dict:
    """Return basic runtime metadata for diagnostics."""
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "in_devcontainer": Path("/.dockerenv").exists(),
    }
