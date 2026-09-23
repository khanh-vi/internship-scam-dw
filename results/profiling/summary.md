# Data Profiling Report

- **Source file**: `E:/project/internship-scam-dw/data/raw/fake_internship_detection_dataset.csv`
- **Generated**: 2026-09-23 16:35:25
- **Source sha256**: `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398`
- **Scope**: profiling only. Nothing in `data/raw/` was written to, and no value in the dataset was cleaned, imputed, re-typed, encoded or removed.

Subsections headed **Observed facts** are measurements taken directly from the data. Subsections headed **Possible issues for manual review** are hypotheses that a human must confirm before any decision is taken. No column is recommended for deletion or modification at this stage.

## 1. Dataset size

**Observed facts**

| Metric | Value |
| --- | --- |
| Rows | 1,000,000 |
| Columns | 33 |
| Cells | 33,000,000 |
| File size on disk | 165.74 MB |
| In-memory size (pandas, deep) | 687.48 MB |
| Numeric columns | 24 |
| Text / categorical columns | 9 |
| Datetime-dtype columns | 0 |
| Boolean columns | 0 |
| Other columns | 0 |

No column arrives from the CSV as a datetime dtype; date-like columns are read as text and are analysed in section 6.

## 2. Missing data

**Observed facts**

- Total missing cells: **30,000** (0.0909% of all cells).
- Columns with at least one missing value: **3 of 33**.
- Columns with no missing value: **30**.

| Column | dtype | Missing | Missing % |
| --- | --- | ---: | ---: |
| `company_age` | float64 | 10,000 | 1.0000% |
| `stipend` | float64 | 10,000 | 1.0000% |
| `trust_signal_score` | float64 | 10,000 | 1.0000% |

**Possible issues for manual review**

- `company_age` has the highest share of missing values (1.0000%). Whether this is structurally missing (the fact does not exist for that posting) or a collection gap cannot be decided from the data alone and needs a human judgement.
- Missingness has **not** been tested for association with the target `is_fake_posting`. If missingness is itself informative, a later imputation decision could destroy signal. Flagged, not acted on.
- Empty strings in text columns are not counted as missing by pandas; see section 7 for those.

## 3. Duplicate rows

**Observed facts**

- Exact duplicate rows (all 33 columns identical, excess copies only): **0** (0.0000% of rows).
- Distinct rows: **1,000,000**.
- Counted with `DataFrame.duplicated(keep='first')`, so the first occurrence of a repeated row is not counted. **No row was removed.**

**Possible issues for manual review**

- No exact duplicate row was found.
- Near-duplicates (rows identical on all but one or two columns) were **not** searched for: an all-pairs comparison is O(n^2) and infeasible at this row count. If it matters, do it later with a blocking key over a few columns.

## 4. Numeric columns and anomalies

**Observed facts**

| Column | min | median | max | zeros | negatives | IQR outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `company_age` | 1 | 20 | 39 | 0 | 0 | 0 (0.00%) |
| `linkedin_presence` | 0 | 1 | 1 | 199,236 | 0 | 0 (0.00%) |
| `website_available` | 0 | 1 | 1 | 150,403 | 0 | 0 (0.00%) |
| `domain_age_months` | 1 | 240 | 500 | 0 | 0 | 0 (0.00%) |
| `verification_status` | 0 | 1 | 1 | 300,287 | 0 | 0 (0.00%) |
| `stipend` | 2,000 | 3.498e+04 | 1.104e+05 | 0 | 0 | 3,348 (0.34%) |
| `unrealistic_salary_flag` | 0 | 0 | 0 | 1,000,000 | 0 | 0 (0.00%) |
| `payment_required` | 0 | 0 | 1 | 900,095 | 0 | 0 (0.00%) |
| `registration_fee` | 0 | 0 | 4,999 | 900,095 | 0 | 0 (0.00%) |
| `job_description_length` | 100 | 1,799 | 5,000 | 0 | 0 | 7,040 (0.70%) |
| `grammatical_errors` | 0 | 3 | 14 | 49,716 | 0 | 11,891 (1.19%) |
| `vague_description_score` | 0 | 30 | 100 | 73,938 | 0 | 3,472 (0.35%) |
| `urgency_score` | 0 | 39 | 100 | 59,153 | 0 | 0 (0.00%) |
| `keyword_spam_score` | 0 | 25 | 100 | 114,428 | 0 | 3,451 (0.35%) |
| `fake_certificate_offer` | 0 | 0 | 1 | 920,170 | 0 | 0 (0.00%) |
| `recruiter_experience_years` | 0 | 5 | 19.6 | 49,615 | 0 | 3,585 (0.36%) |
| `suspicious_email_domain` | 0 | 0 | 1 | 749,433 | 0 | 0 (0.00%) |
| `recruiter_response_time_hours` | 1 | 18 | 63.9 | 0 | 0 | 3,217 (0.32%) |
| `social_media_presence` | 0 | 1 | 1 | 250,200 | 0 | 0 (0.00%) |
| `emotional_manipulation_score` | 0 | 24 | 100 | 114,946 | 0 | 3,516 (0.35%) |
| `phishing_language_score` | 0 | 19 | 100 | 145,727 | 0 | 2,650 (0.27%) |
| `trust_signal_score` | 0 | 56.9 | 100 | 479 | 0 | 4,510 (0.46%) |
| `fraud_score` | 0 | 32.3 | 100 | 51,586 | 0 | 8,881 (0.89%) |
| `is_fake_posting` | 0 | 0 | 1 | 778,042 | 0 | 0 (0.00%) |

Full statistics - count, mean, standard deviation, quartiles - are in `numeric_summary.csv`. IQR outliers use the conventional 1.5x inter-quartile fences and are a screening device, not a verdict.

**Possible issues for manual review**

- No numeric column contains a negative value.
- More than half of all rows are zero in: `unrealistic_salary_flag`, `payment_required`, `registration_fee`, `fake_certificate_offer`, `suspicious_email_domain`, `is_fake_posting`. For a 0/1 indicator that is ordinary class imbalance; for a measured quantity it may signal a default or placeholder value. The distinction cannot be made automatically.
- Constant (single-valued) numeric column(s): `unrealistic_salary_flag`. Flagged only - **not** recommended for removal here.
- Stored with a numeric dtype but holding only two distinct values: `linkedin_presence`, `website_available`, `verification_status`, `payment_required`, `fake_certificate_offer`, `suspicious_email_domain`, `social_media_presence`, `is_fake_posting`. These are very likely flags rather than measures, which matters when deciding what becomes a dimension attribute and what becomes a fact measure. Confirm manually.
- `grammatical_errors` has the largest share of IQR outliers (1.19%, max 14). This may be a genuine long tail rather than an error; no value was capped or removed.

## 5. Categorical cardinality

**Observed facts**

| Column | Distinct values | Most frequent | Count | % of rows |
| --- | ---: | --- | ---: | ---: |
| `company_name` | 535,938 | Smith PLC | 1,248 | 0.125% |
| `posting_date` | 3,287 | 2020-10-10 | 366 | 0.037% |
| `internship_title` | 9 | Marketing Intern | 111,577 | 11.158% |
| `location` | 9 | Sydney | 111,520 | 11.152% |
| `industry` | 9 | AI | 111,803 | 11.180% |
| `company_size` | 4 | Small | 300,184 | 30.018% |
| `employment_type` | 4 | Part-Time | 250,700 | 25.070% |
| `work_mode` | 3 | Remote | 549,339 | 54.934% |
| `recruiter_email_type` | 2 | Corporate | 749,433 | 74.943% |

The top 20 values of every categorical column, missing values included, are listed in `categorical_top_values.txt`.

**Possible issues for manual review**

- `posting_date` is high-cardinality (3,287 distinct values). For a star schema this is a dimension-design question - own dimension, degenerate attribute or grouped - rather than a data-quality defect.
- `company_name` is high-cardinality (535,938 distinct values). For a star schema this is a dimension-design question - own dimension, degenerate attribute or grouped - rather than a data-quality defect.

## 6. Date coverage

**Observed facts**

Candidate date/time columns were detected from the pandas dtype and from column names containing `date`, `time`, `year`, `timestamp`. Parsing was attempted on a copy of the distinct values only; the dataframe itself was not converted.

| Column | dtype | Detected by | Parse success | Min | Max | Invalid |
| --- | --- | --- | ---: | --- | --- | ---: |
| `posting_date` | str | name | 100.00% | 2018-01-01 00:00:00 | 2026-12-31 00:00:00 | 0 |
| `recruiter_experience_years` | float64 | name | 0.00% | - | - | 0 |
| `recruiter_response_time_hours` | float64 | name | 0.00% | - | - | 0 |

- `posting_date` spans **2018-01-01 to 2026-12-31**, over 3,287 distinct parsed values.

**Possible issues for manual review**

- `recruiter_experience_years` matched the date-name heuristic but is **not** a date: numeric dtype matched only by column name; values are not date-like (not whole numbers in a plausible year range), so no parse was attempted - likely a duration/measure, needs manual review. Recorded so the heuristic stays auditable.
- `recruiter_response_time_hours` matched the date-name heuristic but is **not** a date: numeric dtype matched only by column name; values are not date-like (not whole numbers in a plausible year range), so no parse was attempted - likely a duration/measure, needs manual review. Recorded so the heuristic stays auditable.
- Future-dated and far-past postings were not filtered out. The range above should be checked against the period the dataset is meant to cover; a date after the extraction date would be a genuine anomaly. Not acted on.
- A usable date column matters for the warehouse: it is the natural basis for a time dimension and for any date-grain roll-up, so its coverage and granularity deserve a deliberate check.

## 7. Text and string quality

**Observed facts**

| Column | Whitespace-padded | Empty strings | Whitespace-only | Distinct | Distinct (case-insensitive) | Distinct (trimmed + case-insensitive) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `posting_date` | 0 | 0 | 0 | 3,287 | 3,287 | 3,287 |
| `internship_title` | 0 | 0 | 0 | 9 | 9 | 9 |
| `employment_type` | 0 | 0 | 0 | 4 | 4 | 4 |
| `work_mode` | 0 | 0 | 0 | 3 | 3 | 3 |
| `industry` | 0 | 0 | 0 | 9 | 9 | 9 |
| `location` | 0 | 0 | 0 | 9 | 9 | 9 |
| `company_name` | 0 | 0 | 0 | 535,938 | 535,938 | 535,938 |
| `company_size` | 0 | 0 | 0 | 4 | 4 | 4 |
| `recruiter_email_type` | 0 | 0 | 0 | 2 | 2 | 2 |

No string value was trimmed, lower-cased or otherwise altered; the case-insensitive counts come from a temporary copy of the distinct values.

**Possible issues for manual review**

- No whitespace padding, empty string, whitespace-only value or case-variant duplicate was detected in any text column.
- Case- and whitespace-variant counts indicate *potential* duplicates only. Two spellings that differ by case may still be two different real entities; this needs a human decision, especially for company and location names.

## 8. Potential identifier columns

**Observed facts**

A column is reported as a *potential* unique key only when it has no missing value and its distinct-value count equals the row count. **No primary key is declared by this script.**

- Columns satisfying the strict uniqueness test: **0**.
- Columns that are near-unique (ratio >= 0.99) but not strictly unique: **0**.

Five highest-cardinality columns:

| Column | Distinct | Nulls | Uniqueness ratio | Potential unique key |
| --- | ---: | ---: | ---: | --- |
| `company_name` | 535,938 | 0 | 0.535938 | False |
| `stipend` | 73,830 | 10,000 | 0.073830 | False |
| `registration_fee` | 4,951 | 0 | 0.004951 | False |
| `job_description_length` | 3,946 | 0 | 0.003946 | False |
| `posting_date` | 3,287 | 0 | 0.003287 | False |

Every column is listed in `potential_key_analysis.csv`.

**Possible issues for manual review**

- **No single column uniquely identifies a row.** As loaded, the dataset has no natural primary key. For the warehouse that means a surrogate key will have to be introduced, or a composite business key agreed after inspection. That decision is deliberately left open here.

## 9. Columns that deserve manual review

Listed because a measurement raised a question, not because anything is known to be wrong. Nothing here is a recommendation to delete or change a column.

| Column | Why it is listed |
| --- | --- |
| `posting_date` | high cardinality (3,287 distinct); date range 2018-01-01 to 2026-12-31 needs validation against the intended reporting period |
| `company_name` | high cardinality (535,938 distinct) |
| `company_age` | 1.000% missing |
| `linkedin_presence` | numeric dtype but only 2 distinct value(s) - flag or measure? |
| `website_available` | numeric dtype but only 2 distinct value(s) - flag or measure? |
| `verification_status` | numeric dtype but only 2 distinct value(s) - flag or measure? |
| `stipend` | 1.000% missing |
| `unrealistic_salary_flag` | numeric dtype but only 1 distinct value(s) - flag or measure? |
| `payment_required` | numeric dtype but only 2 distinct value(s) - flag or measure? |
| `grammatical_errors` | 1.19% IQR outliers |
| `fake_certificate_offer` | numeric dtype but only 2 distinct value(s) - flag or measure? |
| `recruiter_experience_years` | matched the date-name rule but is not a date column |
| `suspicious_email_domain` | numeric dtype but only 2 distinct value(s) - flag or measure? |
| `recruiter_response_time_hours` | matched the date-name rule but is not a date column |
| `social_media_presence` | numeric dtype but only 2 distinct value(s) - flag or measure? |
| `trust_signal_score` | 1.000% missing |
| `is_fake_posting` | numeric dtype but only 2 distinct value(s) - flag or measure? |

## 10. What this report deliberately does not do

- It does not clean, impute, normalise, deduplicate, re-type or drop anything.
- It does not recommend removing or altering any column.
- It performs no ML preprocessing: no encoding, scaling, TF-IDF, resampling, stemming or lemmatisation.
- It does not declare a primary key.
- It does not write to `data/raw/`, which remains byte-identical.

