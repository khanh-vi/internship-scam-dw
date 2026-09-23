#!/usr/bin/env python3
"""
Staging build for the fake-internship-detection dataset.

STAGING LAYER ONLY.  The raw CSV is opened read-only, never written to and
never re-saved; its sha256 is verified before and after the run.  Exactly
three transformations are applied, all of them approved in
docs/cleaning_rules.md:

    1. posting_date is parsed as a real date and emitted as ISO YYYY-MM-DD
    2. source_row_id is added    (staging lineage identifier, not a business key)
    3. is_future_posting is added (data-quality flag, fixed cutoff 2026-09-23)

Nothing else is changed.  No imputation, no row or column deletion, no
de-duplication, no category mapping, no scaling, no outlier treatment, no
currency conversion, no stipend normalisation, no label derivation.

The CSV is always read with a quote-aware parser; `company_name` contains
embedded commas inside quoted fields (e.g. "Russell, Medina and Evans"), so
naive comma splitting would shift every field after it.  A structural pre-scan
with the stdlib `csv` module proves every physical record carries exactly 33
fields before any value is typed.

Outputs:
    data/staging/internship_postings_staging.csv
    results/staging/staging_validation.md
    results/staging/staging_column_profile.csv
    results/staging/transformation_log.md

Usage:
    python scripts/build_staging.py
    python scripts/build_staging.py --input <csv> --output <csv> --report-dir <dir>
    python scripts/build_staging.py --chunksize 100000
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "fake_internship_detection_dataset.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "staging" / "internship_postings_staging.csv"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "results" / "staging"

# --------------------------------------------------------------------------
# fixed, documented constants
# --------------------------------------------------------------------------
# docs/data_dictionary.md header.  The raw file must still be this exact file.
EXPECTED_RAW_SHA256 = "3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398"

# The audit / reference date.  A FIXED CONSTANT, never the system clock: the
# flag has to be reproducible, so the flagged-row count must not drift between
# runs (docs/cleaning_rules.md R4.2.6).
FUTURE_CUTOFF = "2026-09-23"

DATE_COLUMN = "posting_date"
DATE_FORMAT = "%Y-%m-%d"
ROW_ID_COLUMN = "source_row_id"
FUTURE_FLAG_COLUMN = "is_future_posting"

# The 33 source columns, in original file order.  This order is asserted
# against the physical header and preserved verbatim in the output.
SOURCE_COLUMNS = [
    "posting_date",
    "internship_title",
    "employment_type",
    "work_mode",
    "industry",
    "location",
    "company_name",
    "company_size",
    "company_age",
    "linkedin_presence",
    "website_available",
    "domain_age_months",
    "verification_status",
    "stipend",
    "unrealistic_salary_flag",
    "payment_required",
    "registration_fee",
    "job_description_length",
    "grammatical_errors",
    "vague_description_score",
    "urgency_score",
    "keyword_spam_score",
    "fake_certificate_offer",
    "recruiter_experience_years",
    "recruiter_email_type",
    "suspicious_email_domain",
    "recruiter_response_time_hours",
    "social_media_presence",
    "emotional_manipulation_score",
    "phishing_language_score",
    "trust_signal_score",
    "fraud_score",
    "is_fake_posting",
]

# Output column order: the 33 source columns untouched in positions 1..33,
# then the two derived columns appended.
STAGING_COLUMNS = SOURCE_COLUMNS + [ROW_ID_COLUMN, FUTURE_FLAG_COLUMN]

TEXT_COLUMNS = [
    "internship_title",
    "employment_type",
    "work_mode",
    "industry",
    "location",
    "company_name",
    "company_size",
    "recruiter_email_type",
]

# Verified by the audit: zero non-integral non-null values across 1,000,000
# rows, so nullable-integer semantics lose nothing.  NULL stays NULL.
NULLABLE_INT_COLUMNS = ["company_age", "stipend"]

NON_NULL_INT_COLUMNS = [
    "linkedin_presence",
    "website_available",
    "domain_age_months",
    "verification_status",
    "unrealistic_salary_flag",
    "payment_required",
    "registration_fee",
    "job_description_length",
    "grammatical_errors",
    "vague_description_score",
    "urgency_score",
    "keyword_spam_score",
    "fake_certificate_offer",
    "suspicious_email_domain",
    "social_media_presence",
    "emotional_manipulation_score",
    "phishing_language_score",
    "is_fake_posting",
]

INT_COLUMNS = NULLABLE_INT_COLUMNS + NON_NULL_INT_COLUMNS

# Documented one-decimal columns.  Precision is preserved; they are NOT
# rounded to integers and NOT re-scaled.
DECIMAL1_COLUMNS = [
    "recruiter_experience_years",
    "recruiter_response_time_hours",
    "trust_signal_score",
    "fraud_score",
]

BINARY_COLUMNS = [
    "linkedin_presence",
    "website_available",
    "verification_status",
    "unrealistic_salary_flag",
    "payment_required",
    "fake_certificate_offer",
    "suspicious_email_domain",
    "social_media_presence",
    "is_fake_posting",
]

SCORE_COLUMNS = [
    "vague_description_score",
    "urgency_score",
    "keyword_spam_score",
    "emotional_manipulation_score",
    "phishing_language_score",
    "trust_signal_score",
    "fraud_score",
]
SCORE_MIN, SCORE_MAX = 0.0, 100.0

MISSING_EXPECTED_COLUMNS = ["company_age", "stipend", "trust_signal_score"]

# Columns for which a numeric min/max is meaningful in the column profile.
MINMAX_COLUMNS = INT_COLUMNS + DECIMAL1_COLUMNS + [ROW_ID_COLUMN, FUTURE_FLAG_COLUMN]

# Intended staging datatype, taken verbatim from docs/data_dictionary.md
# sections 2 and 4.  A CSV carries no datatype metadata, so the intent is
# recorded here and the values are written faithfully.
INTENDED_SQL_TYPE = {
    "posting_date": "DATE NOT NULL",
    "internship_title": "VARCHAR(32) NOT NULL",
    "employment_type": "VARCHAR(16) NOT NULL",
    "work_mode": "VARCHAR(16) NOT NULL",
    "industry": "VARCHAR(24) NOT NULL",
    "location": "VARCHAR(24) NOT NULL",
    "company_name": "VARCHAR(64) NOT NULL",
    "company_size": "VARCHAR(16) NOT NULL",
    "company_age": "SMALLINT NULL",
    "linkedin_presence": "SMALLINT NOT NULL",
    "website_available": "SMALLINT NOT NULL",
    "domain_age_months": "SMALLINT NOT NULL",
    "verification_status": "SMALLINT NOT NULL",
    "stipend": "INTEGER NULL",
    "unrealistic_salary_flag": "SMALLINT NOT NULL",
    "payment_required": "SMALLINT NOT NULL",
    "registration_fee": "INTEGER NOT NULL",
    "job_description_length": "SMALLINT NOT NULL",
    "grammatical_errors": "SMALLINT NOT NULL",
    "vague_description_score": "SMALLINT NOT NULL",
    "urgency_score": "SMALLINT NOT NULL",
    "keyword_spam_score": "SMALLINT NOT NULL",
    "fake_certificate_offer": "SMALLINT NOT NULL",
    "recruiter_experience_years": "DECIMAL(3,1) NOT NULL",
    "recruiter_email_type": "VARCHAR(16) NOT NULL",
    "suspicious_email_domain": "SMALLINT NOT NULL",
    "recruiter_response_time_hours": "DECIMAL(3,1) NOT NULL",
    "social_media_presence": "SMALLINT NOT NULL",
    "emotional_manipulation_score": "SMALLINT NOT NULL",
    "phishing_language_score": "SMALLINT NOT NULL",
    "trust_signal_score": "DECIMAL(4,1) NULL",
    "fraud_score": "DECIMAL(4,1) NOT NULL",
    "is_fake_posting": "SMALLINT NOT NULL",
    ROW_ID_COLUMN: "INTEGER NOT NULL",
    FUTURE_FLAG_COLUMN: "SMALLINT NOT NULL",
}

TRANSFORMATION_NOTE = {col: "None - preserved verbatim from source" for col in SOURCE_COLUMNS}
TRANSFORMATION_NOTE[DATE_COLUMN] = (
    "Parsed as a real date, emitted as ISO YYYY-MM-DD (approved representation change; "
    "no value re-dated, no row removed)"
)
for _col in NULLABLE_INT_COLUMNS:
    TRANSFORMATION_NOTE[_col] = (
        "None - value preserved; typed as nullable integer (0 non-integral source values); "
        "NULL preserved as NULL"
    )
TRANSFORMATION_NOTE[ROW_ID_COLUMN] = "Derived: lineage"
TRANSFORMATION_NOTE[FUTURE_FLAG_COLUMN] = "Derived: data-quality flag"

SOURCE_OR_DERIVED = {col: "Source" for col in SOURCE_COLUMNS}
SOURCE_OR_DERIVED[ROW_ID_COLUMN] = "Derived"
SOURCE_OR_DERIVED[FUTURE_FLAG_COLUMN] = "Derived"

# --------------------------------------------------------------------------
# expectations carried over from the completed profiling / audit phase
#
# These are POST-TRANSFORMATION ASSERTIONS ONLY.  None of them is consulted by
# the transformation logic; a mismatch means the source changed, and is
# reported, never repaired.
# --------------------------------------------------------------------------
EXPECT_ROWS = 1_000_000
EXPECT_SOURCE_COLUMNS = 33
EXPECT_STAGING_COLUMNS = 35
EXPECT_FUTURE_ROWS = 30_246
EXPECT_DATE_MIN = "2018-01-01"
EXPECT_DATE_MAX = "2026-12-31"
EXPECT_DISTINCT_DATES = 3_287
EXPECT_MISSING = {"company_age": 10_000, "stipend": 10_000, "trust_signal_score": 10_000}
EXPECT_DISTINCT = {
    "internship_title": 9,
    "employment_type": 4,
    "work_mode": 3,
    "industry": 9,
    "location": 9,
    "company_name": 535_938,
    "company_size": 4,
    "recruiter_email_type": 2,
}
EXPECT_RANGES = {
    "company_age": (1, 39),
    "domain_age_months": (1, 500),
    "stipend": (2_000, 110_428),
    "registration_fee": (0, 4_999),
    "job_description_length": (100, 5_000),
    "grammatical_errors": (0, 14),
    "recruiter_experience_years": (0.0, 19.6),
    "recruiter_response_time_hours": (1.0, 63.9),
}

SEP = "=" * 78


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def rel(path: Path) -> str:
    """Project-relative path for reports; falls back to the absolute path."""
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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
    return round(100.0 * part / whole, 6)


def file_fingerprint(path: Path) -> dict:
    """Size / mtime / sha256 of a file, used to prove the raw CSV is untouched."""
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest.hexdigest(),
    }


class Report:
    """Collects PASS/FAIL checks in declaration order."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def check(self, ref, name, passed, observed, expected, note=""):
        self.rows.append(
            {
                "ref": str(ref),
                "check": name,
                "status": "PASS" if passed else "FAIL",
                "observed": str(observed),
                "expected": str(expected),
                "note": note,
            }
        )
        return bool(passed)

    @property
    def failures(self) -> list[dict]:
        return [r for r in self.rows if r["status"] != "PASS"]

    @property
    def ok(self) -> bool:
        return not self.failures


class ColumnStats:
    """Streaming per-column statistics accumulated across chunks."""

    def __init__(self, columns: list[str], track_values: bool = True) -> None:
        self.track_values = track_values
        self.non_null = {c: 0 for c in columns}
        self.null = {c: 0 for c in columns}
        self.distinct = {c: set() for c in columns}
        self.minimum = {c: None for c in columns}
        self.maximum = {c: None for c in columns}
        self.digest = {c: hashlib.sha256() for c in columns}
        self.pandas_dtype: dict[str, str] = {}

    def update(self, df: pd.DataFrame) -> None:
        for col in df.columns:
            series = df[col]
            n_null = int(series.isna().sum())
            self.null[col] += n_null
            self.non_null[col] += int(len(series) - n_null)

            if self.track_values:
                values = series.dropna()
                if pd.api.types.is_datetime64_any_dtype(series):
                    values = values.dt.strftime(DATE_FORMAT)
                self.distinct[col].update(values.unique().tolist())
                if len(values):
                    lo, hi = values.min(), values.max()
                    self.minimum[col] = lo if self.minimum[col] is None else min(self.minimum[col], lo)
                    self.maximum[col] = hi if self.maximum[col] is None else max(self.maximum[col], hi)

            # Order-sensitive value fingerprint: per-row 64-bit hashes appended
            # in file order, so the digest covers values *and* their sequence.
            hashed = series.dt.strftime(DATE_FORMAT) if pd.api.types.is_datetime64_any_dtype(series) else series
            row_hashes = pd.util.hash_pandas_object(hashed, index=False).to_numpy(dtype=np.uint64)
            self.digest[col].update(row_hashes.tobytes())

    def digests(self) -> dict:
        return {c: h.hexdigest() for c, h in self.digest.items()}


# --------------------------------------------------------------------------
# pass 0 - structural scan with a quote-aware reader
# --------------------------------------------------------------------------
def scan_structure(path: Path) -> dict:
    """
    Walk every physical record with the stdlib csv reader (RFC 4180 quote
    handling) and confirm each one yields exactly 33 fields.

    This is the field-shift guard.  A naive line.split(",") would break on
    "Russell, Medina and Evans"; this pass proves the quote-aware parse is
    structurally sound before any value is typed.
    """
    bad_rows: list[tuple[int, int]] = []
    field_counts: dict[int, int] = {}
    n_records = 0
    quoted_field_rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        for lineno, row in enumerate(reader, start=2):
            if not row:  # tolerate a trailing blank line; it is not a record
                continue
            n_records += 1
            width = len(row)
            field_counts[width] = field_counts.get(width, 0) + 1
            if width != EXPECT_SOURCE_COLUMNS:
                if len(bad_rows) < 20:
                    bad_rows.append((lineno, width))
                continue
            if "," in row[6]:  # company_name, the column with embedded commas
                quoted_field_rows += 1
    n_bad = sum(c for w, c in field_counts.items() if w != EXPECT_SOURCE_COLUMNS)
    return {
        "header": header,
        "n_header_fields": len(header),
        "n_records": n_records,
        "field_counts": dict(sorted(field_counts.items())),
        "bad_rows": bad_rows,
        "n_bad_rows": n_bad,
        "all_rows_33": set(field_counts) == {EXPECT_SOURCE_COLUMNS},
        "quoted_comma_rows": quoted_field_rows,
    }


# --------------------------------------------------------------------------
# shared typing - used identically on the raw side and on the staging re-read
# --------------------------------------------------------------------------
def read_chunks(path: Path, chunksize: int):
    """
    Quote-aware chunked read.  Every field is read as text so that typing is
    explicit and byte-for-byte identical on both sides of the round trip.

    keep_default_na=False with na_values=[""] means ONLY a physically empty
    field becomes NULL.  A literal text value such as "NA" or "None" is
    preserved verbatim rather than silently turned into a null.
    """
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
        chunksize=chunksize,
        encoding="utf-8-sig",
        on_bad_lines="error",
    )


def empty_issues() -> dict:
    return {
        "date_parse_failures": 0,
        "non_integral": {},
        "non_numeric": {},
        "non_one_decimal": {},
        "unexpected_null_int_columns": {},
    }


def merge_issues(total: dict, chunk: dict) -> None:
    """Accumulate typing defects across chunks."""
    total["date_parse_failures"] += chunk["date_parse_failures"]
    for key in ("non_integral", "non_numeric", "non_one_decimal", "unexpected_null_int_columns"):
        for col, n in chunk[key].items():
            total[key][col] = total[key].get(col, 0) + n


def apply_staging_types(text_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Convert an all-text chunk into the staging dtypes.

    Value-preserving only: no mapping, no rounding, no clipping, no fill.
    Returns the typed frame plus the defects observed while typing.
    """
    out = pd.DataFrame(index=text_df.index)
    issues = empty_issues()

    raw_date = text_df[DATE_COLUMN]
    parsed = pd.to_datetime(raw_date, format=DATE_FORMAT, errors="coerce")
    # A failure is counted and reported, never coerced to a default or dropped.
    issues["date_parse_failures"] = int((parsed.isna() & raw_date.notna()).sum())
    out[DATE_COLUMN] = parsed

    for col in TEXT_COLUMNS:
        out[col] = text_df[col]

    for col in INT_COLUMNS:
        num = pd.to_numeric(text_df[col], errors="coerce")
        unparsed = int((num.isna() & text_df[col].notna()).sum())
        if unparsed:
            issues["non_numeric"][col] = unparsed
        non_integral = int((num.notna() & (num % 1 != 0)).sum())
        if non_integral:
            issues["non_integral"][col] = non_integral
        if col in NULLABLE_INT_COLUMNS:
            out[col] = num.astype("Int64")
        else:
            n_null = int(num.isna().sum())
            if n_null:
                # Not expected in any of the 30 NOT NULL columns.  Surface it
                # and keep the null rather than crash or invent a value.
                issues["unexpected_null_int_columns"][col] = n_null
                out[col] = num.astype("Int64")
            else:
                out[col] = num.astype("int64")

    for col in DECIMAL1_COLUMNS:
        num = pd.to_numeric(text_df[col], errors="coerce")
        unparsed = int((num.isna() & text_df[col].notna()).sum())
        if unparsed:
            issues["non_numeric"][col] = unparsed
        scaled = num * 10.0
        off_grid = int((num.notna() & ((scaled - scaled.round()).abs() > 1e-6)).sum())
        if off_grid:
            issues["non_one_decimal"][col] = off_grid
        out[col] = num

    return out[SOURCE_COLUMNS], issues


# --------------------------------------------------------------------------
# pass 1 - build
# --------------------------------------------------------------------------
def build_staging(input_path: Path, output_path: Path, chunksize: int) -> dict:
    """
    Stream the raw CSV into the staging CSV.

    Row order is never altered, so the running counter that produces
    source_row_id stays monotonic across chunks and is never reset.  The header
    is written once; every chunk carries the identical 35-column schema.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cutoff = pd.Timestamp(FUTURE_CUTOFF)

    issues = empty_issues()
    next_row_id = 1
    n_rows = 0
    n_chunks = 0
    header_seen: list[str] = []
    schemas: set[tuple[str, ...]] = set()

    with output_path.open("w", encoding="utf-8", newline="") as out_fh:
        for text_chunk in read_chunks(input_path, chunksize):
            n_chunks += 1
            if not header_seen:
                header_seen = list(text_chunk.columns)
            typed, chunk_issues = apply_staging_types(text_chunk)
            merge_issues(issues, chunk_issues)

            # 2. source_row_id - file order, continuing across chunk boundaries.
            n = len(typed)
            typed[ROW_ID_COLUMN] = np.arange(next_row_id, next_row_id + n, dtype=np.int64)
            next_row_id += n

            # 3. is_future_posting - fixed documented cutoff, not the clock.
            typed[FUTURE_FLAG_COLUMN] = (typed[DATE_COLUMN] > cutoff).astype("int64")

            typed = typed[STAGING_COLUMNS]
            schemas.add(tuple(typed.columns))
            typed.to_csv(
                out_fh,
                index=False,
                header=(n_chunks == 1),
                date_format=DATE_FORMAT,
                lineterminator="\n",
            )
            n_rows += n

    return {
        "raw_header": header_seen,
        "n_rows": n_rows,
        "n_chunks": n_chunks,
        "max_row_id": next_row_id - 1,
        "issues": issues,
        "schema_variants": len(schemas),
        "written_schema": list(next(iter(schemas))) if schemas else [],
    }


# --------------------------------------------------------------------------
# pass 2 - validate the written file against the raw file, in lockstep
# --------------------------------------------------------------------------
def validate_staging(input_path: Path, output_path: Path, chunksize: int) -> dict:
    """
    Re-read the staging CSV with a quote-aware parser and walk it alongside the
    raw CSV, chunk for chunk, applying identical typing to both sides.

    Everything the validation report needs is accumulated here in one streaming
    pass so the full 1,000,000-row output is never held in memory at once.
    """
    cutoff = pd.Timestamp(FUTURE_CUTOFF)
    stats = ColumnStats(STAGING_COLUMNS)
    raw_stats = ColumnStats(SOURCE_COLUMNS, track_values=False)

    state = {
        "n_rows": 0,
        "staging_header": [],
        "row_id_seen": np.zeros(EXPECT_ROWS + 2, dtype=bool),
        "row_id_out_of_range": 0,
        "row_id_monotonic": True,
        "row_id_duplicates": 0,
        "prev_row_id": 0,
        "future_count": 0,
        "future_domain_violations": 0,
        "future_recomputed_mismatch": 0,
        "date_parse_failures": 0,
        "binary_violations": {c: 0 for c in BINARY_COLUMNS},
        "binary_nulls": {c: 0 for c in BINARY_COLUMNS},
        "score_out_of_range": {c: 0 for c in SCORE_COLUMNS},
        "payment_violations": 0,
        "email_violations": 0,
        "negative_values": {},
        "range_violations": {c: 0 for c in EXPECT_RANGES},
        "value_mismatch": {c: 0 for c in SOURCE_COLUMNS},
        "null_mask_mismatch": {c: 0 for c in SOURCE_COLUMNS},
        "text_padded": 0,
        "text_empty": 0,
        "text_whitespace_only": 0,
        "row_hashes": np.empty(0, dtype=np.uint64),
        "issues": empty_issues(),
        "date_format_violations": 0,
    }

    row_hash_parts: list[np.ndarray] = []
    raw_reader = read_chunks(input_path, chunksize)

    for stage_text in read_chunks(output_path, chunksize):
        if not state["staging_header"]:
            state["staging_header"] = list(stage_text.columns)

        raw_text = next(raw_reader)
        if len(raw_text) != len(stage_text):
            raise RuntimeError(
                "lockstep desynchronised: raw chunk %d rows vs staging chunk %d rows"
                % (len(raw_text), len(stage_text))
            )

        # The raw side goes through exactly the same typing code, so any
        # difference that survives is a real round-trip defect, not a dtype
        # artefact of the comparison itself.
        raw_typed, raw_issues = apply_staging_types(raw_text)
        merge_issues(state["issues"], raw_issues)

        # -- posting_date is checked on its written text before parsing -------
        written_date = stage_text[DATE_COLUMN]
        iso_ok = written_date.str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
        state["date_format_violations"] += int((~iso_ok).sum())

        stage_typed, stage_issues = apply_staging_types(
            stage_text[SOURCE_COLUMNS].reset_index(drop=True)
        )
        state["date_parse_failures"] += stage_issues["date_parse_failures"]

        raw_typed = raw_typed.reset_index(drop=True)
        stage_typed = stage_typed.reset_index(drop=True)

        # -- 28: value preservation, source column by source column -----------
        for col in SOURCE_COLUMNS:
            left, right = raw_typed[col], stage_typed[col]
            left_null, right_null = left.isna(), right.isna()
            null_mismatch = int((left_null != right_null).sum())
            if null_mismatch:
                state["null_mask_mismatch"][col] += null_mismatch
            both = ~left_null & ~right_null
            if both.any():
                diff = int((left[both] != right[both]).sum())
                if diff:
                    state["value_mismatch"][col] += diff

        # -- derived columns --------------------------------------------------
        row_ids = pd.to_numeric(
            stage_text[ROW_ID_COLUMN].reset_index(drop=True), errors="coerce"
        )
        future = pd.to_numeric(
            stage_text[FUTURE_FLAG_COLUMN].reset_index(drop=True), errors="coerce"
        )

        ids = row_ids.dropna().astype("int64").to_numpy()
        in_range = (ids >= 1) & (ids <= EXPECT_ROWS)
        state["row_id_out_of_range"] += int((~in_range).sum()) + int(row_ids.isna().sum())
        valid_ids = ids[in_range]
        already = state["row_id_seen"][valid_ids]
        state["row_id_duplicates"] += int(already.sum())
        state["row_id_seen"][valid_ids] = True
        if len(ids):
            if ids[0] != state["prev_row_id"] + 1 or not np.all(np.diff(ids) == 1):
                state["row_id_monotonic"] = False
            state["prev_row_id"] = int(ids[-1])

        state["future_domain_violations"] += int((~future.isin([0, 1])).sum())
        state["future_count"] += int((future == 1).sum())
        recomputed = (stage_typed[DATE_COLUMN] > cutoff).astype("int64")
        state["future_recomputed_mismatch"] += int((recomputed != future.fillna(-1)).sum())

        # -- 23: binary domains ----------------------------------------------
        for col in BINARY_COLUMNS:
            series = stage_typed[col]
            state["binary_nulls"][col] += int(series.isna().sum())
            state["binary_violations"][col] += int((~series.isin([0, 1]) & series.notna()).sum())

        # -- 24: score ranges -------------------------------------------------
        for col in SCORE_COLUMNS:
            series = stage_typed[col]
            bad = series.notna() & ((series < SCORE_MIN) | (series > SCORE_MAX))
            state["score_out_of_range"][col] += int(bad.sum())

        # -- 25 / 26: cross-column invariants (validated, never used to derive)
        fee = stage_typed["registration_fee"]
        state["payment_violations"] += int(
            (stage_typed["payment_required"] != (fee > 0).astype("int64")).sum()
        )
        email = stage_typed["recruiter_email_type"]
        domain = stage_typed["suspicious_email_domain"]
        corporate_bad = int(((email == "Corporate") != (domain == 0)).sum())
        free_bad = int(((email == "Free") != (domain == 1)).sum())
        state["email_violations"] += corporate_bad + free_bad

        # -- descriptive range / sign checks ----------------------------------
        for col in INT_COLUMNS + DECIMAL1_COLUMNS:
            series = stage_typed[col]
            neg = int((series.notna() & (series < 0)).sum())
            if neg:
                state["negative_values"][col] = state["negative_values"].get(col, 0) + neg
        for col, (lo, hi) in EXPECT_RANGES.items():
            series = stage_typed[col]
            bad = series.notna() & ((series < lo) | (series > hi))
            state["range_violations"][col] += int(bad.sum())

        # -- text quality: reported, never repaired ---------------------------
        for col in TEXT_COLUMNS:
            series = stage_typed[col].dropna()
            stripped = series.str.strip()
            state["text_padded"] += int((series != stripped).sum())
            state["text_empty"] += int((series == "").sum())
            state["text_whitespace_only"] += int(((series != "") & (stripped == "")).sum())

        # -- 27: duplicate detection over the 33 SOURCE columns only ----------
        # source_row_id is excluded by construction; including it would make
        # every staging row unique and the check meaningless.
        row_hash_parts.append(
            pd.util.hash_pandas_object(stage_typed[SOURCE_COLUMNS], index=False).to_numpy(
                dtype=np.uint64
            )
        )

        full = stage_typed.copy()
        full[ROW_ID_COLUMN] = row_ids.astype("int64")
        full[FUTURE_FLAG_COLUMN] = future.astype("int64")
        stats.update(full[STAGING_COLUMNS])
        raw_stats.update(raw_typed)

        state["n_rows"] += len(stage_text)

    leftover = 0
    for extra in raw_reader:
        leftover += len(extra)
    state["raw_rows_beyond_staging"] = leftover

    state["row_hashes"] = np.concatenate(row_hash_parts) if row_hash_parts else np.empty(0, np.uint64)
    state["distinct_row_hashes"] = int(np.unique(state["row_hashes"]).size)
    state["row_id_coverage"] = int(state["row_id_seen"][1 : EXPECT_ROWS + 1].sum())
    return {"state": state, "stats": stats, "raw_stats": raw_stats}


# --------------------------------------------------------------------------
# reports
# --------------------------------------------------------------------------
def build_checks(
    fp_before: dict,
    fp_after: dict,
    structure: dict,
    build_info: dict,
    result: dict,
) -> Report:
    """Assemble every PASS/FAIL check required by docs/cleaning_rules.md section 10."""
    rep = Report()
    state, stats, raw_stats = result["state"], result["stats"], result["raw_stats"]
    n = state["n_rows"]
    issues = state["issues"]

    # 1-2, 29: raw immutability
    rep.check(1, "Raw sha256 before processing matches the documented digest",
              fp_before["sha256"] == EXPECTED_RAW_SHA256, fp_before["sha256"], EXPECTED_RAW_SHA256)
    rep.check(2, "Raw sha256 after processing matches the documented digest",
              fp_after["sha256"] == EXPECTED_RAW_SHA256, fp_after["sha256"], EXPECTED_RAW_SHA256)
    rep.check(29, "Raw file unchanged by the run (sha256 + size + mtime)",
              fp_before == fp_after,
              "sha256 %s / %d bytes / mtime_ns %d" % (fp_after["sha256"][:16], fp_after["size_bytes"], fp_after["mtime_ns"]),
              "identical to the pre-run fingerprint")

    # 3-4: parsing
    rep.check(3, "CSV read with a quote-aware parser (embedded commas preserved)",
              structure["quoted_comma_rows"] > 0 and structure["all_rows_33"],
              "%d rows carry a comma inside a quoted company_name; all records parse to 33 fields"
              % structure["quoted_comma_rows"],
              "quote-aware parse, no field shift",
              "A naive split(',') would widen these rows and shift every later field.")
    rep.check(4, "Every parsed record has exactly 33 source fields",
              structure["all_rows_33"] and structure["n_header_fields"] == EXPECT_SOURCE_COLUMNS,
              "header %d fields; record widths %s; malformed records %d"
              % (structure["n_header_fields"], structure["field_counts"], structure["n_bad_rows"]),
              "33 for the header and for all %d records" % EXPECT_ROWS,
              "Any other width is treated as a fatal field-shift error.")

    # 5-9: shape and column preservation
    rep.check(5, "Raw row count", structure["n_records"] == EXPECT_ROWS,
              f"{structure['n_records']:,}", f"{EXPECT_ROWS:,}")
    rep.check(6, "Staging row count", n == EXPECT_ROWS, f"{n:,}", f"{EXPECT_ROWS:,}",
              "No row removed, including the future-dated ones.")
    rep.check(7, "Staging column count", len(state["staging_header"]) == EXPECT_STAGING_COLUMNS,
              len(state["staging_header"]), EXPECT_STAGING_COLUMNS, "33 source + 2 derived")
    missing_cols = [c for c in SOURCE_COLUMNS if c not in state["staging_header"]]
    rep.check(8, "All 33 original columns retained", not missing_cols,
              "0 missing" if not missing_cols else ", ".join(missing_cols), "0 missing")
    rep.check(9, "Original column order preserved",
              state["staging_header"][:EXPECT_SOURCE_COLUMNS] == SOURCE_COLUMNS
              and structure["header"] == SOURCE_COLUMNS,
              "source columns occupy output positions 1-33 in file order",
              "identical to the raw header order",
              "The two derived columns are appended at positions 34-35.")

    # 10-13: source_row_id
    ids_min = stats.minimum[ROW_ID_COLUMN]
    ids_max = stats.maximum[ROW_ID_COLUMN]
    rep.check(10, "source_row_id minimum", ids_min == 1, ids_min, 1)
    rep.check(11, "source_row_id maximum", ids_max == EXPECT_ROWS, f"{ids_max:,}", f"{EXPECT_ROWS:,}")
    rep.check(12, "source_row_id unique",
              state["row_id_duplicates"] == 0
              and state["row_id_coverage"] == EXPECT_ROWS
              and len(stats.distinct[ROW_ID_COLUMN]) == n,
              "%d distinct, %d duplicate(s), %d of 1..%d covered"
              % (len(stats.distinct[ROW_ID_COLUMN]), state["row_id_duplicates"],
                 state["row_id_coverage"], EXPECT_ROWS),
              "1,000,000 distinct, 0 duplicates, contiguous")
    rep.check(13, "source_row_id non-null and out-of-range free",
              stats.null[ROW_ID_COLUMN] == 0 and state["row_id_out_of_range"] == 0,
              "%d null, %d out of range" % (stats.null[ROW_ID_COLUMN], state["row_id_out_of_range"]),
              "0 null, 0 out of range")
    rep.check("13b", "source_row_id ascends with original file order, monotonic across chunks",
              state["row_id_monotonic"], "strictly +1 across all %d chunk boundaries" % build_info["n_chunks"],
              "strictly ascending, never reset per chunk")

    # 14-18: dates and the future flag
    rep.check(14, "posting_date parse failures", state["date_parse_failures"] == 0
              and issues["date_parse_failures"] == 0,
              "%d in staging, %d in raw" % (state["date_parse_failures"], issues["date_parse_failures"]),
              0, "Failures are reported, never coerced or dropped.")
    rep.check("14b", "posting_date written as ISO YYYY-MM-DD",
              state["date_format_violations"] == 0, "%d non-ISO value(s)" % state["date_format_violations"], 0)
    date_min, date_max = stats.minimum[DATE_COLUMN], stats.maximum[DATE_COLUMN]
    rep.check(15, "posting_date minimum", date_min == EXPECT_DATE_MIN, date_min, EXPECT_DATE_MIN)
    rep.check(16, "posting_date maximum", date_max == EXPECT_DATE_MAX, date_max, EXPECT_DATE_MAX)
    rep.check("16b", "Distinct posting_date values",
              len(stats.distinct[DATE_COLUMN]) == EXPECT_DISTINCT_DATES,
              f"{len(stats.distinct[DATE_COLUMN]):,}", f"{EXPECT_DISTINCT_DATES:,}")
    rep.check(17, "is_future_posting domain",
              state["future_domain_violations"] == 0
              and set(stats.distinct[FUTURE_FLAG_COLUMN]) <= {0, 1},
              sorted(stats.distinct[FUTURE_FLAG_COLUMN]), "{0, 1}")
    rep.check(18, "is_future_posting = 1 count", state["future_count"] == EXPECT_FUTURE_ROWS,
              f"{state['future_count']:,} ({pct(state['future_count'], n):.4f}%)",
              f"{EXPECT_FUTURE_ROWS:,}",
              "Expectation only; the cutoff %s is the sole input to the rule." % FUTURE_CUTOFF)
    rep.check("18b", "is_future_posting reproduces from the fixed cutoff on re-read",
              state["future_recomputed_mismatch"] == 0,
              "%d mismatch(es)" % state["future_recomputed_mismatch"], 0,
              "Recomputed against %s, never the system clock." % FUTURE_CUTOFF)

    # 19-22: missingness
    for ref, col in zip((19, 20, 21), MISSING_EXPECTED_COLUMNS):
        rep.check(ref, f"{col} missing count", stats.null[col] == EXPECT_MISSING[col],
                  f"{stats.null[col]:,} ({pct(stats.null[col], n):.4f}%)",
                  f"{EXPECT_MISSING[col]:,}", "Preserved as NULL; no imputation.")
    other = [c for c in SOURCE_COLUMNS if c not in MISSING_EXPECTED_COLUMNS]
    unexpected = {c: stats.null[c] for c in other if stats.null[c]}
    rep.check(22, "No unexpected source missingness introduced", not unexpected,
              "0 nulls across the other %d source columns" % len(other) if not unexpected else str(unexpected),
              "0")
    rep.check("22b", "Staging null counts equal raw null counts, column by column",
              all(stats.null[c] == raw_stats.null[c] for c in SOURCE_COLUMNS),
              "identical for all 33 source columns"
              if all(stats.null[c] == raw_stats.null[c] for c in SOURCE_COLUMNS)
              else str({c: (raw_stats.null[c], stats.null[c]) for c in SOURCE_COLUMNS
                        if raw_stats.null[c] != stats.null[c]}),
              "identical", "Proves no fill, no drop and no new null.")

    # 23: binary flags
    bin_bad = {c: v for c, v in state["binary_violations"].items() if v}
    bin_null = {c: v for c, v in state["binary_nulls"].items() if v}
    rep.check(23, "All nine binary fields strictly in {0,1}, no nulls",
              not bin_bad and not bin_null,
              "0 violations, 0 nulls" if not bin_bad and not bin_null else f"{bin_bad} / {bin_null}",
              "0 violations, 0 nulls",
              "Kept as 0/1; not converted to Yes/No and not rebalanced.")
    usf = stats.distinct["unrealistic_salary_flag"]
    rep.check("23b", "unrealistic_salary_flag retained and still constant 0",
              "unrealistic_salary_flag" in state["staging_header"] and set(usf) == {0},
              "present, values %s" % sorted(usf), "present, {0}",
              "Constant in this extract; kept because dropping it is a modelling decision.")

    # 24: score ranges
    score_bad = {c: v for c, v in state["score_out_of_range"].items() if v}
    rep.check(24, "Seven score columns satisfy 0 <= value <= 100 where non-null",
              not score_bad, "0 out of range" if not score_bad else str(score_bad), "0",
              "Checked only; no value clipped.")

    # 25-26: invariants
    rep.check(25, "payment_required == (registration_fee > 0)", state["payment_violations"] == 0,
              state["payment_violations"], 0, "Validated, not used to derive either column.")
    rep.check(26, "recruiter_email_type Corporate<->0 and Free<->1",
              state["email_violations"] == 0, state["email_violations"], 0,
              "Validated, not used to derive either column.")
    rep.check("26b", "is_fake_posting not derived from fraud_score",
              stats.digest["is_fake_posting"].hexdigest()
              == raw_stats.digest["is_fake_posting"].hexdigest(),
              "label digest identical to source", "identical",
              "The two columns remain independently preserved; the audit found "
              "disagreement at fraud_score = 50.")

    # 27: duplicates
    dup = n - state["distinct_row_hashes"]
    rep.check(27, "Exact duplicate source rows (33 source fields only)", dup == 0,
              f"{dup:,} duplicate(s), {state['distinct_row_hashes']:,} distinct rows", 0,
              "source_row_id and is_future_posting are excluded; including source_row_id "
              "would make every row unique by definition. Checked only, never de-duplicated.")

    # 28: value preservation
    val_bad = {c: v for c, v in state["value_mismatch"].items() if v}
    null_bad = {c: v for c, v in state["null_mask_mismatch"].items() if v}
    rep.check(28, "Source values preserved through the round trip (element-wise)",
              not val_bad and not null_bad,
              "0 differing values across 33,000,000 compared cells"
              if not val_bad and not null_bad else f"values {val_bad} / nulls {null_bad}",
              "0",
              "Raw and staging are re-read in lockstep and typed by identical code.")
    digest_bad = [c for c in SOURCE_COLUMNS
                  if stats.digest[c].hexdigest() != raw_stats.digest[c].hexdigest()]
    rep.check("28b", "Per-column order-sensitive value digests match raw",
              not digest_bad,
              "33 of 33 column digests identical" if not digest_bad else ", ".join(digest_bad),
              "33 of 33")

    # supporting typing and domain evidence
    rep.check("T1", "company_age / stipend contain no non-integral non-null values",
              not issues["non_integral"],
              "0" if not issues["non_integral"] else str(issues["non_integral"]), "0",
              "Basis for nullable-integer typing; NULL preserved as NULL, never zero-filled.")
    rep.check("T2", "One-decimal columns retain one-decimal precision",
              not issues["non_one_decimal"],
              "0 off-grid values in %s" % ", ".join(DECIMAL1_COLUMNS)
              if not issues["non_one_decimal"] else str(issues["non_one_decimal"]), "0",
              "Not rounded to integers.")
    rep.check("T3", "No field failed numeric parsing", not issues["non_numeric"],
              "0" if not issues["non_numeric"] else str(issues["non_numeric"]), "0")
    rep.check("T4", "Identical 35-column schema written for every chunk",
              build_info["schema_variants"] == 1,
              "%d schema variant across %d chunk(s)" % (build_info["schema_variants"], build_info["n_chunks"]),
              "1")
    rep.check("T5", "Header written exactly once",
              len(state["staging_header"]) == EXPECT_STAGING_COLUMNS
              and state["staging_header"] == STAGING_COLUMNS,
              "1 header row, 35 columns", "1 header row, 35 columns")
    neg = state["negative_values"]
    rep.check("T6", "No negative value in any numeric column", not neg,
              "0" if not neg else str(neg), "0")
    range_bad = {c: v for c, v in state["range_violations"].items() if v}
    rep.check("T7", "Numeric columns stay inside their documented observed ranges",
              not range_bad, "0 out of range" if not range_bad else str(range_bad), "0",
              "Descriptive check; no value capped, winsorized, scaled or removed.")
    rep.check("T8", "Text columns unpadded, non-empty, no whitespace-only values",
              state["text_padded"] == 0 and state["text_empty"] == 0
              and state["text_whitespace_only"] == 0,
              "padded %d, empty %d, whitespace-only %d"
              % (state["text_padded"], state["text_empty"], state["text_whitespace_only"]),
              "0 / 0 / 0",
              "Reported, not trimmed: no unconditional TRIM or LOWER is applied.")
    dist_bad = {c: (len(stats.distinct[c]), EXPECT_DISTINCT[c])
                for c in EXPECT_DISTINCT if len(stats.distinct[c]) != EXPECT_DISTINCT[c]}
    rep.check("T9", "Categorical distinct counts unchanged vs source", not dist_bad,
              "all 8 text columns match" if not dist_bad else str(dist_bad), "match",
              "No category mapped, merged, case-folded or ordinal-coded; "
              "company_size stays categorical.")
    rep.check("T10", "Raw stream fully consumed in lockstep with staging",
              state.get("raw_rows_beyond_staging", 0) == 0,
              state.get("raw_rows_beyond_staging", 0), 0)
    return rep


def write_column_profile(path: Path, stats: ColumnStats, n_rows: int) -> None:
    """Per-column staging profile, including the intended (SQL) staging datatype."""
    rows = []
    for col in STAGING_COLUMNS:
        applicable = col in MINMAX_COLUMNS or col == DATE_COLUMN
        lo = stats.minimum[col] if applicable else ""
        hi = stats.maximum[col] if applicable else ""
        rows.append(
            {
                "column_name": col,
                "staging_dtype": INTENDED_SQL_TYPE[col],
                "pandas_dtype": stats.pandas_dtype.get(col, ""),
                "non_null_count": stats.non_null[col],
                "null_count": stats.null[col],
                "null_pct": pct(stats.null[col], n_rows),
                "unique_count": len(stats.distinct[col]),
                "min": lo,
                "max": hi,
                "source_or_derived": SOURCE_OR_DERIVED[col],
                "transformation": TRANSFORMATION_NOTE[col],
                "value_digest_sha256": stats.digest[col].hexdigest(),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, lineterminator="\n")


def write_validation_report(
    path: Path,
    rep: Report,
    fp_before: dict,
    fp_after: dict,
    structure: dict,
    build_info: dict,
    result: dict,
    input_path: Path,
    output_path: Path,
    chunksize: int,
    elapsed: float,
) -> None:
    state, stats = result["state"], result["stats"]
    n = state["n_rows"]
    failures = rep.failures
    overall = "PASS" if rep.ok else "FAIL"

    lines: list[str] = []
    add = lines.append
    add("# Staging Validation Report")
    add("")
    add(f"**Overall result: {overall}** &mdash; {len(rep.rows) - len(failures)} of "
        f"{len(rep.rows)} checks passed.")
    add("")
    add("| Item | Value |")
    add("| --- | --- |")
    add(f"| Generated | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |")
    add(f"| Script | `scripts/build_staging.py` |")
    add(f"| Source | `{rel(input_path)}` |")
    add(f"| Staging output | `{rel(output_path)}` |")
    add(f"| Source sha256 | `{fp_before['sha256']}` |")
    add(f"| Rows in / rows out | {structure['n_records']:,} / {n:,} |")
    add(f"| Columns in / columns out | {structure['n_header_fields']} / "
        f"{len(state['staging_header'])} |")
    add(f"| Reference date (fixed) | **{FUTURE_CUTOFF}** |")
    add(f"| Chunk size / chunks | {chunksize:,} / {build_info['n_chunks']} |")
    add(f"| Runtime | {elapsed:.1f}s |")
    add(f"| Output size | {human_bytes(output_path.stat().st_size)} |")
    add("")
    add("Expected values come from the completed profiling and audit phase "
        "(`results/profiling/`, `results/audit/`) and from "
        "[docs/data_dictionary.md](../../docs/data_dictionary.md). They are "
        "**assertions about the output**, never inputs to the transformation "
        "logic. A failing check is reported here; the pipeline never silently "
        "repairs the data.")
    add("")
    add("---")
    add("")
    add("## 1. Check results")
    add("")
    add("| # | Check | Status | Observed | Expected |")
    add("| --- | --- | --- | --- | --- |")
    for row in rep.rows:
        add("| {ref} | {check} | **{status}** | {observed} | {expected} |".format(**row))
    add("")
    notes = [r for r in rep.rows if r["note"]]
    if notes:
        add("### Notes on individual checks")
        add("")
        for row in notes:
            add(f"- **{row['ref']} &mdash; {row['check']}:** {row['note']}")
        add("")
    add("---")
    add("")

    # -- section 2: parsing ------------------------------------------------
    add("## 2. CSV parsing integrity (fatal-on-failure)")
    add("")
    add("The raw extract contains quoted text fields with embedded commas, for "
        "example `\"Russell, Medina and Evans\"` in `company_name`. Splitting a "
        "line on `,` would read that as two fields and shift every subsequent "
        "column by one position, silently corrupting 24 downstream columns.")
    add("")
    add("**The pipeline never splits on commas.** Two independent quote-aware "
        "readers are used:")
    add("")
    add("1. A structural pre-scan with the stdlib `csv` module (RFC 4180 quote "
        "handling), which walks every physical record and counts its fields.")
    add("2. `pandas.read_csv()` for the build and for the re-read of the output.")
    add("")
    add("| Measurement | Value |")
    add("| --- | --- |")
    add(f"| Header fields | {structure['n_header_fields']} |")
    add(f"| Records scanned | {structure['n_records']:,} |")
    add(f"| Distinct record widths | {structure['field_counts']} |")
    add(f"| Records not 33 fields wide | {structure['n_bad_rows']:,} |")
    add(f"| Records with a comma inside quoted `company_name` | "
        f"{structure['quoted_comma_rows']:,} |")
    add("")
    if structure["bad_rows"]:
        add("**FATAL &mdash; malformed records (first 20):**")
        add("")
        for lineno, width in structure["bad_rows"]:
            add(f"- line {lineno:,}: {width} fields")
        add("")
    else:
        add("Every record parses to exactly 33 fields. **No field shift and no "
            "malformed parsing was found.** Any other width would be a fatal "
            "validation error and would abort the build.")
        add("")
    add("Quoted field contents are preserved exactly: the output is re-read with "
        "the same quote-aware parser and compared element-wise against the raw "
        "file (check 28), so a mis-quoted write would surface as a value "
        "mismatch in `company_name`.")
    add("")
    add("---")
    add("")

    # -- section 3: immutability -------------------------------------------
    add("## 3. Raw-data immutability")
    add("")
    add("| Item | Before | After |")
    add("| --- | --- | --- |")
    add(f"| sha256 | `{fp_before['sha256']}` | `{fp_after['sha256']}` |")
    add(f"| Size (bytes) | {fp_before['size_bytes']:,} | {fp_after['size_bytes']:,} |")
    add(f"| mtime (ns) | {fp_before['mtime_ns']} | {fp_after['mtime_ns']} |")
    add("")
    status = "unchanged" if fp_before == fp_after else "**CHANGED &mdash; INVESTIGATE**"
    add(f"Raw file: {status}. The digest also matches the value documented in "
        f"`docs/data_dictionary.md`: "
        f"`{'match' if fp_after['sha256'] == EXPECTED_RAW_SHA256 else 'MISMATCH'}`.")
    add("")
    add("The raw CSV is opened read-only. Nothing is written to `data/raw/`, no "
        "file there is rewritten, and no timestamp there is touched. "
        "`source_row_id` is added to the **staging** dataset only.")
    add("")
    add("---")
    add("")

    # -- section 4: value preservation --------------------------------------
    add("## 4. Value preservation evidence")
    add("")
    add("The staging CSV is re-read with `pandas.read_csv()` and walked in "
        "lockstep with the raw CSV, chunk for chunk. Both sides are typed by the "
        "**same function**, so any surviving difference is a real defect rather "
        "than an artefact of the comparison.")
    add("")
    add(f"- Cells compared: {n * EXPECT_SOURCE_COLUMNS:,} "
        f"({n:,} rows x {EXPECT_SOURCE_COLUMNS} source columns)")
    add(f"- Differing values: {sum(state['value_mismatch'].values()):,}")
    add(f"- Differing null masks: {sum(state['null_mask_mismatch'].values()):,}")
    add("")
    add("Additionally, an order-sensitive sha256 digest is accumulated per "
        "column on both sides (per-row 64-bit value hashes appended in file "
        "order, so the digest covers values **and** their sequence):")
    add("")
    add("| Source column | Digest (first 16 hex) | Matches raw |")
    add("| --- | --- | --- |")
    raw_stats = result["raw_stats"]
    for col in SOURCE_COLUMNS:
        s_hex = stats.digest[col].hexdigest()
        r_hex = raw_stats.digest[col].hexdigest()
        add(f"| `{col}` | `{s_hex[:16]}` | {'yes' if s_hex == r_hex else '**NO**'} |")
    add("")
    add("`posting_date` is digested from its ISO `YYYY-MM-DD` rendering on both "
        "sides. That is the one approved representation change, and it is "
        "value-preserving: the source is already written as `YYYY-MM-DD`, so no "
        "date is re-interpreted, shifted or re-formatted into a different "
        "calendar value.")
    add("")
    add("`company_age` and `stipend` are written without the trailing `.0` that "
        "pandas produced when reading them as floats. This is a **datatype "
        "representation change, not a value change**: check T1 confirms 0 "
        "non-integral non-null values across all 1,000,000 rows, and the "
        "element-wise comparison in check 28 is numeric, so `43083.0` and "
        "`43083` compare equal. NULLs stay NULL and are never replaced by zero.")
    add("")
    add("---")
    add("")

    # -- section 5: unresolved semantics ------------------------------------
    add("## 5. Unresolved semantic limitation &mdash; `stipend`")
    add("")
    add("**The source documents neither a currency nor a pay period for "
        "`stipend`.** Values range from 2,000 to 110,428 across nine locations "
        "(Bangalore, Berlin, Dubai, London, New York, San Francisco, Singapore, "
        "Sydney, Toronto), and nothing in the extract states whether a value is "
        "monthly or annual, or which currency it is denominated in.")
    add("")
    add("Consequently the staging layer:")
    add("")
    add("- preserves `stipend` numerically, exactly as supplied;")
    add("- does **not** convert currencies;")
    add("- does **not** annualise or otherwise re-base the pay period;")
    add("- does **not** normalise across locations;")
    add("- does **not** create stipend bands.")
    add("")
    add("**This limitation is unresolved and is carried forward.** Until the "
        "currency and pay period are established, `stipend` values from "
        "different locations must not be assumed directly comparable, and any "
        "cross-location aggregation of `stipend` in the analytical layer would "
        "be unsound. The same caveat is recorded in "
        "[transformation_log.md](transformation_log.md).")
    add("")
    add("---")
    add("")

    # -- section 6: relationships -------------------------------------------
    add("## 6. Known relationships &mdash; validated, never used to derive")
    add("")
    add("| Relationship | Violations | Action taken |")
    add("| --- | ---: | --- |")
    add(f"| `payment_required == (registration_fee > 0)` | {state['payment_violations']:,} | "
        "Both columns kept and preserved independently. Neither is derived from the other. |")
    add(f"| `recruiter_email_type` Corporate&harr;0, Free&harr;1 | {state['email_violations']:,} | "
        "Both columns kept and preserved independently. Neither is derived from the other. |")
    add("| `fraud_score` &rarr; `is_fake_posting` | n/a | **Not derived.** The audit found "
        "the two disagree at `fraud_score = 50`, so the label is not a function of the "
        "score. Both are preserved independently. |")
    add("")
    add("---")
    add("")

    # -- section 7: things deliberately not done ----------------------------
    add("## 7. What this run did not do")
    add("")
    add("No imputation, no row deletion, no column deletion, no de-duplication, "
        "no category mapping or merging, no ordinal coding, no case folding or "
        "trimming, no scaling or standardisation, no outlier removal, capping or "
        "winsorizing, no currency conversion, no stipend normalisation or "
        "banding, no class rebalancing, and no label derivation. The full list "
        "with reasons is in [transformation_log.md](transformation_log.md).")
    add("")
    if failures:
        add("---")
        add("")
        add("## 8. Failed checks")
        add("")
        for row in failures:
            add(f"- **{row['ref']} &mdash; {row['check']}**: observed "
                f"`{row['observed']}`, expected `{row['expected']}`.")
        add("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_transformation_log(
    path: Path, build_info: dict, result: dict, fp_before: dict, elapsed: float
) -> None:
    state, stats = result["state"], result["stats"]
    n = state["n_rows"]
    lines: list[str] = []
    add = lines.append
    add("# Transformation Log &mdash; Staging Layer")
    add("")
    add("| Item | Value |")
    add("| --- | --- |")
    add(f"| Generated | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |")
    add("| Script | `scripts/build_staging.py` |")
    add("| Input | `data/raw/fake_internship_detection_dataset.csv` |")
    add(f"| Input sha256 | `{fp_before['sha256']}` |")
    add("| Output | `data/staging/internship_postings_staging.csv` |")
    add(f"| Rows in / out | {EXPECT_ROWS:,} / {n:,} |")
    add(f"| Columns in / out | {EXPECT_SOURCE_COLUMNS} / {len(STAGING_COLUMNS)} |")
    add(f"| Runtime | {elapsed:.1f}s |")
    add("")
    add("Every rule cited below is from "
        "[docs/cleaning_rules.md](../../docs/cleaning_rules.md). **No new "
        "cleaning decision was made in this layer** and no business meaning was "
        "reinterpreted beyond the documented evidence.")
    add("")
    add("---")
    add("")
    add("## 1. Transformations performed")
    add("")
    add("Exactly three. Nothing else was changed.")
    add("")
    add("### 1.1 Parse and standardise `posting_date`")
    add("")
    add("| Item | Detail |")
    add("| --- | --- |")
    add("| Rule | R4.2.1, R4.2.2 |")
    add("| Action | Parsed with the explicit format `%Y-%m-%d` into a real date, "
        "written back as ISO `YYYY-MM-DD`. |")
    add(f"| Parse failures | {state['date_parse_failures']:,} &mdash; failures are "
        "reported, never coerced, defaulted or dropped (R4.2.3) |")
    add(f"| Resulting range | {stats.minimum[DATE_COLUMN]} to {stats.maximum[DATE_COLUMN]} |")
    add(f"| Distinct dates | {len(stats.distinct[DATE_COLUMN]):,} |")
    add("| Rows removed | 0 |")
    add("")
    add("The source already writes the column as `YYYY-MM-DD`, so this changes "
        "the **representation** (text to a typed date and back to ISO text) and "
        "not the meaning: no date is shifted, re-based or re-interpreted, and "
        "no future-dated row is removed (R4.2.4).")
    add("")
    add("### 1.2 Add `source_row_id`")
    add("")
    add("| Item | Detail |")
    add("| --- | --- |")
    add("| Rule | R4.1.1 &ndash; R4.1.4 |")
    add("| Action | Sequential integer assigned in original CSV order, before "
        "any filter, sort or transformation. |")
    add(f"| Range | {stats.minimum[ROW_ID_COLUMN]:,} to {stats.maximum[ROW_ID_COLUMN]:,}, contiguous |")
    add(f"| Distinct / nulls | {len(stats.distinct[ROW_ID_COLUMN]):,} / {stats.null[ROW_ID_COLUMN]:,} |")
    add(f"| Chunks crossed | {build_info['n_chunks']} &mdash; the counter is global "
        "and is never reset per chunk |")
    add("| Added to raw file | **No.** Staging only (R4.1.3). |")
    add("")
    add("**This is a staging lineage identifier, not a natural or business "
        "key.** Profiling found no unique single column and no unique composite "
        "among the 33 source fields, so a surrogate is the only way to address "
        "an individual row. It is meaningful only together with the source "
        "file's sha256, must not be used to join across extracts, and carries no "
        "analytic ordering significance.")
    add("")
    add("### 1.3 Add `is_future_posting`")
    add("")
    add("| Item | Detail |")
    add("| --- | --- |")
    add("| Rule | R4.2.5, R4.2.6 |")
    add(f"| Definition | `1` when `posting_date > {FUTURE_CUTOFF}`, otherwise `0` |")
    add(f"| Reference date | **{FUTURE_CUTOFF}** &mdash; a fixed documented "
        "constant, never the system clock |")
    add(f"| Rows flagged | {state['future_count']:,} ({pct(state['future_count'], n):.4f}%) |")
    add("| Rows removed | 0 &mdash; the flag marks, it does not filter |")
    add("")
    add("The cutoff is pinned so the output is reproducible: computing the flag "
        "from the current date would make the flagged-row count drift on every "
        "run and no two loads could be compared. The expected count of 30,246 "
        "appears **only** as a post-transformation assertion in "
        "[staging_validation.md](staging_validation.md); it is not an input to "
        "the rule.")
    add("")
    add("### 1.4 Datatype realisation (not a value change)")
    add("")
    add("Typing is how the values are represented, not what they mean. Recorded "
        "here for completeness:")
    add("")
    add("- `company_age` and `stipend` use pandas nullable integer (`Int64`). "
        "The audit measured **0 non-integral non-null values** in both, so no "
        "precision is lost. NULL is preserved as NULL and is **never** replaced "
        "by zero. The written CSV therefore shows `23` where the float read "
        "showed `23.0`.")
    add("- `recruiter_experience_years`, `recruiter_response_time_hours`, "
        "`trust_signal_score` and `fraud_score` keep one-decimal precision as "
        "`float64`. They are **not** rounded to integers.")
    add("- The nine binary fields stay as integer `0`/`1`.")
    add("- The eight text columns stay as text, verbatim.")
    add("- The intended SQL datatype for each column is recorded in "
        "[staging_column_profile.csv](staging_column_profile.csv), because a CSV "
        "carries no datatype metadata.")
    add("")
    add("---")
    add("")
    add("## 2. Transformations deliberately NOT performed")
    add("")
    add("Each was considered and rejected on documented evidence. This section "
        "exists so a later reader can tell *decided against* from *overlooked*.")
    add("")
    add("| Not performed | Why |")
    add("| --- | --- |")
    add("| **No imputation** | The 10,000 nulls each in `company_age`, `stipend` "
        "and `trust_signal_score` are preserved. No mean, median, mode, zero, "
        "forward/backward fill or model-based fill. Imputing would manufacture "
        "values the source does not contain and would distort every downstream "
        "aggregate. |")
    add("| **No row deletion** | All 1,000,000 rows retained. No row dropped for "
        "missingness, for being future-dated, or for being an outlier. |")
    add("| **No column deletion** | All 33 source columns retained, including "
        "`unrealistic_salary_flag` (constant `0` in this extract) and both sides "
        "of the two redundant pairs. Dropping a column is a dimensional-modelling "
        "decision, deliberately deferred. |")
    add("| **No de-duplication** | 0 exact duplicates were found and the fact was "
        "re-validated after staging, over the **33 original source fields only**. "
        "`source_row_id` and `is_future_posting` are excluded from that check "
        "because `source_row_id` would make every row unique by definition. |")
    add("| **No category mapping or merging** | `internship_title`, "
        "`employment_type`, `work_mode`, `industry`, `location`, `company_name`, "
        "`company_size` and `recruiter_email_type` are preserved verbatim. |")
    add("| **No ordinal coding of `company_size`** | It stays categorical. The "
        "domain mixes a maturity label (`Startup`) with scale labels (`Small`, "
        "`Medium`, `Enterprise`), so `Startup` is not demonstrably part of a size "
        "scale and no ordinal rank can be justified from the evidence. |")
    add("| **No case folding, trimming or whitespace normalisation** | Measured "
        "0 padded values, 0 empty strings, 0 whitespace-only values, 0 "
        "case-variant duplicates. There is no defect to fix, and an "
        "unconditional `TRIM`/`LOWER` would hide a change in source behaviour "
        "instead of surfacing it. Text quality is re-checked and **reported**, "
        "not repaired. |")
    add("| **No scaling or standardisation** | No min-max, z-score, log or any "
        "other rescaling. Staging preserves source units. |")
    add("| **No outlier removal, capping or winsorizing** | IQR findings are "
        "diagnostic only. No value was removed, clipped or replaced. |")
    add("| **No currency conversion** | The source documents no currency for "
        "`stipend` or `registration_fee`. |")
    add("| **No stipend normalisation or banding** | No annualisation, no "
        "re-basing across locations, no bands. See the limitation below. |")
    add("| **No label derivation** | `is_fake_posting` is **not** derived from "
        "`fraud_score`. The audit found the two disagree at `fraud_score = 50`, "
        "so the label is not a function of the score. Both are preserved "
        "independently. |")
    add("| **No derivation from the validated invariants** | "
        "`payment_required` is not recomputed from `registration_fee`, and "
        "`suspicious_email_domain` is not recomputed from `recruiter_email_type`. "
        "The relationships are **validated only**. |")
    add("| **No class rebalancing** | The `is_fake_posting` distribution is "
        "untouched. |")
    add("| **No encoding** | No one-hot, ordinal, target or hash encoding. That "
        "belongs to modelling, not staging. |")
    add("| **No enrichment** | No geographic, industry or company enrichment; no "
        "fuzzy matching or entity resolution on `company_name`. The recurring "
        "`<Surname> <Suffix>` pattern means name similarity must not be treated "
        "as company identity. |")
    add("| **No change to the raw file** | `data/raw/` is read-only. Nothing was "
        "written, rewritten or re-timestamped there, and `source_row_id` was not "
        "added to it. |")
    add("")
    add("---")
    add("")
    add("## 3. Carried-forward limitation &mdash; `stipend` semantics")
    add("")
    add("The source does not document a **currency** or a **pay period** for "
        "`stipend`. Values span 2,000 to 110,428 across nine locations in "
        "different currency zones, and nothing in the extract indicates whether "
        "a figure is monthly or annual.")
    add("")
    add("This is **unresolved**, not settled. Staging therefore preserves the "
        "numbers as supplied and performs no conversion, annualisation, "
        "cross-location normalisation or banding. Until the currency and pay "
        "period are established from the source system, `stipend` values from "
        "different locations **must not be assumed directly comparable**, and "
        "cross-location aggregation of `stipend` would be unsound.")
    add("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the staging layer (read-only on data/raw/).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--chunksize", type=int, default=100_000,
                        help="rows per chunk (default 100,000)")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    started = time.time()

    input_path = args.input.resolve()
    output_path = args.output.resolve()
    report_dir = args.report_dir.resolve()

    if not input_path.is_file():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 2
    if "raw" in output_path.parts[len(PROJECT_ROOT.parts):]:
        print("ERROR: refusing to write inside data/raw/", file=sys.stderr)
        return 2

    report_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(SEP)
    print("STAGING BUILD - internship-scam-dw")
    print(SEP)
    print(f"Input      : {input_path}")
    print(f"Output     : {output_path}")
    print(f"Reports    : {report_dir}")
    print(f"Chunk size : {args.chunksize:,}")
    print(f"Cutoff     : {FUTURE_CUTOFF} (fixed constant, not the system clock)")
    print()

    print("[0/4] fingerprinting raw file ...")
    fp_before = file_fingerprint(input_path)
    print(f"      sha256 {fp_before['sha256']}")
    if fp_before["sha256"] != EXPECTED_RAW_SHA256:
        print("FATAL: raw sha256 does not match the documented digest.", file=sys.stderr)
        print(f"       expected {EXPECTED_RAW_SHA256}", file=sys.stderr)
        print(f"       observed {fp_before['sha256']}", file=sys.stderr)
        return 2

    print("[1/4] structural scan (quote-aware, field count per record) ...")
    structure = scan_structure(input_path)
    if structure["header"] != SOURCE_COLUMNS:
        print("FATAL: raw header does not match the documented 33 source columns.", file=sys.stderr)
        print(f"       observed {structure['header']}", file=sys.stderr)
        return 2
    if not structure["all_rows_33"]:
        print("FATAL: malformed CSV parsing / field shift detected.", file=sys.stderr)
        print(f"       record widths observed: {structure['field_counts']}", file=sys.stderr)
        for lineno, width in structure["bad_rows"]:
            print(f"       line {lineno:,}: {width} fields", file=sys.stderr)
        return 2
    print(f"      {structure['n_records']:,} records, all exactly 33 fields "
          f"({structure['quoted_comma_rows']:,} with a quoted embedded comma)")

    print("[2/4] building staging output ...")
    build_info = build_staging(input_path, output_path, args.chunksize)
    print(f"      {build_info['n_rows']:,} rows written in {build_info['n_chunks']} chunk(s)")

    print("[3/4] re-reading output and validating against raw ...")
    result = validate_staging(input_path, output_path, args.chunksize)

    fp_after = file_fingerprint(input_path)
    if fp_after != fp_before:
        print("FATAL: the raw file changed during the run.", file=sys.stderr)
        print(f"       before {fp_before}", file=sys.stderr)
        print(f"       after  {fp_after}", file=sys.stderr)

    # Realised pandas dtypes, recorded alongside the intended SQL types.
    sample = pd.read_csv(output_path, nrows=5, dtype=str, keep_default_na=False, na_values=[""])
    typed_sample, _ = apply_staging_types(sample[SOURCE_COLUMNS])
    realised = {c: str(typed_sample[c].dtype) for c in SOURCE_COLUMNS}
    realised[ROW_ID_COLUMN] = "int64"
    realised[FUTURE_FLAG_COLUMN] = "int64"
    result["stats"].pandas_dtype.update(realised)

    print("[4/4] writing reports ...")
    rep = build_checks(fp_before, fp_after, structure, build_info, result)
    elapsed = time.time() - started

    write_column_profile(report_dir / "staging_column_profile.csv", result["stats"],
                         result["state"]["n_rows"])
    write_validation_report(report_dir / "staging_validation.md", rep, fp_before, fp_after,
                            structure, build_info, result, input_path, output_path,
                            args.chunksize, elapsed)
    write_transformation_log(report_dir / "transformation_log.md", build_info, result,
                             fp_before, elapsed)

    # ----------------------------------------------------------------------
    # terminal summary
    # ----------------------------------------------------------------------
    state, stats = result["state"], result["stats"]
    n = state["n_rows"]
    print()
    print(SEP)
    print("STAGING SUMMARY")
    print(SEP)
    print(f"Input shape       : {structure['n_records']:,} rows x "
          f"{structure['n_header_fields']} columns")
    print(f"Output shape      : {n:,} rows x {len(state['staging_header'])} columns "
          f"(33 source + source_row_id + is_future_posting)")
    print(f"source_row_id     : min {stats.minimum[ROW_ID_COLUMN]:,} | "
          f"max {stats.maximum[ROW_ID_COLUMN]:,} | "
          f"distinct {len(stats.distinct[ROW_ID_COLUMN]):,} | "
          f"nulls {stats.null[ROW_ID_COLUMN]:,} | "
          f"contiguous {'YES' if state['row_id_coverage'] == EXPECT_ROWS else 'NO'} | "
          f"file order {'YES' if state['row_id_monotonic'] else 'NO'}")
    print(f"posting_date      : {stats.minimum[DATE_COLUMN]} to {stats.maximum[DATE_COLUMN]} | "
          f"{len(stats.distinct[DATE_COLUMN]):,} distinct | "
          f"parse failures {state['date_parse_failures']:,}")
    print(f"Future count      : {state['future_count']:,} "
          f"({pct(state['future_count'], n):.4f}%) vs expected {EXPECT_FUTURE_ROWS:,} "
          f"[cutoff {FUTURE_CUTOFF}]")
    print("Missing counts    : " + " | ".join(
        f"{c} {stats.null[c]:,}" for c in MISSING_EXPECTED_COLUMNS))
    other_null = sum(stats.null[c] for c in SOURCE_COLUMNS if c not in MISSING_EXPECTED_COLUMNS)
    print(f"                    other 30 source columns: {other_null:,} null(s)")
    print(f"Invariants        : payment/registration {state['payment_violations']:,} | "
          f"email/domain {state['email_violations']:,} | "
          f"binary domain {sum(state['binary_violations'].values()):,} | "
          f"score range {sum(state['score_out_of_range'].values()):,} | "
          f"duplicates {n - state['distinct_row_hashes']:,}")
    print(f"Value preservation: {sum(state['value_mismatch'].values()):,} differing value(s), "
          f"{sum(state['null_mask_mismatch'].values()):,} differing null(s) across "
          f"{n * EXPECT_SOURCE_COLUMNS:,} compared cells")
    print(f"Raw sha256 before : {fp_before['sha256']}")
    print(f"Raw sha256 after  : {fp_after['sha256']}")
    print(f"Raw file unchanged: {'YES' if fp_before == fp_after else 'NO - INVESTIGATE'}")
    print()
    print("Files written:")
    for path in [output_path,
                 report_dir / "staging_validation.md",
                 report_dir / "staging_column_profile.csv",
                 report_dir / "transformation_log.md"]:
        print(f"  {rel(path):<52} {human_bytes(path.stat().st_size):>12}")
    print()
    print(f"Checks            : {len(rep.rows) - len(rep.failures)} passed, "
          f"{len(rep.failures)} failed")
    for row in rep.failures:
        print(f"  FAIL {row['ref']:>4}  {row['check']}")
        print(f"            observed {row['observed']} | expected {row['expected']}")
    print(f"Runtime           : {elapsed:.1f}s")
    print(SEP)
    print(f"OVERALL: {'PASS' if rep.ok and fp_before == fp_after else 'FAIL'}")
    print(SEP)
    print("Staging only. Three approved transformations applied; nothing imputed,")
    print("deleted, de-duplicated, mapped, scaled, capped, converted or derived.")
    print(SEP)

    return 0 if (rep.ok and fp_before == fp_after) else 1


if __name__ == "__main__":
    raise SystemExit(main())
