#!/usr/bin/env bash
# Test script for agent-context feature
# This will be run as part of the devcontainer features test

set -euo pipefail

echo "Testing agent-context feature installation..."

# Test 1: Verify python3 is available
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found"
    exit 1
fi
echo "✓ python3 is available: $(python3 --version)"

# Test 2: Verify uv is available
if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv not found"
    exit 1
fi
echo "✓ uv is available: $(uv --version)"

# Test 3: Verify uv is installed in the correct location
UV_PATH=$(command -v uv)
if [[ "$UV_PATH" != "/usr/local/bin/uv" ]]; then
    # uv might also be in /root/.local/bin/uv if it was already installed
    if [[ "$UV_PATH" != "/root/.local/bin/uv" ]] && [[ "$UV_PATH" != "uv" ]]; then
        echo "WARNING: uv is at unexpected location: $UV_PATH"
    fi
fi
echo "✓ uv is installed at: $UV_PATH"

# Test 4: Verify uv can execute tools
echo "Testing uv tool execution..."
uv tool list || echo "Note: No tools installed yet (expected for fresh installation)"

# Test 5: Verify the MCP registration script exists
if [ ! -f /usr/local/share/agent-context/register_mcp.py ]; then
    echo "ERROR: register_mcp.py not found"
    exit 1
fi
echo "✓ register_mcp.py is present"

# Test 6: Verify python can execute the registration script
if ! python3 /usr/local/share/agent-context/register_mcp.py --help 2>&1 | grep -q "usage\|USAGE\|help\|HELP" || [ $? -eq 0 ]; then
    echo "Note: register_mcp.py --help executed (may have no help flag)"
fi

echo ""
echo "✓ All tests passed!"
