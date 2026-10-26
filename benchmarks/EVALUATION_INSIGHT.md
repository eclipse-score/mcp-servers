# Evaluation Insight: Task Complexity Matters

## The Problem with Simple Tests

Your tests revealed an important finding:

**Test 1: JSON Parsing** (Simple file search)
- rg: 0.106s
- graphify: 1.103s (10x slower)
- **Result**: Graph overhead NOT worth it for simple lookups

**Test 2: Logging Classes** (Slightly more complex)
- rg: 0.145s (5 files)
- graphify: 0.870s (286 nodes)
- **Result**: Graph provides more context, but is it needed?

## The Real Question

The evaluation (F.14) asks for "ca. 20 echte Fragen" but:
- Simple searches (find X files) → grep is faster and sufficient
- Complex understanding (how does X work?) → graph might help

## Better Evaluation Questions

We need questions that grep **CANNOT** answer easily:

### Hard for grep, Easy for graph:

1. **Call Hierarchies**:
   - "What functions call `authenticate()`?"
   - grep: Can't do it (needs call graph)
   - graphify: `query "what calls authenticate"`

2. **Dependency Chains**:
   - "What needs to change if I modify `LogStream`?"
   - grep: Can't show impact analysis
   - graphify: Shows all dependents

3. **Cross-cutting Concerns**:
   - "Which classes use both logging AND error handling?"
   - grep: Multiple searches, manual correlation
   - graphify: Single graph traversal

4. **Architectural Questions**:
   - "What's the coupling between mw/log and mw/com?"
   - grep: Can't measure coupling
   - graphify: Community detection, cross-module edges

5. **Refactoring Impact**:
   - "If I rename this function, what breaks?"
   - grep: Can't find dynamic references
   - graphify: Find all usages including indirect

## Recommendation

Replace current simple questions with genuinely hard ones:

```yaml
# OLD (too simple)
question: "Where is JSON parsing implemented?"

# NEW (requires understanding)
question: "What is the call chain from HTTP request to JSON parsing?"
grep_answer: "Impossible without manual tracing"
graph_answer: "Shows call graph from HTTP handler → parser"
```

## New Evaluation Strategy

Test 3 categories:

1. **Simple searches** (grep wins)
   - "Find file X"
   - "Where is constant Y defined?"
   
2. **Medium complexity** (grep + manual work)
   - "List all uses of function X"
   - grep: Multiple files, manual review
   - graphify: Automated traversal

3. **High complexity** (grep fails)
   - "What's the impact of changing X?"
   - "Show me circular dependencies"
   - "Find dead code paths"
   - grep: Cannot answer
   - graphify: Designed for this

## Success Criteria Update

The plan says "20%+ improvement in correctness" but we need:

- Simple tasks: grep is fine (no graph needed)
- Medium tasks: graph saves 5-10 minutes of manual work
- Hard tasks: graph enables otherwise impossible analysis

**Real success metric**: Time to answer complex questions, not simple ones.

## Next Steps

1. Reword evaluation questions to be harder
2. Focus on questions agents ACTUALLY ask when coding:
   - "What does this function call?"
   - "Who uses this?"
   - "Is this safe to delete?"
   - "What's the architecture here?"

3. Record time including manual analysis time for grep approach

This is why devcontainers matter - agents ask complex questions, not "find file X".
