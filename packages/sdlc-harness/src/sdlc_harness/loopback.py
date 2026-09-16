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

"""Record SDLC loopbacks discovered during implementation."""

from datetime import UTC, datetime
from pathlib import Path

from .artifact_writer import issue_directory

VALID_STAGES = {"requirement", "specification", "architecture", "plan", "task"}
REVIEW_MARKER = "<!-- SDLC-HARNESS: review required -->"


def record_loopback(
    issue_id: str,
    trigger: str,
    stage_returned_to: str,
    affected_artifact: str,
    stage_dir: str = ".stage",
) -> dict[str, str]:
    """Append a loopback event and mark the affected artifact for review."""
    if stage_returned_to not in VALID_STAGES:
        raise ValueError(f"Unknown SDLC stage: {stage_returned_to}")

    issue_dir = issue_directory(issue_id, stage_dir)
    issue_dir.mkdir(parents=True, exist_ok=True)
    affected_path = Path(affected_artifact)
    if not affected_path.is_absolute():
        affected_path = issue_dir / affected_path
    if affected_path.exists():
        text = affected_path.read_text(encoding="utf-8")
        if REVIEW_MARKER not in text:
            affected_path.write_text(f"{REVIEW_MARKER}\n{text}", encoding="utf-8")

    log_path = issue_dir / "08-loopback-log.md"
    if not log_path.exists():
        spdx_header = (
            f"<!-- {'SPDX-' + 'License-Identifier'}: Apache-2.0 -->\n\n# Loopback Log\n"
        )
        log_path.write_text(spdx_header, encoding="utf-8")
    timestamp = datetime.now(UTC).isoformat()
    with log_path.open("a", encoding="utf-8") as log:
        log.write(
            f"\n## {timestamp}\n\n"
            f"- Trigger: {trigger}\n"
            f"- Return to: {stage_returned_to}\n"
            f"- Affected artifact: {affected_path}\n"
        )
    return {
        "ok": "true",
        "log_path": str(log_path),
        "affected_artifact": str(affected_path),
    }
