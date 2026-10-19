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
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_pins = load("check_pins")
prepare_release = load("prepare_release")

SHA = "4c562c1fafa337beacd9f076d739096aca998577"
SOURCE = "git+https://github.com/eclipse-score/mcp-servers{ref}#subdirectory=packages/x"


def write_repo(root: Path, version: str, pin: str) -> None:
    package = root / "packages" / "x"
    package.mkdir(parents=True)
    (root / "apm.yml").write_text(
        f"version: {version}\nmarketplace:\n  packages:\n    - name: x\n"
        f'      version: "{version}"\n',
        encoding="utf-8",
    )
    ref, _, comment = pin.partition(" # ")
    source = SOURCE.format(ref=ref) + (f" # {comment}" if comment else "")
    (package / "apm.yml").write_text(
        f"version: {version}\nargs:\n  - {source}\n",
        encoding="utf-8",
    )
    (package / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nversion = "{version}"\n', encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("pin", "error"),
    [
        (f"@{SHA} # v0.1.0", None),
        (f"@{SHA}", "needs the comment '# v0.1.0', found none"),
        (f"@{SHA} # v0.0.9", "needs the comment '# v0.1.0', found # v0.0.9"),
        ("@v0.1.0 # v0.1.0", "pinned to a full commit SHA, found v0.1.0"),
        (f"@{SHA[:12]} # v0.1.0", "pinned to a full commit SHA"),
        ("", "pinned to a full commit SHA, found no ref"),
    ],
)
def test_mcp_sources(tmp_path: Path, pin: str, error: str | None) -> None:
    write_repo(tmp_path, "0.1.0", pin)
    errors = check_pins.check_mcp_sources(tmp_path)
    assert (error in errors[0]) if error else errors == []


def test_versions_must_match_release(tmp_path: Path) -> None:
    write_repo(tmp_path, "0.1.0", f"@{SHA} # v0.1.0")
    assert check_pins.check_versions(tmp_path) == []
    pyproject = tmp_path / "packages" / "x" / "pyproject.toml"
    pyproject.write_text('version = "0.2.0"\n', encoding="utf-8")
    assert check_pins.check_versions(tmp_path) == [
        "packages/x/pyproject.toml: version 0.2.0 differs from release version 0.1.0"
    ]


def test_prepare_release(tmp_path: Path) -> None:
    write_repo(tmp_path, "0.1.0", "@v0.1.0")
    changed = prepare_release.prepare("0.2.0", SHA, tmp_path)
    assert len(changed) == 3
    assert prepare_release.current_version(tmp_path) == "0.2.0"
    assert check_pins.check_versions(tmp_path) == []
    assert check_pins.check_mcp_sources(tmp_path) == []
    assert f"@{SHA}#subdirectory=packages/x # v0.2.0" in (
        tmp_path / "packages" / "x" / "apm.yml"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize(("version", "commit"), [("v0.2.0", SHA), ("0.2.0", "HEAD")])
def test_prepare_release_rejects_input(version: str, commit: str) -> None:
    with pytest.raises(SystemExit):
        prepare_release.prepare(version, commit, Path("/nonexistent"))


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def commit_all(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(
        root,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        message,
    )
    return git(root, "rev-parse", "HEAD")


def test_release_only_changes_metadata(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    write_repo(tmp_path, "0.1.0", "@v0.1.0")
    (tmp_path / "packages" / "x" / "server.py").write_text("v1\n", encoding="utf-8")
    base = commit_all(tmp_path, "code")
    prepare_release.prepare("0.2.0", base, tmp_path)
    commit_all(tmp_path, "release")
    assert check_pins.check_release(tmp_path) == []

    (tmp_path / "packages" / "x" / "server.py").write_text("v2\n", encoding="utf-8")
    commit_all(tmp_path, "code after pin")
    assert check_pins.check_release(tmp_path) == [
        f"packages/x/server.py: changed since pinned commit {base[:12]}, "
        "only release metadata may differ"
    ]


def test_release_unknown_commit(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    write_repo(tmp_path, "0.1.0", f"@{SHA} # v0.1.0")
    commit_all(tmp_path, "init")
    assert check_pins.check_release(tmp_path) == [
        f"pinned commit {SHA} is not in the local history"
    ]


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
