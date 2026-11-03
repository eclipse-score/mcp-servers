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
from ruamel.yaml import YAML

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


@pytest.mark.parametrize(
    "command",
    [
        "uv tool install --with-executables-from graphifyy package",
        '["uv", "tool", "install", "--with-executables-from", "graphifyy", source]',
    ],
)
def test_executable_provider_is_not_a_dependency_spec(command: str) -> None:
    match = check_pins.GRAPHIFY_RE.search(command)
    assert match is not None
    assert not check_pins.is_install_spec(command, match)


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


def test_release_plan_first_release(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    write_repo(tmp_path, "0.2.3", "@v0.2.1")
    source = commit_all(tmp_path, "merged code and docs")
    assert prepare_release.release_plan(source, tmp_path) == {
        "version": "0.2.3",
        "sha": "",
    }


def test_release_plan_retry_and_next_merge(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    write_repo(tmp_path, "0.2.3", "@v0.2.1")
    source = commit_all(tmp_path, "merged code and docs")
    prepare_release.prepare("0.2.3", source, tmp_path)
    release = commit_all(tmp_path, f"release\n\nRelease-Source: {source}")
    git(tmp_path, "tag", "--no-sign", "v0.2.3")
    assert prepare_release.release_plan(source, tmp_path) == {
        "version": "0.2.3",
        "sha": release,
    }
    git(tmp_path, "switch", "--detach", source)
    (tmp_path / "needs.json").write_text('{"changed": true}\n', encoding="utf-8")
    next_source = commit_all(tmp_path, "new docs-as-code graph")
    assert prepare_release.release_plan(next_source, tmp_path) == {
        "version": "0.2.4",
        "sha": "",
    }
    prepare_release.prepare("0.2.4", next_source, tmp_path)
    commit_all(tmp_path, f"release\n\nRelease-Source: {next_source}")
    assert check_pins.check_release(tmp_path) == []


@pytest.mark.parametrize(
    ("requested", "expected"), [("0.2.3", "0.2.11"), ("1.0.0", "1.0.0")]
)
def test_release_plan_uses_highest_numeric_tag(
    tmp_path: Path, requested: str, expected: str
) -> None:
    git(tmp_path, "init", "-q")
    write_repo(tmp_path, requested, "@v0.2.1")
    source = commit_all(tmp_path, "source")
    for tag in ("v0.2.9", "v0.2.10", "unrelated", "v1.0.0-rc.1"):
        git(tmp_path, "tag", "--no-sign", tag)
    assert prepare_release.release_plan(source, tmp_path) == {
        "version": expected,
        "sha": "",
    }


def test_tag_only_release_preserves_remote_main(tmp_path: Path) -> None:
    source_repo = tmp_path / "source"
    remote = tmp_path / "remote.git"
    consumer = tmp_path / "consumer"
    for directory in (source_repo, remote):
        directory.mkdir()
    git(remote, "init", "--bare", "-q")
    git(source_repo, "init", "-q")
    write_repo(source_repo, "0.2.3", "@v0.2.1")
    (source_repo / "needs.json").write_text('{"changed": true}\n', encoding="utf-8")
    source = commit_all(source_repo, "merged docs-as-code graph")
    git(source_repo, "remote", "add", "origin", str(remote))
    git(source_repo, "push", "origin", "HEAD:refs/heads/main")
    prepare_release.prepare("0.2.3", source, source_repo)
    release = commit_all(source_repo, f"release\n\nRelease-Source: {source}")
    git(source_repo, "tag", "--no-sign", "v0.2.3")
    git(source_repo, "push", "origin", "refs/tags/v0.2.3")
    assert git(remote, "rev-parse", "refs/heads/main") == source
    git(tmp_path, "clone", "--branch", "v0.2.3", str(remote), str(consumer))
    assert git(consumer, "rev-parse", "HEAD") == release
    assert check_pins.pinned_commits(consumer) == {source}
    assert check_pins.check_release(consumer) == []
    assert check_pins.check_versions(consumer) == []
    assert (consumer / "needs.json").read_text() == '{"changed": true}\n'
    assert prepare_release.release_plan(source, consumer)["sha"] == release


def test_release_workflow_uses_one_verified_revision() -> None:
    workflow = YAML(typ="safe").load(
        (SCRIPTS.parent / ".github/workflows/release.yml").read_text()
    )
    jobs = workflow["jobs"]
    steps = jobs["release"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    assert 'git push origin "refs/tags/v${VERSION}"' in commands
    assert "git push\n" not in commands
    assert "--plan" in commands
    assert "new" not in jobs["release"]["outputs"]
    smoke = next(
        step for step in steps if step["name"] == "Smoke-test shipped MCP pins"
    )
    assert '--ref "v${VERSION}"' in smoke["run"]
    assert "check_remote_mcp.py" in smoke["run"]
    assert "re.sub" not in smoke["run"]
    assert jobs["features"]["steps"][0]["with"]["ref"] == (
        "${{ needs.release.outputs.sha }}"
    )
    assert jobs["publish"]["needs"] == ["release", "features"]


@pytest.mark.parametrize(
    "path", sorted((SCRIPTS.parent / ".github/workflows").glob("*.y*ml"))
)
def test_workflow_yaml_is_valid(path: Path) -> None:
    workflow = YAML(typ="safe").load(path.read_text())
    assert isinstance(workflow["jobs"], dict)
    for job in workflow["jobs"].values():
        assert isinstance(job, dict)
