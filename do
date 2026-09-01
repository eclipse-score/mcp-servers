#!/usr/bin/env bash

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

# MCP Servers task runner
# Run: ./do <task> [args]
# Available tasks can be discovered by running: ./do

set -euo pipefail

script_dir="$(cd "$(dirname "${0}")"; pwd -P)"

function task_usage() {
	echo "Usage: ${0} <task> [args...]"
	echo ""
	echo "Available tasks:"
	for script in "${script_dir}"/scripts/setup-*; do
		if [[ -f "$script" ]] && [[ -x "$script" ]] && [[ "$(basename "$script")" != "setup-common.sh" ]]; then
			task_name=$(basename "$script")
			help=$(grep '^##' "$script" 2>/dev/null | head -1 | sed 's/^##[[:space:]]*//')
			printf "  %-30s %s\n" "$task_name" "$help"
		fi
	done | sort
	echo ""
	echo "Examples:"
	echo "  ./do setup-graphify          # Interactive setup wizard"
	echo "  ./do setup-graphify --help   # Show help"
}

cmd=${1:-}
if [[ -z "$cmd" ]]; then
	task_usage
	exit 1
fi
shift || true

cmd_script="${script_dir}/scripts/${cmd}"
if [[ -f ${cmd_script} ]] && [[ -x ${cmd_script} ]]; then
	"${cmd_script}" "$@"
else
	task_usage
	exit 1
fi
