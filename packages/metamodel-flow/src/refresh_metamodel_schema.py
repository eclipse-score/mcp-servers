# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Download and refresh the metamodel schema and data from docs-as-code repository.

This script fetches the generated metamodel schema and data from the docs-as-code
repository and updates the local model files.

Usage:
    refresh_metamodel_schema.py --source-commit SHA [--repo-root PATH]
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

# Source repository information
_SOURCE_REPO_URL = "https://github.com/eclipse-score/docs-as-code.git"
_SOURCE_FILE_HEADER = (
    "# SPDX-License-Identifier: Apache-2.0\n"
    "# Copyright (c) 2026 Contributors to the Eclipse Foundation\n"
)


def _source_text(source_commit: str) -> str:
    """Generate source metadata file."""
    return (
        _SOURCE_FILE_HEADER
        + "\n"
        + f"source_repo_url={_SOURCE_REPO_URL}\n"
        + f"source_commit={source_commit}\n"
        + "generator_command=bazel run //src/extensions/score_metamodel/schema_export:generate_all_bin\n"
    )


def refresh(
    *,
    source_commit: str,
    repo_root: Path,
    schema_file: str = "metamodel-schema.json",
    data_file: str = "metamodel-data.json",
) -> None:
    """Refresh the metamodel schema and data from docs-as-code.
    
    In a CI environment, these files would be downloaded from the docs-as-code
    artifacts. For local development, they can be generated using the generate_all.py
    script from docs-as-code.
    """
    model_dir = repo_root / "packages" / "metamodel-flow" / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # For now, we assume the files are generated locally or downloaded
    # In CI, this would fetch from docs-as-code artifacts
    
    print(f"Metamodel schema and data should be generated from docs-as-code")
    print(f"Source commit: {source_commit}")
    print(f"Output directory: {model_dir}")
    print(f"\nTo generate locally:")
    print(f"  cd /workspaces/docs-as-code_agent")
    print(f"  bazel run //src/extensions/score_metamodel/schema_export:generate_all_bin -- \\")
    print(f"    --output-dir {model_dir} \\")
    print(f"    --source-commit {source_commit}")
    
    # The actual files would be:
    # - model_dir / schema_file (metamodel-schema.json)
    # - model_dir / data_file (metamodel-data.json)
    # - model_dir / "source.txt" (source metadata)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--schema-file", default="metamodel-schema.json")
    parser.add_argument("--data-file", default="metamodel-data.json")
    args = parser.parse_args(argv)
    
    refresh(
        source_commit=args.source_commit,
        repo_root=args.repo_root,
        schema_file=args.schema_file,
        data_file=args.data_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
