"""
Verify the Star Schema v1 design artifacts in docs/schema/.

This script is READ-ONLY with respect to data/. It hashes the staging CSV
before and after the run to prove nothing was written.

Checks
  1. Every staging field appears exactly once in the source-to-target mapping.
  2. No duplicate target primary keys are defined across the model.
  3. Every Fact FK points at an existing candidate Dimension.
  4. Every measure named in the design document appears in measure_catalog.csv.
  5. The English and Vietnamese documents contain the same numeric decisions.
  6. No source or staging dataset was modified.

Usage:  python scripts/verify_star_schema.py
Exit code 0 = all checks passed, 1 = at least one failure.
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "docs" / "schema"
STAGING = ROOT / "data" / "staging" / "internship_postings_staging.csv"
RAW_DIR = ROOT / "data" / "raw"

EN = SCHEMA / "star_schema_design_en.md"
VI = SCHEMA / "star_schema_design_vi.md"
MAPPING = SCHEMA / "source_to_target_mapping.csv"
MEASURES = SCHEMA / "measure_catalog.csv"
DIMENSIONS = SCHEMA / "dimension_catalog.csv"

FACT = "FactInternshipPosting"

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------- integrity 0
staging_before = sha256(STAGING)
raw_before = {p.name: sha256(p) for p in sorted(RAW_DIR.glob("*.csv"))}


# ------------------------------------------------------------------- check 1
def check_mapping_completeness() -> None:
    with STAGING.open(encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    staging_cols = [c.strip() for c in header]

    rows = read_csv(MAPPING)
    mapped = [r["staging_column"].strip() for r in rows]

    missing = [c for c in staging_cols if c not in mapped]
    extra = [c for c in mapped if c not in staging_cols]
    dupes = sorted({c for c in mapped if mapped.count(c) > 1})

    ok = not missing and not extra and not dupes and len(mapped) == len(staging_cols)
    detail = (
        f"{len(staging_cols)} staging columns, {len(mapped)} mapping rows; "
        f"missing={missing or 'none'}, extra={extra or 'none'}, duplicated={dupes or 'none'}"
    )
    record("1. Every staging field appears exactly once in the mapping", ok, detail)

    # Every mapping row must name a target, or be explicitly marked as excluded.
    bad = []
    for r in rows:
        excluded = "EXCLUDED" in r["disposition"].upper()
        has_target = r["target_table"].strip() not in ("", "(none)")
        if excluded and has_target:
            bad.append(f"{r['staging_column']} (excluded but has a target)")
        if not excluded and not has_target:
            bad.append(f"{r['staging_column']} (no target and not marked EXCLUDED)")
    n_excluded = sum("EXCLUDED" in r["disposition"].upper() for r in rows)
    record(
        "1b. Excluded fields are marked explicitly, not omitted",
        not bad,
        f"{n_excluded} field(s) explicitly excluded; anomalies={bad or 'none'}",
    )


# ------------------------------------------------------------------- check 2
def check_primary_keys() -> list[dict[str, str]]:
    dims = read_csv(DIMENSIONS)
    pks = [("FactInternshipPosting", "FactPostingKey")]
    pks += [(d["dimension_name"], d["surrogate_key"]) for d in dims]

    names = [pk for _, pk in pks]
    tables = [t for t, _ in pks]
    dup_pk = sorted({n for n in names if names.count(n) > 1})
    dup_tbl = sorted({t for t in tables if tables.count(t) > 1})

    ok = not dup_pk and not dup_tbl
    record(
        "2. No duplicate target primary keys are defined",
        ok,
        f"{len(pks)} tables / {len(set(names))} distinct PK names; "
        f"duplicate PK names={dup_pk or 'none'}, duplicate tables={dup_tbl or 'none'}",
    )
    return dims


# ------------------------------------------------------------------- check 3
def check_fact_foreign_keys(dims: list[dict[str, str]]) -> None:
    text = EN.read_text(encoding="utf-8")
    # Rows of the §8.1 key table look like: | `DateKey` | `INT` | NO | FK -> `DimDate` |
    fks = re.findall(r"\|\s*`(\w+Key)`\s*\|[^|]*\|[^|]*\|\s*FK\s*→\s*`(\w+)`\s*\|", text)

    dim_by_name = {d["dimension_name"]: d["surrogate_key"] for d in dims}
    problems = []
    for fk_col, dim_name in fks:
        if dim_name not in dim_by_name:
            problems.append(f"{fk_col} -> {dim_name} (no such dimension)")
        elif dim_by_name[dim_name] != fk_col:
            problems.append(
                f"{fk_col} -> {dim_name} (dimension PK is {dim_by_name[dim_name]})"
            )

    unreferenced = sorted(set(dim_by_name) - {d for _, d in fks})
    ok = bool(fks) and not problems and not unreferenced and len(fks) == len(dims)
    record(
        "3. Every Fact FK points at an existing candidate Dimension",
        ok,
        f"{len(fks)} FKs declared for {len(dims)} dimensions; "
        f"bad={problems or 'none'}, dimensions never referenced={unreferenced or 'none'}",
    )

    # The fact PK must not be SourceRowID.
    pk_line = re.search(r"\|\s*`(\w+)`\s*\|[^|]*\|[^|]*\|\s*\*\*Primary key\.\*\*", text)
    pk = pk_line.group(1) if pk_line else None
    record(
        "3b. Fact PK is the DW surrogate key, not SourceRowID",
        pk == "FactPostingKey",
        f"declared fact primary key = {pk!r}",
    )


# ------------------------------------------------------------------- check 4
def check_measures() -> None:
    rows = read_csv(MEASURES)
    catalog = [r["dw_measure_name"].strip() for r in rows]
    dupes = sorted({m for m in catalog if catalog.count(m) > 1})

    text = EN.read_text(encoding="utf-8")
    # Measures named in the §9 catalogue table and the §16 additivity matrix.
    section9 = text.split("## 9. Measure catalogue")[1].split("### 9.1")[0]
    matrix = text.split("## 16. Additivity matrix")[1].split("## 17.")[0]
    named = set(re.findall(r"^\|\s*`(\w+)`\s*\|", section9, re.M))
    named |= set(re.findall(r"^\|\s*`(\w+)`\s*\|", matrix, re.M))

    missing = sorted(named - set(catalog))
    uncited = sorted(set(catalog) - named)

    # Every measure must also appear in the mapping, or be a derived measure.
    mapping_targets = {r["target_column"].strip() for r in read_csv(MAPPING)}
    derived = {"PostingCount", "FakePostingRate"}
    unmapped = sorted(set(catalog) - mapping_targets - derived)

    ok = not missing and not uncited and not dupes and not unmapped
    record(
        "4. Every measure appears in measure_catalog.csv",
        ok,
        f"{len(catalog)} measures in catalogue ({len(derived)} calculated, "
        f"{len(catalog) - len(derived)} stored); named in document but absent from catalogue="
        f"{missing or 'none'}; in catalogue but not cited={uncited or 'none'}; "
        f"duplicated={dupes or 'none'}; stored measures with no mapping row={unmapped or 'none'}",
    )


# ------------------------------------------------------------------- check 5
# Matches a thousands-separated number or a plain one, and never swallows a
# trailing comma or full stop (which would make "2026-09-23," differ from
# "2026-09-23").
NUM = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")


def numbers_in(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    # Strip the mermaid block: it is identical in both files and carries no findings.
    text = re.sub(r"```mermaid.*?```", "", text, flags=re.S)
    # English prose spells the quantity ("reaches zero", "zero-filled") where the
    # Vietnamese uses the numeral. Normalise so the comparison is of findings,
    # not of writing style.
    text = re.sub(r"\bzero(e?s)?\b", "0", text, flags=re.I)
    return sorted(NUM.findall(text))


def check_bilingual_numbers() -> None:
    en, vi = numbers_in(EN), numbers_in(VI)
    from collections import Counter

    ce, cv = Counter(en), Counter(vi)
    only_en = sorted((ce - cv).elements())
    only_vi = sorted((cv - ce).elements())
    ok = not only_en and not only_vi
    record(
        "5. EN and VI documents contain the same numeric decisions",
        ok,
        f"{len(en)} numeric tokens in EN, {len(vi)} in VI; "
        f"only in EN={only_en or 'none'}; only in VI={only_vi or 'none'}",
    )

    # Structural equivalence: same section headings count.
    def heads(p: Path) -> int:
        return len(re.findall(r"^#{2,3} ", p.read_text(encoding="utf-8"), re.M))

    record(
        "5b. EN and VI documents have identical structure",
        heads(EN) == heads(VI),
        f"{heads(EN)} headings in EN, {heads(VI)} in VI",
    )


# ------------------------------------------------------------------- check 6
def check_integrity() -> None:
    staging_after = sha256(STAGING)
    raw_after = {p.name: sha256(p) for p in sorted(RAW_DIR.glob("*.csv"))}
    ok = staging_after == staging_before and raw_after == raw_before
    record(
        "6. No source or staging dataset was modified",
        ok,
        f"staging sha256 before={staging_before[:8]}...{staging_before[-8:]} "
        f"after={staging_after[:8]}...{staging_after[-8:]}; "
        f"{len(raw_before)} raw file(s) unchanged={raw_after == raw_before}",
    )


def main() -> int:
    check_mapping_completeness()
    dims = check_primary_keys()
    check_fact_foreign_keys(dims)
    check_measures()
    check_bilingual_numbers()
    check_integrity()

    width = max(len(n) for n, _, _ in results)
    print("=" * 78)
    print("STAR SCHEMA v1 - VERIFICATION")
    print("=" * 78)
    failures = 0
    for name, ok, detail in results:
        flag = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"[{flag}] {name.ljust(width)}")
        print(f"       {detail}")
    print("-" * 78)
    print(f"{len(results) - failures}/{len(results)} checks passed.")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
