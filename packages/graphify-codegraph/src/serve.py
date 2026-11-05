#!/usr/bin/env python3
# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

"""Launch Graphify's built-in MCP server."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from graph_cache import build, prepare


def main() -> None:
    """Launch graphify's built-in MCP server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--repo-path", type=Path, default=Path.cwd())
    parser.add_argument("--force-local", action="store_true")
    args = parser.parse_args()
    build_results: list[bool] = []

    def build_local(root: Path, cache: Path) -> bool:
        result = build(root, cache)
        build_results.append(result)
        return result

    graph, thread = prepare(
        args.repo_path, builder=build_local, force_local=args.force_local
    )
    if args.prepare_only:
        if thread is not None:
            thread.join()
        ready = graph is not None and graph.exists()
        if thread is not None:
            ready = ready and bool(build_results) and all(build_results)
        provenance = graph.parent / "registry.json" if graph is not None else None
        print(
            json.dumps(
                {
                    "ok": ready,
                    "graph_path": str(graph) if graph is not None else None,
                    "source": "prebuilt"
                    if provenance and provenance.exists()
                    else "local",
                    "provenance": json.loads(provenance.read_text())
                    if provenance and provenance.exists()
                    else None,
                }
            )
        )
        return
    command = [sys.executable, "-m", "graphify.serve"]
    try:
        subprocess.run([*command, str(graph)] if graph else command, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(
            "Error: graphify not found. Install with: uv tool install "
            "'graphifyy[mcp]==0.9.97'"
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutdown requested")
        sys.exit(0)


if __name__ == "__main__":
    main()
