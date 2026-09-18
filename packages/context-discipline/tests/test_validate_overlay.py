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

import json
import subprocess
import sys
from pathlib import Path

from context_overlay import OverlayNode, OverlayStore, Provenance

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "validate_overlay.py"


def make_store(path: Path, title: str = "Decision") -> OverlayStore:
    store = OverlayStore(path)
    store.upsert_node(
        OverlayNode(
            "dec__1",
            "dec_rec",
            title,
            Provenance("example", "test", 0.9, "2026-01-01T00:00:00Z"),
        )
    )
    store.save()
    return store


def run_validator(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(path), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def node_payload(path: Path) -> tuple[Path, dict[str, object]]:
    shard = path / "score-context" / "nodes" / "dec__1.json"
    return shard, json.loads(shard.read_text(encoding="utf-8"))


def test_clean_fixture_passes(tmp_path: Path) -> None:
    make_store(tmp_path)
    result = run_validator(tmp_path)
    assert result.returncode == 0
    assert "overlay: valid" in result.stdout


def test_invalid_policy_version_fails_without_overlay_shards(tmp_path: Path) -> None:
    policy_path = tmp_path / "score-context" / "policy.toml"
    policy_path.parent.mkdir()
    policy_path.write_text("version = 9\n", encoding="utf-8")

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "unknown policy version" in result.stdout


def test_unknown_policy_key_fails_without_overlay_shards(tmp_path: Path) -> None:
    policy_path = tmp_path / "score-context" / "policy.toml"
    policy_path.parent.mkdir()
    policy_path.write_text("version = 1\n[overlay]\nunknown = 1\n", encoding="utf-8")

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "unknown policy key" in result.stdout


def test_legacy_overlay_file_fails_validation(tmp_path: Path) -> None:
    overlay_path = tmp_path / "score-context" / "overlay.json"
    overlay_path.parent.mkdir()
    overlay_path.write_text(
        '{"version": 1, "nodes": [], "edges": []}\n', encoding="utf-8"
    )

    result = run_validator(tmp_path)

    assert result.returncode == 1
    assert "legacy single-file overlay must be migrated to shards" in result.stdout


def test_bad_node_type_fails(tmp_path: Path) -> None:
    make_store(tmp_path)
    shard, payload = node_payload(tmp_path)
    payload["type"] = "not-a-node-type"
    shard.write_text(json.dumps(payload), encoding="utf-8")
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "unknown overlay node type" in result.stdout


def test_overlong_title_fails(tmp_path: Path) -> None:
    make_store(tmp_path)
    shard, payload = node_payload(tmp_path)
    payload["title"] = "x" * 201
    shard.write_text(json.dumps(payload), encoding="utf-8")
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "max_title_chars" in result.stdout


def test_too_many_attributes_fails(tmp_path: Path) -> None:
    make_store(tmp_path)
    shard, payload = node_payload(tmp_path)
    payload["attributes"] = {f"key{index}": "value" for index in range(21)}
    shard.write_text(json.dumps(payload), encoding="utf-8")
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "max_attributes" in result.stdout


def test_lowered_node_count_limit_fails(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.upsert_node(
        OverlayNode(
            "dec__2",
            "dec_rec",
            "Second",
            Provenance("example", "test", 0.9, "2026-01-01T00:00:00Z"),
        )
    )
    store.save()
    (tmp_path / "score-context" / "policy.toml").write_text(
        "version = 1\n[overlay]\nmax_nodes = 1\n",
        encoding="utf-8",
    )
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "max_nodes" in result.stdout


def test_renamed_node_shard_fails(tmp_path: Path) -> None:
    make_store(tmp_path)
    shard, _ = node_payload(tmp_path)
    shard.rename(shard.with_name("wrong.json"))
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "filename does not match node id" in result.stdout


def test_fake_secret_value_fails_without_printing_value(tmp_path: Path) -> None:
    make_store(tmp_path)
    shard, payload = node_payload(tmp_path)
    fake_value = "AKIAFAKEFAKEFAKEFAKE"
    payload["attributes"] = {"note": fake_value}
    shard.write_text(json.dumps(payload), encoding="utf-8")
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "aws-access-key" in result.stdout
    assert fake_value not in result.stdout


def test_email_in_title_fails(tmp_path: Path) -> None:
    make_store(tmp_path, "Contact test@example.invalid")
    result = run_validator(tmp_path)
    assert result.returncode == 1
    assert "email-address" in result.stdout
    assert "test@example.invalid" not in result.stdout


def test_added_file_limit_fails(tmp_path: Path) -> None:
    make_store(tmp_path)
    (tmp_path / "score-context" / "policy.toml").write_text(
        "version = 1\n[overlay]\nmax_added_nodes_per_change = 0\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Overlay Test"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "base"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "add", "score-context"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "overlay"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    result = run_validator(tmp_path, "--base", base)
    assert result.returncode == 1
    assert "max_added_nodes_per_change" in result.stdout
