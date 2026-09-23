# Data Quality / Semantic Audit

- **Source file**: `E:/project/internship-scam-dw/data/raw/fake_internship_detection_dataset.csv`
- **Generated**: 2026-09-23 16:55:24
- **Source sha256**: `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398`
- **Rows x columns**: 1,000,000 x 33
- **Audit reference date**: 2026-09-23 (lower plausibility bound used: 2018-01-01)
- **Scope**: audit only. Nothing in `data/raw/` was written to. No value was cleaned, imputed, capped, dropped, normalised, encoded or de-duplicated. `posting_date` was parsed into a temporary in-memory Series; the loaded DataFrame was never mutated.

Every table below is a measurement. Where a section names a hypothesis ("is X derived from Y?") the evidence for and against it is given, and the decision is left open. No column is recommended for deletion or modification.

## 1. Posting date audit

**Observed facts**

| Metric | Value |
| --- | ---: |
| Minimum `posting_date` | 2018-01-01 |
| Maximum `posting_date` | 2026-12-31 |
| Span (days) | 3,286 |
| Distinct dates | 3,287 |
| Values not parseable as `%Y-%m-%d` | 0 |
| Values not parseable in any format | 0 |
| Rows before 2018-01-01 | 0 |
| Rows after 2026-09-23 (future rows) | 30,246 |
| Future rows as % of dataset | 3.0246% |
| Distinct future dates | 99 |

Future rows by year and month:

| Year | Month | Rows | Distinct dates | `is_fake_posting`=0 | `is_fake_posting`=1 | % of future rows | % of all rows |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026 | 9 | 2,195 | 7 | 1,685 | 510 | 7.2572% | 0.2195% |
| 2026 | 10 | 9,435 | 31 | 7,370 | 2,065 | 31.1942% | 0.9435% |
| 2026 | 11 | 9,195 | 30 | 7,140 | 2,055 | 30.4007% | 0.9195% |
| 2026 | 12 | 9,421 | 31 | 7,308 | 2,113 | 31.1479% | 0.9421% |

Future rows by `is_fake_posting`:

| `is_fake_posting` | Rows | % of future rows |
| ---: | ---: | ---: |
| 0 | 23,503 | 77.7061% |
| 1 | 6,743 | 22.2939% |

For comparison, the label rate across the whole dataset is 22.1958%.

Per-date detail for the future block is in `future_dates.csv`; the monthly aggregation is in `future_dates_by_month.csv`; the boundary metrics are in `date_bounds.csv`.

**Possible issues for manual review**

- 30,246 rows (3.0246%) carry a posting date later than the audit reference date 2026-09-23, spread over 99 distinct dates. A posting date in the future is either a data-entry/generation artefact or a legitimate "starts later" semantic that has been stored in the wrong column. The data alone cannot distinguish the two. **No future row was deleted.**
- Whether the fact table's date dimension should span these dates, cap them, or route them to a late-arriving/unknown-date member is a staging decision, not an audit finding.
- No row falls before 2018-01-01.

## 2. Missing-value relationship audit

**Observed facts**

| Column | Missing | Missing % | missing: label 0 | missing: label 1 | missing: label 1 rate | present: label 0 | present: label 1 | present: label 1 rate | Difference (pp) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `company_age` | 10,000 | 1.0000% | 7,800 | 2,200 | 22.0000% | 770,242 | 219,758 | 22.1978% | -0.1978 |
| `stipend` | 10,000 | 1.0000% | 7,804 | 2,196 | 21.9600% | 770,238 | 219,762 | 22.1982% | -0.2382 |
| `trust_signal_score` | 10,000 | 1.0000% | 7,762 | 2,238 | 22.3800% | 770,280 | 219,720 | 22.1939% | +0.1861 |

Pairwise overlap of the missing-value masks:

| Missing in \ also missing in | `company_age` | `stipend` | `trust_signal_score` |
| --- | ---: | ---: | ---: |
| `company_age` | 10,000 | 88 | 96 |
| `stipend` | 88 | 10,000 | 88 |
| `trust_signal_score` | 96 | 88 | 10,000 |

Observed co-missing counts against what statistical independence would predict:

| Pair | Missing in both | Expected if independent | Observed - expected | Jaccard | Masks identical |
| --- | ---: | ---: | ---: | ---: | ---: |
| `company_age` & `stipend` | 88 | 100.00 | -12.00 | 0.004419 | no |
| `company_age` & `trust_signal_score` | 96 | 100.00 | -4.00 | 0.004823 | no |
| `stipend` & `trust_signal_score` | 88 | 100.00 | -12.00 | 0.004419 | no |

- Rows missing at least one of the three columns: **29,728**.
- Rows missing all three: **0** (independence would predict about 1.00).
- Any two masks bit-for-bit identical: **no**.
- Highest pairwise Jaccard overlap: **0.004823**.

The full combination table, including the expected count under independence for every one of the observed missingness patterns, is in `missing_combination_counts.csv`. The pairwise matrix is in `missing_overlap.csv`, the per-column label breakdown in `missing_value_relationship.csv`.

**Possible issues for manual review**

- The largest gap between the fraud rate among missing rows and among present rows is 0.2382 percentage points. A gap near zero is evidence that missingness carries no label information; it is not proof, and it says nothing about association with other columns.
- No row is missing all three values, and no two masks are identical, so the three gaps are not a single record-level dropout.
- **Nothing was imputed.** Whether these are structurally missing (the fact does not exist for the posting) or collection gaps cannot be decided from the data; that determines whether the staging layer keeps a NULL, uses an "unknown" dimension member, or leaves the measure empty in the fact table.

## 3. Binary flag validation

**Observed facts**

| Column | dtype | Distinct values | Count 0 | Count 1 | Other / null | % of rows = 1 | Strictly {0,1} | Constant |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `linkedin_presence` | int64 | 0, 1 | 199,236 | 800,764 | 0 | 80.0764% | yes | no |
| `website_available` | int64 | 0, 1 | 150,403 | 849,597 | 0 | 84.9597% | yes | no |
| `verification_status` | int64 | 0, 1 | 300,287 | 699,713 | 0 | 69.9713% | yes | no |
| `unrealistic_salary_flag` | int64 | 0 | 1,000,000 | 0 | 0 | 0.0000% | yes | yes |
| `payment_required` | int64 | 0, 1 | 900,095 | 99,905 | 0 | 9.9905% | yes | no |
| `fake_certificate_offer` | int64 | 0, 1 | 920,170 | 79,830 | 0 | 7.9830% | yes | no |
| `suspicious_email_domain` | int64 | 0, 1 | 749,433 | 250,567 | 0 | 25.0567% | yes | no |
| `social_media_presence` | int64 | 0, 1 | 250,200 | 749,800 | 0 | 74.9800% | yes | no |
| `is_fake_posting` | int64 | 0, 1 | 778,042 | 221,958 | 0 | 22.1958% | yes | no |

Per-value counts are in `binary_flags.csv` (one row per column) and `binary_flag_value_counts.csv` (one row per column/value pair).

**Possible issues for manual review**

- All nine columns take values strictly in {0,1} with no nulls, so each can be modelled as a boolean-valued attribute.
- Constant column(s): `unrealistic_salary_flag`. A constant column carries no information for slicing and would produce a single-member degenerate dimension. Flagged only - **not** recommended for removal here, because a constant in this extract may still be meaningful in the source system.

## 4. Payment consistency audit

**Observed facts**

| Check | Rows | % of rows |
| --- | ---: | ---: |
| payment_required = 0 AND registration_fee > 0 | 0 | 0.0000% |
| payment_required = 1 AND registration_fee = 0 | 0 | 0.0000% |
| payment_required = 0 AND registration_fee = 0 (consistent) | 900,095 | 90.0095% |
| payment_required = 1 AND registration_fee > 0 (consistent) | 99,905 | 9.9905% |
| registration_fee < 0 | 0 | 0.0000% |
| registration_fee is null | 0 | 0.0000% |

`registration_fee` statistics by `payment_required`:

| `payment_required` | Rows | Fee = 0 | Fee > 0 | min | p25 | median | p75 | max | mean | std |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 900,095 | 900,095 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 1 | 99,905 | 0 | 99,905 | 50.00 | 1,284.00 | 2,520.00 | 3,763.00 | 4,999.00 | 2,523.23 | 1,430.61 |

Both tables are in `payment_consistency.csv`.

**Possible issues for manual review**

- The two columns never contradict each other: there is no row with `payment_required = 0` and a positive fee, and no row with `payment_required = 1` and a zero fee. `payment_required` is therefore recoverable from `registration_fee > 0` on this extract.
- That makes the pair fully redundant **on this extract**, which matters when choosing whether the flag becomes a dimension attribute and the fee a fact measure, or whether only the fee is carried. It does not prove the source system enforces the constraint, and no column is dropped here.
- No negative `registration_fee` value exists.

## 5. Email consistency audit

**Observed facts**

| `recruiter_email_type` \ `suspicious_email_domain` | 0 | 1 | Total |
| --- | ---: | ---: | ---: |
| Corporate | 749,433 | 0 | 749,433 |
| Free | 0 | 250,567 | 250,567 |
| **Total** | 749,433 | 250,567 | 1,000,000 |

Same table as a share of all rows:

| `recruiter_email_type` | `suspicious_email_domain` = 0 | `suspicious_email_domain` = 1 |
| --- | ---: | ---: |
| Corporate | 74.9433% | 0.0000% |
| Free | 0.0000% | 25.0567% |

Functional-dependency test, in both directions:

| Direction | Distinct determinant values | Max distinct dependent values per key | Exact function | Violating rows | % of rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| `recruiter_email_type` -> `suspicious_email_domain` | 2 | 1 | yes | 0 | 0.000000% |
| `suspicious_email_domain` -> `recruiter_email_type` | 2 | 1 | yes | 0 | 0.000000% |

- Chi-square: 1,000,000.00. Cramer's V: 1.000000 (1.0 means the two columns are in perfect one-to-one correspondence).
- Rows that fall outside the modal mapping: **0**.

The counts and all three percentage bases are in `email_crosstab.csv`.

**Possible issues for manual review**

- The mapping is **exact and bijective in both directions**: every value of `recruiter_email_type` corresponds to exactly one value of `suspicious_email_domain` and vice versa, with 0 violating rows out of 1,000,000 and Cramer's V = 1.000000. This is a mathematical demonstration on this extract, so the two columns carry identical information here.
- What it does **not** demonstrate: that the source system guarantees the mapping. `recruiter_email_type` is a label with more possible values than a boolean; a future extract could contain a third type. Carrying both as a dimension attribute costs almost nothing and preserves that headroom. **No decision to drop either column is made here.**

## 6. Fraud label relationship audit

**Observed facts**

| `is_fake_posting` | Rows | % of rows | min | p05 | p25 | median | p75 | p95 | max | mean | std |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 778,042 | 77.8042% | 0.00 | 0.00 | 14.40 | 26.20 | 37.00 | 47.00 | 50.00 | 25.2939 | 14.2375 |
| 1 | 221,958 | 22.1958% | 50.00 | 50.90 | 55.00 | 61.40 | 71.10 | 90.00 | 100.00 | 64.5733 | 12.1187 |

`fraud_score` binned into deciles, crossed with the label:

| `fraud_score` bin | label 0 | label 1 | Total | % of rows | label 1 rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| (-0.001, 10.0] | 139,153 | 0 | 139,153 | 13.9153% | 0.0000% |
| (10.0, 20.0] | 142,756 | 0 | 142,756 | 14.2756% | 0.0000% |
| (20.0, 30.0] | 177,858 | 0 | 177,858 | 17.7858% | 0.0000% |
| (30.0, 40.0] | 175,390 | 0 | 175,390 | 17.5390% | 0.0000% |
| (40.0, 50.0] | 142,885 | 620 | 143,505 | 14.3505% | 0.4320% |
| (50.0, 60.0] | 0 | 100,407 | 100,407 | 10.0407% | 100.0000% |
| (60.0, 70.0] | 0 | 60,761 | 60,761 | 6.0761% | 100.0000% |
| (70.0, 80.0] | 0 | 32,915 | 32,915 | 3.2915% | 100.0000% |
| (80.0, 90.0] | 0 | 16,224 | 16,224 | 1.6224% | 100.0000% |
| (90.0, 100.0] | 0 | 11,031 | 11,031 | 1.1031% | 100.0000% |

Exhaustive threshold scan over every observed `fraud_score` value, for the rule *predict `is_fake_posting` = 1 when `fraud_score` >= t*:

| Metric | Value |
| --- | ---: |
| Best threshold t | 50.0000 |
| Mismatches at best t | 607 |
|   of which false positives (label 0, score >= t) | 607 |
|   of which false negatives (label 1, score < t) | 0 |
| Accuracy at best t | 99.939300% |
| Perfect reproduction possible | NO |
| Max `fraud_score` among label 0 | 50.00 |
| Min `fraud_score` among label 1 | 50.00 |
| Rows in the overlapping score range | 1,227 |
| Overlap as % of dataset | 0.1227% |
| Distinct `fraud_score` values where both classes occur | 1 |

The decile crosstab is in `fraud_score_relationship.csv`, the per-class statistics in `fraud_score_class_stats.csv`, and the full threshold sweep (one row per candidate threshold) in `fraud_score_threshold_scan.csv`.

**Possible issues for manual review**

- The best single threshold is `fraud_score` >= 50.0000, leaving **607 mismatches** (0.060700% of rows: 607 false positives and 0 false negatives). No threshold reproduces the label exactly, so `is_fake_posting` is not a pure cut of `fraud_score`.
- The disagreement is not spread across a range: both classes occur at **exactly one** `fraud_score` value, 50.0000, where 607 rows carry label 0 and 620 carry label 1 (1,227 rows in total, 0.1227%). At every other observed score value the label is constant.
- That is the signature of a boundary rule of the form `fraud_score` > 50.0000 (or >=) with the value 50.0000 itself resolved some other way - by a second criterion, by rounding before the comparison, or arbitrarily. Which of those applies cannot be read off the data and is a question for the source. Until it is answered, treat `fraud_score` = 50.0000 as the one region where the two columns genuinely differ.
- **Neither column was removed.** Both remain available; which one becomes a fact measure and which a dimension attribute is a modelling decision.

## 7. Trust signal audit

**Observed facts**

`trust_signal_score` is analysed against `verification_status`, `linkedin_presence`, `website_available`, `social_media_presence`. 990,000 rows have all five values present; 10,000 rows are excluded from this section because `trust_signal_score` is null. **Excluded rows were not filled in.**

Point-biserial correlation and group means:

| Indicator | Pearson r | Mean score when 0 | Mean score when 1 | Difference | Additive OLS coefficient |
| --- | ---: | ---: | ---: | ---: | ---: |
| `verification_status` | 0.278794 | 49.5913 | 59.5437 | 9.9524 | 9.952744 |
| `linkedin_presence` | 0.243830 | 48.5577 | 58.5459 | 9.9882 | 9.988511 |
| `website_available` | -0.001497 | 56.6141 | 56.5455 | -0.0686 | -0.042025 |
| `social_media_presence` | 0.001566 | 56.5115 | 56.5706 | 0.0592 | 0.035713 |
| `(intercept)` | n/a | n/a | n/a | n/a | 41.601641 |

Every observed combination of the four indicators (this is the saturated model - if the within-group range is zero everywhere, the score is a deterministic function of the four flags):

| `verification_status` | `linkedin_presence` | `website_available` | `social_media_presence` | Rows | % of rows | mean | std | min | max | range | distinct scores |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 | 2,231 | 0.2254% | 41.2713 | 15.571299 | 0.0000 | 90.0000 | 90.000000 | 633 |
| 0 | 0 | 0 | 1 | 6,549 | 0.6615% | 41.7213 | 15.272969 | 0.0000 | 93.4000 | 93.400000 | 779 |
| 0 | 0 | 1 | 0 | 12,724 | 1.2853% | 41.6875 | 15.208161 | 0.0000 | 88.6000 | 88.600000 | 813 |
| 0 | 1 | 0 | 0 | 9,021 | 0.9112% | 51.5934 | 15.197238 | 0.0000 | 100.0000 | 100.000000 | 801 |
| 1 | 0 | 0 | 0 | 5,255 | 0.5308% | 51.5982 | 15.146531 | 0.0000 | 97.3000 | 97.300000 | 748 |
| 0 | 0 | 1 | 1 | 37,707 | 3.8088% | 41.5668 | 15.140824 | 0.0000 | 95.5000 | 95.500000 | 869 |
| 0 | 1 | 1 | 0 | 50,368 | 5.0877% | 51.5454 | 15.159028 | 0.0000 | 100.0000 | 100.000000 | 949 |
| 0 | 1 | 0 | 1 | 26,725 | 2.6995% | 51.5563 | 15.234000 | 0.0000 | 100.0000 | 100.000000 | 915 |
| 1 | 0 | 1 | 0 | 29,580 | 2.9879% | 51.4180 | 15.319693 | 0.0000 | 100.0000 | 100.000000 | 917 |
| 1 | 0 | 0 | 1 | 15,428 | 1.5584% | 51.6471 | 15.155436 | 0.0000 | 100.0000 | 100.000000 | 866 |
| 1 | 1 | 0 | 0 | 21,196 | 2.1410% | 61.5809 | 15.105733 | 2.9000 | 100.0000 | 97.100000 | 847 |
| 0 | 1 | 1 | 1 | 151,888 | 15.3422% | 51.5944 | 15.246157 | 0.0000 | 100.0000 | 100.000000 | 986 |
| 1 | 0 | 1 | 1 | 87,778 | 8.8665% | 51.5631 | 15.207905 | 0.0000 | 100.0000 | 100.000000 | 974 |
| 1 | 1 | 0 | 1 | 62,410 | 6.3040% | 61.5802 | 15.155975 | 0.0000 | 100.0000 | 100.000000 | 915 |
| 1 | 1 | 1 | 0 | 117,285 | 11.8470% | 61.5092 | 15.173402 | 0.0000 | 100.0000 | 100.000000 | 937 |
| 1 | 1 | 1 | 1 | 353,855 | 35.7429% | 61.5323 | 15.194943 | 0.0000 | 100.0000 | 100.000000 | 979 |

| Metric | Value |
| --- | ---: |
| Observed indicator combinations | 16 of 16 possible |
| Largest within-combination range of the score | 100.000000 |
| Largest within-combination standard deviation | 15.571299 |
| Largest number of distinct scores in one combination | 986 |
| R^2, saturated model (combination -> score) | 0.13719010 |
| R^2, additive model (weighted sum of the four flags) | 0.13718609 |
| Residual std, additive model | 15.198586 |
| Max absolute residual, additive model | 61.578609 |
| Correlation of the score with `is_fake_posting` | -0.386458 |

The group table is in `trust_signal_relationship.csv` and the correlations in `trust_signal_correlations.csv`.

**Evidence, not a decision**

- The score varies within flag combinations (largest within-group range 100.000000, largest within-group standard deviation 15.571299), so it is **not** a deterministic function of these four indicators alone.
- The four flags together explain R^2 = 0.137190 of the score's variance in the saturated model, and R^2 = 0.137186 as a simple additive weighted sum. The gap between the two is the part that depends on interactions between flags; the remainder depends on something not in this column set.
- What this section does **not** decide: whether `trust_signal_score` should be kept alongside the indicators. A derived measure can still be worth storing in a fact table for query convenience. That is a modelling call.

## 8. Company / domain-age sanity audit

**Observed facts**

| Metric | Value |
| --- | ---: |
| `company_age_min` | 1 |
| `company_age_max` | 39 |
| `company_age_median` | 20 |
| `company_age_null` | 10,000 |
| `domain_age_months_min` | 1 |
| `domain_age_months_max` | 500 |
| `domain_age_months_median` | 240 |
| `domain_age_months_null` | 0 |
| `rows_comparable` | 990,000 |
| `rows_domain_older_than_company` | 469,297 |
| `pct_of_all_rows` | 46.9297 |
| `pct_of_comparable_rows` | 47.4037 |
| `excess_months_min` | 1 |
| `excess_months_median` | 10 |
| `excess_months_max` | 73 |
| `excess_months_mean` | 12.0821 |
| `pearson_r_company_months_vs_domain_months` | 0.9940 |
| `domain_older_label_0` | 365,049 |
| `domain_older_label_1` | 104,248 |
| `domain_older_label_1_rate_pct` | 22.2137 |

Full table in `company_domain_age.csv`.

**Possible issues for manual review**

- `company_age` spans 1 to 39 (years); `domain_age_months` spans 1 to 500 (months, i.e. 0.1 to 41.7 years).
- 469,297 rows (46.9297% of all rows, 47.4037% of rows where both values are present) have `domain_age_months` greater than `company_age * 12`.
- **These rows are not called invalid.** A domain can legitimately predate the company that now uses it: acquired domains, rebrands, parked domains and holding-company registrations all produce this pattern. The count is reported so a human can decide whether the magnitude is plausible for this source.
- The largest excess is 73 months (6.1 years) beyond the company's age. Whether an excess of that size is plausible is a judgement about the source, not something the data settles.

## 9. Score range validation

**Observed facts**

| Column | Observed min | Observed max | < 0 | > 100 | Outside 0-100 | Nulls | Distinct values | Within 0-100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `vague_description_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 101 | yes |
| `urgency_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 101 | yes |
| `keyword_spam_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 101 | yes |
| `emotional_manipulation_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 101 | yes |
| `phishing_language_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 100 | yes |
| `trust_signal_score` | 0.00 | 100.00 | 0 | 0 | 0 | 10,000 | 1,001 | yes |
| `fraud_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 1,001 | yes |

Full table in `score_range_validation.csv`.

**Possible issues for manual review**

- Every one of the seven score columns stays inside 0-100. **0 out-of-range values.** The 0-100 range is therefore safe to declare as a check constraint in the staging layer.
- A value inside 0-100 is not the same as a value being correct; this section validates the range only.

## 10. Numeric sanity checks

**Observed facts**

| Column | Negatives | Zeros | Zeros % | min | median | max | Lower fence | Upper fence | IQR outliers | Outliers % | Nulls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `company_age` | 0 | 0 | 0.0000% | 1.00 | 20.00 | 39.00 | -20.00 | 60.00 | 0 | 0.0000% | 10,000 |
| `stipend` | 0 | 0 | 0.0000% | 2,000.00 | 34,984.00 | 110,428.00 | -5,583.50 | 75,548.50 | 3,348 | 0.3348% | 10,000 |
| `registration_fee` | 0 | 900,095 | 90.0095% | 0.00 | 0.00 | 4,999.00 | 0.00 | 0.00 | 99,905 | 9.9905% | 0 |
| `job_description_length` | 0 | 0 | 0.0000% | 100.00 | 1,799.00 | 5,000.00 | 183.00 | 3,415.00 | 7,040 | 0.7040% | 0 |
| `grammatical_errors` | 0 | 49,716 | 4.9716% | 0.00 | 3.00 | 14.00 | -1.00 | 7.00 | 11,891 | 1.1891% | 0 |
| `recruiter_experience_years` | 0 | 49,615 | 4.9615% | 0.00 | 5.00 | 19.60 | -3.00 | 13.00 | 3,585 | 0.3585% | 0 |
| `recruiter_response_time_hours` | 0 | 0 | 0.0000% | 1.00 | 18.00 | 63.90 | -9.20 | 45.20 | 3,217 | 0.3217% | 0 |

Fences are the conventional 1.5x inter-quartile bounds. Full statistics (mean, std, quartiles, per-side outlier counts) are in `numeric_sanity.csv`.

**Possible issues for manual review**

- No column in this set contains a negative value.
- Column(s) containing zeros: `registration_fee`, `grammatical_errors`, `recruiter_experience_years`. A zero may be a real measurement or a placeholder for "unknown"; the two cannot be told apart from the data. This matters most for `registration_fee`, where zero is meaningful (see section 4).
- 128,986 observations in total fall outside a 1.5x IQR fence. The IQR fence is a screening device, not a verdict: a long right tail in a stipend or a response time is ordinary. **No outlier was removed or capped.**
- The fence is **meaningless** for `registration_fee`, where the first and third quartiles are both 0, so the inter-quartile range is 0 and both fences collapse onto 0. Every non-zero value is then counted as an outlier by construction. Read those counts as "rows with a non-zero value", not as extreme observations. Excluding these columns, 29,081 observations fall outside a fence.

## 11. Candidate row identifier

**Observed facts**

| Column | Distinct values | Uniqueness | Most frequent value appears | Nulls | Unique key |
| --- | ---: | ---: | ---: | ---: | --- |
| `company_name` | 535,938 | 53.5938% | 1,248 | 0 | no |
| `stipend` | 73,830 | 7.3830% | 13,752 | 10,000 | no |
| `registration_fee` | 4,951 | 0.4951% | 900,095 | 0 | no |
| `job_description_length` | 3,946 | 0.3946% | 2,325 | 0 | no |
| `posting_date` | 3,287 | 0.3287% | 366 | 0 | no |
| `fraud_score` | 1,001 | 0.1001% | 51,586 | 0 | no |
| `trust_signal_score` | 1,001 | 0.1001% | 2,495 | 10,000 | no |
| `recruiter_response_time_hours` | 595 | 0.0595% | 44,700 | 0 | no |
| `domain_age_months` | 500 | 0.0500% | 8,630 | 0 | no |
| `recruiter_experience_years` | 183 | 0.0183% | 49,615 | 0 | no |

The ten highest-cardinality candidates are shown; all 33 columns plus the tested composites are in `key_candidates.csv`.

- **There is no natural single-column key.** The most distinctive column, `company_name`, has 535,938 distinct values across 1,000,000 rows (53.5938% unique), so it repeats.
- None of the tested column combinations is unique either.

**Recommendation (for the later staging layer only)**

- **No key was created and nothing was added to the raw data.** The raw CSV is unchanged.
- For the staging layer: generate a `source_row_id` from the original file row order (1..N as read, ascending, before any filter or sort) and carry it through as a lineage column. It is the only stable way to point from a warehouse row back to a specific line of this extract, given that no natural key exists.
- Because it comes from file order, `source_row_id` is only meaningful together with the file's sha256; record both in the load audit table. It is a lineage handle, not a business key, and should not be used to join across extracts.

## 12. Indicators requiring source-provenance verification

This section lists **objective, measurable regularities only**. It does **not** conclude whether the dataset is synthetic or real - that question cannot be answered from the data and requires the source documentation, the collection method and the licence. Each item below is a property that is unusual in organically collected data and therefore worth confirming against the source.

**Observed facts**

*Row count*

| Observation | Value | Note |
| --- | ---: | --- |
| row count | 1,000,000 | exactly 1,000,000 |

*Date coverage density*

| Observation | Value | Note |
| --- | ---: | --- |
| distinct dates observed | 3,287 |  |
| calendar days in span | 3,287 |  |
| share of calendar days with at least one row | 100 | 100% means no gap day in the range |
| rows per date - min | 247 |  |
| rows per date - max | 366 |  |
| rows per date - mean | 304.2288 |  |
| rows per date - std | 16.9621 |  |
| rows per date - coefficient of variation | 0.0558 | a low value means dates are close to evenly loaded |
| min weekday share | 14.2196 | uniform across 7 weekdays would be 14.2857% |
| max weekday share | 14.3617 |  |

*Categorical balance*

| Observation | Value | Note |
| --- | ---: | --- |
| internship_title: distinct values | 9 |  |
| internship_title: max deviation from uniform share (pp) | 0.0609 | uniform share would be 11.1111% |
| employment_type: distinct values | 4 |  |
| employment_type: max deviation from uniform share (pp) | 0.0700 | uniform share would be 25.0000% |
| work_mode: distinct values | 3 |  |
| work_mode: max deviation from uniform share (pp) | 21.6006 | uniform share would be 33.3333% |
| industry: distinct values | 9 |  |
| industry: max deviation from uniform share (pp) | 0.0692 | uniform share would be 11.1111% |
| location: distinct values | 9 |  |
| location: max deviation from uniform share (pp) | 0.0552 | uniform share would be 11.1111% |
| company_size: distinct values | 4 |  |
| company_size: max deviation from uniform share (pp) | 9.9640 | uniform share would be 25.0000% |
| recruiter_email_type: distinct values | 2 |  |
| recruiter_email_type: max deviation from uniform share (pp) | 24.9433 | uniform share would be 50.0000% |

*Missingness pattern*

| Observation | Value | Note |
| --- | ---: | --- |
| columns with missing values | 3 |  |
| missing counts | 10000, 10000, 10000 | identical counts across columns would be a pattern, not a coincidence |
| all missing counts identical | yes |  |
| missing percentages | 1.0000%, 1.0000%, 1.0000% |  |
| rows missing in all three columns | 0 | independence would predict about 1.00 |

*Duplicates*

| Observation | Value | Note |
| --- | ---: | --- |
| exact duplicate rows (all 33 columns) | 0 | counted with duplicated(keep='first'); no row was removed |

*String cleanliness*

- Text columns checked: 9.
- Rows affected by leading/trailing whitespace, empty-after-strip values, non-ASCII characters or double spaces, summed across all text columns: **0**.
- Every text column is free of all four defects. No leading or trailing whitespace, no empty-after-stripping value, no non-ASCII character and no double space anywhere in the text columns.

The complete list of observations is in `provenance_indicators.csv`.

**What needs confirming from the source, not from the data**

- The row count is exactly 1,000,000. Organically collected extracts are rarely round; a round count usually means a sampling cap, a generation parameter, or a deliberate truncation. Which of those applies is a question for whoever produced the file.
- Rows are spread across dates with a coefficient of variation of 0.0558 and 100.00% of the calendar days in the range are populated. Near-even loading across every calendar day, including weekends and holidays, is not typical of job-posting activity.
- 4 of 7 low-cardinality categorical columns are within one percentage point of a perfectly even split (largest deviation among them: 0.0700 pp): `employment_type`, `industry`, `internship_title`, `location`. An even spread across every category value is rare in observed data, where some titles, industries and cities always dominate.
- The remaining low-cardinality columns are **not** near-uniform: `company_size` (9.9640 pp), `recruiter_email_type` (24.9433 pp), `work_mode` (21.6006 pp). They are listed for completeness, as counter-evidence to the point above.
- The three incomplete columns are missing in exactly the same number of rows, at exactly 1.0000% each, with the overlaps matching what independence predicts (section 2). Missingness that lands on an exact round percentage independently in three columns is a pattern, not an accident of collection.
- Across 1,000,000 rows and 33 columns there is not one exact duplicate row.
- Text fields contain no whitespace, encoding or casing defects at all. Free-text fields entered by humans normally carry some.

**Explicitly not concluded**: none of the above establishes that the data is synthetic. Each item is equally consistent with a real dataset that has already been cleaned, sampled and normalised upstream. Resolve it by asking for the provenance of the file; until then, treat the dataset's realism as unverified rather than as either confirmed or denied.

## Scope statement

- `fake_internship_detection_dataset.csv` was opened read-only. Its sha256 is verified before and after this run.
- No row was deleted, including future-dated rows. No value was imputed, capped, clipped, rounded, re-typed or encoded. No column was dropped, including the columns shown above to be derivable from others. No key was added to the raw data.
- The only recommendation in this document is section 11's `source_row_id`, and it applies to the staging layer, not to the raw file.

