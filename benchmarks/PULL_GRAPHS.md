# How to Pull Pre-Built Graphs from Central Registry

## Overview

Instead of building graphs locally (takes 15-30 seconds), pull them from the central registry built by CI.

## Prerequisites

```bash
# Install ORAS (OCI Registry as Storage)
brew install oras  # macOS
# or download from: https://github.com/oras-project/oras

# Install graphify
uv tool install 'graphifyy[mcp]==0.9.70'
```

## Pull Graph for a Repo

### Option 1: Pull `main` tag (latest)

```bash
cd ~/baselibs  # or any eclipse-score repo

# Pull the latest graph
mkdir -p ~/.local/share/score-agent/baselibs
oras pull ghcr.io/eclipse-score/mcp-servers/graphs/baselibs:main \
  --output ~/.local/share/score-agent/baselibs/graph.tar.gz

# Extract
cd ~/.local/share/score-agent/baselibs/graph.tar.gz
tar -xzf graph.tar.gz

# Verify
cat metadata.json | jq .

# Use it (copy to repo or let graphify find it in cache)
mkdir -p ~/baselibs/graphify-out
cp {graph.json,manifest.json,needs.json} ~/baselibs/graphify-out/
```

### Option 2: Pull specific commit

```bash
# Get the commit SHA
cd ~/baselibs
COMMIT=$(git rev-parse HEAD)

# Pull exact graph for that commit
oras pull ghcr.io/eclipse-score/mcp-servers/graphs/baselibs:${COMMIT} \
  --output ~/.local/share/score-agent/baselibs/graph-${COMMIT}.tar.gz

# Extract
cd ~/.local/share/score-agent/baselibs
mkdir graph-${COMMIT} && cd graph-${COMMIT}
tar -xzf ../graph-${COMMIT}.tar.gz
```

### Option 3: Let graphify-codegraph do it automatically

The lazy loading in `graph_cache.py` will:
1. Check if `graphify-out/graph.json` exists in repo
2. Check user cache `~/.local/share/score-agent/<repo>/`
3. Pull from registry if eclipse-score repo
4. Build locally if no graph available

Just run:
```bash
cd ~/baselibs
graphify-codegraph  # Will auto-pull or build as needed
```

## Available Repositories

Check what's in the registry:

```bash
# List all repos with graphs
oras repository show-tags ghcr.io/eclipse-score/mcp-servers/graphs/baselibs
oras repository show-tags ghcr.io/eclipse-score/mcp-servers/graphs/communication
```

Current graphs built nightly from `known_good.json`.

## Cache Structure

```
~/.local/share/score-agent/
├── baselibs/
│   ├── graph.tar.gz/          # Downloaded tarball
│   │   ├── graph.json
│   │   ├── manifest.json
│   │   ├── needs.json
│   │   └── metadata.json
│   └── metadata.json          # Cache metadata
└── communication/
    └── ...
```

## Benefits

✅ **Fast**: Pull in ~1 second vs 15-30 seconds to build
✅ **Deterministic**: Same graph everyone else uses
✅ **Needs included**: Pre-merged with needs.json from GitHub Pages
✅ **Versioned**: Pull exact commit or latest main

## Testing Right Now

```bash
# Test with baselibs
cd ~/baselibs

# 1. Pull the graph (1-2 seconds)
oras pull ghcr.io/eclipse-score/mcp-servers/graphs/baselibs:main \
  --output /tmp/baselibs-graph.tar.gz

# 2. Extract
cd /tmp && tar -xzf baselibs-graph.tar.gz

# 3. Query it
graphify query "show logging functions" --graph graph.json

# Compare time:
# - Pull + query: ~2-3 seconds total
# - Build + query: ~15-30 seconds total
```

## In Evaluation Tests

For the benchmarks (F.14), use pulled graphs to test:

```bash
cd ~/baselibs

# Ensure graph is available
test -f graphify-out/graph.json || {
  oras pull ghcr.io/eclipse-score/mcp-servers/graphs/baselibs:main --output /tmp/graph.tar.gz
  tar -xzf /tmp/graph.tar.gz -C graphify-out/
}

# Run test
time graphify query "show JSON parsing files"
```

This ensures fast, reproducible tests without building graphs every time.
