"""
Present the DBML star schema docs/schema/star_schema.dbml as a Markdown page.

Output
  docs/schema/star_schema_dbml_vi.md   Vietnamese presentation of the schema:
                                       diagram, table overview, relationships,
                                       fact columns (keys vs measures),
                                       every dimension, and the DBML source.

The page is built only from the .dbml file (and links to star_schema.svg,
which scripts/mmd_to_dbml.py renders). Run that script first.

Supported DBML subset: Project, Table (with column settings pk / unique /
not null / note), and single-column Ref lines using >, <, - or <>.

Usage:  python scripts/dbml_to_md.py
Exit code 0 = success, 1 = parse failure.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "docs" / "schema"
DBML = SCHEMA / "star_schema.dbml"
SVG = SCHEMA / "star_schema.svg"
MD = SCHEMA / "star_schema_dbml_vi.md"

TABLE_RE = re.compile(r"^Table\s+(?P<name>\w+)\s*(?:\[(?P<settings>[^\]]*)\])?\s*\{$")
COLUMN_RE = re.compile(r"^(?P<name>\w+)\s+(?P<type>[\w(),]+)\s*(?:\[(?P<settings>.*)\])?$")
REF_RE = re.compile(
    r"^Ref(?:\s+\w+)?\s*:\s*(?P<lt>\w+)\.(?P<lc>\w+)\s*(?P<op><>|<|>|-)\s*(?P<rt>\w+)\.(?P<rc>\w+)"
)
PROJECT_RE = re.compile(r"^Project\s+(?P<name>\w+)\s*\{$")
KV_RE = re.compile(r"^(?P<key>\w+)\s*:\s*'(?P<value>(?:\\.|[^'\\])*)'$")
NOTE_RE = re.compile(r"note\s*:\s*'(?P<value>(?:\\.|[^'\\])*)'", re.IGNORECASE)


@dataclass
class Column:
    name: str
    type: str
    pk: bool = False
    unique: bool = False
    not_null: bool = False
    note: str = ""


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)

    @property
    def is_fact(self) -> bool:
        return self.name.startswith("Fact")

    @property
    def pk(self) -> list[Column]:
        return [c for c in self.columns if c.pk]


@dataclass
class Ref:
    many_table: str
    many_column: str
    one_table: str
    one_column: str
    kind: str  # "n-1", "1-1", "n-n"


@dataclass
class Schema:
    project: str = ""
    database_type: str = ""
    project_note: str = ""
    tables: dict[str, Table] = field(default_factory=dict)
    refs: list[Ref] = field(default_factory=list)


def unescape(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def parse_column(line: str) -> Column:
    m = COLUMN_RE.match(line)
    if not m:
        raise ValueError(f"cannot parse column: {line!r}")
    col = Column(m["name"], m["type"])
    settings = m["settings"] or ""
    note = NOTE_RE.search(settings)
    if note:
        col.note = unescape(note["value"])
        settings = settings[: note.start()] + settings[note.end():]
    flags = {s.strip().lower() for s in settings.split(",") if s.strip()}
    col.pk = "pk" in flags or "primary key" in flags
    col.unique = "unique" in flags
    col.not_null = "not null" in flags or col.pk
    return col


def parse_dbml(text: str) -> Schema:
    schema = Schema()
    block: str | None = None  # "project" | "table" | "skip"
    table: Table | None = None

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("//", 1)[0].strip()
        if not line:
            continue

        if block is not None:
            if line == "}":
                block, table = None, None
            elif block == "table":
                try:
                    table.columns.append(parse_column(line))
                except ValueError as exc:
                    raise ValueError(f"line {lineno}: {exc}") from None
            elif block == "project":
                kv = KV_RE.match(line)
                if kv and kv["key"].lower() == "database_type":
                    schema.database_type = unescape(kv["value"])
                elif kv and kv["key"].lower() == "note":
                    schema.project_note = unescape(kv["value"])
            continue

        if m := PROJECT_RE.match(line):
            schema.project, block = m["name"], "project"
        elif m := TABLE_RE.match(line):
            table = schema.tables.setdefault(m["name"], Table(m["name"]))
            block = "table"
        elif m := REF_RE.match(line):
            lt, lc, op, rt, rc = m["lt"], m["lc"], m["op"], m["rt"], m["rc"]
            if op == ">":
                schema.refs.append(Ref(lt, lc, rt, rc, "n-1"))
            elif op == "<":
                schema.refs.append(Ref(rt, rc, lt, lc, "n-1"))
            else:
                schema.refs.append(Ref(lt, lc, rt, rc, "1-1" if op == "-" else "n-n"))
        elif line.endswith("{"):
            block = "skip"  # TableGroup, Enum, ... are not presented
        else:
            raise ValueError(f"line {lineno}: unrecognised DBML syntax: {raw!r}")

    for r in schema.refs:
        for t, c in ((r.many_table, r.many_column), (r.one_table, r.one_column)):
            if t not in schema.tables or not any(col.name == c for col in schema.tables[t].columns):
                raise ValueError(f"Ref points at unknown column {t}.{c}")
    return schema


# ------------------------------------------------------------------ rendering

NOT_MEASURE = "Không phải measure"
UNRESOLVED = "Chưa xác định"


def additivity(note: str) -> str:
    """Classify a fact column from the additivity keywords in its DBML note."""
    n = note.lower()
    if "non-additive" in n:
        return "Không cộng"
    if "semi-additive" in n:
        return "Bán cộng"
    if "additive" in n:
        return "Cộng được"
    if "unresolved" in n:
        return UNRESOLVED
    if "lineage" in n or "data quality" in n:
        return NOT_MEASURE
    return "—"


def md_table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out.extend("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows)
    return out


def code(text: str) -> str:
    return f"`{text}`" if text else ""


def render(schema: Schema, dbml_text: str) -> str:
    facts = [t for t in schema.tables.values() if t.is_fact]
    dims = [t for t in schema.tables.values() if not t.is_fact]
    fk_of: dict[tuple[str, str], Ref] = {(r.many_table, r.many_column): r for r in schema.refs}
    referenced_by: dict[str, list[Ref]] = {}
    for r in schema.refs:
        referenced_by.setdefault(r.one_table, []).append(r)

    dbml_rel = DBML.relative_to(SCHEMA).as_posix()
    svg_rel = SVG.relative_to(SCHEMA).as_posix()
    kind_label = {"n-1": "N : 1", "1-1": "1 : 1", "n-n": "N : N"}

    out: list[str] = [
        "# Star Schema v1 — trình bày từ DBML",
        "",
        "> Tệp này được sinh tự động bởi `scripts/dbml_to_md.py` từ "
        f"[`{dbml_rel}`]({dbml_rel}). Không sửa tay: hãy sửa `star_schema.mmd` rồi chạy lại "
        "hai script ở mục *Tái tạo tài liệu* cuối trang.",
        "",
    ]
    out += md_table(
        ["Mục", "Giá trị"],
        [
            ["Project DBML", code(schema.project)],
            ["Hệ quản trị đích", schema.database_type or "—"],
            ["Mô tả", schema.project_note or "—"],
            ["Nguồn gốc", "`star_schema.mmd` → `star_schema.dbml` → tài liệu này"],
            ["Số bảng", f"{len(schema.tables)} ({len(facts)} Fact, {len(dims)} Dimension)"],
            ["Số quan hệ", str(len(schema.refs))],
            ["Tài liệu thiết kế đầy đủ", "[star_schema_design_vi.md](star_schema_design_vi.md)"],
        ],
    )

    # 1. Diagram
    out += [
        "",
        "## 1. Sơ đồ",
        "",
        f"![Star Schema v1]({svg_rel})",
        "",
        "Cách đọc sơ đồ:",
        "",
        "- Header **đỏ** là bảng Fact, header **xanh** là bảng Dimension.",
        "- Cột in **đậm** là khóa chính (PK).",
        "- Mỗi đường nối đi từ cột khóa ngoại (FK) trong Fact tới PK của Dimension; "
        "đầu `*` là phía nhiều (Fact), đầu `1` là phía một (Dimension).",
        f"- Sơ đồ được vẽ bằng `@softwaretechnik/dbml-renderer`. Có thể dán nội dung "
        f"[`{dbml_rel}`]({dbml_rel}) vào <https://dbdiagram.io> để xem và kéo thả tương tác.",
        "",
    ]

    # 2. Overview
    out += ["## 2. Tổng quan các bảng", ""]
    rows = []
    for t in schema.tables.values():
        if t.is_fact:
            joins = ", ".join(sorted({r.one_table for r in schema.refs if r.many_table == t.name}))
            link = f"{len([r for r in schema.refs if r.many_table == t.name])} FK → {joins}"
        else:
            link = ", ".join(f"{code(r.many_table + '.' + r.many_column)}" for r in referenced_by.get(t.name, [])) or "—"
        rows.append([
            f"[{t.name}](#{t.name.lower()})",
            "Fact" if t.is_fact else "Dimension",
            ", ".join(code(c.name) for c in t.pk) or "—",
            str(len(t.columns)),
            link,
        ])
    out += md_table(["Bảng", "Loại", "Khóa chính", "Số cột", "Liên kết"], rows)
    out.append("")

    # 3. Relationships
    out += ["## 3. Quan hệ", ""]
    out += md_table(
        ["#", "Phía nhiều (FK)", "Phía một (PK)", "Bản số"],
        [
            [str(i), code(f"{r.many_table}.{r.many_column}"), code(f"{r.one_table}.{r.one_column}"), kind_label[r.kind]]
            for i, r in enumerate(schema.refs, start=1)
        ],
    )
    out += [
        "",
        "Mọi quan hệ đều là N : 1 từ Fact tới Dimension, và không Dimension nào nối với Dimension "
        "khác — đúng dạng star schema (không snowflake)."
        if all(
            r.kind == "n-1" and schema.tables[r.many_table].is_fact and not schema.tables[r.one_table].is_fact
            for r in schema.refs
        )
        else "Lưu ý: có quan hệ không phải N : 1 từ Fact tới Dimension.",
        "",
    ]

    # 4. Fact tables
    section = 4
    for t in facts:
        keys = [c for c in t.columns if c.pk or (t.name, c.name) in fk_of]
        others = [c for c in t.columns if c not in keys]
        out += [f"## {section}. Bảng Fact: {t.name}", "", f'<a id="{t.name.lower()}"></a>', ""]
        out += [f"### {section}.1 Khóa ({len(keys)} cột)", ""]
        out += md_table(
            ["Cột", "Kiểu", "Vai trò", "Tham chiếu"],
            [
                [
                    code(c.name), code(c.type),
                    "PK" if c.pk else "FK",
                    code(f"{fk_of[(t.name, c.name)].one_table}.{fk_of[(t.name, c.name)].one_column}")
                    if (t.name, c.name) in fk_of else "—",
                ]
                for c in keys
            ],
        )
        counts: dict[str, int] = {}
        for c in others:
            counts[additivity(c.note)] = counts.get(additivity(c.note), 0) + 1
        summary = ", ".join(f"{v} {k.lower()}" for k, v in counts.items())
        out += [
            "",
            f"### {section}.2 Measure và thuộc tính khác ({len(others)} cột)",
            "",
            f"Phân loại theo ghi chú trong DBML: {summary}.",
            "",
        ]
        out += md_table(
            ["Cột", "Kiểu", "Tính cộng", "Cho phép NULL", "Ghi chú (nguyên văn DBML)"],
            [
                [
                    code(c.name), code(c.type), additivity(c.note),
                    "Có" if "nullable" in c.note.lower() else "",
                    c.note,
                ]
                for c in others
            ],
        )
        out += [
            "",
            "Ý nghĩa cột *Tính cộng*: **Cộng được** — có thể `SUM` theo mọi Dimension; "
            "**Bán cộng** — không nên `SUM` dọc theo một số chiều (ví dụ tuổi); "
            "**Không cộng** — chỉ dùng `AVG`/`MIN`/`MAX`/phân phối, không `SUM`; "
            f"**{UNRESOLVED}** — ngữ nghĩa (đơn vị, tiền tệ) chưa được xác lập, chưa nên tổng hợp; "
            f"**{NOT_MEASURE}** — cột lineage hoặc cờ chất lượng dữ liệu.",
            "",
        ]
        section += 1

    # 5. Dimensions
    out += [f"## {section}. Các bảng Dimension", ""]
    for i, t in enumerate(dims, start=1):
        used = ", ".join(code(f"{r.many_table}.{r.many_column}") for r in referenced_by.get(t.name, []))
        out += [
            f"### {section}.{i} {t.name}",
            "",
            f'<a id="{t.name.lower()}"></a>',
            "",
            f"Được tham chiếu bởi: {used or '—'}.",
            "",
        ]
        out += md_table(
            ["Cột", "Kiểu", "Khóa", "Ghi chú"],
            [[code(c.name), code(c.type), "PK" if c.pk else ("UK" if c.unique else ""), c.note] for c in t.columns],
        )
        out.append("")
    section += 1

    # 6. Source
    out += [f"## {section}. Mã nguồn DBML", "", "```dbml", dbml_text.rstrip("\n"), "```", ""]
    section += 1

    # 7. Rebuild
    out += [
        f"## {section}. Tái tạo tài liệu",
        "",
        "```bash",
        "python scripts/mmd_to_dbml.py   # star_schema.mmd -> star_schema.dbml + star_schema.svg",
        "python scripts/dbml_to_md.py    # star_schema.dbml -> star_schema_dbml_vi.md",
        "```",
        "",
        "Bước vẽ SVG cần Node.js (`npx`); lần chạy đầu sẽ tải `@softwaretechnik/dbml-renderer`. "
        "Dùng `python scripts/mmd_to_dbml.py --no-svg` nếu chỉ cần tệp DBML.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    try:
        dbml_text = DBML.read_text(encoding="utf-8")
        schema = parse_dbml(dbml_text)
    except (OSError, ValueError) as exc:
        print(f"[fail] {exc}", file=sys.stderr)
        return 1
    if not SVG.exists():
        print(f"[warn] {SVG.relative_to(ROOT)} not found; run scripts/mmd_to_dbml.py to draw it")
    MD.write_text(render(schema, dbml_text), encoding="utf-8", newline="\n")
    print(f"[ok] {MD.relative_to(ROOT)}  ({len(schema.tables)} tables, {len(schema.refs)} refs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
