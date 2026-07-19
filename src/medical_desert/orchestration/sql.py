from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

_TOKEN = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CATALOG_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def validate_variables(variables: Mapping[str, str]) -> None:
    for key in ("project_catalog", "source_catalog", "source_schema"):
        value = variables[key]
        pattern = _CATALOG_IDENTIFIER if key.endswith("catalog") else _IDENTIFIER
        if not pattern.fullmatch(value):
            raise ValueError(f"Unsafe SQL identifier for {key}: {value!r}")
    for key in ("source_bundle_id", "policy_version", "geography_version"):
        value = variables[key]
        if not value or any(char in value for char in ("'", ";", "\x00")):
            raise ValueError(f"Unsafe SQL literal for {key}")


def render_sql(template: str, variables: Mapping[str, str]) -> str:
    validate_variables(variables)
    missing = sorted(set(_TOKEN.findall(template)) - set(variables))
    if missing:
        raise KeyError(f"Missing SQL template variables: {', '.join(missing)}")
    rendered = _TOKEN.sub(lambda match: variables[match.group(1)], template)
    unresolved = _TOKEN.findall(rendered)
    if unresolved:
        raise ValueError(f"Unresolved SQL template variables: {unresolved}")
    return rendered


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if in_line_comment:
            buffer.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            buffer.append(char)
            if char == "*" and next_char == "/":
                buffer.append(next_char)
                index += 2
                in_block_comment = False
            else:
                index += 1
            continue

        if not in_single_quote and not in_double_quote:
            if char == "-" and next_char == "-":
                buffer.extend((char, next_char))
                index += 2
                in_line_comment = True
                continue
            if char == "/" and next_char == "*":
                buffer.extend((char, next_char))
                index += 2
                in_block_comment = True
                continue

        if char == "'" and not in_double_quote:
            if in_single_quote and next_char == "'":
                buffer.extend((char, next_char))
                index += 2
                continue
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
        else:
            buffer.append(char)
        index += 1

    trailing = "".join(buffer).strip()
    if trailing:
        statements.append(trailing)
    return statements


def read_and_render(path: Path, variables: Mapping[str, str]) -> str:
    return render_sql(path.read_text(encoding="utf-8"), variables)


def write_rendered_sql(path: Path, statements: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ";\n\n".join(statement.rstrip("; \n") for statement in statements) + ";\n"
    path.write_text(content, encoding="utf-8")
