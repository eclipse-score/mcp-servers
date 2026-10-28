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

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "next_version.py"
_spec = importlib.util.spec_from_file_location("next_version", SCRIPT)
assert _spec is not None and _spec.loader is not None
next_version = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(next_version)


@pytest.mark.parametrize(
    ("message", "level"),
    [
        ("feat: add x", "minor"),
        ("feat(metamodel-flow): add x (#52)", "minor"),
        ("fix: y", "patch"),
        ("perf(graph): z", "patch"),
        ("chore(deps): bump a", None),
        ("docs: readme", None),
        ("feat!: drop x", "major"),
        ("refactor(api)!: rename", "major"),
        ("fix: y\n\nBREAKING CHANGE: removed z", "major"),
        ("Add agent-context devcontainer feature (#50)", None),
        ("feature: not a type", None),
    ],
)
def test_bump_level(message: str, level: str | None) -> None:
    assert next_version.bump_level(message) == level


@pytest.mark.parametrize(
    ("current", "messages", "expected"),
    [
        ("0.2.0", ["fix: a", "chore: b"], "0.2.1"),
        ("0.2.0", ["fix: a", "feat: b"], "0.3.0"),
        ("0.2.3", ["feat!: a"], "0.3.0"),
        ("1.2.3", ["feat!: a", "fix: b"], "2.0.0"),
        ("1.2.3", ["feat: a"], "1.3.0"),
        ("0.2.0", ["chore: a", "Merge something"], None),
        ("0.2.0", [], None),
    ],
)
def test_next_version(current: str, messages: list[str], expected: str | None) -> None:
    assert next_version.next_version(current, messages) == expected


def test_rejects_invalid_current() -> None:
    with pytest.raises(ValueError):
        next_version.next_version("0.2", ["feat: a"])


def _commit(repo: Path, message: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", message],
        check=True,
        env={
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
            "PATH": "/usr/bin:/bin",
        },
    )


def test_commits_since_detached_release_tag(tmp_path: Path) -> None:
    git = ["git", "-C", str(tmp_path)]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    _commit(tmp_path, "feat: before release")
    subprocess.run([*git, "checkout", "-q", "--detach"], check=True)
    _commit(tmp_path, "chore(release): v0.2.0")
    subprocess.run([*git, "tag", "v0.2.0"], check=True)
    subprocess.run([*git, "tag", "not-a-version"], check=True)
    subprocess.run([*git, "checkout", "-q", "main"], check=True)
    _commit(tmp_path, "fix: after release")

    tag = next_version.last_tag(tmp_path)
    messages = next_version.commit_messages(tag, "HEAD", tmp_path)

    assert tag == "v0.2.0"
    assert messages == ["fix: after release"]
    assert next_version.next_version(tag[1:], messages) == "0.2.1"
