# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
"""review-watch.fabro: check script routing against fixture reviews and a fake gh."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

WORKFLOW = Path(__file__).resolve().parents[1] / "workflows" / "review-watch.fabro"
HEAD = "a" * 40
OLD = "b" * 40
AUTHOR = "author-user"
URL = "https://github.com/OWNER/REPO/pull/7"

requires_jq = pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed")
requires_fabro = pytest.mark.skipif(
    shutil.which("fabro") is None, reason="fabro CLI not installed"
)


def _check_script() -> str:
    """Return the unescaped check_review script from the checked-in DOT file."""
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r'check_review \[.*?script="((?:[^"\\]|\\.)*)"', text)
    assert match, "check_review script not found"
    return match.group(1).replace('\\"', '"').replace("\\\\", "\\")


def _fake_gh(bin_dir: Path, reviews: list[dict[str, Any]]) -> None:
    """Fake gh that answers the three pulls/ lookups and the reviews listing."""
    fixture = bin_dir / "reviews.json"
    fixture.write_text(json.dumps(reviews), encoding="utf-8")
    script = bin_dir / "gh"
    script.write_text(
        "#!/bin/sh\n"
        'jqexpr=""\n'
        'for arg in "$@"; do\n'
        '  if [ "$prev" = "--jq" ]; then jqexpr="$arg"; fi\n'
        '  prev="$arg"\n'
        "done\n"
        'case "$*" in\n'
        '  *"/reviews"*) jq -c "$jqexpr" ' + str(fixture) + " ;;\n"
        '  *) case "$jqexpr" in\n'
        f"       .user.login) echo {AUTHOR} ;;\n"
        f"       .head.sha) echo {HEAD} ;;\n"
        f"       .html_url) echo {URL} ;;\n"
        "     esac ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    script.chmod(0o755)


def _review(user: str, state: str, commit: str, at: str) -> dict[str, Any]:
    return {
        "user": {"login": user},
        "state": state,
        "commit_id": commit,
        "submitted_at": at,
    }


def _route(tmp_path: Path, reviews: list[dict[str, Any]]) -> dict[str, Any]:
    _fake_gh(tmp_path, reviews)
    script = _check_script()
    command = script.replace("{{ inputs.repo }}", "OWNER/REPO").replace(
        "{{ inputs.pr }}", "7"
    )
    result = subprocess.run(
        ["sh", "-c", command],
        capture_output=True,
        text=True,
        env={"PATH": f"{tmp_path}:/usr/bin:/bin"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@requires_jq
@pytest.mark.parametrize(
    ("reviews", "expected"),
    [
        ([], "pending"),
        ([_review("reviewer-a", "APPROVED", HEAD, "2026-11-01T10:00:00Z")], "approved"),
        # The author's own approval never counts.
        ([_review(AUTHOR, "APPROVED", HEAD, "2026-11-01T10:00:00Z")], "pending"),
        # An approval on an older commit does not cover the current head.
        ([_review("reviewer-a", "APPROVED", OLD, "2026-11-01T10:00:00Z")], "pending"),
        ([_review("reviewer-a", "COMMENTED", HEAD, "2026-11-01T10:00:00Z")], "pending"),
        (
            [_review("reviewer-a", "CHANGES_REQUESTED", HEAD, "2026-11-01T10:00:00Z")],
            "changes_requested",
        ),
        # Latest review per reviewer wins: a later approval clears the request.
        (
            [
                _review(
                    "reviewer-a", "CHANGES_REQUESTED", HEAD, "2026-11-01T10:00:00Z"
                ),
                _review("reviewer-a", "APPROVED", HEAD, "2026-11-02T10:00:00Z"),
            ],
            "approved",
        ),
        # An outstanding request from anyone blocks approval.
        (
            [
                _review("reviewer-a", "APPROVED", HEAD, "2026-11-01T10:00:00Z"),
                _review(
                    "reviewer-b", "CHANGES_REQUESTED", HEAD, "2026-11-02T10:00:00Z"
                ),
            ],
            "changes_requested",
        ),
    ],
)
def test_check_script_routes_review_state(
    tmp_path: Path, reviews: list[dict[str, Any]], expected: str
) -> None:
    routing = _route(tmp_path, reviews)
    assert routing["preferred_next_label"] == expected
    assert routing["context_updates"]["review_head"] == HEAD
    assert routing["context_updates"]["review_target"] == {
        "label": "PR #7",
        "url": URL,
        "kind": "document",
    }


def test_workflow_has_no_local_approval_edges() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "[A] Approve" not in text
    assert "[R] Revise" not in text
    assert "hexagon" in text  # the author decision gate is still present


def test_only_approved_route_reaches_record_approval() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    into_record = re.findall(r"-> record_approved \[([^\]]*)\]", text)
    assert into_record == ['label="approved", condition="preferred_label=approved"']


def test_fallback_for_unrecognized_routing_is_pending_not_approved() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    fallback = re.search(r"check_review -> (\w+) \[label=\"unrecognized[^\]]*\]", text)
    assert fallback and fallback.group(1) == "wait_review"


@requires_fabro
def test_review_watch_passes_fabro_validate(tmp_path: Path) -> None:
    target = tmp_path / "review-watch.fabro"
    shutil.copyfile(WORKFLOW, target)
    result = subprocess.run(
        ["fabro", "validate", str(target)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    # The only expected warning is the unbound run-time inputs (repo, pr).
    warnings = [line for line in output.splitlines() if line.startswith("warning:")]
    assert all("unbound_input" in line for line in warnings), output
