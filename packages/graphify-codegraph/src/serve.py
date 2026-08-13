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

"""
Graphify MCP Server Launcher

Wraps external graphify CLI's MCP server.
Requires: graphify CLI installed (uv tool install graphifyy)
"""

import subprocess
import sys


def main():
    """Launch graphify MCP server."""
    try:
        # Run graphify's built-in MCP server
        subprocess.run([sys.executable, "-m", "graphify.serve"], check=True)
    except FileNotFoundError:
        print("Error: graphify not found. Install with: uv tool install graphifyy")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutdown requested")
        sys.exit(0)


if __name__ == "__main__":
    main()
