<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

# sdlc-harness

sdlc-harness is a local MCP server package that enforces a traceable SDLC workflow for Eclipse S-CORE style work. It helps an agent:

1. Build structured stage artifacts from a requirement.
2. Check stage preconditions before moving forward.
3. Record implementation evidence per task.
4. Record loopbacks when implementation invalidates an earlier-stage decision.

The package is deterministic and file-backed. No cloud calls are made by the tools.

## Graph-Backed Evidence

The APM package depends on `context-discipline` and `graphify-codegraph`. Its lifecycle guidance uses `query_graph` to locate relevant code and `resolve_requirements` to verify requirement IDs and links, then requires confirming findings against source files and tests before recording evidence. Graphs are discovery and traceability aids, not authoritative source content. The `agent-context` devcontainer feature registers the Graphify MCP server, but does not install these APM instructions or the SDLC harness; consumers need an APM deployment for the workflow guidance and tools.

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
  src/
    serve.py
    artifact_writer.py
    implementation_tracking.py
    loopback.py
```

## Runtime Architecture

1. MCP host starts src/serve.py over stdio.
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

1. entry_point is serve.
2. Seven tools are declared.
3. Schemas define required fields and enum constraints.


### src/serve.py

MCP stdio transport implementation and dispatcher.

Important behavior:

1. Supports direct file execution from the src directory.
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

### src/artifact_writer.py

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

### src/implementation_tracking.py

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

### src/loopback.py

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
```

Notes:

1. harness/implementation-evidence.json is required for review stage completeness checks.
2. check_stage_completeness for review fails without harness/implementation-evidence.json.
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

## Local Fabro MVP

The SDLC lifecycle can also run as a Fabro workflow on a local model. No cloud key and no remote server are needed. This section records what was verified and what is still missing.

Verified with Fabro `0.415.0-nightly.0` (newest published build, Homebrew tap `fabro-sh/tap`, formula SHA-256 matched the GitHub release digest) and LM Studio on macOS arm64.

### Files

- `workflows/local-smoke.fabro`: one agent node that checks the local model answers through Fabro.
- `workflows/sdlc-lifecycle.fabro`: the 13-node SDLC lifecycle. It is generated by `src/graphify_fabro_conversion.py` and a test fails if the two diverge:

  ```bash
  python src/graphify_fabro_conversion.py sdlc ISSUE-1 \
    --requirement "Example requirement: replace with the requirement text" \
    -o workflows/sdlc-lifecycle.fabro
  ```

### Setup

1. Install Fabro. The `apm-setup` MCP tool `setup_fabro` with `install_fabro=true` does this, or run:

   ```bash
   brew tap fabro-sh/tap
   brew trust --formula fabro-sh/tap/fabro-nightly
   brew install fabro-sh/tap/fabro-nightly
   fabro --version
   ```

2. Start LM Studio's local server (port 1234) and load one model with tool calling. Check which models are loaded with `curl -s localhost:1234/api/v0/models`. `/v1/models` lists downloaded models too, not only loaded ones.

3. Create `~/.fabro/settings.toml`. Replace `<model-id>` with the loaded model's id:

   ```toml
   _version = 1

   [llm.providers.lmstudio]
   display_name = "LM Studio (local)"
   base_url = "http://localhost:1234/v1"
   auth = { type = "none" }

   [llm.providers.lmstudio.models."<model-id>"]
   display_name = "LM Studio local model"
   api_model = "<model-id>"
   limits = { context_tokens = 32768, max_output_tokens = 4096 }
   capabilities = { text = true, tools = true, reasoning = "unknown" }

   [llm.providers.lmstudio.models."<model-id>".metadata.agent]
   reasoning_by_default = false

   [server.auth]
   methods = ["dev-token"]

   [server.web]
   enabled = false
   ```

   `context_tokens` is a guess. Set it to the context length LM Studio actually loaded.

4. Create `~/.fabro/storage/server.env` with mode 600:

   ```text
   SESSION_SECRET=<output of: openssl rand -hex 32>
   FABRO_DEV_TOKEN=fabro_dev_<output of: openssl rand -hex 32>
   ```

5. Start the local daemon and log the CLI in with the dev token. The token is read from the file, so it does not appear on the command line:

   ```bash
   fabro server start
   fabro auth login --dev-token "$(grep '^FABRO_DEV_TOKEN=' ~/.fabro/storage/server.env | cut -d= -f2-)"
   ```

### Run

Run from a directory that is not a git checkout. See finding 6.

```bash
W=/path/to/mcp-servers/packages/sdlc-harness/workflows
fabro validate $W/local-smoke.fabro
fabro run --provider lmstudio --model <model-id> --environment local \
  --auto-approve $W/local-smoke.fabro
fabro run --dry-run --provider lmstudio --model <model-id> --environment local \
  --auto-approve $W/sdlc-lifecycle.fabro
```

Results on the verified setup:

- `local-smoke.fabro` ran to `SUCCEEDED` and printed `HELLO FROM LM STUDIO`.
- `sdlc-lifecycle.fabro` dry-run `SUCCEEDED`, visiting all 11 executable nodes.

### Findings

1. **Native validation is the real gate.** Round-trip tests only prove the DOT is self-consistent. `fabro validate` found problems they missed: 13 unreachable nodes in the process workflow, goal gates without a `retry_target`, unbounded loops, and a non-standard `approvers` attribute. The generator now sets retry targets, loop caps (`max_node_visits`, plus `max_visits` on key nodes), and a human "Select process activity" gate that reaches every process workflow. The tests in `tests/test_workflows.py` and the `fabro validate` integration tests in `tests/test_graphify_fabro_conversion.py` guard these.
2. **`fabro run` needs a local daemon.** `run`, `model list`, `model test`, and `graph` all start a daemon on `~/.fabro/fabro.sock`. It is a local process, not remote infrastructure. The docs call `fabro run` a direct CLI run. On this setup it is not.
3. **Dev-token login is required.** Once auth is enabled, the daemon does not write the `server.dev-token` file the CLI waits for. The fix is step 5 above. Removing `FABRO_DEV_TOKEN` makes startup fail, so keep it.
4. **An environment must be named.** The server has no `default` environment, so `--environment local` is required. `local` runs shell tools directly on the host.
5. **Local model settings.** The model needs `reasoning = "unknown"` and `reasoning_by_default = false`. Without them the follow-up turn fails with "does not support reasoning". Shell tools need `--permissions full` in `fabro exec`. `fabro exec` is a direct single-session path with no daemon. It is useful for checking the model, but it does not run a workflow graph.
6. **Dry runs are not side-effect free in a git checkout.** The docs say `--dry-run` may still fetch and upload workflow source, and that target observation can publish committed changes. In a checkout of this repository a dry run pushed `fabro-sdlc-workflow` to `origin`. The branch was deleted afterwards. Run workflows from a non-git directory.
7. **Do not hard-code a cloud model.** An earlier generated file carried `model_stylesheet = "* { model: claude-sonnet-4-5; }"`. The run was rejected because LM Studio is not a cloud provider. The generator only emits a stylesheet when `--model` is given. Choose the model with `--provider` and `--model` on `fabro run`.
8. **Human gates need `--auto-approve` for non-interactive runs.** This applies to the review gate in the SDLC workflow and to the process activity gate.
9. **The SDLC lifecycle cannot produce artifacts yet.** Its agent nodes are instructed to call the sdlc-harness MCP tools (`bootstrap_sdlc_issue`, `assess_sdlc_issue`, and others). The runs have no MCP servers configured, so those calls cannot happen. A real run would walk the graph without writing `.stage/` artifacts. Wiring the tools through `[run.agent.mcps]` is the next step.
10. **Fabro version.** The nightly channel is the newest published build and it is unpinned. Stable `v0.254.0` is older and lacks workflow-version registration, which the `s-core_sw_fabric` runtime contract depends on. Pin a specific build once a runtime is chosen.

### Review Watcher Prototype

`workflows/review-watch.fabro` is the in-run GitHub review gate. It polls a pull request and continues only when a reviewer other than the author approves the current head commit. Approval comes from GitHub, not from a local command.

```bash
fabro run workflows/review-watch.fabro -I repo=OWNER/REPO -I pr=NUMBER \
  --environment local --auto-approve
```

Routing:

- `approved` goes to `record_approved` and then exit.
- `pending` and any unrecognised routing go through a 5-minute wait back to the check. Unrecognised routing is treated as pending, so it can never approve.
- `changes_requested` goes to a human gate. The gate shows the PR as `review_target`. `[A]` lets the agent address the feedback, `[S]` stops.
- A failed check (`gh` error) goes to exit. The goal gate then fails the run.

The check node is a single `gh api` script. It reads the REST reviews endpoint, not `latestReviews` from GraphQL, because the REST `commit_id` is the reviewed commit. The rule:

- Ignore the author's own reviews.
- Use each reviewer's latest approval or change request.
- Any outstanding change request blocks approval.
- An approval counts only on the current head commit.

Verified:

- Live approved run against PR #74 (approved on its head): `SUCCEEDED`.
- Live pending run against PR #78 (no reviews): the check, wait and re-check loop ran, then the run failed closed when the visit budget ran out (`node 1 exceeded its firing budget`).
- The check script is tested by `tests/test_review_watch.py`. That file runs the exact script from the DOT file against a fake `gh` and fixture reviews. It covers approval by the author, approval on an older commit, comments only, changes requested, a later approval after a request, and a request from a second reviewer.

Findings:

1. **`latestReviews` is unreliable for approvals.** The approval on PR #74 had an empty `commit.oid`. The REST endpoint reports the reviewed commit in `commit_id`.
2. **`gh api --paginate --slurp` does not work with `--jq`.** The script uses `per_page=100` instead, so only the first 100 reviews are read.
3. **`jq` 1.7 rejects `+` inside an object value without parentheses.** `gh`'s built-in jq accepts it, so the bug only shows up in local tests. The script uses parentheses.
4. **A live `gh` call works inside a Fabro worker with the local environment,** so the worker doesn't need a token passed in.
5. **Live tests can't cover changes requested or approval by someone else.** The only logged-in account here is the PR author, so those paths are tested with fixtures only.
6. **The 5-minute wait is not tested for stall timeouts yet.** The 24-hour cap comes from `max_visits=288`. Whether a long wait trips `stall_timeout` is still open.
7. **`fabro validate` warns about unbound inputs** (`repo`, `pr`). That is expected because inputs are bound at run time. `fabro preflight -I` returned no detail in this setup.

### Not Yet Done

- Expose the sdlc-harness MCP tools to workflow agents.
- A real (non-dry) SDLC lifecycle run that produces `.stage/` artifacts.
- Running the process-derived workflows beyond validation.
- Pinning the Fabro build.

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
uv run pytest packages/sdlc-harness/tests
fabro validate packages/sdlc-harness/workflows/sdlc-lifecycle.fabro
fabro validate packages/sdlc-harness/workflows/local-smoke.fabro
apm marketplace check --offline
```

The `fabro validate` lines need the Fabro CLI on `PATH`. The pytest suite skips its Fabro checks when the CLI is missing.

Quick stdio MCP handshake test:

```powershell
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' |
  uv run python packages/sdlc-harness/src/serve.py
```

## License

Apache License 2.0
