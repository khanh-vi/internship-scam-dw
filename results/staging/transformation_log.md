# Transformation Log &mdash; Staging Layer

| Item | Value |
| --- | --- |
| Generated | 2026-09-23 17:23:06 |
| Script | `scripts/build_staging.py` |
| Input | `data/raw/fake_internship_detection_dataset.csv` |
| Input sha256 | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Output | `data/staging/internship_postings_staging.csv` |
| Rows in / out | 1,000,000 / 1,000,000 |
| Columns in / out | 33 / 35 |
| Runtime | 68.0s |

Every rule cited below is from [docs/cleaning_rules.md](../../docs/cleaning_rules.md). **No new cleaning decision was made in this layer** and no business meaning was reinterpreted beyond the documented evidence.

---

## 1. Transformations performed

Exactly three. Nothing else was changed.

### 1.1 Parse and standardise `posting_date`

| Item | Detail |
| --- | --- |
| Rule | R4.2.1, R4.2.2 |
| Action | Parsed with the explicit format `%Y-%m-%d` into a real date, written back as ISO `YYYY-MM-DD`. |
| Parse failures | 0 &mdash; failures are reported, never coerced, defaulted or dropped (R4.2.3) |
| Resulting range | 2018-01-01 to 2026-12-31 |
| Distinct dates | 3,287 |
| Rows removed | 0 |

The source already writes the column as `YYYY-MM-DD`, so this changes the **representation** (text to a typed date and back to ISO text) and not the meaning: no date is shifted, re-based or re-interpreted, and no future-dated row is removed (R4.2.4).

### 1.2 Add `source_row_id`

| Item | Detail |
| --- | --- |
| Rule | R4.1.1 &ndash; R4.1.4 |
| Action | Sequential integer assigned in original CSV order, before any filter, sort or transformation. |
| Range | 1 to 1,000,000, contiguous |
| Distinct / nulls | 1,000,000 / 0 |
| Chunks crossed | 10 &mdash; the counter is global and is never reset per chunk |
| Added to raw file | **No.** Staging only (R4.1.3). |

**This is a staging lineage identifier, not a natural or business key.** Profiling found no unique single column and no unique composite among the 33 source fields, so a surrogate is the only way to address an individual row. It is meaningful only together with the source file's sha256, must not be used to join across extracts, and carries no analytic ordering significance.

### 1.3 Add `is_future_posting`

| Item | Detail |
| --- | --- |
| Rule | R4.2.5, R4.2.6 |
| Definition | `1` when `posting_date > 2026-09-23`, otherwise `0` |
| Reference date | **2026-09-23** &mdash; a fixed documented constant, never the system clock |
| Rows flagged | 30,246 (3.0246%) |
| Rows removed | 0 &mdash; the flag marks, it does not filter |

The cutoff is pinned so the output is reproducible: computing the flag from the current date would make the flagged-row count drift on every run and no two loads could be compared. The expected count of 30,246 appears **only** as a post-transformation assertion in [staging_validation.md](staging_validation.md); it is not an input to the rule.

### 1.4 Datatype realisation (not a value change)

Typing is how the values are represented, not what they mean. Recorded here for completeness:

- `company_age` and `stipend` use pandas nullable integer (`Int64`). The audit measured **0 non-integral non-null values** in both, so no precision is lost. NULL is preserved as NULL and is **never** replaced by zero. The written CSV therefore shows `23` where the float read showed `23.0`.
- `recruiter_experience_years`, `recruiter_response_time_hours`, `trust_signal_score` and `fraud_score` keep one-decimal precision as `float64`. They are **not** rounded to integers.
- The nine binary fields stay as integer `0`/`1`.
- The eight text columns stay as text, verbatim.
- The intended SQL datatype for each column is recorded in [staging_column_profile.csv](staging_column_profile.csv), because a CSV carries no datatype metadata.

---

## 2. Transformations deliberately NOT performed

Each was considered and rejected on documented evidence. This section exists so a later reader can tell *decided against* from *overlooked*.

| Not performed | Why |
| --- | --- |
| **No imputation** | The 10,000 nulls each in `company_age`, `stipend` and `trust_signal_score` are preserved. No mean, median, mode, zero, forward/backward fill or model-based fill. Imputing would manufacture values the source does not contain and would distort every downstream aggregate. |
| **No row deletion** | All 1,000,000 rows retained. No row dropped for missingness, for being future-dated, or for being an outlier. |
| **No column deletion** | All 33 source columns retained, including `unrealistic_salary_flag` (constant `0` in this extract) and both sides of the two redundant pairs. Dropping a column is a dimensional-modelling decision, deliberately deferred. |
| **No de-duplication** | 0 exact duplicates were found and the fact was re-validated after staging, over the **33 original source fields only**. `source_row_id` and `is_future_posting` are excluded from that check because `source_row_id` would make every row unique by definition. |
| **No category mapping or merging** | `internship_title`, `employment_type`, `work_mode`, `industry`, `location`, `company_name`, `company_size` and `recruiter_email_type` are preserved verbatim. |
| **No ordinal coding of `company_size`** | It stays categorical. The domain mixes a maturity label (`Startup`) with scale labels (`Small`, `Medium`, `Enterprise`), so `Startup` is not demonstrably part of a size scale and no ordinal rank can be justified from the evidence. |
| **No case folding, trimming or whitespace normalisation** | Measured 0 padded values, 0 empty strings, 0 whitespace-only values, 0 case-variant duplicates. There is no defect to fix, and an unconditional `TRIM`/`LOWER` would hide a change in source behaviour instead of surfacing it. Text quality is re-checked and **reported**, not repaired. |
| **No scaling or standardisation** | No min-max, z-score, log or any other rescaling. Staging preserves source units. |
| **No outlier removal, capping or winsorizing** | IQR findings are diagnostic only. No value was removed, clipped or replaced. |
| **No currency conversion** | The source documents no currency for `stipend` or `registration_fee`. |
| **No stipend normalisation or banding** | No annualisation, no re-basing across locations, no bands. See the limitation below. |
| **No label derivation** | `is_fake_posting` is **not** derived from `fraud_score`. The audit found the two disagree at `fraud_score = 50`, so the label is not a function of the score. Both are preserved independently. |
| **No derivation from the validated invariants** | `payment_required` is not recomputed from `registration_fee`, and `suspicious_email_domain` is not recomputed from `recruiter_email_type`. The relationships are **validated only**. |
| **No class rebalancing** | The `is_fake_posting` distribution is untouched. |
| **No encoding** | No one-hot, ordinal, target or hash encoding. That belongs to modelling, not staging. |
| **No enrichment** | No geographic, industry or company enrichment; no fuzzy matching or entity resolution on `company_name`. The recurring `<Surname> <Suffix>` pattern means name similarity must not be treated as company identity. |
| **No change to the raw file** | `data/raw/` is read-only. Nothing was written, rewritten or re-timestamped there, and `source_row_id` was not added to it. |

---

## 3. Carried-forward limitation &mdash; `stipend` semantics

The source does not document a **currency** or a **pay period** for `stipend`. Values span 2,000 to 110,428 across nine locations in different currency zones, and nothing in the extract indicates whether a figure is monthly or annual.

This is **unresolved**, not settled. Staging therefore preserves the numbers as supplied and performs no conversion, annualisation, cross-location normalisation or banding. Until the currency and pay period are established from the source system, `stipend` values from different locations **must not be assumed directly comparable**, and cross-location aggregation of `stipend` would be unsound.

