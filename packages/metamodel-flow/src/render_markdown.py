# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Contributors to the Eclipse Foundation

"""Render the validated S-CORE metamodel projection as APM instructions."""

from __future__ import annotations

import argparse
import difflib
import json
from collections.abc import Sequence
from pathlib import Path

from agent_context import (
    AgentContext,
    GraphRule,
    LinkType,
    LinkUsage,
    NeedType,
    Option,
    load_agent_context,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WRITE_COMMAND = "python src/render_markdown.py --write"


def _option_line(option: Option) -> str:
    qualifier = "mandatory" if option.required else "optional"
    return f"- `{option.name}` ({qualifier}): `{option.pattern}`"


def _targets(link: LinkUsage) -> str:
    if link.any_target:
        return "any target (`*`)"
    return ", ".join(f"`{target}`" for target in sorted(link.targets))


def _link_line(link: LinkUsage) -> str:
    qualifier = "mandatory" if link.required else "optional"
    return f"- `{link.name}` ({qualifier}; targets: {_targets(link)})"


def _render_need_type(need_type: NeedType) -> list[str]:
    lines = [f"### `{need_type.name}` — {need_type.title}"]
    if need_type.tags:
        lines.append(f"Tags: {', '.join(f'`{tag}`' for tag in sorted(need_type.tags))}")
    if need_type.prefix is not None:
        lines.append(f"Prefix: `{need_type.prefix}`")
    if need_type.parts is not None:
        lines.append(f"Parts: `{need_type.parts}`")
    lines.append("")

    options = sorted(need_type.options, key=lambda option: option.name)
    mandatory_options = [option for option in options if option.required]
    optional_options = [option for option in options if not option.required]
    links = sorted(need_type.links, key=lambda link: link.name)
    mandatory_links = [link for link in links if link.required]
    optional_links = [link for link in links if not link.required]

    if mandatory_options:
        lines.append("**Mandatory options**")
        lines.extend(_option_line(option) for option in mandatory_options)
        lines.append("")
    if mandatory_links:
        lines.append("**Mandatory links**")
        lines.extend(_link_line(link) for link in mandatory_links)
        lines.append("")
    if optional_options:
        lines.append("**Optional options**")
        lines.extend(_option_line(option) for option in optional_options)
        lines.append("")
    if optional_links:
        lines.append("**Optional links**")
        lines.extend(_link_line(link) for link in optional_links)
        lines.append("")
    return lines


def _raw_text(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _render_graph_rule(rule: GraphRule) -> list[str]:
    applies_to = ", ".join(f"`{name}`" for name in sorted(rule.applies_to))
    return [
        f"### `{rule.name}`",
        f"Applies to: {applies_to}",
        "",
        "Condition:",
        "```text",
        _raw_text(rule.condition_raw),
        "```",
        "",
        "Check:",
        "```text",
        _raw_text(rule.check_raw),
        "```",
        "",
        f"Explanation: {rule.explanation}",
        "",
    ]


def _render_link_type(link_type: LinkType) -> str:
    if link_type.declared:
        return (
            f"- `{link_type.name}` — declared; outgoing `{link_type.outgoing}`, "
            f"incoming `{link_type.incoming}`."
        )
    return f"- `{link_type.name}` — undeclared built-in link type."


def render_markdown(context: AgentContext) -> str:
    """Render ``context`` into deterministic APM instruction Markdown."""
    lines = [
        "<!-- SPDX-License-Identifier: Apache-2.0 -->",
        "<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->",
        "",
        "---",
        "name: score-artifact-model",
        "description: Normative S-CORE artifact model — need types, options, "
        "links and graph rules",
        'applyTo: "**/*.rst"',
        "---",
        "",
        "# S-CORE Artifact Model",
        "",
        "> Generated from the `docs-as-code` metamodel projection. Do not edit "
        "this file by hand.",
        f"> Regenerate with `{WRITE_COMMAND}`.",
        f"> Metamodel digest: `{context.metamodel_digest}`.",
        "",
        "## Base options",
        "",
    ]
    base_options = sorted(
        (*context.base_options.mandatory, *context.base_options.optional),
        key=lambda option: option.name,
    )
    lines.extend(_option_line(option) for option in base_options)
    lines.extend(["", "## Need types", ""])
    for need_type in sorted(context.need_types, key=lambda item: item.name):
        lines.extend(_render_need_type(need_type))

    lines.extend(["## Link types", ""])
    lines.extend(
        _render_link_type(link_type)
        for link_type in sorted(context.link_types, key=lambda item: item.name)
    )
    lines.extend(["", "## Graph rules", ""])
    for rule in sorted(context.graph_rules, key=lambda item: item.name):
        lines.extend(_render_graph_rule(rule))

    lines.extend(["## Prohibited words", ""])
    for check in sorted(
        context.prohibited_words, key=lambda item: (item.check, item.option)
    ):
        tags = (
            ", ".join(f"`{tag}`" for tag in sorted(check.applies_to_tags))
            if check.applies_to_tags
            else "all tags"
        )
        words = ", ".join(f"`{word}`" for word in sorted(check.words))
        lines.append(f"- `{check.check}` checks `{check.option}` for {tags}: {words}.")
    lines.append("")
    return "\n".join(lines)


def _paths(package_root: Path) -> tuple[Path, Path]:
    return (
        package_root / "model" / "agent_context.json",
        package_root / ".apm" / "instructions" / "score-artifact-model.instructions.md",
    )


def write_output(package_root: Path) -> None:
    model_path, instruction_path = _paths(package_root)
    instruction_path.parent.mkdir(parents=True, exist_ok=True)
    instruction_path.write_text(
        render_markdown(load_agent_context(model_path)), encoding="utf-8"
    )


def check_output(package_root: Path) -> int:
    model_path, instruction_path = _paths(package_root)
    expected = render_markdown(load_agent_context(model_path))
    actual = (
        instruction_path.read_text(encoding="utf-8")
        if instruction_path.is_file()
        else ""
    )
    if actual == expected:
        return 0
    diff = "".join(
        difflib.unified_diff(
            actual.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=str(instruction_path),
            tofile="fresh render",
        )
    )
    print(
        f"Generated instructions are out of date. Run `{WRITE_COMMAND}`.\n{diff}",
        end="",
    )
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true", help="write generated Markdown")
    modes.add_argument(
        "--check", action="store_true", help="check committed Markdown for drift"
    )
    parser.add_argument(
        "--package-root",
        type=Path,
        default=PACKAGE_ROOT,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    if args.write:
        write_output(args.package_root)
        return 0
    return check_output(args.package_root)


if __name__ == "__main__":
    raise SystemExit(main())
