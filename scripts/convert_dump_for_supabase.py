#!/usr/bin/env python3
"""Convert pg_dump COPY format to plain SQL for Supabase SQL Editor."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_copy_blocks(content: str) -> list[tuple[str, list[str], list[list[str]]]]:
    blocks: list[tuple[str, list[str], list[list[str]]]] = []
    lines = content.splitlines()
    index = 0
    copy_re = re.compile(r"^COPY public\.(\w+) \((.+)\) FROM stdin;$")

    while index < len(lines):
        match = copy_re.match(lines[index])
        if not match:
            index += 1
            continue

        table = match.group(1)
        columns = [part.strip() for part in match.group(2).split(",")]
        index += 1
        rows: list[list[str]] = []

        while index < len(lines) and lines[index] != "\\.":
            row_line = lines[index]
            if row_line.strip():
                rows.append(row_line.split("\t"))
            index += 1

        if index < len(lines) and lines[index] == "\\.":
            index += 1

        blocks.append((table, columns, rows))

    return blocks


def sql_value(raw: str, column: str) -> str:
    if raw == r"\N":
        return "NULL"
    if column in {"approved", "real_estate_enabled"}:
        return "TRUE" if raw == "t" else "FALSE"
    if column in {"amount", "sort_order", "id"} and re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
        return raw
    escaped = raw.replace("'", "''")
    return f"'{escaped}'"


def convert(src: Path, dst: Path) -> None:
    text = src.read_text(encoding="utf-8")
    schema_end = text.index("COPY public.")
    schema_part = text[:schema_end]
    skip_prefixes = ("SELECT pg_catalog.set_config",)
    schema_lines = [
        line
        for line in schema_part.splitlines()
        if not any(line.strip().startswith(prefix) for prefix in skip_prefixes)
    ]
    parts = ["\n".join(schema_lines).strip(), ""]
    blocks = parse_copy_blocks(text)
    order = {"documents": 0, "document_approvers": 1, "diadoc_sync_state": 2}
    blocks.sort(key=lambda item: order.get(item[0], 99))

    for table, columns, rows in blocks:
        if not rows:
            continue
        values = []
        for row in rows:
            if len(row) != len(columns):
                raise ValueError(f"Column mismatch in {table}: {row}")
            rendered = ", ".join(sql_value(value, column) for value, column in zip(row, columns))
            values.append(f"  ({rendered})")
        col_list = ", ".join(columns)
        parts.append(f"INSERT INTO public.{table} ({col_list}) VALUES\n" + ",\n".join(values) + ";")
        parts.append("")

    seq_match = re.search(
        r"SELECT pg_catalog\.setval\('public\.document_approvers_id_seq', (\d+), true\);",
        text,
    )
    if seq_match:
        parts.append(f"SELECT setval('public.document_approvers_id_seq', {seq_match.group(1)}, true);")
        parts.append("")

    constraint_start = text.index("-- Name: diadoc_sync_state diadoc_sync_state_pkey")
    parts.append(text[constraint_start:].strip())

    dst.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    src = ROOT / "veles_backup.sql"
    dst = ROOT / "veles_backup_supabase.sql"
    if len(sys.argv) >= 2:
        src = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        dst = Path(sys.argv[2])
    convert(src, dst)
    blocks = parse_copy_blocks(src.read_text(encoding="utf-8"))
    print(f"Wrote {dst}")
    for table, _, rows in blocks:
        print(f"  {table}: {len(rows)} rows")


if __name__ == "__main__":
    main()
