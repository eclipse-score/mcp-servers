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

from __future__ import annotations

import argparse
import json
from pathlib import Path

from score_context.harness.adapter import execute


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the context-attention harness.")
    parser.add_argument("request", type=Path, help="Adapter request JSON path")
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    response = execute(request, Path.cwd())
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
