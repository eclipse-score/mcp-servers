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


def test_overlay_round_trip(tmp_path: Path) -> None:
    store = OverlayStore(tmp_path)
    store.upsert_node(node())
    store.upsert_edge(edge())
    store.save()

    restored = OverlayStore(tmp_path)
    restored.load()
    assert restored.nodes == (node(),)
    assert restored.edges == (edge(),)


def test_overlay_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        OverlayNode("x", "unknown", "Node", provenance())
    with pytest.raises(ValueError):
        OverlayEdge("x", "y", "unknown", provenance())
    with pytest.raises(ValueError):
        Provenance("example", "test", 1.5, "now")


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

    assert (first.path.read_bytes()) == second.path.read_bytes()
