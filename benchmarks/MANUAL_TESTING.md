# Manual Testing Guide

Since we don't have a full LLM integration yet, here's how to manually test the evaluation questions.

## Prerequisites

1. Have access to baselibs or communication repos
2. Have graphify installed: `uv tool install 'graphifyy[mcp]==0.9.70'`
3. Have the central graphs available (or build locally)

## Test Process

### Test 1: Baselibs JSON Parsing (01_json_parsing.yaml)

**Without graph** (traditional approach):
```bash
cd /path/to/baselibs
rg -i "json.*pars|parse.*json" --type cpp -l
rg "nlohmann" --type cpp -l
find score/json -name "*.cpp" -o -name "*.h"
```

Time: ____ seconds
Tools used: grep, rg, find
Confidence: ____ / 10

**With graph**:
```bash
cd /path/to/baselibs
graphify query "show me all JSON parsing related files and functions"
graphify query "what depends on nlohmann json?"
```

Time: ____ seconds
Tools used: graphify query
Confidence: ____ / 10

**Improvement**: ____% faster, ____% more confident

---

### Test 2: Baselibs Logging Mechanism (02_logging_mechanism.yaml)

**Without graph**:
```bash
cd /path/to/baselibs
find score/mw/log -type f -name "*.h" | head -20
rg "class.*LogStream|struct.*LogStream" --type cpp
rg "LOG_INFO|LOG_ERROR|LOG_DEBUG" --type cpp -c | sort -t: -k2 -nr | head -10
```

Time: ____ seconds
Tools used: ____
Confidence: ____ / 10

**With graph**:
```bash
graphify query "show logging classes and their hierarchy"
graphify query "what functions call LOG_INFO?"
```

Time: ____ seconds
Tools used: ____
Confidence: ____ / 10

**Improvement**: ____%

---

### Test 3: Communication Structure (01_mw_com_structure.yaml)

**Without graph**:
```bash
cd /path/to/communication
find score/mw/com -type d | head -20
rg "namespace.*com" --type cpp -l | wc -l
ls -la score/mw/com/impl/
ls -la score/mw/com/bindings/
```

Time: ____ seconds
Confidence: ____ / 10

**With graph**:
```bash
graphify query "show namespace hierarchy in score/mw/com"
graphify query "what modules exist in communication middleware?"
```

Time: ____ seconds
Confidence: ____ / 10

**Improvement**: ____%

---

### Test 4: LoLa Binding (02_lola_binding.yaml)

**Without graph**:
```bash
cd /path/to/communication
find score/mw/com/bindings/lola -name "*.h" -o -name "*.cpp"
rg "class.*Proxy|class.*Skeleton" score/mw/com/bindings/lola --type cpp
rg "shared.?memory" score/mw/com/bindings/lola --type cpp -l
```

Time: ____ seconds
Confidence: ____ / 10

**With graph**:
```bash
graphify query "show me the LoLa binding classes"
graphify query "what classes in lola use shared memory?"
```

Time: ____ seconds
Confidence: ____ / 10

**Improvement**: ____%

---

## Recording Results

After manual testing, record your results:

1. Create results file: `benchmarks/results/<repo>/<id>_manual.json`

```json
{
  "question_id": "01_json_parsing",
  "mode": "manual_test",
  "timestamp": "2026-10-26T...",
  "metrics": {
    "time_ms": 45000,
    "tools_used": ["rg", "find", "grep"],
    "correctness_score": 0.7
  },
  "notes": "Found most components but missed some edge cases",
  "graph_comparison": {
    "graph_time_ms": 5000,
    "graph_correctness": 0.9,
    "improvement_percent": 28.5
  }
}
```

2. Run comparison: `python benchmarks/scripts/compare_results.py`

## Expected Patterns

Based on the plan (F.14), we expect:

| Metric | Without Graph | With Graph | Target |
|--------|---------------|------------|--------|
| Correctness | 60-70% | 80-95% | +20%+ |
| Time | 30-60s | 2-5s | 10x faster |
| Tokens | High | Low | < 30% |

## Quick Test Script

```bash
#!/bin/bash
# Run all manual tests

echo "=== BASELIBS TESTS ==="
echo "Test 1: JSON Parsing"
# ... run commands and time them

echo "Test 2: Logging"
# ... run commands and time them

echo "=== COMMUNICATION TESTS ==="
echo "Test 1: MW/COM Structure"
# ... run commands and time them

echo "Test 2: LoLa Binding"
# ... run commands and time them

echo "=== RESULTS ==="
# Compare and summarize
```

Store results in `benchmarks/results/manual_test_summary.md` for evidence when discussing with maintainers.
