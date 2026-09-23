#!/usr/bin/env python3
"""
Dimensional consistency / functional dependency audit for the staging dataset.

AUDIT ONLY.  This script is strictly read-only with respect to data/raw/ and
data/staging/: it opens data/staging/internship_postings_staging.csv for
reading, writes nothing back, and performs NO cleaning, imputation, capping,
dropping, normalisation, encoding, entity resolution or de-duplication.  The
sha256 of the staging file is measured before and after the run and the two
values are compared.

The purpose is to establish, from evidence only, which attributes could later
be grouped into dimensions.  Nothing here designs a star schema, fixes a
grain, or creates SQL.  Every number below is an observation; every grouping
is a candidate.

Outputs (results/dimensional_audit/):
    dimensional_consistency_en.md
    dimensional_consistency_vi.md
    company_consistency.csv
    company_consistency_examples.csv
    company_age_time_consistency.csv
    domain_age_time_consistency.csv
    company_attribute_combinations.csv
    title_attribute_crosstab.csv
    industry_title_crosstab.csv
    location_profile.csv
    location_industry_crosstab.csv
    employment_workmode_crosstab.csv
    email_bijection.csv
    payment_consistency_check.csv
    categorical_dependency_summary.csv
    field_classification.csv
    candidate_dimension_summary.csv
    candidate_measure_summary.csv
    grain_evidence.csv

Usage:
    python scripts/audit_dimensional_consistency.py
    python scripts/audit_dimensional_consistency.py --input <csv> --output-dir <dir>
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
DEFAULT_INPUT = PROJECT_ROOT / "data" / "staging" / "internship_postings_staging.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "dimensional_audit"

SEP = "=" * 74
DATE_COLUMN = "posting_date"
GROUP_COLUMN = "company_name"
LABEL = "is_fake_posting"

# Attributes inspected for stability within one company_name (section 1).
COMPANY_DEPENDENT_ATTRIBUTES = [
    "company_size",
    "company_age",
    "linkedin_presence",
    "website_available",
    "domain_age_months",
    "verification_status",
    "social_media_presence",
    "location",
    "industry",
]

# Attributes whose joint combination is tested against company_name (section 4).
COMPANY_COMBINATION_ATTRIBUTES = [
    "company_size",
    "linkedin_presence",
    "website_available",
    "verification_status",
    "social_media_presence",
]

# Attributes profiled against internship_title (section 5).
TITLE_DEPENDENT_ATTRIBUTES = ["industry", "employment_type", "work_mode", "location"]

# Logical field groups (section 11).
CONTENT_QUALITY_FIELDS = [
    "job_description_length",
    "grammatical_errors",
    "vague_description_score",
    "urgency_score",
    "keyword_spam_score",
    "emotional_manipulation_score",
    "phishing_language_score",
]
TRUST_COMPANY_FIELDS = [
    "linkedin_presence",
    "website_available",
    "verification_status",
    "domain_age_months",
    "social_media_presence",
    "trust_signal_score",
]
FRAUD_OUTCOME_FIELDS = [
    "unrealistic_salary_flag",
    "payment_required",
    "registration_fee",
    "fake_certificate_offer",
    "suspicious_email_domain",
    "fraud_score",
    "is_fake_posting",
]

# Every column whose stability within company_name is measured (superset).
STABILITY_FIELDS = sorted(set(
    COMPANY_DEPENDENT_ATTRIBUTES
    + CONTENT_QUALITY_FIELDS
    + TRUST_COMPANY_FIELDS
    + FRAUD_OUTCOME_FIELDS
    + ["internship_title", "employment_type", "work_mode", "stipend",
       "recruiter_experience_years", "recruiter_email_type",
       "recruiter_response_time_hours", "is_future_posting"]
))

# Compact read dtypes.  Ranges were established by the staging column profile
# (results/staging/staging_column_profile.csv) and are re-validated below;
# narrowing the physical width changes no value.
READ_DTYPES = {
    "posting_date": "str",
    "internship_title": "str",
    "employment_type": "str",
    "work_mode": "str",
    "industry": "str",
    "location": "str",
    "company_name": "str",
    "company_size": "str",
    "recruiter_email_type": "str",
    "company_age": "float32",
    "linkedin_presence": "int8",
    "website_available": "int8",
    "domain_age_months": "int16",
    "verification_status": "int8",
    "stipend": "float32",
    "unrealistic_salary_flag": "int8",
    "payment_required": "int8",
    "registration_fee": "int16",
    "job_description_length": "int16",
    "grammatical_errors": "int8",
    "vague_description_score": "int8",
    "urgency_score": "int8",
    "keyword_spam_score": "int8",
    "fake_certificate_offer": "int8",
    "recruiter_experience_years": "float32",
    "suspicious_email_domain": "int8",
    "recruiter_response_time_hours": "float32",
    "social_media_presence": "int8",
    "emotional_manipulation_score": "int8",
    "phishing_language_score": "int8",
    "trust_signal_score": "float32",
    "fraud_score": "float32",
    "is_fake_posting": "int8",
    "source_row_id": "int32",
    "is_future_posting": "int8",
}

CATEGORY_COLUMNS = [
    "internship_title", "employment_type", "work_mode", "industry",
    "location", "company_size", "recruiter_email_type", "company_name",
]

CHUNK_ROWS = 100_000

# Tolerances used when comparing a stated age against elapsed calendar time.
# They are reporting thresholds only: no row is corrected, and a row outside a
# tolerance is evidence to review, not an established error.
AGE_YEAR_TOLERANCE = 1.0       # years, for company_age vs elapsed time
DOMAIN_MONTH_TOLERANCE = 6.0   # months, for domain_age_months vs elapsed time
DAYS_PER_YEAR = 365.25
DAYS_PER_MONTH = 30.436875


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def pct(part: float, whole: float) -> float:
    return 0.0 if not whole else 100.0 * float(part) / float(whole)


def file_fingerprint(path: Path) -> dict:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    st = path.stat()
    return {
        "sha256": h.hexdigest(),
        "size_bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }


def i(x) -> str:
    """Integer with thousands separators."""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "n/a"
        return f"{int(x):,}"
    except (TypeError, ValueError):
        return str(x)


def f(x, d: int = 4) -> str:
    """Fixed-precision float."""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "n/a"
        return f"{float(x):,.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def md_table(headers, rows, aligns=None) -> list[str]:
    if aligns is None:
        aligns = ["---"] * len(headers)
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "| " + " | ".join(aligns) + " |"]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    out.append("")
    return out


def distinct_per_group(group_codes: np.ndarray, value_codes: np.ndarray,
                       n_groups: int) -> np.ndarray:
    """
    Number of distinct non-negative value codes per group.

    A value code of -1 marks a missing value and is excluded from the count;
    missingness is reported separately rather than counted as a value.
    """
    keep = value_codes >= 0
    g = group_codes[keep]
    v = value_codes[keep]
    if g.size == 0:
        return np.zeros(n_groups, dtype=np.int64)
    order = np.lexsort((v, g))
    g = g[order]
    v = v[order]
    first = np.empty(g.size, dtype=bool)
    first[0] = True
    np.not_equal(g[1:], g[:-1], out=first[1:])
    np.logical_or(first[1:], v[1:] != v[:-1], out=first[1:])
    return np.bincount(g[first], minlength=n_groups).astype(np.int64)


def codes_of(series: pd.Series) -> tuple[np.ndarray, int]:
    """Factorise a Series to int32 codes (-1 for missing) plus a level count."""
    if isinstance(series.dtype, pd.CategoricalDtype):
        codes = np.asarray(series.cat.codes)
        return codes.astype(np.int32, copy=False), int(len(series.cat.categories))
    codes, uniques = pd.factorize(series, use_na_sentinel=True)
    return np.asarray(codes).astype(np.int32, copy=False), int(len(uniques))


def cramers_v(table: np.ndarray):
    """Bias-corrected Cramer's V.  Returns None when undefined."""
    table = np.asarray(table, dtype=float)
    n = table.sum()
    if n <= 0 or min(table.shape) < 2:
        return None
    row = table.sum(axis=1, keepdims=True)
    col = table.sum(axis=0, keepdims=True)
    expected = row @ col / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = float(np.nansum(np.where(expected > 0,
                                        (table - expected) ** 2 / expected, 0.0)))
    phi2 = chi2 / n
    r, k = table.shape
    phi2corr = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    rcorr = r - (r - 1) ** 2 / (n - 1)
    kcorr = k - (k - 1) ** 2 / (n - 1)
    denom = min(kcorr - 1, rcorr - 1)
    if denom <= 0:
        return None
    return float(np.sqrt(phi2corr / denom))


def functional_dependency(left: pd.Series, right: pd.Series) -> dict:
    """
    Test left -> right: does each value of `left` map to exactly one value of
    `right`?  Rows where either side is missing are excluded and counted.
    """
    mask = left.notna() & right.notna()
    lc, nl = codes_of(left[mask])
    rc, _ = codes_of(right[mask])
    per = distinct_per_group(lc, rc, nl)
    counts = np.bincount(lc[lc >= 0], minlength=nl)
    used = per[counts > 0]
    violating_groups = int((per > 1).sum())
    violating_rows = int(counts[per > 1].sum())
    return {
        "holds": bool(violating_groups == 0),
        "left_levels": int((counts > 0).sum()),
        "violating_groups": violating_groups,
        "violating_rows": violating_rows,
        "max_targets": int(used.max()) if used.size else 0,
        "excluded_rows": int((~mask).sum()),
    }


def numeric_summary(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce")
    nn = s.dropna()
    if nn.empty:
        return {"count": 0, "min": np.nan, "max": np.nan, "mean": np.nan,
                "std": np.nan, "median": np.nan, "distinct": 0, "zeros": 0}
    return {
        "count": int(nn.size),
        "min": float(nn.min()),
        "max": float(nn.max()),
        "mean": float(nn.mean()),
        "std": float(nn.std()),
        "median": float(nn.median()),
        "distinct": int(nn.nunique()),
        "zeros": int((nn == 0).sum()),
    }


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def load_staging(path: Path, verbose: bool = True) -> pd.DataFrame:
    """
    Quote-aware chunked read of the staging CSV with compact dtypes.

    Chunking and dtype narrowing are performance measures only; no value is
    altered.  company_name is read with a quote-aware parser because values
    contain embedded commas.
    """
    frames = []
    reader = pd.read_csv(path, dtype=READ_DTYPES, chunksize=CHUNK_ROWS,
                         keep_default_na=True)
    total = 0
    for k, chunk in enumerate(reader, start=1):
        frames.append(chunk)
        total += len(chunk)
        if verbose:
            print(f"    chunk {k:>2}: {total:,} rows", flush=True)
    df = pd.concat(frames, ignore_index=True)
    del frames
    for col in CATEGORY_COLUMNS:
        df[col] = df[col].astype("category")
    return df


# --------------------------------------------------------------------------
# section 1 - company entity consistency
# --------------------------------------------------------------------------
def audit_company_consistency(df: pd.DataFrame) -> dict:
    """
    For each dependent attribute, how stable is it inside one company_name?

    company_name is used as a grouping attribute only.  It is NOT assumed to
    be a company identifier: two rows sharing a name may or may not be the
    same real company, and the dataset carries no company id to settle it.
    """
    ccodes, n_companies = codes_of(df[GROUP_COLUMN])
    posting_count = np.bincount(ccodes, minlength=n_companies).astype(np.int64)
    repeated_mask = posting_count > 1
    n_repeated = int(repeated_mask.sum())
    n_single = int(n_companies - n_repeated)
    rows_in_repeated = int(posting_count[repeated_mask].sum())

    rows = []
    distinct_matrix = {}
    for col in COMPANY_DEPENDENT_ATTRIBUTES:
        vcodes, _ = codes_of(df[col])
        per = distinct_per_group(ccodes, vcodes, n_companies)
        distinct_matrix[col] = per
        # Companies with no observed non-missing value at all.
        no_value_all = int((per == 0).sum())
        rep = per[repeated_mask]
        stable = int((rep == 1).sum())
        multi = int((rep > 1).sum())
        none_rep = int((rep == 0).sum())
        rows.append({
            "attribute": col,
            "companies_total": n_companies,
            "companies_repeated": n_repeated,
            "repeated_with_one_distinct_value": stable,
            "repeated_with_multiple_distinct_values": multi,
            "repeated_with_no_observed_value": none_rep,
            "pct_stable_among_repeated": pct(stable, n_repeated),
            "pct_stable_among_repeated_with_value": pct(stable, n_repeated - none_rep),
            "max_distinct_values_one_company": int(per.max()) if per.size else 0,
            "max_distinct_among_repeated": int(rep.max()) if rep.size else 0,
            "companies_with_no_observed_value": no_value_all,
            "mean_distinct_among_repeated": float(rep.mean()) if rep.size else 0.0,
            "attribute_distinct_values_dataset": int(df[col].nunique(dropna=True)),
            "attribute_missing_rows": int(df[col].isna().sum()),
        })
    table = pd.DataFrame(rows)

    # Problematic examples: repeated companies ranked by total distinct values
    # observed across the nine attributes, then by posting count.
    total_distinct = np.zeros(n_companies, dtype=np.int64)
    for col in COMPANY_DEPENDENT_ATTRIBUTES:
        total_distinct += distinct_matrix[col]
    score = np.where(repeated_mask, total_distinct, -1)
    order = np.lexsort((-posting_count, -score))
    top = order[:20]
    categories = df[GROUP_COLUMN].cat.categories
    ex_rows = []
    for gid in top:
        if score[gid] < 0:
            continue
        rec = {"company_name": str(categories[gid]),
               "posting_count": int(posting_count[gid]),
               "total_distinct_across_attributes": int(total_distinct[gid])}
        for col in COMPANY_DEPENDENT_ATTRIBUTES:
            rec[f"distinct_{col}"] = int(distinct_matrix[col][gid])
        ex_rows.append(rec)
    examples = pd.DataFrame(ex_rows)

    # Distribution of postings per company_name.
    bins = [1, 2, 3, 4, 5, 10, 20, 50, 10 ** 9]
    labels = ["1", "2", "3", "4", "5-9", "10-19", "20-49", "50+"]
    idx = np.digitize(posting_count, bins[1:], right=False)
    dist_rows = []
    for k, lab in enumerate(labels):
        sel = idx == k
        dist_rows.append({
            "postings_per_company": lab,
            "company_names": int(sel.sum()),
            "pct_of_company_names": pct(int(sel.sum()), n_companies),
            "rows_covered": int(posting_count[sel].sum()),
            "pct_of_rows": pct(int(posting_count[sel].sum()), len(df)),
        })
    distribution = pd.DataFrame(dist_rows)

    facts = {
        "n_rows": int(len(df)),
        "n_companies": n_companies,
        "n_repeated": n_repeated,
        "n_single": n_single,
        "pct_repeated": pct(n_repeated, n_companies),
        "rows_in_repeated": rows_in_repeated,
        "pct_rows_in_repeated": pct(rows_in_repeated, len(df)),
        "max_postings_one_company": int(posting_count.max()),
        "max_postings_company_name": str(categories[int(posting_count.argmax())]),
        "mean_postings_per_company": float(posting_count.mean()),
        "any_attribute_fully_stable": [r["attribute"] for r in rows
                                       if r["repeated_with_multiple_distinct_values"] == 0],
        "lowest_stability_attribute": min(rows, key=lambda r: r["pct_stable_among_repeated"])["attribute"],
        "lowest_stability_pct": min(r["pct_stable_among_repeated"] for r in rows),
        "highest_stability_attribute": max(rows, key=lambda r: r["pct_stable_among_repeated"])["attribute"],
        "highest_stability_pct": max(r["pct_stable_among_repeated"] for r in rows),
    }
    return {"table": table, "examples": examples, "distribution": distribution,
            "facts": facts, "ccodes": ccodes, "n_companies": n_companies,
            "posting_count": posting_count, "repeated_mask": repeated_mask}


# --------------------------------------------------------------------------
# section 2 / 3 - a stated age against calendar time
# --------------------------------------------------------------------------
def _time_series_consistency(df: pd.DataFrame, ccodes: np.ndarray, n_companies: int,
                             value_col: str, day_scale: float, tolerance: float,
                             posting_count: np.ndarray) -> dict:
    """
    Shared machinery for sections 2 and 3.

    Sorts each company's rows by posting_date and compares the change in the
    stated age between consecutive postings against the calendar time that
    elapsed between them.  `day_scale` converts days to the unit of the value
    column (years for company_age, months for domain_age_months).

    Nothing is corrected.  A row outside the tolerance is listed as evidence.
    """
    vals = pd.to_numeric(df[value_col], errors="coerce").to_numpy(dtype="float64")
    days = df["_date_ordinal"].to_numpy(dtype="float64")
    ok = ~np.isnan(vals) & ~np.isnan(days)
    g = ccodes[ok]
    v = vals[ok]
    d = days[ok]

    order = np.lexsort((v, d, g))
    g = g[order]
    v = v[order]
    d = d[order]

    same = g[1:] == g[:-1]
    dv = v[1:] - v[:-1]
    dd = d[1:] - d[:-1]
    elapsed = dd / day_scale

    # Only consecutive pairs inside one company_name are meaningful.
    pair_company = g[1:][same]
    pair_dv = dv[same]
    pair_dd = dd[same]
    pair_elapsed = elapsed[same]

    n_pairs = int(pair_dv.size)
    decreases = pair_dv < 0
    n_decrease = int(decreases.sum())
    companies_with_decrease = int(np.unique(pair_company[decreases]).size) if n_decrease else 0
    increases = pair_dv > 0
    flat = pair_dv == 0

    # "Jump" = the stated age moved much more, or much less, than calendar time.
    residual = pair_dv - pair_elapsed
    implausible = np.abs(residual) > tolerance
    n_implausible = int(implausible.sum())
    companies_implausible = int(np.unique(pair_company[implausible]).size) if n_implausible else 0

    # Same company, same calendar day, different stated value.
    same_day = same & (dd == 0)
    same_day_conflict = same_day & (dv != 0)
    n_same_day_conflict = int(same_day_conflict.sum())

    # Distinct values per company, and per (company, calendar year).
    vcodes, n_levels = codes_of(pd.Series(vals))
    per_company = distinct_per_group(ccodes, vcodes, n_companies)
    rep = per_company[posting_count > 1]
    years = df["_posting_year"].to_numpy()
    ymin = int(np.nanmin(years))
    year_key = (ccodes.astype(np.int64) * 16) + (years - ymin)
    yk_codes, yk_uniques = pd.factorize(year_key)
    yk_codes = np.asarray(yk_codes).astype(np.int64)
    n_yk = int(len(yk_uniques))
    per_year = distinct_per_group(yk_codes.astype(np.int32), vcodes, n_yk)
    yk_counts = np.bincount(yk_codes, minlength=n_yk)
    multi_row_year_groups = int((yk_counts > 1).sum())
    year_groups_multi_value = int((per_year > 1).sum())

    summary = pd.DataFrame([
        {"metric": "companies_with_more_than_one_posting",
         "value": int((posting_count > 1).sum())},
        {"metric": "repeated_companies_with_one_distinct_value",
         "value": int((rep == 1).sum())},
        {"metric": "repeated_companies_with_multiple_distinct_values",
         "value": int((rep > 1).sum())},
        {"metric": "max_distinct_values_one_company", "value": int(per_company.max())},
        {"metric": "consecutive_posting_pairs_examined", "value": n_pairs},
        {"metric": "pairs_value_increases", "value": int(increases.sum())},
        {"metric": "pairs_value_unchanged", "value": int(flat.sum())},
        {"metric": "pairs_value_decreases", "value": n_decrease},
        {"metric": "companies_showing_a_decrease", "value": companies_with_decrease},
        {"metric": "pairs_same_day_conflicting_value", "value": n_same_day_conflict},
        {"metric": "company_year_groups_with_more_than_one_row",
         "value": multi_row_year_groups},
        {"metric": "company_year_groups_with_multiple_distinct_values",
         "value": year_groups_multi_value},
        {"metric": "pairs_outside_elapsed_time_tolerance", "value": n_implausible},
        {"metric": "companies_outside_elapsed_time_tolerance", "value": companies_implausible},
    ])

    resid_stats = numeric_summary(pd.Series(residual)) if n_pairs else numeric_summary(pd.Series([], dtype=float))
    facts = {
        "value_col": value_col,
        "tolerance": tolerance,
        "n_pairs": n_pairs,
        "n_increase": int(increases.sum()),
        "n_flat": int(flat.sum()),
        "n_decrease": n_decrease,
        "pct_decrease": pct(n_decrease, n_pairs),
        "pct_increase": pct(int(increases.sum()), n_pairs),
        "pct_flat": pct(int(flat.sum()), n_pairs),
        "companies_with_decrease": companies_with_decrease,
        "n_same_day_conflict": n_same_day_conflict,
        "multi_row_year_groups": multi_row_year_groups,
        "year_groups_multi_value": year_groups_multi_value,
        "pct_year_groups_multi_value": pct(year_groups_multi_value, multi_row_year_groups),
        "n_implausible": n_implausible,
        "pct_implausible": pct(n_implausible, n_pairs),
        "companies_implausible": companies_implausible,
        "repeated_one_value": int((rep == 1).sum()),
        "repeated_multi_value": int((rep > 1).sum()),
        "pct_repeated_one_value": pct(int((rep == 1).sum()), int(rep.size)),
        "max_distinct_one_company": int(per_company.max()),
        "residual_min": resid_stats["min"],
        "residual_max": resid_stats["max"],
        "residual_mean": resid_stats["mean"],
        "residual_median": resid_stats["median"],
        "max_decrease": float(pair_dv.min()) if n_pairs else np.nan,
        "max_elapsed_days": float(pair_dd.max()) if n_pairs else np.nan,
    }
    return {"summary": summary, "facts": facts}


def audit_company_age_time(df, ccodes, n_companies, posting_count) -> dict:
    return _time_series_consistency(df, ccodes, n_companies, "company_age",
                                    DAYS_PER_YEAR, AGE_YEAR_TOLERANCE, posting_count)


def audit_domain_age_time(df, ccodes, n_companies, posting_count) -> dict:
    return _time_series_consistency(df, ccodes, n_companies, "domain_age_months",
                                    DAYS_PER_MONTH, DOMAIN_MONTH_TOLERANCE, posting_count)


# --------------------------------------------------------------------------
# section 4 - company attribute combination test
# --------------------------------------------------------------------------
def audit_company_combination(df: pd.DataFrame, ccodes: np.ndarray,
                              n_companies: int, posting_count: np.ndarray) -> dict:
    """
    Does company_name alone determine the whole combination of the five
    company-presence attributes?
    """
    combo = np.zeros(len(df), dtype=np.int64)
    widths = []
    for col in COMPANY_COMBINATION_ATTRIBUTES:
        vcodes, n_levels = codes_of(df[col])
        widths.append(n_levels)
        combo = combo * n_levels + vcodes.astype(np.int64)
    combo_codes, combo_uniques = pd.factorize(combo)
    combo_codes = np.asarray(combo_codes).astype(np.int32)
    n_combos_observed = int(len(combo_uniques))
    n_combos_possible = int(np.prod(widths))

    per = distinct_per_group(ccodes, combo_codes, n_companies)
    repeated = posting_count > 1
    rep = per[repeated]
    one_combo_all = int((per == 1).sum())
    multi_all = int((per > 1).sum())

    counts = np.bincount(per, minlength=int(per.max()) + 1)
    dist_rows = []
    for k, c in enumerate(counts):
        if c == 0:
            continue
        sel = per == k
        dist_rows.append({
            "distinct_combinations_per_company_name": int(k),
            "company_names": int(c),
            "pct_of_company_names": pct(int(c), n_companies),
            "rows_covered": int(posting_count[sel].sum()),
            "pct_of_rows": pct(int(posting_count[sel].sum()), len(df)),
        })
    distribution = pd.DataFrame(dist_rows)

    fd = functional_dependency(df[GROUP_COLUMN],
                               pd.Series(pd.Categorical(combo_codes)))
    facts = {
        "n_companies": n_companies,
        "one_combination": one_combo_all,
        "multiple_combinations": multi_all,
        "pct_one_combination": pct(one_combo_all, n_companies),
        "repeated_one_combination": int((rep == 1).sum()),
        "repeated_multiple_combinations": int((rep > 1).sum()),
        "pct_repeated_one_combination": pct(int((rep == 1).sum()), int(rep.size)),
        "max_combinations_one_company": int(per.max()),
        "combinations_observed": n_combos_observed,
        "combinations_possible": n_combos_possible,
        "attributes": list(COMPANY_COMBINATION_ATTRIBUTES),
        "fd_holds": fd["holds"],
        "fd_violating_groups": fd["violating_groups"],
        "fd_violating_rows": fd["violating_rows"],
        "pct_rows_in_violating_groups": pct(fd["violating_rows"], len(df)),
    }
    return {"distribution": distribution, "facts": facts}


# --------------------------------------------------------------------------
# section 5 / 6 / 7 / 8 - categorical structure
# --------------------------------------------------------------------------
def tidy_crosstab(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    ct = pd.crosstab(df[a], df[b])
    tidy = ct.stack().reset_index()
    tidy.columns = [a, b, "rows"]
    tidy["pct_of_all_rows"] = tidy["rows"].map(lambda v: pct(v, len(df)))
    row_totals = ct.sum(axis=1)
    col_totals = ct.sum(axis=0)
    tidy["pct_within_" + a] = [
        pct(r["rows"], row_totals[r[a]]) for _, r in tidy.iterrows()]
    tidy["pct_within_" + b] = [
        pct(r["rows"], col_totals[r[b]]) for _, r in tidy.iterrows()]
    return tidy


def audit_title(df: pd.DataFrame) -> dict:
    """internship_title against the four placement attributes."""
    parts = []
    rows = []
    for col in TITLE_DEPENDENT_ATTRIBUTES:
        ct = pd.crosstab(df["internship_title"], df[col])
        tidy = ct.stack().reset_index()
        tidy.columns = ["internship_title", "value", "rows"]
        tidy.insert(1, "attribute", col)
        tidy["pct_within_title"] = tidy.apply(
            lambda r: pct(r["rows"], int(ct.loc[r["internship_title"]].sum())), axis=1)
        parts.append(tidy)
        v = cramers_v(ct.to_numpy())
        fd_fwd = functional_dependency(df["internship_title"], df[col])
        fd_rev = functional_dependency(df[col], df["internship_title"])
        per_title = ct.gt(0).sum(axis=1)
        rows.append({
            "left": "internship_title",
            "right": col,
            "left_levels": int(df["internship_title"].nunique()),
            "right_levels": int(df[col].nunique()),
            "observed_combinations": int((ct > 0).sum().sum()),
            "possible_combinations": int(ct.shape[0] * ct.shape[1]),
            "all_combinations_present": bool((ct > 0).all().all()),
            "cramers_v": v,
            "left_determines_right": fd_fwd["holds"],
            "right_determines_left": fd_rev["holds"],
            "min_right_values_per_left": int(per_title.min()),
            "max_right_values_per_left": int(per_title.max()),
            "min_cell_rows": int(ct.to_numpy().min()),
            "max_cell_rows": int(ct.to_numpy().max()),
        })
    crosstab = pd.concat(parts, ignore_index=True)
    title_counts = df["internship_title"].value_counts()
    title_profile = pd.DataFrame({
        "internship_title": title_counts.index.astype(str),
        "rows": title_counts.to_numpy(),
        "pct_of_rows": [pct(v, len(df)) for v in title_counts.to_numpy()],
    })
    facts = {
        "n_titles": int(df["internship_title"].nunique()),
        "min_share": float(title_profile["pct_of_rows"].min()),
        "max_share": float(title_profile["pct_of_rows"].max()),
        "max_cramers_v": max((r["cramers_v"] or 0.0) for r in rows),
        "any_determinism": any(r["left_determines_right"] or r["right_determines_left"]
                               for r in rows),
        "all_full_grids": all(r["all_combinations_present"] for r in rows),
    }
    return {"crosstab": crosstab, "profile": title_profile,
            "pairs": pd.DataFrame(rows), "facts": facts}


def audit_industry_title(df: pd.DataFrame) -> dict:
    ct = pd.crosstab(df["industry"], df["internship_title"])
    tidy = tidy_crosstab(df, "industry", "internship_title")
    titles_per_industry = ct.gt(0).sum(axis=1)
    industries_per_title = ct.gt(0).sum(axis=0)
    fwd = functional_dependency(df["industry"], df["internship_title"])
    rev = functional_dependency(df["internship_title"], df["industry"])
    v = cramers_v(ct.to_numpy())
    facts = {
        "n_industries": int(ct.shape[0]),
        "n_titles": int(ct.shape[1]),
        "cells": int(ct.shape[0] * ct.shape[1]),
        "nonzero_cells": int((ct > 0).sum().sum()),
        "all_present": bool((ct > 0).all().all()),
        "min_titles_per_industry": int(titles_per_industry.min()),
        "max_titles_per_industry": int(titles_per_industry.max()),
        "min_industries_per_title": int(industries_per_title.min()),
        "max_industries_per_title": int(industries_per_title.max()),
        "cramers_v": v,
        "industry_determines_title": fwd["holds"],
        "title_determines_industry": rev["holds"],
        "min_cell": int(ct.to_numpy().min()),
        "max_cell": int(ct.to_numpy().max()),
        "expected_cell": float(len(df) / (ct.shape[0] * ct.shape[1])),
    }
    return {"tidy": tidy, "matrix": ct, "facts": facts}


def audit_location(df: pd.DataFrame, ccodes: np.ndarray) -> dict:
    """
    Per-location profile.  stipend is deliberately NOT aggregated here: the
    currency and pay period of stipend are undocumented, and the nine cities
    sit in different currency areas, so any cross-location stipend figure
    would be arithmetic without meaning.
    """
    rows = []
    loc_codes, n_loc = codes_of(df["location"])
    categories = list(df["location"].cat.categories)
    label = df[LABEL].to_numpy()
    for k, name in enumerate(categories):
        sel = loc_codes == k
        n = int(sel.sum())
        companies = int(np.unique(ccodes[sel]).size)
        rows.append({
            "location": str(name),
            "rows": n,
            "pct_of_rows": pct(n, len(df)),
            "distinct_company_names": companies,
            "rows_per_company_name": float(n / companies) if companies else np.nan,
            "distinct_industries": int(df.loc[sel, "industry"].nunique()),
            "distinct_internship_titles": int(df.loc[sel, "internship_title"].nunique()),
            "fake_postings": int(label[sel].sum()),
            "fake_posting_rate_pct": pct(int(label[sel].sum()), n),
        })
    profile = pd.DataFrame(rows)
    industry_ct = tidy_crosstab(df, "location", "industry")
    fd_loc_ind = functional_dependency(df["location"], df["industry"])
    v = cramers_v(pd.crosstab(df["location"], df["industry"]).to_numpy())
    baseline = pct(int(label.sum()), len(df))
    facts = {
        "n_locations": n_loc,
        "baseline_fake_rate": baseline,
        "min_fake_rate": float(profile["fake_posting_rate_pct"].min()),
        "max_fake_rate": float(profile["fake_posting_rate_pct"].max()),
        "fake_rate_spread_pp": float(profile["fake_posting_rate_pct"].max()
                                     - profile["fake_posting_rate_pct"].min()),
        "min_share": float(profile["pct_of_rows"].min()),
        "max_share": float(profile["pct_of_rows"].max()),
        "min_companies": int(profile["distinct_company_names"].min()),
        "max_companies": int(profile["distinct_company_names"].max()),
        "cramers_v_location_industry": v,
        "location_determines_industry": fd_loc_ind["holds"],
        "total_company_names": int(np.unique(ccodes).size),
        "sum_location_company_names": int(profile["distinct_company_names"].sum()),
    }
    return {"profile": profile, "industry_crosstab": industry_ct, "facts": facts}


def audit_employment_work_mode(df: pd.DataFrame) -> dict:
    ct = pd.crosstab(df["employment_type"], df["work_mode"])
    tidy = tidy_crosstab(df, "employment_type", "work_mode")
    fwd = functional_dependency(df["employment_type"], df["work_mode"])
    rev = functional_dependency(df["work_mode"], df["employment_type"])
    v = cramers_v(ct.to_numpy())
    cells = int(ct.shape[0] * ct.shape[1])
    facts = {
        "employment_levels": int(ct.shape[0]),
        "work_mode_levels": int(ct.shape[1]),
        "possible_combinations": cells,
        "observed_combinations": int((ct > 0).sum().sum()),
        "all_present": bool((ct > 0).all().all()),
        "cramers_v": v,
        "employment_determines_work_mode": fwd["holds"],
        "work_mode_determines_employment": rev["holds"],
        "min_cell": int(ct.to_numpy().min()),
        "max_cell": int(ct.to_numpy().max()),
        "min_cell_pct": pct(int(ct.to_numpy().min()), len(df)),
        "max_cell_pct": pct(int(ct.to_numpy().max()), len(df)),
        "employment_shares": {str(k): pct(v2, len(df))
                              for k, v2 in df["employment_type"].value_counts().items()},
        "work_mode_shares": {str(k): pct(v2, len(df))
                             for k, v2 in df["work_mode"].value_counts().items()},
    }
    return {"tidy": tidy, "matrix": ct, "facts": facts}


# --------------------------------------------------------------------------
# section 9 - email attributes
# --------------------------------------------------------------------------
def audit_email(df: pd.DataFrame) -> dict:
    ct = pd.crosstab(df["recruiter_email_type"], df["suspicious_email_domain"])
    tidy = ct.stack().reset_index()
    tidy.columns = ["recruiter_email_type", "suspicious_email_domain", "rows"]
    tidy["pct_of_rows"] = tidy["rows"].map(lambda v: pct(v, len(df)))
    fwd = functional_dependency(df["recruiter_email_type"], df["suspicious_email_domain"])
    rev = functional_dependency(df["suspicious_email_domain"], df["recruiter_email_type"])
    v = cramers_v(ct.to_numpy())
    off_diagonal = int(((ct.to_numpy() > 0).sum()) - min(ct.shape))
    mapping = {}
    for name in ct.index:
        row = ct.loc[name]
        mapping[str(name)] = int(row.idxmax())
    facts = {
        "bijection": bool(fwd["holds"] and rev["holds"]),
        "forward_holds": fwd["holds"],
        "reverse_holds": rev["holds"],
        "forward_violating_rows": fwd["violating_rows"],
        "reverse_violating_rows": rev["violating_rows"],
        "cramers_v": v,
        "nonzero_cells": int((ct > 0).sum().sum()),
        "possible_cells": int(ct.shape[0] * ct.shape[1]),
        "off_diagonal_cells": off_diagonal,
        "mapping": mapping,
        "levels": int(ct.shape[0]),
        "cell_counts": {f"{r}|{c}": int(ct.loc[r, c]) for r in ct.index for c in ct.columns},
    }
    return {"tidy": tidy, "facts": facts}


# --------------------------------------------------------------------------
# section 10 - payment attributes
# --------------------------------------------------------------------------
def audit_payment(df: pd.DataFrame) -> dict:
    flag = df["payment_required"].to_numpy()
    fee = df["registration_fee"].to_numpy()
    derived = (fee > 0).astype(np.int8)
    flag0_fee_pos = int(((flag == 0) & (fee > 0)).sum())
    flag1_fee_zero = int(((flag == 1) & (fee == 0)).sum())
    agree = int((flag == derived).sum())
    fee_pos = fee[fee > 0]
    table = pd.DataFrame([
        {"check": "payment_required == (registration_fee > 0)",
         "rows_examined": len(df),
         "rows_agreeing": agree,
         "rows_disagreeing": len(df) - agree,
         "flag_0_with_positive_fee": flag0_fee_pos,
         "flag_1_with_zero_fee": flag1_fee_zero,
         "invariant_holds": bool(len(df) - agree == 0)},
    ])
    facts = {
        "rows": len(df),
        "agree": agree,
        "disagree": int(len(df) - agree),
        "flag0_fee_pos": flag0_fee_pos,
        "flag1_fee_zero": flag1_fee_zero,
        "holds": bool(len(df) - agree == 0),
        "flag_1_rows": int((flag == 1).sum()),
        "flag_1_pct": pct(int((flag == 1).sum()), len(df)),
        "fee_zero_rows": int((fee == 0).sum()),
        "fee_zero_pct": pct(int((fee == 0).sum()), len(df)),
        "fee_distinct": int(pd.Series(fee).nunique()),
        "fee_positive_distinct": int(pd.Series(fee_pos).nunique()),
        "fee_positive_min": int(fee_pos.min()) if fee_pos.size else 0,
        "fee_positive_max": int(fee_pos.max()) if fee_pos.size else 0,
        "fee_positive_mean": float(fee_pos.mean()) if fee_pos.size else np.nan,
        "fee_positive_median": float(np.median(fee_pos)) if fee_pos.size else np.nan,
        "fee_mean_all": float(fee.mean()),
    }
    return {"table": table, "facts": facts}


# --------------------------------------------------------------------------
# section 11 - provisional field classification
# --------------------------------------------------------------------------
def audit_field_groups(df: pd.DataFrame, ccodes: np.ndarray, n_companies: int,
                       posting_count: np.ndarray) -> dict:
    """
    Measure the evidence used to classify each field provisionally.

    The decisive measurement is company-stability: a field that takes one
    value per company_name behaves like a company attribute; a field that
    varies row by row inside the same company_name behaves like something
    recorded per posting.  Stability is measured only over company_names with
    more than one posting, because a single-row company is stable by
    construction and would inflate every figure.
    """
    repeated = posting_count > 1
    n_repeated = int(repeated.sum())
    group_of = {}
    for c in CONTENT_QUALITY_FIELDS:
        group_of[c] = "content_quality"
    for c in TRUST_COMPANY_FIELDS:
        group_of.setdefault(c, "trust_company")
    for c in FRAUD_OUTCOME_FIELDS:
        group_of.setdefault(c, "fraud_outcome")

    rows = []
    for col in STABILITY_FIELDS:
        s = df[col]
        vcodes, _ = codes_of(s)
        per = distinct_per_group(ccodes, vcodes, n_companies)
        rep = per[repeated]
        stable = int((rep == 1).sum())
        numeric = pd.api.types.is_numeric_dtype(s)
        stats = numeric_summary(s) if numeric else {}
        distinct = int(s.nunique(dropna=True))
        is_binary = numeric and distinct <= 2 and set(
            pd.unique(pd.to_numeric(s, errors="coerce").dropna())).issubset({0, 1})
        rows.append({
            "field": col,
            "group": group_of.get(col, "other"),
            "dtype": str(s.dtype),
            "distinct_values": distinct,
            "missing_rows": int(s.isna().sum()),
            "missing_pct": pct(int(s.isna().sum()), len(df)),
            "min": stats.get("min", np.nan),
            "max": stats.get("max", np.nan),
            "mean": stats.get("mean", np.nan),
            "is_binary_0_1": bool(is_binary),
            "is_constant": bool(distinct <= 1),
            "repeated_companies": n_repeated,
            "repeated_companies_stable": stable,
            "pct_stable_within_company_name": pct(stable, n_repeated),
            "max_distinct_one_company": int(per.max()),
        })
    table = pd.DataFrame(rows)
    return {"table": table, "n_repeated": n_repeated}


# --------------------------------------------------------------------------
# section 12 - grain evidence
# --------------------------------------------------------------------------
def audit_grain(df: pd.DataFrame, composites) -> dict:
    """
    Does anything contradict "one row = one internship posting"?

    The test is not whether a candidate key exists (the profiling stage
    already found none) but whether the rows that collide on a business-like
    composite are genuinely the same posting recorded twice, or two different
    postings that happen to share those attributes.
    """
    n = len(df)
    rid = df["source_row_id"]
    rid_unique = int(rid.nunique())
    rid_min, rid_max = int(rid.min()), int(rid.max())
    contiguous = bool(rid_unique == n and rid_min == 1 and rid_max == n)

    business_cols = [c for c in df.columns if c not in ("source_row_id", "_date_ordinal",
                                                        "_posting_year")]
    hashed = pd.util.hash_pandas_object(df[business_cols], index=False)
    dup_mask = hashed.duplicated(keep=False)
    n_hash_dups = int(dup_mask.sum())
    exact_duplicates = 0
    if n_hash_dups:
        sub = df.loc[dup_mask, business_cols]
        exact_duplicates = int(sub.duplicated(keep="first").sum())
    del hashed

    rows = [
        {"check": "rows_in_staging", "value": n, "note": "one physical line per row"},
        {"check": "source_row_id_distinct", "value": rid_unique,
         "note": "lineage handle, not a business key"},
        {"check": "source_row_id_contiguous_1_to_n", "value": int(contiguous), "note": ""},
        {"check": "exact_duplicate_rows_excluding_source_row_id",
         "value": exact_duplicates, "note": "full 34-attribute comparison"},
    ]
    comp_rows = []
    for cols in composites:
        sub = df[list(cols)]
        dup = int(sub.duplicated(keep="first").sum())
        distinct = n - dup
        comp_rows.append({
            "composite": " + ".join(cols),
            "attributes": len(cols),
            "distinct_combinations": distinct,
            "duplicate_rows": dup,
            "duplicate_pct": pct(dup, n),
            "is_unique_key": bool(dup == 0),
        })
        rows.append({"check": "composite_duplicate_rows: " + " + ".join(cols),
                     "value": dup, "note": "not a key" if dup else "unique"})
    table = pd.DataFrame(rows)
    composites_table = pd.DataFrame(comp_rows)
    facts = {
        "n_rows": n,
        "rid_unique": rid_unique,
        "rid_contiguous": contiguous,
        "exact_duplicates": exact_duplicates,
        "natural_key_found": any(c["is_unique_key"] for c in comp_rows),
        "narrowest_composite": comp_rows[0]["composite"] if comp_rows else "",
        "narrow_composite_dups": comp_rows[0]["duplicate_rows"] if comp_rows else 0,
        "widest_composite_dups": comp_rows[-1]["duplicate_rows"] if comp_rows else 0,
        "widest_composite": comp_rows[-1]["composite"] if comp_rows else "",
        "widest_composite_pct": comp_rows[-1]["duplicate_pct"] if comp_rows else 0.0,
        "n_dates": int(df[DATE_COLUMN].nunique()),
        "date_min": str(df[DATE_COLUMN].min()),
        "date_max": str(df[DATE_COLUMN].max()),
    }
    return {"table": table, "composites": composites_table, "facts": facts}


# --------------------------------------------------------------------------
# flag bundles - junk-dimension feasibility
# --------------------------------------------------------------------------
FLAG_BUNDLES = {
    "trust_presence_flags": ["linkedin_presence", "website_available",
                             "verification_status", "social_media_presence"],
    "fraud_flags": ["payment_required", "fake_certificate_offer",
                    "suspicious_email_domain", "unrealistic_salary_flag"],
    "employment_arrangement": ["employment_type", "work_mode"],
    "company_presence_5": COMPANY_COMBINATION_ATTRIBUTES,
    "recruiter_email_pair": ["recruiter_email_type", "suspicious_email_domain"],
}


def audit_flag_bundles(df: pd.DataFrame) -> dict:
    """
    How many distinct combinations does each candidate low-cardinality bundle
    actually take?  A bundle whose observed combination count stays small is a
    feasible junk-dimension candidate; this measures feasibility only and
    proposes nothing.
    """
    rows = []
    for name, cols in FLAG_BUNDLES.items():
        combo = np.zeros(len(df), dtype=np.int64)
        possible = 1
        for col in cols:
            vcodes, n_levels = codes_of(df[col])
            possible *= max(n_levels, 1)
            combo = combo * max(n_levels, 1) + vcodes.astype(np.int64)
        uniq, counts = np.unique(combo, return_counts=True)
        rows.append({
            "bundle": name,
            "attributes": " + ".join(cols),
            "attribute_count": len(cols),
            "possible_combinations": int(possible),
            "observed_combinations": int(uniq.size),
            "pct_of_possible_observed": pct(int(uniq.size), int(possible)),
            "largest_combination_rows": int(counts.max()),
            "largest_combination_pct": pct(int(counts.max()), len(df)),
            "smallest_combination_rows": int(counts.min()),
        })
    return {"table": pd.DataFrame(rows)}


# --------------------------------------------------------------------------
# provisional field classification (section 11)
# --------------------------------------------------------------------------
# label -> (english clause, vietnamese clause).  The clause states why the
# label was chosen; the measured numbers are appended by the builder so both
# language versions carry exactly the same figures.
LABELS = {
    "measure": ("candidate measure", "candidate measure"),
    "dimension_attribute": ("candidate dimension attribute", "candidate dimension attribute"),
    "flag": ("candidate flag", "candidate flag"),
    "outcome": ("outcome", "outcome"),
    "degenerate": ("degenerate attribute", "degenerate attribute"),
    "unresolved": ("unresolved", "unresolved"),
}

CLASSIFICATION = {
    "job_description_length": ("measure",
        "Numeric, wide range, varies row by row inside the same company_name; nothing about it is a label to slice by.",
        "Dạng số, biên độ rộng, thay đổi theo từng dòng trong cùng một company_name; không có tính chất nhãn để cắt lát."),
    "grammatical_errors": ("measure",
        "A count (0-14). Additive as a count; could alternatively be banded into a dimension attribute, which is not decided here.",
        "Là một đại lượng đếm (0-14). Additive khi cộng dồn; cũng có thể chia dải thành một dimension attribute, nhưng điều đó không được quyết định ở đây."),
    "vague_description_score": ("measure",
        "Bounded 0-100 score recorded per posting; the construction rule is undocumented.",
        "Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa."),
    "urgency_score": ("measure",
        "Bounded 0-100 score recorded per posting; the construction rule is undocumented.",
        "Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa."),
    "keyword_spam_score": ("measure",
        "Bounded 0-100 score recorded per posting; the construction rule is undocumented.",
        "Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa."),
    "emotional_manipulation_score": ("measure",
        "Bounded 0-100 score recorded per posting; the construction rule is undocumented.",
        "Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa."),
    "phishing_language_score": ("measure",
        "Bounded 0-100 score recorded per posting; the construction rule is undocumented.",
        "Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa."),
    "linkedin_presence": ("flag",
        "Binary 0/1. Reads as a company property, but it is not stable across rows sharing a company_name, so it cannot be attached to a company entity on this evidence.",
        "Nhị phân 0/1. Về ngữ nghĩa giống thuộc tính công ty, nhưng không ổn định giữa các dòng cùng company_name, nên không thể gắn vào một thực thể công ty với bằng chứng hiện có."),
    "website_available": ("flag",
        "Binary 0/1. Same situation as linkedin_presence.",
        "Nhị phân 0/1. Tình huống giống linkedin_presence."),
    "verification_status": ("flag",
        "Binary 0/1. Same situation as linkedin_presence.",
        "Nhị phân 0/1. Tình huống giống linkedin_presence."),
    "social_media_presence": ("flag",
        "Binary 0/1. Same situation as linkedin_presence.",
        "Nhị phân 0/1. Tình huống giống linkedin_presence."),
    "domain_age_months": ("unresolved",
        "Numeric and company-flavoured at the same time: it would be a slowly changing company attribute if company_name were an entity key, and a per-posting measure otherwise. The instability measured below leaves both readings open.",
        "Vừa mang tính số vừa mang tính công ty: nó sẽ là một thuộc tính công ty thay đổi chậm nếu company_name là khóa thực thể, và là measure theo tin đăng nếu không. Mức bất ổn đo được bên dưới để ngỏ cả hai cách đọc."),
    "trust_signal_score": ("measure",
        "Bounded composite score, 1% missing, established by the earlier audit as NOT deterministic from the four trust flags.",
        "Điểm tổng hợp có giới hạn, thiếu 1%, audit trước đã xác lập rằng nó KHÔNG được suy ra tất định từ bốn cờ trust."),
    "unrealistic_salary_flag": ("degenerate",
        "Constant across all rows. A single-valued attribute produces a one-member dimension and cannot slice anything; it is kept in staging and its warehouse treatment is deferred.",
        "Hằng số trên toàn bộ các dòng. Một thuộc tính chỉ có một giá trị tạo ra dimension một phần tử và không cắt lát được gì; nó vẫn được giữ trong staging và cách xử lý trong warehouse được hoãn lại."),
    "payment_required": ("flag",
        "Binary 0/1, and exactly reproducible from registration_fee > 0. Storing it is a redundancy question, not an information question.",
        "Nhị phân 0/1, và tái tạo chính xác được từ registration_fee > 0. Việc lưu nó là câu hỏi về dư thừa, không phải câu hỏi về thông tin."),
    "registration_fee": ("measure",
        "Numeric and genuinely a quantity; 0 is meaningful (no fee), not a placeholder. Currency is undocumented.",
        "Dạng số và thực sự là một đại lượng; giá trị 0 có nghĩa (không thu phí), không phải giá trị thay thế. Đơn vị tiền tệ không được tài liệu hóa."),
    "fake_certificate_offer": ("flag",
        "Binary 0/1 describing what the posting offers.",
        "Nhị phân 0/1 mô tả nội dung mà tin đăng đưa ra."),
    "suspicious_email_domain": ("flag",
        "Binary 0/1, in perfect bijection with recruiter_email_type; the pair carries one attribute's worth of information.",
        "Nhị phân 0/1, song ánh hoàn hảo với recruiter_email_type; cặp này chỉ mang lượng thông tin của một thuộc tính."),
    "fraud_score": ("measure",
        "Bounded 0-100 composite; the earlier audit established it does NOT determine is_fake_posting.",
        "Điểm tổng hợp giới hạn 0-100; audit trước đã xác lập rằng nó KHÔNG quyết định is_fake_posting."),
    "is_fake_posting": ("outcome",
        "The labelled result of a posting. It is what the warehouse is built to analyse, not a slicing attribute chosen independently of it.",
        "Là kết quả được gán nhãn của một tin đăng. Đây là thứ mà warehouse được xây để phân tích, không phải một thuộc tính cắt lát chọn độc lập."),
    "company_size": ("dimension_attribute",
        "Four-valued label with no natural order; a textbook slicing attribute, subject to the company-identity problem below.",
        "Nhãn bốn giá trị không có thứ tự tự nhiên; là thuộc tính cắt lát điển hình, nhưng vướng vấn đề định danh công ty nêu bên dưới."),
    "company_age": ("unresolved",
        "Numeric, but semantically a company property measured in years. Same ambiguity as domain_age_months.",
        "Dạng số, nhưng về ngữ nghĩa là thuộc tính công ty tính bằng năm. Cùng sự nhập nhằng như domain_age_months."),
    "location": ("dimension_attribute",
        "Nine-valued label, complete and near-uniform. What it locates - work, company or recruiter - is not established by the source.",
        "Nhãn chín giá trị, đầy đủ và gần như đều. Nó định vị cái gì - nơi làm việc, công ty hay nhà tuyển dụng - không được nguồn xác lập."),
    "industry": ("dimension_attribute",
        "Nine-valued label, complete and near-uniform.",
        "Nhãn chín giá trị, đầy đủ và gần như đều."),
    "internship_title": ("dimension_attribute",
        "Nine-valued label describing the role advertised.",
        "Nhãn chín giá trị mô tả vai trò được đăng tuyển."),
    "employment_type": ("dimension_attribute",
        "Four-valued contractual label.",
        "Nhãn bốn giá trị về hình thức hợp đồng."),
    "work_mode": ("dimension_attribute",
        "Three-valued label describing where the work happens.",
        "Nhãn ba giá trị mô tả nơi thực hiện công việc."),
    "recruiter_email_type": ("dimension_attribute",
        "Two-valued label; carries the same information as suspicious_email_domain.",
        "Nhãn hai giá trị; mang cùng thông tin với suspicious_email_domain."),
    "recruiter_experience_years": ("measure",
        "Numeric level recorded per posting. There is no recruiter identifier, so it cannot be attached to a recruiter entity.",
        "Mức số ghi nhận theo từng tin đăng. Không có định danh nhà tuyển dụng nên không thể gắn vào một thực thể recruiter."),
    "recruiter_response_time_hours": ("measure",
        "Numeric duration recorded per posting; same absence of a recruiter identifier.",
        "Khoảng thời gian dạng số ghi nhận theo từng tin đăng; cũng thiếu định danh nhà tuyển dụng."),
    "stipend": ("unresolved",
        "Numeric, but currency and pay period are undocumented, so it cannot yet be called a measure of anything specific.",
        "Dạng số, nhưng đơn vị tiền tệ và kỳ trả không được tài liệu hóa, nên chưa thể gọi nó là measure của một đại lượng cụ thể nào."),
    "is_future_posting": ("flag",
        "Staging-derived data-quality marker against a fixed reference date; not a business attribute.",
        "Cờ đánh dấu chất lượng dữ liệu sinh ở staging so với một ngày tham chiếu cố định; không phải thuộc tính nghiệp vụ."),
}


def build_field_classification(field_table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in field_table.iterrows():
        col = r["field"]
        label, en, vi = CLASSIFICATION.get(
            col, ("unresolved", "No classification rule defined.", "Chưa có quy tắc phân loại."))
        rows.append({
            "field": col,
            "group": r["group"],
            "provisional_class": LABELS[label][0],
            "distinct_values": int(r["distinct_values"]),
            "missing_pct": float(r["missing_pct"]),
            "pct_stable_within_company_name": float(r["pct_stable_within_company_name"]),
            "max_distinct_one_company_name": int(r["max_distinct_one_company"]),
            "is_binary_0_1": bool(r["is_binary_0_1"]),
            "is_constant": bool(r["is_constant"]),
            "evidence_en": en,
            "evidence_vi": vi,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# candidate dimensions and measures (sections 13 / 14)
# --------------------------------------------------------------------------
def bi(en: str, vi: str) -> dict:
    return {"en": en, "vi": vi}


def build_candidate_dimensions(F: dict) -> list[dict]:
    """
    Candidate groupings, each justified by a measured number.  These are
    candidates for later review, not a schema.  Both language strings are
    written side by side and share the same formatted figures.
    """
    cc = F["company"]
    cmb = F["combination"]
    tt = F["title"]
    it = F["industry_title"]
    lo = F["location"]
    ew = F["employment"]
    em = F["email"]
    gr = F["grain"]
    ca = F["company_age"]
    da = F["domain_age"]
    fb = F["bundles"]

    n_dates, d_min, d_max = i(gr["n_dates"]), gr["date_min"], gr["date_max"]

    out = []
    out.append(dict(
        name=bi("Date", "Date"),
        attributes=["posting_date", "is_future_posting"],
        attributes_note=bi("plus calendar attributes derived from posting_date "
                           "(year, quarter, month, day of week)",
                           "cộng các thuộc tính lịch dẫn xuất từ posting_date "
                           "(năm, quý, tháng, thứ trong tuần)"),
        confidence="High",
        evidence=bi(
            f"posting_date is present and parseable on all {i(cc['n_rows'])} rows, with "
            f"{n_dates} distinct dates spanning {d_min} to {d_max}. A date dimension is "
            f"generated from the calendar, not inferred from the data, so its attributes "
            f"need no evidence of stability.",
            f"posting_date có mặt và parse được trên toàn bộ {i(cc['n_rows'])} dòng, với "
            f"{n_dates} date phân biệt trải từ {d_min} đến {d_max}. Một dimension ngày được "
            f"sinh ra từ lịch chứ không suy ra từ dữ liệu, nên các thuộc tính của nó không "
            f"cần bằng chứng về tính ổn định."),
        problems=bi(
            f"{i(F['future_rows'])} rows ({f(F['future_rows_pct'])}%) are dated after the fixed "
            f"reference date 2026-09-23 and are flagged, not filtered. A date dimension must "
            f"therefore cover future dates or those rows lose their join.",
            f"{i(F['future_rows'])} dòng ({f(F['future_rows_pct'])}%) có ngày sau ngày tham chiếu "
            f"cố định 2026-09-23 và chỉ được đánh cờ, không bị lọc bỏ. Do đó dimension ngày phải "
            f"bao phủ cả các ngày tương lai, nếu không những dòng đó mất liên kết join."),
        cardinality=bi(
            f"{n_dates} rows if built at day grain over the observed range - trivially small.",
            f"{n_dates} dòng nếu xây ở grain ngày trên khoảng quan sát được - rất nhỏ."),
        time_variance=bi(
            "None. Calendar attributes of a given date do not change.",
            "Không có. Các thuộc tính lịch của một ngày cho trước không thay đổi."),
        scd=bi("Not applicable.", "Không áp dụng."),
    ))

    out.append(dict(
        name=bi("Internship / Role", "Internship / Role"),
        attributes=["internship_title"],
        attributes_note=bi("and possibly industry", "và có thể cả industry"),
        confidence="Medium",
        evidence=bi(
            f"internship_title takes {i(tt['n_titles'])} values, shares of rows from "
            f"{f(tt['min_share'])}% to {f(tt['max_share'])}%. Against industry, all "
            f"{i(it['nonzero_cells'])} of {i(it['cells'])} cells are populated and Cramer's V is "
            f"{f(it['cramers_v'], 6)}, i.e. the two vary independently.",
            f"internship_title nhận {i(tt['n_titles'])} giá trị, tỷ trọng dòng từ "
            f"{f(tt['min_share'])}% đến {f(tt['max_share'])}%. So với industry, cả "
            f"{i(it['nonzero_cells'])} trên {i(it['cells'])} ô đều có dữ liệu và Cramer's V bằng "
            f"{f(it['cramers_v'], 6)}, tức hai thuộc tính biến thiên độc lập."),
        problems=bi(
            f"internship_title does NOT determine industry ({i(it['max_industries_per_title'])} "
            f"industries per title) and industry does NOT determine internship_title "
            f"({i(it['max_titles_per_industry'])} titles per industry). Folding both into one "
            f"dimension would create a cross product of {i(it['cells'])} rows with no functional "
            f"dependency to justify it.",
            f"internship_title KHÔNG quyết định industry ({i(it['max_industries_per_title'])} "
            f"industry cho mỗi title) và industry KHÔNG quyết định internship_title "
            f"({i(it['max_titles_per_industry'])} title cho mỗi industry). Gộp cả hai vào một "
            f"dimension sẽ tạo tích Descartes {i(it['cells'])} dòng mà không có functional "
            f"dependency nào biện minh."),
        cardinality=bi(
            f"{i(tt['n_titles'])} rows alone, or {i(it['cells'])} if industry is folded in.",
            f"{i(tt['n_titles'])} dòng nếu đứng riêng, hoặc {i(it['cells'])} nếu gộp industry vào."),
        time_variance=bi(
            "The nine labels are stable strings; no attribute of a title changes over time in "
            "this extract.",
            "Chín nhãn là các chuỗi ổn định; không thuộc tính nào của một title thay đổi theo "
            "thời gian trong bản trích này."),
        scd=bi("Not needed at this cardinality if the dimension is a plain lookup of the labels.",
               "Không cần ở mức cardinality này nếu dimension chỉ là bảng tra cứu nhãn."),
    ))

    out.append(dict(
        name=bi("Company", "Company"),
        attributes=["company_name", "company_size", "company_age", "linkedin_presence",
                    "website_available", "domain_age_months", "verification_status",
                    "social_media_presence"],
        confidence="Low",
        evidence=bi(
            f"company_name is the only company handle in the dataset: {i(cc['n_companies'])} "
            f"distinct values over {i(cc['n_rows'])} rows, of which {i(cc['n_repeated'])} "
            f"({f(cc['pct_repeated'])}%) appear on more than one row, covering "
            f"{i(cc['rows_in_repeated'])} rows ({f(cc['pct_rows_in_repeated'])}%).",
            f"company_name là handle công ty duy nhất trong dataset: {i(cc['n_companies'])} "
            f"giá trị phân biệt trên {i(cc['n_rows'])} dòng, trong đó {i(cc['n_repeated'])} "
            f"({f(cc['pct_repeated'])}%) xuất hiện ở nhiều hơn một dòng, bao phủ "
            f"{i(cc['rows_in_repeated'])} dòng ({f(cc['pct_rows_in_repeated'])}%)."),
        problems=bi(
            f"Severe. Only {i(cmb['repeated_one_combination'])} of {i(cc['n_repeated'])} repeated "
            f"company_names ({f(cmb['pct_repeated_one_combination'])}%) carry a single combination "
            f"of the five presence attributes. The weakest single attribute is "
            f"{cc['lowest_stability_attribute']} at {f(cc['lowest_stability_pct'])}% stable. Either "
            f"company_name is not a company identifier, or a company's recorded attributes change "
            f"between postings; the data cannot tell the two apart.",
            f"Nghiêm trọng. Chỉ {i(cmb['repeated_one_combination'])} trong {i(cc['n_repeated'])} "
            f"company_name lặp lại ({f(cmb['pct_repeated_one_combination'])}%) mang một tổ hợp duy "
            f"nhất của năm thuộc tính hiện diện. Thuộc tính yếu nhất là "
            f"{cc['lowest_stability_attribute']} với {f(cc['lowest_stability_pct'])}% ổn định. Hoặc "
            f"company_name không phải định danh công ty, hoặc thuộc tính ghi nhận của một công ty "
            f"thay đổi giữa các lần đăng tin; dữ liệu không phân biệt được hai khả năng."),
        cardinality=bi(
            f"{i(cc['n_companies'])} members - {f(pct(cc['n_companies'], cc['n_rows']))}% of the "
            f"fact row count. A dimension at that size is close to storing the fact table twice.",
            f"{i(cc['n_companies'])} phần tử - {f(pct(cc['n_companies'], cc['n_rows']))}% số dòng "
            f"fact. Một dimension cỡ đó gần như lưu bảng fact hai lần."),
        time_variance=bi(
            f"Measured directly: of {i(ca['n_pairs'])} consecutive posting pairs inside one "
            f"company_name, company_age decreases in {i(ca['n_decrease'])} ({f(ca['pct_decrease'])}%) "
            f"and domain_age_months decreases in {i(da['n_decrease'])} ({f(da['pct_decrease'])}%). "
            f"These attributes do not behave like a monotonic company history.",
            f"Đo trực tiếp: trong {i(ca['n_pairs'])} cặp tin đăng liên tiếp cùng một company_name, "
            f"company_age giảm ở {i(ca['n_decrease'])} cặp ({f(ca['pct_decrease'])}%) và "
            f"domain_age_months giảm ở {i(da['n_decrease'])} cặp ({f(da['pct_decrease'])}%). Các "
            f"thuộc tính này không hành xử như một lịch sử công ty đơn điệu."),
        scd=bi(
            "SCD Type 2 would be the textbook answer to changing company attributes, but SCD "
            "presupposes a stable business key. There is none here, so an SCD design would "
            "version an identifier that may not identify anything.",
            "SCD Type 2 là câu trả lời kinh điển cho thuộc tính công ty thay đổi, nhưng SCD giả "
            "định có một business key ổn định. Ở đây không có, nên thiết kế SCD sẽ version hóa một "
            "định danh có thể không định danh gì cả."),
    ))

    out.append(dict(
        name=bi("Location", "Location"),
        attributes=["location"],
        confidence="Medium",
        evidence=bi(
            f"{i(lo['n_locations'])} values, each between {f(lo['min_share'])}% and "
            f"{f(lo['max_share'])}% of rows, complete on every row. Fake-posting rate runs from "
            f"{f(lo['min_fake_rate'])}% to {f(lo['max_fake_rate'])}% against a "
            f"{f(lo['baseline_fake_rate'])}% baseline - a spread of "
            f"{f(lo['fake_rate_spread_pp'])} pp.",
            f"{i(lo['n_locations'])} giá trị, mỗi giá trị chiếm từ {f(lo['min_share'])}% đến "
            f"{f(lo['max_share'])}% số dòng, đầy đủ trên mọi dòng. Tỷ lệ tin giả chạy từ "
            f"{f(lo['min_fake_rate'])}% đến {f(lo['max_fake_rate'])}% so với mức nền "
            f"{f(lo['baseline_fake_rate'])}% - chênh lệch {f(lo['fake_rate_spread_pp'])} pp."),
        problems=bi(
            "Semantic, not structural. The source does not say whether location is the work "
            "location, the company location or the recruiter location, and there is no country, "
            "region or country-code column, so no geographic hierarchy can be built from this "
            "dataset alone.",
            "Vấn đề thuộc về ngữ nghĩa, không phải cấu trúc. Nguồn không nói rõ location là nơi "
            "làm việc, địa chỉ công ty hay vị trí nhà tuyển dụng, và không có cột quốc gia, khu "
            "vực hay mã quốc gia, nên không thể xây phân cấp địa lý chỉ từ dataset này."),
        cardinality=bi(f"{i(lo['n_locations'])} rows.", f"{i(lo['n_locations'])} dòng."),
        time_variance=bi("None observed.", "Không quan sát thấy."),
        scd=bi("Not needed unless a hierarchy is imported from outside and later revised.",
               "Không cần, trừ khi nhập phân cấp từ nguồn ngoài rồi sau đó sửa đổi."),
    ))

    out.append(dict(
        name=bi("Employment / Work Arrangement", "Employment / Work Arrangement"),
        attributes=["employment_type", "work_mode"],
        confidence="High",
        evidence=bi(
            f"All {i(ew['observed_combinations'])} of {i(ew['possible_combinations'])} "
            f"employment_type x work_mode combinations occur, cell sizes from "
            f"{f(ew['min_cell_pct'])}% to {f(ew['max_cell_pct'])}% of rows, and Cramer's V is "
            f"{f(ew['cramers_v'], 6)}. Neither attribute determines the other, so the pair is a "
            f"small complete grid rather than a hierarchy.",
            f"Cả {i(ew['observed_combinations'])} trên {i(ew['possible_combinations'])} tổ hợp "
            f"employment_type x work_mode đều xuất hiện, kích thước ô từ {f(ew['min_cell_pct'])}% "
            f"đến {f(ew['max_cell_pct'])}% số dòng, và Cramer's V bằng {f(ew['cramers_v'], 6)}. "
            f"Không thuộc tính nào quyết định thuộc tính kia, nên cặp này là một lưới đầy đủ nhỏ "
            f"chứ không phải một phân cấp."),
        problems=bi(
            "Only that employment_type contains values (Full-Time, Part-Time, Contract) that sit "
            "oddly beside the word internship in a dataset about internship postings. That is a "
            "source-semantics question, not a data defect.",
            "Chỉ là employment_type chứa các giá trị (Full-Time, Part-Time, Contract) nghe không "
            "khớp với chữ internship trong một dataset về tin tuyển thực tập. Đây là câu hỏi ngữ "
            "nghĩa của nguồn, không phải lỗi dữ liệu."),
        cardinality=bi(
            f"{i(ew['possible_combinations'])} rows as a combined dimension, or "
            f"{i(ew['employment_levels'])} + {i(ew['work_mode_levels'])} as two.",
            f"{i(ew['possible_combinations'])} dòng nếu gộp thành một dimension, hoặc "
            f"{i(ew['employment_levels'])} + {i(ew['work_mode_levels'])} nếu tách đôi."),
        time_variance=bi("None observed.", "Không quan sát thấy."),
        scd=bi("Not needed.", "Không cần."),
    ))

    out.append(dict(
        name=bi("Recruiter", "Recruiter"),
        attributes=["recruiter_email_type", "suspicious_email_domain"],
        confidence="Medium",
        evidence=bi(
            f"The bijection recruiter_email_type <-> suspicious_email_domain still holds exactly "
            f"in staging: {i(em['forward_violating_rows'])} forward and "
            f"{i(em['reverse_violating_rows'])} reverse violating rows, "
            f"{i(em['nonzero_cells'])} of {i(em['possible_cells'])} cells populated, Cramer's V "
            f"{f(em['cramers_v'], 6)}. A two-row dimension is trivially cheap.",
            f"Song ánh recruiter_email_type <-> suspicious_email_domain vẫn đúng chính xác trong "
            f"staging: {i(em['forward_violating_rows'])} dòng vi phạm chiều thuận và "
            f"{i(em['reverse_violating_rows'])} dòng vi phạm chiều ngược, {i(em['nonzero_cells'])} "
            f"trên {i(em['possible_cells'])} ô có dữ liệu, Cramer's V {f(em['cramers_v'], 6)}. "
            f"Một dimension hai dòng thì cực rẻ."),
        problems=bi(
            "There is no recruiter identifier anywhere in the dataset. recruiter_experience_years "
            "and recruiter_response_time_hours therefore cannot be attached to a recruiter entity "
            "and behave as per-posting numbers. Storing both email attributes in one dimension "
            "duplicates a single attribute's information.",
            "Không có định danh nhà tuyển dụng ở bất kỳ đâu trong dataset. Do đó "
            "recruiter_experience_years và recruiter_response_time_hours không thể gắn vào một "
            "thực thể recruiter và hành xử như các con số theo từng tin đăng. Lưu cả hai thuộc "
            "tính email trong cùng một dimension là nhân đôi thông tin của một thuộc tính duy nhất."),
        cardinality=bi(f"{i(em['levels'])} rows.", f"{i(em['levels'])} dòng."),
        time_variance=bi("None observed.", "Không quan sát thấy."),
        scd=bi("Not needed.", "Không cần."),
    ))

    fraud_bundle = fb[fb["bundle"] == "fraud_flags"].iloc[0]
    trust_bundle = fb[fb["bundle"] == "trust_presence_flags"].iloc[0]
    out.append(dict(
        name=bi("Fraud / Risk attributes", "Fraud / Risk attributes"),
        attributes=["payment_required", "fake_certificate_offer",
                    "suspicious_email_domain", "unrealistic_salary_flag"],
        attributes_note=bi("and, as a separate bundle, the trust flags linkedin_presence, "
                           "website_available, verification_status and social_media_presence",
                           "và, như một bó riêng, các cờ trust linkedin_presence, "
                           "website_available, verification_status và social_media_presence"),
        confidence="Low",
        evidence=bi(
            f"The four fraud flags take {i(fraud_bundle['observed_combinations'])} of "
            f"{i(fraud_bundle['possible_combinations'])} possible combinations; the four trust "
            f"flags take {i(trust_bundle['observed_combinations'])} of "
            f"{i(trust_bundle['possible_combinations'])}. Both bundles are small enough to be "
            f"technically feasible as junk dimensions.",
            f"Bốn cờ fraud nhận {i(fraud_bundle['observed_combinations'])} trong "
            f"{i(fraud_bundle['possible_combinations'])} tổ hợp khả dĩ; bốn cờ trust nhận "
            f"{i(trust_bundle['observed_combinations'])} trong "
            f"{i(trust_bundle['possible_combinations'])}. Cả hai bó đều đủ nhỏ để khả thi về mặt "
            f"kỹ thuật như junk dimension."),
        problems=bi(
            "Feasible is not the same as correct. is_fake_posting is the analytical outcome and "
            "does not belong in a slicing dimension alongside its own predictors; "
            "unrealistic_salary_flag is constant and would add a column that never varies; "
            "suspicious_email_domain already appears in the Recruiter candidate, so the same "
            "information would be reachable by two paths.",
            "Khả thi không đồng nghĩa với đúng. is_fake_posting là kết quả phân tích và không nên "
            "nằm trong một dimension cắt lát cùng với chính các biến dự báo của nó; "
            "unrealistic_salary_flag là hằng số và sẽ thêm một cột không bao giờ biến thiên; "
            "suspicious_email_domain đã xuất hiện trong ứng viên Recruiter, nên cùng một thông tin "
            "sẽ tới được bằng hai đường."),
        cardinality=bi(
            f"{i(fraud_bundle['observed_combinations'])} and "
            f"{i(trust_bundle['observed_combinations'])} rows respectively.",
            f"Lần lượt {i(fraud_bundle['observed_combinations'])} và "
            f"{i(trust_bundle['observed_combinations'])} dòng."),
        time_variance=bi(
            "The trust flags are unstable within company_name (see the company section), which is "
            "why they are treated as posting-level flags here rather than company attributes.",
            "Các cờ trust không ổn định trong cùng company_name (xem phần công ty), đó là lý do ở "
            "đây chúng được xem là cờ mức tin đăng chứ không phải thuộc tính công ty."),
        scd=bi("Not applicable to a junk dimension of flag combinations.",
               "Không áp dụng cho một junk dimension gồm các tổ hợp cờ."),
    ))
    return out


def build_candidate_measures(F: dict, field_class: pd.DataFrame) -> list[dict]:
    """Measure candidates with an additivity classification and its evidence."""
    pay = F["payment"]
    stats = F["measure_stats"]

    def s(col, key):
        return stats.get(col, {}).get(key, np.nan)

    rows = []

    rows.append(dict(
        measure="posting_count", additivity="additive",
        basis=bi(
            f"Not a stored column: the count of fact rows, 1 per posting, "
            f"{i(F['grain']['n_rows'])} in total.",
            f"Không phải cột lưu sẵn: là số dòng fact, mỗi tin đăng 1 dòng, tổng cộng "
            f"{i(F['grain']['n_rows'])}."),
        note=bi("Sums correctly across every dimension. The safest measure in the dataset.",
                "Cộng đúng trên mọi dimension. Là measure an toàn nhất trong dataset.")))

    rows.append(dict(
        measure="registration_fee", additivity="unresolved",
        basis=bi(
            f"Range {i(s('registration_fee','min'))} to {i(s('registration_fee','max'))}, mean "
            f"{f(s('registration_fee','mean'), 6)}, {i(pay['fee_zero_rows'])} rows at 0 "
            f"({f(pay['fee_zero_pct'])}%) where 0 means no fee.",
            f"Biên độ {i(s('registration_fee','min'))} đến {i(s('registration_fee','max'))}, trung "
            f"bình {f(s('registration_fee','mean'), 6)}, {i(pay['fee_zero_rows'])} dòng bằng 0 "
            f"({f(pay['fee_zero_pct'])}%) trong đó 0 nghĩa là không thu phí."),
        note=bi(
            "Structurally additive - it is a money amount and the 0 values are real. Marked "
            "unresolved because the currency is undocumented, so a sum across the nine cities "
            "adds different units together.",
            "Về cấu trúc là additive - đây là số tiền và các giá trị 0 là thật. Đánh dấu unresolved "
            "vì đơn vị tiền tệ không được tài liệu hóa, nên tổng qua chín thành phố là cộng các đơn "
            "vị khác nhau.")))

    rows.append(dict(
        measure="stipend", additivity="unresolved",
        basis=bi(
            f"Range {i(s('stipend','min'))} to {i(s('stipend','max'))}, mean "
            f"{f(s('stipend','mean'), 4)}, median {f(s('stipend','median'), 1)}, "
            f"{i(s('stipend','missing'))} missing rows.",
            f"Biên độ {i(s('stipend','min'))} đến {i(s('stipend','max'))}, trung bình "
            f"{f(s('stipend','mean'), 4)}, trung vị {f(s('stipend','median'), 1)}, "
            f"{i(s('stipend','missing'))} dòng thiếu giá trị."),
        note=bi(
            "SEMANTICALLY UNRESOLVED. Neither the currency nor the pay period (monthly, annual, "
            "total) is documented, and rows span nine cities in different currency areas. Summing "
            "or averaging stipend across location would produce a number with no defensible "
            "meaning. No stipend figure is reported per location anywhere in this audit.",
            "CHƯA GIẢI QUYẾT VỀ NGỮ NGHĨA. Cả đơn vị tiền tệ lẫn kỳ trả (tháng, năm, trọn gói) đều "
            "không được tài liệu hóa, và các dòng trải trên chín thành phố thuộc các vùng tiền tệ "
            "khác nhau. Cộng hay lấy trung bình stipend theo location sẽ cho ra một con số không "
            "bảo vệ được về mặt ý nghĩa. Không có số liệu stipend nào theo location được báo cáo ở "
            "bất kỳ đâu trong audit này.")))

    rows.append(dict(
        measure="job_description_length", additivity="additive",
        basis=bi(
            f"Range {i(s('job_description_length','min'))} to "
            f"{i(s('job_description_length','max'))}, mean "
            f"{f(s('job_description_length','mean'), 4)}, "
            f"{i(s('job_description_length','distinct'))} distinct values.",
            f"Biên độ {i(s('job_description_length','min'))} đến "
            f"{i(s('job_description_length','max'))}, trung bình "
            f"{f(s('job_description_length','mean'), 4)}, "
            f"{i(s('job_description_length','distinct'))} giá trị phân biệt."),
        note=bi(
            "A length in characters; a total length over a set of postings is a real quantity. "
            "The average is the more useful aggregate in practice.",
            "Là độ dài tính theo ký tự; tổng độ dài trên một tập tin đăng là một đại lượng có "
            "thật. Trong thực tế, giá trị trung bình mới là tổng hợp hữu dụng hơn.")))

    rows.append(dict(
        measure="grammatical_errors", additivity="additive",
        basis=bi(
            f"Integer count from {i(s('grammatical_errors','min'))} to "
            f"{i(s('grammatical_errors','max'))}, mean {f(s('grammatical_errors','mean'), 6)}.",
            f"Số đếm nguyên từ {i(s('grammatical_errors','min'))} đến "
            f"{i(s('grammatical_errors','max'))}, trung bình {f(s('grammatical_errors','mean'), 6)}."),
        note=bi("A count of occurrences, so totals are meaningful.",
                "Là số lần xuất hiện, nên tổng có ý nghĩa.")))

    for col in ["vague_description_score", "urgency_score", "keyword_spam_score",
                "emotional_manipulation_score", "phishing_language_score"]:
        rows.append(dict(
            measure=col, additivity="non-additive",
            basis=bi(
                f"Bounded score {i(s(col,'min'))} to {i(s(col,'max'))}, "
                f"{i(s(col,'distinct'))} distinct values, mean {f(s(col,'mean'), 6)}.",
                f"Điểm có giới hạn từ {i(s(col,'min'))} đến {i(s(col,'max'))}, "
                f"{i(s(col,'distinct'))} giá trị phân biệt, trung bình {f(s(col,'mean'), 6)}."),
            note=bi(
                "A bounded score is not a quantity that accumulates: adding two scores can exceed "
                "the scale's own maximum. Only averages, medians and distributions are defensible, "
                "and even those assume the undocumented scoring rule is comparable across rows.",
                "Một điểm số có giới hạn không phải là đại lượng tích lũy: cộng hai điểm có thể "
                "vượt quá cực đại của chính thang đo. Chỉ trung bình, trung vị và phân phối là bảo "
                "vệ được, và ngay cả thế vẫn giả định rằng quy tắc chấm điểm không được tài liệu "
                "hóa là so sánh được giữa các dòng.")))

    rows.append(dict(
        measure="trust_signal_score", additivity="non-additive",
        basis=bi(
            f"Bounded composite {f(s('trust_signal_score','min'), 1)} to "
            f"{f(s('trust_signal_score','max'), 1)}, mean {f(s('trust_signal_score','mean'), 6)}, "
            f"{i(s('trust_signal_score','missing'))} missing rows.",
            f"Điểm tổng hợp có giới hạn từ {f(s('trust_signal_score','min'), 1)} đến "
            f"{f(s('trust_signal_score','max'), 1)}, trung bình "
            f"{f(s('trust_signal_score','mean'), 6)}, {i(s('trust_signal_score','missing'))} dòng "
            f"thiếu giá trị."),
        note=bi(
            "Composite and bounded, so not additive. The earlier audit established it is not "
            "reproducible from the four trust flags, so it also cannot be recomputed if dropped.",
            "Vừa tổng hợp vừa có giới hạn nên không additive. Audit trước đã xác lập rằng nó không "
            "tái tạo được từ bốn cờ trust, nên cũng không thể tính lại nếu bị bỏ đi.")))

    rows.append(dict(
        measure="fraud_score", additivity="non-additive",
        basis=bi(
            f"Bounded composite {f(s('fraud_score','min'), 1)} to {f(s('fraud_score','max'), 1)}, "
            f"mean {f(s('fraud_score','mean'), 6)}, {i(s('fraud_score','distinct'))} distinct values.",
            f"Điểm tổng hợp có giới hạn từ {f(s('fraud_score','min'), 1)} đến "
            f"{f(s('fraud_score','max'), 1)}, trung bình {f(s('fraud_score','mean'), 6)}, "
            f"{i(s('fraud_score','distinct'))} giá trị phân biệt."),
        note=bi(
            "Same reasoning as the other scores. It is also close to, but not deterministic of, "
            "is_fake_posting, so the two must not be treated as interchangeable.",
            "Lý do giống các điểm số khác. Nó cũng gần nhưng không tất định với is_fake_posting, "
            "nên hai cái không được coi là thay thế cho nhau.")))

    rows.append(dict(
        measure="recruiter_experience_years", additivity="non-additive",
        basis=bi(
            f"Range {f(s('recruiter_experience_years','min'), 1)} to "
            f"{f(s('recruiter_experience_years','max'), 1)}, mean "
            f"{f(s('recruiter_experience_years','mean'), 6)}.",
            f"Biên độ {f(s('recruiter_experience_years','min'), 1)} đến "
            f"{f(s('recruiter_experience_years','max'), 1)}, trung bình "
            f"{f(s('recruiter_experience_years','mean'), 6)}."),
        note=bi(
            "A level attached to a person, not a flow. Summing years of experience across "
            "postings counts the same recruiter repeatedly - and with no recruiter identifier, "
            "there is no way to know how often.",
            "Là một mức gắn với một con người, không phải một dòng chảy. Cộng số năm kinh nghiệm "
            "qua các tin đăng là đếm lặp cùng một nhà tuyển dụng - và vì không có định danh "
            "recruiter, không có cách nào biết lặp bao nhiêu lần.")))

    rows.append(dict(
        measure="recruiter_response_time_hours", additivity="non-additive",
        basis=bi(
            f"Range {f(s('recruiter_response_time_hours','min'), 1)} to "
            f"{f(s('recruiter_response_time_hours','max'), 1)} hours, mean "
            f"{f(s('recruiter_response_time_hours','mean'), 6)}.",
            f"Biên độ {f(s('recruiter_response_time_hours','min'), 1)} đến "
            f"{f(s('recruiter_response_time_hours','max'), 1)} giờ, trung bình "
            f"{f(s('recruiter_response_time_hours','mean'), 6)}."),
        note=bi("A duration per posting; averages are meaningful, totals are not.",
                "Là khoảng thời gian theo từng tin đăng; trung bình có ý nghĩa, tổng thì không.")))

    rows.append(dict(
        measure="company_age", additivity="semi-additive",
        basis=bi(
            f"Range {i(s('company_age','min'))} to {i(s('company_age','max'))} years, "
            f"{i(s('company_age','missing'))} missing rows, "
            f"{i(s('company_age','distinct'))} distinct values.",
            f"Biên độ {i(s('company_age','min'))} đến {i(s('company_age','max'))} năm, "
            f"{i(s('company_age','missing'))} dòng thiếu giá trị, "
            f"{i(s('company_age','distinct'))} giá trị phân biệt."),
        note=bi(
            "A stock, not a flow: it can be averaged across any dimension but never summed over "
            "time, which is the defining behaviour of a semi-additive measure. Whether it belongs "
            "in the fact at all depends on the unresolved company-identity question.",
            "Là một đại lượng tồn kho chứ không phải dòng chảy: có thể lấy trung bình theo mọi "
            "dimension nhưng không bao giờ cộng dồn theo thời gian, đúng đặc trưng của measure "
            "semi-additive. Việc nó có nên nằm trong fact hay không phụ thuộc vào câu hỏi định "
            "danh công ty còn bỏ ngỏ.")))

    rows.append(dict(
        measure="domain_age_months", additivity="semi-additive",
        basis=bi(
            f"Range {i(s('domain_age_months','min'))} to {i(s('domain_age_months','max'))} months, "
            f"{i(s('domain_age_months','distinct'))} distinct values, mean "
            f"{f(s('domain_age_months','mean'), 6)}.",
            f"Biên độ {i(s('domain_age_months','min'))} đến {i(s('domain_age_months','max'))} "
            f"tháng, {i(s('domain_age_months','distinct'))} giá trị phân biệt, trung bình "
            f"{f(s('domain_age_months','mean'), 6)}."),
        note=bi("Same reasoning as company_age.", "Lý do giống company_age.")))

    rows.append(dict(
        measure="is_fake_posting", additivity="additive",
        basis=bi(
            f"Binary outcome; {i(F['label_positive'])} positive rows "
            f"({f(F['label_rate'])}% of all rows).",
            f"Kết quả nhị phân; {i(F['label_positive'])} dòng dương "
            f"({f(F['label_rate'])}% tổng số dòng)."),
        note=bi(
            "Additive when summed as a counter of fake postings. It is the outcome being "
            "analysed, so it is listed here as a measure and NOT as a slicing attribute.",
            "Additive khi cộng như một bộ đếm số tin giả. Đây là kết quả đang được phân tích, nên "
            "nó được liệt kê ở đây như một measure và KHÔNG phải thuộc tính cắt lát.")))

    for col in ["payment_required", "fake_certificate_offer", "suspicious_email_domain",
                "linkedin_presence", "website_available", "verification_status",
                "social_media_presence"]:
        rows.append(dict(
            measure=col, additivity="additive",
            basis=bi(
                f"Binary 0/1; {i(s(col,'sum'))} rows carry 1 ({f(pct(s(col,'sum'), F['grain']['n_rows']))}%).",
                f"Nhị phân 0/1; {i(s(col,'sum'))} dòng mang giá trị 1 "
                f"({f(pct(s(col,'sum'), F['grain']['n_rows']))}%)."),
            note=bi(
                "Additive only in the narrow sense that summing the flag counts the rows where it "
                "is set. Whether it is stored as a fact counter or as a dimension attribute is a "
                "schema decision left open.",
                "Additive chỉ theo nghĩa hẹp rằng cộng cờ lại chính là đếm số dòng có cờ bật. Việc "
                "lưu nó như bộ đếm trong fact hay như thuộc tính dimension là quyết định schema "
                "còn để ngỏ.")))

    rows.append(dict(
        measure="unrealistic_salary_flag", additivity="non-additive",
        basis=bi(
            f"Constant: {i(s('unrealistic_salary_flag','distinct'))} distinct value over "
            f"{i(F['grain']['n_rows'])} rows, sum {i(s('unrealistic_salary_flag','sum'))}.",
            f"Hằng số: {i(s('unrealistic_salary_flag','distinct'))} giá trị phân biệt trên "
            f"{i(F['grain']['n_rows'])} dòng, tổng {i(s('unrealistic_salary_flag','sum'))}."),
        note=bi(
            "Its sum is 0 by construction on this extract, so aggregating it carries no "
            "information. It is neither removed nor relied upon.",
            "Tổng của nó bằng 0 theo cấu tạo trong bản trích này, nên việc tổng hợp không mang "
            "thông tin nào. Nó không bị xóa và cũng không được dựa vào.")))
    return rows


# --------------------------------------------------------------------------
# bilingual report builder
# --------------------------------------------------------------------------
class Report:
    """
    Emits one language of the report from one set of computed numbers.

    Every English sentence sits next to its Vietnamese counterpart in the same
    call, and every figure is formatted once in shared code, so the two files
    cannot drift apart in their numbers, findings or cautions.
    """

    def __init__(self, lang: str):
        self.lang = lang
        self.lines: list[str] = []

    def w(self, en: str, vi: str | None = None) -> None:
        self.lines.append(en if self.lang == "en" else (vi if vi is not None else en))

    def blank(self) -> None:
        self.lines.append("")

    def tbl(self, headers, rows, aligns=None) -> None:
        hs = [h[0] if self.lang == "en" else h[1] for h in headers]
        self.lines.extend(md_table(hs, rows, aligns))

    def text(self) -> str:
        return "\n".join(self.lines).rstrip() + "\n"


CONF = {
    "High": ("High", "Cao"),
    "Medium": ("Medium", "Trung bình"),
    "Low": ("Low", "Thấp"),
}


def build_report(lang: str, meta: dict, company: dict, cage: dict, dage: dict,
                 comb: dict, title: dict, indtitle: dict, loc: dict, empmode: dict,
                 email: dict, payment: dict, fields: dict, fieldclass: pd.DataFrame,
                 bundles: dict, grain: dict, dims: list, measures: list,
                 F: dict) -> str:
    R = Report(lang)
    cc = company["facts"]
    ca = cage["facts"]
    da = dage["facts"]
    cb = comb["facts"]
    tt = title["facts"]
    it = indtitle["facts"]
    lo = loc["facts"]
    ew = empmode["facts"]
    em = email["facts"]
    pa = payment["facts"]
    gr = grain["facts"]

    R.w("# Dimensional Consistency / Functional Dependency Audit",
        "# Audit Tính nhất quán Chiều / Phụ thuộc Hàm")
    R.blank()

    # ---------------------------------------------------------------- 1
    R.w("## 1. Purpose", "## 1. Mục đích")
    R.blank()
    R.w("This audit asks one question: **which attributes can safely be grouped "
        "together into a dimension?** It answers it with measurements, not with a "
        "design.",
        "Audit này đặt đúng một câu hỏi: **những thuộc tính nào có thể được gom an toàn "
        "vào cùng một dimension?** Và trả lời bằng phép đo, không phải bằng một thiết kế.")
    R.blank()
    R.w("Grouping attributes into a dimension is a claim about dependency. Putting "
        "`company_size` next to `company_name` claims that a company has a size; "
        "putting `industry` next to `internship_title` claims that a title belongs to "
        "an industry. Those claims are testable before any schema is drawn, and this "
        "audit tests them.",
        "Việc gom thuộc tính vào một dimension là một khẳng định về sự phụ thuộc. Đặt "
        "`company_size` cạnh `company_name` là khẳng định rằng một công ty có một quy mô; "
        "đặt `industry` cạnh `internship_title` là khẳng định rằng một title thuộc về một "
        "ngành. Những khẳng định đó kiểm chứng được trước khi vẽ bất kỳ schema nào, và "
        "audit này kiểm chứng chúng.")
    R.blank()
    R.w("**What this audit does not do.** It does not design the star schema, does not "
        "fix the grain, does not create SQL, does not choose surrogate keys, and does not "
        "decide which of two redundant columns to keep. Where the evidence is ambiguous "
        "the ambiguity is recorded rather than resolved. Sections 10 and 11 list exactly "
        "what is left open.",
        "**Những gì audit này không làm.** Nó không thiết kế star schema, không chốt grain, "
        "không tạo SQL, không chọn surrogate key, và không quyết định giữ cột nào trong hai "
        "cột dư thừa. Ở đâu bằng chứng còn mơ hồ thì sự mơ hồ được ghi nhận chứ không được "
        "giải quyết. Mục 10 và 11 liệt kê chính xác những gì còn bỏ ngỏ.")
    R.blank()
    R.w("**Reading rule.** A differing value inside a group is reported as *variation*, "
        "not as an *error*. This dataset carries no company identifier, no recruiter "
        "identifier and no posting identifier, so a disagreement between two rows may mean "
        "bad data, or it may mean the two rows were never about the same thing. Nothing "
        "below assumes which.",
        "**Nguyên tắc đọc.** Một giá trị khác biệt bên trong một nhóm được báo cáo là *biến "
        "thiên*, không phải *lỗi*. Dataset này không có định danh công ty, định danh nhà "
        "tuyển dụng hay định danh tin đăng, nên sự bất đồng giữa hai dòng có thể là dữ liệu "
        "sai, mà cũng có thể là hai dòng vốn chưa bao giờ nói về cùng một đối tượng. Không "
        "phần nào bên dưới giả định điều nào đúng.")
    R.blank()

    # ---------------------------------------------------------------- 2
    R.w("## 2. Data basis", "## 2. Cơ sở dữ liệu")
    R.blank()
    R.tbl([("Item", "Mục"), ("Value", "Giá trị")], [
        [("Source file", "File nguồn")[0 if lang == "en" else 1],
         f"`{meta['source']}`"],
        [("Rows x columns", "Số dòng x số cột")[0 if lang == "en" else 1],
         f"{i(meta['n_rows'])} x {i(meta['n_cols'])}"],
        [("File size", "Kích thước file")[0 if lang == "en" else 1],
         human_bytes(meta['fingerprint_before']['size_bytes'])],
        [("sha256 before the audit", "sha256 trước khi audit")[0 if lang == "en" else 1],
         f"`{meta['fingerprint_before']['sha256']}`"],
        [("sha256 after the audit", "sha256 sau khi audit")[0 if lang == "en" else 1],
         f"`{meta['fingerprint_after']['sha256']}`"],
        [("Staging file unchanged", "File staging không thay đổi")[0 if lang == "en" else 1],
         ("**YES**" if meta["unchanged"] else "**NO**") if lang == "en"
         else ("**CÓ**" if meta["unchanged"] else "**KHÔNG**")],
        [("Generated at", "Thời điểm tạo")[0 if lang == "en" else 1], meta["generated_at"]],
        [("Script", "Script")[0 if lang == "en" else 1],
         "`scripts/audit_dimensional_consistency.py`"],
        [("Rows analysed", "Số dòng được phân tích")[0 if lang == "en" else 1],
         i(meta["n_rows"])],
        [("posting_date range", "Khoảng posting_date")[0 if lang == "en" else 1],
         f"{gr['date_min']} -> {gr['date_max']} ({i(gr['n_dates'])} "
         + ("distinct dates)" if lang == "en" else "date phân biệt)")],
    ])
    R.w("Authoritative documentation used for the semantics of every column: "
        "`docs/data_dictionary.md` and `docs/cleaning_rules.md`. Prior evidence reused "
        "rather than re-derived: `results/profiling/`, `results/audit/`, "
        "`results/staging/`.",
        "Tài liệu chuẩn được dùng cho ngữ nghĩa của từng cột: `docs/data_dictionary.md` và "
        "`docs/cleaning_rules.md`. Bằng chứng trước đó được tái sử dụng thay vì suy lại: "
        "`results/profiling/`, `results/audit/`, `results/staging/`.")
    R.blank()
    R.w("**Integrity.** The staging CSV was opened read-only. No value was cleaned, "
        "imputed, capped, dropped, normalised, encoded, resolved or de-duplicated. Two "
        "working columns (a date ordinal and a posting year) were derived in memory for "
        "the time-series checks and were never written anywhere. The sha256 above was "
        "measured before the run started and again after every output had been written.",
        "**Tính toàn vẹn.** File CSV staging được mở ở chế độ chỉ đọc. Không giá trị nào bị "
        "làm sạch, impute, chặn ngưỡng, loại bỏ, chuẩn hóa, encode, hợp nhất thực thể hay "
        "khử trùng lặp. Hai cột làm việc (một số thứ tự ngày và một năm đăng tin) được sinh "
        "ra trong bộ nhớ để phục vụ các kiểm tra chuỗi thời gian và không bao giờ được ghi "
        "ra đâu cả. Giá trị sha256 ở trên được đo trước khi chạy và đo lại sau khi mọi kết "
        "quả đã được ghi.")
    R.blank()
    R.w("**A note on the CSV outputs.** The companion CSV files in this directory use "
        "English column names and English evidence text, because they are machine-readable "
        "artefacts shared by both language versions of this report. Every number they "
        "contain also appears in both reports.",
        "**Ghi chú về các file CSV kèm theo.** Các file CSV trong thư mục này dùng tên cột "
        "và phần diễn giải bằng tiếng Anh, vì chúng là các artefact máy đọc được dùng chung "
        "cho cả hai bản ngôn ngữ của báo cáo. Mọi con số trong đó cũng đều xuất hiện trong "
        "cả hai bản báo cáo.")
    R.blank()

    # ---------------------------------------------------------------- 3
    R.w("## 3. Company consistency", "## 3. Tính nhất quán của thực thể công ty")
    R.blank()
    R.w("### 3.1 How company_name behaves as a group",
        "### 3.1 company_name hành xử thế nào khi dùng làm khóa gom nhóm")
    R.blank()
    R.w(f"`company_name` is used here purely as a **grouping attribute**. It is not "
        f"assumed to be a company ID, and the data dictionary is explicit that no company "
        f"identifier exists in this source.",
        f"`company_name` ở đây chỉ được dùng thuần túy như một **thuộc tính gom nhóm**. Nó "
        f"không được giả định là company ID, và data dictionary nói rõ rằng nguồn này không "
        f"có định danh công ty nào.")
    R.blank()
    R.tbl([("Metric", "Chỉ số"), ("Value", "Giá trị")], [
        [("Distinct company_name values", "Số company_name phân biệt")[0 if lang == "en" else 1],
         i(cc["n_companies"])],
        [("Appearing on exactly one row", "Chỉ xuất hiện đúng một dòng")[0 if lang == "en" else 1],
         f"{i(cc['n_single'])} ({f(pct(cc['n_single'], cc['n_companies']))}%)"],
        [("Appearing on more than one row", "Xuất hiện ở nhiều hơn một dòng")[0 if lang == "en" else 1],
         f"{i(cc['n_repeated'])} ({f(cc['pct_repeated'])}%)"],
        [("Rows covered by repeated names", "Số dòng thuộc các tên lặp lại")[0 if lang == "en" else 1],
         f"{i(cc['rows_in_repeated'])} ({f(cc['pct_rows_in_repeated'])}%)"],
        [("Mean postings per company_name", "Trung bình số tin đăng mỗi company_name")[0 if lang == "en" else 1],
         f(cc["mean_postings_per_company"], 6)],
        [("Most postings for one company_name", "Số tin đăng nhiều nhất của một company_name")[0 if lang == "en" else 1],
         f"{i(cc['max_postings_one_company'])} (`{cc['max_postings_company_name']}`)"],
    ], ["---", "---:"])
    R.w("Distribution of postings per `company_name`:",
        "Phân phối số tin đăng trên mỗi `company_name`:")
    R.blank()
    R.tbl([("Postings", "Số tin đăng"), ("company_name values", "Số company_name"),
           ("% of names", "% số tên"), ("Rows covered", "Số dòng bao phủ"),
           ("% of rows", "% số dòng")],
          [[r["postings_per_company"], i(r["company_names"]),
            f(r["pct_of_company_names"]), i(r["rows_covered"]), f(r["pct_of_rows"])]
           for _, r in company["distribution"].iterrows()],
          ["---", "---:", "---:", "---:", "---:"])

    R.w("### 3.2 Stability of the dependent attributes",
        "### 3.2 Tính ổn định của các thuộc tính phụ thuộc")
    R.blank()
    R.w(f"For each attribute the table below counts, among the {i(cc['n_repeated'])} "
        f"`company_name` values that appear on more than one row, how many carry exactly "
        f"one distinct value and how many carry several. Single-row names are excluded "
        f"because they are stable by construction and would inflate every percentage "
        f"towards 100%. Missing values are excluded from the distinct-value count rather "
        f"than treated as a value of their own.",
        f"Với mỗi thuộc tính, bảng dưới đây đếm trong số {i(cc['n_repeated'])} giá trị "
        f"`company_name` xuất hiện ở nhiều hơn một dòng, bao nhiêu giá trị mang đúng một "
        f"giá trị phân biệt và bao nhiêu mang nhiều giá trị. Các tên chỉ có một dòng bị loại "
        f"khỏi phép tính vì chúng ổn định theo cấu tạo và sẽ đẩy mọi tỷ lệ về sát 100%. Giá "
        f"trị thiếu bị loại khỏi phép đếm giá trị phân biệt chứ không được coi là một giá "
        f"trị riêng.")
    R.blank()
    R.tbl([("Attribute", "Thuộc tính"),
           ("Repeated names", "Số tên lặp lại"),
           ("Exactly 1 distinct value", "Đúng 1 giá trị phân biệt"),
           ("Multiple distinct values", "Nhiều giá trị phân biệt"),
           ("% stable", "% ổn định"),
           ("Max distinct for one name", "Số giá trị phân biệt tối đa cho một tên"),
           ("Distinct in dataset", "Số giá trị phân biệt toàn dataset")],
          [[f"`{r['attribute']}`", i(r["companies_repeated"]),
            i(r["repeated_with_one_distinct_value"]),
            i(r["repeated_with_multiple_distinct_values"]),
            f(r["pct_stable_among_repeated"]),
            i(r["max_distinct_among_repeated"]),
            i(r["attribute_distinct_values_dataset"])]
           for _, r in company["table"].iterrows()],
          ["---", "---:", "---:", "---:", "---:", "---:", "---:"])
    R.w(f"The most stable attribute is `{cc['highest_stability_attribute']}` at "
        f"{f(cc['highest_stability_pct'])}%; the least stable is "
        f"`{cc['lowest_stability_attribute']}` at {f(cc['lowest_stability_pct'])}%.",
        f"Thuộc tính ổn định nhất là `{cc['highest_stability_attribute']}` với "
        f"{f(cc['highest_stability_pct'])}%; kém ổn định nhất là "
        f"`{cc['lowest_stability_attribute']}` với {f(cc['lowest_stability_pct'])}%.")
    R.blank()
    R.w("**How to read this.** A low stability percentage does **not** establish that the "
        "data is wrong. Two readings fit the same numbers equally well: either a single "
        "company genuinely changed its recorded attributes between postings, or rows "
        "sharing a `company_name` are simply different companies with the same name. The "
        "data dictionary already warns that the names follow a `<Surname> <Suffix>` "
        "pattern and that name similarity must not be read as company identity. Nothing "
        "in this dataset settles the question, and nothing here is corrected on the basis "
        "of it.",
        "**Cách đọc.** Tỷ lệ ổn định thấp **không** chứng minh rằng dữ liệu sai. Có hai cách "
        "đọc khớp với cùng các con số này như nhau: hoặc một công ty thực sự đã thay đổi "
        "thuộc tính ghi nhận giữa các lần đăng tin, hoặc các dòng cùng `company_name` đơn "
        "giản là những công ty khác nhau trùng tên. Data dictionary đã cảnh báo rằng các tên "
        "tuân theo mẫu `<Họ> <Hậu tố>` và sự giống nhau về tên không được đọc thành sự đồng "
        "nhất về công ty. Không gì trong dataset này giải quyết được câu hỏi đó, và không gì "
        "ở đây bị sửa dựa trên nó.")
    R.blank()

    R.w("### 3.3 Selected examples", "### 3.3 Một số ví dụ được chọn")
    R.blank()
    R.w("The `company_name` values below show the widest spread of distinct values across "
        "the nine attributes. They are listed as evidence to inspect, not as defects.",
        "Các giá trị `company_name` dưới đây có mức phân tán giá trị phân biệt rộng nhất "
        "trên chín thuộc tính. Chúng được liệt kê như bằng chứng để xem xét, không phải như "
        "lỗi.")
    R.blank()
    ex = company["examples"]
    short = ["size", "age", "li", "web", "dom", "ver", "soc", "loc", "ind"]
    R.tbl([("company_name", "company_name"), ("Postings", "Số tin đăng")] +
          [(f"`{c}`", f"`{c}`") for c in short],
          [[f"`{r['company_name']}`", i(r["posting_count"])] +
           [i(r[f"distinct_{c}"]) for c in COMPANY_DEPENDENT_ATTRIBUTES]
           for _, r in ex.head(12).iterrows()],
          ["---", "---:"] + ["---:"] * 9)
    R.w("Column abbreviations: `size` = `company_size`, `age` = `company_age`, `li` = "
        "`linkedin_presence`, `web` = `website_available`, `dom` = `domain_age_months`, "
        "`ver` = `verification_status`, `soc` = `social_media_presence`, `loc` = "
        "`location`, `ind` = `industry`. Each cell is the number of distinct values that "
        "`company_name` takes for that attribute.",
        "Viết tắt cột: `size` = `company_size`, `age` = `company_age`, `li` = "
        "`linkedin_presence`, `web` = `website_available`, `dom` = `domain_age_months`, "
        "`ver` = `verification_status`, `soc` = `social_media_presence`, `loc` = "
        "`location`, `ind` = `industry`. Mỗi ô là số giá trị phân biệt mà `company_name` đó "
        "nhận cho thuộc tính tương ứng.")
    R.blank()

    R.w("### 3.4 The combination test", "### 3.4 Kiểm tra tổ hợp thuộc tính")
    R.blank()
    R.w(f"Attribute-by-attribute stability is the generous test. The strict test asks "
        f"whether `company_name` alone determines the **whole combination** of "
        f"{', '.join('`' + a + '`' for a in cb['attributes'])} at once - which is exactly "
        f"what a single row in a `DimCompany` would assert.",
        f"Kiểm tra từng thuộc tính riêng lẻ là phép thử dễ dãi. Phép thử nghiêm ngặt hỏi "
        f"liệu `company_name` một mình có quyết định **toàn bộ tổ hợp** của "
        f"{', '.join('`' + a + '`' for a in cb['attributes'])} cùng lúc hay không - đó chính "
        f"là điều mà một dòng trong `DimCompany` khẳng định.")
    R.blank()
    R.tbl([("Metric", "Chỉ số"), ("Value", "Giá trị")], [
        [("Distinct combinations observed", "Số tổ hợp quan sát được")[0 if lang == "en" else 1],
         f"{i(cb['combinations_observed'])} / {i(cb['combinations_possible'])}"],
        [("company_names with exactly one combination",
          "Số company_name có đúng một tổ hợp")[0 if lang == "en" else 1],
         f"{i(cb['one_combination'])} ({f(cb['pct_one_combination'])}%)"],
        [("company_names with multiple combinations",
          "Số company_name có nhiều tổ hợp")[0 if lang == "en" else 1],
         i(cb["multiple_combinations"])],
        [("Repeated names with exactly one combination",
          "Tên lặp lại có đúng một tổ hợp")[0 if lang == "en" else 1],
         f"{i(cb['repeated_one_combination'])} / {i(cc['n_repeated'])} "
         f"({f(cb['pct_repeated_one_combination'])}%)"],
        [("Repeated names with multiple combinations",
          "Tên lặp lại có nhiều tổ hợp")[0 if lang == "en" else 1],
         i(cb["repeated_multiple_combinations"])],
        [("Max combinations for one name",
          "Số tổ hợp tối đa của một tên")[0 if lang == "en" else 1],
         i(cb["max_combinations_one_company"])],
        [("company_name -> combination is a functional dependency",
          "company_name -> tổ hợp có phải functional dependency")[0 if lang == "en" else 1],
         ("**No**" if not cb["fd_holds"] else "**Yes**") if lang == "en"
         else ("**Không**" if not cb["fd_holds"] else "**Có**")],
        [("Rows inside violating groups", "Số dòng nằm trong các nhóm vi phạm")[0 if lang == "en" else 1],
         f"{i(cb['fd_violating_rows'])} ({f(cb['pct_rows_in_violating_groups'])}%)"],
    ], ["---", "---:"])
    R.w("Distribution of the number of distinct combinations per `company_name`:",
        "Phân phối số tổ hợp phân biệt trên mỗi `company_name`:")
    R.blank()
    R.tbl([("Combinations", "Số tổ hợp"), ("company_name values", "Số company_name"),
           ("% of names", "% số tên"), ("Rows covered", "Số dòng bao phủ"),
           ("% of rows", "% số dòng")],
          [[i(r["distinct_combinations_per_company_name"]), i(r["company_names"]),
            f(r["pct_of_company_names"]), i(r["rows_covered"]), f(r["pct_of_rows"])]
           for _, r in comb["distribution"].iterrows()],
          ["---:", "---:", "---:", "---:", "---:"])
    R.w("**This is the single most consequential measurement in the audit.** It is the "
        "direct test of whether a simple `DimCompany` keyed on `company_name` is "
        "defensible, and the answer is that it is not defensible on this evidence alone. "
        "That does not make a company dimension impossible - it makes it a decision that "
        "needs a stated assumption, not a decision the data supports by itself.",
        "**Đây là phép đo có hệ quả lớn nhất trong toàn bộ audit.** Nó là phép thử trực "
        "tiếp xem một `DimCompany` đơn giản khóa theo `company_name` có bảo vệ được hay "
        "không, và câu trả lời là chỉ với bằng chứng này thì không. Điều đó không làm cho "
        "một dimension công ty trở nên bất khả thi - nó khiến việc tạo dimension đó thành "
        "một quyết định cần nêu rõ giả định, chứ không phải quyết định được dữ liệu tự nó "
        "ủng hộ.")
    R.blank()

    # ---------------------------------------------------------------- 4
    R.w("## 4. Time-varying company attributes",
        "## 4. Thuộc tính công ty biến thiên theo thời gian")
    R.blank()
    R.w("Sections 3.2 and 3.4 measured whether attributes differ. This section measures "
        "whether they differ **plausibly over calendar time**. For each `company_name` its "
        "rows are sorted by `posting_date` and consecutive postings are compared: the "
        "change in the stated age is set against the time that actually elapsed between "
        "the two postings.",
        "Mục 3.2 và 3.4 đo xem các thuộc tính có khác nhau hay không. Mục này đo xem chúng "
        "có khác nhau **một cách hợp lý theo thời gian lịch** hay không. Với mỗi "
        "`company_name`, các dòng được sắp theo `posting_date` và các tin đăng liên tiếp "
        "được so sánh: mức thay đổi của tuổi được ghi nhận được đặt cạnh khoảng thời gian "
        "thực tế đã trôi qua giữa hai tin đăng.")
    R.blank()
    R.w("### 4.1 company_age over time", "### 4.1 company_age theo thời gian")
    R.blank()
    R.tbl([("Metric", "Chỉ số"), ("Value", "Giá trị")], [
        [("Repeated company_names with one distinct company_age",
          "Tên lặp lại có một giá trị company_age")[0 if lang == "en" else 1],
         f"{i(ca['repeated_one_value'])} ({f(ca['pct_repeated_one_value'])}%)"],
        [("Repeated company_names with several",
          "Tên lặp lại có nhiều giá trị")[0 if lang == "en" else 1],
         i(ca["repeated_multi_value"])],
        [("Max distinct company_age for one name",
          "Số company_age phân biệt tối đa cho một tên")[0 if lang == "en" else 1],
         i(ca["max_distinct_one_company"])],
        [("Consecutive posting pairs examined",
          "Số cặp tin đăng liên tiếp được xét")[0 if lang == "en" else 1], i(ca["n_pairs"])],
        [("Pairs where company_age increases", "Cặp có company_age tăng")[0 if lang == "en" else 1],
         f"{i(ca['n_increase'])} ({f(ca['pct_increase'])}%)"],
        [("Pairs where it is unchanged", "Cặp có giá trị không đổi")[0 if lang == "en" else 1],
         f"{i(ca['n_flat'])} ({f(ca['pct_flat'])}%)"],
        [("Pairs where it **decreases** over time",
          "Cặp có giá trị **giảm** theo thời gian")[0 if lang == "en" else 1],
         f"**{i(ca['n_decrease'])}** ({f(ca['pct_decrease'])}%)"],
        [("company_names showing at least one decrease",
          "Số tên có ít nhất một lần giảm")[0 if lang == "en" else 1],
         i(ca["companies_with_decrease"])],
        [("Same name, same day, conflicting company_age",
          "Cùng tên, cùng ngày, company_age mâu thuẫn")[0 if lang == "en" else 1],
         i(ca["n_same_day_conflict"])],
        [("(company_name, year) groups with >1 row",
          "Nhóm (company_name, năm) có >1 dòng")[0 if lang == "en" else 1],
         i(ca["multi_row_year_groups"])],
        [("... of those, with multiple company_age values",
          "... trong đó, có nhiều giá trị company_age")[0 if lang == "en" else 1],
         f"{i(ca['year_groups_multi_value'])} ({f(ca['pct_year_groups_multi_value'])}%)"],
        [(f"Pairs outside a +/-{f(ca['tolerance'], 1)} year tolerance vs elapsed time",
          f"Cặp nằm ngoài dung sai +/-{f(ca['tolerance'], 1)} năm so với thời gian trôi qua")[0 if lang == "en" else 1],
         f"{i(ca['n_implausible'])} ({f(ca['pct_implausible'])}%)"],
        [("Largest single decrease (years)", "Mức giảm lớn nhất (năm)")[0 if lang == "en" else 1],
         f(ca["max_decrease"], 1)],
    ], ["---", "---:"])
    R.w(f"**Evidence only.** A company's age cannot fall as the calendar advances, so "
        f"{i(ca['n_decrease'])} decreasing pairs and {i(ca['year_groups_multi_value'])} "
        f"(company, year) groups holding several ages are inconsistent with `company_age` "
        f"being a property of a stable entity tracked over time. They are equally "
        f"consistent with `company_name` not identifying a single entity. **No value is "
        f"corrected, and no row is flagged as invalid.**",
        f"**Chỉ là bằng chứng.** Tuổi của một công ty không thể giảm khi lịch tiến lên, nên "
        f"{i(ca['n_decrease'])} cặp giảm và {i(ca['year_groups_multi_value'])} nhóm "
        f"(công ty, năm) chứa nhiều giá trị tuổi là không nhất quán với giả thiết rằng "
        f"`company_age` là thuộc tính của một thực thể ổn định được theo dõi theo thời gian. "
        f"Chúng cũng nhất quán không kém với giả thiết rằng `company_name` không định danh "
        f"một thực thể duy nhất. **Không giá trị nào bị sửa, và không dòng nào bị đánh dấu "
        f"là không hợp lệ.**")
    R.blank()

    R.w("### 4.2 domain_age_months over time",
        "### 4.2 domain_age_months theo thời gian")
    R.blank()
    R.tbl([("Metric", "Chỉ số"), ("Value", "Giá trị")], [
        [("Repeated company_names with one distinct domain_age_months",
          "Tên lặp lại có một giá trị domain_age_months")[0 if lang == "en" else 1],
         f"{i(da['repeated_one_value'])} ({f(da['pct_repeated_one_value'])}%)"],
        [("Repeated company_names with several",
          "Tên lặp lại có nhiều giá trị")[0 if lang == "en" else 1],
         i(da["repeated_multi_value"])],
        [("Max distinct domain_age_months for one name",
          "Số domain_age_months phân biệt tối đa cho một tên")[0 if lang == "en" else 1],
         i(da["max_distinct_one_company"])],
        [("Consecutive posting pairs examined",
          "Số cặp tin đăng liên tiếp được xét")[0 if lang == "en" else 1], i(da["n_pairs"])],
        [("Pairs where it increases over time", "Cặp tăng theo thời gian")[0 if lang == "en" else 1],
         f"{i(da['n_increase'])} ({f(da['pct_increase'])}%)"],
        [("Pairs where it is unchanged", "Cặp không đổi")[0 if lang == "en" else 1],
         f"{i(da['n_flat'])} ({f(da['pct_flat'])}%)"],
        [("Pairs where it **decreases**", "Cặp **giảm**")[0 if lang == "en" else 1],
         f"**{i(da['n_decrease'])}** ({f(da['pct_decrease'])}%)"],
        [("company_names showing at least one decrease",
          "Số tên có ít nhất một lần giảm")[0 if lang == "en" else 1],
         i(da["companies_with_decrease"])],
        [("Same name, same day, conflicting value",
          "Cùng tên, cùng ngày, giá trị mâu thuẫn")[0 if lang == "en" else 1],
         i(da["n_same_day_conflict"])],
        [(f"Pairs outside a +/-{f(da['tolerance'], 1)} month tolerance vs elapsed time",
          f"Cặp nằm ngoài dung sai +/-{f(da['tolerance'], 1)} tháng so với thời gian trôi qua")[0 if lang == "en" else 1],
         f"{i(da['n_implausible'])} ({f(da['pct_implausible'])}%)"],
        [("company_names involved in those pairs",
          "Số tên liên quan tới các cặp đó")[0 if lang == "en" else 1],
         i(da["companies_implausible"])],
        [("Largest single decrease (months)", "Mức giảm lớn nhất (tháng)")[0 if lang == "en" else 1],
         f(da["max_decrease"], 1)],
        [("Residual (change minus elapsed months): min / median / max",
          "Phần dư (mức thay đổi trừ số tháng trôi qua): nhỏ nhất / trung vị / lớn nhất")[0 if lang == "en" else 1],
         f"{f(da['residual_min'], 2)} / {f(da['residual_median'], 2)} / {f(da['residual_max'], 2)}"],
    ], ["---", "---:"])
    R.w("A domain's age in months should rise by roughly the number of months that pass "
        "between two postings. The residual column above measures exactly that gap. As "
        "with `company_age`, the observed behaviour is reported and nothing is corrected: "
        "the data dictionary already records that `domain_age_months` exceeding "
        "`company_age * 12` is **not** treated as invalid, since acquired domains, "
        "rebrands and parked registrations all produce it legitimately.",
        "Tuổi domain tính theo tháng lẽ ra phải tăng xấp xỉ bằng số tháng trôi qua giữa hai "
        "tin đăng. Cột phần dư ở trên đo đúng khoảng chênh đó. Cũng như với `company_age`, "
        "hành vi quan sát được chỉ được báo cáo và không gì bị sửa: data dictionary đã ghi "
        "nhận rằng việc `domain_age_months` vượt `company_age * 12` **không** bị coi là "
        "không hợp lệ, vì domain mua lại, đổi thương hiệu và tên miền đăng ký để đó đều tạo "
        "ra hiện tượng này một cách chính đáng.")
    R.blank()
    R.w("**Modelling consequence.** If `company_name` were adopted as a company key, both "
        "ages would be time-varying attributes of that key, which is the textbook trigger "
        "for an SCD Type 2 design. The measurements above show the variation is not "
        "monotonic and therefore does not look like an entity history, so an SCD design "
        "would be recording version changes that may not correspond to anything real. This "
        "is stated as a risk, not as a recommendation either way.",
        "**Hệ quả với mô hình hóa.** Nếu `company_name` được chọn làm khóa công ty thì cả "
        "hai giá trị tuổi sẽ là thuộc tính biến thiên theo thời gian của khóa đó, và đây "
        "đúng là dấu hiệu kinh điển dẫn tới thiết kế SCD Type 2. Nhưng các phép đo ở trên "
        "cho thấy biến thiên không đơn điệu và do đó không giống một lịch sử thực thể, nên "
        "một thiết kế SCD sẽ ghi lại những thay đổi phiên bản có thể không tương ứng với "
        "điều gì có thật. Đây được nêu như một rủi ro, không phải khuyến nghị theo hướng nào.")
    R.blank()

    # ---------------------------------------------------------------- 5
    R.w("## 5. Categorical dependencies", "## 5. Phụ thuộc giữa các thuộc tính phân loại")
    R.blank()
    R.w("### 5.1 internship_title against the placement attributes",
        "### 5.1 internship_title so với các thuộc tính vị trí công việc")
    R.blank()
    R.w("No dependency is assumed in either direction. The table reports association and "
        "cardinality only. Cramer's V is bias-corrected; a value near 0 means the two "
        "attributes vary independently.",
        "Không giả định phụ thuộc theo bất kỳ chiều nào. Bảng chỉ báo cáo mức liên hệ và "
        "cardinality. Cramer's V đã hiệu chỉnh độ chệch; giá trị gần 0 nghĩa là hai thuộc "
        "tính biến thiên độc lập.")
    R.blank()
    R.tbl([("Pair", "Cặp"), ("Levels", "Số mức"),
           ("Observed / possible cells", "Số ô quan sát / khả dĩ"),
           ("Cramer's V", "Cramer's V"),
           ("title -> attribute", "title -> thuộc tính"),
           ("attribute -> title", "thuộc tính -> title"),
           ("Values per title", "Số giá trị mỗi title")],
          [[f"`internship_title` x `{r['right']}`",
            f"{i(r['left_levels'])} x {i(r['right_levels'])}",
            f"{i(r['observed_combinations'])} / {i(r['possible_combinations'])}",
            f(r["cramers_v"], 6),
            (("yes" if r["left_determines_right"] else "no") if lang == "en"
             else ("có" if r["left_determines_right"] else "không")),
            (("yes" if r["right_determines_left"] else "no") if lang == "en"
             else ("có" if r["right_determines_left"] else "không")),
            f"{i(r['min_right_values_per_left'])}-{i(r['max_right_values_per_left'])}"]
           for _, r in title["pairs"].iterrows()],
          ["---", "---:", "---:", "---:", ":---:", ":---:", "---:"])
    R.w(f"Row shares of the {i(tt['n_titles'])} titles run from {f(tt['min_share'])}% to "
        f"{f(tt['max_share'])}%. The largest association measured is "
        f"{f(tt['max_cramers_v'], 6)}. **`internship_title` determines none of the four "
        f"attributes, and none of them determines it.** Every title x attribute grid is "
        f"fully populated, which is the pattern of independent labels rather than of a "
        f"hierarchy.",
        f"Tỷ trọng dòng của {i(tt['n_titles'])} title chạy từ {f(tt['min_share'])}% đến "
        f"{f(tt['max_share'])}%. Mức liên hệ lớn nhất đo được là {f(tt['max_cramers_v'], 6)}. "
        f"**`internship_title` không quyết định thuộc tính nào trong bốn thuộc tính, và "
        f"không thuộc tính nào quyết định nó.** Mọi lưới title x thuộc tính đều đầy đủ, đó "
        f"là dấu hiệu của các nhãn độc lập chứ không phải của một phân cấp.")
    R.blank()

    R.w("### 5.2 industry against internship_title",
        "### 5.2 industry so với internship_title")
    R.blank()
    R.tbl([("Metric", "Chỉ số"), ("Value", "Giá trị")], [
        [("Industries x titles", "Số industry x số title")[0 if lang == "en" else 1],
         f"{i(it['n_industries'])} x {i(it['n_titles'])} = {i(it['cells'])} "
         + ("cells" if lang == "en" else "ô")],
        [("Populated cells", "Số ô có dữ liệu")[0 if lang == "en" else 1],
         f"{i(it['nonzero_cells'])} ({f(pct(it['nonzero_cells'], it['cells']))}%)"],
        [("Titles per industry (min-max)", "Số title mỗi industry (nhỏ nhất-lớn nhất)")[0 if lang == "en" else 1],
         f"{i(it['min_titles_per_industry'])}-{i(it['max_titles_per_industry'])}"],
        [("Industries per title (min-max)", "Số industry mỗi title (nhỏ nhất-lớn nhất)")[0 if lang == "en" else 1],
         f"{i(it['min_industries_per_title'])}-{i(it['max_industries_per_title'])}"],
        [("Cramer's V", "Cramer's V")[0 if lang == "en" else 1], f(it["cramers_v"], 6)],
        [("industry -> internship_title", "industry -> internship_title")[0 if lang == "en" else 1],
         (("no" if not it["industry_determines_title"] else "yes") if lang == "en"
          else ("không" if not it["industry_determines_title"] else "có"))],
        [("internship_title -> industry", "internship_title -> industry")[0 if lang == "en" else 1],
         (("no" if not it["title_determines_industry"] else "yes") if lang == "en"
          else ("không" if not it["title_determines_industry"] else "có"))],
        [("Smallest / largest cell", "Ô nhỏ nhất / lớn nhất")[0 if lang == "en" else 1],
         f"{i(it['min_cell'])} / {i(it['max_cell'])}"],
        [("Expected cell under independence", "Giá trị ô kỳ vọng nếu độc lập")[0 if lang == "en" else 1],
         f(it["expected_cell"], 2)],
    ], ["---", "---:"])
    R.w(f"**No deterministic relationship exists in either direction.** Every industry "
        f"carries all {i(it['max_titles_per_industry'])} titles and every title appears in "
        f"all {i(it['max_industries_per_title'])} industries; observed cell counts sit "
        f"close to the {f(it['expected_cell'], 0)} expected under independence. The two "
        f"attributes are therefore **not** forced into a shared dimension here. Whether "
        f"they end up together is a design decision about query convenience, and it must "
        f"be made in the knowledge that it creates a {i(it['cells'])}-row cross product "
        f"with no functional dependency behind it.",
        f"**Không tồn tại quan hệ tất định theo bất kỳ chiều nào.** Mỗi industry đều chứa cả "
        f"{i(it['max_titles_per_industry'])} title và mỗi title đều xuất hiện ở cả "
        f"{i(it['max_industries_per_title'])} industry; số đếm ô quan sát được nằm sát mức "
        f"{f(it['expected_cell'], 0)} kỳ vọng khi độc lập. Do đó ở đây hai thuộc tính "
        f"**không** bị ép vào chung một dimension. Việc chúng có được gộp lại hay không là "
        f"quyết định thiết kế vì sự tiện lợi khi truy vấn, và phải được đưa ra với hiểu biết "
        f"rằng nó tạo ra một tích Descartes {i(it['cells'])} dòng không có functional "
        f"dependency nào đứng sau.")
    R.blank()

    R.w("### 5.3 location", "### 5.3 location")
    R.blank()
    R.tbl([("location", "location"), ("Rows", "Số dòng"), ("% of rows", "% số dòng"),
           ("Distinct company_names", "Số company_name phân biệt"),
           ("Rows per name", "Số dòng mỗi tên"),
           ("Industries", "Số industry"), ("Titles", "Số title"),
           ("Fake postings", "Số tin giả"), ("Fake rate %", "Tỷ lệ tin giả %")],
          [[f"`{r['location']}`", i(r["rows"]), f(r["pct_of_rows"]),
            i(r["distinct_company_names"]), f(r["rows_per_company_name"], 4),
            i(r["distinct_industries"]), i(r["distinct_internship_titles"]),
            i(r["fake_postings"]), f(r["fake_posting_rate_pct"])]
           for _, r in loc["profile"].iterrows()],
          ["---", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---:"])
    R.w(f"Fake-posting rates run from {f(lo['min_fake_rate'])}% to "
        f"{f(lo['max_fake_rate'])}% against a dataset baseline of "
        f"{f(lo['baseline_fake_rate'])}% - a spread of {f(lo['fake_rate_spread_pp'])} "
        f"percentage points. The association between `location` and `industry` is "
        f"{f(lo['cramers_v_location_industry'], 6)}.",
        f"Tỷ lệ tin giả chạy từ {f(lo['min_fake_rate'])}% đến {f(lo['max_fake_rate'])}% so "
        f"với mức nền toàn dataset {f(lo['baseline_fake_rate'])}% - chênh lệch "
        f"{f(lo['fake_rate_spread_pp'])} điểm phần trăm. Mức liên hệ giữa `location` và "
        f"`industry` là {f(lo['cramers_v_location_industry'], 6)}.")
    R.blank()
    R.w(f"Note also that the nine per-location `company_name` counts sum to "
        f"{i(lo['sum_location_company_names'])} against {i(lo['total_company_names'])} "
        f"distinct names overall - the same name appears in more than one city, which is "
        f"further evidence that `company_name` does not behave as an entity key.",
        f"Cũng lưu ý rằng tổng số `company_name` của chín thành phố là "
        f"{i(lo['sum_location_company_names'])} trong khi toàn bộ chỉ có "
        f"{i(lo['total_company_names'])} tên phân biệt - cùng một tên xuất hiện ở nhiều "
        f"thành phố, thêm một bằng chứng nữa rằng `company_name` không hành xử như một khóa "
        f"thực thể.")
    R.blank()
    R.w("> **Limitation preserved: stipend is deliberately not reported by location.** "
        "The currency and the pay period of `stipend` are undocumented in the source, and "
        "the nine cities sit in different currency areas. Any average, total or comparison "
        "of `stipend` across `location` would add or compare different units and would "
        "look authoritative while meaning nothing. This limitation is unresolved and is "
        "carried forward to sections 7, 10 and 11.",
        "> **Giới hạn được giữ nguyên: stipend cố ý không được báo cáo theo location.** Đơn "
        "vị tiền tệ và kỳ trả của `stipend` không được tài liệu hóa trong nguồn, và chín "
        "thành phố thuộc các vùng tiền tệ khác nhau. Mọi giá trị trung bình, tổng hay so "
        "sánh `stipend` theo `location` sẽ là cộng hoặc so sánh các đơn vị khác nhau, trông "
        "có vẻ đáng tin nhưng không mang ý nghĩa gì. Giới hạn này chưa được giải quyết và "
        "được chuyển tiếp sang mục 7, 10 và 11.")
    R.blank()

    R.w("### 5.4 employment_type and work_mode",
        "### 5.4 employment_type và work_mode")
    R.blank()
    mat = empmode["matrix"]
    R.tbl([("employment_type \\ work_mode", "employment_type \\ work_mode")] +
          [(str(c), str(c)) for c in mat.columns] + [("Total", "Tổng")],
          [[f"`{idx}`"] + [i(mat.loc[idx, c]) for c in mat.columns] +
           [i(int(mat.loc[idx].sum()))] for idx in mat.index] +
          [[("**Total**" if lang == "en" else "**Tổng**")] +
           [i(int(mat[c].sum())) for c in mat.columns] +
           [i(int(mat.to_numpy().sum()))]],
          ["---"] + ["---:"] * (len(mat.columns) + 1))
    R.tbl([("Metric", "Chỉ số"), ("Value", "Giá trị")], [
        [("Possible combinations", "Số tổ hợp khả dĩ")[0 if lang == "en" else 1],
         i(ew["possible_combinations"])],
        [("Observed combinations", "Số tổ hợp quan sát được")[0 if lang == "en" else 1],
         i(ew["observed_combinations"])],
        [("All combinations occur", "Mọi tổ hợp đều xuất hiện")[0 if lang == "en" else 1],
         (("**Yes**" if ew["all_present"] else "**No**") if lang == "en"
          else ("**Có**" if ew["all_present"] else "**Không**"))],
        [("Smallest / largest cell", "Ô nhỏ nhất / lớn nhất")[0 if lang == "en" else 1],
         f"{i(ew['min_cell'])} ({f(ew['min_cell_pct'])}%) / {i(ew['max_cell'])} "
         f"({f(ew['max_cell_pct'])}%)"],
        [("Cramer's V", "Cramer's V")[0 if lang == "en" else 1], f(ew["cramers_v"], 6)],
        [("employment_type -> work_mode", "employment_type -> work_mode")[0 if lang == "en" else 1],
         (("no" if not ew["employment_determines_work_mode"] else "yes") if lang == "en"
          else ("không" if not ew["employment_determines_work_mode"] else "có"))],
        [("work_mode -> employment_type", "work_mode -> employment_type")[0 if lang == "en" else 1],
         (("no" if not ew["work_mode_determines_employment"] else "yes") if lang == "en"
          else ("không" if not ew["work_mode_determines_employment"] else "có"))],
    ], ["---", "---:"])
    R.w("Neither attribute functionally determines the other and the grid is complete, so "
        "the pair is two independent labels. They can be kept as two dimensions or merged "
        "into one small combined dimension; both are defensible and neither is chosen here.",
        "Không thuộc tính nào quyết định hàm thuộc tính kia và lưới là đầy đủ, nên cặp này "
        "là hai nhãn độc lập. Có thể giữ thành hai dimension hoặc gộp thành một dimension "
        "kết hợp nhỏ; cả hai đều bảo vệ được và ở đây không chọn phương án nào.")
    R.blank()

    R.w("### 5.5 Email attributes", "### 5.5 Các thuộc tính email")
    R.blank()
    R.tbl([("Metric", "Chỉ số"), ("Value", "Giá trị")], [
        [("recruiter_email_type -> suspicious_email_domain",
          "recruiter_email_type -> suspicious_email_domain")[0 if lang == "en" else 1],
         (("holds" if em["forward_holds"] else "fails") if lang == "en"
          else ("đúng" if em["forward_holds"] else "sai"))
         + f" ({i(em['forward_violating_rows'])} "
         + ("violating rows)" if lang == "en" else "dòng vi phạm)")],
        [("suspicious_email_domain -> recruiter_email_type",
          "suspicious_email_domain -> recruiter_email_type")[0 if lang == "en" else 1],
         (("holds" if em["reverse_holds"] else "fails") if lang == "en"
          else ("đúng" if em["reverse_holds"] else "sai"))
         + f" ({i(em['reverse_violating_rows'])} "
         + ("violating rows)" if lang == "en" else "dòng vi phạm)")],
        [("Perfect bijection", "Song ánh hoàn hảo")[0 if lang == "en" else 1],
         (("**CONFIRMED**" if em["bijection"] else "**NOT CONFIRMED**") if lang == "en"
          else ("**ĐÃ XÁC NHẬN**" if em["bijection"] else "**KHÔNG XÁC NHẬN**"))],
        [("Populated cells", "Số ô có dữ liệu")[0 if lang == "en" else 1],
         f"{i(em['nonzero_cells'])} / {i(em['possible_cells'])}"],
        [("Cramer's V", "Cramer's V")[0 if lang == "en" else 1], f(em["cramers_v"], 6)],
    ], ["---", "---:"])
    R.tbl([("recruiter_email_type", "recruiter_email_type"),
           ("suspicious_email_domain", "suspicious_email_domain"),
           ("Rows", "Số dòng"), ("% of rows", "% số dòng")],
          [[f"`{r['recruiter_email_type']}`", i(r["suspicious_email_domain"]),
            i(r["rows"]), f(r["pct_of_rows"])]
           for _, r in email["tidy"].iterrows()],
          ["---", "---:", "---:", "---:"])
    R.w("**Confirmed in staging.** The bijection established by the earlier audit still "
        "holds exactly. For dimensional modelling this means that storing both attributes "
        "in the same small dimension would store one attribute's information twice: given "
        "either value, the other is known with certainty. **That redundancy is documented "
        "here, not acted on.** Dropping one of them is a schema decision, and it has a "
        "real cost - the two columns are not interchangeable in meaning, one being a "
        "human-readable label and the other a flag, and a later extract could break the "
        "bijection.",
        "**Đã xác nhận trong staging.** Song ánh mà audit trước xác lập vẫn đúng chính xác. "
        "Với mô hình hóa chiều, điều này nghĩa là lưu cả hai thuộc tính trong cùng một "
        "dimension nhỏ sẽ lưu thông tin của một thuộc tính hai lần: biết một giá trị là biết "
        "chắc giá trị kia. **Sự dư thừa đó được ghi nhận ở đây, không được xử lý.** Việc bỏ "
        "một trong hai là quyết định schema, và nó có chi phí thật - hai cột không thay thế "
        "được cho nhau về ý nghĩa, một bên là nhãn người đọc được còn một bên là cờ, và một "
        "bản trích sau này có thể phá vỡ song ánh.")
    R.blank()

    R.w("### 5.6 Payment attributes", "### 5.6 Các thuộc tính thanh toán")
    R.blank()
    R.tbl([("Check", "Kiểm tra"), ("Value", "Giá trị")], [
        [("Rows examined", "Số dòng được kiểm")[0 if lang == "en" else 1], i(pa["rows"])],
        [("payment_required == (registration_fee > 0)",
          "payment_required == (registration_fee > 0)")[0 if lang == "en" else 1],
         (("**HOLDS EXACTLY**" if pa["holds"] else "**FAILS**") if lang == "en"
          else ("**ĐÚNG CHÍNH XÁC**" if pa["holds"] else "**SAI**"))],
        [("Rows disagreeing", "Số dòng bất đồng")[0 if lang == "en" else 1], i(pa["disagree"])],
        [("payment_required = 0 with a positive fee",
          "payment_required = 0 nhưng có phí dương")[0 if lang == "en" else 1],
         i(pa["flag0_fee_pos"])],
        [("payment_required = 1 with fee = 0",
          "payment_required = 1 nhưng phí bằng 0")[0 if lang == "en" else 1],
         i(pa["flag1_fee_zero"])],
        [("Rows with payment_required = 1", "Số dòng payment_required = 1")[0 if lang == "en" else 1],
         f"{i(pa['flag_1_rows'])} ({f(pa['flag_1_pct'])}%)"],
        [("Rows with registration_fee = 0", "Số dòng registration_fee = 0")[0 if lang == "en" else 1],
         f"{i(pa['fee_zero_rows'])} ({f(pa['fee_zero_pct'])}%)"],
        [("Distinct fee values (all rows / rows with fee > 0)",
          "Số giá trị phí phân biệt (mọi dòng / dòng khác 0)")[0 if lang == "en" else 1],
         f"{i(pa['fee_distinct'])} / {i(pa['fee_positive_distinct'])}"],
        [("Fee > 0: min / median / max",
          "Phí khác 0: nhỏ nhất / trung vị / lớn nhất")[0 if lang == "en" else 1],
         f"{i(pa['fee_positive_min'])} / {f(pa['fee_positive_median'], 1)} / "
         f"{i(pa['fee_positive_max'])}"],
    ], ["---", "---:"])
    R.w("**Confirmed again on staging.** Structurally the two columns are not the same "
        "kind of thing: `payment_required` is a **flag** with two states, suited to being "
        "a dimension attribute or a junk-dimension member, while `registration_fee` is a "
        "**numeric amount** that can be summed and averaged, suited to being a fact "
        "measure. The flag is a coarsening of the amount - it can always be recomputed "
        "from it, but the amount can never be recovered from the flag.",
        "**Đã xác nhận lại trên staging.** Về cấu trúc, hai cột không cùng một loại: "
        "`payment_required` là một **cờ** hai trạng thái, phù hợp làm thuộc tính dimension "
        "hoặc phần tử của junk dimension, trong khi `registration_fee` là một **lượng số** "
        "có thể cộng và lấy trung bình, phù hợp làm measure trong fact. Cờ là dạng thô hóa "
        "của lượng - luôn tính lại được từ lượng, nhưng lượng thì không bao giờ khôi phục "
        "được từ cờ.")
    R.blank()
    R.w("**Neither column is removed and no decision is made here** about whether one is "
        "stored as a measure, the other as a derived field, or both are kept. That choice "
        "belongs to the star-schema stage and is listed in section 10.",
        "**Không cột nào bị xóa và không quyết định nào được đưa ra ở đây** về việc lưu cột "
        "nào như measure, cột nào như trường dẫn xuất, hay giữ cả hai. Lựa chọn đó thuộc về "
        "giai đoạn star schema và được liệt kê ở mục 10.")
    R.blank()

    R.w("### 5.7 Low-cardinality bundles", "### 5.7 Các bó thuộc tính cardinality thấp")
    R.blank()
    R.w("How many combinations each candidate bundle actually takes. A small observed "
        "count means a junk dimension is technically feasible; it says nothing about "
        "whether one is appropriate.",
        "Mỗi bó ứng viên thực sự nhận bao nhiêu tổ hợp. Số tổ hợp quan sát được nhỏ nghĩa "
        "là một junk dimension khả thi về mặt kỹ thuật; điều đó không nói gì về việc có nên "
        "dùng hay không.")
    R.blank()
    R.tbl([("Bundle", "Bó"), ("Attributes", "Thuộc tính"),
           ("Observed / possible", "Quan sát / khả dĩ"),
           ("Largest combination", "Tổ hợp lớn nhất")],
          [[f"`{r['bundle']}`", f"`{r['attributes']}`",
            f"{i(r['observed_combinations'])} / {i(r['possible_combinations'])}",
            f"{i(r['largest_combination_rows'])} ({f(r['largest_combination_pct'])}%)"]
           for _, r in bundles["table"].iterrows()],
          ["---", "---", "---:", "---:"])

    # ---------------------------------------------------------------- 6
    R.w("## 6. Candidate dimensions", "## 6. Các dimension ứng viên")
    R.blank()
    R.w("### 6.1 Provisional field classification",
        "### 6.1 Phân loại tạm thời cho từng trường")
    R.blank()
    R.w("Each field in the three logical groups named in the brief - content quality, "
        "trust/company, and fraud/outcome - is classified **provisionally**. No dimension "
        "is created from a group merely because its members sound related. The column "
        "*% stable* is the share of multi-row `company_name` values for which the field "
        "takes a single distinct value; it is the main evidence separating company "
        "attributes from posting-level values.",
        "Mỗi trường trong ba nhóm logic mà đề bài nêu - chất lượng nội dung, trust/công ty, "
        "và gian lận/kết quả - được phân loại **tạm thời**. Không dimension nào được tạo ra "
        "từ một nhóm chỉ vì các thành viên nghe có vẻ liên quan. Cột *% ổn định* là tỷ lệ "
        "các `company_name` nhiều dòng mà tại đó trường chỉ nhận một giá trị phân biệt; đây "
        "là bằng chứng chính để tách thuộc tính công ty khỏi giá trị mức tin đăng.")
    R.blank()
    for group, gname_en, gname_vi in [
            ("content_quality", "Content quality", "Chất lượng nội dung"),
            ("trust_company", "Trust / company", "Trust / công ty"),
            ("fraud_outcome", "Fraud / outcome", "Gian lận / kết quả")]:
        sub = fieldclass[fieldclass["group"] == group]
        R.w(f"**{gname_en}**", f"**{gname_vi}**")
        R.blank()
        R.tbl([("Field", "Trường"), ("Provisional class", "Phân loại tạm thời"),
               ("Distinct", "Số giá trị phân biệt"), ("Missing %", "% thiếu"),
               ("% stable within company_name", "% ổn định trong company_name"),
               ("Evidence", "Bằng chứng")],
              [[f"`{r['field']}`", f"**{r['provisional_class']}**",
                i(r["distinct_values"]), f(r["missing_pct"]),
                f(r["pct_stable_within_company_name"]),
                r["evidence_en"] if lang == "en" else r["evidence_vi"]]
               for _, r in sub.iterrows()],
              ["---", "---", "---:", "---:", "---:", "---"])
    R.w("Fields outside the three groups, classified on the same evidence:",
        "Các trường ngoài ba nhóm trên, phân loại theo cùng bằng chứng:")
    R.blank()
    other = fieldclass[~fieldclass["group"].isin(
        ["content_quality", "trust_company", "fraud_outcome"])]
    R.tbl([("Field", "Trường"), ("Provisional class", "Phân loại tạm thời"),
           ("Distinct", "Số giá trị phân biệt"), ("Missing %", "% thiếu"),
           ("% stable within company_name", "% ổn định trong company_name"),
           ("Evidence", "Bằng chứng")],
          [[f"`{r['field']}`", f"**{r['provisional_class']}**",
            i(r["distinct_values"]), f(r["missing_pct"]),
            f(r["pct_stable_within_company_name"]),
            r["evidence_en"] if lang == "en" else r["evidence_vi"]]
           for _, r in other.iterrows()],
          ["---", "---", "---:", "---:", "---:", "---"])

    R.w("### 6.2 Candidate dimension groups", "### 6.2 Các nhóm dimension ứng viên")
    R.blank()
    R.w("**These are candidates for later review. No star schema is proposed, and the "
        "list below is not a design.** Confidence states how well the evidence supports "
        "the grouping, not how useful the dimension would be.",
        "**Đây là các ứng viên để xem xét về sau. Không star schema nào được đề xuất, và "
        "danh sách dưới đây không phải một thiết kế.** Mức tin cậy nói lên bằng chứng ủng hộ "
        "cách gom nhóm đến đâu, không phải dimension đó sẽ hữu ích đến mức nào.")
    R.blank()
    for d in dims:
        R.w(f"#### {d['name']['en']} - confidence: **{CONF[d['confidence']][0]}**",
            f"#### {d['name']['vi']} - mức tin cậy: **{CONF[d['confidence']][1]}**")
        R.blank()
        R.tbl([("Aspect", "Khía cạnh"), ("Finding", "Kết luận")], [
            [("Possible attributes", "Thuộc tính có thể đưa vào")[0 if lang == "en" else 1],
             "`" + "`, `".join(d["attributes"]) + "`"
             + (" - " + d["attributes_note"][lang] if d.get("attributes_note") else "")],
            [("Evidence supporting the grouping",
              "Bằng chứng ủng hộ cách gom nhóm")[0 if lang == "en" else 1],
             d["evidence"][lang]],
            [("Consistency problems", "Vấn đề về tính nhất quán")[0 if lang == "en" else 1],
             d["problems"][lang]],
            [("Cardinality concerns", "Lo ngại về cardinality")[0 if lang == "en" else 1],
             d["cardinality"][lang]],
            [("Time-variance concerns", "Lo ngại về biến thiên theo thời gian")[0 if lang == "en" else 1],
             d["time_variance"][lang]],
            [("SCD consideration", "Cân nhắc về SCD")[0 if lang == "en" else 1], d["scd"][lang]],
            [("Confidence", "Mức tin cậy")[0 if lang == "en" else 1],
             f"**{CONF[d['confidence']][0 if lang == 'en' else 1]}**"],
        ], ["---", "---"])

    # ---------------------------------------------------------------- 7
    R.w("## 7. Candidate measures", "## 7. Các measure ứng viên")
    R.blank()
    R.w("Additivity is classified per candidate. **Scores are not treated as additive by "
        "default**: a bounded score is not a quantity that accumulates, and summing two "
        "scores can exceed the maximum of the scale they are drawn from.",
        "Tính additive được phân loại cho từng ứng viên. **Các điểm số không mặc định được "
        "coi là additive**: một điểm số có giới hạn không phải đại lượng tích lũy, và cộng "
        "hai điểm có thể vượt quá cực đại của chính thang đo.")
    R.blank()
    R.tbl([("Measure candidate", "Measure ứng viên"), ("Additivity", "Tính additive"),
           ("Measured basis", "Cơ sở đo được"), ("Why", "Vì sao")],
          [[f"`{m['measure']}`", f"**{m['additivity']}**", m["basis"][lang], m["note"][lang]]
           for m in measures],
          ["---", "---", "---", "---"])
    R.w("> **`stipend` remains semantically unresolved.** It is listed as a measure "
        "candidate because it is numeric, but neither its currency nor its pay period "
        "(monthly, annual or total) is documented, so what it measures is unknown. Until "
        "that is settled, no aggregate of `stipend` - and in particular no comparison "
        "across `location` - can be defended.",
        "> **`stipend` vẫn chưa được giải quyết về ngữ nghĩa.** Nó được liệt kê như measure "
        "ứng viên vì nó là số, nhưng cả đơn vị tiền tệ lẫn kỳ trả (tháng, năm hay trọn gói) "
        "đều không được tài liệu hóa, nên không rõ nó đo cái gì. Chừng nào điều đó chưa được "
        "làm rõ, không phép tổng hợp nào của `stipend` - và đặc biệt là không phép so sánh "
        "nào theo `location` - bảo vệ được.")
    R.blank()

    # ---------------------------------------------------------------- 8
    R.w("## 8. Grain evidence", "## 8. Bằng chứng về grain")
    R.blank()
    R.w("The proposition under test is: **one row represents one internship posting.** "
        "It is evaluated, not adopted.",
        "Mệnh đề được kiểm chứng là: **một dòng đại diện cho một tin tuyển thực tập.** Nó "
        "được đánh giá, chứ không được chấp nhận sẵn.")
    R.blank()
    R.w("**Evidence supporting this grain**", "**Bằng chứng ủng hộ grain này**")
    R.blank()
    R.tbl([("Evidence", "Bằng chứng"), ("Value", "Giá trị")], [
        [("Rows in staging", "Số dòng trong staging")[0 if lang == "en" else 1], i(gr["n_rows"])],
        [("Exact duplicate rows (all 34 business attributes)",
          "Số dòng trùng lặp hoàn toàn (cả 34 thuộc tính nghiệp vụ)")[0 if lang == "en" else 1],
         i(gr["exact_duplicates"])],
        [("source_row_id distinct values", "Số giá trị source_row_id phân biệt")[0 if lang == "en" else 1],
         i(gr["rid_unique"])],
        [("source_row_id contiguous 1..N", "source_row_id liên tục 1..N")[0 if lang == "en" else 1],
         (("yes" if gr["rid_contiguous"] else "no") if lang == "en"
          else ("có" if gr["rid_contiguous"] else "không"))],
        [("Every row carries a posting_date, a title, a company_name and a location",
          "Mọi dòng đều có posting_date, title, company_name và location")[0 if lang == "en" else 1],
         ("yes" if lang == "en" else "có")],
    ], ["---", "---:"])
    R.w(f"No two rows are identical across all business attributes "
        f"({i(gr['exact_duplicates'])} exact duplicates), so no row is a redundant copy of "
        f"another, and every row carries a complete set of posting-describing attributes. "
        f"Nothing measured in this audit contradicts the posting-level grain.",
        f"Không có hai dòng nào giống hệt nhau trên toàn bộ thuộc tính nghiệp vụ "
        f"({i(gr['exact_duplicates'])} bản trùng tuyệt đối), nên không dòng nào là bản sao "
        f"thừa của dòng khác, và mọi dòng đều mang đủ bộ thuộc tính mô tả một tin đăng. "
        f"Không phép đo nào trong audit này mâu thuẫn với grain mức tin đăng.")
    R.blank()
    R.w("**Absence of a natural posting ID**", "**Không có ID tin đăng tự nhiên**")
    R.blank()
    R.tbl([("Composite tested", "Tổ hợp được kiểm"), ("Attributes", "Số thuộc tính"),
           ("Distinct combinations", "Số tổ hợp phân biệt"),
           ("Duplicate rows", "Số dòng trùng"), ("% of rows", "% số dòng"),
           ("Unique key", "Là khóa duy nhất")],
          [[f"`{r['composite']}`", i(r["attributes"]), i(r["distinct_combinations"]),
            i(r["duplicate_rows"]), f(r["duplicate_pct"]),
            (("yes" if r["is_unique_key"] else "no") if lang == "en"
             else ("có" if r["is_unique_key"] else "không"))]
           for _, r in grain["composites"].iterrows()],
          ["---", "---:", "---:", "---:", "---:", ":---:"])
    if gr["natural_key_found"]:
        R.w(f"**There is no declared posting identifier in this dataset.** A wide composite "
            f"of business attributes does happen to be unique on this extract - the widest "
            f"tested (`{gr['widest_composite']}`) leaves {i(gr['widest_composite_dups'])} "
            f"duplicate rows ({f(gr['widest_composite_pct'])}%). Uniqueness that holds by "
            f"accident on one extract is not a key: nothing in the source guarantees it, and "
            f"one collision in a later load would break it. It must not be adopted as the "
            f"fact table's key on this evidence.",
            f"**Dataset này không có định danh tin đăng nào được khai báo.** Một tổ hợp rộng "
            f"các thuộc tính nghiệp vụ tình cờ là duy nhất trên bản trích này - tổ hợp rộng "
            f"nhất được kiểm (`{gr['widest_composite']}`) để lại "
            f"{i(gr['widest_composite_dups'])} dòng trùng "
            f"({f(gr['widest_composite_pct'])}%). Tính duy nhất xảy ra ngẫu nhiên trên một "
            f"bản trích thì không phải là khóa: nguồn không bảo đảm điều đó, và chỉ một va "
            f"chạm ở lần nạp sau là đủ phá vỡ. Không được lấy nó làm khóa cho bảng fact với "
            f"bằng chứng hiện có.")
    else:
        R.w(f"**There is no natural posting identifier in this dataset, and no composite of "
            f"business attributes is unique.** Even the widest composite tested "
            f"(`{gr['widest_composite']}`) still produces duplicates: "
            f"{i(gr['widest_composite_dups'])} of {i(gr['n_rows'])} rows "
            f"({f(gr['widest_composite_pct'])}%). A row therefore cannot be addressed by "
            f"its business content alone.",
            f"**Dataset này không có định danh tin đăng tự nhiên, và không tổ hợp thuộc tính "
            f"nghiệp vụ nào là duy nhất.** Ngay cả tổ hợp rộng nhất được kiểm "
            f"(`{gr['widest_composite']}`) vẫn tạo ra trùng lặp: "
            f"{i(gr['widest_composite_dups'])} trên {i(gr['n_rows'])} dòng "
            f"({f(gr['widest_composite_pct'])}%). Do đó không thể định vị một dòng chỉ "
            f"bằng nội dung nghiệp vụ của nó.")
    R.blank()
    R.w("**The role of `source_row_id`**", "**Vai trò của `source_row_id`**")
    R.blank()
    R.w("`source_row_id` is a staging-derived **lineage handle only**. It is the position "
        "of the row in the original extract, meaningful only together with that file's "
        "sha256. It is not a business key, not a posting ID, and not an ordering with "
        "analytic significance; the same value in a different extract refers to a "
        "different posting. It can therefore support traceability back to the source, but "
        "it cannot be used to decide whether two rows describe the same posting, and it "
        "must not be reused as a surrogate key in the warehouse without that decision "
        "being made explicitly.",
        "`source_row_id` chỉ là một **handle truy vết nguồn gốc** sinh ra ở staging. Nó là "
        "vị trí của dòng trong bản trích gốc, chỉ có nghĩa khi đi kèm sha256 của file đó. Nó "
        "không phải business key, không phải ID tin đăng, và không phải một thứ tự có ý "
        "nghĩa phân tích; cùng một giá trị ở một bản trích khác trỏ tới một tin đăng khác. "
        "Do đó nó hỗ trợ truy vết ngược về nguồn, nhưng không thể dùng để quyết định hai "
        "dòng có mô tả cùng một tin đăng hay không, và không được tái sử dụng làm surrogate "
        "key trong warehouse nếu quyết định đó chưa được nêu rõ ràng.")
    R.blank()
    R.w("**Unresolved concerns**", "**Những băn khoăn chưa giải quyết**")
    R.blank()
    R.w(f"1. Without a posting ID, \"one row = one posting\" cannot be *proved*; it can "
        f"only be shown to be un-contradicted. Two genuinely distinct postings and one "
        f"posting loaded twice would look the same to every test available here.\n"
        f"2. Rows that collide on a business composite are where this matters most: the "
        f"narrowest composite tested leaves {i(gr['narrow_composite_dups'])} such rows and "
        f"the widest leaves {i(gr['widest_composite_dups'])}. The data cannot say which "
        f"reading is right for any of them.\n"
        f"3. The company-identity problem in section 3 sits underneath this: if "
        f"`company_name` does not identify a company, then \"the same company posting "
        f"twice\" is not an observable event in this dataset.\n"
        f"4. The grain is therefore **not finalised here.** It is recorded as plausible "
        f"and un-contradicted, pending the questions in section 11.",
        f"1. Không có ID tin đăng thì \"một dòng = một tin đăng\" không thể được *chứng "
        f"minh*; chỉ có thể cho thấy nó không bị bác bỏ. Hai tin đăng thực sự khác nhau và "
        f"một tin đăng bị nạp hai lần sẽ trông giống hệt nhau dưới mọi phép thử khả dụng ở "
        f"đây.\n"
        f"2. Các dòng va chạm trên một tổ hợp nghiệp vụ là nơi điều này quan trọng nhất: tổ "
        f"hợp hẹp nhất được kiểm để lại {i(gr['narrow_composite_dups'])} dòng như vậy và tổ "
        f"hợp rộng nhất để lại {i(gr['widest_composite_dups'])}. Dữ liệu không thể nói cách đọc "
        f"nào là đúng.\n"
        f"3. Vấn đề định danh công ty ở mục 3 nằm bên dưới chuyện này: nếu `company_name` "
        f"không định danh một công ty thì \"cùng một công ty đăng tin hai lần\" không phải "
        f"một sự kiện quan sát được trong dataset này.\n"
        f"4. Do đó grain **không được chốt ở đây.** Nó được ghi nhận là hợp lý và chưa bị "
        f"bác bỏ, chờ các câu hỏi ở mục 11.")
    R.blank()
    return R, F


def build_report_tail(R, lang, F, meta, company, cage, dage, comb, title, indtitle,
                      loc, empmode, email, payment, bundles, grain) -> str:
    cc = company["facts"]
    ca = cage["facts"]
    da = dage["facts"]
    cb = comb["facts"]
    it = indtitle["facts"]
    lo = loc["facts"]
    em = email["facts"]
    pa = payment["facts"]
    gr = grain["facts"]

    # ---------------------------------------------------------------- 9
    R.w("## 9. Modelling risks", "## 9. Rủi ro khi mô hình hóa")
    R.blank()
    R.tbl([("Risk", "Rủi ro"), ("Evidence", "Bằng chứng"), ("Consequence", "Hệ quả")], [
        [("Company identity", "Định danh công ty")[0 if lang == "en" else 1],
         f"{i(cb['repeated_multiple_combinations'])} "
         + ("of" if lang == "en" else "trên") +
         f" {i(cc['n_repeated'])} "
         + ("repeated company_names carry more than one attribute combination"
            if lang == "en" else
            "company_name lặp lại mang nhiều hơn một tổ hợp thuộc tính"),
         ("A DimCompany keyed on company_name would silently merge rows that may belong "
          "to different companies, or split one company across versions. Every "
          "company-level figure would inherit that ambiguity."
          if lang == "en" else
          "Một DimCompany khóa theo company_name sẽ âm thầm gộp các dòng có thể thuộc về "
          "những công ty khác nhau, hoặc chẻ một công ty thành nhiều phiên bản. Mọi con số "
          "ở mức công ty sẽ thừa hưởng sự mơ hồ đó.")],
        [("Dimension cardinality", "Cardinality của dimension")[0 if lang == "en" else 1],
         f"{i(cc['n_companies'])} "
         + ("distinct company_name values over" if lang == "en" else
            "giá trị company_name phân biệt trên") +
         f" {i(cc['n_rows'])} " + ("rows" if lang == "en" else "dòng"),
         ("A dimension holding roughly half as many rows as the fact table gives up most "
          "of the storage and join benefit of a star schema."
          if lang == "en" else
          "Một dimension chứa số dòng xấp xỉ một nửa bảng fact sẽ đánh mất phần lớn lợi ích "
          "về lưu trữ và join của star schema.")],
        [("Non-monotonic time behaviour", "Hành vi thời gian không đơn điệu")[0 if lang == "en" else 1],
         f"company_age " + ("decreases in" if lang == "en" else "giảm ở") +
         f" {i(ca['n_decrease'])} " + ("pairs; domain_age_months in" if lang == "en"
                                       else "cặp; domain_age_months giảm ở") +
         f" {i(da['n_decrease'])}",
         ("SCD Type 2 assumes attribute changes are a history. Here the changes do not "
          "form a history, so versioning them would encode noise as fact."
          if lang == "en" else
          "SCD Type 2 giả định rằng thay đổi thuộc tính là một lịch sử. Ở đây các thay đổi "
          "không tạo thành lịch sử, nên version hóa chúng sẽ mã hóa nhiễu thành sự thật.")],
        [("Redundant attribute pairs", "Cặp thuộc tính dư thừa")[0 if lang == "en" else 1],
         ("recruiter_email_type <-> suspicious_email_domain bijection; payment_required "
          "== (registration_fee > 0)" if lang == "en" else
          "song ánh recruiter_email_type <-> suspicious_email_domain; payment_required "
          "== (registration_fee > 0)"),
         ("Storing both members of a pair lets two query paths produce the same number by "
          "different routes, and lets a future load break the invariant without any query "
          "noticing." if lang == "en" else
          "Lưu cả hai thành viên của một cặp khiến hai đường truy vấn cho ra cùng một con "
          "số theo hai lối khác nhau, và khiến một lần nạp dữ liệu sau này có thể phá vỡ "
          "bất biến mà không truy vấn nào nhận ra.")],
        [("Undocumented units", "Đơn vị không được tài liệu hóa")[0 if lang == "en" else 1],
         ("stipend has no documented currency or pay period; registration_fee has no "
          "documented currency" if lang == "en" else
          "stipend không có đơn vị tiền tệ hay kỳ trả được tài liệu hóa; registration_fee "
          "không có đơn vị tiền tệ được tài liệu hóa"),
         ("Any monetary aggregate across the nine cities sums different units. The result "
          "is presentable and wrong, which is the dangerous combination."
          if lang == "en" else
          "Mọi tổng hợp tiền tệ qua chín thành phố là cộng các đơn vị khác nhau. Kết quả "
          "trình bày được nhưng sai, và đó là sự kết hợp nguy hiểm.")],
        [("Outcome leakage", "Rò rỉ biến kết quả")[0 if lang == "en" else 1],
         ("is_fake_posting and fraud_score are the analysis target, not independent "
          "descriptors" if lang == "en" else
          "is_fake_posting và fraud_score là mục tiêu phân tích, không phải các mô tả độc "
          "lập"),
         ("Placing either in a slicing dimension invites analyses that explain the outcome "
          "with itself." if lang == "en" else
          "Đặt bất kỳ cái nào trong một dimension cắt lát sẽ dẫn tới các phân tích giải "
          "thích kết quả bằng chính nó.")],
        [("Degenerate attribute", "Thuộc tính suy biến")[0 if lang == "en" else 1],
         ("unrealistic_salary_flag is constant across all "
          + i(gr["n_rows"]) + " rows" if lang == "en" else
          "unrealistic_salary_flag là hằng số trên toàn bộ " + i(gr["n_rows"]) + " dòng"),
         ("It would produce a one-member dimension that can never slice anything, while "
          "still costing a join." if lang == "en" else
          "Nó sẽ tạo ra một dimension chỉ có một phần tử, không bao giờ cắt lát được gì mà "
          "vẫn tốn một phép join.")],
        [("Location semantics", "Ngữ nghĩa của location")[0 if lang == "en" else 1],
         ("location is one of " + i(lo["n_locations"]) + " cities with no country or "
          "region column, and the source does not say what it locates" if lang == "en" else
          "location là một trong " + i(lo["n_locations"]) + " thành phố, không có cột quốc "
          "gia hay khu vực, và nguồn không nói nó định vị cái gì"),
         ("A geographic hierarchy cannot be built from this dataset alone, and any "
          "imported hierarchy imports an assumption with it." if lang == "en" else
          "Không thể xây phân cấp địa lý chỉ từ dataset này, và mọi phân cấp nhập từ ngoài "
          "đều kéo theo một giả định.")],
    ], ["---", "---", "---"])

    # ---------------------------------------------------------------- 10
    R.w("## 10. Deferred decisions", "## 10. Các quyết định được hoãn lại")
    R.blank()
    R.w("Every item below is deliberately left open by this audit. Each is a decision for "
        "the star-schema stage, and each needs a stated assumption rather than more "
        "measurement of this extract.",
        "Mọi mục dưới đây đều được audit này cố ý để ngỏ. Mỗi mục là một quyết định thuộc "
        "giai đoạn star schema, và mỗi mục cần một giả định được nêu rõ chứ không phải thêm "
        "phép đo trên bản trích này.")
    R.blank()
    R.tbl([("#", "#"), ("Deferred decision", "Quyết định được hoãn"),
           ("Why it is deferred", "Vì sao hoãn")],
          [[k + 1, a if lang == "en" else b, c if lang == "en" else d]
           for k, (a, b, c, d) in enumerate([
               ("Whether a DimCompany exists at all, and what it is keyed on",
                "Có tồn tại DimCompany hay không, và khóa theo cái gì",
                f"Only {f(cb['pct_repeated_one_combination'])}% of repeated company_names "
                f"carry a single attribute combination; the data cannot distinguish a "
                f"changing company from two companies sharing a name.",
                f"Chỉ {f(cb['pct_repeated_one_combination'])}% company_name lặp lại mang "
                f"một tổ hợp thuộc tính duy nhất; dữ liệu không phân biệt được một công ty "
                f"đang thay đổi với hai công ty trùng tên."),
               ("Whether company attributes need SCD treatment, and which type",
                "Thuộc tính công ty có cần xử lý SCD hay không, và loại nào",
                "SCD presupposes a stable business key, which has not been established.",
                "SCD giả định có một business key ổn định, điều chưa được xác lập."),
               ("Whether industry joins the Internship dimension or stands alone",
                "industry có gia nhập dimension Internship hay đứng riêng",
                f"No functional dependency in either direction; Cramer's V "
                f"{f(it['cramers_v'], 6)}.",
                f"Không có functional dependency theo chiều nào; Cramer's V "
                f"{f(it['cramers_v'], 6)}."),
               ("Whether employment_type and work_mode become one dimension or two",
                "employment_type và work_mode thành một dimension hay hai",
                "Both are defensible: the grid is complete and neither determines the other.",
                "Cả hai đều bảo vệ được: lưới là đầy đủ và không cái nào quyết định cái kia."),
               ("Which of recruiter_email_type / suspicious_email_domain is stored",
                "Lưu cột nào trong recruiter_email_type / suspicious_email_domain",
                "The bijection makes them redundant, but they are not interchangeable in "
                "meaning and a later extract could break it.",
                "Song ánh khiến chúng dư thừa, nhưng chúng không thay thế được cho nhau về ý "
                "nghĩa và một bản trích sau có thể phá vỡ nó."),
               ("Whether payment_required is stored, derived, or both",
                "payment_required được lưu, được dẫn xuất, hay cả hai",
                f"The invariant holds on all {i(pa['rows'])} rows, so either choice is "
                f"currently lossless.",
                f"Bất biến đúng trên cả {i(pa['rows'])} dòng, nên hiện tại lựa chọn nào "
                f"cũng không mất thông tin."),
               ("Whether registration_fee is a fact measure or a dimension attribute",
                "registration_fee là measure trong fact hay thuộc tính dimension",
                "It is numeric and additive in form, but its currency is undocumented.",
                "Nó là số và về hình thức là additive, nhưng đơn vị tiền tệ không được tài "
                "liệu hóa."),
               ("Whether stipend can be used at all",
                "stipend có dùng được hay không",
                "Currency and pay period are both undocumented; no aggregate is defensible "
                "until they are established.",
                "Cả đơn vị tiền tệ lẫn kỳ trả đều không được tài liệu hóa; không phép tổng "
                "hợp nào bảo vệ được cho tới khi hai điều đó được xác lập."),
               ("Whether the trust and fraud flags become junk dimensions",
                "Các cờ trust và fraud có trở thành junk dimension hay không",
                "Technically feasible at the observed combination counts, but "
                "is_fake_posting is an outcome and unrealistic_salary_flag is constant.",
                "Khả thi về kỹ thuật với số tổ hợp quan sát được, nhưng is_fake_posting là "
                "biến kết quả và unrealistic_salary_flag là hằng số."),
               ("Whether unrealistic_salary_flag enters the warehouse",
                "unrealistic_salary_flag có vào warehouse hay không",
                "Constant on this extract, but a later extract could contain a value of 1; the "
                "cleaning rules keep it in staging for that reason.",
                "Hằng số trên bản trích này, nhưng bản trích sau có thể chứa giá trị 1; "
                "cleaning rules giữ nó trong staging vì lý do đó."),
               ("Whether score fields stay numeric or are also banded",
                "Các trường điểm số giữ nguyên dạng số hay còn được chia dải",
                "Banding creates dimension attributes but imposes thresholds the source "
                "does not document.",
                "Chia dải tạo ra thuộc tính dimension nhưng áp đặt các ngưỡng mà nguồn không "
                "tài liệu hóa."),
               ("The final grain statement and its surrogate key",
                "Phát biểu grain cuối cùng và surrogate key của nó",
                "Posting-level grain is un-contradicted but unprovable without a posting "
                "ID; source_row_id is lineage only.",
                "Grain mức tin đăng chưa bị bác bỏ nhưng không chứng minh được nếu không có "
                "ID tin đăng; source_row_id chỉ dùng để truy vết nguồn."),
               ("Whether is_future_posting rows are included in analytical queries",
                "Các dòng is_future_posting có được đưa vào truy vấn phân tích hay không",
                f"{i(F['future_rows'])} rows are dated after the fixed reference date and "
                f"are flagged, not filtered.",
                f"{i(F['future_rows'])} dòng có ngày sau ngày tham chiếu cố định và chỉ "
                f"được đánh cờ, không bị lọc."),
           ])],
          ["---:", "---", "---"])

    # ---------------------------------------------------------------- 11
    R.w("## 11. Recommended questions to resolve before the final star schema",
        "## 11. Các câu hỏi cần giải quyết trước khi thiết kế star schema cuối cùng")
    R.blank()
    R.w("These questions cannot be answered by measuring this extract further. They need "
        "the source system, its documentation, or an explicit modelling assumption agreed "
        "and written down.",
        "Những câu hỏi này không thể trả lời bằng cách đo thêm bản trích hiện có. Chúng cần "
        "hệ thống nguồn, tài liệu của nó, hoặc một giả định mô hình hóa được thống nhất và "
        "ghi lại rõ ràng.")
    R.blank()
    R.tbl([("#", "#"), ("Question", "Câu hỏi"),
           ("What it unblocks", "Nó mở khóa điều gì")],
          [[k + 1, a if lang == "en" else b, c if lang == "en" else d]
           for k, (a, b, c, d) in enumerate([
               ("Is there a company identifier in the source system that did not survive "
                "into this extract?",
                "Trong hệ thống nguồn có định danh công ty nào mà bản trích này không giữ "
                "lại không?",
                "Everything about DimCompany: its existence, its key, its grain and whether "
                "SCD applies.",
                "Toàn bộ vấn đề về DimCompany: sự tồn tại, khóa, grain và việc có áp dụng "
                "SCD hay không."),
               ("If not, may company_name be treated as a company key by explicit "
                "assumption, and is that assumption acceptable to the coursework?",
                "Nếu không, có được phép coi company_name là khóa công ty theo một giả định "
                "nêu rõ, và giả định đó có được chấp nhận trong bài tập không?",
                "A defensible DimCompany built on a stated assumption rather than on "
                "evidence the data does not provide.",
                "Một DimCompany bảo vệ được, dựa trên một giả định được nêu rõ thay vì dựa "
                "trên bằng chứng mà dữ liệu không có."),
               ("What currency is stipend denominated in, and over what pay period?",
                "stipend được tính bằng đơn vị tiền tệ nào, và theo kỳ trả nào?",
                "Any use of stipend at all, and in particular any comparison across "
                "location.",
                "Mọi cách sử dụng stipend, và đặc biệt là mọi so sánh theo location."),
               ("What currency is registration_fee denominated in?",
                "registration_fee được tính bằng đơn vị tiền tệ nào?",
                "Whether registration_fee can be summed across locations as a fact measure.",
                "Việc registration_fee có được cộng qua các location như một measure trong "
                "fact hay không."),
               ("Does location refer to the work location, the company location or the "
                "recruiter location?",
                "location chỉ nơi làm việc, địa chỉ công ty hay vị trí nhà tuyển dụng?",
                "Whether DimLocation can be conformed with any other dimension, and whether "
                "a geographic hierarchy may be imported.",
                "Việc DimLocation có thể conform với dimension khác hay không, và có được "
                "nhập một phân cấp địa lý hay không."),
               ("How are the seven 0-100 scores computed, and is the scale comparable "
                "across rows and over time?",
                "Bảy điểm số 0-100 được tính thế nào, và thang đo có so sánh được giữa các "
                "dòng và theo thời gian không?",
                "Whether averaging them is defensible, and whether banding them into "
                "dimension attributes is legitimate.",
                "Việc lấy trung bình chúng có bảo vệ được không, và việc chia dải chúng "
                "thành thuộc tính dimension có chính đáng không."),
               ("Is there a recruiter identifier in the source system?",
                "Hệ thống nguồn có định danh nhà tuyển dụng không?",
                "Whether DimRecruiter can hold recruiter_experience_years and "
                "recruiter_response_time_hours instead of leaving them in the fact.",
                "Việc DimRecruiter có thể chứa recruiter_experience_years và "
                "recruiter_response_time_hours thay vì để chúng trong fact hay không."),
               ("Is there a posting identifier in the source system?",
                "Hệ thống nguồn có định danh tin đăng không?",
                "A provable grain statement and a business-meaningful key for the fact "
                "table.",
                "Một phát biểu grain chứng minh được và một khóa có ý nghĩa nghiệp vụ cho "
                "bảng fact."),
               ("Why does company_age fall between later postings by the same "
                "company_name?",
                "Vì sao company_age lại giảm ở các tin đăng sau của cùng một company_name?",
                "Whether company attributes are a genuine history worth versioning, or "
                "noise that must not be versioned.",
                "Việc thuộc tính công ty có phải một lịch sử thật đáng version hóa hay chỉ "
                "là nhiễu không được phép version hóa."),
               ("Is the bijection between recruiter_email_type and "
                "suspicious_email_domain guaranteed by the source, or an accident of this "
                "extract?",
                "Song ánh giữa recruiter_email_type và suspicious_email_domain được nguồn "
                "bảo đảm, hay chỉ là ngẫu nhiên của bản trích này?",
                "Whether one of the two may safely be dropped from the model.",
                "Việc có thể an toàn bỏ một trong hai khỏi mô hình hay không."),
               ("Is payment_required guaranteed by the source to equal registration_fee > "
                "0, or is that an accident of this extract?",
                "Nguồn có bảo đảm payment_required luôn bằng registration_fee > 0, hay đó "
                "chỉ là ngẫu nhiên của bản trích này?",
                "Whether the flag may be derived rather than stored.",
                "Việc có thể dẫn xuất cờ thay vì lưu nó hay không."),
               ("Will unrealistic_salary_flag ever take a value other than 0 in a future extract?",
                "unrealistic_salary_flag có bao giờ khác 0 ở một bản trích tương lai không?",
                "Whether it is a degenerate column to exclude or a real flag to keep.",
                "Việc nó là một cột suy biến cần loại bỏ hay một cờ thật cần giữ lại."),
               ("Should future-dated postings be included in, excluded from, or reported "
                "separately in analytical queries?",
                "Các tin đăng ngày tương lai nên được đưa vào, loại ra, hay báo cáo riêng "
                "trong truy vấn phân tích?",
                "How the date dimension is bounded and how every time-series figure is read.",
                "Cách giới hạn dimension ngày và cách đọc mọi con số theo chuỗi thời gian."),
           ])],
          ["---:", "---", "---"])

    R.w("---", "---")
    R.blank()
    R.w(f"*Generated by `scripts/audit_dimensional_consistency.py` on "
        f"{meta['generated_at']} from {i(meta['n_rows'])} staging rows. Staging sha256 "
        f"unchanged: "
        f"{'yes' if meta['unchanged'] else 'NO'}. No data was modified.*",
        f"*Được tạo bởi `scripts/audit_dimensional_consistency.py` lúc "
        f"{meta['generated_at']} từ {i(meta['n_rows'])} dòng staging. sha256 của staging "
        f"không đổi: {'có' if meta['unchanged'] else 'KHÔNG'}. Không dữ liệu nào bị thay "
        f"đổi.*")
    return R.text()


def render_report(lang: str, **kw) -> str:
    R, F = build_report(lang, **kw)
    return build_report_tail(
        R, lang, F, kw["meta"], kw["company"], kw["cage"], kw["dage"], kw["comb"],
        kw["title"], kw["indtitle"], kw["loc"], kw["empmode"], kw["email"],
        kw["payment"], kw["bundles"], kw["grain"])


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Read-only dimensional consistency / functional dependency audit.")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                   help="path to the staging CSV (read-only)")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                   help="directory for the audit outputs")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    source: Path = args.input.resolve()
    out_dir: Path = args.output_dir.resolve()

    if not source.is_file():
        print(f"ERROR: input file not found: {source}", file=sys.stderr)
        return 1
    if out_dir.is_file():
        print(f"ERROR: output path exists and is a file: {out_dir}", file=sys.stderr)
        return 1
    if source.parent == out_dir:
        print("ERROR: refusing to write audit output into the staging data directory.",
              file=sys.stderr)
        return 1
    for protected in ("data/raw", "data/staging"):
        if protected.replace("/", "\\") in str(out_dir) or protected in str(out_dir).replace("\\", "/"):
            print(f"ERROR: refusing to write audit output under {protected}.", file=sys.stderr)
            return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    print(SEP)
    print("DIMENSIONAL CONSISTENCY / FUNCTIONAL DEPENDENCY AUDIT (read-only)")
    print(SEP)
    print(f"Input      : {source}")
    print(f"Output dir : {out_dir}")
    print("Fingerprinting staging file (before) ...", flush=True)
    fp_before = file_fingerprint(source)
    print(f"  size {human_bytes(fp_before['size_bytes'])}")
    print(f"  sha256 {fp_before['sha256']}")

    print("Loading staging CSV (quote-aware, chunked) ...", flush=True)
    t0 = time.perf_counter()
    df = load_staging(source)
    load_seconds = time.perf_counter() - t0
    n_rows, n_cols = df.shape
    print(f"  loaded {n_rows:,} rows x {n_cols} columns in {load_seconds:.2f}s")

    # Working columns, in memory only, never written back anywhere.
    parsed = pd.to_datetime(df[DATE_COLUMN], format="%Y-%m-%d")
    df["_date_ordinal"] = parsed.to_numpy().astype("datetime64[D]").astype("int32")
    df["_posting_year"] = parsed.dt.year.to_numpy().astype("int16")
    del parsed

    print(" 1/11 company entity consistency ...", flush=True)
    company = audit_company_consistency(df)
    ccodes = company["ccodes"]
    n_companies = company["n_companies"]
    posting_count = company["posting_count"]

    print(" 2/11 company_age over calendar time ...", flush=True)
    cage = audit_company_age_time(df, ccodes, n_companies, posting_count)
    print(" 3/11 domain_age_months over calendar time ...", flush=True)
    dage = audit_domain_age_time(df, ccodes, n_companies, posting_count)
    print(" 4/11 company attribute combination test ...", flush=True)
    comb = audit_company_combination(df, ccodes, n_companies, posting_count)
    print(" 5/11 internship_title analysis ...", flush=True)
    title = audit_title(df)
    print(" 6/11 industry / title relationship ...", flush=True)
    indtitle = audit_industry_title(df)
    print(" 7/11 location analysis ...", flush=True)
    loc = audit_location(df, ccodes)
    print(" 8/11 employment_type / work_mode analysis ...", flush=True)
    empmode = audit_employment_work_mode(df)
    print(" 9/11 email and payment invariants ...", flush=True)
    email = audit_email(df)
    payment = audit_payment(df)
    bundles = audit_flag_bundles(df)
    print("10/11 field group classification ...", flush=True)
    fields = audit_field_groups(df, ccodes, n_companies, posting_count)
    fieldclass = build_field_classification(fields["table"])
    print("11/11 grain evidence ...", flush=True)
    grain = audit_grain(df, composites=[
        ("company_name", "posting_date"),
        ("company_name", "posting_date", "internship_title"),
        ("company_name", "posting_date", "internship_title", "location"),
        ("company_name", "posting_date", "internship_title", "location",
         "industry", "employment_type", "work_mode"),
    ])

    # ---- shared facts used by the narrative builders
    measure_stats = {}
    for col in df.columns:
        if col.startswith("_") or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        nn = s.dropna()
        measure_stats[col] = {
            "min": float(nn.min()) if nn.size else np.nan,
            "max": float(nn.max()) if nn.size else np.nan,
            "mean": float(nn.mean()) if nn.size else np.nan,
            "median": float(nn.median()) if nn.size else np.nan,
            "distinct": int(nn.nunique()),
            "missing": int(s.isna().sum()),
            "sum": float(nn.sum()),
        }
    label_positive = int(df[LABEL].sum())
    future_rows = int(df["is_future_posting"].sum())
    F = {
        "company": company["facts"],
        "company_age": cage["facts"],
        "domain_age": dage["facts"],
        "combination": comb["facts"],
        "title": title["facts"],
        "industry_title": indtitle["facts"],
        "location": loc["facts"],
        "employment": empmode["facts"],
        "email": email["facts"],
        "payment": payment["facts"],
        "grain": grain["facts"],
        "bundles": bundles["table"],
        "measure_stats": measure_stats,
        "label_positive": label_positive,
        "label_rate": pct(label_positive, n_rows),
        "future_rows": future_rows,
        "future_rows_pct": pct(future_rows, n_rows),
    }
    dims = build_candidate_dimensions(F)
    measures = build_candidate_measures(F, fieldclass)

    # ---- CSV outputs
    print("Writing CSV outputs ...", flush=True)
    company["table"].to_csv(out_dir / "company_consistency.csv", index=False)
    company["examples"].to_csv(out_dir / "company_consistency_examples.csv", index=False)
    company["distribution"].to_csv(out_dir / "company_posting_distribution.csv", index=False)
    cage["summary"].to_csv(out_dir / "company_age_time_consistency.csv", index=False)
    dage["summary"].to_csv(out_dir / "domain_age_time_consistency.csv", index=False)
    comb["distribution"].to_csv(out_dir / "company_attribute_combinations.csv", index=False)
    title["crosstab"].to_csv(out_dir / "title_attribute_crosstab.csv", index=False)
    indtitle["tidy"].to_csv(out_dir / "industry_title_crosstab.csv", index=False)
    loc["profile"].to_csv(out_dir / "location_profile.csv", index=False)
    loc["industry_crosstab"].to_csv(out_dir / "location_industry_crosstab.csv", index=False)
    empmode["tidy"].to_csv(out_dir / "employment_workmode_crosstab.csv", index=False)
    email["tidy"].to_csv(out_dir / "email_bijection.csv", index=False)
    payment["table"].to_csv(out_dir / "payment_consistency_check.csv", index=False)
    bundles["table"].to_csv(out_dir / "flag_bundle_combinations.csv", index=False)
    fieldclass.to_csv(out_dir / "field_classification.csv", index=False)
    grain["table"].to_csv(out_dir / "grain_evidence.csv", index=False)
    grain["composites"].to_csv(out_dir / "grain_composite_keys.csv", index=False)

    # categorical_dependency_summary.csv - every categorical pair tested anywhere
    dep_rows = []
    for _, r in title["pairs"].iterrows():
        dep_rows.append({
            "left": r["left"], "right": r["right"],
            "left_levels": r["left_levels"], "right_levels": r["right_levels"],
            "observed_combinations": r["observed_combinations"],
            "possible_combinations": r["possible_combinations"],
            "all_combinations_present": r["all_combinations_present"],
            "cramers_v": r["cramers_v"],
            "left_determines_right": r["left_determines_right"],
            "right_determines_left": r["right_determines_left"],
        })
    for a, b in [("industry", "internship_title"), ("employment_type", "work_mode"),
                 ("location", "industry"), ("location", "internship_title"),
                 ("location", "company_size"), ("industry", "company_size"),
                 ("recruiter_email_type", "suspicious_email_domain"),
                 ("payment_required", "fake_certificate_offer"),
                 ("company_size", "verification_status")]:
        ct = pd.crosstab(df[a], df[b])
        fwd = functional_dependency(df[a], df[b])
        rev = functional_dependency(df[b], df[a])
        dep_rows.append({
            "left": a, "right": b,
            "left_levels": int(ct.shape[0]), "right_levels": int(ct.shape[1]),
            "observed_combinations": int((ct > 0).sum().sum()),
            "possible_combinations": int(ct.shape[0] * ct.shape[1]),
            "all_combinations_present": bool((ct > 0).all().all()),
            "cramers_v": cramers_v(ct.to_numpy()),
            "left_determines_right": fwd["holds"],
            "right_determines_left": rev["holds"],
        })
    dep_rows.append({
        "left": "company_name", "right": " + ".join(COMPANY_COMBINATION_ATTRIBUTES),
        "left_levels": n_companies,
        "right_levels": comb["facts"]["combinations_observed"],
        "observed_combinations": comb["facts"]["combinations_observed"],
        "possible_combinations": comb["facts"]["combinations_possible"],
        "all_combinations_present": bool(
            comb["facts"]["combinations_observed"] == comb["facts"]["combinations_possible"]),
        "cramers_v": None,
        "left_determines_right": comb["facts"]["fd_holds"],
        "right_determines_left": False,
    })
    dependency_summary = pd.DataFrame(dep_rows)
    dependency_summary.to_csv(out_dir / "categorical_dependency_summary.csv", index=False)

    # candidate_dimension_summary.csv
    dim_rows = [{
        "candidate_dimension": d["name"]["en"],
        "possible_attributes": ", ".join(d["attributes"])
                               + (" (" + d["attributes_note"]["en"] + ")"
                                  if d.get("attributes_note") else ""),
        "evidence_supporting_grouping": d["evidence"]["en"],
        "consistency_problems": d["problems"]["en"],
        "high_cardinality_concerns": d["cardinality"]["en"],
        "time_variance_concerns": d["time_variance"]["en"],
        "scd_consideration": d["scd"]["en"],
        "confidence": d["confidence"],
    } for d in dims]
    pd.DataFrame(dim_rows).to_csv(out_dir / "candidate_dimension_summary.csv", index=False)

    meas_rows = [{
        "measure_candidate": m["measure"],
        "additivity": m["additivity"],
        "measured_basis": m["basis"]["en"],
        "reasoning": m["note"]["en"],
    } for m in measures]
    pd.DataFrame(meas_rows).to_csv(out_dir / "candidate_measure_summary.csv", index=False)

    # ---- reports
    fp_after = file_fingerprint(source)
    unchanged = fp_after == fp_before
    meta = {
        "source": source.as_posix(),
        "n_rows": n_rows,
        "n_cols": n_cols - 2,  # the two in-memory working columns are not part of staging
        "fingerprint_before": fp_before,
        "fingerprint_after": fp_after,
        "unchanged": unchanged,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    kw = dict(meta=meta, company=company, cage=cage, dage=dage, comb=comb, title=title,
              indtitle=indtitle, loc=loc, empmode=empmode, email=email, payment=payment,
              fields=fields, fieldclass=fieldclass, bundles=bundles, grain=grain,
              dims=dims, measures=measures, F=F)
    print("Writing reports ...", flush=True)
    (out_dir / "dimensional_consistency_en.md").write_text(
        render_report("en", **kw), encoding="utf-8")
    (out_dir / "dimensional_consistency_vi.md").write_text(
        render_report("vi", **kw), encoding="utf-8")

    # ---- verify outputs exist and are non-empty
    expected = [
        "dimensional_consistency_en.md", "dimensional_consistency_vi.md",
        "company_consistency.csv", "company_consistency_examples.csv",
        "company_posting_distribution.csv", "company_age_time_consistency.csv",
        "domain_age_time_consistency.csv", "company_attribute_combinations.csv",
        "title_attribute_crosstab.csv", "industry_title_crosstab.csv",
        "location_profile.csv", "location_industry_crosstab.csv",
        "employment_workmode_crosstab.csv", "email_bijection.csv",
        "payment_consistency_check.csv", "flag_bundle_combinations.csv",
        "categorical_dependency_summary.csv", "field_classification.csv",
        "candidate_dimension_summary.csv", "candidate_measure_summary.csv",
        "grain_evidence.csv", "grain_composite_keys.csv",
    ]
    missing = [name for name in expected
               if not (out_dir / name).is_file() or (out_dir / name).stat().st_size == 0]

    cc = company["facts"]
    ca = cage["facts"]
    da = dage["facts"]
    cb = comb["facts"]
    tt = title["facts"]
    it = indtitle["facts"]
    lo = loc["facts"]
    ew = empmode["facts"]
    em = email["facts"]
    pa = payment["facts"]
    gr = grain["facts"]

    print()
    print(SEP)
    print("DIMENSIONAL AUDIT SUMMARY")
    print(SEP)
    print(f" Rows analysed        : {n_rows:,}")
    print(f" Staging sha256       : {'UNCHANGED' if unchanged else 'CHANGED - INVESTIGATE'}")
    print(f" Outputs written      : {len(expected) - len(missing)}/{len(expected)}"
          + (f"  MISSING: {', '.join(missing)}" if missing else ""))
    print()
    print(" 1. Company grouping  : "
          f"{cc['n_companies']:,} distinct company_name | "
          f"{cc['n_repeated']:,} repeated ({cc['pct_repeated']:.4f}%) covering "
          f"{cc['rows_in_repeated']:,} rows ({cc['pct_rows_in_repeated']:.4f}%)")
    print(f"                        max postings for one name: "
          f"{cc['max_postings_one_company']:,}")
    print(" 2. Attribute stability (repeated names, one distinct value):")
    for _, r in company["table"].iterrows():
        print(f"      {r['attribute']:<24} "
              f"{r['repeated_with_one_distinct_value']:>9,} stable | "
              f"{r['repeated_with_multiple_distinct_values']:>9,} multi | "
              f"{r['pct_stable_among_repeated']:>8.4f}% | max "
              f"{int(r['max_distinct_among_repeated'])}")
    print(" 3. Combination test  : "
          f"{cb['repeated_one_combination']:,}/{cc['n_repeated']:,} repeated names "
          f"({cb['pct_repeated_one_combination']:.4f}%) carry ONE combination of "
          f"{len(cb['attributes'])} attributes")
    print(f"                        company_name -> combination is a functional "
          f"dependency: {'YES' if cb['fd_holds'] else 'NO'} "
          f"({cb['fd_violating_rows']:,} rows in violating groups)")
    print(f" 4. company_age       : {ca['n_pairs']:,} consecutive pairs | "
          f"decreases {ca['n_decrease']:,} ({ca['pct_decrease']:.4f}%) | "
          f"same-year multi-value groups {ca['year_groups_multi_value']:,}")
    print(f" 5. domain_age_months : {da['n_pairs']:,} consecutive pairs | "
          f"increases {da['n_increase']:,} ({da['pct_increase']:.4f}%) | "
          f"decreases {da['n_decrease']:,} ({da['pct_decrease']:.4f}%) | "
          f"outside +/-{da['tolerance']:.0f}mo tolerance {da['n_implausible']:,}")
    print(f" 6. internship_title  : {tt['n_titles']} titles | max Cramer's V vs "
          f"placement attributes {tt['max_cramers_v']:.6f} | any determinism: "
          f"{'YES' if tt['any_determinism'] else 'NO'}")
    print(f" 7. industry x title  : {it['nonzero_cells']}/{it['cells']} cells populated | "
          f"Cramer's V {it['cramers_v']:.6f} | deterministic either way: "
          f"{'YES' if (it['industry_determines_title'] or it['title_determines_industry']) else 'NO'}")
    print(f" 8. location          : {lo['n_locations']} cities | fake rate "
          f"{lo['min_fake_rate']:.4f}%-{lo['max_fake_rate']:.4f}% "
          f"(baseline {lo['baseline_fake_rate']:.4f}%) | stipend NOT aggregated "
          f"(currency/pay-period unresolved)")
    print(f" 9. employment x mode : {ew['observed_combinations']}/"
          f"{ew['possible_combinations']} combinations present | Cramer's V "
          f"{ew['cramers_v']:.6f} | either determines the other: "
          f"{'YES' if (ew['employment_determines_work_mode'] or ew['work_mode_determines_employment']) else 'NO'}")
    print(f"10. email bijection   : "
          f"{'CONFIRMED' if em['bijection'] else 'NOT CONFIRMED'} "
          f"({em['forward_violating_rows']:,} fwd / {em['reverse_violating_rows']:,} rev "
          f"violating rows)")
    print(f"11. payment invariant : "
          f"{'HOLDS' if pa['holds'] else 'FAILS'} "
          f"({pa['disagree']:,} disagreeing rows of {pa['rows']:,})")
    counts = fieldclass["provisional_class"].value_counts()
    print("12. Field classes     : "
          + " | ".join(f"{k}: {v}" for k, v in counts.items()))
    print(f"13. Grain             : {gr['n_rows']:,} rows | exact duplicate rows "
          f"{gr['exact_duplicates']:,} | declared posting ID: NONE | unique business "
          f"composite found: {'YES (by accident, not a key)' if gr['natural_key_found'] else 'NO'}")
    print(f"                        narrowest composite leaves "
          f"{gr['narrow_composite_dups']:,} duplicate rows, widest leaves "
          f"{gr['widest_composite_dups']:,}")
    print(f"14. Candidates        : {len(dims)} candidate dimensions "
          + "(" + ", ".join(f"{d['name']['en']}={d['confidence']}" for d in dims) + ")")
    print(f"                        {len(measures)} candidate measures | additivity: "
          + " | ".join(f"{k}: {v}" for k, v in
                       pd.Series([m["additivity"] for m in measures]).value_counts().items()))
    print()
    print(SEP)
    print("CONCLUSIONS")
    print(SEP)
    print(f" - Staging data unchanged            : "
          f"{'YES - sha256 identical before and after' if unchanged else 'NO - INVESTIGATE'}")
    print(f" - Company consistency               : company_name is NOT a reliable company "
          f"identifier on this evidence;")
    print(f"                                       only {cb['pct_repeated_one_combination']:.4f}% "
          f"of repeated names carry a single attribute combination")
    strong = []
    if em["bijection"]:
        strong.append("recruiter_email_type <-> suspicious_email_domain (bijection)")
    if pa["holds"]:
        strong.append("payment_required == (registration_fee > 0)")
    print(f" - Strong functional dependencies     : "
          + (f"{len(strong)} found - " + "; ".join(strong) if strong else "none found"))
    print(f"                                       no categorical pair among title / "
          f"industry / location / employment_type / work_mode shows any determinism")
    print(f" - Posting-level grain                : PLAUSIBLE and un-contradicted "
          f"({gr['exact_duplicates']:,} exact duplicate rows), but NOT proven -")
    print(f"                                       no posting ID exists in the source"
          + (", a wide business composite is unique only by accident,"
             if gr["natural_key_found"] else ",")
          + " and source_row_id is lineage only")
    print(f" - Unresolved modelling decisions     : DimCompany existence and key; SCD "
          f"treatment of company attributes;")
    print(f"                                       stipend currency and pay period; "
          f"registration_fee currency; industry placement;")
    print(f"                                       redundant email pair; "
          f"payment_required stored vs derived; junk-dimension design;")
    print(f"                                       unrealistic_salary_flag inclusion; "
          f"final grain statement and surrogate key")
    print(SEP)

    if not unchanged:
        print("ERROR: the staging file changed during the audit.", file=sys.stderr)
        return 1
    if missing:
        print(f"ERROR: expected outputs missing or empty: {missing}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
