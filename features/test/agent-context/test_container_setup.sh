#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation
set -euo pipefail

python3 - <<'PY'
import json
import os
from pathlib import Path

home = Path.home()
workspace = Path.cwd()
config_path = (
    Path(os.environ["VSCODE_AGENT_FOLDER"]) / "data" / "User" / "mcp.json"
)
config = json.loads(config_path.read_text(encoding="utf-8"))
servers = config["servers"]
assert set(servers) == {"existing-server", "graphify-codegraph", "apm-setup"}, servers
assert config["inputs"] == []
assert Path(servers["graphify-codegraph"]["command"]).is_file()
setup_server = servers["apm-setup"]
assert setup_server["type"] == "stdio"
assert Path(setup_server["command"]).is_file()
assert Path(setup_server["args"][2]).is_dir()
assert (home / ".agents/skills/map-repository-graph/SKILL.md").is_file()
assert (home / ".agents/skills/setup-agent-context/SKILL.md").is_file()
assert not (home / ".copilot/mcp-config.json").exists()
for generated in (
    "apm.yml",
    "apm.lock.yaml",
    "apm_modules",
    ".apm",
    ".agents",
    ".copilot",
    ".github",
    ".vscode",
    "graphify-out",
    ".score-local",
):
    assert not (workspace / generated).exists(), workspace / generated
PY

echo "container APM setup passed without consumer-repository output"
