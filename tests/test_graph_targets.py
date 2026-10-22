# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "graph_targets.py"
spec = importlib.util.spec_from_file_location("graph_targets", SCRIPT)
assert spec is not None and spec.loader is not None
graph_targets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph_targets)

SHA = "ee40fece5abacb28ea641b448446a04175038b17"


def test_targets_selects_eclipse_score_repos() -> None:
    modules = {
        "modules": {
            "target_sw": {
                "score_baselibs": {
                    "repo": "https://github.com/eclipse-score/baselibs.git",
                    "hash": SHA,
                },
                "score_itf": {"repo": "https://github.com/eclipse-score/itf.git"},
                "duplicate": {"repo": "https://github.com/eclipse-score/itf"},
                "foreign": {"repo": "https://github.com/other/repo.git"},
                "injected": {"repo": "https://github.com/eclipse-score/$(id).git"},
            },
            "tooling": {
                "score_tooling": {
                    "repo": "https://github.com/eclipse-score/tooling.git",
                }
            },
        }
    }

    assert graph_targets.targets(modules, ["target_sw"]) == [
        {"name": "baselibs"},
        {"name": "itf"},
    ]
    assert len(graph_targets.targets(modules, ["target_sw", "tooling"])) == 3
