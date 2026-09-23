#!/usr/bin/env python3
"""
Data profiling for the fake-internship-detection dataset.

PROFILING ONLY.  This script is strictly read-only with respect to the raw
data: it opens data/raw/fake_internship_detection_dataset.csv for reading,
never writes to data/raw/, and performs no cleaning, imputation, encoding,
scaling, deduplication or any other transformation of the dataset.  Every
derived value is computed on an in-memory copy and written to
results/profiling/.

Outputs (results/profiling/):
    dataset_overview.txt
    column_profile.csv
    numeric_summary.csv
    categorical_summary.csv
    categorical_top_values.txt
    date_analysis.csv
    string_quality.csv
    potential_key_analysis.csv
    summary.md

Usage:
    python scripts/profile_data.py
    python scripts/profile_data.py --input <csv> --output-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "fake_internship_detection_dataset.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "profiling"

# Name tokens that hint at a date/time column (used alongside the actual dtype).
DATE_NAME_TOKENS = ("date", "time", "year", "timestamp")
TOP_N_CATEGORICAL = 20
# A column is only *flagged for review* as a candidate key above this ratio;
# no primary key is declared by this script.
NEAR_UNIQUE_THRESHOLD = 0.99
# Plausible range when deciding whether an integer column could encode a year.
YEAR_MIN, YEAR_MAX = 1900, 2100

SEP = "=" * 78
SUB = "-" * 78


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def human_bytes(n: float) -> str:
    """Format a byte count for human reading."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:,.2f} {unit}"
        n /= 1024.0
    return f"{n:,.2f} PB"


def pct(part: float, whole: float) -> float:
    """Safe percentage, rounded for stable file output."""
    if not whole:
        return 0.0
    return round(100.0 * part / whole, 4)


def file_fingerprint(path: Path) -> dict:
    """Size / mtime / sha256 of a file, used to prove the raw CSV is untouched."""
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "size_bytes": stat.st_size,
        "mtime": stat.st_mtime,
        "sha256": digest.hexdigest(),
    }


def classify_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    """Split columns into numeric / text / datetime / boolean / other buckets."""
    buckets: dict[str, list[str]] = {
        "numeric": [],
        "text": [],
        "datetime": [],
        "boolean": [],
        "other": [],
    }
    for col in df.columns:
        dtype = df[col].dtype
        if isinstance(dtype, pd.CategoricalDtype):
            buckets["text"].append(col)
        elif pd.api.types.is_bool_dtype(dtype):
            buckets["boolean"].append(col)
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            buckets["datetime"].append(col)
        elif pd.api.types.is_numeric_dtype(dtype):
            buckets["numeric"].append(col)
        elif dtype == object or pd.api.types.is_string_dtype(dtype):
            buckets["text"].append(col)
        else:
            buckets["other"].append(col)
    return buckets


# --------------------------------------------------------------------------
# 1. dataset overview
# --------------------------------------------------------------------------
def write_dataset_overview(
    df: pd.DataFrame,
    out_path: Path,
    source: Path,
    fingerprint: dict,
    duplicate_rows: int,
    load_seconds: float,
) -> dict:
    mem = df.memory_usage(deep=True)
    total_mem = int(mem.sum())
    n_rows, n_cols = df.shape

    lines: list[str] = []
    lines.append(SEP)
    lines.append("DATASET OVERVIEW")
    lines.append(SEP)
    lines.append(f"Generated            : {datetime.now():%Y-%m-%d %H:%M:%S}")
    lines.append(f"Source file          : {source}")
    lines.append(
        f"Source size on disk  : {human_bytes(fingerprint['size_bytes'])}"
        f" ({fingerprint['size_bytes']:,} bytes)"
    )
    lines.append(f"Source sha256        : {fingerprint['sha256']}")
    lines.append(f"Load time            : {load_seconds:.2f} s")
    lines.append("")
    lines.append(SUB)
    lines.append("SHAPE")
    lines.append(SUB)
    lines.append(f"Number of rows       : {n_rows:,}")
    lines.append(f"Number of columns    : {n_cols:,}")
    lines.append(f"Total cells          : {n_rows * n_cols:,}")
    lines.append("")
    lines.append(SUB)
    lines.append("MEMORY USAGE (in-memory pandas representation, deep=True)")
    lines.append(SUB)
    lines.append(f"Total                : {human_bytes(total_mem)} ({total_mem:,} bytes)")
    lines.append(
        f"Average per row      : {human_bytes(total_mem / n_rows) if n_rows else '0 B'}"
    )
    lines.append("")
    lines.append(f"{'column':<34}{'dtype':<12}{'memory':>16}{'share':>10}")
    for name, value in mem.items():
        label = "<Index>" if name == "Index" else str(name)
        dtype = "-" if name == "Index" else str(df[name].dtype)
        lines.append(
            f"{label:<34}{dtype:<12}{human_bytes(value):>16}{pct(value, total_mem):>9.2f}%"
        )
    lines.append("")
    lines.append(SUB)
    lines.append("COLUMN NAMES (in file order)")
    lines.append(SUB)
    for i, col in enumerate(df.columns, start=1):
        lines.append(f"{i:>3}. {col}  [{df[col].dtype}]")
    lines.append("")
    lines.append(SUB)
    lines.append("EXACT DUPLICATE ROWS (all columns identical)")
    lines.append(SUB)
    lines.append(f"Duplicate rows (excess copies)   : {duplicate_rows:,}")
    lines.append(f"Duplicate rows as % of dataset   : {pct(duplicate_rows, n_rows):.4f}%")
    lines.append(f"Distinct rows                    : {n_rows - duplicate_rows:,}")
    lines.append("")
    lines.append("Note: counted with pandas .duplicated(keep='first'), i.e. the first")
    lines.append("occurrence of each repeated row is NOT counted. No rows were removed.")
    lines.append("")
    lines.append(SEP)
    lines.append("This file is descriptive only. No column was dropped, cleaned,")
    lines.append("re-typed or otherwise modified, and data/raw/ was never written to.")
    lines.append(SEP)

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"total_memory_bytes": total_mem}


# --------------------------------------------------------------------------
# 2. column profile
# --------------------------------------------------------------------------
def build_column_profile(df: pd.DataFrame) -> pd.DataFrame:
    n_rows = len(df)
    rows = []
    for col in df.columns:
        series = df[col]
        non_null = int(series.notna().sum())
        null = n_rows - non_null
        unique = int(series.nunique(dropna=True))
        rows.append(
            {
                "column_name": col,
                "pandas_dtype": str(series.dtype),
                "non_null_count": non_null,
                "null_count": null,
                "null_percentage": pct(null, n_rows),
                "unique_count": unique,
                # share of all rows that distinct values could cover
                "unique_percentage": pct(unique, n_rows),
                # cardinality relative to the values that are actually present
                "unique_percentage_of_non_null": pct(unique, non_null),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 3. numeric summary
# --------------------------------------------------------------------------
def build_numeric_summary(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    columns = [
        "column_name", "pandas_dtype", "count", "null_count", "mean", "std", "min",
        "25%", "median", "75%", "max", "zero_count", "negative_count",
        "distinct_values", "iqr_lower_fence", "iqr_upper_fence",
        "iqr_outlier_count", "iqr_outlier_percentage",
    ]
    if not numeric_cols:
        return pd.DataFrame(columns=columns)

    desc = df[numeric_cols].describe().T
    rows = []
    for col in numeric_cols:
        series = df[col]
        values = series.to_numpy(dtype="float64", na_value=np.nan)
        finite = values[np.isfinite(values)]
        q1 = float(desc.loc[col, "25%"])
        q3 = float(desc.loc[col, "75%"])
        iqr = q3 - q1
        if iqr > 0:
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outliers = int(((finite < low) | (finite > high)).sum())
        else:
            low = high = np.nan
            outliers = 0
        rows.append(
            {
                "column_name": col,
                "pandas_dtype": str(series.dtype),
                "count": int(desc.loc[col, "count"]),
                "null_count": int(len(df) - desc.loc[col, "count"]),
                "mean": float(desc.loc[col, "mean"]),
                "std": float(desc.loc[col, "std"]),
                "min": float(desc.loc[col, "min"]),
                "25%": q1,
                "median": float(desc.loc[col, "50%"]),
                "75%": q3,
                "max": float(desc.loc[col, "max"]),
                "zero_count": int((finite == 0).sum()),
                "negative_count": int((finite < 0).sum()),
                "distinct_values": int(series.nunique(dropna=True)),
                "iqr_lower_fence": low,
                "iqr_upper_fence": high,
                "iqr_outlier_count": outliers,
                "iqr_outlier_percentage": pct(outliers, len(finite)),
            }
        )
    return pd.DataFrame(rows, columns=columns)


# --------------------------------------------------------------------------
# 4. categorical summary
# --------------------------------------------------------------------------
def build_categorical_summary(
    df: pd.DataFrame, text_cols: list[str], value_counts: dict[str, pd.Series]
) -> pd.DataFrame:
    n_rows = len(df)
    rows = []
    for col in text_cols:
        vc = value_counts[col]
        non_null = int(vc.sum())
        if len(vc):
            top_value, top_count = vc.index[0], int(vc.iloc[0])
        else:
            top_value, top_count = pd.NA, 0
        rows.append(
            {
                "column_name": col,
                "pandas_dtype": str(df[col].dtype),
                "non_null_count": non_null,
                "null_count": n_rows - non_null,
                "unique_count": int(len(vc)),
                "most_frequent_value": top_value,
                "most_frequent_count": top_count,
                "most_frequent_percentage": pct(top_count, n_rows),
                "most_frequent_percentage_of_non_null": pct(top_count, non_null),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 5. categorical top values
# --------------------------------------------------------------------------
def write_categorical_top_values(
    df: pd.DataFrame,
    text_cols: list[str],
    out_path: Path,
    top_n: int = TOP_N_CATEGORICAL,
) -> None:
    n_rows = len(df)
    lines: list[str] = []
    lines.append(SEP)
    lines.append(f"TOP {top_n} VALUES PER CATEGORICAL / TEXT COLUMN (missing values included)")
    lines.append(SEP)
    lines.append(f"Generated : {datetime.now():%Y-%m-%d %H:%M:%S}")
    lines.append(f"Rows      : {n_rows:,}")
    lines.append("")
    lines.append("Values are shown with Python repr() so that quoting, leading/trailing")
    lines.append("whitespace and empty strings stay visible. <NA> denotes a missing value.")
    lines.append("Percentages are of ALL rows, missing values included.")
    lines.append("")

    for col in text_cols:
        vc_all = df[col].value_counts(dropna=False)
        distinct_incl_na = int(len(vc_all))
        covered = int(vc_all.head(top_n).sum())
        lines.append(SUB)
        lines.append(f"COLUMN: {col}   [{df[col].dtype}]")
        lines.append(f"distinct values (missing counted as one) : {distinct_incl_na:,}")
        lines.append(
            f"coverage of top {top_n}                          : "
            f"{covered:,} rows ({pct(covered, n_rows):.2f}%)"
        )
        lines.append(SUB)
        lines.append(f"{'#':>4}  {'count':>12}  {'pct':>8}  value")
        for rank, (value, count) in enumerate(vc_all.head(top_n).items(), start=1):
            label = "<NA> (missing)" if pd.isna(value) else repr(value)
            lines.append(
                f"{rank:>4}  {int(count):>12,}  {pct(count, n_rows):>7.3f}%  {label}"
            )
        if distinct_incl_na > top_n:
            lines.append(
                f"      ... {distinct_incl_na - top_n:,} further distinct value(s) not shown"
            )
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# 6. date analysis
# --------------------------------------------------------------------------
def build_date_analysis(
    df: pd.DataFrame,
    buckets: dict[str, list[str]],
    value_counts: dict[str, pd.Series],
) -> pd.DataFrame:
    n_rows = len(df)
    candidates: list[tuple[str, str]] = []
    for col in df.columns:
        lowered = col.lower()
        by_name = any(token in lowered for token in DATE_NAME_TOKENS)
        by_dtype = col in buckets["datetime"]
        if by_dtype and by_name:
            candidates.append((col, "dtype+name"))
        elif by_dtype:
            candidates.append((col, "dtype"))
        elif by_name:
            candidates.append((col, "name"))

    rows = []
    for col, detected_by in candidates:
        series = df[col]
        non_null = int(series.notna().sum())
        record = {
            "column": col,
            "pandas_dtype": str(series.dtype),
            "detected_by": detected_by,
            "non_null_count": non_null,
            "null_count": n_rows - non_null,
            "parsed_count": 0,
            "parse_success_percentage": 0.0,
            "min_date": pd.NA,
            "max_date": pd.NA,
            "invalid_count": 0,
            "distinct_parsed_values": 0,
            "notes": "",
        }

        if col in buckets["datetime"]:
            parsed = series.dropna()
            record.update(
                parsed_count=non_null,
                parse_success_percentage=100.0 if non_null else 0.0,
                min_date=str(parsed.min()) if non_null else pd.NA,
                max_date=str(parsed.max()) if non_null else pd.NA,
                invalid_count=0,
                distinct_parsed_values=int(parsed.nunique()),
                notes="already a datetime dtype; no parsing needed",
            )
            rows.append(record)
            continue

        if col in buckets["text"]:
            # Parse the distinct values only: O(n) for the hashing pass that
            # already happened, then O(distinct) for the parse itself.
            uniques = value_counts[col].index
            counts = value_counts[col].to_numpy()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                parsed_uniques = pd.to_datetime(
                    pd.Series(uniques.astype("object")), errors="coerce"
                )
            ok = parsed_uniques.notna().to_numpy()
            parsed_rows = int(counts[ok].sum())
            invalid_rows = int(counts[~ok].sum())
            good = parsed_uniques[ok]
            record.update(
                parsed_count=parsed_rows,
                parse_success_percentage=pct(parsed_rows, non_null),
                min_date=str(good.min()) if len(good) else pd.NA,
                max_date=str(good.max()) if len(good) else pd.NA,
                invalid_count=invalid_rows,
                distinct_parsed_values=int(good.nunique()),
                notes="parsed from text on distinct values only; dataframe untouched",
            )
            rows.append(record)
            continue

        if col in buckets["numeric"]:
            values = series.dropna().to_numpy(dtype="float64")
            looks_like_year = (
                values.size > 0
                and bool(np.all(values == np.floor(values)))
                and float(values.min()) >= YEAR_MIN
                and float(values.max()) <= YEAR_MAX
            )
            if looks_like_year:
                years = np.unique(values.astype("int64"))
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    parsed = pd.to_datetime(
                        pd.Series(years.astype(str)), format="%Y", errors="coerce"
                    )
                ok = int(parsed.notna().sum())
                record.update(
                    parsed_count=non_null if ok == len(years) else 0,
                    parse_success_percentage=100.0 if ok == len(years) else 0.0,
                    min_date=str(parsed.min()),
                    max_date=str(parsed.max()),
                    invalid_count=0,
                    distinct_parsed_values=int(len(years)),
                    notes="numeric column whose integer values fall in a plausible "
                          "year range; read as a year for profiling only",
                )
            else:
                record["notes"] = (
                    "numeric dtype matched only by column name; values are not "
                    "date-like (not whole numbers in a plausible year range), so no "
                    "parse was attempted - likely a duration/measure, needs manual "
                    "review"
                )
            rows.append(record)
            continue

        record["notes"] = "matched by name but dtype is neither text, numeric nor datetime"
        rows.append(record)

    columns = [
        "column", "pandas_dtype", "detected_by", "non_null_count", "null_count",
        "parsed_count", "parse_success_percentage", "min_date", "max_date",
        "invalid_count", "distinct_parsed_values", "notes",
    ]
    return pd.DataFrame(rows, columns=columns)


# --------------------------------------------------------------------------
# 7. string quality
# --------------------------------------------------------------------------
def build_string_quality(
    df: pd.DataFrame, text_cols: list[str], value_counts: dict[str, pd.Series]
) -> pd.DataFrame:
    n_rows = len(df)
    rows = []
    for col in text_cols:
        vc = value_counts[col]
        # Inspect the distinct values and weight by their counts, rather than
        # running the string operations across all 1M rows.
        uniques = pd.Index(vc.index.astype("object")).astype("str")
        counts = vc.to_numpy()
        non_null = int(counts.sum())

        stripped = uniques.str.strip()
        lengths = uniques.str.len().to_numpy()

        ws_mask = np.asarray(stripped != uniques)
        empty_mask = np.asarray(uniques == "")
        ws_only_mask = np.asarray(stripped == "") & ~empty_mask

        unique_count = int(len(uniques))
        case_folded = int(pd.Index(uniques.str.lower()).nunique())
        trim_case_folded = int(pd.Index(stripped.str.lower()).nunique())

        rows.append(
            {
                "column_name": col,
                "pandas_dtype": str(df[col].dtype),
                "non_null_count": non_null,
                "null_count": n_rows - non_null,
                "leading_trailing_whitespace_count": int(counts[ws_mask].sum()),
                "leading_trailing_whitespace_distinct": int(ws_mask.sum()),
                "empty_string_count": int(counts[empty_mask].sum()),
                "whitespace_only_count": int(counts[ws_only_mask].sum()),
                "unique_count": unique_count,
                "unique_count_case_insensitive": case_folded,
                # distinct values that differ from another only by letter case
                "case_only_duplicate_values": unique_count - case_folded,
                "unique_count_trimmed_case_insensitive": trim_case_folded,
                # ... or only by case and/or surrounding whitespace
                "case_or_whitespace_duplicate_values": unique_count - trim_case_folded,
                "min_length": int(lengths.min()) if unique_count else 0,
                "max_length": int(lengths.max()) if unique_count else 0,
                "mean_length_weighted": (
                    round(float((lengths * counts).sum() / non_null), 4)
                    if non_null
                    else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 8. potential key analysis
# --------------------------------------------------------------------------
def build_key_analysis(df: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    n_rows = len(df)
    rows = []
    for record in profile.to_dict("records"):
        unique = int(record["unique_count"])
        nulls = int(record["null_count"])
        ratio = round(unique / n_rows, 6) if n_rows else 0.0
        strictly_unique = unique == n_rows and nulls == 0
        rows.append(
            {
                "column_name": record["column_name"],
                "pandas_dtype": record["pandas_dtype"],
                "row_count": n_rows,
                "unique_count": unique,
                "null_count": nulls,
                "uniqueness_ratio": ratio,
                # every row distinct AND no missing values
                "potential_unique_key": bool(strictly_unique),
                # close to unique - worth a human look, nothing more
                "near_unique_needs_review": bool(
                    ratio >= NEAR_UNIQUE_THRESHOLD and not strictly_unique
                ),
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(
        "uniqueness_ratio", ascending=False, kind="stable"
    ).reset_index(drop=True)


# --------------------------------------------------------------------------
# 9. summary.md
# --------------------------------------------------------------------------
def write_summary_md(
    out_path: Path,
    source: Path,
    fingerprint: dict,
    df: pd.DataFrame,
    buckets: dict[str, list[str]],
    duplicate_rows: int,
    total_memory: int,
    profile: pd.DataFrame,
    numeric: pd.DataFrame,
    categorical: pd.DataFrame,
    dates: pd.DataFrame,
    strings: pd.DataFrame,
    keys: pd.DataFrame,
) -> list[str]:
    n_rows, n_cols = df.shape
    L: list[str] = []
    add = L.append

    add("# Data Profiling Report")
    add("")
    add(f"- **Source file**: `{source.as_posix()}`")
    add(f"- **Generated**: {datetime.now():%Y-%m-%d %H:%M:%S}")
    add(f"- **Source sha256**: `{fingerprint['sha256']}`")
    add("- **Scope**: profiling only. Nothing in `data/raw/` was written to, and no "
        "value in the dataset was cleaned, imputed, re-typed, encoded or removed.")
    add("")
    add("Subsections headed **Observed facts** are measurements taken directly from the "
        "data. Subsections headed **Possible issues for manual review** are hypotheses "
        "that a human must confirm before any decision is taken. No column is "
        "recommended for deletion or modification at this stage.")
    add("")

    # ---- 1 size
    add("## 1. Dataset size")
    add("")
    add("**Observed facts**")
    add("")
    add("| Metric | Value |")
    add("| --- | --- |")
    add(f"| Rows | {n_rows:,} |")
    add(f"| Columns | {n_cols:,} |")
    add(f"| Cells | {n_rows * n_cols:,} |")
    add(f"| File size on disk | {human_bytes(fingerprint['size_bytes'])} |")
    add(f"| In-memory size (pandas, deep) | {human_bytes(total_memory)} |")
    add(f"| Numeric columns | {len(buckets['numeric'])} |")
    add(f"| Text / categorical columns | {len(buckets['text'])} |")
    add(f"| Datetime-dtype columns | {len(buckets['datetime'])} |")
    add(f"| Boolean columns | {len(buckets['boolean'])} |")
    add(f"| Other columns | {len(buckets['other'])} |")
    add("")
    if not buckets["datetime"]:
        add("No column arrives from the CSV as a datetime dtype; date-like columns are "
            "read as text and are analysed in section 6.")
        add("")

    # ---- 2 missing
    add("## 2. Missing data")
    add("")
    add("**Observed facts**")
    add("")
    missing = profile[profile["null_count"] > 0].sort_values(
        "null_count", ascending=False
    )
    total_missing = int(profile["null_count"].sum())
    add(f"- Total missing cells: **{total_missing:,}** "
        f"({pct(total_missing, n_rows * n_cols):.4f}% of all cells).")
    add(f"- Columns with at least one missing value: **{len(missing)} of {n_cols}**.")
    add(f"- Columns with no missing value: **{n_cols - len(missing)}**.")
    add("")
    if len(missing):
        add("| Column | dtype | Missing | Missing % |")
        add("| --- | --- | ---: | ---: |")
        for r in missing.to_dict("records"):
            add(f"| `{r['column_name']}` | {r['pandas_dtype']} | "
                f"{int(r['null_count']):,} | {r['null_percentage']:.4f}% |")
    else:
        add("No column contains a missing value.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    if len(missing):
        worst = missing.iloc[0]
        add(f"- `{worst['column_name']}` has the highest share of missing values "
            f"({worst['null_percentage']:.4f}%). Whether this is structurally missing "
            "(the fact does not exist for that posting) or a collection gap cannot be "
            "decided from the data alone and needs a human judgement.")
        add("- Missingness has **not** been tested for association with the target "
            "`is_fake_posting`. If missingness is itself informative, a later imputation "
            "decision could destroy signal. Flagged, not acted on.")
        add("- Empty strings in text columns are not counted as missing by pandas; see "
            "section 7 for those.")
    else:
        add("- None. Completeness is total; no imputation question arises.")
    add("")

    # ---- 3 duplicates
    add("## 3. Duplicate rows")
    add("")
    add("**Observed facts**")
    add("")
    add(f"- Exact duplicate rows (all {n_cols} columns identical, excess copies only): "
        f"**{duplicate_rows:,}** ({pct(duplicate_rows, n_rows):.4f}% of rows).")
    add(f"- Distinct rows: **{n_rows - duplicate_rows:,}**.")
    add("- Counted with `DataFrame.duplicated(keep='first')`, so the first occurrence of "
        "a repeated row is not counted. **No row was removed.**")
    add("")
    add("**Possible issues for manual review**")
    add("")
    if duplicate_rows:
        add(f"- {duplicate_rows:,} fully identical rows exist. With no identifier column "
            "present (section 8), the data cannot tell us whether these are the same "
            "posting loaded twice or genuinely distinct postings that happen to share "
            "every attribute - both are plausible when many columns are low-cardinality. "
            "Needs manual review before any deduplication is considered.")
    else:
        add("- No exact duplicate row was found.")
    add("- Near-duplicates (rows identical on all but one or two columns) were **not** "
        "searched for: an all-pairs comparison is O(n^2) and infeasible at this row "
        "count. If it matters, do it later with a blocking key over a few columns.")
    add("")

    # ---- 4 numeric
    add("## 4. Numeric columns and anomalies")
    add("")
    add("**Observed facts**")
    add("")
    add("| Column | min | median | max | zeros | negatives | IQR outliers |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in numeric.to_dict("records"):
        add(f"| `{r['column_name']}` | {r['min']:,.4g} | {r['median']:,.4g} | "
            f"{r['max']:,.4g} | {int(r['zero_count']):,} | "
            f"{int(r['negative_count']):,} | {int(r['iqr_outlier_count']):,} "
            f"({r['iqr_outlier_percentage']:.2f}%) |")
    add("")
    add("Full statistics - count, mean, standard deviation, quartiles - are in "
        "`numeric_summary.csv`. IQR outliers use the conventional 1.5x inter-quartile "
        "fences and are a screening device, not a verdict.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    negatives = numeric[numeric["negative_count"] > 0]
    if len(negatives):
        for r in negatives.to_dict("records"):
            add(f"- `{r['column_name']}` contains {int(r['negative_count']):,} negative "
                f"value(s) (min {r['min']:,.4g}). Whether a negative is meaningful here "
                "depends on what the column measures - needs manual review.")
    else:
        add("- No numeric column contains a negative value.")
    heavy_zero = numeric[numeric["zero_count"] / max(n_rows, 1) > 0.5]
    if len(heavy_zero):
        names = ", ".join(f"`{c}`" for c in heavy_zero["column_name"])
        add(f"- More than half of all rows are zero in: {names}. For a 0/1 indicator that "
            "is ordinary class imbalance; for a measured quantity it may signal a default "
            "or placeholder value. The distinction cannot be made automatically.")
    constants = numeric[numeric["distinct_values"] <= 1]
    if len(constants):
        names = ", ".join(f"`{c}`" for c in constants["column_name"])
        add(f"- Constant (single-valued) numeric column(s): {names}. Flagged only - "
            "**not** recommended for removal here.")
    else:
        add("- No numeric column is constant; every numeric column varies.")
    binary = numeric[numeric["distinct_values"] == 2]
    if len(binary):
        names = ", ".join(f"`{c}`" for c in binary["column_name"])
        add(f"- Stored with a numeric dtype but holding only two distinct values: {names}. "
            "These are very likely flags rather than measures, which matters when "
            "deciding what becomes a dimension attribute and what becomes a fact "
            "measure. Confirm manually.")
    worst_outlier = numeric.sort_values("iqr_outlier_percentage", ascending=False)
    if len(worst_outlier) and worst_outlier.iloc[0]["iqr_outlier_percentage"] > 1:
        r = worst_outlier.iloc[0]
        add(f"- `{r['column_name']}` has the largest share of IQR outliers "
            f"({r['iqr_outlier_percentage']:.2f}%, max {r['max']:,.4g}). This may be a "
            "genuine long tail rather than an error; no value was capped or removed.")
    add("")

    # ---- 5 categorical
    add("## 5. Categorical cardinality")
    add("")
    add("**Observed facts**")
    add("")
    add("| Column | Distinct values | Most frequent | Count | % of rows |")
    add("| --- | ---: | --- | ---: | ---: |")
    for r in categorical.sort_values("unique_count", ascending=False).to_dict("records"):
        top = "<NA>" if pd.isna(r["most_frequent_value"]) else str(r["most_frequent_value"])
        top = top.replace("|", "\\|")
        add(f"| `{r['column_name']}` | {int(r['unique_count']):,} | {top} | "
            f"{int(r['most_frequent_count']):,} | {r['most_frequent_percentage']:.3f}% |")
    add("")
    add(f"The top {TOP_N_CATEGORICAL} values of every categorical column, missing values "
        "included, are listed in `categorical_top_values.txt`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    high_card = categorical[categorical["unique_count"] > 1000]
    low_card = categorical[categorical["unique_count"] <= 1]
    dominant = categorical[categorical["most_frequent_percentage"] > 90]
    if len(high_card):
        for r in high_card.to_dict("records"):
            add(f"- `{r['column_name']}` is high-cardinality "
                f"({int(r['unique_count']):,} distinct values). For a star schema this "
                "is a dimension-design question - own dimension, degenerate attribute or "
                "grouped - rather than a data-quality defect.")
    if len(low_card):
        names = ", ".join(f"`{c}`" for c in low_card["column_name"])
        add(f"- Single-valued categorical column(s): {names}. Flagged only.")
    if len(dominant):
        for r in dominant.to_dict("records"):
            add(f"- `{r['column_name']}` is dominated by a single value "
                f"({r['most_frequent_percentage']:.2f}% of rows). Confirm whether the "
                "rare values are real or data-entry noise.")
    if not len(high_card) and not len(low_card) and not len(dominant):
        add("- No categorical column shows extreme cardinality or a dominant-value "
            "imbalance.")
    add("")

    # ---- 6 dates
    add("## 6. Date coverage")
    add("")
    add("**Observed facts**")
    add("")
    add("Candidate date/time columns were detected from the pandas dtype and from column "
        "names containing "
        + ", ".join(f"`{t}`" for t in DATE_NAME_TOKENS)
        + ". Parsing was attempted on a copy of the distinct values only; the dataframe "
          "itself was not converted.")
    add("")
    add("| Column | dtype | Detected by | Parse success | Min | Max | Invalid |")
    add("| --- | --- | --- | ---: | --- | --- | ---: |")
    for r in dates.to_dict("records"):
        lo = "-" if pd.isna(r["min_date"]) else str(r["min_date"])
        hi = "-" if pd.isna(r["max_date"]) else str(r["max_date"])
        add(f"| `{r['column']}` | {r['pandas_dtype']} | {r['detected_by']} | "
            f"{r['parse_success_percentage']:.2f}% | {lo} | {hi} | "
            f"{int(r['invalid_count']):,} |")
    add("")
    parsed_ok = dates[dates["parse_success_percentage"] > 0]
    for r in parsed_ok.to_dict("records"):
        add(f"- `{r['column']}` spans **{str(r['min_date'])[:10]} to "
            f"{str(r['max_date'])[:10]}**, over "
            f"{int(r['distinct_parsed_values']):,} distinct parsed values.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    bad_parse = dates[dates["invalid_count"] > 0]
    not_parsed = dates[dates["parse_success_percentage"] == 0]
    if len(bad_parse):
        for r in bad_parse.to_dict("records"):
            add(f"- `{r['column']}`: {int(r['invalid_count']):,} non-null value(s) could "
                "not be parsed as a date. Inspect them before any conversion.")
    if len(not_parsed):
        for r in not_parsed.to_dict("records"):
            add(f"- `{r['column']}` matched the date-name heuristic but is **not** a "
                f"date: {r['notes']}. Recorded so the heuristic stays auditable.")
    if len(parsed_ok):
        add("- Future-dated and far-past postings were not filtered out. The range above "
            "should be checked against the period the dataset is meant to cover; a date "
            "after the extraction date would be a genuine anomaly. Not acted on.")
        add("- A usable date column matters for the warehouse: it is the natural basis "
            "for a time dimension and for any date-grain roll-up, so its coverage and "
            "granularity deserve a deliberate check.")
    add("")

    # ---- 7 string quality
    add("## 7. Text and string quality")
    add("")
    add("**Observed facts**")
    add("")
    add("| Column | Whitespace-padded | Empty strings | Whitespace-only | Distinct | "
        "Distinct (case-insensitive) | Distinct (trimmed + case-insensitive) |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in strings.to_dict("records"):
        add(f"| `{r['column_name']}` | "
            f"{int(r['leading_trailing_whitespace_count']):,} | "
            f"{int(r['empty_string_count']):,} | "
            f"{int(r['whitespace_only_count']):,} | "
            f"{int(r['unique_count']):,} | "
            f"{int(r['unique_count_case_insensitive']):,} | "
            f"{int(r['unique_count_trimmed_case_insensitive']):,} |")
    add("")
    add("No string value was trimmed, lower-cased or otherwise altered; the "
        "case-insensitive counts come from a temporary copy of the distinct values.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    flagged = False
    for r in strings.to_dict("records"):
        problems = []
        if r["leading_trailing_whitespace_count"]:
            problems.append(
                f"{int(r['leading_trailing_whitespace_count']):,} value(s) carrying "
                "leading or trailing whitespace"
            )
        if r["empty_string_count"]:
            problems.append(
                f"{int(r['empty_string_count']):,} empty string(s), which pandas does "
                "NOT count as missing"
            )
        if r["whitespace_only_count"]:
            problems.append(
                f"{int(r['whitespace_only_count']):,} whitespace-only value(s)"
            )
        if r["case_only_duplicate_values"]:
            problems.append(
                f"{int(r['case_only_duplicate_values']):,} distinct value(s) that differ "
                "from another value only by letter case"
            )
        extra = int(r["case_or_whitespace_duplicate_values"]) - int(
            r["case_only_duplicate_values"]
        )
        if extra > 0:
            problems.append(
                f"{extra:,} further value(s) that collapse once surrounding whitespace "
                "is ignored as well"
            )
        if problems:
            flagged = True
            add(f"- `{r['column_name']}`: " + "; ".join(problems) + ".")
    if not flagged:
        add("- No whitespace padding, empty string, whitespace-only value or "
            "case-variant duplicate was detected in any text column.")
    add("- Case- and whitespace-variant counts indicate *potential* duplicates only. Two "
        "spellings that differ by case may still be two different real entities; this "
        "needs a human decision, especially for company and location names.")
    add("")

    # ---- 8 keys
    add("## 8. Potential identifier columns")
    add("")
    add("**Observed facts**")
    add("")
    add("A column is reported as a *potential* unique key only when it has no missing "
        "value and its distinct-value count equals the row count. **No primary key is "
        "declared by this script.**")
    add("")
    strict = keys[keys["potential_unique_key"]]
    near = keys[keys["near_unique_needs_review"]]
    add(f"- Columns satisfying the strict uniqueness test: **{len(strict)}**.")
    add(f"- Columns that are near-unique (ratio >= {NEAR_UNIQUE_THRESHOLD}) but not "
        f"strictly unique: **{len(near)}**.")
    add("")
    add("Five highest-cardinality columns:")
    add("")
    add("| Column | Distinct | Nulls | Uniqueness ratio | Potential unique key |")
    add("| --- | ---: | ---: | ---: | --- |")
    for r in keys.head(5).to_dict("records"):
        add(f"| `{r['column_name']}` | {int(r['unique_count']):,} | "
            f"{int(r['null_count']):,} | {r['uniqueness_ratio']:.6f} | "
            f"{r['potential_unique_key']} |")
    add("")
    add("Every column is listed in `potential_key_analysis.csv`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    if len(strict) == 0:
        add("- **No single column uniquely identifies a row.** As loaded, the dataset has "
            "no natural primary key. For the warehouse that means a surrogate key will "
            "have to be introduced, or a composite business key agreed after inspection. "
            "That decision is deliberately left open here.")
    else:
        names = ", ".join(f"`{c}`" for c in strict["column_name"])
        add(f"- Strictly unique column(s): {names}. Uniqueness within this extract does "
            "not prove uniqueness in general - confirm against the source before "
            "treating any of them as a business key.")
    if len(near):
        names = ", ".join(f"`{c}`" for c in near["column_name"])
        add(f"- Near-unique column(s) worth inspecting: {names}.")
    add("")

    # ---- 9 review list
    add("## 9. Columns that deserve manual review")
    add("")
    add("Listed because a measurement raised a question, not because anything is known "
        "to be wrong. Nothing here is a recommendation to delete or change a column.")
    add("")
    review: dict[str, list[str]] = {}

    def flag(column: str, reason: str) -> None:
        review.setdefault(column, []).append(reason)

    for r in profile[profile["null_count"] > 0].to_dict("records"):
        flag(r["column_name"], f"{r['null_percentage']:.3f}% missing")
    for r in numeric[numeric["negative_count"] > 0].to_dict("records"):
        flag(r["column_name"], f"{int(r['negative_count']):,} negative value(s)")
    for r in numeric[numeric["iqr_outlier_percentage"] > 1].to_dict("records"):
        flag(r["column_name"], f"{r['iqr_outlier_percentage']:.2f}% IQR outliers")
    for r in numeric[numeric["distinct_values"] <= 2].to_dict("records"):
        flag(
            r["column_name"],
            f"numeric dtype but only {int(r['distinct_values'])} distinct value(s) - "
            "flag or measure?",
        )
    for r in categorical[categorical["unique_count"] > 1000].to_dict("records"):
        flag(r["column_name"], f"high cardinality ({int(r['unique_count']):,} distinct)")
    for r in categorical[categorical["most_frequent_percentage"] > 90].to_dict("records"):
        flag(
            r["column_name"],
            f"dominated by one value ({r['most_frequent_percentage']:.2f}%)",
        )
    for r in strings.to_dict("records"):
        if r["case_or_whitespace_duplicate_values"]:
            flag(
                r["column_name"],
                f"{int(r['case_or_whitespace_duplicate_values']):,} possible "
                "case/whitespace variant duplicate(s)",
            )
        if r["empty_string_count"] or r["whitespace_only_count"]:
            flag(r["column_name"], "empty or whitespace-only values present")
    for r in dates.to_dict("records"):
        if r["invalid_count"]:
            flag(r["column"], f"{int(r['invalid_count']):,} unparseable date value(s)")
        elif r["parse_success_percentage"] == 0:
            flag(r["column"], "matched the date-name rule but is not a date column")
        else:
            flag(
                r["column"],
                f"date range {str(r['min_date'])[:10]} to {str(r['max_date'])[:10]} "
                "needs validation against the intended reporting period",
            )

    add("| Column | Why it is listed |")
    add("| --- | --- |")
    if review:
        for col in df.columns:
            if col in review:
                add(f"| `{col}` | " + "; ".join(review[col]) + " |")
    else:
        add("| - | No column raised a review question. |")
    add("")

    add("## 10. What this report deliberately does not do")
    add("")
    add("- It does not clean, impute, normalise, deduplicate, re-type or drop anything.")
    add("- It does not recommend removing or altering any column.")
    add("- It performs no ML preprocessing: no encoding, scaling, TF-IDF, resampling, "
        "stemming or lemmatisation.")
    add("- It does not declare a primary key.")
    add("- It does not write to `data/raw/`, which remains byte-identical.")
    add("")

    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return [col for col in df.columns if col in review]


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Profile the raw internship dataset (read-only, no cleaning)."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="path to the raw CSV (opened read-only)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="directory for the profiling outputs")
    args = parser.parse_args(argv)

    source: Path = args.input.resolve()
    out_dir: Path = args.output_dir.resolve()

    if not source.is_file():
        print(f"ERROR: input file not found: {source}", file=sys.stderr)
        return 1
    if out_dir == source.parent or out_dir.is_relative_to(source.parent):
        print(
            "ERROR: refusing to write profiling output inside the raw data directory: "
            f"{out_dir}",
            file=sys.stderr,
        )
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    print(SEP)
    print("DATA PROFILING (read-only)")
    print(SEP)
    print(f"Input      : {source}")
    print(f"Output dir : {out_dir}")
    print("Fingerprinting raw file ...", flush=True)
    fingerprint_before = file_fingerprint(source)
    print(f"  size {human_bytes(fingerprint_before['size_bytes'])}, "
          f"sha256 {fingerprint_before['sha256'][:16]}...")

    print("Loading CSV ...", flush=True)
    t0 = time.perf_counter()
    df = pd.read_csv(source)
    load_seconds = time.perf_counter() - t0
    n_rows, n_cols = df.shape
    print(f"  loaded {n_rows:,} rows x {n_cols} columns in {load_seconds:.2f}s")

    buckets = classify_columns(df)
    text_cols = buckets["text"]
    numeric_cols = buckets["numeric"]

    # One hashing pass per text column, reused by the categorical, string-quality
    # and date sections instead of re-scanning each column several times.
    print("Counting distinct values for text columns ...", flush=True)
    value_counts = {col: df[col].value_counts(dropna=True) for col in text_cols}

    print("Counting exact duplicate rows ...", flush=True)
    duplicate_rows = int(df.duplicated(keep="first").sum())

    print("Building profiles ...", flush=True)
    profile = build_column_profile(df)
    numeric = build_numeric_summary(df, numeric_cols)
    categorical = build_categorical_summary(df, text_cols, value_counts)
    dates = build_date_analysis(df, buckets, value_counts)
    strings = build_string_quality(df, text_cols, value_counts)
    keys = build_key_analysis(df, profile)

    print("Writing outputs ...", flush=True)
    overview = write_dataset_overview(
        df,
        out_dir / "dataset_overview.txt",
        source,
        fingerprint_before,
        duplicate_rows,
        load_seconds,
    )
    profile.to_csv(out_dir / "column_profile.csv", index=False)
    numeric.to_csv(out_dir / "numeric_summary.csv", index=False)
    categorical.to_csv(out_dir / "categorical_summary.csv", index=False)
    write_categorical_top_values(df, text_cols, out_dir / "categorical_top_values.txt")
    dates.to_csv(out_dir / "date_analysis.csv", index=False)
    strings.to_csv(out_dir / "string_quality.csv", index=False)
    keys.to_csv(out_dir / "potential_key_analysis.csv", index=False)
    review_columns = write_summary_md(
        out_dir / "summary.md",
        source,
        fingerprint_before,
        df,
        buckets,
        duplicate_rows,
        overview["total_memory_bytes"],
        profile,
        numeric,
        categorical,
        dates,
        strings,
        keys,
    )

    fingerprint_after = file_fingerprint(source)
    raw_unchanged = fingerprint_after == fingerprint_before

    # ---- terminal summary
    total_missing = int(profile["null_count"].sum())
    cols_with_nulls = int((profile["null_count"] > 0).sum())
    strict_keys = keys[keys["potential_unique_key"]]["column_name"].tolist()
    parsed_dates = dates[dates["parse_success_percentage"] > 0]

    print()
    print(SEP)
    print("PROFILING SUMMARY")
    print(SEP)
    print(f"Rows x columns        : {n_rows:,} x {n_cols}")
    print(f"In-memory size        : {human_bytes(overview['total_memory_bytes'])}")
    print(f"Column types          : {len(numeric_cols)} numeric, {len(text_cols)} text, "
          f"{len(buckets['datetime'])} datetime, {len(buckets['boolean'])} boolean, "
          f"{len(buckets['other'])} other")
    print(f"Missing cells         : {total_missing:,} "
          f"({pct(total_missing, n_rows * n_cols):.4f}%) in {cols_with_nulls} column(s)")
    print(f"Exact duplicate rows  : {duplicate_rows:,} "
          f"({pct(duplicate_rows, n_rows):.4f}%)")
    neg_cols = numeric[numeric["negative_count"] > 0]["column_name"].tolist()
    print(f"Numeric w/ negatives  : {len(neg_cols)}"
          + (f" -> {', '.join(neg_cols[:5])}" if neg_cols else ""))
    if len(categorical):
        widest = categorical.sort_values("unique_count", ascending=False).iloc[0]
        print(f"Highest cardinality   : {widest['column_name']} "
              f"({int(widest['unique_count']):,} distinct values)")
    for r in parsed_dates.to_dict("records"):
        print(f"Date coverage         : {r['column']} "
              f"{str(r['min_date'])[:10]} -> {str(r['max_date'])[:10]} "
              f"({r['parse_success_percentage']:.2f}% parsed, "
              f"{int(r['invalid_count']):,} invalid)")
    print("Potential unique keys : "
          f"{', '.join(strict_keys) if strict_keys else 'none (no natural primary key)'}")
    print(f"Columns flagged for manual review : {len(review_columns)}")
    print()
    print("Files written:")
    for path in sorted(p for p in out_dir.glob("*") if p.is_file()):
        print(f"  {path.name:<32} {human_bytes(path.stat().st_size):>12}")
    print()
    print(f"Raw file unchanged    : {'YES' if raw_unchanged else 'NO - INVESTIGATE'} "
          "(sha256 re-checked after profiling)")
    print(SEP)
    print("Profiling only. Nothing was cleaned, imputed, encoded or removed.")
    print(SEP)

    return 0 if raw_unchanged else 2


if __name__ == "__main__":
    raise SystemExit(main())
