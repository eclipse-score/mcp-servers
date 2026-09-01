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

## Common utilities for setup scripts

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
info() {
	echo -e "${BLUE}ℹ${NC} $*"
}

success() {
	echo -e "${GREEN}✓${NC} $*"
}

warn() {
	echo -e "${YELLOW}⚠${NC} $*"
}

error() {
	echo -e "${RED}✗${NC} $*"
}

die() {
	error "$@"
	exit 1
}

# Check if command exists
command_exists() {
	command -v "$1" >/dev/null 2>&1
}

# Prompt user for yes/no confirmation
confirm() {
	local prompt="$1"
	local response
	read -p "$(echo -e "${BLUE}${prompt}${NC}") [y/N] " -n 1 -r response
	echo
	[[ "${response}" =~ ^[Yy]$ ]]
}

# Prompt user for input
prompt() {
	local prompt="$1"
	local default="$2"
	local response
	
	if [[ -n "${default}" ]]; then
		read -p "$(echo -e "${BLUE}${prompt}${NC}") [${default}]: " response
		echo "${response:-${default}}"
	else
		read -p "$(echo -e "${BLUE}${prompt}${NC}"): " response
		echo "${response}"
	fi
}

# Run command and handle errors
run_cmd() {
	local cmd="$*"
	info "Running: $cmd"
	if eval "$cmd"; then
		return 0
	else
		error "Command failed: $cmd"
		return 1
	fi
}

# Check if file/directory exists
path_exists() {
	[[ -e "$1" ]]
}

# Get directory of this script
get_script_dir() {
	cd "$(dirname "${BASH_SOURCE[0]}")"
	pwd -P
}
