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
"""APM only reads frontmatter that starts on the first line of a file."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APM_DOCS = sorted(ROOT.glob("packages/*/.apm/**/*.md"))


@pytest.mark.parametrize("path", APM_DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_frontmatter_is_first(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "\n---\n" not in text and not text.startswith("---\n"):
        pytest.skip("no frontmatter")
    assert text.startswith("---\n"), "frontmatter must start on line 1"
