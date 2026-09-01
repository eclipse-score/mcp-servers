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

import subprocess
import sys


def main() -> None:
    """Launch graphify's built-in MCP server."""
    try:
        subprocess.run([sys.executable, "-m", "graphify.serve"], check=True)
    except FileNotFoundError:
        print(
            "Error: graphify not found. Install with: uv tool install 'graphifyy[mcp]'"
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutdown requested")
        sys.exit(0)


if __name__ == "__main__":
    main()
