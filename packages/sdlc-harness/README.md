<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# sdlc-harness

sdlc-harness is a local MCP server package that enforces a traceable SDLC workflow for Eclipse S-CORE style work. It helps an agent:

1. Build structured stage artifacts from a requirement.
2. Check stage preconditions before moving forward.
3. Record implementation evidence per task.
4. Record loopbacks when implementation invalidates an earlier-stage decision.

The package is deterministic and file-backed. No cloud calls are made by the tools.

## What This README Covers

This is an implementation-level README for the package. It documents:

1. Every file in the package and what it does.
2. Every MCP tool and the Python function it dispatches to.
3. Function-by-function behavior, input contracts, outputs, and error conditions.
4. Prompt guidance in .apm/instructions and .apm/skills.

## Package Structure

```text
packages/sdlc-harness/
  apm.yml
  mcp.yml
  README.md
  IMPLEMENTATION.md
  .apm/
    instructions/
      sdlc-lifecycle-stages.instructions.md
      loopback-detection.instructions.md
    skills/
      bootstrap-sdlc-issue/SKILL.md
      write-stage-artifact/SKILL.md
      track-implementation-progress/SKILL.md
      detect-loopback/SKILL.md
  src/sdlc_harness/
    __init__.py
    serve.py
    artifact_writer.py
    implementation_tracking.py
    loopback.py
```

## Runtime Architecture

1. MCP host starts src/sdlc_harness/serve.py over stdio.
2. The server receives newline-delimited JSON-RPC requests.
3. tools/list exposes the tool catalog.
4. tools/call routes to local Python functions.
5. Functions read or write stage artifacts in .stage/ISSUE-ID/.
6. Server returns JSON content wrapped in MCP text payload format.

## File-By-File Reference

### apm.yml

Declares package metadata, supported targets, dependency packages, and MCP process invocation.

Key points:

1. Package name/version: sdlc-harness 0.1.0.
2. Depends on context-discipline and graphify-codegraph at APM level.
3. Declares an MCP stdio process running python3 with serve.py path.

### mcp.yml

Declares the MCP tool contract as schema metadata for APM consumers.

Key points:

1. entry_point is sdlc_harness.serve.
2. Seven tools are declared.
3. Schemas define required fields and enum constraints.

### src/sdlc_harness/__init__.py

Package marker and package docstring.

### src/sdlc_harness/serve.py

MCP stdio transport implementation and dispatcher.

Important behavior:

1. Supports both direct file execution and package-module execution.
2. Defines TOOLS metadata surfaced by tools/list.
3. Implements JSON-RPC methods initialize, tools/list, tools/call.
4. Converts tool exceptions KeyError, OSError, ValueError into JSON-RPC error code -32000.
5. Returns -32601 for unknown protocol method.
6. Ignores notifications/initialized without response.

Main functions:

1. call_tool(name, arguments)
Maps a tool name to the concrete function and passes normalized defaults.

2. response(request_id, result=None, error=None)
Formats a JSON-RPC response object as JSON text.

3. handle(request)
Handles protocol-level dispatch and tool invocation wrapping.

4. main()
Reads stdin line by line and writes responses to stdout.

### src/sdlc_harness/artifact_writer.py

Handles artifact creation, stage completeness checks, SDLC bootstrap, and content quality assessment.

Constants:

1. ARTIFACT_PATHS
Maps artifact type to deterministic numbered file path.

2. STAGE_REQUIREMENTS
Defines required files/directories per stage.

3. SPDX_MARKDOWN
Default SPDX comment header for Markdown artifacts.

Core functions:

1. issue_directory(issue_id, stage_dir=.stage)
Validates issue_id is a single directory name and returns stage path.
Rejected values include empty string, dot entries, and path traversal names.

2. write_stage_artifact(issue_id, artifact_type, title, content, links=None, stage_dir=.stage)
Writes one artifact file with deterministic naming and metadata.
For task artifacts, assigns the next task-NNN.md number.
For plan artifacts, writes YAML format.
For non-plan artifacts, writes Markdown with frontmatter.
Returns path and ok flag.

3. check_stage_completeness(issue_id, stage, stage_dir=.stage)
Checks presence prerequisites only, not semantic quality.
For 05-tasks/ requirement, directory must exist and be non-empty.
Returns complete boolean and list of missing requirements.

4. bootstrap_sdlc_issue(issue_id, title, requirement, stage_dir=.stage)
Creates complete SDLC draft set for a new issue:

- 01-requirement.md
- 02-specification.md
- 03-architecture.md
- 04-plan.yaml
- task-001.md
- task-002.md
- task-003.md

Behavior includes:

1. Fails if issue stage directory already exists and is non-empty.
2. Inserts [DRAFT] placeholders into specification, architecture, plan, and tasks.
3. Returns created paths and explicit next step requiring repository-grounded replacement.

5. assess_sdlc_issue(issue_id, stage_dir=.stage)
Performs semantic status assessment of requirement/spec/architecture/plan/tasks.
Detects:

1. Missing artifacts.
2. Placeholder-heavy artifacts using [DRAFT].
3. Requirement dependency references in requirement text using issue pattern like #179.
4. Missing or incomplete Dependency analysis section when dependencies exist.
5. Missing or placeholder Repository evidence section.

Returns issue summary with per-area status and findings list.

Internal helpers and behavior:

1. _artifact_path
Computes file target, including auto-numbering for task files.

2. _markdown_document, _yaml_document, _frontmatter, _link_lines
Serialize artifacts in Markdown or YAML while preserving links metadata.

3. _specification_draft, _architecture_draft, _plan_draft, _task_one_draft, _task_two_draft, _task_three_draft
Provide deterministic draft text for bootstrap.

4. _read_artifact and _read_task_artifacts
Read existing artifact content for assessment.

5. _artifact_status, _dependency_status, _evidence_status, _tasks_status
Evaluate completeness status categories.

6. _assessment_findings
Converts status results into human-readable blocking findings.

7. _section_content
Regex-based section extractor for Markdown heading blocks.

### src/sdlc_harness/implementation_tracking.py

Records task evidence and computes implementation progress metrics.

Constants:

1. EVIDENCE_FILENAME = implementation-evidence.json
2. VALID_STATUSES = completed, blocked, failed, in_progress

Core functions:

1. record_implementation_evidence(issue_id, task_id, requirement_ids, source_files, tests, status, summary, stage_dir=.stage)

Behavior:

1. Validates status enum.
2. Validates task file exists under 05-tasks.
3. Loads existing evidence entries.
4. Replaces old entry for same task_id (idempotent per task).
5. Sorts entries by task_id.
6. Writes JSON file at harness/implementation-evidence.json.

2. assess_implementation_progress(issue_id, stage_dir=.stage)

Computes:

1. Task totals and completion percentage.
2. Tasks without evidence.
3. Linked requirement ids.
4. Linked source files.
5. Test totals and passed counts.
6. Findings for incomplete tasks, missing evidence, and failing/blocked tests.

Internal helpers:

1. _read_evidence
Returns entries list or validates on-disk format.

2. _progress_findings
Builds issue findings from evidence and test statuses.

3. _percentage
Rounded completion percentage.

### src/sdlc_harness/loopback.py

Records implementation-discovered SDLC loopbacks.

Constants:

1. VALID_STAGES = requirement, specification, architecture, plan, task
2. REVIEW_MARKER = <!-- SDLC-HARNESS: review required -->

Core function:

1. record_loopback(issue_id, trigger, stage_returned_to, affected_artifact, stage_dir=.stage)

Behavior:

1. Validates stage enum.
2. Resolves affected artifact path relative to issue directory when given as relative path.
3. If affected file exists and marker is missing, prepends review marker line.
4. Creates or appends to 08-loopback-log.md.
5. Writes UTC ISO timestamp and loopback metadata.
6. Returns log path and resolved artifact path.

## MCP Tool Reference

The package exposes seven MCP tools:

1. record_implementation_evidence
2. assess_implementation_progress
3. assess_sdlc_issue
4. bootstrap_sdlc_issue
5. write_stage_artifact
6. record_loopback
7. check_stage_completeness

Tool dispatch map in serve.py:

1. record_implementation_evidence -> implementation_tracking.record_implementation_evidence
2. assess_implementation_progress -> implementation_tracking.assess_implementation_progress
3. assess_sdlc_issue -> artifact_writer.assess_sdlc_issue
4. bootstrap_sdlc_issue -> artifact_writer.bootstrap_sdlc_issue
5. write_stage_artifact -> artifact_writer.write_stage_artifact
6. record_loopback -> loopback.record_loopback
7. check_stage_completeness -> artifact_writer.check_stage_completeness

## Stage Artifact Layout

Expected issue workspace under default stage root:

```text
.stage/ISSUE-N/
  01-requirement.md
  02-specification.md
  03-architecture.md
  04-plan.yaml
  05-tasks/
    task-001.md
    task-002.md
    task-003.md
  08-loopback-log.md
  harness/
    implementation-evidence.json
    run.json
```

Notes:

1. harness/run.json is required for review stage completeness checks.
2. check_stage_completeness for review fails without harness/run.json.
3. Markdown artifacts include SPDX and YAML frontmatter links.
4. Plan artifact is YAML, not Markdown.

## Prompt And Skill Guidance (.apm)

The package ships prompt-like guidance in .apm files. These files are not executed by MCP tools themselves. They are consumed by agent packaging/compilation context.

Instruction files:

1. .apm/instructions/sdlc-lifecycle-stages.instructions.md
Defines staged lifecycle behavior, draft replacement requirement, assessment gate, and implementation evidence expectations.

2. .apm/instructions/loopback-detection.instructions.md
Requires record_loopback when implementation exposes upstream gaps.

Skill files:

1. bootstrap-sdlc-issue/SKILL.md
Workflow for starting issue artifacts from one requirement.

2. write-stage-artifact/SKILL.md
Workflow to check prerequisites then write artifacts.

3. track-implementation-progress/SKILL.md
Workflow to record implementation evidence continuously and assess progress.

4. detect-loopback/SKILL.md
Workflow to log lifecycle loopbacks and stop if logging fails.

Important integration note:

1. Registering only .vscode/mcp.json exposes tools but does not automatically load .apm behavioral guidance.
2. Install or compile APM package to apply instructions and skills to agent behavior.

## End-To-End Workflow Example

1. Start staged issue from requirement.

2. Replace draft sections with repository-backed decisions.

3. Run assess_sdlc_issue and resolve all findings.

4. Execute each task and record evidence using record_implementation_evidence.

5. Run assess_implementation_progress before review.

6. If implementation reveals upstream gap, run record_loopback and update affected artifact before proceeding.

## Error Handling And Contracts

Protocol-level behavior:

1. Unknown JSON-RPC method -> -32601.
2. Tool input/IO/validation failures -> -32000.

Tool-level behavior examples:

1. Unknown artifact type or stage enum -> ValueError.
2. Unknown implementation status -> ValueError.
3. Missing task file for evidence recording -> ValueError.

## Local Validation Commands

Run from repository root:

```powershell
$env:PYTHONPATH = "$PWD\packages\sdlc-harness\src"
uv run ruff check packages/sdlc-harness
uv run python -m compileall -q packages/sdlc-harness/src
apm marketplace check --offline
```

Quick stdio MCP handshake test:

```powershell
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' |
  uv run python packages/sdlc-harness/src/sdlc_harness/serve.py
```

## License

Apache License 2.0
