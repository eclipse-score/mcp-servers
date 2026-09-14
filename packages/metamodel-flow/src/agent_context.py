# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Load and validate the generated S-CORE metamodel projection."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class AgentContextValidationError(ValueError):
    """Raised when an agent-context projection violates its contract."""


@dataclass(frozen=True)
class Option:
    name: str
    pattern: str
    required: bool
    inherited: bool


@dataclass(frozen=True)
class BaseOptions:
    mandatory: tuple[Option, ...]
    optional: tuple[Option, ...]


@dataclass(frozen=True)
class ProhibitedWordCheck:
    check: str
    option: str
    applies_to_tags: tuple[str, ...]
    words: tuple[str, ...]


@dataclass(frozen=True)
class LinkType:
    name: str
    outgoing: str | None
    incoming: str | None
    declared: bool


@dataclass(frozen=True)
class LinkUsage:
    name: str
    targets: tuple[str, ...]
    any_target: bool
    required: bool


@dataclass(frozen=True)
class NeedType:
    name: str
    title: str
    prefix: str | None
    tags: tuple[str, ...]
    parts: int | None
    options: tuple[Option, ...]
    links: tuple[LinkUsage, ...]


@dataclass(frozen=True)
class GraphRule:
    name: str
    applies_to: tuple[str, ...]
    condition_raw: JsonValue
    check_raw: JsonValue
    explanation: str


@dataclass(frozen=True)
class AgentContext:
    schema_version: int
    metamodel_digest: str
    base_options: BaseOptions
    prohibited_words: tuple[ProhibitedWordCheck, ...]
    link_types: tuple[LinkType, ...]
    need_types: tuple[NeedType, ...]
    graph_rules: tuple[GraphRule, ...]


def _error(field: str, message: str) -> AgentContextValidationError:
    return AgentContextValidationError(f"{field}: {message}")


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(field, "expected an object")
    if any(not isinstance(key, str) for key in value):
        raise _error(field, "object keys must be strings")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise _error(field, "expected an array")
    return value


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise _error(field, "expected a string")
    return value


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise _error(field, "expected a boolean")
    return value


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(field, "expected an integer")
    return value


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _string(value, field)


def _json_value(value: Any, field: str) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_json_value(item, f"{field}[]") for item in value]
    if isinstance(value, dict):
        mapping = _mapping(value, field)
        return {
            key: _json_value(item, f"{field}.{key}") for key, item in mapping.items()
        }
    raise _error(field, "contains a value that is not valid JSON")


def _option(value: Any, field: str, *, inherited_default: bool = False) -> Option:
    mapping = _mapping(value, field)
    return Option(
        name=_string(mapping.get("name"), f"{field}.name"),
        pattern=_string(mapping.get("pattern"), f"{field}.pattern"),
        required=_boolean(mapping.get("required"), f"{field}.required"),
        inherited=_boolean(
            mapping.get("inherited", inherited_default), f"{field}.inherited"
        ),
    )


def _base_options(value: Any) -> BaseOptions:
    mapping = _mapping(value, "base_options")
    mandatory = tuple(
        Option(
            name=_string(
                _mapping(item, f"base_options.mandatory[{index}]").get("name"),
                f"base_options.mandatory[{index}].name",
            ),
            pattern=_string(
                _mapping(item, f"base_options.mandatory[{index}]").get("pattern"),
                f"base_options.mandatory[{index}].pattern",
            ),
            required=True,
            inherited=True,
        )
        for index, item in enumerate(
            _list(mapping.get("mandatory"), "base_options.mandatory")
        )
    )
    optional = tuple(
        Option(
            name=_string(
                _mapping(item, f"base_options.optional[{index}]").get("name"),
                f"base_options.optional[{index}].name",
            ),
            pattern=_string(
                _mapping(item, f"base_options.optional[{index}]").get("pattern"),
                f"base_options.optional[{index}].pattern",
            ),
            required=False,
            inherited=True,
        )
        for index, item in enumerate(
            _list(mapping.get("optional"), "base_options.optional")
        )
    )
    return BaseOptions(mandatory=mandatory, optional=optional)


def _prohibited_word_check(value: Any, index: int) -> ProhibitedWordCheck:
    field = f"prohibited_words[{index}]"
    mapping = _mapping(value, field)
    return ProhibitedWordCheck(
        check=_string(mapping.get("check"), f"{field}.check"),
        option=_string(mapping.get("option"), f"{field}.option"),
        applies_to_tags=tuple(
            _string(item, f"{field}.applies_to_tags[]")
            for item in _list(
                mapping.get("applies_to_tags"), f"{field}.applies_to_tags"
            )
        ),
        words=tuple(
            _string(item, f"{field}.words[]")
            for item in _list(mapping.get("words"), f"{field}.words")
        ),
    )


def _link_type(value: Any, index: int) -> LinkType:
    field = f"link_types[{index}]"
    mapping = _mapping(value, field)
    outgoing = mapping.get("outgoing")
    incoming = mapping.get("incoming")
    if outgoing is not None:
        outgoing = _string(outgoing, f"{field}.outgoing")
    if incoming is not None:
        incoming = _string(incoming, f"{field}.incoming")
    return LinkType(
        name=_string(mapping.get("name"), f"{field}.name"),
        outgoing=outgoing,
        incoming=incoming,
        declared=_boolean(mapping.get("declared"), f"{field}.declared"),
    )


def _link_usage(value: Any, field: str) -> LinkUsage:
    mapping = _mapping(value, field)
    return LinkUsage(
        name=_string(mapping.get("name"), f"{field}.name"),
        targets=tuple(
            _string(item, f"{field}.targets[]")
            for item in _list(mapping.get("targets"), f"{field}.targets")
        ),
        any_target=_boolean(mapping.get("any_target"), f"{field}.any_target"),
        required=_boolean(mapping.get("required"), f"{field}.required"),
    )


def _need_type(value: Any, index: int) -> NeedType:
    field = f"need_types[{index}]"
    mapping = _mapping(value, field)
    parts = mapping.get("parts")
    return NeedType(
        name=_string(mapping.get("name"), f"{field}.name"),
        title=_string(mapping.get("title"), f"{field}.title"),
        prefix=_optional_string(mapping.get("prefix"), f"{field}.prefix"),
        tags=tuple(
            _string(item, f"{field}.tags[]")
            for item in _list(mapping.get("tags"), f"{field}.tags")
        ),
        parts=None if parts is None else _integer(parts, f"{field}.parts"),
        options=tuple(
            _option(item, f"{field}.options[{option_index}]")
            for option_index, item in enumerate(
                _list(mapping.get("options"), f"{field}.options")
            )
        ),
        links=tuple(
            _link_usage(item, f"{field}.links[{link_index}]")
            for link_index, item in enumerate(
                _list(mapping.get("links"), f"{field}.links")
            )
        ),
    )


def _graph_rule(value: Any, index: int) -> GraphRule:
    field = f"graph_rules[{index}]"
    mapping = _mapping(value, field)
    return GraphRule(
        name=_string(mapping.get("name"), f"{field}.name"),
        applies_to=tuple(
            _string(item, f"{field}.applies_to[]")
            for item in _list(mapping.get("applies_to"), f"{field}.applies_to")
        ),
        condition_raw=_json_value(
            mapping.get("condition_raw"), f"{field}.condition_raw"
        ),
        check_raw=_json_value(mapping.get("check_raw"), f"{field}.check_raw"),
        explanation=_string(mapping.get("explanation"), f"{field}.explanation"),
    )


def _decode(value: Any) -> AgentContext:
    mapping = _mapping(value, "agent_context")
    required_sections = (
        "base_options",
        "prohibited_words",
        "link_types",
        "need_types",
        "graph_rules",
    )
    for section in required_sections:
        if section not in mapping:
            raise _error(section, "missing required section")

    schema_version = mapping.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != 1:
        raise _error("schema_version", "must be 1")
    digest = _string(mapping.get("metamodel_digest"), "metamodel_digest")
    if not _DIGEST_PATTERN.fullmatch(digest):
        raise _error("metamodel_digest", "must match ^sha256:[0-9a-f]{64}$")

    return AgentContext(
        schema_version=schema_version,
        metamodel_digest=digest,
        base_options=_base_options(mapping["base_options"]),
        prohibited_words=tuple(
            _prohibited_word_check(item, index)
            for index, item in enumerate(
                _list(mapping["prohibited_words"], "prohibited_words")
            )
        ),
        link_types=tuple(
            _link_type(item, index)
            for index, item in enumerate(_list(mapping["link_types"], "link_types"))
        ),
        need_types=tuple(
            _need_type(item, index)
            for index, item in enumerate(_list(mapping["need_types"], "need_types"))
        ),
        graph_rules=tuple(
            _graph_rule(item, index)
            for index, item in enumerate(_list(mapping["graph_rules"], "graph_rules"))
        ),
    )


def load_agent_context(path: str | Path) -> AgentContext:
    """Load and validate an agent-context projection from ``path``."""
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AgentContextValidationError(
            f"{source}: unable to load JSON projection: {error}"
        ) from error
    return _decode(value)
