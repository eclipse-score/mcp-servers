#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

# Validate mcp-servers repository structure without APM CLI

set -euo pipefail

echo "=== Repository Validation ==="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass=0
fail=0

# Check function
check() {
	local name="$1"
	local cmd="$2"
	
	if eval "$cmd" > /dev/null 2>&1; then
		echo -e "${GREEN}✓${NC} $name"
		((pass++))
	else
		echo -e "${RED}✗${NC} $name"
		((fail++))
	fi
}

# 1. License headers
echo "1. License Headers"
py_missing=$(find packages -name "*.py" 2>/dev/null | xargs grep -L "SPDX-License-Identifier" | wc -l)
bash_missing=$(find scripts -name "*.sh" 2>/dev/null | xargs grep -L "SPDX-License-Identifier" 2>/dev/null | wc -l)

if [ "$py_missing" -eq 0 ]; then
	echo -e "${GREEN}✓${NC} All Python files have SPDX headers"
	((pass++))
else
	echo -e "${RED}✗${NC} $py_missing Python files missing SPDX headers"
	((fail++))
fi

if [ "$bash_missing" -eq 0 ]; then
	echo -e "${GREEN}✓${NC} All Bash files have SPDX headers"
	((pass++))
else
	echo -e "${RED}✗${NC} $bash_missing Bash files missing SPDX headers"
	((fail++))
fi

echo ""
echo "2. Package Structure"

for pkg in packages/graphify-codegraph packages/context-discipline; do
	pkg_name=$(basename "$pkg")
	
	check "  $pkg_name: apm.yml" "test -f $pkg/apm.yml"
	check "  $pkg_name: mcp.yml" "test -f $pkg/mcp.yml"
	check "  $pkg_name: README.md" "test -f $pkg/README.md"
	check "  $pkg_name: .apm/" "test -d $pkg/.apm"
	check "  $pkg_name: .apm/instructions/" "test -d $pkg/.apm/instructions"
	check "  $pkg_name: .apm/skills/" "test -d $pkg/.apm/skills"
done

echo ""
echo "3. Setup Scripts"

check "  ./do executable" "test -x ./do"
check "  scripts/setup-graphify executable" "test -x scripts/setup-graphify"
check "  scripts/setup-context-discipline executable" "test -x scripts/setup-context-discipline"
check "  scripts/setup-common.sh readable" "test -r scripts/setup-common.sh"

echo ""
echo "4. Documentation"

check "  README.md exists" "test -f README.md"
check "  AGENTS.md exists" "test -f AGENTS.md"
check "  CONTRIBUTION.md exists" "test -f CONTRIBUTION.md"

echo ""
echo "5. Python Modules"

check "  context-discipline: __init__.py" "test -f packages/context-discipline/src/__init__.py"
check "  context-discipline: context_discipline_mcp.py" "test -f packages/context-discipline/src/context_discipline_mcp.py"
check "  graphify-codegraph: __init__.py" "test -f packages/graphify-codegraph/src/__init__.py"
check "  graphify-codegraph: serve.py" "test -f packages/graphify-codegraph/src/serve.py"

echo ""
echo "6. Git Configuration"

check "  .gitignore exists" "test -f .gitignore"
check "  .gitignore has .score-local/" "grep -q '.score-local/' .gitignore"
check "  .gitignore has graphify-out/" "grep -q 'graphify-out/' .gitignore"
check "  .gitignore has .working-memory/" "grep -q '.working-memory/' .gitignore"

echo ""
echo "=== Summary ==="
echo -e "Passed: ${GREEN}$pass${NC}"
echo -e "Failed: ${RED}$fail${NC}"

if [ "$fail" -eq 0 ]; then
	echo -e "${GREEN}✓ All checks passed!${NC}"
	exit 0
else
	echo -e "${RED}✗ Some checks failed${NC}"
	exit 1
fi
