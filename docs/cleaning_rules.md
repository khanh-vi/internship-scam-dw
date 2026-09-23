# Cleaning Rules — `internship-scam-dw`

| Item | Value |
| --- | --- |
| Source file | `data/raw/fake_internship_detection_dataset.csv` |
| Source sha256 | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Source rows × columns | 1,000,000 × 33 |
| Audit / reference date | **2026-09-23** |
| Evidence base | `results/profiling/`, `results/audit/` |
| Companion document | [data_dictionary.md](data_dictionary.md) |
| Status | **Approved.** Reviewed and signed off by the project owner. |

These rules are binding on the staging load. They were derived from the
completed profiling and audit phases and approved by a human. **They are not to
be extended, reinterpreted or supplemented with new cleaning decisions during
implementation.** A defect that these rules do not cover is escalated for a
decision; it is not fixed on the fly.

---

## Layer vocabulary used throughout

Three kinds of field are distinguished everywhere in this document, and the
distinction is load-bearing:

| Term | Meaning |
| --- | --- |
| **Source field** | One of the 33 columns physically present in the raw CSV. |
| **Staging-derived field** | A field created by the staging load. It exists only in staging, never in the raw file. There are exactly **two**: `source_row_id` and `is_future_posting`. |
| **Dimensional-model decision** | A choice explicitly deferred to the later star-schema design. Recorded here as an open question, **not** acted on. |

A rule that applies to a source field never authorises changing the raw file. A
staging-derived field is always marked as such. A deferred decision is never
silently resolved.

---

## 1. Purpose

This document states, for every source column and column group, exactly what the
staging load does and does not do, and why.

It exists to make the pipeline **auditable and reproducible**. Specifically:

1. It records the cleaning decisions that were approved, so implementation is
   transcription rather than judgement.
2. It records the transformations that were **explicitly rejected**, so that a
   later reader can tell the difference between "not done" and "forgotten".
   This is the point of §11.
3. It ties each decision to the measurement that justifies it, so that a
   challenge to a decision can be settled by re-running the evidence rather than
   by argument.
4. It fixes the boundary between staging and dimensional modelling, so that
   modelling choices are not smuggled into the cleaning layer.

The scope of this document is the **raw → staging** step. It does not cover the
dimensional model, the ETL orchestration or any OLAP cube definition.

---

## 2. Raw-data immutability policy

**`data/raw/` is immutable. This rule has no exceptions.**

| Rule | Detail |
| --- | --- |
| R2.1 | The raw CSV is **never** modified, overwritten, re-saved, re-encoded, sorted or re-ordered. |
| R2.2 | The raw CSV is opened **read-only**. No process in this project acquires a write handle to it. |
| R2.3 | **No column is added to the raw file** — in particular not `source_row_id`, which exists only in staging (§9). |
| R2.4 | All **1,000,000 source rows are preserved** into staging. No row is dropped, filtered, sampled or de-duplicated for any reason. |
| R2.5 | All **33 source columns are preserved** into staging, including columns proven redundant (§8) and the constant `unrealistic_salary_flag`. |
| R2.6 | The file's sha256 is verified **before and after** every run. A mismatch is a hard failure, not a warning. |
| R2.7 | Cleaning output is written to a **separate staging dataset**. Staging never writes back into `data/raw/`. |

The expected sha256 is
`3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398`. Both the
profiling run and the audit run verified it and left the file byte-identical.

**Reading requirement.** `company_name` contains embedded commas and is quoted
in the CSV (e.g. `"Russell, Medina and Evans"`). The file **must** be read with
a quote-aware CSV parser. Naive delimiter splitting shifts every field after
`company_name` and silently corrupts all downstream columns — this was confirmed
in practice, not assumed.

---

## 3. Cleaning philosophy

The governing principle is **preservation over correction**.

This is a Data Warehouse and OLAP pipeline. Staging's job is to make the source
loadable, typed and traceable — not to improve it. Every transformation is a
loss of information that a later analyst cannot undo.

Five rules follow from that:

**3.1 — Evidence precedes action.** No column is cleaned because it *looks*
dirty. The profiling and audit phases measured the dataset, and only a measured
defect justifies a change. Where the measurement found no defect, the column is
passed through untouched.

**3.2 — An anomaly is not an error.** Several genuinely surprising patterns were
found: domains older than their companies, a constant flag, a 46.9% rate on a
cross-field inequality, near-uniform categorical distributions, a long tail in
`grammatical_errors`. None is *evidence of invalidity*. An unexplained value is
preserved and documented; it is not corrected into something explicable.

**3.3 — Redundancy is documented, not resolved.** Two column pairs were proven
mathematically redundant on this extract (§8). Neither is dropped. A property
holding across 1,000,000 rows of one extract does not prove the source system
enforces it, and dropping a column is irreversible while carrying it is nearly
free. The decision belongs to dimensional modelling.

**3.4 — Missing means missing.** A NULL is a fact about the data. Replacing it
with a mean, a median or a zero manufactures a value that was never observed and
disguises the gap from every downstream consumer (§5).

**3.5 — Staging is not feature engineering.** No encoding, scaling, resampling
or text processing happens here (§11). Those belong to a modelling workflow,
which this is not.

**Consequence.** The staging dataset is a **faithful, typed, addressable**
rendering of the raw extract: same 1,000,000 rows, same 33 source columns, same
values, plus two lineage/quality fields and a validation report.

---

## 4. Column and column-group cleaning rules

### 4.1 Row identity — staging-derived

See §9 for the full lineage policy.

| Rule | Detail |
| --- | --- |
| R4.1.1 | Add **`source_row_id`** to the **staging** dataset only. |
| R4.1.2 | It starts at **1** and follows the **original CSV row order**, assigned before any filter, sort or transformation. |
| R4.1.3 | It is **not** added to the raw file. |
| R4.1.4 | Expected result: values 1…1,000,000, contiguous, unique, non-null. |

**Why** — profiling tested all 33 columns and the composites: **no natural
single-column key exists** and none is near-unique (ratio ≥ 0.99). The most
distinctive column, `company_name`, is only 53.5938% unique. Without a surrogate
there is no way to address an individual row.

### 4.2 `posting_date`

| Rule | Detail |
| --- | --- |
| R4.2.1 | Parse `posting_date` as a **real date**, not text. |
| R4.2.2 | Store and output it in **ISO `YYYY-MM-DD`**. |
| R4.2.3 | Any value that fails to parse **must be reported** in the validation output. It is not coerced, defaulted or dropped silently. |
| R4.2.4 | **Future dates are NOT removed.** |
| R4.2.5 | Add the staging-derived flag **`is_future_posting`**: `1` when `posting_date > 2026-09-23`, `0` otherwise. |
| R4.2.6 | The cutoff **2026-09-23** is the **audit/reference date** — a fixed documented constant. |

**Evidence** — 100.00% of values parse as `%Y-%m-%d`; 0 unparseable values.
Range 2018-01-01 to 2026-12-31. **30,246 rows (3.0246%)** post-date the
reference date, across 99 distinct dates.

**Why future dates are kept** — they are not a parse failure and not a
corruption; they are simply dated ahead of the reference date. Their fraud rate
(22.2939%) is indistinguishable from the overall rate (22.1958%), so removing
them would discard 3% of the dataset without removing any identifiable defect.
Flagging preserves the information and lets any analysis exclude them
explicitly.

**Why the cutoff is a fixed constant, not "today"** — deriving the flag from the
current date would make the staging dataset non-reproducible: the count of
flagged rows would drift on every run and no output could be compared with
another. Pinning it to 2026-09-23 makes `is_future_posting` deterministic and
reproducible, and it matches the date the audit evidence was generated.

### 4.3 Text and categorical columns

Applies to: `internship_title`, `employment_type`, `work_mode`, `industry`,
`location`, `company_name`, `company_size`, `recruiter_email_type`.

| Rule | Detail |
| --- | --- |
| R4.3.1 | **Preserve original values verbatim.** |
| R4.3.2 | Do **not** lowercase or alter case in any way. |
| R4.3.3 | Do **not** trim — **unless** validation unexpectedly finds a defect, which is then escalated, not silently fixed. |
| R4.3.4 | Do **not** map categories. |
| R4.3.5 | Do **not** merge categories. |

**Evidence** — all eight columns were measured clean on every string-quality
dimension:

| Check | Result across all 8 columns |
| --- | ---: |
| Whitespace-padded values | **0** |
| Empty strings | **0** |
| Whitespace-only values | **0** |
| Non-ASCII characters | **0** |
| Double spaces | **0** |
| Case-variant duplicates | **0** |

For every one of these columns, `distinct` = `distinct (case-insensitive)` =
`distinct (trimmed + case-insensitive)`. There is no defect to clean.

**Why trimming is still forbidden by default** — a `TRIM` or `LOWER` applied
"just in case" is an unconditional transformation with no measured
justification. If a future extract does contain padding, R4.3.3 requires the
validation step to **surface** it so a human decides, rather than having the
pipeline quietly absorb a change in source behaviour.

**Why categories are not merged** — the value domains are small and fully
enumerated in the data dictionary. Merging would require a business judgement
nobody has made. Two cases specifically:
`company_size` mixes a maturity label (`Startup`) with scale labels
(`Small`/`Medium`/`Enterprise`), so **no ordinal ranking is imposed**; and
`company_name`'s recurring `<Surname> <Suffix>` pattern means **name similarity
must not be treated as company identity** — no fuzzy matching or entity
resolution is performed.

### 4.4 Missing numeric values

Covered by the missing-value policy in §5. Applies to `company_age`, `stipend`
and `trust_signal_score`.

### 4.5 Binary indicators

Applies to: `linkedin_presence`, `website_available`, `verification_status`,
`unrealistic_salary_flag`, `payment_required`, `fake_certificate_offer`,
`suspicious_email_domain`, `social_media_presence`, `is_fake_posting`.

| Rule | Detail |
| --- | --- |
| R4.5.1 | **Preserve the 0/1 representation.** Do not convert to boolean, `Y`/`N`, `true`/`false` or any label. |
| R4.5.2 | **Validate** that values remain strictly within `{0,1}`. |
| R4.5.3 | Do **not** rebalance, resample or reweight. |
| R4.5.4 | Do **not** remove rows on the basis of any flag value. |

**Evidence** — all nine columns are strictly `{0,1}` with **zero** nulls and
zero out-of-domain values:

| Column | Count 0 | Count 1 | % = 1 |
| --- | ---: | ---: | ---: |
| `linkedin_presence` | 199,236 | 800,764 | 80.0764% |
| `website_available` | 150,403 | 849,597 | 84.9597% |
| `verification_status` | 300,287 | 699,713 | 69.9713% |
| `unrealistic_salary_flag` | 1,000,000 | **0** | 0.0000% |
| `payment_required` | 900,095 | 99,905 | 9.9905% |
| `fake_certificate_offer` | 920,170 | 79,830 | 7.9830% |
| `suspicious_email_domain` | 749,433 | 250,567 | 25.0567% |
| `social_media_presence` | 250,200 | 749,800 | 74.9800% |
| `is_fake_posting` | 778,042 | 221,958 | 22.1958% |

The staging type is `SMALLINT`, not a native boolean, so that R4.5.1 is honoured
literally in the schema.

**`unrealistic_salary_flag` — constant zero.**

| Rule | Detail |
| --- | --- |
| R4.5.5 | It is **constant 0** across all 1,000,000 rows in this extract. |
| R4.5.6 | **Keep it in staging.** |
| R4.5.7 | Document it as a **candidate for exclusion from the analytical warehouse** — a decision deferred to dimensional modelling (§8.4). |

**Why it is kept** — a constant column carries no information for slicing and
would produce a single-member degenerate dimension, so it is a reasonable
candidate for exclusion *later*. But constant *in this extract* is not the same
as constant *in the source system*: a later extract could contain `1`s. Dropping
it at staging would hide that change; keeping it makes the change visible.

**Why class imbalance is untouched** — the 78/22 split of `is_fake_posting` is
the real class balance of this population. Resampling it would corrupt every
OLAP aggregate built on the fact table, which is the opposite of what this
pipeline is for (see §11).

### 4.6 `payment_required` / `registration_fee`

| Rule | Detail |
| --- | --- |
| R4.6.1 | **Keep both fields** in staging. |
| R4.6.2 | Do **not** derive one from the other, in either direction. |
| R4.6.3 | **Validate** that the invariant still holds on every load. |
| R4.6.4 | Document the redundancy for later dimensional-model review (§8.1). |

**Proven invariant** — `payment_required == (registration_fee > 0)` for **all
1,000,000 source rows**: 0 rows with `payment_required = 0` and a positive fee,
0 rows with `payment_required = 1` and a zero fee.

`registration_fee` zeros are **meaningful, not placeholders**: the exact
agreement with `payment_required = 0` across 900,095 rows confirms that zero
means "no fee requested".

### 4.7 `recruiter_email_type` / `suspicious_email_domain`

| Rule | Detail |
| --- | --- |
| R4.7.1 | **Preserve both fields** in staging. |
| R4.7.2 | Document the exact relationship (§8.2). |
| R4.7.3 | Do **NOT** automatically delete either field. |
| R4.7.4 | Defer redundancy handling to dimensional modelling. |

**Proven bijection** — `Corporate ↔ 0` and `Free ↔ 1`, with **zero violations**
out of 1,000,000 rows, functional dependency holding in **both** directions, and
Cramér's V = **1.000000**.

### 4.8 `fraud_score` / `is_fake_posting`

| Rule | Detail |
| --- | --- |
| R4.8.1 | **Preserve both columns.** |
| R4.8.2 | Do **not** derive `is_fake_posting` from `fraud_score`. |
| R4.8.3 | Do **not** modify either column's values. |

**Evidence that no threshold works** — an exhaustive scan over every observed
`fraud_score` value found the best rule to be `fraud_score >= 50`, which still
leaves **607 mismatches** (607 false positives, 0 false negatives). **Perfect
reproduction is impossible.** The disagreement sits at exactly one score value:
at `fraud_score = 50.0`, 607 rows are labelled 0 and 620 are labelled 1.

**Why this matters** — a pipeline that derived the label from a threshold would
mislabel those 607 rows and, worse, would present a derived value as if it were
observed. Both columns are carried as they are.

### 4.9 `trust_signal_score` and the trust flags

| Rule | Detail |
| --- | --- |
| R4.9.1 | `trust_signal_score` is **not** deterministic from `verification_status`, `linkedin_presence`, `website_available`, `social_media_presence`. |
| R4.9.2 | **Keep all five fields unchanged.** |
| R4.9.3 | Never reconstruct or impute the score from the flags. |

**Evidence** — all 16 flag combinations occur; the largest within-combination
range of the score is **100.0** (the full scale); the largest within-combination
standard deviation is 15.5713; one combination contains 986 distinct scores. The
saturated model explains only **R² = 0.137190**. Two of the four flags
(`website_available` at r = -0.001497, `social_media_presence` at r = 0.001566)
have effectively **no** relationship with the score at all.

### 4.10 `company_age` / `domain_age_months`

| Rule | Detail |
| --- | --- |
| R4.10.1 | Some domain ages exceed company ages. |
| R4.10.2 | **Do NOT modify these records** — the relationship is **not sufficient evidence of invalidity**. |

**Evidence** — 469,297 rows (46.9297% of all rows; 47.4037% of the 990,000
comparable rows) have `domain_age_months > company_age * 12`. Excess ranges from
1 to 73 months, median 10. Pearson r between the two on a common scale is 0.9940.

**Why nothing is changed** — a domain can legitimately predate the company using
it: acquired domains, rebrands, parked domains and holding-company registrations
all produce exactly this pattern. The unit difference (years vs months) also
makes `company_age` the coarser measurement, so small excesses are expected from
rounding alone. Nearly half the dataset shows the pattern; treating it as a
defect would mean rewriting half the extract on an assumption.

### 4.11 Score columns — range validation

Applies to: `vague_description_score`, `urgency_score`, `keyword_spam_score`,
`emotional_manipulation_score`, `phishing_language_score`, `trust_signal_score`,
`fraud_score`.

| Rule | Detail |
| --- | --- |
| R4.11.1 | **Preserve values.** |
| R4.11.2 | **Validate `0 <= value <= 100`** where the value is non-null. |

**Evidence** — every one of the seven columns lies entirely within 0–100:
**0 values below 0 and 0 above 100**, in all cases. The 0–100 range is therefore
safe to declare as a check constraint in staging.

The `where non-null` qualifier matters for exactly one column:
`trust_signal_score` has 10,000 nulls. The other six have none.

**Note** — being inside 0–100 validates the *range* only, not correctness.

### 4.12 Numeric outliers

| Rule | Detail |
| --- | --- |
| R4.12.1 | Do **not** delete outliers. |
| R4.12.2 | Do **not** winsorize. |
| R4.12.3 | Do **not** cap or clip. |
| R4.12.4 | Do **not** normalize. |
| R4.12.5 | Do **not** standardize. |
| R4.12.6 | IQR results are **descriptive only**. |

Detail and rationale in §7.

### 4.13 Duplicate rows

| Rule | Detail |
| --- | --- |
| R4.13.1 | There are **zero exact duplicate rows**. |
| R4.13.2 | **Perform the validation**, but **do not deduplicate anything.** |

**Evidence** — across 1,000,000 rows and all 33 columns, exact duplicates
(excess copies, `duplicated(keep='first')`) = **0**. Distinct rows = 1,000,000.

**Why the check is still run** — it is a regression check on the source, not a
cleaning step. If a future extract contains duplicates, the load must surface
that rather than absorb it. And because `keep='first'` deduplication would
silently destroy rows, R4.13.2 makes the check strictly read-only.

**Note** — near-duplicates were deliberately **not** searched for: an all-pairs
comparison is O(n²) and infeasible at this row count. This is a known,
documented gap, not an oversight.

---

## 5. Missing-value policy

**Only three columns have missing values**, each at exactly 1.0000%:

| Column | Missing | Missing % | Staging type |
| --- | ---: | ---: | --- |
| `company_age` | 10,000 | 1.0000% | `SMALLINT NULL` |
| `stipend` | 10,000 | 1.0000% | `INTEGER NULL` |
| `trust_signal_score` | 10,000 | 1.0000% | `DECIMAL(4,1) NULL` |

The other 30 columns are complete. Total missing cells: 30,000 of 33,000,000
(0.0909%).

Text columns contain **no empty strings and no whitespace-only values**, so for
those columns the null count is the complete missingness picture — there is no
hidden missingness disguised as text.

### Rules

| Rule | Detail |
| --- | --- |
| R5.1 | **Preserve missing values as NULL/NaN.** |
| R5.2 | Do **NOT** impute the mean. |
| R5.3 | Do **NOT** impute the median. |
| R5.4 | Do **NOT** replace with zero. |
| R5.5 | Do **NOT** remove rows because of these missing values. |
| R5.6 | Do **not** add a "missing" sentinel value or an "unknown" member at the staging layer. |
| R5.7 | The three columns are declared `NULL`-able in staging; the other 30 are `NOT NULL`. |

### Why

**Imputation destroys a measured fact.** Each gap is exactly 1.0000% — the
missingness is a real property of the extract, and it was measured, not guessed.

**Zero would be actively wrong** in all three cases. `stipend` has **no zeros at
all** (minimum 2,000) and `company_age` has **no zeros at all** (minimum 1), so
inserting zeros would create values that do not occur anywhere in the observed
domain and would sit far below the real minimum. `trust_signal_score` does have
479 genuine zeros, so zero-filling would make 10,000 unknown rows
indistinguishable from 479 genuinely-zero ones.

**Mean or median would fabricate precision.** It would pull 10,000 rows onto a
single point, shrinking variance and biasing every OLAP aggregate that touches
the column — silently, because nothing downstream would show the values were
invented.

**Dropping rows would lose more than it fixes.** The three gaps are **not** a
single record-level dropout. No row is missing all three values, no two masks
are identical, and pairwise overlaps (88, 96, 88) sit essentially at what
independence predicts (100). **29,728 distinct rows** are missing at least one
value — dropping them would discard almost 3% of the dataset, including columns
that are perfectly populated in those rows.

**The missingness carries almost no label information**, so there is no
signal-preservation argument for special handling either:

| Column | Fraud rate, missing rows | Fraud rate, present rows | Gap |
| --- | ---: | ---: | ---: |
| `company_age` | 22.0000% | 22.1978% | -0.1978 pp |
| `stipend` | 21.9600% | 22.1982% | -0.2382 pp |
| `trust_signal_score` | 22.3800% | 22.1939% | +0.1861 pp |

All three gaps are under a quarter of a percentage point. This is evidence that
the missingness is uninformative; it is **not** proof, and it says nothing about
association with other columns.

**Whether these are structurally missing or collection gaps cannot be decided
from the data.** That distinction determines whether the warehouse eventually
uses a NULL, an "unknown" dimension member, or an empty fact measure — a
**dimensional-model decision**, explicitly deferred. Staging keeps the NULL so
that all three options remain open.

---

## 6. Date-quality policy

### Rules

| Rule | Detail |
| --- | --- |
| R6.1 | Parse `posting_date` as a real date. |
| R6.2 | Store/output as ISO **`YYYY-MM-DD`**. |
| R6.3 | **Invalid parsing must be reported** — never silently coerced, defaulted or null-filled. |
| R6.4 | **Do NOT remove future dates.** |
| R6.5 | Add staging-derived `is_future_posting`: `1` when `posting_date > 2026-09-23`, else `0`. |
| R6.6 | The cutoff **2026-09-23** is the documented **audit/reference date**. |

### Measured date quality

| Metric | Value |
| --- | ---: |
| Parse success (`%Y-%m-%d`) | **100.00%** |
| Values unparseable in that format | **0** |
| Values unparseable in any format | **0** |
| Minimum | 2018-01-01 |
| Maximum | 2026-12-31 |
| Distinct dates | 3,287 |
| Span in days | 3,286 |
| Calendar days with at least one row | **100%** — no gap day |
| Rows before 2018-01-01 | 0 |
| **Rows after 2026-09-23** | **30,246 (3.0246%)** |
| Distinct future dates | 99 |

Future rows by month: 2026-09 → 2,195; 2026-10 → 9,435; 2026-11 → 9,195;
2026-12 → 9,421.

### Why future dates are flagged rather than removed

They are **not** a parse failure — every one is a valid, well-formed date. Being
later than the reference date makes a row *notable*, not *invalid*.

Their fraud rate is **22.2939%** against a dataset-wide **22.1958%** — a
difference of under 0.1 pp. Future dating carries no label signal, so removal
would cost 3% of the data and buy nothing.

Flagging is strictly more useful than filtering: any analysis can exclude
`is_future_posting = 1` when it needs to, and no analysis can recover rows that
staging already deleted.

### Why the cutoff is a fixed constant

`2026-09-23` is hard-coded, **not** computed from the system clock. Using "today"
would make the staging dataset non-reproducible — the flagged row count would
drift with every run and two loads of the same file would disagree. Pinning the
constant makes `is_future_posting` deterministic and makes the 30,246 figure a
verifiable expectation. The date is the one the profiling and audit evidence was
generated against.

### Other date observations — recorded, not acted on

- Every calendar day in the range is populated, with rows spread almost evenly
  (coefficient of variation 0.0558) and weekday shares of 14.2196%–14.3617%
  against a uniform 14.2857%.
- Near-even loading across every day including weekends and holidays is not
  typical of real job-posting activity.

These are **provenance observations** requiring source documentation to resolve.
They are not data-quality defects and trigger **no** transformation.

### Columns that look like dates but are not

`recruiter_experience_years` and `recruiter_response_time_hours` matched the
profiler's date-name heuristic (their names contain `years` and `time`) but are
**duration measures**, with 0.00% parse success. They are **not** parsed as
dates. This is recorded so the heuristic stays auditable.

---

## 7. Outlier policy

### Rules

| Rule | Detail |
| --- | --- |
| R7.1 | Do **NOT** delete outliers. |
| R7.2 | Do **NOT** winsorize. |
| R7.3 | Do **NOT** cap or clip. |
| R7.4 | Do **NOT** normalize. |
| R7.5 | Do **NOT** standardize. |
| R7.6 | IQR results are **descriptive only** — a screening device, never a verdict. |

### Measured outlier counts (1.5 × IQR fences)

| Column | Lower fence | Upper fence | IQR outliers | % |
| --- | ---: | ---: | ---: | ---: |
| `company_age` | -20.00 | 60.00 | **0** | 0.0000% |
| `stipend` | -5,583.50 | 75,548.50 | 3,348 | 0.3348% |
| `registration_fee` | 0.00 | 0.00 | 99,905 | 9.9905% |
| `job_description_length` | 183.00 | 3,415.00 | 7,040 | 0.7040% |
| `grammatical_errors` | -1.00 | 7.00 | **11,891** | **1.1891%** |
| `recruiter_experience_years` | -3.00 | 13.00 | 3,585 | 0.3585% |
| `recruiter_response_time_hours` | -9.20 | 45.20 | 3,217 | 0.3217% |

Also flagged among the score columns: `vague_description_score` 3,472 (0.3472%),
`keyword_spam_score` 3,451 (0.3451%), `emotional_manipulation_score` 3,516
(0.3516%), `phishing_language_score` 2,650 (0.2650%), `trust_signal_score` 4,510
(0.4510%), `fraud_score` 8,881 (0.8881%). `urgency_score` has **0**.

Total flagged: 128,986 observations. Excluding the degenerate-fence columns:
**29,081**.

### Why nothing is treated

**No negative value exists anywhere in the dataset.** Not one numeric column
contains a negative, so there is no sign error to correct.

**The flagged values are ordinary long tails.** A high stipend, a slow recruiter
response and a long job description are all genuinely possible. Their share is
tiny — mostly around 0.3%.

**`grammatical_errors` has the largest share (1.1891%) and is bounded 0–14.** A
maximum of 14 grammatical errors is entirely plausible for a real posting. The
fence at 7 is an artefact of a tight, small-integer distribution, not a sign of
corruption.

**The `registration_fee` fence is meaningless.** Q1 and Q3 are both 0, so the
interquartile range collapses to 0 and both fences land on 0 — every non-zero
value is flagged **by construction**. Read that 99,905 as "rows with a non-zero
fee", not as extreme observations. Acting on it would delete every paying row in
the dataset, destroying exactly the population a scam-detection warehouse exists
to study.

**Scaling and standardizing have no place here.** They are model-preparation
steps. A standardized `stipend` is unreadable in an OLAP report and cannot be
summed, averaged or drilled into meaningfully, and the transform would have to
be reversed for every query.

---

## 8. Redundancy observations

Four redundancy findings. **None causes a column to be dropped or derived at the
staging layer.** Each is recorded as an open question for the dimensional model.

### 8.1 `payment_required` ≡ `registration_fee > 0` — exact

| Check | Rows | % |
| --- | ---: | ---: |
| `payment_required = 0` AND `registration_fee > 0` | **0** | 0.0000% |
| `payment_required = 1` AND `registration_fee = 0` | **0** | 0.0000% |
| Consistent, both zero | 900,095 | 90.0095% |
| Consistent, flag set and fee positive | 99,905 | 9.9905% |

`payment_required` is fully recoverable from `registration_fee`.

**Staging** — keep both, derive neither, validate the invariant on every load.
**Deferred to dimensional modelling** — whether the flag becomes a dimension
attribute and the fee a fact measure, or whether only the fee is carried.

### 8.2 `recruiter_email_type` ↔ `suspicious_email_domain` — perfect bijection

| | `suspicious_email_domain` = 0 | = 1 | Total |
| --- | ---: | ---: | ---: |
| `Corporate` | 749,433 | **0** | 749,433 |
| `Free` | **0** | 250,567 | 250,567 |

Functional dependency holds in **both** directions, 0 violating rows out of
1,000,000, Cramér's V = **1.000000**. The two columns carry identical
information on this extract.

**Staging** — preserve both; **do not** automatically delete either.
**Deferred to dimensional modelling** — how to resolve the duplication.

**Why neither is deleted now** — the proof covers *this extract*, not the source
system. `recruiter_email_type` is a **label** with room for values beyond two; a
future extract could contain a third email type, which the boolean flag could
not represent. Carrying both preserves that headroom at negligible cost, and the
deletion is irreversible while the redundancy is not harmful.

### 8.3 `fraud_score` vs `is_fake_posting` — **not** redundant

Listed here because it is easy to *assume* redundancy. The audit disproves it.

| Metric | Value |
| --- | ---: |
| Best threshold | `fraud_score >= 50` |
| **Mismatches** | **607** |
| Accuracy | 99.939300% |
| **Perfect reproduction possible** | **NO** |
| Distinct scores where both classes occur | **1** (exactly 50.0) |

**Staging** — preserve both; derive neither.
**Deferred to dimensional modelling** — which becomes a fact measure and which a
dimension attribute. The boundary behaviour at `fraud_score = 50.0` is a
**question for the source owner**, not something the data can settle.

### 8.4 `unrealistic_salary_flag` — constant, no information

Constant `0` across all 1,000,000 rows. It would produce a single-member
degenerate dimension and cannot support any slicing.

**Staging** — keep and validate.
**Deferred to dimensional modelling** — **candidate for exclusion from the
analytical warehouse.** Kept in staging because constant-in-this-extract is not
constant-in-the-source-system.

### 8.5 Non-redundancy explicitly established

Recorded so nobody re-opens these as "obvious" simplifications:

- **`trust_signal_score` is NOT derivable** from `verification_status`,
  `linkedin_presence`, `website_available`, `social_media_presence`. Largest
  within-combination range 100.0 (full scale); saturated R² = 0.137190. All five
  columns are kept.
- **`domain_age_months` is NOT a restatement of `company_age`.** Despite r =
  0.9940, 469,297 rows have a domain older than the company. Both are kept.

---

## 9. Row lineage policy

### Rules

| Rule | Detail |
| --- | --- |
| R9.1 | There is **no natural single-column key** in the source. |
| R9.2 | Add **`source_row_id`** to the **STAGING** dataset. |
| R9.3 | It starts at **1** and follows the **original CSV row order**. |
| R9.4 | It is assigned **before** any filter, sort or transformation. |
| R9.5 | **Do NOT add `source_row_id` to the raw file.** |
| R9.6 | Record it together with the source file's **sha256** in the load audit record. |
| R9.7 | It is a **lineage handle, not a business key**. It must **not** be used to join across extracts. |

### Evidence

Profiling tested all 33 columns and composite combinations:

| Test | Result |
| --- | ---: |
| Columns satisfying strict uniqueness | **0** |
| Columns near-unique (ratio ≥ 0.99) | **0** |
| Highest-cardinality column | `company_name` — 535,938 distinct (53.5938%) |
| Its most frequent value | `Smith PLC`, 1,248 occurrences |
| Unique composites found | **none** |

**No primary key was declared by the profiling or audit scripts, and none was
added to the raw data.** `source_row_id` is the single recommendation those
phases made, and it applies to the staging layer only.

### Why file order

Because the source offers nothing else. With no natural key, file position is
the only stable way to point from a warehouse row back to a specific line of
this extract.

### Why it is not a business key

Its meaning depends entirely on **which file** it came from. Row 5 of this
extract and row 5 of a re-issued extract are different postings. That is why
R9.6 requires the sha256 to be stored alongside it — the pair
`(sha256, source_row_id)` is the actual identifier — and why R9.7 forbids
cross-extract joins. It carries no business meaning and is not a posting ID.

### Expected outcome

Values 1…1,000,000, contiguous, unique, non-null — one per preserved source row.

---

## 10. Validation requirements

The staging load must run every check below and emit a validation report. A
check that fails is **reported**; the pipeline does **not** silently repair the
data. Expected values are taken from the profiling and audit evidence, so any
deviation means the source changed.

### 10.1 Integrity and lineage

| # | Check | Expected |
| --- | --- | --- |
| V1 | Raw file sha256 before and after the run | `3463d99b…f3b1398`, unchanged |
| V2 | Raw file not modified | byte-identical |
| V3 | Source row count | **1,000,000** |
| V4 | Source column count | **33** |
| V5 | Staging row count equals source row count | **1,000,000** |
| V6 | All 33 source columns present in staging | yes |
| V7 | `source_row_id` unique, non-null, contiguous 1…1,000,000 | yes |
| V8 | `source_row_id` order matches original file order | yes |
| V9 | CSV read with a quote-aware parser | required (`company_name` has embedded commas) |

### 10.2 Dates

| # | Check | Expected |
| --- | --- | --- |
| V10 | `posting_date` parse failures | **0** — any failure **must be reported** |
| V11 | Output format | ISO `YYYY-MM-DD` |
| V12 | Min / max | 2018-01-01 / 2026-12-31 |
| V13 | Distinct dates | 3,287 |
| V14 | `is_future_posting = 1` count | **30,246** (3.0246%) |
| V15 | `is_future_posting` computed against the fixed constant 2026-09-23 | yes — never the system clock |
| V16 | No row removed for being future-dated | 1,000,000 retained |

### 10.3 Missing values

| # | Check | Expected |
| --- | --- | --- |
| V17 | `company_age` nulls | **10,000** (1.0000%) |
| V18 | `stipend` nulls | **10,000** (1.0000%) |
| V19 | `trust_signal_score` nulls | **10,000** (1.0000%) |
| V20 | Nulls in the other 30 columns | **0** |
| V21 | No imputation applied | null counts unchanged from source |
| V22 | Rows missing at least one of the three | 29,728 |
| V23 | Rows missing all three | **0** |

### 10.4 Binary flags

| # | Check | Expected |
| --- | --- | --- |
| V24 | All nine flags strictly within `{0,1}` | yes, 0 violations |
| V25 | No nulls in any flag | **0** |
| V26 | 0/1 representation preserved (not boolean/text) | yes |
| V27 | Per-flag counts match §4.5 | exact match |
| V28 | `unrealistic_salary_flag` still constant 0 | 1,000,000 zeros — **report if it changes** |

### 10.5 Cross-column invariants

| # | Check | Expected |
| --- | --- | --- |
| V29 | `payment_required == (registration_fee > 0)` | **0 violations** |
| V30 | `registration_fee >= 0` | **0 negatives** |
| V31 | `recruiter_email_type='Corporate'` ⟺ `suspicious_email_domain=0` | **0 violations** |
| V32 | `recruiter_email_type='Free'` ⟺ `suspicious_email_domain=1` | **0 violations** |
| V33 | Neither column of either pair was dropped | both present |
| V34 | `is_fake_posting` not derived from `fraud_score` | label values byte-identical to source |

### 10.6 Ranges and domains

| # | Check | Expected |
| --- | --- | --- |
| V35 | Seven score columns satisfy `0 <= value <= 100` where non-null | **0 out-of-range** |
| V36 | No negative value in any numeric column | **0** |
| V37 | `company_age` within 1–39 | yes |
| V38 | `domain_age_months` within 1–500 | yes |
| V39 | `stipend` within 2,000–110,428 where non-null | yes |
| V40 | `registration_fee` within 0–4,999 | yes |
| V41 | `job_description_length` within 100–5,000 | yes |
| V42 | `grammatical_errors` within 0–14 | yes |
| V43 | `recruiter_experience_years` within 0.0–19.6 | yes |
| V44 | `recruiter_response_time_hours` within 1.0–63.9 | yes |

### 10.7 Text quality

| # | Check | Expected |
| --- | --- | --- |
| V45 | Whitespace-padded values across the 8 text columns | **0** — **report, do not trim** |
| V46 | Empty strings | **0** |
| V47 | Whitespace-only values | **0** |
| V48 | Distinct counts unchanged vs source | `internship_title` 9, `employment_type` 4, `work_mode` 3, `industry` 9, `location` 9, `company_size` 4, `recruiter_email_type` 2, `company_name` 535,938 |
| V49 | No case folding applied | distinct = case-insensitive distinct |
| V50 | Category domains unchanged | exactly the values in the data dictionary |

V45 is the trigger for R4.3.3: if padding unexpectedly appears, the validation
**surfaces it for a human decision**. The pipeline does not trim on its own.

### 10.8 Duplicates and outliers

| # | Check | Expected |
| --- | --- | --- |
| V51 | Exact duplicate rows | **0** — check only, **never deduplicate** |
| V52 | Distinct rows | 1,000,000 |
| V53 | No outlier deleted, capped or winsorized | distributions match source |
| V54 | IQR statistics recomputed as descriptive output only | no values altered |

### 10.9 Typing

| # | Check | Expected |
| --- | --- | --- |
| V55 | `posting_date` is a real `DATE` | yes |
| V56 | `company_age`, `stipend` load as integers without loss | **0 non-integral values** in source |
| V57 | One-decimal columns retain precision | `recruiter_experience_years`, `recruiter_response_time_hours`, `trust_signal_score`, `fraud_score` |
| V58 | No value changed by a type conversion | round-trip comparison against source |

---

## 11. Explicit transformations NOT performed

Everything below was **considered and deliberately rejected**. This section
exists so a later reader can distinguish *decided against* from *overlooked*.
Doing any of these would be a departure from the approved rules.

### 11.1 Raw data

- ❌ Modifying, overwriting or re-saving the raw CSV
- ❌ Adding any column to the raw file, including `source_row_id`
- ❌ Dropping, filtering or sampling any of the 1,000,000 rows
- ❌ Re-ordering or sorting the source

### 11.2 Missing values

- ❌ Mean imputation
- ❌ Median imputation
- ❌ Zero replacement
- ❌ Mode / constant / sentinel filling
- ❌ Forward-fill, back-fill or interpolation
- ❌ Model-based imputation (kNN, MICE, regression)
- ❌ Dropping rows with missing values
- ❌ Dropping `company_age`, `stipend` or `trust_signal_score` for incompleteness
- ❌ Reconstructing `trust_signal_score` from the four trust flags

### 11.3 Text and categorical

- ❌ Lowercasing or any case folding
- ❌ Trimming or whitespace normalisation (no defect exists; V45 reports instead)
- ❌ Category mapping, renaming or recoding
- ❌ Category merging or grouping of rare values
- ❌ Imposing an ordinal ranking on `company_size`
- ❌ Fuzzy matching, entity resolution or grouping of `company_name`
- ❌ Standardising `location` to countries/regions or geographic enrichment

### 11.4 Dates

- ❌ Removing future-dated rows
- ❌ Clipping `posting_date` to the reference date
- ❌ Silently coercing or null-filling an unparseable date
- ❌ Computing `is_future_posting` from the system clock instead of 2026-09-23
- ❌ Parsing `recruiter_experience_years` or `recruiter_response_time_hours` as dates

### 11.5 Outliers and distributions

- ❌ Deleting outliers
- ❌ Winsorizing
- ❌ Capping or clipping
- ❌ Normalizing
- ❌ Standardizing
- ❌ Log or power transforms
- ❌ Binning or discretizing continuous measures
- ❌ Acting on the degenerate `registration_fee` IQR fence

### 11.6 Redundancy

- ❌ Dropping `payment_required` because it equals `registration_fee > 0`
- ❌ Dropping `registration_fee` in favour of the flag
- ❌ Dropping `recruiter_email_type` or `suspicious_email_domain`
- ❌ Deriving `is_fake_posting` from a `fraud_score` threshold
- ❌ Deriving `fraud_score` from the label
- ❌ Dropping `unrealistic_salary_flag` from staging for being constant
- ❌ Dropping `company_age` or `domain_age_months` as duplicative

### 11.7 Records flagged but not altered

- ❌ Modifying the 469,297 rows where the domain is older than the company
- ❌ Deleting or correcting the 30,246 future-dated rows
- ❌ Adjusting the 1,227 rows at `fraud_score = 50.0`
- ❌ Deduplicating anything (there are no exact duplicates)

### 11.8 Machine-learning preprocessing

**None of this belongs in a Data Warehouse and OLAP pipeline.**

- ❌ One-hot encoding
- ❌ Label encoding for dimensions
- ❌ Ordinal encoding
- ❌ `MinMaxScaler`
- ❌ `StandardScaler`
- ❌ Any other scaler or normalizer
- ❌ SMOTE
- ❌ Undersampling
- ❌ Oversampling
- ❌ Class weighting or rebalancing of `is_fake_posting`
- ❌ TF-IDF
- ❌ Stemming
- ❌ Lemmatization
- ❌ Stop-word removal, tokenisation or any NLP step
- ❌ Feature selection or dimensionality reduction (PCA and similar)
- ❌ Train/test splitting

Note that the text-processing items are doubly inapplicable: the dataset
contains **no free-text column at all**. `job_description_length` is a numeric
length; the description itself is not in the data.

### 11.9 Not attempted, and why

- **Near-duplicate detection.** An all-pairs comparison is O(n²) and infeasible
  at 1,000,000 rows. A blocked approach could be added later if it matters. This
  is a known, documented gap.
- **Testing missingness against columns other than the label.** Missingness was
  tested for association with `is_fake_posting` only.
- **Resolving provenance.** The exactly-round row count, the near-uniform
  categorical splits, the 100% calendar coverage, the three exactly-1.0000%
  missingness rates, the zero duplicates and the flawless text cleanliness are
  **recorded as observations**. They do **not** establish that the data is
  synthetic — each is equally consistent with a real dataset already cleaned and
  sampled upstream. Resolving it requires the source documentation, not more
  analysis. Until then the dataset's realism is **unverified**, rather than
  confirmed or denied.

---

## 12. Decisions deferred to dimensional modelling

Collected for the next phase. **None of these is resolved here.**

| # | Open question | Evidence |
| --- | --- | --- |
| D1 | Resolve the `payment_required` / `registration_fee` redundancy — flag as dimension attribute and fee as measure, or fee alone? | §8.1 |
| D2 | Resolve the `recruiter_email_type` / `suspicious_email_domain` bijection — keep the label, the flag, or both? | §8.2 |
| D3 | Exclude `unrealistic_salary_flag` from the analytical warehouse? (constant, single-member degenerate dimension) | §8.4 |
| D4 | Which of `fraud_score` / `is_fake_posting` becomes a fact measure and which a dimension attribute? | §8.3 |
| D5 | Ask the source owner how `fraud_score = 50.0` is resolved into a label | §8.3 |
| D6 | Keep `trust_signal_score` alongside the four trust flags? (a derived measure can still be worth storing) | §8.5 |
| D7 | `posting_date` — own time dimension, degenerate attribute, or grouped? (3,287 distinct values) | data dictionary §3.1 |
| D8 | `company_name` — own dimension, degenerate attribute, or grouped? (535,938 distinct, no company key) | data dictionary §3.3 |
| D9 | NULL vs an "unknown" dimension member vs an empty fact measure, for the three incomplete columns | §5 |
| D10 | Whether `stipend` can be aggregated across `location` without a documented currency | data dictionary §3.4 |
| D11 | Which flags become dimension attributes and which become fact-table degenerate flags | §4.5 |

---

## 13. Rule-to-evidence traceability

| Rule group | Evidence |
| --- | --- |
| §2 immutability, row/column counts, duplicates | `results/profiling/dataset_overview.txt` |
| §4.1 / §9 lineage, no natural key | `results/profiling/potential_key_analysis.csv`, `results/audit/key_candidates.csv` |
| §4.2 / §6 dates | `results/profiling/date_analysis.csv`, `results/audit/date_bounds.csv`, `future_dates.csv`, `future_dates_by_month.csv` |
| §4.3 text quality | `results/profiling/string_quality.csv`, `categorical_summary.csv`, `categorical_top_values.txt` |
| §4.5 binary flags | `results/audit/binary_flags.csv`, `binary_flag_value_counts.csv` |
| §4.6 / §8.1 payment invariant | `results/audit/payment_consistency.csv` |
| §4.7 / §8.2 email bijection | `results/audit/email_crosstab.csv` |
| §4.8 / §8.3 fraud score vs label | `results/audit/fraud_score_threshold_scan.csv`, `fraud_score_relationship.csv`, `fraud_score_class_stats.csv` |
| §4.9 / §8.5 trust signal | `results/audit/trust_signal_relationship.csv`, `trust_signal_correlations.csv` |
| §4.10 company vs domain age | `results/audit/company_domain_age.csv` |
| §4.11 score ranges | `results/audit/score_range_validation.csv` |
| §5 missing values | `results/profiling/column_profile.csv`, `results/audit/missing_overlap.csv`, `missing_combination_counts.csv`, `missing_value_relationship.csv` |
| §7 outliers | `results/audit/numeric_sanity.csv`, `results/profiling/numeric_summary.csv` |
| §11.9 provenance | `results/audit/provenance_indicators.csv` |
| Narrative reports | `results/profiling/summary.md`, `results/audit/audit_summary.md` |

---

## 14. Change control

- These rules are **approved**. Implementation transcribes them; it does not
  extend them.
- A defect not covered here is **escalated**, not fixed at implementation time.
- Any new cleaning decision requires a new round of evidence and a new approval,
  and is recorded here before it is implemented.
- This document describes the **raw → staging** step only. Dimensional-model
  decisions are listed in §12 and settled in the next phase.
