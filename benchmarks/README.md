# Agent Intelligence Evaluation Harness

Evaluates the effectiveness of graph-based code understanding for AI agents.

## Purpose

Before approaching devcontainer maintainers (G.16), we need evidence that:
1. Graph-based queries improve answer quality
2. The overhead is acceptable (time, tokens)
3. Real-world questions benefit from the graph

## Structure

```
benchmarks/
├── questions/
│   ├── baselibs/
│   │   ├── 01_auth_functions.yaml
│   │   ├── 02_error_handling.yaml
│   │   └── ...
│   └── communication/
│       ├── 01_mw_com_structure.yaml
│       └── ...
├── results/
│   ├── baselibs/
│   └── communication/
├── scripts/
│   ├── run_eval.py           # Main evaluation runner
│   ├── compare_results.py    # Compare with/without graph
│   └── generate_report.py    # Create summary report
└── README.md
```

## Running Evaluations

```bash
# Run all benchmarks
uv run python benchmarks/scripts/run_eval.py --all

# Run specific repo
uv run python benchmarks/scripts/run_eval.py --repo baselibs

# Run single question
uv run python benchmarks/scripts/run_eval.py --question baselibs/01_auth_functions

# Force re-run
uv run python benchmarks/scripts/run_eval.py --all --force

# Generate report
uv run python benchmarks/scripts/generate_report.py
```

## Success Criteria

- ✅ Graph mode shows 20%+ improvement in correctness for code structure questions
- ✅ Average query time < 5 seconds
- ✅ Token overhead < 30% increase
- ✅ Graph build cache hit rate > 80% (for repos with central graphs)

## Question Format

Each question in `questions/<repo>/<id>.yaml`:

```yaml
id: 01_auth_functions
category: code_structure
difficulty: easy  # easy, medium, hard
question: |
  What authentication functions exist in the codebase?
expected_answer: |
  List of function names and their locations:
  - authenticate() in score/mw/auth/auth.cpp:45
  - validate_token() in score/mw/auth/token.cpp:23
  - ...
validation:
  must_include:
    - authenticate
    - validate_token
  should_include:
    - token_expiration
  forbidden:
    - deprecated_auth
graph_expected_features:
  - Function nodes with 'auth' in name
  - Call edges to auth functions
```

## Results Format

Results stored in `results/<repo>/<id>_graph.json` and `results/<repo>/<id>_nograph.json`:

```json
{
  "question_id": "01_auth_functions",
  "mode": "graph",
  "timestamp": "2026-10-26T...",
  "metrics": {
    "time_ms": 1234,
    "tokens_used": 567,
    "correctness_score": 0.95
  },
  "answer": "...",
  "validation": {
    "must_include_passed": true,
    "should_include_score": 0.8,
    "forbidden_violated": false
  },
  "graph_metrics": {
    "cache_hit": true,
    "graph_load_time_ms": 234,
    "query_time_ms": 1000
  }
}
```

## Extending

To add new questions:

1. Create `questions/<repo>/<id>.yaml`
2. Define question, expected answer, validation criteria
3. Run: `uv run python benchmarks/scripts/run_eval.py --question <repo>/<id>`
4. Review result and adjust validation if needed

## Automation

The evaluation can be run:
- Manually during development
- In CI on a schedule (weekly/before releases)
- Before submitting PRs to devcontainer repo

Results are committed to show evidence of effectiveness.
