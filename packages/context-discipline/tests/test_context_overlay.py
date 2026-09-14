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
from hashlib import sha256
from pathlib import Path

import pytest
from context_overlay import (
    OverlayEdge,
    OverlayNode,
    OverlayStore,
    Provenance,
)


def provenance() -> Provenance:
    return Provenance("example", "test", 0.9, "2026-01-01T00:00:00+00:00")


def node(node_id: str = "dec__1") -> OverlayNode:
    return OverlayNode(node_id, "dec_rec", "Decision", provenance())


def edge(source: str = "dec__1", target: str = "code__1") -> OverlayEdge:
    return OverlayEdge(source, target, "affects", provenance())


def test_overlay_sharded_round_trip_and_layout(tmp_path: Path) -> None:
    store = OverlayStore(tmp_path)
    store.upsert_node(node())
    store.upsert_edge(edge())
    store.save()

    digest = sha256(b"dec__1\0affects\0code__1").hexdigest()[:16]
    assert sorted(
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*")
        if path.is_file()
    ) == [
        f"score-context/edges/{digest}.json",
        "score-context/meta.json",
        "score-context/nodes/dec__1.json",
    ]
    assert store.meta_path.read_text(encoding="utf-8") == '{\n  "version": 1\n}\n'

    restored = OverlayStore(tmp_path)
    restored.load()
    assert restored.nodes == (node(),)
    assert restored.edges == (edge(),)


def test_shards_for_different_nodes_are_disjoint(tmp_path: Path) -> None:
    first = OverlayStore(tmp_path / "first")
    first.upsert_node(node("first"))
    first.save()
    second = OverlayStore(tmp_path / "second")
    second.upsert_node(node("second"))
    second.save()

    first_files = {path.name for path in first.nodes_dir.glob("*.json")}
    second_files = {path.name for path in second.nodes_dir.glob("*.json")}
    assert first_files.isdisjoint(second_files)


def test_removing_node_deletes_its_shard(tmp_path: Path) -> None:
    store = OverlayStore(tmp_path)
    store.upsert_node(node())
    store.save()
    (store.nodes_dir / "dec__1.json").unlink()
    store.load()
    store.save()
    assert not (store.nodes_dir / "dec__1.json").exists()


def test_legacy_overlay_is_read_then_removed_on_save(tmp_path: Path) -> None:
    store = OverlayStore(tmp_path)
    store.legacy_path.parent.mkdir(parents=True)
    store.legacy_path.write_text(
        json.dumps(
            {
                "version": 1,
                "nodes": [
                    {
                        "id": node().id,
                        "type": node().type,
                        "title": node().title,
                        "provenance": {
                            "repo": "example",
                            "adapter": "test",
                            "confidence": 0.9,
                            "observed_at": "2026-01-01T00:00:00+00:00",
                        },
                        "attributes": {},
                    }
                ],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    store.load()
    assert store.nodes == (node(),)
    store.save()
    assert not store.legacy_path.exists()
    assert (store.nodes_dir / "dec__1.json").exists()


@pytest.mark.parametrize(
    "unsafe_id",
    ["../evil", "a/b", ".hidden", "a\\b", "", "x" * 129],
)
def test_overlay_rejects_unsafe_node_ids(unsafe_id: str) -> None:
    with pytest.raises(ValueError, match="A-Za-z0-9"):
        OverlayNode(unsafe_id, "dec_rec", "Node", provenance())


def test_edge_endpoints_allow_graphify_paths_but_reject_controls() -> None:
    assert OverlayEdge("src/path.py", "target/path.py", "affects", provenance())
    with pytest.raises(ValueError, match="control"):
        OverlayEdge("src\x00path", "target", "affects", provenance())


def test_overlay_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        OverlayNode("x", "unknown", "Node", provenance())
    with pytest.raises(ValueError):
        OverlayEdge("x", "y", "unknown", provenance())
    with pytest.raises(ValueError):
        Provenance("example", "test", 1.5, "now")
    with pytest.raises(ValueError):
        OverlayEdge("", "y", "affects", provenance())
    with pytest.raises(ValueError):
        OverlayEdge("x", "", "affects", provenance())


def test_overlay_save_is_deterministic(tmp_path: Path) -> None:
    first = OverlayStore(tmp_path / "first")
    first.upsert_node(node("b"))
    first.upsert_node(node("a"))
    first.upsert_edge(edge("b", "z"))
    first.upsert_edge(edge("a", "z"))
    first.save()

    second = OverlayStore(tmp_path / "second")
    second.upsert_edge(edge("a", "z"))
    second.upsert_edge(edge("b", "z"))
    second.upsert_node(node("a"))
    second.upsert_node(node("b"))
    second.save()

    first_files = {
        path.relative_to(first.root): path.read_bytes()
        for path in first.root.rglob("*.json")
    }
    second_files = {
        path.relative_to(second.root): path.read_bytes()
        for path in second.root.rglob("*.json")
    }
    assert first_files == second_files
