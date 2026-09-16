#!/usr/bin/env python3
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

"""Stdio MCP server entry point for the SDLC Harness package."""

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from sdlc_harness.artifact_writer import (
        assess_sdlc_issue,
        bootstrap_sdlc_issue,
        check_stage_completeness,
        write_stage_artifact,
    )
    from sdlc_harness.implementation_tracking import (
        assess_implementation_progress,
        record_implementation_evidence,
        write_sphinx_progress_report,
    )
    from sdlc_harness.loopback import record_loopback
else:
    from .artifact_writer import (
        assess_sdlc_issue,
        bootstrap_sdlc_issue,
        check_stage_completeness,
        write_stage_artifact,
    )
    from .implementation_tracking import (
        assess_implementation_progress,
        record_implementation_evidence,
        write_sphinx_progress_report,
    )
    from .loopback import record_loopback

TOOLS = [
    {
        "name": "record_implementation_evidence",
        "description": (
            "Link a completed, blocked, failed, or in-progress task to "
            "requirement IDs, source files, and real test results."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string"},
                "task_id": {"type": "string"},
                "requirement_ids": {"type": "array", "items": {"type": "string"}},
                "source_files": {"type": "array", "items": {"type": "string"}},
                "tests": {"type": "array", "items": {"type": "object"}},
                "status": {
                    "type": "string",
                    "enum": ["completed", "blocked", "failed", "in_progress"],
                },
                "summary": {"type": "string"},
                "stage_dir": {"type": "string", "default": ".stage"},
            },
            "required": [
                "issue_id",
                "task_id",
                "requirement_ids",
                "source_files",
                "tests",
                "status",
                "summary",
            ],
        },
    },
    {
        "name": "assess_implementation_progress",
        "description": (
            "Report task completion percentage, linked source files, requirement IDs, "
            "and test evidence."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string"},
                "stage_dir": {"type": "string", "default": ".stage"},
            },
            "required": ["issue_id"],
        },
    },
    {
        "name": "write_sphinx_progress_report",
        "description": (
            "Write an RST progress report with a task table and sphinx-needs needflow."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string"},
                "report_path": {"type": "string"},
                "stage_dir": {"type": "string", "default": ".stage"},
            },
            "required": ["issue_id", "report_path"],
        },
    },
    {
        "name": "assess_sdlc_issue",
        "description": (
            "Assess SDLC artifact content for unresolved drafts, requirement "
            "dependencies, repository evidence, plans, and tasks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string"},
                "stage_dir": {"type": "string", "default": ".stage"},
            },
            "required": ["issue_id"],
        },
    },
    {
        "name": "bootstrap_sdlc_issue",
        "description": (
            "Create a complete review-marked SDLC draft from one requirement. "
            "The client must replace [DRAFT] sections using repository evidence "
            "before implementation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string"},
                "title": {"type": "string"},
                "requirement": {"type": "string"},
                "stage_dir": {"type": "string", "default": ".stage"},
            },
            "required": ["issue_id", "title", "requirement"],
        },
    },
    {
        "name": "write_stage_artifact",
        "description": "Write an SDLC stage artifact.",
        "inputSchema": {
            "type": "object",
            "required": ["issue_id", "artifact_type", "title", "content"],
        },
    },
    {
        "name": "record_loopback",
        "description": "Record an SDLC loopback event.",
        "inputSchema": {
            "type": "object",
            "required": [
                "issue_id",
                "trigger",
                "stage_returned_to",
                "affected_artifact",
            ],
        },
    },
    {
        "name": "check_stage_completeness",
        "description": "Check SDLC stage prerequisites.",
        "inputSchema": {"type": "object", "required": ["issue_id", "stage"]},
    },
]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch an MCP tool call to its implementation."""
    if name == "record_implementation_evidence":
        return record_implementation_evidence(
            arguments["issue_id"],
            arguments["task_id"],
            arguments["requirement_ids"],
            arguments["source_files"],
            arguments["tests"],
            arguments["status"],
            arguments["summary"],
            arguments.get("stage_dir", ".stage"),
        )
    if name == "assess_implementation_progress":
        return assess_implementation_progress(
            arguments["issue_id"], arguments.get("stage_dir", ".stage")
        )
    if name == "write_sphinx_progress_report":
        return write_sphinx_progress_report(
            arguments["issue_id"],
            arguments["report_path"],
            arguments.get("stage_dir", ".stage"),
        )
    if name == "assess_sdlc_issue":
        return assess_sdlc_issue(
            arguments["issue_id"], arguments.get("stage_dir", ".stage")
        )
    if name == "bootstrap_sdlc_issue":
        return bootstrap_sdlc_issue(
            arguments["issue_id"],
            arguments["title"],
            arguments["requirement"],
            arguments.get("stage_dir", ".stage"),
        )
    if name == "write_stage_artifact":
        return write_stage_artifact(
            arguments["issue_id"],
            arguments["artifact_type"],
            arguments["title"],
            arguments["content"],
            arguments.get("links"),
            arguments.get("stage_dir", ".stage"),
        )
    if name == "record_loopback":
        return record_loopback(
            arguments["issue_id"],
            arguments["trigger"],
            arguments["stage_returned_to"],
            arguments["affected_artifact"],
            arguments.get("stage_dir", ".stage"),
        )
    if name == "check_stage_completeness":
        return check_stage_completeness(
            arguments["issue_id"],
            arguments["stage"],
            arguments.get("stage_dir", ".stage"),
        )
    raise ValueError(f"Unknown tool: {name}")


def response(
    request_id: Any, result: Any = None, error: dict[str, Any] | None = None
) -> str:
    """Serialize one JSON-RPC response."""
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is None:
        payload["result"] = result
    else:
        payload["error"] = error
    return json.dumps(payload)


def handle(request: dict[str, Any]) -> str | None:
    """Handle the MCP initialize, tool discovery, and tool call methods."""
    method = request.get("method")
    if method == "notifications/initialized":
        return None
    request_id = request.get("id")
    if method == "initialize":
        return response(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "sdlc-harness", "version": "0.1.0"},
            },
        )
    if method == "tools/list":
        return response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = request.get("params", {})
        try:
            result = call_tool(params["name"], params.get("arguments", {}))
            return response(
                request_id, {"content": [{"type": "text", "text": json.dumps(result)}]}
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            return response(request_id, error={"code": -32000, "message": str(exc)})
        except Exception as exc:
            return response(
                request_id, error={"code": -32000, "message": f"Internal error: {exc}"}
            )
    return response(
        request_id, error={"code": -32601, "message": f"Unknown method: {method}"}
    )


def main() -> None:
    """Serve newline-delimited JSON-RPC requests over standard I/O."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            output = handle(json.loads(line))
        except (json.JSONDecodeError, TypeError) as exc:
            output = response(
                None,
                error={"code": -32700, "message": f"Invalid JSON-RPC request: {exc}"},
            )
        except Exception as exc:
            output = response(
                None,
                error={"code": -32603, "message": f"Server error: {exc}"},
            )
        if output is not None:
            sys.stdout.write(output + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
