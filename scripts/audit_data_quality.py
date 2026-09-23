#!/usr/bin/env python3
"""
Data quality / semantic audit for the fake-internship-detection dataset.

AUDIT ONLY.  This script is strictly read-only with respect to the raw data:
it opens data/raw/fake_internship_detection_dataset.csv for reading, never
writes to data/raw/, and performs NO cleaning, imputation, capping, dropping,
normalisation, encoding or de-duplication.  Date parsing happens on a
temporary in-memory copy of the column; the loaded DataFrame is never mutated.
Every number produced here is an observation, not a decision.  Cleaning
decisions are deliberately left to a human and to the later staging layer.

Outputs (results/audit/):
    audit_summary.md
    date_bounds.csv
    future_dates.csv
    future_dates_by_month.csv
    missing_value_relationship.csv
    missing_overlap.csv
    missing_combination_counts.csv
    binary_flags.csv
    binary_flag_value_counts.csv
    payment_consistency.csv
    email_crosstab.csv
    fraud_score_relationship.csv
    fraud_score_class_stats.csv
    fraud_score_threshold_scan.csv
    trust_signal_relationship.csv
    trust_signal_correlations.csv
    company_domain_age.csv
    score_range_validation.csv
    numeric_sanity.csv
    key_candidates.csv
    provenance_indicators.csv

Usage:
    python scripts/audit_data_quality.py
    python scripts/audit_data_quality.py --input <csv> --output-dir <dir>
    python scripts/audit_data_quality.py --future-cutoff 2026-09-23
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "fake_internship_detection_dataset.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "audit"

DATE_COLUMN = "posting_date"
DATE_FORMAT = "%Y-%m-%d"
LABEL = "is_fake_posting"

# Audit reference dates.  EARLY_CUTOFF is the lower plausibility bound stated in
# the audit brief; FUTURE_CUTOFF is "today" for this run.  Both are reporting
# boundaries only - no row is removed because it falls outside them.
DEFAULT_EARLY_CUTOFF = "2018-01-01"
DEFAULT_FUTURE_CUTOFF = "2026-09-23"

MISSING_AUDIT_COLUMNS = ["company_age", "stipend", "trust_signal_score"]

BINARY_FLAG_COLUMNS = [
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

NUMERIC_SANITY_COLUMNS = [
    "company_age",
    "stipend",
    "registration_fee",
    "job_description_length",
    "grammatical_errors",
    "recruiter_experience_years",
    "recruiter_response_time_hours",
]

TRUST_INDICATORS = [
    "verification_status",
    "linkedin_presence",
    "website_available",
    "social_media_presence",
]

FRAUD_BIN_EDGES = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# A deterministic-derivation claim is only made when the within-group spread of
# the derived column is below this tolerance for every observed group.
DETERMINISM_TOLERANCE = 1e-9

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
    return round(100.0 * part / whole, 6)


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


def i(x) -> str:
    """Integer with thousands separators, NA-safe."""
    if x is None:
        return "n/a"
    if isinstance(x, float) and np.isnan(x):
        return "n/a"
    return f"{int(x):,}"


def f(x, d: int = 4) -> str:
    """Float with thousands separators, NA-safe."""
    if x is None:
        return "n/a"
    try:
        value = float(x)
    except (TypeError, ValueError):
        return str(x)
    if np.isnan(value):
        return "n/a"
    return f"{value:,.{d}f}"


def smart(x) -> str:
    """Format a mixed-type metric value: booleans as yes/no, whole numbers as ints."""
    if isinstance(x, (bool, np.bool_)):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    if isinstance(x, (float, np.floating)):
        if np.isnan(x):
            return "n/a"
        if float(x).is_integer():
            return f"{int(x):,}"
        return f"{float(x):,.4f}"
    return str(x)


def is_text_column(series: pd.Series) -> bool:
    """
    True for object- and string-dtype columns.  pandas 3 infers plain text as the
    `str` dtype rather than `object`, so an `== object` test misses every text
    column; both are checked here.
    """
    dtype = series.dtype
    if pd.api.types.is_numeric_dtype(dtype) or pd.api.types.is_bool_dtype(dtype):
        return False
    return pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype)


def md_table(headers, rows, aligns=None) -> list[str]:
    """Build a GitHub-flavoured markdown table as a list of lines."""
    if aligns is None:
        aligns = ["---"] * len(headers)
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(aligns) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return out


def describe_numeric(series: pd.Series) -> dict:
    """Positional statistics for a numeric series; NaNs are excluded, not filled."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    keys = ("count", "mean", "std", "min", "p01", "p05", "p25", "median",
            "p75", "p95", "p99", "max")
    if s.empty:
        return {k: float("nan") for k in keys}
    return {
        "count": int(s.size),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=1)) if s.size > 1 else float("nan"),
        "min": float(s.min()),
        "p01": float(s.quantile(0.01)),
        "p05": float(s.quantile(0.05)),
        "p25": float(s.quantile(0.25)),
        "median": float(s.median()),
        "p75": float(s.quantile(0.75)),
        "p95": float(s.quantile(0.95)),
        "p99": float(s.quantile(0.99)),
        "max": float(s.max()),
    }


def label_split(df: pd.DataFrame, mask) -> dict:
    """Distribution of the fraud label inside a boolean row mask."""
    mask = np.asarray(mask, dtype=bool)
    total = int(mask.sum())
    if LABEL not in df.columns:
        return {"rows": total, "label_0": np.nan, "label_1": np.nan,
                "label_1_rate_pct": np.nan}
    sub = df[LABEL].to_numpy()[mask]
    ones = int((sub == 1).sum())
    zeros = int((sub == 0).sum())
    return {
        "rows": total,
        "label_0": zeros,
        "label_1": ones,
        "label_1_rate_pct": pct(ones, total),
    }


def cramers_v(table: np.ndarray):
    """Chi-square statistic and Cramer's V for a contingency table (no scipy)."""
    observed = np.asarray(table, dtype=float)
    n = observed.sum()
    if n == 0:
        return float("nan"), float("nan")
    row_sums = observed.sum(axis=1, keepdims=True)
    col_sums = observed.sum(axis=0, keepdims=True)
    expected = row_sums @ col_sums / n
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(expected > 0, (observed - expected) ** 2 / expected, 0.0)
    chi2 = float(terms.sum())
    k = min(observed.shape) - 1
    v = float(np.sqrt(chi2 / (n * k))) if k > 0 else float("nan")
    return chi2, v


def functional_dependency(df: pd.DataFrame, left: str, right: str) -> dict:
    """
    Test whether `left` functionally determines `right`: for every value of
    `left`, does `right` take exactly one value?  Violating rows are the rows
    that disagree with the most frequent (modal) mapping for their key.
    """
    pair_counts = df.groupby([left, right], dropna=False).size()
    distinct_per_value = pair_counts.groupby(level=0).size()
    modal = pair_counts.groupby(level=0).max()
    totals = pair_counts.groupby(level=0).sum()
    violations = int((totals - modal).sum())
    return {
        "determinant": left,
        "dependent": right,
        "distinct_determinant_values": int(distinct_per_value.size),
        "max_distinct_dependent_per_value": int(distinct_per_value.max()),
        "is_exact_function": bool((distinct_per_value <= 1).all()),
        "violating_rows": violations,
        "violating_rows_pct": pct(violations, len(df)),
    }


def iqr_fences(series: pd.Series):
    """Conventional 1.5x IQR fences; a screening device, not a verdict."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return (float("nan"),) * 5 + (0, 0)
    q1 = float(s.quantile(0.25))
    q3 = float(s.quantile(0.75))
    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    return q1, q3, iqr, low, high, int((s < low).sum()), int((s > high).sum())


# --------------------------------------------------------------------------
# 1. posting date audit
# --------------------------------------------------------------------------
def audit_posting_dates(df: pd.DataFrame, early_cutoff, future_cutoff) -> dict:
    """
    Parse posting_date on a TEMPORARY copy and report boundaries and future
    rows.  Nothing is deleted and df[DATE_COLUMN] keeps its original dtype.
    """
    raw = df[DATE_COLUMN]
    parsed = pd.to_datetime(raw, format=DATE_FORMAT, errors="coerce")
    strict_unparsed = int(parsed.isna().sum()) - int(raw.isna().sum())
    if strict_unparsed > 0:
        # Fall back to a permissive parse purely to measure how many values are
        # merely in a different format rather than genuinely unparseable.
        lenient = pd.to_datetime(raw, errors="coerce")
        lenient_unparsed = int(lenient.isna().sum()) - int(raw.isna().sum())
    else:
        lenient_unparsed = 0

    n_rows = len(df)
    valid = parsed.notna()
    before = parsed < early_cutoff
    after = parsed > future_cutoff
    future_mask = after & valid

    n_before = int((before & valid).sum())
    n_after = int(future_mask.sum())
    distinct_future = int(parsed[future_mask].nunique())
    span_days = (parsed.max() - parsed.min()).days if valid.any() else np.nan

    bounds = pd.DataFrame([
        {"metric": "rows_total", "value": n_rows},
        {"metric": "rows_null_raw", "value": int(raw.isna().sum())},
        {"metric": "rows_unparsed_strict_format", "value": strict_unparsed},
        {"metric": "rows_unparsed_any_format", "value": lenient_unparsed},
        {"metric": "min_date", "value": str(parsed.min().date()) if valid.any() else "n/a"},
        {"metric": "max_date", "value": str(parsed.max().date()) if valid.any() else "n/a"},
        {"metric": "span_days", "value": span_days},
        {"metric": "distinct_dates", "value": int(parsed.nunique())},
        {"metric": "early_cutoff", "value": str(early_cutoff.date())},
        {"metric": "rows_before_early_cutoff", "value": n_before},
        {"metric": "rows_before_early_cutoff_pct", "value": pct(n_before, n_rows)},
        {"metric": "future_cutoff", "value": str(future_cutoff.date())},
        {"metric": "rows_after_future_cutoff", "value": n_after},
        {"metric": "rows_after_future_cutoff_pct", "value": pct(n_after, n_rows)},
        {"metric": "distinct_future_dates", "value": distinct_future},
    ])

    # Per-date detail for the future block, split by the fraud label.
    if n_after:
        future_dates = parsed[future_mask]
        detail = pd.DataFrame({
            "posting_date": future_dates.dt.strftime("%Y-%m-%d").to_numpy(),
            "year": future_dates.dt.year.to_numpy(),
            "month": future_dates.dt.month.to_numpy(),
            LABEL: df.loc[future_mask, LABEL].to_numpy() if LABEL in df.columns else 0,
        })
        per_date = (
            detail.groupby(["posting_date", "year", "month"], as_index=False)
            .agg(row_count=(LABEL, "size"),
                 label_1_count=(LABEL, "sum"))
        )
        per_date["label_0_count"] = per_date["row_count"] - per_date["label_1_count"]
        per_date["label_1_rate_pct"] = [
            pct(a, b) for a, b in zip(per_date["label_1_count"], per_date["row_count"])
        ]
        per_date = per_date.sort_values("posting_date").reset_index(drop=True)

        per_month = (
            detail.groupby(["year", "month"], as_index=False)
            .agg(row_count=(LABEL, "size"),
                 label_1_count=(LABEL, "sum"),
                 distinct_dates=("posting_date", "nunique"))
        )
        per_month["label_0_count"] = per_month["row_count"] - per_month["label_1_count"]
        per_month["pct_of_all_rows"] = [
            pct(c, n_rows) for c in per_month["row_count"]
        ]
        per_month["pct_of_future_rows"] = [
            pct(c, n_after) for c in per_month["row_count"]
        ]
        per_month = per_month.sort_values(["year", "month"]).reset_index(drop=True)

        future_label = (
            detail.groupby(LABEL, as_index=False)
            .agg(row_count=("posting_date", "size"))
        )
        future_label["pct_of_future_rows"] = [
            pct(c, n_after) for c in future_label["row_count"]
        ]
    else:
        per_date = pd.DataFrame(columns=["posting_date", "year", "month", "row_count",
                                         "label_1_count", "label_0_count",
                                         "label_1_rate_pct"])
        per_month = pd.DataFrame(columns=["year", "month", "row_count", "label_1_count",
                                          "distinct_dates", "label_0_count",
                                          "pct_of_all_rows", "pct_of_future_rows"])
        future_label = pd.DataFrame(columns=[LABEL, "row_count", "pct_of_future_rows"])

    # Baseline label rate, so the future block can be compared to the dataset.
    baseline_rate = pct(int((df[LABEL] == 1).sum()), n_rows) if LABEL in df.columns else np.nan

    return {
        "parsed": parsed,
        "bounds": bounds,
        "per_date": per_date,
        "per_month": per_month,
        "future_label": future_label,
        "facts": {
            "min_date": str(parsed.min().date()) if valid.any() else "n/a",
            "max_date": str(parsed.max().date()) if valid.any() else "n/a",
            "span_days": span_days,
            "distinct_dates": int(parsed.nunique()),
            "rows_before": n_before,
            "rows_after": n_after,
            "rows_after_pct": pct(n_after, n_rows),
            "distinct_future_dates": distinct_future,
            "strict_unparsed": strict_unparsed,
            "lenient_unparsed": lenient_unparsed,
            "baseline_label_rate": baseline_rate,
        },
    }


# --------------------------------------------------------------------------
# 2. missing-value relationship audit
# --------------------------------------------------------------------------
def audit_missing(df: pd.DataFrame) -> dict:
    """Missingness of the three incomplete columns and how it co-occurs."""
    n_rows = len(df)
    cols = [c for c in MISSING_AUDIT_COLUMNS if c in df.columns]
    masks = {c: df[c].isna().to_numpy() for c in cols}

    rel_rows = []
    for c in cols:
        m = masks[c]
        miss = label_split(df, m)
        present = label_split(df, ~m)
        rel_rows.append({
            "column": c,
            "missing_count": int(m.sum()),
            "missing_pct": pct(int(m.sum()), n_rows),
            "non_missing_count": int((~m).sum()),
            "missing_label_0": miss["label_0"],
            "missing_label_1": miss["label_1"],
            "missing_label_1_rate_pct": miss["label_1_rate_pct"],
            "non_missing_label_0": present["label_0"],
            "non_missing_label_1": present["label_1"],
            "non_missing_label_1_rate_pct": present["label_1_rate_pct"],
            "label_1_rate_difference_pp": round(
                miss["label_1_rate_pct"] - present["label_1_rate_pct"], 6),
        })
    relationship = pd.DataFrame(rel_rows)

    # Pairwise overlap: observed co-missing rows vs what independence predicts.
    overlap_rows = []
    for a in cols:
        for b in cols:
            ma, mb = masks[a], masks[b]
            both = int((ma & mb).sum())
            either = int((ma | mb).sum())
            expected = (ma.sum() * mb.sum()) / n_rows if n_rows else 0.0
            overlap_rows.append({
                "column_a": a,
                "column_b": b,
                "missing_a": int(ma.sum()),
                "missing_b": int(mb.sum()),
                "missing_both": both,
                "missing_either": either,
                "jaccard": round(both / either, 6) if either else 0.0,
                "expected_both_if_independent": round(expected, 4),
                "observed_minus_expected": round(both - expected, 4),
                "masks_identical": bool(np.array_equal(ma, mb)),
            })
    overlap = pd.DataFrame(overlap_rows)

    # Full missingness pattern: every observed combination of the three flags.
    pattern = pd.DataFrame({c: masks[c] for c in cols})
    combo = (
        pattern.groupby(cols, as_index=False)
        .size()
        .rename(columns={"size": "row_count"})
    )
    combo["n_missing_columns"] = combo[cols].sum(axis=1)
    combo["pct_of_rows"] = [pct(c, n_rows) for c in combo["row_count"]]
    independent = np.ones(len(combo))
    for c in cols:
        p = masks[c].sum() / n_rows if n_rows else 0.0
        independent = independent * np.where(combo[c].to_numpy(), p, 1 - p)
    combo["expected_rows_if_independent"] = np.round(independent * n_rows, 4)
    combo = combo.sort_values("n_missing_columns").reset_index(drop=True)

    any_missing = np.zeros(n_rows, dtype=bool)
    for c in cols:
        any_missing |= masks[c]
    all_missing = np.ones(n_rows, dtype=bool)
    for c in cols:
        all_missing &= masks[c]

    return {
        "relationship": relationship,
        "overlap": overlap,
        "combinations": combo,
        "facts": {
            "columns": cols,
            "rows_any_missing": int(any_missing.sum()),
            "rows_all_missing": int(all_missing.sum()),
            "rows_all_missing_expected": round(
                np.prod([masks[c].sum() / n_rows for c in cols]) * n_rows, 4) if cols else 0.0,
            "any_masks_identical": bool(
                any(np.array_equal(masks[a], masks[b])
                    for k, a in enumerate(cols) for b in cols[k + 1:])),
            "max_pairwise_jaccard": float(
                overlap[overlap["column_a"] != overlap["column_b"]]["jaccard"].max())
            if len(cols) > 1 else float("nan"),
        },
    }


# --------------------------------------------------------------------------
# 3. binary flag validation
# --------------------------------------------------------------------------
def audit_binary_flags(df: pd.DataFrame) -> dict:
    """Confirm the nine indicator columns really are 0/1 and not constant."""
    n_rows = len(df)
    summary_rows = []
    long_rows = []
    for c in BINARY_FLAG_COLUMNS:
        if c not in df.columns:
            continue
        s = df[c]
        vc = s.value_counts(dropna=False).sort_index()
        distinct = [v for v in vc.index]
        non_null_distinct = {v for v in distinct if not pd.isna(v)}
        strictly_binary = non_null_distinct.issubset({0, 1}) and int(s.isna().sum()) == 0
        count_0 = int((s == 0).sum())
        count_1 = int((s == 1).sum())
        other = n_rows - count_0 - count_1
        for value, count in vc.items():
            long_rows.append({
                "column": c,
                "value": "NaN" if pd.isna(value) else value,
                "count": int(count),
                "pct": pct(int(count), n_rows),
            })
        summary_rows.append({
            "column": c,
            "dtype": str(s.dtype),
            "n_distinct_incl_null": int(len(distinct)),
            "distinct_values": ", ".join(
                "NaN" if pd.isna(v) else str(v) for v in distinct),
            "count_0": count_0,
            "count_1": count_1,
            "count_other_or_null": int(other),
            "null_count": int(s.isna().sum()),
            "pct_1": pct(count_1, n_rows),
            "strictly_binary_0_1": bool(strictly_binary),
            "is_constant": bool(len(non_null_distinct) <= 1),
        })
    summary = pd.DataFrame(summary_rows)
    long = pd.DataFrame(long_rows)
    constant_cols = summary[summary["is_constant"]]["column"].tolist()
    non_binary = summary[~summary["strictly_binary_0_1"]]["column"].tolist()
    return {
        "summary": summary,
        "value_counts": long,
        "facts": {
            "constant_columns": constant_cols,
            "non_binary_columns": non_binary,
            "checked": summary["column"].tolist(),
        },
    }


# --------------------------------------------------------------------------
# 4. payment consistency audit
# --------------------------------------------------------------------------
def audit_payment(df: pd.DataFrame) -> dict:
    """Cross-check the payment_required flag against the registration_fee amount."""
    n_rows = len(df)
    flag = df["payment_required"]
    fee = df["registration_fee"]

    contradiction_a = int(((flag == 0) & (fee > 0)).sum())
    contradiction_b = int(((flag == 1) & (fee == 0)).sum())
    fee_negative = int((fee < 0).sum())
    fee_null = int(fee.isna().sum())

    rows = [
        {"check": "payment_required = 0 AND registration_fee > 0",
         "row_count": contradiction_a, "pct_of_rows": pct(contradiction_a, n_rows)},
        {"check": "payment_required = 1 AND registration_fee = 0",
         "row_count": contradiction_b, "pct_of_rows": pct(contradiction_b, n_rows)},
        {"check": "payment_required = 0 AND registration_fee = 0 (consistent)",
         "row_count": int(((flag == 0) & (fee == 0)).sum()),
         "pct_of_rows": pct(int(((flag == 0) & (fee == 0)).sum()), n_rows)},
        {"check": "payment_required = 1 AND registration_fee > 0 (consistent)",
         "row_count": int(((flag == 1) & (fee > 0)).sum()),
         "pct_of_rows": pct(int(((flag == 1) & (fee > 0)).sum()), n_rows)},
        {"check": "registration_fee < 0", "row_count": fee_negative,
         "pct_of_rows": pct(fee_negative, n_rows)},
        {"check": "registration_fee is null", "row_count": fee_null,
         "pct_of_rows": pct(fee_null, n_rows)},
    ]
    checks = pd.DataFrame(rows)

    stat_rows = []
    for value in sorted(flag.dropna().unique()):
        sub = fee[flag == value]
        d = describe_numeric(sub)
        d.update({
            "payment_required": value,
            "rows": int(sub.size),
            "zeros": int((sub == 0).sum()),
            "positives": int((sub > 0).sum()),
            "negatives": int((sub < 0).sum()),
            "nulls": int(sub.isna().sum()),
        })
        stat_rows.append(d)
    stats = pd.DataFrame(stat_rows)
    ordered = ["payment_required", "rows", "zeros", "positives", "negatives", "nulls",
               "count", "mean", "std", "min", "p01", "p05", "p25", "median",
               "p75", "p95", "p99", "max"]
    stats = stats[[c for c in ordered if c in stats.columns]]

    combined = pd.concat(
        [checks.assign(section="consistency_check"),
         stats.assign(section="registration_fee_by_payment_required")],
        ignore_index=True,
    )

    return {
        "checks": checks,
        "stats": stats,
        "combined": combined,
        "facts": {
            "flag0_fee_positive": contradiction_a,
            "flag1_fee_zero": contradiction_b,
            "fee_negative": fee_negative,
            "perfectly_consistent": contradiction_a == 0 and contradiction_b == 0,
        },
    }


# --------------------------------------------------------------------------
# 5. email consistency audit
# --------------------------------------------------------------------------
def audit_email(df: pd.DataFrame) -> dict:
    """Crosstab recruiter_email_type against suspicious_email_domain."""
    n_rows = len(df)
    left, right = "recruiter_email_type", "suspicious_email_domain"
    ct = pd.crosstab(df[left], df[right], dropna=False)
    chi2, v = cramers_v(ct.to_numpy())

    tidy_rows = []
    col_totals = ct.sum(axis=0)
    row_totals = ct.sum(axis=1)
    for r in ct.index:
        for c in ct.columns:
            count = int(ct.loc[r, c])
            tidy_rows.append({
                "recruiter_email_type": r,
                "suspicious_email_domain": c,
                "count": count,
                "pct_of_all_rows": pct(count, n_rows),
                "pct_within_email_type": pct(count, int(row_totals[r])),
                "pct_within_suspicious_flag": pct(count, int(col_totals[c])),
            })
    tidy = pd.DataFrame(tidy_rows)

    fd_forward = functional_dependency(df, left, right)
    fd_reverse = functional_dependency(df, right, left)

    # Cells that are non-zero but fall outside the modal mapping are exactly the
    # rows that break a claim of a deterministic mapping.
    off_diagonal = int(fd_forward["violating_rows"])

    return {
        "crosstab": ct,
        "tidy": tidy,
        "dependencies": pd.DataFrame([fd_forward, fd_reverse]),
        "facts": {
            "chi2": chi2,
            "cramers_v": v,
            "forward_exact": fd_forward["is_exact_function"],
            "reverse_exact": fd_reverse["is_exact_function"],
            "forward_violations": fd_forward["violating_rows"],
            "reverse_violations": fd_reverse["violating_rows"],
            "off_diagonal_rows": off_diagonal,
            "n_email_types": int(ct.shape[0]),
            "n_flag_values": int(ct.shape[1]),
        },
    }


# --------------------------------------------------------------------------
# 6. fraud label relationship audit
# --------------------------------------------------------------------------
def audit_fraud(df: pd.DataFrame) -> dict:
    """fraud_score against is_fake_posting, including an exhaustive threshold scan."""
    n_rows = len(df)
    score = pd.to_numeric(df["fraud_score"], errors="coerce")
    label = df[LABEL]
    usable = score.notna() & label.notna()

    class_rows = []
    for value in sorted(label.dropna().unique()):
        sub = score[(label == value) & usable]
        d = describe_numeric(sub)
        d.update({LABEL: value, "rows": int(sub.size),
                  "pct_of_rows": pct(int(sub.size), n_rows)})
        class_rows.append(d)
    class_stats = pd.DataFrame(class_rows)
    ordered = [LABEL, "rows", "pct_of_rows", "count", "mean", "std", "min", "p01",
               "p05", "p25", "median", "p75", "p95", "p99", "max"]
    class_stats = class_stats[[c for c in ordered if c in class_stats.columns]]

    bins = pd.cut(score, bins=FRAUD_BIN_EDGES, include_lowest=True, right=True)
    binned = pd.crosstab(bins, label, dropna=False)
    bin_rows = []
    for idx in binned.index:
        c0 = int(binned.loc[idx, 0]) if 0 in binned.columns else 0
        c1 = int(binned.loc[idx, 1]) if 1 in binned.columns else 0
        total = c0 + c1
        bin_rows.append({
            "fraud_score_bin": str(idx),
            "label_0": c0,
            "label_1": c1,
            "total": total,
            "pct_of_rows": pct(total, n_rows),
            "label_1_rate_pct": pct(c1, total),
        })
    bin_table = pd.DataFrame(bin_rows)

    # Exhaustive scan over every observed score value for the rule
    #     predict is_fake_posting = 1  <=>  fraud_score >= t
    counts = pd.crosstab(score[usable], label[usable]).sort_index()
    values = counts.index.to_numpy(dtype=float)
    c0 = counts[0].to_numpy() if 0 in counts.columns else np.zeros(len(values))
    c1 = counts[1].to_numpy() if 1 in counts.columns else np.zeros(len(values))
    tot0, tot1 = c0.sum(), c1.sum()
    cum0 = np.concatenate([[0.0], np.cumsum(c0)[:-1]])   # class 0 strictly below t
    cum1 = np.concatenate([[0.0], np.cumsum(c1)[:-1]])   # class 1 strictly below t
    false_positives = tot0 - cum0                        # class 0 predicted fake
    false_negatives = cum1                               # class 1 predicted genuine
    mismatches = false_positives + false_negatives
    scan = pd.DataFrame({
        "threshold": values,
        "rule": "predict 1 if fraud_score >= threshold",
        "false_positives": false_positives.astype("int64"),
        "false_negatives": false_negatives.astype("int64"),
        "mismatches": mismatches.astype("int64"),
        "mismatch_pct": [pct(m, int(usable.sum())) for m in mismatches],
        "accuracy_pct": [pct(int(usable.sum()) - m, int(usable.sum())) for m in mismatches],
    })
    best_idx = int(np.argmin(mismatches))
    best = scan.iloc[best_idx]

    max_score_class0 = float(score[(label == 0) & usable].max())
    min_score_class1 = float(score[(label == 1) & usable].min())
    overlap_mask = (score >= min_score_class1) & (score <= max_score_class0) & usable
    overlap_rows = int(overlap_mask.sum())
    # When both classes appear at only one score value, the whole ambiguity is a
    # tie at that value rather than a genuine region of disagreement.
    ambiguous_values = counts[(counts.get(0, 0) > 0) & (counts.get(1, 0) > 0)] \
        if {0, 1}.issubset(set(counts.columns)) else counts.iloc[0:0]
    single_tie_value = (float(ambiguous_values.index[0])
                        if len(ambiguous_values) == 1 else None)
    tie_split = ({"label_0": int(ambiguous_values.iloc[0][0]),
                  "label_1": int(ambiguous_values.iloc[0][1])}
                 if single_tie_value is not None else None)

    return {
        "class_stats": class_stats,
        "bin_table": bin_table,
        "scan": scan,
        "facts": {
            "best_threshold": float(best["threshold"]),
            "best_mismatches": int(best["mismatches"]),
            "best_false_positives": int(best["false_positives"]),
            "best_false_negatives": int(best["false_negatives"]),
            "best_accuracy_pct": float(best["accuracy_pct"]),
            "perfect_separation": int(best["mismatches"]) == 0,
            "max_score_class0": max_score_class0,
            "min_score_class1": min_score_class1,
            "overlap_rows": overlap_rows,
            "overlap_pct": pct(overlap_rows, n_rows),
            "usable_rows": int(usable.sum()),
            "ambiguous_score_values": int(len(ambiguous_values)),
            "single_tie_value": single_tie_value,
            "tie_split": tie_split,
        },
    }


# --------------------------------------------------------------------------
# 7. trust signal audit
# --------------------------------------------------------------------------
def audit_trust(df: pd.DataFrame) -> dict:
    """
    Is trust_signal_score a function of the four presence/verification flags?
    The group table below is the saturated model: if every observed combination
    of the flags has zero within-group spread, the score is deterministic in
    them.  Rows where trust_signal_score is null are excluded from the fit and
    counted separately - they are not filled in.
    """
    cols = [c for c in TRUST_INDICATORS if c in df.columns]
    score = pd.to_numeric(df["trust_signal_score"], errors="coerce")
    usable = score.notna()
    for c in cols:
        usable &= df[c].notna()
    excluded = int((~usable).sum())

    work = pd.DataFrame({c: df.loc[usable, c].to_numpy() for c in cols})
    work["trust_signal_score"] = score[usable].to_numpy()

    grouped = (
        work.groupby(cols, as_index=False)
        .agg(row_count=("trust_signal_score", "size"),
             mean=("trust_signal_score", "mean"),
             std=("trust_signal_score", "std"),
             min=("trust_signal_score", "min"),
             max=("trust_signal_score", "max"),
             distinct_scores=("trust_signal_score", "nunique"))
    )
    grouped["range"] = grouped["max"] - grouped["min"]
    grouped["indicator_sum"] = grouped[cols].sum(axis=1)
    grouped["pct_of_usable_rows"] = [
        pct(c, int(usable.sum())) for c in grouped["row_count"]
    ]
    grouped = grouped.sort_values("indicator_sum").reset_index(drop=True)

    max_within_range = float(grouped["range"].max()) if len(grouped) else float("nan")
    deterministic = bool(max_within_range <= DETERMINISM_TOLERANCE)

    # Saturated-model R^2: how much of the score's variance the flag combination
    # alone explains.
    total_var = float(((work["trust_signal_score"] - work["trust_signal_score"].mean()) ** 2).sum())
    group_means = work.groupby(cols)["trust_signal_score"].transform("mean")
    residual_ss = float(((work["trust_signal_score"] - group_means) ** 2).sum())
    r2_saturated = 1.0 - residual_ss / total_var if total_var else float("nan")

    # Additive least-squares fit, to show whether a simple weighted sum reproduces it.
    x = np.column_stack([np.ones(len(work))] + [work[c].to_numpy(dtype=float) for c in cols])
    y = work["trust_signal_score"].to_numpy(dtype=float)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ coef
    residuals = y - fitted
    additive_ss = float((residuals ** 2).sum())
    r2_additive = 1.0 - additive_ss / total_var if total_var else float("nan")

    corr_rows = []
    for c in cols:
        r = float(np.corrcoef(work[c].to_numpy(dtype=float), y)[0, 1])
        means = work.groupby(c)["trust_signal_score"].mean()
        corr_rows.append({
            "indicator": c,
            "pearson_r_with_trust_signal_score": round(r, 6),
            "mean_score_when_0": float(means.get(0, np.nan)),
            "mean_score_when_1": float(means.get(1, np.nan)),
            "mean_difference": float(means.get(1, np.nan)) - float(means.get(0, np.nan)),
            "additive_ols_coefficient": round(float(coef[cols.index(c) + 1]), 6),
        })
    corr_rows.append({
        "indicator": "(intercept)",
        "pearson_r_with_trust_signal_score": np.nan,
        "mean_score_when_0": np.nan,
        "mean_score_when_1": np.nan,
        "mean_difference": np.nan,
        "additive_ols_coefficient": round(float(coef[0]), 6),
    })
    correlations = pd.DataFrame(corr_rows)

    # Also relate the score to the fraud label, since section 6 pairs with this.
    label_corr = float(np.corrcoef(
        df.loc[usable, LABEL].to_numpy(dtype=float), y)[0, 1]) if LABEL in df.columns else np.nan

    return {
        "grouped": grouped,
        "correlations": correlations,
        "facts": {
            "indicators": cols,
            "usable_rows": int(usable.sum()),
            "excluded_rows": excluded,
            "observed_combinations": int(len(grouped)),
            "possible_combinations": 2 ** len(cols),
            "max_within_group_range": max_within_range,
            "max_within_group_std": float(grouped["std"].max()) if len(grouped) else float("nan"),
            "max_distinct_scores_per_group": int(grouped["distinct_scores"].max()) if len(grouped) else 0,
            "deterministic": deterministic,
            "r2_saturated": r2_saturated,
            "r2_additive": r2_additive,
            "residual_std_additive": float(residuals.std(ddof=1)),
            "max_abs_residual_additive": float(np.abs(residuals).max()),
            "corr_with_label": label_corr,
        },
    }


# --------------------------------------------------------------------------
# 8. company / domain age sanity audit
# --------------------------------------------------------------------------
def audit_company_domain(df: pd.DataFrame) -> dict:
    """
    Compare domain_age_months with company_age * 12.  A domain older than its
    company is unusual but not impossible (acquired or parked domains), so this
    section counts the rows and stops there.
    """
    n_rows = len(df)
    company_age = pd.to_numeric(df["company_age"], errors="coerce")
    domain_age = pd.to_numeric(df["domain_age_months"], errors="coerce")
    comparable = company_age.notna() & domain_age.notna()

    company_months = company_age * 12
    excess = domain_age - company_months
    older_mask = comparable & (domain_age > company_months)
    n_older = int(older_mask.sum())

    rows = [
        {"metric": "company_age_min", "value": float(company_age.min())},
        {"metric": "company_age_max", "value": float(company_age.max())},
        {"metric": "company_age_median", "value": float(company_age.median())},
        {"metric": "company_age_null", "value": int(company_age.isna().sum())},
        {"metric": "domain_age_months_min", "value": float(domain_age.min())},
        {"metric": "domain_age_months_max", "value": float(domain_age.max())},
        {"metric": "domain_age_months_median", "value": float(domain_age.median())},
        {"metric": "domain_age_months_null", "value": int(domain_age.isna().sum())},
        {"metric": "rows_comparable", "value": int(comparable.sum())},
        {"metric": "rows_domain_older_than_company", "value": n_older},
        {"metric": "pct_of_all_rows", "value": pct(n_older, n_rows)},
        {"metric": "pct_of_comparable_rows", "value": pct(n_older, int(comparable.sum()))},
        {"metric": "excess_months_min", "value": float(excess[older_mask].min()) if n_older else np.nan},
        {"metric": "excess_months_median", "value": float(excess[older_mask].median()) if n_older else np.nan},
        {"metric": "excess_months_max", "value": float(excess[older_mask].max()) if n_older else np.nan},
        {"metric": "excess_months_mean", "value": float(excess[older_mask].mean()) if n_older else np.nan},
        {"metric": "pearson_r_company_months_vs_domain_months",
         "value": float(company_months[comparable].corr(domain_age[comparable]))},
    ]
    older_label = label_split(df, older_mask.to_numpy())
    rows.extend([
        {"metric": "domain_older_label_0", "value": older_label["label_0"]},
        {"metric": "domain_older_label_1", "value": older_label["label_1"]},
        {"metric": "domain_older_label_1_rate_pct", "value": older_label["label_1_rate_pct"]},
    ])
    table = pd.DataFrame(rows)

    return {
        "table": table,
        "facts": {
            "company_age_min": float(company_age.min()),
            "company_age_max": float(company_age.max()),
            "domain_age_min": float(domain_age.min()),
            "domain_age_max": float(domain_age.max()),
            "n_older": n_older,
            "pct_older": pct(n_older, n_rows),
            "pct_older_comparable": pct(n_older, int(comparable.sum())),
            "max_excess_months": float(excess[older_mask].max()) if n_older else np.nan,
        },
    }


# --------------------------------------------------------------------------
# 9. score range validation
# --------------------------------------------------------------------------
def audit_score_ranges(df: pd.DataFrame) -> dict:
    """Confirm the seven 0-100 scores actually stay inside 0-100."""
    n_rows = len(df)
    rows = []
    for c in SCORE_COLUMNS:
        if c not in df.columns:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        below = int((s < SCORE_MIN).sum())
        above = int((s > SCORE_MAX).sum())
        rows.append({
            "column": c,
            "expected_min": SCORE_MIN,
            "expected_max": SCORE_MAX,
            "observed_min": float(s.min()),
            "observed_max": float(s.max()),
            "count_below_0": below,
            "count_above_100": above,
            "count_outside_range": below + above,
            "pct_outside_range": pct(below + above, n_rows),
            "null_count": int(s.isna().sum()),
            "distinct_values": int(s.nunique()),
            "within_expected_range": bool(below == 0 and above == 0),
        })
    table = pd.DataFrame(rows)
    return {
        "table": table,
        "facts": {
            "violating_columns": table[~table["within_expected_range"]]["column"].tolist(),
            "total_out_of_range": int(table["count_outside_range"].sum()),
        },
    }


# --------------------------------------------------------------------------
# 10. numeric sanity checks
# --------------------------------------------------------------------------
def audit_numeric_sanity(df: pd.DataFrame) -> dict:
    """Negatives, zeros, bounds and IQR-fence counts.  Nothing is capped."""
    n_rows = len(df)
    rows = []
    for c in NUMERIC_SANITY_COLUMNS:
        if c not in df.columns:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        q1, q3, iqr, low, high, below, above = iqr_fences(s)
        d = describe_numeric(s)
        rows.append({
            "column": c,
            "non_null_count": int(s.notna().sum()),
            "null_count": int(s.isna().sum()),
            "negatives": int((s < 0).sum()),
            "zeros": int((s == 0).sum()),
            "zeros_pct": pct(int((s == 0).sum()), n_rows),
            "min": d["min"],
            "p25": q1,
            "median": d["median"],
            "p75": q3,
            "max": d["max"],
            "mean": d["mean"],
            "std": d["std"],
            "iqr": iqr,
            "lower_fence": low,
            "upper_fence": high,
            "below_lower_fence": below,
            "above_upper_fence": above,
            "iqr_outliers": below + above,
            "iqr_outliers_pct": pct(below + above, n_rows),
            # With a zero IQR both fences collapse onto the same value, so every
            # observation that differs from it at all is counted. The count is
            # arithmetically correct but says nothing about extremeness.
            "iqr_is_degenerate": bool(iqr == 0),
        })
    table = pd.DataFrame(rows)
    degenerate = table[table["iqr_is_degenerate"]]["column"].tolist()
    return {
        "table": table,
        "facts": {
            "columns_with_negatives": table[table["negatives"] > 0]["column"].tolist(),
            "columns_with_zeros": table[table["zeros"] > 0]["column"].tolist(),
            "total_iqr_outliers": int(table["iqr_outliers"].sum()),
            "degenerate_iqr_columns": degenerate,
            "total_iqr_outliers_excl_degenerate": int(
                table[~table["iqr_is_degenerate"]]["iqr_outliers"].sum()),
        },
    }


# --------------------------------------------------------------------------
# 11. candidate row identifier
# --------------------------------------------------------------------------
def audit_key_candidates(df: pd.DataFrame, composite_candidates) -> dict:
    """
    Look for a natural single-column key.  No key is created here, and nothing
    is written back to the raw data.
    """
    n_rows = len(df)
    rows = []
    for c in df.columns:
        s = df[c]
        nunique = int(s.nunique(dropna=True))
        nulls = int(s.isna().sum())
        vc_max = int(s.value_counts(dropna=True).max()) if nunique else 0
        rows.append({
            "column": c,
            "dtype": str(s.dtype),
            "distinct_values": nunique,
            "null_count": nulls,
            "uniqueness_ratio": round(nunique / n_rows, 8) if n_rows else 0.0,
            "max_value_frequency": vc_max,
            "is_unique_key": bool(nunique == n_rows and nulls == 0),
        })
    single = pd.DataFrame(rows).sort_values(
        "distinct_values", ascending=False).reset_index(drop=True)

    comp_rows = []
    for combo in composite_candidates:
        present = [c for c in combo if c in df.columns]
        if len(present) != len(combo):
            continue
        nunique = int(df[present].drop_duplicates().shape[0])
        comp_rows.append({
            "column": " + ".join(present),
            "dtype": "composite",
            "distinct_values": nunique,
            "null_count": int(df[present].isna().any(axis=1).sum()),
            "uniqueness_ratio": round(nunique / n_rows, 8) if n_rows else 0.0,
            "max_value_frequency": np.nan,
            "is_unique_key": bool(nunique == n_rows),
        })
    composite = pd.DataFrame(comp_rows)
    combined = pd.concat([single, composite], ignore_index=True) if len(composite) else single

    unique_cols = single[single["is_unique_key"]]["column"].tolist()
    best = single.iloc[0]

    return {
        "table": combined,
        "facts": {
            "unique_single_columns": unique_cols,
            "has_natural_key": bool(unique_cols),
            "highest_cardinality_column": best["column"],
            "highest_cardinality_distinct": int(best["distinct_values"]),
            "highest_cardinality_ratio": float(best["uniqueness_ratio"]),
            "unique_composites": composite[composite["is_unique_key"]]["column"].tolist()
            if len(composite) else [],
        },
    }


# --------------------------------------------------------------------------
# 12. indicators requiring source-provenance verification
# --------------------------------------------------------------------------
def audit_provenance(df: pd.DataFrame, parsed_dates: pd.Series,
                     duplicate_rows: int, missing_result: dict) -> dict:
    """
    Objective, measurable regularities only.  This section deliberately does NOT
    conclude whether the data is synthetic or real - that needs the source.
    """
    n_rows = len(df)
    observations = []

    def add(category, observation, value, note=""):
        observations.append({
            "category": category,
            "observation": observation,
            "value": value,
            "note": note,
        })

    # --- row count
    add("row_count", "row count", n_rows,
        "exactly 1,000,000" if n_rows == 1_000_000 else "not a round number")

    # --- date coverage density
    valid = parsed_dates.notna()
    per_date = parsed_dates[valid].value_counts()
    span_days = (parsed_dates.max() - parsed_dates.min()).days + 1 if valid.any() else 0
    add("date_coverage", "distinct dates observed", int(per_date.size))
    add("date_coverage", "calendar days in span", span_days)
    add("date_coverage", "share of calendar days with at least one row",
        pct(int(per_date.size), span_days), "100% means no gap day in the range")
    add("date_coverage", "rows per date - min", int(per_date.min()) if per_date.size else 0)
    add("date_coverage", "rows per date - max", int(per_date.max()) if per_date.size else 0)
    add("date_coverage", "rows per date - mean", round(float(per_date.mean()), 4) if per_date.size else 0)
    add("date_coverage", "rows per date - std", round(float(per_date.std(ddof=1)), 4) if per_date.size > 1 else 0)
    cv = float(per_date.std(ddof=1) / per_date.mean()) if per_date.size > 1 and per_date.mean() else np.nan
    add("date_coverage", "rows per date - coefficient of variation", round(cv, 6),
        "a low value means dates are close to evenly loaded")
    # Weekday balance - real posting data is usually weekday-heavy.
    weekday = parsed_dates[valid].dt.dayofweek.value_counts(normalize=True).sort_index()
    add("date_coverage", "min weekday share", round(float(weekday.min()) * 100, 4),
        "uniform across 7 weekdays would be 14.2857%")
    add("date_coverage", "max weekday share", round(float(weekday.max()) * 100, 4))

    # --- categorical balance
    text_cols = [c for c in df.columns
                 if is_text_column(df[c]) and df[c].nunique(dropna=True) <= 50]
    for c in text_cols:
        vc = df[c].value_counts(dropna=True, normalize=True)
        k = int(vc.size)
        expected = 100.0 / k if k else np.nan
        deviation = float((vc * 100 - expected).abs().max())
        add("categorical_balance", f"{c}: distinct values", k)
        add("categorical_balance", f"{c}: max deviation from uniform share (pp)",
            round(deviation, 4), f"uniform share would be {expected:.4f}%")

    # --- patterned missingness
    rel = missing_result["relationship"]
    counts = rel["missing_count"].tolist()
    add("missingness", "columns with missing values", int(len(rel)))
    add("missingness", "missing counts", ", ".join(str(int(c)) for c in counts),
        "identical counts across columns would be a pattern, not a coincidence")
    add("missingness", "all missing counts identical",
        bool(len(set(counts)) == 1) if counts else False)
    add("missingness", "missing percentages",
        ", ".join(f"{p:.4f}%" for p in rel["missing_pct"]))
    add("missingness", "rows missing in all three columns",
        missing_result["facts"]["rows_all_missing"],
        f"independence would predict about "
        f"{missing_result['facts']['rows_all_missing_expected']:.2f}")

    # --- duplicates
    add("duplicates", "exact duplicate rows (all 33 columns)", duplicate_rows,
        "counted with duplicated(keep='first'); no row was removed")

    # --- string cleanliness (computed over distinct values, weighted by frequency)
    all_text = [c for c in df.columns if is_text_column(df[c])]
    for c in all_text:
        vc = df[c].value_counts(dropna=True)
        values = np.asarray(vc.index.astype(str), dtype=object)
        counts_arr = vc.to_numpy()
        stripped = np.array([v.strip() for v in values], dtype=object)
        lead_trail = int(counts_arr[values != stripped].sum())
        empty = int(counts_arr[stripped == ""].sum())
        non_ascii = int(counts_arr[
            np.array([not v.isascii() for v in values], dtype=bool)].sum())
        double_space = int(counts_arr[
            np.array(["  " in v for v in values], dtype=bool)].sum())
        add("string_quality", f"{c}: rows with leading/trailing whitespace", lead_trail)
        add("string_quality", f"{c}: rows that are empty after stripping", empty)
        add("string_quality", f"{c}: rows containing non-ASCII characters", non_ascii)
        add("string_quality", f"{c}: rows containing a double space", double_space)

    table = pd.DataFrame(observations)

    # Which low-cardinality categoricals sit within a percentage point of a
    # perfectly even split, and which do not.
    deviations = {}
    for c in text_cols:
        match = table[(table["category"] == "categorical_balance") &
                      (table["observation"] == f"{c}: max deviation from uniform share (pp)")]
        if len(match):
            deviations[c] = float(match.iloc[0]["value"])
    near_uniform = sorted(c for c, d in deviations.items() if d <= 1.0)
    not_uniform = sorted(c for c, d in deviations.items() if d > 1.0)

    string_issue_rows = int(
        table[(table["category"] == "string_quality")]["value"]
        .apply(lambda v: int(v) if isinstance(v, (int, np.integer)) else 0).sum()
    )

    return {
        "table": table,
        "facts": {
            "row_count_exact_million": n_rows == 1_000_000,
            "date_coverage_pct": pct(int(per_date.size), span_days),
            "rows_per_date_cv": cv,
            "duplicate_rows": duplicate_rows,
            "string_issue_rows": string_issue_rows,
            "identical_missing_counts": bool(len(set(counts)) == 1) if counts else False,
            "categorical_deviations": deviations,
            "near_uniform_categoricals": near_uniform,
            "non_uniform_categoricals": not_uniform,
            "max_near_uniform_deviation_pp": max(
                (deviations[c] for c in near_uniform), default=float("nan")),
        },
    }


# --------------------------------------------------------------------------
# markdown report
# --------------------------------------------------------------------------
def write_audit_summary(path: Path, source: Path, fingerprint: dict, df: pd.DataFrame,
                        early_cutoff, future_cutoff, dates, missing, flags, payment,
                        email, fraud, trust, company, scores, numeric, keys,
                        provenance) -> None:
    n_rows, n_cols = df.shape
    lines: list[str] = []
    add = lines.append

    add("# Data Quality / Semantic Audit")
    add("")
    add(f"- **Source file**: `{source.as_posix()}`")
    add(f"- **Generated**: {datetime.now():%Y-%m-%d %H:%M:%S}")
    add(f"- **Source sha256**: `{fingerprint['sha256']}`")
    add(f"- **Rows x columns**: {n_rows:,} x {n_cols}")
    add(f"- **Audit reference date**: {future_cutoff.date()} "
        f"(lower plausibility bound used: {early_cutoff.date()})")
    add("- **Scope**: audit only. Nothing in `data/raw/` was written to. No value was "
        "cleaned, imputed, capped, dropped, normalised, encoded or de-duplicated. "
        "`posting_date` was parsed into a temporary in-memory Series; the loaded "
        "DataFrame was never mutated.")
    add("")
    add("Every table below is a measurement. Where a section names a hypothesis "
        "(\"is X derived from Y?\") the evidence for and against it is given, and the "
        "decision is left open. No column is recommended for deletion or modification.")
    add("")

    # ---- 1 dates
    fd = dates["facts"]
    add("## 1. Posting date audit")
    add("")
    add("**Observed facts**")
    add("")
    rows = [
        ["Minimum `posting_date`", fd["min_date"]],
        ["Maximum `posting_date`", fd["max_date"]],
        ["Span (days)", i(fd["span_days"])],
        ["Distinct dates", i(fd["distinct_dates"])],
        [f"Values not parseable as `{DATE_FORMAT}`", i(fd["strict_unparsed"])],
        ["Values not parseable in any format", i(fd["lenient_unparsed"])],
        [f"Rows before {early_cutoff.date()}", i(fd["rows_before"])],
        [f"Rows after {future_cutoff.date()} (future rows)", i(fd["rows_after"])],
        ["Future rows as % of dataset", f"{fd['rows_after_pct']:.4f}%"],
        ["Distinct future dates", i(fd["distinct_future_dates"])],
    ]
    lines.extend(md_table(["Metric", "Value"], rows, ["---", "---:"]))
    add("")

    if fd["rows_after"]:
        add("Future rows by year and month:")
        add("")
        pm = dates["per_month"]
        rows = [[int(r["year"]), int(r["month"]), i(r["row_count"]),
                 i(r["distinct_dates"]), i(r["label_0_count"]), i(r["label_1_count"]),
                 f"{r['pct_of_future_rows']:.4f}%", f"{r['pct_of_all_rows']:.4f}%"]
                for _, r in pm.iterrows()]
        lines.extend(md_table(
            ["Year", "Month", "Rows", "Distinct dates", "`is_fake_posting`=0",
             "`is_fake_posting`=1", "% of future rows", "% of all rows"],
            rows, ["---:"] * 8))
        add("")
        add("Future rows by `is_fake_posting`:")
        add("")
        fl = dates["future_label"]
        rows = [[int(r[LABEL]), i(r["row_count"]), f"{r['pct_of_future_rows']:.4f}%"]
                for _, r in fl.iterrows()]
        lines.extend(md_table(["`is_fake_posting`", "Rows", "% of future rows"],
                              rows, ["---:", "---:", "---:"]))
        add("")
        add(f"For comparison, the label rate across the whole dataset is "
            f"{fd['baseline_label_rate']:.4f}%.")
        add("")
    else:
        add(f"No row carries a `posting_date` after {future_cutoff.date()}.")
        add("")

    add("Per-date detail for the future block is in `future_dates.csv`; the monthly "
        "aggregation is in `future_dates_by_month.csv`; the boundary metrics are in "
        "`date_bounds.csv`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    if fd["rows_after"]:
        add(f"- {fd['rows_after']:,} rows ({fd['rows_after_pct']:.4f}%) carry a posting "
            f"date later than the audit reference date {future_cutoff.date()}, spread "
            f"over {fd['distinct_future_dates']:,} distinct dates. A posting date in "
            "the future is either a data-entry/generation artefact or a legitimate "
            "\"starts later\" semantic that has been stored in the wrong column. The "
            "data alone cannot distinguish the two. **No future row was deleted.**")
        add("- Whether the fact table's date dimension should span these dates, cap "
            "them, or route them to a late-arriving/unknown-date member is a staging "
            "decision, not an audit finding.")
    else:
        add("- No future-dated rows to review.")
    if fd["rows_before"]:
        add(f"- {fd['rows_before']:,} rows fall before {early_cutoff.date()}. That "
            "boundary is an assumption supplied to this audit, not something the data "
            "asserts; confirm the intended reporting window before acting on it.")
    else:
        add(f"- No row falls before {early_cutoff.date()}.")
    add("")

    # ---- 2 missing
    add("## 2. Missing-value relationship audit")
    add("")
    add("**Observed facts**")
    add("")
    rel = missing["relationship"]
    rows = [[f"`{r['column']}`", i(r["missing_count"]), f"{r['missing_pct']:.4f}%",
             i(r["missing_label_0"]), i(r["missing_label_1"]),
             f"{r['missing_label_1_rate_pct']:.4f}%",
             i(r["non_missing_label_0"]), i(r["non_missing_label_1"]),
             f"{r['non_missing_label_1_rate_pct']:.4f}%",
             f"{r['label_1_rate_difference_pp']:+.4f}"]
            for _, r in rel.iterrows()]
    lines.extend(md_table(
        ["Column", "Missing", "Missing %", "missing: label 0", "missing: label 1",
         "missing: label 1 rate", "present: label 0", "present: label 1",
         "present: label 1 rate", "Difference (pp)"],
        rows, ["---"] + ["---:"] * 9))
    add("")
    add("Pairwise overlap of the missing-value masks:")
    add("")
    ov = missing["overlap"]
    cols = missing["facts"]["columns"]
    header = ["Missing in \\ also missing in"] + [f"`{c}`" for c in cols]
    rows = []
    for a in cols:
        row = [f"`{a}`"]
        for b in cols:
            cell = ov[(ov["column_a"] == a) & (ov["column_b"] == b)].iloc[0]
            row.append(i(cell["missing_both"]))
        rows.append(row)
    lines.extend(md_table(header, rows, ["---"] + ["---:"] * len(cols)))
    add("")
    add("Observed co-missing counts against what statistical independence would "
        "predict:")
    add("")
    pairs = ov[ov["column_a"] < ov["column_b"]]
    rows = [[f"`{r['column_a']}` & `{r['column_b']}`", i(r["missing_both"]),
             f(r["expected_both_if_independent"], 2),
             f(r["observed_minus_expected"], 2), f(r["jaccard"], 6),
             "yes" if r["masks_identical"] else "no"]
            for _, r in pairs.iterrows()]
    lines.extend(md_table(
        ["Pair", "Missing in both", "Expected if independent", "Observed - expected",
         "Jaccard", "Masks identical"], rows, ["---"] + ["---:"] * 5))
    add("")
    fm = missing["facts"]
    add(f"- Rows missing at least one of the three columns: **{fm['rows_any_missing']:,}**.")
    add(f"- Rows missing all three: **{fm['rows_all_missing']:,}** "
        f"(independence would predict about {fm['rows_all_missing_expected']:.2f}).")
    add(f"- Any two masks bit-for-bit identical: **"
        f"{'yes' if fm['any_masks_identical'] else 'no'}**.")
    add(f"- Highest pairwise Jaccard overlap: **{fm['max_pairwise_jaccard']:.6f}**.")
    add("")
    add("The full combination table, including the expected count under independence "
        "for every one of the observed missingness patterns, is in "
        "`missing_combination_counts.csv`. The pairwise matrix is in "
        "`missing_overlap.csv`, the per-column label breakdown in "
        "`missing_value_relationship.csv`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    max_diff = rel["label_1_rate_difference_pp"].abs().max()
    add(f"- The largest gap between the fraud rate among missing rows and among "
        f"present rows is {max_diff:.4f} percentage points. A gap near zero is "
        "evidence that missingness carries no label information; it is not proof, "
        "and it says nothing about association with other columns.")
    if fm["rows_all_missing"] == 0:
        add("- No row is missing all three values, and no two masks are identical, so "
            "the three gaps are not a single record-level dropout.")
    add("- **Nothing was imputed.** Whether these are structurally missing (the fact "
        "does not exist for the posting) or collection gaps cannot be decided from "
        "the data; that determines whether the staging layer keeps a NULL, uses an "
        "\"unknown\" dimension member, or leaves the measure empty in the fact table.")
    add("")

    # ---- 3 binary flags
    add("## 3. Binary flag validation")
    add("")
    add("**Observed facts**")
    add("")
    sm = flags["summary"]
    rows = [[f"`{r['column']}`", r["dtype"], r["distinct_values"],
             i(r["count_0"]), i(r["count_1"]), i(r["count_other_or_null"]),
             f"{r['pct_1']:.4f}%",
             "yes" if r["strictly_binary_0_1"] else "NO",
             "yes" if r["is_constant"] else "no"]
            for _, r in sm.iterrows()]
    lines.extend(md_table(
        ["Column", "dtype", "Distinct values", "Count 0", "Count 1",
         "Other / null", "% of rows = 1", "Strictly {0,1}", "Constant"],
        rows, ["---", "---", "---", "---:", "---:", "---:", "---:", "---", "---"]))
    add("")
    add("Per-value counts are in `binary_flags.csv` (one row per column) and "
        "`binary_flag_value_counts.csv` (one row per column/value pair).")
    add("")
    add("**Possible issues for manual review**")
    add("")
    ff = flags["facts"]
    if ff["non_binary_columns"]:
        add("- Column(s) holding a value outside {0,1} or holding nulls: "
            + ", ".join(f"`{c}`" for c in ff["non_binary_columns"])
            + ". These are not safe to treat as clean booleans without a decision.")
    else:
        add("- All nine columns take values strictly in {0,1} with no nulls, so each "
            "can be modelled as a boolean-valued attribute.")
    if ff["constant_columns"]:
        add("- Constant column(s): "
            + ", ".join(f"`{c}`" for c in ff["constant_columns"])
            + ". A constant column carries no information for slicing and would "
            "produce a single-member degenerate dimension. Flagged only - **not** "
            "recommended for removal here, because a constant in this extract may "
            "still be meaningful in the source system.")
    else:
        add("- No flag column is constant.")
    add("")

    # ---- 4 payment
    add("## 4. Payment consistency audit")
    add("")
    add("**Observed facts**")
    add("")
    rows = [[r["check"], i(r["row_count"]), f"{r['pct_of_rows']:.4f}%"]
            for _, r in payment["checks"].iterrows()]
    lines.extend(md_table(["Check", "Rows", "% of rows"], rows, ["---", "---:", "---:"]))
    add("")
    add("`registration_fee` statistics by `payment_required`:")
    add("")
    ps = payment["stats"]
    rows = [[int(r["payment_required"]), i(r["rows"]), i(r["zeros"]), i(r["positives"]),
             f(r["min"], 2), f(r["p25"], 2), f(r["median"], 2), f(r["p75"], 2),
             f(r["max"], 2), f(r["mean"], 2), f(r["std"], 2)]
            for _, r in ps.iterrows()]
    lines.extend(md_table(
        ["`payment_required`", "Rows", "Fee = 0", "Fee > 0", "min", "p25", "median",
         "p75", "max", "mean", "std"], rows, ["---:"] * 11))
    add("")
    add("Both tables are in `payment_consistency.csv`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    pf = payment["facts"]
    if pf["perfectly_consistent"]:
        add("- The two columns never contradict each other: there is no row with "
            "`payment_required = 0` and a positive fee, and no row with "
            "`payment_required = 1` and a zero fee. `payment_required` is therefore "
            "recoverable from `registration_fee > 0` on this extract.")
        add("- That makes the pair fully redundant **on this extract**, which matters "
            "when choosing whether the flag becomes a dimension attribute and the fee "
            "a fact measure, or whether only the fee is carried. It does not prove the "
            "source system enforces the constraint, and no column is dropped here.")
    else:
        add(f"- {pf['flag0_fee_positive']:,} rows have `payment_required = 0` with a "
            f"positive fee and {pf['flag1_fee_zero']:,} rows have "
            "`payment_required = 1` with a zero fee. Which column is authoritative "
            "is a source question, not something the data can settle.")
    if pf["fee_negative"]:
        add(f"- {pf['fee_negative']:,} rows carry a negative `registration_fee`.")
    else:
        add("- No negative `registration_fee` value exists.")
    add("")

    # ---- 5 email
    add("## 5. Email consistency audit")
    add("")
    add("**Observed facts**")
    add("")
    ct = email["crosstab"]
    n_total = int(ct.to_numpy().sum())
    header = ["`recruiter_email_type` \\ `suspicious_email_domain`"] + \
             [str(c) for c in ct.columns] + ["Total"]
    rows = []
    for r in ct.index:
        vals = [int(ct.loc[r, c]) for c in ct.columns]
        rows.append([str(r)] + [i(v) for v in vals] + [i(sum(vals))])
    totals = [int(ct[c].sum()) for c in ct.columns]
    rows.append(["**Total**"] + [i(v) for v in totals] + [i(sum(totals))])
    lines.extend(md_table(header, rows, ["---"] + ["---:"] * (len(ct.columns) + 1)))
    add("")
    add("Same table as a share of all rows:")
    add("")
    rows = []
    for r in ct.index:
        rows.append([str(r)] + [f"{pct(int(ct.loc[r, c]), n_total):.4f}%"
                                for c in ct.columns])
    lines.extend(md_table(
        ["`recruiter_email_type`"] + [f"`suspicious_email_domain` = {c}" for c in ct.columns],
        rows, ["---"] + ["---:"] * len(ct.columns)))
    add("")
    add("Functional-dependency test, in both directions:")
    add("")
    dep = email["dependencies"]
    rows = [[f"`{r['determinant']}` -> `{r['dependent']}`",
             i(r["distinct_determinant_values"]),
             i(r["max_distinct_dependent_per_value"]),
             "yes" if r["is_exact_function"] else "no",
             i(r["violating_rows"]), f"{r['violating_rows_pct']:.6f}%"]
            for _, r in dep.iterrows()]
    lines.extend(md_table(
        ["Direction", "Distinct determinant values",
         "Max distinct dependent values per key", "Exact function",
         "Violating rows", "% of rows"], rows, ["---"] + ["---:"] * 5))
    add("")
    ef = email["facts"]
    add(f"- Chi-square: {ef['chi2']:,.2f}. Cramer's V: {ef['cramers_v']:.6f} "
        "(1.0 means the two columns are in perfect one-to-one correspondence).")
    add(f"- Rows that fall outside the modal mapping: **{ef['off_diagonal_rows']:,}**.")
    add("")
    add("The counts and all three percentage bases are in `email_crosstab.csv`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    if ef["forward_exact"] and ef["reverse_exact"]:
        add(f"- The mapping is **exact and bijective in both directions**: every value "
            f"of `recruiter_email_type` corresponds to exactly one value of "
            f"`suspicious_email_domain` and vice versa, with 0 violating rows out of "
            f"{n_rows:,} and Cramer's V = {ef['cramers_v']:.6f}. This is a "
            "mathematical demonstration on this extract, so the two columns carry "
            "identical information here.")
        add("- What it does **not** demonstrate: that the source system guarantees the "
            "mapping. `recruiter_email_type` is a label with more possible values than "
            "a boolean; a future extract could contain a third type. Carrying both as "
            "a dimension attribute costs almost nothing and preserves that headroom. "
            "**No decision to drop either column is made here.**")
    elif ef["forward_exact"]:
        add(f"- `recruiter_email_type` determines `suspicious_email_domain` exactly "
            f"(0 violating rows), but not the reverse "
            f"({ef['reverse_violations']:,} violating rows). The flag is a coarsening "
            "of the type, not an equivalent of it.")
    elif ef["reverse_exact"]:
        add(f"- `suspicious_email_domain` determines `recruiter_email_type` exactly, "
            f"but not the reverse ({ef['forward_violations']:,} violating rows).")
    else:
        add(f"- Neither direction is an exact function "
            f"({ef['forward_violations']:,} forward and {ef['reverse_violations']:,} "
            "reverse violating rows), so the columns are associated but not "
            "redundant. Nothing here justifies calling either one derivable.")
    add("")

    # ---- 6 fraud
    add("## 6. Fraud label relationship audit")
    add("")
    add("**Observed facts**")
    add("")
    cs = fraud["class_stats"]
    rows = [[int(r[LABEL]), i(r["rows"]), f"{r['pct_of_rows']:.4f}%", f(r["min"], 2),
             f(r["p05"], 2), f(r["p25"], 2), f(r["median"], 2), f(r["p75"], 2),
             f(r["p95"], 2), f(r["max"], 2), f(r["mean"], 4), f(r["std"], 4)]
            for _, r in cs.iterrows()]
    lines.extend(md_table(
        ["`is_fake_posting`", "Rows", "% of rows", "min", "p05", "p25", "median",
         "p75", "p95", "max", "mean", "std"], rows, ["---:"] * 12))
    add("")
    add("`fraud_score` binned into deciles, crossed with the label:")
    add("")
    bt = fraud["bin_table"]
    rows = [[r["fraud_score_bin"], i(r["label_0"]), i(r["label_1"]), i(r["total"]),
             f"{r['pct_of_rows']:.4f}%", f"{r['label_1_rate_pct']:.4f}%"]
            for _, r in bt.iterrows()]
    lines.extend(md_table(
        ["`fraud_score` bin", "label 0", "label 1", "Total", "% of rows",
         "label 1 rate"], rows, ["---"] + ["---:"] * 5))
    add("")
    frf = fraud["facts"]
    add("Exhaustive threshold scan over every observed `fraud_score` value, for the "
        "rule *predict `is_fake_posting` = 1 when `fraud_score` >= t*:")
    add("")
    rows = [
        ["Best threshold t", f(frf["best_threshold"], 4)],
        ["Mismatches at best t", i(frf["best_mismatches"])],
        ["  of which false positives (label 0, score >= t)", i(frf["best_false_positives"])],
        ["  of which false negatives (label 1, score < t)", i(frf["best_false_negatives"])],
        ["Accuracy at best t", f"{frf['best_accuracy_pct']:.6f}%"],
        ["Perfect reproduction possible", "YES" if frf["perfect_separation"] else "NO"],
        ["Max `fraud_score` among label 0", f(frf["max_score_class0"], 2)],
        ["Min `fraud_score` among label 1", f(frf["min_score_class1"], 2)],
        ["Rows in the overlapping score range", i(frf["overlap_rows"])],
        ["Overlap as % of dataset", f"{frf['overlap_pct']:.4f}%"],
        ["Distinct `fraud_score` values where both classes occur",
         i(frf["ambiguous_score_values"])],
    ]
    lines.extend(md_table(["Metric", "Value"], rows, ["---", "---:"]))
    add("")
    add("The decile crosstab is in `fraud_score_relationship.csv`, the per-class "
        "statistics in `fraud_score_class_stats.csv`, and the full threshold sweep "
        "(one row per candidate threshold) in `fraud_score_threshold_scan.csv`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    if frf["perfect_separation"]:
        add(f"- A single threshold reproduces the label perfectly: "
            f"`fraud_score` >= {frf['best_threshold']:.4f} gives **0 mismatches** "
            f"across {frf['usable_rows']:,} rows. The two columns are the same fact "
            "at two resolutions.")
        add("- For the warehouse this means `is_fake_posting` is a derived attribute "
            "of `fraud_score`, not an independent one. Both are kept. If the two ever "
            "disagree in a later extract, that disagreement is itself the finding.")
    else:
        add(f"- The best single threshold is `fraud_score` >= "
            f"{frf['best_threshold']:.4f}, leaving **{frf['best_mismatches']:,} "
            f"mismatches** ({100 - frf['best_accuracy_pct']:.6f}% of rows: "
            f"{frf['best_false_positives']:,} false positives and "
            f"{frf['best_false_negatives']:,} false negatives). No threshold "
            "reproduces the label exactly, so `is_fake_posting` is not a pure "
            "cut of `fraud_score`.")
        if frf["single_tie_value"] is not None:
            tie = frf["tie_split"]
            add(f"- The disagreement is not spread across a range: both classes occur "
                f"at **exactly one** `fraud_score` value, "
                f"{frf['single_tie_value']:.4f}, where "
                f"{tie['label_0']:,} rows carry label 0 and {tie['label_1']:,} carry "
                f"label 1 ({frf['overlap_rows']:,} rows in total, "
                f"{frf['overlap_pct']:.4f}%). At every other observed score value the "
                "label is constant.")
            add(f"- That is the signature of a boundary rule of the form "
                f"`fraud_score` > {frf['single_tie_value']:.4f} (or >=) with the value "
                f"{frf['single_tie_value']:.4f} itself resolved some other way - by a "
                "second criterion, by rounding before the comparison, or "
                "arbitrarily. Which of those applies cannot be read off the data and "
                "is a question for the source. Until it is answered, treat "
                f"`fraud_score` = {frf['single_tie_value']:.4f} as the one region "
                "where the two columns genuinely differ.")
        else:
            add(f"- The classes overlap on the score range "
                f"[{frf['min_score_class1']:.2f}, {frf['max_score_class0']:.2f}], "
                f"covering {frf['overlap_rows']:,} rows ({frf['overlap_pct']:.4f}%) "
                f"across {frf['ambiguous_score_values']:,} distinct score values. "
                "Those rows are where the label adds information the score does not.")
    add("- **Neither column was removed.** Both remain available; which one becomes a "
        "fact measure and which a dimension attribute is a modelling decision.")
    add("")

    # ---- 7 trust
    add("## 7. Trust signal audit")
    add("")
    add("**Observed facts**")
    add("")
    tf = trust["facts"]
    add(f"`trust_signal_score` is analysed against "
        + ", ".join(f"`{c}`" for c in tf["indicators"]) + ". "
        f"{tf['usable_rows']:,} rows have all five values present; "
        f"{tf['excluded_rows']:,} rows are excluded from this section because "
        "`trust_signal_score` is null. **Excluded rows were not filled in.**")
    add("")
    add("Point-biserial correlation and group means:")
    add("")
    tc = trust["correlations"]
    rows = [[f"`{r['indicator']}`",
             f(r["pearson_r_with_trust_signal_score"], 6),
             f(r["mean_score_when_0"], 4), f(r["mean_score_when_1"], 4),
             f(r["mean_difference"], 4), f(r["additive_ols_coefficient"], 6)]
            for _, r in tc.iterrows()]
    lines.extend(md_table(
        ["Indicator", "Pearson r", "Mean score when 0", "Mean score when 1",
         "Difference", "Additive OLS coefficient"], rows, ["---"] + ["---:"] * 5))
    add("")
    add("Every observed combination of the four indicators (this is the saturated "
        "model - if the within-group range is zero everywhere, the score is a "
        "deterministic function of the four flags):")
    add("")
    g = trust["grouped"]
    ind = tf["indicators"]
    header = [f"`{c}`" for c in ind] + ["Rows", "% of rows", "mean", "std", "min",
                                        "max", "range", "distinct scores"]
    rows = [[int(r[c]) for c in ind] +
            [i(r["row_count"]), f"{r['pct_of_usable_rows']:.4f}%", f(r["mean"], 4),
             f(r["std"], 6), f(r["min"], 4), f(r["max"], 4), f(r["range"], 6),
             i(r["distinct_scores"])]
            for _, r in g.iterrows()]
    lines.extend(md_table(header, rows, ["---:"] * len(header)))
    add("")
    rows = [
        ["Observed indicator combinations",
         f"{tf['observed_combinations']} of {tf['possible_combinations']} possible"],
        ["Largest within-combination range of the score", f(tf["max_within_group_range"], 6)],
        ["Largest within-combination standard deviation", f(tf["max_within_group_std"], 6)],
        ["Largest number of distinct scores in one combination",
         i(tf["max_distinct_scores_per_group"])],
        ["R^2, saturated model (combination -> score)", f(tf["r2_saturated"], 8)],
        ["R^2, additive model (weighted sum of the four flags)", f(tf["r2_additive"], 8)],
        ["Residual std, additive model", f(tf["residual_std_additive"], 6)],
        ["Max absolute residual, additive model", f(tf["max_abs_residual_additive"], 6)],
        ["Correlation of the score with `is_fake_posting`", f(tf["corr_with_label"], 6)],
    ]
    lines.extend(md_table(["Metric", "Value"], rows, ["---", "---:"]))
    add("")
    add("The group table is in `trust_signal_relationship.csv` and the correlations "
        "in `trust_signal_correlations.csv`.")
    add("")
    add("**Evidence, not a decision**")
    add("")
    if tf["deterministic"]:
        add(f"- Within every one of the {tf['observed_combinations']} observed flag "
            "combinations, `trust_signal_score` takes exactly one value (largest "
            f"within-group range {tf['max_within_group_range']:.6f}). On this extract "
            "the score is therefore a **deterministic function** of the four "
            "indicators - demonstrated, not assumed.")
    else:
        add(f"- The score varies within flag combinations (largest within-group range "
            f"{tf['max_within_group_range']:.6f}, largest within-group standard "
            f"deviation {tf['max_within_group_std']:.6f}), so it is **not** a "
            "deterministic function of these four indicators alone.")
        add(f"- The four flags together explain R^2 = {tf['r2_saturated']:.6f} of the "
            f"score's variance in the saturated model, and R^2 = "
            f"{tf['r2_additive']:.6f} as a simple additive weighted sum. The gap "
            "between the two is the part that depends on interactions between flags; "
            "the remainder depends on something not in this column set.")
    add("- What this section does **not** decide: whether `trust_signal_score` should "
        "be kept alongside the indicators. A derived measure can still be worth "
        "storing in a fact table for query convenience. That is a modelling call.")
    add("")

    # ---- 8 company / domain age
    add("## 8. Company / domain-age sanity audit")
    add("")
    add("**Observed facts**")
    add("")
    cf = company["facts"]
    ct8 = company["table"]
    rows = [[f"`{r['metric']}`", smart(r["value"])] for _, r in ct8.iterrows()]
    lines.extend(md_table(["Metric", "Value"], rows, ["---", "---:"]))
    add("")
    add("Full table in `company_domain_age.csv`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    add(f"- `company_age` spans {cf['company_age_min']:.0f} to "
        f"{cf['company_age_max']:.0f} (years); `domain_age_months` spans "
        f"{cf['domain_age_min']:.0f} to {cf['domain_age_max']:.0f} (months, i.e. "
        f"{cf['domain_age_min'] / 12:.1f} to {cf['domain_age_max'] / 12:.1f} years).")
    add(f"- {cf['n_older']:,} rows ({cf['pct_older']:.4f}% of all rows, "
        f"{cf['pct_older_comparable']:.4f}% of rows where both values are present) "
        "have `domain_age_months` greater than `company_age * 12`.")
    add("- **These rows are not called invalid.** A domain can legitimately predate "
        "the company that now uses it: acquired domains, rebrands, parked domains and "
        "holding-company registrations all produce this pattern. The count is reported "
        "so a human can decide whether the magnitude is plausible for this source.")
    if not np.isnan(cf["max_excess_months"]):
        add(f"- The largest excess is {cf['max_excess_months']:.0f} months "
            f"({cf['max_excess_months'] / 12:.1f} years) beyond the company's age. "
            "Whether an excess of that size is plausible is a judgement about the "
            "source, not something the data settles.")
    add("")

    # ---- 9 score ranges
    add("## 9. Score range validation")
    add("")
    add("**Observed facts**")
    add("")
    st = scores["table"]
    rows = [[f"`{r['column']}`", f(r["observed_min"], 2), f(r["observed_max"], 2),
             i(r["count_below_0"]), i(r["count_above_100"]), i(r["count_outside_range"]),
             i(r["null_count"]), i(r["distinct_values"]),
             "yes" if r["within_expected_range"] else "NO"]
            for _, r in st.iterrows()]
    lines.extend(md_table(
        ["Column", "Observed min", "Observed max", "< 0", "> 100", "Outside 0-100",
         "Nulls", "Distinct values", "Within 0-100"],
        rows, ["---"] + ["---:"] * 7 + ["---"]))
    add("")
    add("Full table in `score_range_validation.csv`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    sf = scores["facts"]
    if sf["violating_columns"]:
        add("- Column(s) with values outside the expected 0-100 range: "
            + ", ".join(f"`{c}`" for c in sf["violating_columns"])
            + f" ({sf['total_out_of_range']:,} rows in total). **No value was "
            "clipped.**")
    else:
        add("- Every one of the seven score columns stays inside 0-100. "
            "**0 out-of-range values.** The 0-100 range is therefore safe to declare "
            "as a check constraint in the staging layer.")
    add("- A value inside 0-100 is not the same as a value being correct; this section "
        "validates the range only.")
    add("")

    # ---- 10 numeric sanity
    add("## 10. Numeric sanity checks")
    add("")
    add("**Observed facts**")
    add("")
    nt = numeric["table"]
    rows = [[f"`{r['column']}`", i(r["negatives"]), i(r["zeros"]),
             f"{r['zeros_pct']:.4f}%", f(r["min"], 2), f(r["median"], 2),
             f(r["max"], 2), f(r["lower_fence"], 2), f(r["upper_fence"], 2),
             i(r["iqr_outliers"]), f"{r['iqr_outliers_pct']:.4f}%", i(r["null_count"])]
            for _, r in nt.iterrows()]
    lines.extend(md_table(
        ["Column", "Negatives", "Zeros", "Zeros %", "min", "median", "max",
         "Lower fence", "Upper fence", "IQR outliers", "Outliers %", "Nulls"],
        rows, ["---"] + ["---:"] * 11))
    add("")
    add("Fences are the conventional 1.5x inter-quartile bounds. Full statistics "
        "(mean, std, quartiles, per-side outlier counts) are in `numeric_sanity.csv`.")
    add("")
    add("**Possible issues for manual review**")
    add("")
    nf = numeric["facts"]
    if nf["columns_with_negatives"]:
        add("- Column(s) with negative values: "
            + ", ".join(f"`{c}`" for c in nf["columns_with_negatives"])
            + ". For a quantity that cannot be negative this is a genuine defect.")
    else:
        add("- No column in this set contains a negative value.")
    if nf["columns_with_zeros"]:
        add("- Column(s) containing zeros: "
            + ", ".join(f"`{c}`" for c in nf["columns_with_zeros"])
            + ". A zero may be a real measurement or a placeholder for \"unknown\"; "
            "the two cannot be told apart from the data. This matters most for "
            "`registration_fee`, where zero is meaningful (see section 4).")
    add(f"- {nf['total_iqr_outliers']:,} observations in total fall outside a 1.5x IQR "
        "fence. The IQR fence is a screening device, not a verdict: a long right tail "
        "in a stipend or a response time is ordinary. **No outlier was removed or "
        "capped.**")
    if nf["degenerate_iqr_columns"]:
        add("- The fence is **meaningless** for "
            + ", ".join(f"`{c}`" for c in nf["degenerate_iqr_columns"])
            + ", where the first and third quartiles are both 0, so the inter-quartile "
            "range is 0 and both fences collapse onto 0. Every non-zero value is then "
            "counted as an outlier by construction. Read those counts as \"rows with a "
            "non-zero value\", not as extreme observations. Excluding these columns, "
            f"{nf['total_iqr_outliers_excl_degenerate']:,} observations fall outside a "
            "fence.")
    add("")

    # ---- 11 key
    add("## 11. Candidate row identifier")
    add("")
    add("**Observed facts**")
    add("")
    kt = keys["table"].head(10)
    rows = [[f"`{r['column']}`", i(r["distinct_values"]),
             f"{r['uniqueness_ratio'] * 100:.4f}%",
             i(r["max_value_frequency"]) if not pd.isna(r["max_value_frequency"]) else "n/a",
             i(r["null_count"]), "yes" if r["is_unique_key"] else "no"]
            for _, r in kt.iterrows()]
    lines.extend(md_table(
        ["Column", "Distinct values", "Uniqueness", "Most frequent value appears",
         "Nulls", "Unique key"], rows, ["---"] + ["---:"] * 4 + ["---"]))
    add("")
    add("The ten highest-cardinality candidates are shown; all 33 columns plus the "
        "tested composites are in `key_candidates.csv`.")
    add("")
    kf = keys["facts"]
    if kf["has_natural_key"]:
        add("- Column(s) that are unique and non-null: "
            + ", ".join(f"`{c}`" for c in kf["unique_single_columns"]) + ".")
    else:
        add(f"- **There is no natural single-column key.** The most distinctive "
            f"column, `{kf['highest_cardinality_column']}`, has "
            f"{kf['highest_cardinality_distinct']:,} distinct values across "
            f"{n_rows:,} rows ({kf['highest_cardinality_ratio'] * 100:.4f}% unique), "
            "so it repeats.")
    if kf["unique_composites"]:
        add("- Composite(s) that are unique: "
            + ", ".join(f"`{c}`" for c in kf["unique_composites"]) + ".")
    else:
        add("- None of the tested column combinations is unique either.")
    add("")
    add("**Recommendation (for the later staging layer only)**")
    add("")
    add("- **No key was created and nothing was added to the raw data.** The raw CSV "
        "is unchanged.")
    add("- For the staging layer: generate a `source_row_id` from the original file "
        "row order (1..N as read, ascending, before any filter or sort) and carry it "
        "through as a lineage column. It is the only stable way to point from a "
        "warehouse row back to a specific line of this extract, given that no natural "
        "key exists.")
    add("- Because it comes from file order, `source_row_id` is only meaningful "
        "together with the file's sha256; record both in the load audit table. It is a "
        "lineage handle, not a business key, and should not be used to join across "
        "extracts.")
    add("")

    # ---- 12 provenance
    add("## 12. Indicators requiring source-provenance verification")
    add("")
    add("This section lists **objective, measurable regularities only**. It does "
        "**not** conclude whether the dataset is synthetic or real - that question "
        "cannot be answered from the data and requires the source documentation, the "
        "collection method and the licence. Each item below is a property that is "
        "unusual in organically collected data and therefore worth confirming against "
        "the source.")
    add("")
    add("**Observed facts**")
    add("")
    pf12 = provenance["facts"]
    pt = provenance["table"]
    for category, label in [
        ("row_count", "Row count"),
        ("date_coverage", "Date coverage density"),
        ("categorical_balance", "Categorical balance"),
        ("missingness", "Missingness pattern"),
        ("duplicates", "Duplicates"),
    ]:
        sub = pt[pt["category"] == category]
        if sub.empty:
            continue
        add(f"*{label}*")
        add("")
        rows = [[r["observation"], smart(r["value"]), r["note"]]
                for _, r in sub.iterrows()]
        lines.extend(md_table(["Observation", "Value", "Note"], rows,
                              ["---", "---:", "---"]))
        add("")

    add("*String cleanliness*")
    add("")
    sq = pt[pt["category"] == "string_quality"]
    issue = sq[sq["value"].apply(
        lambda v: isinstance(v, (int, np.integer)) and int(v) > 0)]
    add(f"- Text columns checked: {len(set(o.split(':')[0] for o in sq['observation']))}.")
    add(f"- Rows affected by leading/trailing whitespace, empty-after-strip values, "
        f"non-ASCII characters or double spaces, summed across all text columns: "
        f"**{pf12['string_issue_rows']:,}**.")
    if len(issue):
        add("- Non-zero findings:")
        for _, r in issue.iterrows():
            add(f"  - {r['observation']}: {int(r['value']):,}")
    else:
        add("- Every text column is free of all four defects. No leading or trailing "
            "whitespace, no empty-after-stripping value, no non-ASCII character and no "
            "double space anywhere in the text columns.")
    add("")
    add("The complete list of observations is in `provenance_indicators.csv`.")
    add("")
    add("**What needs confirming from the source, not from the data**")
    add("")
    if pf12["row_count_exact_million"]:
        add("- The row count is exactly 1,000,000. Organically collected extracts are "
            "rarely round; a round count usually means a sampling cap, a generation "
            "parameter, or a deliberate truncation. Which of those applies is a "
            "question for whoever produced the file.")
    if not np.isnan(pf12["rows_per_date_cv"]):
        add(f"- Rows are spread across dates with a coefficient of variation of "
            f"{pf12['rows_per_date_cv']:.4f} and {pf12['date_coverage_pct']:.2f}% of "
            "the calendar days in the range are populated. Near-even loading across "
            "every calendar day, including weekends and holidays, is not typical of "
            "job-posting activity.")
    if pf12["near_uniform_categoricals"]:
        add(f"- {len(pf12['near_uniform_categoricals'])} of "
            f"{len(pf12['categorical_deviations'])} low-cardinality categorical "
            "columns are within one percentage point of a perfectly even split "
            f"(largest deviation among them: "
            f"{pf12['max_near_uniform_deviation_pp']:.4f} pp): "
            + ", ".join(f"`{c}`" for c in pf12["near_uniform_categoricals"]) + ". "
            "An even spread across every category value is rare in observed data, "
            "where some titles, industries and cities always dominate.")
        if pf12["non_uniform_categoricals"]:
            add("- The remaining low-cardinality columns are **not** near-uniform: "
                + ", ".join(
                    f"`{c}` ({pf12['categorical_deviations'][c]:.4f} pp)"
                    for c in pf12["non_uniform_categoricals"])
                + ". They are listed for completeness, as counter-evidence to the "
                "point above.")
    if pf12["identical_missing_counts"]:
        add("- The three incomplete columns are missing in exactly the same number of "
            "rows, at exactly 1.0000% each, with the overlaps matching what "
            "independence predicts (section 2). Missingness that lands on an exact "
            "round percentage independently in three columns is a pattern, not an "
            "accident of collection.")
    if pf12["duplicate_rows"] == 0:
        add(f"- Across {n_rows:,} rows and {n_cols} columns there is not one exact "
            "duplicate row.")
    if pf12["string_issue_rows"] == 0:
        add("- Text fields contain no whitespace, encoding or casing defects at all. "
            "Free-text fields entered by humans normally carry some.")
    add("")
    add("**Explicitly not concluded**: none of the above establishes that the data is "
        "synthetic. Each item is equally consistent with a real dataset that has "
        "already been cleaned, sampled and normalised upstream. Resolve it by asking "
        "for the provenance of the file; until then, treat the dataset's realism as "
        "unverified rather than as either confirmed or denied.")
    add("")

    # ---- closing
    add("## Scope statement")
    add("")
    add(f"- `{source.name}` was opened read-only. Its sha256 is verified before and "
        "after this run.")
    add("- No row was deleted, including future-dated rows. No value was imputed, "
        "capped, clipped, rounded, re-typed or encoded. No column was dropped, "
        "including the columns shown above to be derivable from others. No key was "
        "added to the raw data.")
    add("- The only recommendation in this document is section 11's `source_row_id`, "
        "and it applies to the staging layer, not to the raw file.")
    add("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only data quality / semantic audit (no cleaning).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="path to the raw CSV (read-only)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="directory for the audit outputs")
    parser.add_argument("--early-cutoff", default=DEFAULT_EARLY_CUTOFF,
                        help="lower plausibility bound for posting_date")
    parser.add_argument("--future-cutoff", default=DEFAULT_FUTURE_CUTOFF,
                        help="audit reference date; rows after it are 'future rows'")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    source: Path = args.input.resolve()
    out_dir: Path = args.output_dir.resolve()
    early_cutoff = pd.Timestamp(args.early_cutoff)
    future_cutoff = pd.Timestamp(args.future_cutoff)

    if not source.is_file():
        print(f"ERROR: input file not found: {source}", file=sys.stderr)
        return 1
    if out_dir.is_file():
        print(f"ERROR: output path exists and is a file: {out_dir}", file=sys.stderr)
        return 1
    if source.parent == out_dir:
        print("ERROR: refusing to write audit output into the raw data directory.",
              file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    print(SEP)
    print("DATA QUALITY / SEMANTIC AUDIT (read-only)")
    print(SEP)
    print(f"Input          : {source}")
    print(f"Output dir     : {out_dir}")
    print(f"Early cutoff   : {early_cutoff.date()}")
    print(f"Future cutoff  : {future_cutoff.date()}")
    print("Fingerprinting raw file (before) ...", flush=True)
    fingerprint_before = file_fingerprint(source)
    print(f"  size {human_bytes(fingerprint_before['size_bytes'])}, "
          f"sha256 {fingerprint_before['sha256']}")

    print("Loading CSV ...", flush=True)
    t0 = time.perf_counter()
    df = pd.read_csv(source)
    load_seconds = time.perf_counter() - t0
    n_rows, n_cols = df.shape
    print(f"  loaded {n_rows:,} rows x {n_cols} columns in {load_seconds:.2f}s")

    print(" 1/12 posting date audit ...", flush=True)
    dates = audit_posting_dates(df, early_cutoff, future_cutoff)
    print(" 2/12 missing-value relationship audit ...", flush=True)
    missing = audit_missing(df)
    print(" 3/12 binary flag validation ...", flush=True)
    flags = audit_binary_flags(df)
    print(" 4/12 payment consistency audit ...", flush=True)
    payment = audit_payment(df)
    print(" 5/12 email consistency audit ...", flush=True)
    email = audit_email(df)
    print(" 6/12 fraud label relationship audit ...", flush=True)
    fraud = audit_fraud(df)
    print(" 7/12 trust signal audit ...", flush=True)
    trust = audit_trust(df)
    print(" 8/12 company / domain-age sanity audit ...", flush=True)
    company = audit_company_domain(df)
    print(" 9/12 score range validation ...", flush=True)
    scores = audit_score_ranges(df)
    print("10/12 numeric sanity checks ...", flush=True)
    numeric = audit_numeric_sanity(df)
    print("11/12 candidate row identifier ...", flush=True)
    keys = audit_key_candidates(df, composite_candidates=[
        ("company_name", "posting_date"),
        ("company_name", "posting_date", "internship_title"),
        ("company_name", "posting_date", "internship_title", "location"),
    ])
    print("12/12 provenance indicators ...", flush=True)
    duplicate_rows = int(df.duplicated(keep="first").sum())
    provenance = audit_provenance(df, dates["parsed"], duplicate_rows, missing)

    print("Writing outputs ...", flush=True)
    dates["bounds"].to_csv(out_dir / "date_bounds.csv", index=False)
    dates["per_date"].to_csv(out_dir / "future_dates.csv", index=False)
    dates["per_month"].to_csv(out_dir / "future_dates_by_month.csv", index=False)
    missing["relationship"].to_csv(out_dir / "missing_value_relationship.csv", index=False)
    missing["overlap"].to_csv(out_dir / "missing_overlap.csv", index=False)
    missing["combinations"].to_csv(out_dir / "missing_combination_counts.csv", index=False)
    flags["summary"].to_csv(out_dir / "binary_flags.csv", index=False)
    flags["value_counts"].to_csv(out_dir / "binary_flag_value_counts.csv", index=False)
    payment["combined"].to_csv(out_dir / "payment_consistency.csv", index=False)
    email["tidy"].to_csv(out_dir / "email_crosstab.csv", index=False)
    fraud["bin_table"].to_csv(out_dir / "fraud_score_relationship.csv", index=False)
    fraud["class_stats"].to_csv(out_dir / "fraud_score_class_stats.csv", index=False)
    fraud["scan"].to_csv(out_dir / "fraud_score_threshold_scan.csv", index=False)
    trust["grouped"].to_csv(out_dir / "trust_signal_relationship.csv", index=False)
    trust["correlations"].to_csv(out_dir / "trust_signal_correlations.csv", index=False)
    company["table"].to_csv(out_dir / "company_domain_age.csv", index=False)
    scores["table"].to_csv(out_dir / "score_range_validation.csv", index=False)
    numeric["table"].to_csv(out_dir / "numeric_sanity.csv", index=False)
    keys["table"].to_csv(out_dir / "key_candidates.csv", index=False)
    provenance["table"].to_csv(out_dir / "provenance_indicators.csv", index=False)
    write_audit_summary(out_dir / "audit_summary.md", source, fingerprint_before, df,
                        early_cutoff, future_cutoff, dates, missing, flags, payment,
                        email, fraud, trust, company, scores, numeric, keys, provenance)

    fingerprint_after = file_fingerprint(source)
    raw_unchanged = fingerprint_after == fingerprint_before

    # ---- terminal summary
    fd = dates["facts"]
    ff = flags["facts"]
    pf = payment["facts"]
    ef = email["facts"]
    frf = fraud["facts"]
    tf = trust["facts"]
    cf = company["facts"]
    sf = scores["facts"]
    nf = numeric["facts"]
    kf = keys["facts"]
    pf12 = provenance["facts"]

    print()
    print(SEP)
    print("AUDIT SUMMARY")
    print(SEP)
    print(f" 1. Dates        : {fd['min_date']} -> {fd['max_date']} "
          f"({fd['distinct_dates']:,} distinct)")
    print(f"                   before {early_cutoff.date()}: {fd['rows_before']:,} | "
          f"after {future_cutoff.date()}: {fd['rows_after']:,} "
          f"({fd['rows_after_pct']:.4f}%) over "
          f"{fd['distinct_future_dates']:,} distinct dates")
    mrel = missing["relationship"]
    print(f" 2. Missingness  : "
          + " | ".join(f"{r['column']} {int(r['missing_count']):,} "
                       f"({r['missing_pct']:.4f}%)" for _, r in mrel.iterrows()))
    print(f"                   rows missing all three: "
          f"{missing['facts']['rows_all_missing']:,} | masks identical: "
          f"{'yes' if missing['facts']['any_masks_identical'] else 'no'}")
    print(f" 3. Binary flags : {len(ff['checked'])} checked | not strictly 0/1: "
          f"{', '.join(ff['non_binary_columns']) if ff['non_binary_columns'] else 'none'}"
          f" | constant: "
          f"{', '.join(ff['constant_columns']) if ff['constant_columns'] else 'none'}")
    print(f" 4. Payment      : flag=0 & fee>0: {pf['flag0_fee_positive']:,} | "
          f"flag=1 & fee=0: {pf['flag1_fee_zero']:,} | "
          f"consistent: {'YES' if pf['perfectly_consistent'] else 'NO'}")
    print(f" 5. Email        : Cramer's V {ef['cramers_v']:.6f} | exact function "
          f"fwd/rev: {'yes' if ef['forward_exact'] else 'no'}/"
          f"{'yes' if ef['reverse_exact'] else 'no'} | "
          f"rows off the modal mapping: {ef['off_diagonal_rows']:,}")
    print(f" 6. Fraud score  : best threshold >= {frf['best_threshold']:.4f} -> "
          f"{frf['best_mismatches']:,} mismatches "
          f"({frf['best_accuracy_pct']:.6f}% accuracy) | perfect: "
          f"{'YES' if frf['perfect_separation'] else 'NO'}")
    if frf["single_tie_value"] is not None:
        print(f"                   both classes occur at exactly one score value "
              f"({frf['single_tie_value']:.4f}): "
              f"{frf['tie_split']['label_0']:,} label 0 / "
              f"{frf['tie_split']['label_1']:,} label 1")
    print(f" 7. Trust signal : {tf['observed_combinations']}/"
          f"{tf['possible_combinations']} flag combinations | max within-group range "
          f"{tf['max_within_group_range']:.6f} | R^2 saturated {tf['r2_saturated']:.6f} "
          f"| deterministic: {'YES' if tf['deterministic'] else 'NO'}")
    print(f" 8. Company/domain: company_age {cf['company_age_min']:.0f}-"
          f"{cf['company_age_max']:.0f} yr | domain_age_months "
          f"{cf['domain_age_min']:.0f}-{cf['domain_age_max']:.0f} | "
          f"domain older than company: {cf['n_older']:,} ({cf['pct_older']:.4f}%)")
    print(f" 9. Score ranges : out of 0-100: {sf['total_out_of_range']:,} value(s)"
          + (f" in {', '.join(sf['violating_columns'])}" if sf["violating_columns"] else ""))
    print(f"10. Numeric      : negatives in "
          f"{', '.join(nf['columns_with_negatives']) if nf['columns_with_negatives'] else 'none'}"
          f" | IQR-fence observations: {nf['total_iqr_outliers']:,}")
    print(f"11. Row key      : natural single-column key: "
          f"{'YES - ' + ', '.join(kf['unique_single_columns']) if kf['has_natural_key'] else 'NONE'}"
          f" (best: {kf['highest_cardinality_column']}, "
          f"{kf['highest_cardinality_ratio'] * 100:.2f}% unique)")
    print(f"                   recommendation: generate source_row_id in STAGING only; "
          "nothing added to raw")
    print(f"12. Provenance   : rows {n_rows:,}"
          f"{' (exactly 1,000,000)' if pf12['row_count_exact_million'] else ''} | "
          f"date coverage {pf12['date_coverage_pct']:.2f}% of calendar days | "
          f"duplicates {pf12['duplicate_rows']:,} | string defects "
          f"{pf12['string_issue_rows']:,}")
    print("                   labelled 'indicators requiring source-provenance "
          "verification'; synthetic vs real NOT concluded")
    print()
    print("Files written:")
    for path in sorted(p for p in out_dir.glob("*") if p.is_file()):
        print(f"  {path.name:<36} {human_bytes(path.stat().st_size):>12}")
    print()
    print(f"Raw sha256 before : {fingerprint_before['sha256']}")
    print(f"Raw sha256 after  : {fingerprint_after['sha256']}")
    print(f"Raw file unchanged: {'YES' if raw_unchanged else 'NO - INVESTIGATE'}")
    print(SEP)
    print("Audit only. Nothing was cleaned, imputed, capped, dropped, encoded or")
    print("de-duplicated, and no cleaning decision was made.")
    print(SEP)

    return 0 if raw_unchanged else 2


if __name__ == "__main__":
    raise SystemExit(main())
