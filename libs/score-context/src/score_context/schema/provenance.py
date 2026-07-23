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

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceRef(BaseModel):
    """Natural source location observed by an adapter."""

    model_config = ConfigDict(extra="forbid")

    repo: str = Field(min_length=1)
    ref: str = Field(min_length=1)
    sha: str | None = None


class Provenance(BaseModel):
    """Audit information attached to every graph object."""

    model_config = ConfigDict(extra="forbid")

    repo: str = Field(min_length=1)
    sha: str | None = None
    adapter: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    observed_at: datetime
