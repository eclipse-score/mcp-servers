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

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_pins.py"
spec = importlib.util.spec_from_file_location("check_pins", SCRIPT)
assert spec is not None and spec.loader is not None
check_pins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_pins)

SOURCE = "git+https://github.com/eclipse-score/mcp-servers{ref}#subdirectory=packages/x"


def write_package(root: Path, version: str, ref: str) -> None:
    package = root / "packages" / "x"
    package.mkdir(parents=True)
    (package / "apm.yml").write_text(
        f"version: {version}\nargs:\n  - {SOURCE.format(ref=ref)}\n",
        encoding="utf-8",
    )


def test_mcp_source_pinned_to_package_version(tmp_path: Path) -> None:
    write_package(tmp_path, "0.1.0", "@v0.1.0")
    assert check_pins.check_mcp_sources(tmp_path) == []


def test_mcp_source_unpinned(tmp_path: Path) -> None:
    write_package(tmp_path, "0.1.0", "")
    assert "found no ref" in check_pins.check_mcp_sources(tmp_path)[0]


def test_mcp_source_version_mismatch(tmp_path: Path) -> None:
    write_package(tmp_path, "0.2.0", "@v0.1.0")
    assert (
        "pinned to @v0.2.0, found @v0.1.0" in check_pins.check_mcp_sources(tmp_path)[0]
    )


def test_graphify_installs(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "\n".join(
            [
                "uv tool install 'graphifyy[mcp]==0.9.53'",
                "uvx --from graphifyy graphify",
                'dependencies = ["graphifyy[mcp]>=0.9"]',
                "pip install graphifyy==0.9.1",
                "See the graphifyy project documentation.",
                "Run `graphify update` from the graphifyy package.",
            ]
        ),
        encoding="utf-8",
    )
    errors = check_pins.check_graphify_installs("0.9.53", tmp_path)
    assert [error.split(":")[1] for error in errors] == ["2", "3", "4"]
