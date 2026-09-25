"""
Convert the Mermaid ER diagram docs/schema/star_schema.mmd into DBML and
render it as an SVG diagram.

Outputs
  docs/schema/star_schema.dbml   DBML source (paste into dbdiagram.io or dbdocs)
  docs/schema/star_schema.svg    diagram rendered by @softwaretechnik/dbml-renderer

Mapping rules
  - Each Mermaid entity becomes a DBML Table; PK attributes get [pk].
  - The quoted Mermaid comment becomes the column note.
  - A relationship `Parent ||--o{ Child : Column` becomes a many-to-one Ref
    between Child.Column and Parent.<PK of Parent>. Every second Ref is
    written as `Parent.PK < Child.FK` (same meaning) so Graphviz places the
    dimensions on both sides of the fact table instead of one tall column.
  - Header colour by prefix: Fact* red, everything else blue. No TableGroup is
    emitted because the renderer draws groups as clusters, which would force
    all dimensions back into a single column.

Usage:  python scripts/mmd_to_dbml.py [--no-svg]
The SVG step needs Node.js (npx) and network access on first run.
Exit code 0 = success, 1 = parse or render failure.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "docs" / "schema"
MMD = SCHEMA / "star_schema.mmd"
DBML = SCHEMA / "star_schema.dbml"
SVG = SCHEMA / "star_schema.svg"

RENDERER = "@softwaretechnik/dbml-renderer"
FACT_COLOR = "#C0392B"
DIM_COLOR = "#2E86C1"

# `Parent ||--o{ Child : label`  (label may be quoted)
REL_RE = re.compile(
    r'^(?P<left>\w+)\s+(?P<lcard>\|\||\|o|o\||\}o|o\}|\}\||\|\})'
    r'(?:--|\.\.)(?P<rcard>\|\||\|o|o\||\}o|o\{|\|\{|\{o|\{\|)\s+(?P<right>\w+)'
    r'\s*:\s*"?(?P<label>[^"]+?)"?\s*$'
)
ENTITY_START_RE = re.compile(r"^(?P<name>\w+)\s*\{\s*$")
ATTR_RE = re.compile(
    r'^(?P<type>[\w()\[\],]+)\s+(?P<name>\w+)'
    r'(?:\s+(?P<keys>(?:PK|FK|UK)(?:\s*,\s*(?:PK|FK|UK))*))?'
    r'(?:\s+"(?P<comment>[^"]*)")?\s*$'
)


@dataclass
class Column:
    name: str
    type: str
    keys: list[str] = field(default_factory=list)
    comment: str = ""


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)

    @property
    def pk(self) -> list[Column]:
        return [c for c in self.columns if "PK" in c.keys]

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)


@dataclass
class Relationship:
    left: str
    right: str
    left_many: bool
    right_many: bool
    label: str


def is_many(card: str) -> bool:
    return "{" in card or "}" in card


def parse_mermaid(text: str) -> tuple[dict[str, Table], list[Relationship]]:
    tables: dict[str, Table] = {}
    rels: list[Relationship] = []
    current: Table | None = None

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("%%", 1)[0].strip()
        if not line or line == "erDiagram":
            continue

        if current is not None:
            if line == "}":
                current = None
                continue
            m = ATTR_RE.match(line)
            if not m:
                raise ValueError(f"line {lineno}: cannot parse attribute: {raw!r}")
            keys = [k.strip() for k in (m["keys"] or "").split(",") if k.strip()]
            current.columns.append(
                Column(m["name"], m["type"], keys, m["comment"] or "")
            )
            continue

        m = ENTITY_START_RE.match(line)
        if m:
            current = tables.setdefault(m["name"], Table(m["name"]))
            continue

        m = REL_RE.match(line)
        if m:
            rels.append(
                Relationship(
                    m["left"], m["right"],
                    is_many(m["lcard"]), is_many(m["rcard"]),
                    m["label"].strip(),
                )
            )
            continue

        raise ValueError(f"line {lineno}: unrecognised Mermaid syntax: {raw!r}")

    if current is not None:
        raise ValueError(f"entity {current.name} is not closed with '}}'")
    return tables, rels


def quote(text: str) -> str:
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def ref_line(rel: Relationship, tables: dict[str, Table], flip: bool = False) -> str:
    """Resolve a Mermaid relationship label into a column-level DBML Ref.

    flip=True writes a many-to-one Ref from the parent side (`P.pk < C.fk`);
    the meaning is identical, only the Graphviz edge direction changes.
    """
    for name in (rel.left, rel.right):
        if name not in tables:
            raise ValueError(f"relationship references unknown entity {name}")

    if rel.left_many and not rel.right_many:
        parent, child, op = tables[rel.right], tables[rel.left], ">"
    elif rel.right_many and not rel.left_many:
        parent, child, op = tables[rel.left], tables[rel.right], ">"
    else:
        parent, child = tables[rel.left], tables[rel.right]
        op = "<>" if rel.left_many else "-"

    child_col = child.column(rel.label)
    if child_col is None:
        raise ValueError(f"{child.name} has no column {rel.label} (from relationship label)")
    parent_col = parent.column(rel.label) or (parent.pk[0] if len(parent.pk) == 1 else None)
    if parent_col is None:
        raise ValueError(f"cannot resolve referenced column in {parent.name} for {rel.label}")
    if flip and op == ">":
        return f"Ref: {parent.name}.{parent_col.name} < {child.name}.{child_col.name}"
    return f"Ref: {child.name}.{child_col.name} {op} {parent.name}.{parent_col.name}"


def to_dbml(tables: dict[str, Table], rels: list[Relationship]) -> str:
    out: list[str] = [
        f"// Generated by scripts/mmd_to_dbml.py from {MMD.relative_to(ROOT).as_posix()}.",
        "// Do not edit by hand: change the .mmd file and re-run the script.",
        "",
        "Project internship_scam_dw {",
        "  database_type: 'SQL Server'",
        "  Note: 'Star Schema v1 - internship postings and internship scam analysis'",
        "}",
        "",
    ]

    for t in tables.values():
        color = FACT_COLOR if t.name.startswith("Fact") else DIM_COLOR
        out.append(f"Table {t.name} [headercolor: {color}] {{")
        width = max(len(c.name) for c in t.columns)
        type_width = max(len(c.type) for c in t.columns)
        for c in t.columns:
            settings = []
            if "PK" in c.keys:
                settings.append("pk")
            if "UK" in c.keys:
                settings.append("unique")
            if c.comment:
                settings.append(f"note: {quote(c.comment)}")
            suffix = f" [{', '.join(settings)}]" if settings else ""
            out.append(f"  {c.name.ljust(width)} {c.type.ljust(type_width)}{suffix}".rstrip())
        out.append("}")
        out.append("")

    out.append("// Relationships: Fact (many) -> Dimension (one).")
    out.append("// `A.x > B.y` and `B.y < A.x` mean the same; they alternate for layout.")
    out.extend(ref_line(r, tables, flip=i % 2 == 1) for i, r in enumerate(rels))
    out.append("")

    return "\n".join(out)


def render_svg(dbml_path: Path, svg_path: Path) -> None:
    npx = shutil.which("npx")
    if npx is None:
        raise RuntimeError("npx not found; install Node.js or run with --no-svg")
    subprocess.run(
        [npx, "-y", RENDERER, "-i", str(dbml_path), "-o", str(svg_path)],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--no-svg", action="store_true", help="only write the .dbml file")
    args = parser.parse_args()

    try:
        tables, rels = parse_mermaid(MMD.read_text(encoding="utf-8"))
        DBML.write_text(to_dbml(tables, rels), encoding="utf-8", newline="\n")
        print(f"[ok] {DBML.relative_to(ROOT)}  ({len(tables)} tables, {len(rels)} refs)")
        if not args.no_svg:
            render_svg(DBML, SVG)
            print(f"[ok] {SVG.relative_to(ROOT)}")
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[fail] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
