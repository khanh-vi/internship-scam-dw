# Data Dictionary — `fake_internship_detection_dataset.csv`

| Item | Value |
| --- | --- |
| Source file | `data/raw/fake_internship_detection_dataset.csv` |
| Source sha256 | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Rows | 1,000,000 |
| Source columns | 33 |
| Audit / reference date | **2026-09-23** |
| Evidence | `results/profiling/` (generated 2026-09-23 16:35:25), `results/audit/` (generated 2026-09-23 16:55:24) |
| Status of raw file | Immutable. Never written to. See [cleaning_rules.md](cleaning_rules.md). |

This document describes the **33 original source columns only**. Two additional
columns are created in the staging layer and are documented separately in
[§4 Staging-derived columns](#4-staging-derived-columns); they do **not** exist
in the raw file.

Every number in this document is a measurement taken from the profiling and
audit outputs listed above, or a re-verification against the raw CSV. No
business meaning is asserted beyond what the column name, the observed value
domain and the audit evidence support. Where the intended meaning of a column
cannot be established from the data, this document says so explicitly rather
than guessing.

---

## 1. Conventions used in this document

**Semantic category** is one of:

| Category | Meaning in this project |
| --- | --- |
| Identifier | Uniquely identifies a row or a business entity. |
| Date | A calendar date, basis for a time dimension. |
| Dimension candidate | Low-to-high cardinality descriptive value suitable for slicing. |
| Descriptive attribute | Describes an entity but is unlikely to be sliced on directly. |
| Measure candidate | Numeric quantity suitable for aggregation in a fact table. |
| Flag | Boolean-valued indicator, strictly `{0,1}`. |
| Outcome | The labelled result the warehouse is meant to analyse. |

These are **candidacies, not decisions**. Which column becomes a dimension
attribute, a fact measure or a degenerate dimension is settled during
dimensional modelling, not here.

**No source column is an Identifier.** The profiling key analysis
(`results/profiling/potential_key_analysis.csv`) tested all 33 columns plus
composites: 0 columns satisfy the uniqueness test, and 0 are near-unique
(ratio ≥ 0.99). The most distinctive column, `company_name`, is 53.5938%
unique. Row identity is therefore supplied by the staging-derived
`source_row_id` (§4).

**Missing %** is measured over all 1,000,000 rows. Text columns contain no
empty strings and no whitespace-only values, so for those columns the pandas
null count is the complete missingness picture
(`results/profiling/string_quality.csv`).

**Expected staging type** is written in generic SQL. `NULL` / `NOT NULL`
reflects what the data actually permits, not a preference. Types are sized
from observed ranges and from a direct re-verification of decimal precision
against the raw CSV; `company_age` and `stipend` are serialised by pandas with
a trailing `.0` but hold **zero** non-integral values across 1,000,000 rows,
so they are typed as integers.

---

## 2. Summary of all 33 source columns

| # | Column | Source type (as loaded) | Semantic category | Missing % | Distinct | Expected staging type |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | `posting_date` | str (`YYYY-MM-DD`) | Date | 0.0000% | 3,287 | `DATE NOT NULL` |
| 2 | `internship_title` | str | Dimension candidate | 0.0000% | 9 | `VARCHAR(32) NOT NULL` |
| 3 | `employment_type` | str | Dimension candidate | 0.0000% | 4 | `VARCHAR(16) NOT NULL` |
| 4 | `work_mode` | str | Dimension candidate | 0.0000% | 3 | `VARCHAR(16) NOT NULL` |
| 5 | `industry` | str | Dimension candidate | 0.0000% | 9 | `VARCHAR(24) NOT NULL` |
| 6 | `location` | str | Dimension candidate | 0.0000% | 9 | `VARCHAR(24) NOT NULL` |
| 7 | `company_name` | str | Dimension candidate | 0.0000% | 535,938 | `VARCHAR(64) NOT NULL` |
| 8 | `company_size` | str | Dimension candidate | 0.0000% | 4 | `VARCHAR(16) NOT NULL` |
| 9 | `company_age` | float64 | Measure candidate | 1.0000% | 39 | `SMALLINT NULL` |
| 10 | `linkedin_presence` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 11 | `website_available` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 12 | `domain_age_months` | int64 | Measure candidate | 0.0000% | 500 | `SMALLINT NOT NULL` |
| 13 | `verification_status` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 14 | `stipend` | float64 | Measure candidate | 1.0000% | 73,830 | `INTEGER NULL` |
| 15 | `unrealistic_salary_flag` | int64 | Flag (constant) | 0.0000% | 1 | `SMALLINT NOT NULL` |
| 16 | `payment_required` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 17 | `registration_fee` | int64 | Measure candidate | 0.0000% | 4,951 | `INTEGER NOT NULL` |
| 18 | `job_description_length` | int64 | Measure candidate | 0.0000% | 3,946 | `SMALLINT NOT NULL` |
| 19 | `grammatical_errors` | int64 | Measure candidate | 0.0000% | 15 | `SMALLINT NOT NULL` |
| 20 | `vague_description_score` | int64 | Measure candidate | 0.0000% | 101 | `SMALLINT NOT NULL` |
| 21 | `urgency_score` | int64 | Measure candidate | 0.0000% | 101 | `SMALLINT NOT NULL` |
| 22 | `keyword_spam_score` | int64 | Measure candidate | 0.0000% | 101 | `SMALLINT NOT NULL` |
| 23 | `fake_certificate_offer` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 24 | `recruiter_experience_years` | float64 | Measure candidate | 0.0000% | 183 | `DECIMAL(3,1) NOT NULL` |
| 25 | `recruiter_email_type` | str | Dimension candidate | 0.0000% | 2 | `VARCHAR(16) NOT NULL` |
| 26 | `suspicious_email_domain` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 27 | `recruiter_response_time_hours` | float64 | Measure candidate | 0.0000% | 595 | `DECIMAL(3,1) NOT NULL` |
| 28 | `social_media_presence` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 29 | `emotional_manipulation_score` | int64 | Measure candidate | 0.0000% | 101 | `SMALLINT NOT NULL` |
| 30 | `phishing_language_score` | int64 | Measure candidate | 0.0000% | 100 | `SMALLINT NOT NULL` |
| 31 | `trust_signal_score` | float64 | Measure candidate | 1.0000% | 1,001 | `DECIMAL(4,1) NULL` |
| 32 | `fraud_score` | float64 | Measure candidate | 0.0000% | 1,001 | `DECIMAL(4,1) NOT NULL` |
| 33 | `is_fake_posting` | int64 | Outcome | 0.0000% | 2 | `SMALLINT NOT NULL` |

`SMALLINT` is used for the nine flags rather than a native boolean type so that
the approved rule "preserve the 0/1 representation" is honoured literally in
the staging schema.

---

## 3. Column detail

### 3.1 Temporal

#### `posting_date`

| Attribute | Value |
| --- | --- |
| Source type | `str`, formatted `YYYY-MM-DD` |
| Business interpretation | The date the internship posting was published. |
| Missing | 0 (0.0000%) |
| Cardinality | 3,287 distinct dates |
| Expected staging type | `DATE NOT NULL` |
| Semantic category | Date |

**Data quality observations**

- 100.00% of values parse as `%Y-%m-%d`; **0 values are unparseable** in that format or in any format (audit §1).
- Range: **2018-01-01 to 2026-12-31**, a span of 3,286 days covering 3,287 distinct dates — i.e. **every calendar day in the range is populated**, with no gap day.
- Rows per date: min 247, max 366, mean 304.2288, coefficient of variation 0.0558. Weekday shares run 14.2196%–14.3617% against a uniform 14.2857%.
- **30,246 rows (3.0246%) carry a posting date later than the 2026-09-23 audit reference date**, across 99 distinct future dates: 2026-09 (2,195 rows), 2026-10 (9,435), 2026-11 (9,195), 2026-12 (9,421). Of these, 23,503 are labelled `is_fake_posting = 0` and 6,743 are labelled 1 (22.2939%, against a dataset-wide rate of 22.1958%).
- No row falls before 2018-01-01.
- High cardinality relative to the other categoricals, but for a star schema this is a dimension-design question, not a defect.

**Cleaning action**

- Parse to a real `DATE`; output in ISO `YYYY-MM-DD`. Any parse failure must be reported, not silently coerced.
- **Future-dated rows are retained.** They are flagged by the staging-derived `is_future_posting` (§4.2), not removed.
- The even daily loading and full calendar coverage are recorded as provenance observations (audit §12); they are not treated as a data-quality defect and trigger no change.

---

### 3.2 Role and placement attributes

All five columns in this group were verified free of whitespace padding, empty
strings, whitespace-only values, non-ASCII characters, double spaces and
case-variant duplicates (`results/profiling/string_quality.csv`; distinct,
case-insensitive distinct and trimmed+case-insensitive distinct counts are
identical for every column). **Their values are therefore preserved exactly as
found: no trimming, no lowercasing, no category mapping, no category merging.**

#### `internship_title`

| Attribute | Value |
| --- | --- |
| Source type | `str` |
| Business interpretation | The advertised role title for the internship. |
| Missing | 0 (0.0000%) |
| Cardinality | 9 distinct (max length 21 characters) |
| Expected staging type | `VARCHAR(32) NOT NULL` |
| Semantic category | Dimension candidate |

**Data quality observations**

- Complete value domain: `Marketing Intern` (11.158%), `Cloud Engineer` (11.148%), `AI Research Intern` (11.144%), `Cybersecurity Analyst` (11.140%), `UI/UX Designer` (11.139%), `Backend Developer` (11.093%), `ML Engineer` (11.069%), `Frontend Developer` (11.059%), `Data Science Intern` (11.050%).
- Near-uniform: maximum deviation from an even 11.1111% share is 0.0609 pp. Recorded as a provenance observation only.
- Only 4 of the 9 titles contain the word "Intern"; the column is a role label, and whether the other five are internship roles is not established by the data.

**Cleaning action** — Preserve verbatim. No transformation.

#### `employment_type`

| Attribute | Value |
| --- | --- |
| Source type | `str` |
| Business interpretation | The contractual basis on which the role is offered. |
| Missing | 0 (0.0000%) |
| Cardinality | 4 distinct (max length 10 characters) |
| Expected staging type | `VARCHAR(16) NOT NULL` |
| Semantic category | Dimension candidate |

**Data quality observations**

- Complete value domain: `Part-Time` (25.070%), `Internship` (25.000%), `Contract` (24.967%), `Full-Time` (24.963%).
- Near-uniform: maximum deviation from 25.0000% is 0.0700 pp.
- `employment_type = 'Internship'` applies to only 25% of rows although every row is an internship posting by the dataset's own framing. The two notions are not reconciled by the data and no reconciliation is attempted.

**Cleaning action** — Preserve verbatim. No transformation.

#### `work_mode`

| Attribute | Value |
| --- | --- |
| Source type | `str` |
| Business interpretation | Where the work is performed. |
| Missing | 0 (0.0000%) |
| Cardinality | 3 distinct (max length 6 characters) |
| Expected staging type | `VARCHAR(16) NOT NULL` |
| Semantic category | Dimension candidate |

**Data quality observations**

- Complete value domain: `Remote` (54.934%), `Hybrid` (25.053%), `Onsite` (20.014%).
- **Not** near-uniform (21.6006 pp deviation from an even split) — recorded as counter-evidence in the provenance section.

**Cleaning action** — Preserve verbatim. No transformation.

#### `industry`

| Attribute | Value |
| --- | --- |
| Source type | `str` |
| Business interpretation | The sector the hiring company is listed under. |
| Missing | 0 (0.0000%) |
| Cardinality | 9 distinct (max length 13 characters) |
| Expected staging type | `VARCHAR(24) NOT NULL` |
| Semantic category | Dimension candidate |

**Data quality observations**

- Complete value domain: `AI` (11.180%), `EdTech` (11.142%), `Healthcare` (11.136%), `FinTech` (11.102%), `E-Commerce` (11.102%), `Marketing` (11.101%), `Gaming` (11.097%), `Cybersecurity` (11.088%), `Software` (11.053%).
- Near-uniform: maximum deviation from 11.1111% is 0.0692 pp.

**Cleaning action** — Preserve verbatim. No transformation.

#### `location`

| Attribute | Value |
| --- | --- |
| Source type | `str` |
| Business interpretation | The city associated with the posting. Whether this is the company's location, the work location or the recruiter's location is **not** established by the data. |
| Missing | 0 (0.0000%) |
| Cardinality | 9 distinct (max length 13 characters) |
| Expected staging type | `VARCHAR(24) NOT NULL` |
| Semantic category | Dimension candidate |

**Data quality observations**

- Complete value domain: `Sydney` (11.152%), `Toronto` (11.148%), `Bangalore` (11.144%), `San Francisco` (11.139%), `Berlin` (11.099%), `Dubai` (11.099%), `Singapore` (11.088%), `London` (11.075%), `New York` (11.056%).
- Near-uniform: maximum deviation from 11.1111% is 0.0552 pp.
- All nine are city names only; no country, region or country-code column exists in the source. Any geographic hierarchy would have to be added from outside this dataset.
- 54.934% of rows are `work_mode = 'Remote'`, so `location` cannot be assumed to be where the work is physically done.

**Cleaning action** — Preserve verbatim. No transformation. No geographic enrichment in staging.

---

### 3.3 Company attributes

#### `company_name`

| Attribute | Value |
| --- | --- |
| Source type | `str` (quoted in the CSV; values may contain commas, e.g. `"Russell, Medina and Evans"`) |
| Business interpretation | The name of the company that published the posting. |
| Missing | 0 (0.0000%) |
| Cardinality | 535,938 distinct (53.5938% unique; max length 38 characters) |
| Expected staging type | `VARCHAR(64) NOT NULL` |
| Semantic category | Dimension candidate |

**Data quality observations**

- Highest-cardinality column in the dataset, but **not** a key: the most frequent value, `Smith PLC`, appears 1,248 times, and the top 20 values cover only 1.90% of rows.
- No whitespace, casing, empty-string or non-ASCII defect; distinct and trimmed+case-insensitive distinct counts are both 535,938.
- Values follow a `<Surname> <Suffix>` pattern (`Smith PLC`, `Smith and Sons`, `Smith Ltd`, `Smith Inc`, `Smith LLC`, `Smith Group`, `Johnson LLC`, …). Because the same surname recurs across suffixes, **name similarity must not be treated as company identity**.
- **Embedded commas mean the CSV must be read with a quote-aware CSV parser.** Naive delimiter splitting shifts every field after `company_name` and was confirmed during this work to corrupt the downstream columns.
- There is no company identifier column. Whether two rows sharing a `company_name` refer to the same real company cannot be determined from this dataset.

**Cleaning action** — Preserve verbatim. No trimming, no case folding, no fuzzy matching, no entity resolution, no grouping. Read with a quote-aware CSV parser.

#### `company_size`

| Attribute | Value |
| --- | --- |
| Source type | `str` |
| Business interpretation | Banded size of the hiring company. The underlying headcount thresholds are **not** provided by the source. |
| Missing | 0 (0.0000%) |
| Cardinality | 4 distinct (max length 10 characters) |
| Expected staging type | `VARCHAR(16) NOT NULL` |
| Semantic category | Dimension candidate |

**Data quality observations**

- Complete value domain: `Small` (30.018%), `Startup` (29.986%), `Medium` (24.959%), `Enterprise` (15.036%).
- **Not** near-uniform (9.9640 pp deviation).
- The four values are not a strict size ordering: `Startup` describes company maturity while the other three describe scale. An ordinal ranking would therefore be an assumption, not a fact, and **none is imposed here**.

**Cleaning action** — Preserve verbatim. No transformation, no ordinal encoding, no category merging.

#### `company_age`

| Attribute | Value |
| --- | --- |
| Source type | `float64` (serialised with a trailing `.0`; verified **0 non-integral values** across 1,000,000 rows) |
| Business interpretation | Age of the company in **years**. |
| Missing | 10,000 (1.0000%) |
| Cardinality | 39 distinct |
| Expected staging type | `SMALLINT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 1 to 39; mean 20.000174, std 11.252082, median 20, quartiles 10 / 20 / 30.
- No negatives, no zeros, **0 IQR outliers**.
- Of the 10,000 rows with a missing value, 7,800 are labelled `is_fake_posting = 0` and 2,200 are labelled 1 — a 22.0000% fraud rate against 22.1978% among rows where the value is present, a gap of **-0.1978 pp**. This is evidence that the missingness carries little label information; it is not proof.
- The missingness is **not** a shared record-level dropout: only 88 rows are also missing `stipend` and 96 also missing `trust_signal_score` (independence predicts 100 in each case), and **no row is missing all three**.
- Whether the value is structurally missing (the company has no recorded age) or a collection gap **cannot be determined from the data**.
- See `domain_age_months` for the cross-column age relationship.

**Cleaning action** — Preserve. Missing values stay `NULL`. **No imputation of any kind** (no mean, no median, no zero, no forward-fill). No row is dropped because of this gap.

#### `domain_age_months`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Age of the company's web domain in **months**. |
| Missing | 0 (0.0000%) |
| Cardinality | 500 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 1 to 500 months (0.1 to 41.7 years); mean 239.541209, std 135.737891, median 240.
- No negatives, no zeros, **0 IQR outliers**.
- Correlation with `company_age` expressed in months: **Pearson r = 0.9940**.
- **469,297 rows (46.9297% of all rows; 47.4037% of the 990,000 comparable rows) have `domain_age_months > company_age * 12`.** The excess runs from 1 to 73 months, median 10, mean 12.0821. Among those rows the fraud rate is 22.2137%, essentially the dataset baseline.
- **These rows are explicitly not treated as invalid.** A domain can legitimately predate the company using it — acquired domains, rebrands, parked domains and holding-company registrations all produce this pattern. The unit mismatch (years vs months) also means `company_age` is the coarser measurement, so small excesses are expected from rounding alone.

**Cleaning action** — Preserve. **No record is modified, corrected or removed on the basis of this relationship**; the audit concluded the evidence is not sufficient to call the rows invalid.

---

### 3.4 Compensation and payment

#### `stipend`

| Attribute | Value |
| --- | --- |
| Source type | `float64` (serialised with a trailing `.0`; verified **0 non-integral values** across 1,000,000 rows) |
| Business interpretation | The stipend offered for the internship. **The currency and the pay period (monthly, annual, total) are not documented by the source** and cannot be inferred from the data. |
| Missing | 10,000 (1.0000%) |
| Cardinality | 73,830 distinct |
| Expected staging type | `INTEGER NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 2,000 to 110,428; mean 35,066.20, std 14,830.06, median 34,984, quartiles 24,841 / 34,984 / 45,124.
- No negatives, **no zeros** — so zero is not used as a placeholder here.
- 3,348 rows (0.3348%) fall above the 1.5×IQR upper fence of 75,548.50. This is a long right tail, which is ordinary for a pay distribution.
- Fraud rate among the 10,000 rows with a missing stipend: 21.9600%, against 22.1982% where present — a gap of **-0.2382 pp**, the largest of the three incomplete columns and still negligible.
- Because rows span 9 cities in different currency areas, aggregating `stipend` across `location` without a documented currency would produce a meaningless figure. Flagged for the dimensional-modelling stage; **no conversion is performed**.
- `unrealistic_salary_flag` is constant 0 and therefore marks none of these values as anomalous.

**Cleaning action** — Preserve. Missing values stay `NULL`. **No imputation, no capping, no winsorising, no scaling.** No row is dropped.

#### `unrealistic_salary_flag`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Intended as an indicator that the advertised pay is implausible. **Its activation rule is unknown and unobservable in this extract.** |
| Missing | 0 (0.0000%) |
| Cardinality | **1 distinct value** |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Flag (constant) |

**Data quality observations**

- **Constant: 0 in all 1,000,000 rows.** The count of `1` is zero.
- Strictly within `{0,1}`, no nulls.
- A constant column carries no information for slicing and would produce a single-member degenerate dimension.
- The audit did **not** recommend removal: a value that is constant in this extract may still be meaningful in the source system, and a later extract could contain `1`s.

**Cleaning action** — **Keep in staging**, preserved as 0/1 and validated. Documented here as a **candidate for exclusion from the analytical warehouse**; that exclusion is a dimensional-modelling decision and is deliberately deferred.

#### `payment_required`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Indicates the applicant is required to pay to apply or to take up the role. |
| Missing | 0 (0.0000%) |
| Cardinality | 2 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Flag |

**Data quality observations**

- `0`: 900,095 rows (90.0095%); `1`: 99,905 rows (9.9905%). Strictly `{0,1}`, no nulls.
- **Fully redundant with `registration_fee` on this extract.** Across all 1,000,000 rows: 0 rows have `payment_required = 0` with a positive fee, and 0 rows have `payment_required = 1` with a zero fee. The invariant `payment_required == (registration_fee > 0)` holds exactly. See §5.1.

**Cleaning action** — Preserve the 0/1 representation. **Both columns are kept in staging; neither is derived from the other.** The invariant is re-validated on every load. The redundancy is documented for dimensional-model review, not resolved here.

#### `registration_fee`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | The fee the applicant is asked to pay. Currency **not** documented by the source. |
| Missing | 0 (0.0000%) |
| Cardinality | 4,951 distinct |
| Expected staging type | `INTEGER NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0 to 4,999; mean 252.083069, std 881.467489, median 0.
- **900,095 rows (90.0095%) are zero**, and here zero is **meaningful, not a placeholder**: it means no fee was requested, which the exact agreement with `payment_required = 0` confirms.
- Among the 99,905 rows where a fee is charged: min 50, p25 1,284, median 2,520, p75 3,763, max 4,999, mean 2,523.23, std 1,430.61. No zero appears in this group.
- No negative value.
- The reported "99,905 IQR outliers (9.9905%)" is an **artefact**: Q1 and Q3 are both 0, so the interquartile range collapses to 0 and every non-zero value is flagged by construction. Read that count as "rows with a non-zero fee", **not** as extreme observations.

**Cleaning action** — Preserve all values including the zeros. **No outlier treatment** — the IQR fence is meaningless for this column. Validate `registration_fee >= 0` and the `payment_required` invariant.

---

### 3.5 Listing content quality

#### `job_description_length`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Length of the job description text. **The unit (characters or words) is not documented**; the 100–5,000 range is consistent with characters. The description text itself is **not** in the dataset. |
| Missing | 0 (0.0000%) |
| Cardinality | 3,946 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 100 to 5,000; mean 1,799.538324, std 598.563156, median 1,799, quartiles 1,395 / 1,799 / 2,203.
- No negatives, no zeros. The floor of exactly 100 and the ceiling of exactly 5,000 suggest bounds applied upstream.
- 7,040 rows (0.7040%) fall outside the 1.5×IQR fences of 183 / 3,415.

**Cleaning action** — Preserve. No capping, no scaling. No text processing is possible or required: **no free-text column exists in this dataset**.

#### `grammatical_errors`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Count of grammatical errors detected in the posting. The detection method is **not** documented. |
| Missing | 0 (0.0000%) |
| Cardinality | 15 distinct (values 0–14) |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0 to 14; mean 2.998825, std 1.731828, median 3.
- 49,716 rows (4.9716%) are zero. A zero here is plausibly a real measurement (no errors found), but it cannot be distinguished from a placeholder using the data alone.
- **Largest IQR outlier share of any column in the dataset: 11,891 rows (1.1891%)**, above the upper fence of 7. Given the column is a small bounded count, this is a genuine long tail rather than a defect.

**Cleaning action** — Preserve. **No outlier removal or capping.**

#### `vague_description_score`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Score for how vague the posting's description is. Derivation **not** documented. |
| Missing | 0 (0.0000%) |
| Cardinality | 101 distinct (every integer 0–100) |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0 to 100, fully within bounds: **0 values below 0, 0 above 100**.
- Mean 30.132072, std 18.814980, median 30; 73,938 rows (7.3938%) are zero.
- 3,472 rows (0.3472%) outside the IQR fences.

**Cleaning action** — Preserve. Validate `0 <= value <= 100`.

#### `urgency_score`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Score for urgency/pressure language in the posting. Derivation **not** documented. |
| Missing | 0 (0.0000%) |
| Cardinality | 101 distinct (every integer 0–100) |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0 to 100, fully within bounds: 0 out-of-range values.
- Mean 40.047191, std 23.612605, median 39; 59,153 rows (5.9153%) are zero.
- **0 IQR outliers** — the widest-spread of the content scores.

**Cleaning action** — Preserve. Validate `0 <= value <= 100`.

#### `keyword_spam_score`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Score for keyword stuffing in the posting. Derivation **not** documented. |
| Missing | 0 (0.0000%) |
| Cardinality | 101 distinct (every integer 0–100) |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0 to 100, fully within bounds: 0 out-of-range values.
- Mean 25.573860, std 18.116422, median 25; 114,428 rows (11.4428%) are zero.
- 3,451 rows (0.3451%) outside the IQR fences.

**Cleaning action** — Preserve. Validate `0 <= value <= 100`.

#### `emotional_manipulation_score`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Score for emotionally manipulative language in the posting. Derivation **not** documented. |
| Missing | 0 (0.0000%) |
| Cardinality | 101 distinct (every integer 0–100) |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0 to 100, fully within bounds: 0 out-of-range values.
- Mean 25.563839, std 18.129998, median 24; 114,946 rows (11.4946%) are zero.
- 3,516 rows (0.3516%) outside the IQR fences.

**Cleaning action** — Preserve. Validate `0 <= value <= 100`.

#### `phishing_language_score`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Score for phishing-style language in the posting. Derivation **not** documented. |
| Missing | 0 (0.0000%) |
| Cardinality | **100 distinct** — one integer in 0–100 is unobserved |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0 to 100, fully within bounds: 0 out-of-range values.
- Mean 20.749288, std 15.884219, median 19; 145,727 rows (14.5727%) are zero — the highest zero share of the six integer content scores.
- 2,650 rows (0.2650%) outside the IQR fences.
- The single unobserved integer is a sampling gap in a 1,000,000-row extract, **not** a defect; no value is inserted and the 0–100 constraint still applies.

**Cleaning action** — Preserve. Validate `0 <= value <= 100`.

#### `fake_certificate_offer`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Indicates the posting offers a certificate that is fraudulent or of no value. |
| Missing | 0 (0.0000%) |
| Cardinality | 2 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Flag |

**Data quality observations**

- `0`: 920,170 rows (92.0170%); `1`: 79,830 rows (7.9830%). Strictly `{0,1}`, no nulls.
- The 92/8 split is ordinary class imbalance for a fraud indicator, not a defect.

**Cleaning action** — Preserve the 0/1 representation. **No rebalancing of any kind.** Validate membership of `{0,1}`.

---

### 3.6 Recruiter attributes

#### `recruiter_experience_years`

| Attribute | Value |
| --- | --- |
| Source type | `float64`, one decimal place (856,914 non-integral values) |
| Business interpretation | The recruiter's experience in years. |
| Missing | 0 (0.0000%) |
| Cardinality | 183 distinct |
| Expected staging type | `DECIMAL(3,1) NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0.0 to 19.6; mean 5.052660, std 2.871692, median 5, quartiles 3 / 5 / 7.
- 49,615 rows (4.9615%) are exactly 0. Whether 0 means "no experience" or "not recorded" **cannot be determined from the data**; it is left as 0 either way.
- 3,585 rows (0.3585%) above the upper IQR fence of 13.
- **This column matched the profiler's date-name heuristic** (its name contains `years`) but is **not** a date: parse success was 0.00% and the values are a duration measure. Recorded so the heuristic stays auditable; no date parsing is attempted.

**Cleaning action** — Preserve, including the zeros. Not parsed as a date. No outlier treatment.

#### `recruiter_email_type`

| Attribute | Value |
| --- | --- |
| Source type | `str` |
| Business interpretation | Whether the recruiter's email address is on a corporate domain or a free email provider. |
| Missing | 0 (0.0000%) |
| Cardinality | 2 distinct (max length 9 characters) |
| Expected staging type | `VARCHAR(16) NOT NULL` |
| Semantic category | Dimension candidate |

**Data quality observations**

- Complete value domain: `Corporate` (749,433 rows, 74.9433%), `Free` (250,567 rows, 25.0567%).
- No whitespace, casing or empty-string defect.
- **In perfect bijection with `suspicious_email_domain`** — see §5.2. `Corporate` ↔ 0 and `Free` ↔ 1, with 0 violating rows out of 1,000,000 and Cramér's V = 1.000000.
- Being a label rather than a boolean, it has headroom the flag does not: a future extract could contain a third type.

**Cleaning action** — Preserve verbatim. **Not deleted**, despite the proven redundancy; the relationship is documented and the redundancy decision is deferred to dimensional modelling.

#### `suspicious_email_domain`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Indicates the recruiter's email domain is suspicious. On this extract it is exactly the indicator for `recruiter_email_type = 'Free'`. |
| Missing | 0 (0.0000%) |
| Cardinality | 2 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Flag |

**Data quality observations**

- `0`: 749,433 rows (74.9433%); `1`: 250,567 rows (25.0567%). Strictly `{0,1}`, no nulls.
- Counts match `recruiter_email_type` exactly. See §5.2 for the full bijection evidence.

**Cleaning action** — Preserve the 0/1 representation. **Not deleted.** Validate `{0,1}` membership and re-validate the bijection on each load.

#### `recruiter_response_time_hours`

| Attribute | Value |
| --- | --- |
| Source type | `float64`, one decimal place (860,182 non-integral values) |
| Business interpretation | How long the recruiter takes to respond, in hours. **What event the interval is measured from is not documented.** |
| Missing | 0 (0.0000%) |
| Cardinality | 595 distinct |
| Expected staging type | `DECIMAL(3,1) NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 1.0 to 63.9 hours; mean 18.180467, std 9.611051, median 18, quartiles 11.2 / 18.0 / 24.8.
- No negatives and **no zeros**, so zero is not used as a placeholder.
- 3,217 rows (0.3217%) above the upper IQR fence of 45.2 — an ordinary long right tail for a response-time distribution.
- **This column matched the profiler's date-name heuristic** (its name contains `time`) but is **not** a date: parse success was 0.00% and the values are a duration measure. Recorded so the heuristic stays auditable.

**Cleaning action** — Preserve. Not parsed as a date or a timestamp. No capping.

#### `social_media_presence`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Indicates the company has a detectable social-media presence. |
| Missing | 0 (0.0000%) |
| Cardinality | 2 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Flag |

**Data quality observations**

- `0`: 250,200 rows (25.0200%); `1`: 749,800 rows (74.9800%). Strictly `{0,1}`, no nulls.
- Correlation with `trust_signal_score` is **+0.001566** — effectively none (see §5.4).

**Cleaning action** — Preserve the 0/1 representation. Validate `{0,1}` membership.

---

### 3.7 Trust and company-presence flags

#### `linkedin_presence`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Indicates the company has a LinkedIn presence. |
| Missing | 0 (0.0000%) |
| Cardinality | 2 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Flag |

**Data quality observations**

- `0`: 199,236 rows (19.9236%); `1`: 800,764 rows (80.0764%). Strictly `{0,1}`, no nulls.
- One of only two flags with a material association with `trust_signal_score`: Pearson r = **0.243830**, group means 48.5577 (flag 0) vs 58.5459 (flag 1), difference 9.9882.

**Cleaning action** — Preserve the 0/1 representation. Validate `{0,1}` membership.

#### `website_available`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Indicates the company has a reachable website. |
| Missing | 0 (0.0000%) |
| Cardinality | 2 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Flag |

**Data quality observations**

- `0`: 150,403 rows (15.0403%); `1`: 849,597 rows (84.9597%). Strictly `{0,1}`, no nulls.
- Correlation with `trust_signal_score` is **-0.001497** — effectively none, and negative, despite the column's apparent meaning. Recorded as an observation; it is not corrected.
- `domain_age_months` is populated for all 1,000,000 rows, including the 150,403 where `website_available = 0`. The two are not reconciled by the source and **no reconciliation is attempted**.

**Cleaning action** — Preserve the 0/1 representation. Validate `{0,1}` membership.

#### `verification_status`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | Indicates the company or posting has been verified. **The verifying party and the criteria are not documented.** |
| Missing | 0 (0.0000%) |
| Cardinality | 2 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Flag |

**Data quality observations**

- `0`: 300,287 rows (30.0287%); `1`: 699,713 rows (69.9713%). Strictly `{0,1}`, no nulls.
- The strongest single correlate of `trust_signal_score`: Pearson r = **0.278794**, group means 49.5913 (flag 0) vs 59.5437 (flag 1), difference 9.9524.

**Cleaning action** — Preserve the 0/1 representation. Validate `{0,1}` membership.

---

### 3.8 Composite scores and outcome

#### `trust_signal_score`

| Attribute | Value |
| --- | --- |
| Source type | `float64`, one decimal place (888,982 non-integral values) |
| Business interpretation | A composite score summarising trust signals for the posting. **The derivation is not documented and is demonstrably not reproducible from the four presence/verification flags.** |
| Missing | 10,000 (1.0000%) |
| Cardinality | 1,001 distinct (0.0–100.0 at one decimal place) |
| Expected staging type | `DECIMAL(4,1) NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0.0 to 100.0, fully within bounds: 0 out-of-range values. Mean 56.555847, std 16.362310, median 56.9, quartiles 45.6 / 56.9 / 67.9.
- 479 rows are exactly 0; 4,510 rows (0.4510%) fall outside the IQR fences.
- **Not deterministic from `verification_status`, `linkedin_presence`, `website_available` and `social_media_presence`** (§5.4): all 16 flag combinations occur, the largest within-combination range is 100.0, the largest within-combination standard deviation is 15.5713, and one combination contains 986 distinct scores. The saturated model explains only R² = 0.137190.
- Fraud rate among the 10,000 rows with a missing score: 22.3800%, against 22.1939% where present — a gap of **+0.1861 pp**, the only one of the three incomplete columns where the missing rows are *more* often fraudulent.
- Correlation with `is_fake_posting`: **-0.386458**.

**Cleaning action** — Preserve. Missing values stay `NULL`; **no imputation**, and in particular it is **not** reconstructed from the four flags, because the audit proved that reconstruction is not possible. Validate `0 <= value <= 100` where non-null.

#### `fraud_score`

| Attribute | Value |
| --- | --- |
| Source type | `float64`, one decimal place (849,582 non-integral values) |
| Business interpretation | A composite fraud-risk score for the posting. The derivation is **not** documented. |
| Missing | 0 (0.0000%) |
| Cardinality | 1,001 distinct (0.0–100.0 at one decimal place) |
| Expected staging type | `DECIMAL(4,1) NOT NULL` |
| Semantic category | Measure candidate |

**Data quality observations**

- Range 0.0 to 100.0, fully within bounds: 0 out-of-range values. Mean 34.012258, std 21.371783, median 32.3, quartiles 18.1 / 32.3 / 47.8.
- 51,586 rows (5.1586%) are exactly 0; 8,881 rows (0.8881%) outside the IQR fences.
- By label: mean 25.2939 (std 14.2375) where `is_fake_posting = 0`, mean 64.5733 (std 12.1187) where 1.
- **Closely aligned with, but not equal to, the label** (§5.3). An exhaustive scan of every observed score found the best threshold to be `fraud_score >= 50.0`, leaving **607 mismatches** (0.0607% — 607 false positives, 0 false negatives; accuracy 99.939300%). **No threshold reproduces the label exactly.**
- The disagreement is concentrated at a **single value**: at `fraud_score = 50.0` exactly, 607 rows carry label 0 and 620 carry label 1 (1,227 rows, 0.1227%). At every other observed score the label is constant.

**Cleaning action** — Preserve. Validate `0 <= value <= 100`. **`is_fake_posting` is not derived from this column, and this column is not derived from the label.** No values are modified.

#### `is_fake_posting`

| Attribute | Value |
| --- | --- |
| Source type | `int64` |
| Business interpretation | The labelled outcome: whether the posting is a fake/scam internship listing. **The labelling process is not documented.** |
| Missing | 0 (0.0000%) |
| Cardinality | 2 distinct |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Outcome |

**Data quality observations**

- `0`: 778,042 rows (77.8042%); `1`: 221,958 rows (22.1958%). Strictly `{0,1}`, no nulls.
- The 78/22 split is the natural class balance of this extract.
- Not reproducible from `fraud_score` by any threshold (see above).
- The fraud rate among future-dated rows is 22.2939%, against 22.1958% overall — future dating is **not** associated with the label.

**Cleaning action** — Preserve the 0/1 representation. **No resampling, no rebalancing, no SMOTE, no class weighting.** Validate `{0,1}` membership.

---

## 4. Staging-derived columns

The two columns below are **not present in the raw CSV**. They are created by
the staging load and exist only in the staging dataset. The raw file keeps 33
columns; the staging dataset has 35.

### 4.1 `source_row_id`

| Attribute | Value |
| --- | --- |
| Origin | **Staging-derived** — not in the source |
| Business interpretation | Lineage handle pointing back to one physical line of this extract. |
| Definition | The position of the row in the original CSV, ascending, starting at **1**, assigned in original file order **before any filter, sort or transformation**. |
| Range | 1 to 1,000,000, contiguous |
| Missing | 0 |
| Cardinality | 1,000,000 distinct (100% unique) |
| Expected staging type | `INTEGER NOT NULL` — staging primary key |
| Semantic category | Identifier |

**Why it exists** — the profiling key analysis found **no natural single-column
key and no unique composite** among the 33 source columns. A surrogate is the
only way to address an individual row.

**Constraints on its use**

- It is a **lineage handle, not a business key.** It is meaningful only in
  combination with the source file's sha256, and both must be recorded together
  in the load audit record.
- It must **not** be used to join across extracts: the same `source_row_id` in a
  different file refers to a different posting.
- It must **not** be added to the raw CSV.
- It carries no business meaning and must not be treated as a sequence number,
  a posting ID or an ordering with analytic significance.

### 4.2 `is_future_posting`

| Attribute | Value |
| --- | --- |
| Origin | **Staging-derived** — not in the source |
| Business interpretation | Marks a posting dated after the audit reference date. |
| Definition | `1` when `posting_date > 2026-09-23`; `0` otherwise. |
| Reference date | **2026-09-23** — the audit/reference date, fixed and documented |
| Missing | 0 |
| Expected value distribution | `1`: 30,246 rows (3.0246%); `0`: 969,754 rows (96.9754%) |
| Expected staging type | `SMALLINT NOT NULL` |
| Semantic category | Flag |

**Notes**

- The flag **marks** future-dated rows; it does **not** filter them. All 30,246
  rows remain in staging.
- `2026-09-23` is a **fixed constant**, not "today". Computing this flag against
  the current date would make the staging dataset non-reproducible: the row
  counts above would drift with every run. The cutoff is pinned so the output
  is deterministic.
- The flag is a data-quality marker, not a fraud signal. Future-dated rows carry
  a 22.2939% fraud rate against 22.1958% overall.

---

## 5. Cross-column relationships established by the audit

These are measured dependencies between source columns. **None of them causes a
column to be dropped or derived at the staging stage.** Each is recorded so the
dimensional-modelling stage can make an informed decision.

### 5.1 `payment_required` ↔ `registration_fee` — exact, redundant

| Check | Rows | % |
| --- | ---: | ---: |
| `payment_required = 0` AND `registration_fee > 0` | **0** | 0.0000% |
| `payment_required = 1` AND `registration_fee = 0` | **0** | 0.0000% |
| `payment_required = 0` AND `registration_fee = 0` (consistent) | 900,095 | 90.0095% |
| `payment_required = 1` AND `registration_fee > 0` (consistent) | 99,905 | 9.9905% |

`payment_required == (registration_fee > 0)` holds for **all 1,000,000 rows**.
The flag is fully recoverable from the fee on this extract.

**Status** — both columns kept; the invariant is a validation rule (§10 of
[cleaning_rules.md](cleaning_rules.md)); the redundancy is deferred to
dimensional modelling. The audit noted that this demonstrates the constraint on
*this extract*, not that the source system enforces it.

### 5.2 `recruiter_email_type` ↔ `suspicious_email_domain` — perfect bijection

| `recruiter_email_type` \ `suspicious_email_domain` | 0 | 1 | Total |
| --- | ---: | ---: | ---: |
| `Corporate` | 749,433 | **0** | 749,433 |
| `Free` | **0** | 250,567 | 250,567 |
| **Total** | 749,433 | 250,567 | 1,000,000 |

Functional dependency holds in **both** directions with 0 violating rows;
Cramér's V = **1.000000**; chi-square = 1,000,000.00. The mapping is
`Corporate ↔ 0` and `Free ↔ 1`.

**Status** — both columns kept and preserved; neither is deleted automatically.
The audit's reasoning: the text column is a label with room for a third value in
a future extract, while the flag is boolean, so carrying both costs almost
nothing and preserves that headroom.

### 5.3 `fraud_score` → `is_fake_posting` — close but **not** deterministic

| Metric | Value |
| --- | ---: |
| Best threshold | `fraud_score >= 50.0` |
| Mismatches at best threshold | **607** |
| — false positives (label 0, score ≥ 50) | 607 |
| — false negatives (label 1, score < 50) | 0 |
| Accuracy at best threshold | 99.939300% |
| **Perfect reproduction possible** | **NO** |
| Max `fraud_score` among label 0 | 50.00 |
| Min `fraud_score` among label 1 | 50.00 |
| Distinct scores where both classes occur | **1** (exactly 50.0) |
| Rows at that score | 1,227 (0.1227%) — 607 label 0, 620 label 1 |

Below 50.0 every row is label 0; above 50.0 every row is label 1. The entire
disagreement sits on the single boundary value. That is the signature of a rule
resolved at the boundary by some second criterion, by rounding, or arbitrarily —
which of those applies **cannot be read off the data**.

**Status** — both columns preserved; the label is **not** derived from the
score, and the score is **not** derived from the label.

### 5.4 Trust signals → `trust_signal_score` — **not** deterministic

Measured over the 990,000 rows where the score is present.

| Indicator | Pearson r | Mean @ 0 | Mean @ 1 | Difference |
| --- | ---: | ---: | ---: | ---: |
| `verification_status` | 0.278794 | 49.5913 | 59.5437 | 9.9524 |
| `linkedin_presence` | 0.243830 | 48.5577 | 58.5459 | 9.9882 |
| `website_available` | -0.001497 | 56.6141 | 56.5455 | -0.0686 |
| `social_media_presence` | 0.001566 | 56.5115 | 56.5706 | 0.0592 |

| Metric | Value |
| --- | ---: |
| Observed flag combinations | 16 of 16 |
| Largest within-combination range | **100.000000** |
| Largest within-combination std | 15.571299 |
| Largest distinct scores in one combination | 986 |
| R², saturated model | **0.13719010** |
| R², additive model | 0.13718609 |

If the score were a function of the four flags, the within-combination range
would be 0 everywhere. It is 100.0 — the full scale. **The score is not
reconstructible from these flags**, and roughly 86% of its variance depends on
something outside this column set.

**Status** — all five columns preserved unchanged. The score is never imputed
from the flags.

### 5.5 `company_age` vs `domain_age_months` — not sufficient evidence of invalidity

469,297 rows (47.4037% of the 990,000 comparable rows) have a domain older than
the company, by 1 to 73 months (median 10). Pearson r between the two, on a
common scale, is 0.9940.

**Status** — no record modified. Acquired domains, rebrands and parked domains
produce this legitimately, and the years-vs-months granularity difference alone
accounts for small excesses.

### 5.6 Missingness structure — three independent gaps

| Pair | Missing in both | Expected if independent | Jaccard | Masks identical |
| --- | ---: | ---: | ---: | --- |
| `company_age` & `stipend` | 88 | 100.00 | 0.004419 | no |
| `company_age` & `trust_signal_score` | 96 | 100.00 | 0.004823 | no |
| `stipend` & `trust_signal_score` | 88 | 100.00 | 0.004419 | no |

- Rows missing at least one of the three: **29,728**.
- Rows missing all three: **0** (independence predicts ~1).
- No two masks are identical.

The three gaps are **not** one record-level dropout, so they cannot be handled
as a single "incomplete record" condition.

---

## 6. Evidence index

| Claim in this document | Evidence file |
| --- | --- |
| Row/column counts, dtypes, duplicates, sha256 | `results/profiling/dataset_overview.txt` |
| Null counts, distinct counts per column | `results/profiling/column_profile.csv` |
| Numeric min/max/mean/std/quartiles/zeros | `results/profiling/numeric_summary.csv` |
| Categorical distinct counts and modes | `results/profiling/categorical_summary.csv` |
| Complete category value domains | `results/profiling/categorical_top_values.txt` |
| Whitespace / empty / case-variant checks | `results/profiling/string_quality.csv` |
| Date parse rate and range | `results/profiling/date_analysis.csv` |
| Key candidacy for all 33 columns | `results/profiling/potential_key_analysis.csv` |
| Narrative profiling report | `results/profiling/summary.md` |
| Future-date counts and breakdown | `results/audit/future_dates.csv`, `future_dates_by_month.csv`, `date_bounds.csv` |
| Missingness overlap and label association | `results/audit/missing_overlap.csv`, `missing_combination_counts.csv`, `missing_value_relationship.csv` |
| Binary flag validation | `results/audit/binary_flags.csv`, `binary_flag_value_counts.csv` |
| Payment invariant | `results/audit/payment_consistency.csv` |
| Email bijection | `results/audit/email_crosstab.csv` |
| Fraud score / label relationship | `results/audit/fraud_score_relationship.csv`, `fraud_score_class_stats.csv`, `fraud_score_threshold_scan.csv` |
| Trust signal determinism test | `results/audit/trust_signal_relationship.csv`, `trust_signal_correlations.csv` |
| Company vs domain age | `results/audit/company_domain_age.csv` |
| 0–100 range validation | `results/audit/score_range_validation.csv` |
| Negatives, zeros, IQR fences | `results/audit/numeric_sanity.csv` |
| Key candidacy and `source_row_id` recommendation | `results/audit/key_candidates.csv` |
| Provenance observations | `results/audit/provenance_indicators.csv` |
| Narrative audit report | `results/audit/audit_summary.md` |

Decimal precision, integrality of `company_age` and `stipend`, maximum text
lengths and the embedded-comma finding in `company_name` were re-verified
directly against the raw CSV during the writing of this document, read-only.

---

## 7. Scope of this document

- It describes and classifies. It **does not** modify the dataset.
- Semantic categories are **candidacies**, not modelling decisions.
- Where the source does not document a meaning — the currency and period of
  `stipend`, the currency of `registration_fee`, the unit of
  `job_description_length`, the criteria behind `verification_status`, the
  derivation of the six content scores, `trust_signal_score` and `fraud_score`,
  the labelling process behind `is_fake_posting`, and the activation rule for
  `unrealistic_salary_flag` — this document records that the meaning is
  undocumented rather than supplying one.
- The cleaning actions summarised per column are stated in full, with their
  rationale and their validation requirements, in
  [cleaning_rules.md](cleaning_rules.md).
