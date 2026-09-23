# Staging Validation Report

**Overall result: PASS** &mdash; 47 of 47 checks passed.

| Item | Value |
| --- | --- |
| Generated | 2026-09-23 17:23:06 |
| Script | `scripts/build_staging.py` |
| Source | `data/raw/fake_internship_detection_dataset.csv` |
| Staging output | `data/staging/internship_postings_staging.csv` |
| Source sha256 | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Rows in / rows out | 1,000,000 / 1,000,000 |
| Columns in / columns out | 33 / 35 |
| Reference date (fixed) | **2026-09-23** |
| Chunk size / chunks | 100,000 / 10 |
| Runtime | 68.0s |
| Output size | 170.44 MB |

Expected values come from the completed profiling and audit phase (`results/profiling/`, `results/audit/`) and from [docs/data_dictionary.md](../../docs/data_dictionary.md). They are **assertions about the output**, never inputs to the transformation logic. A failing check is reported here; the pipeline never silently repairs the data.

---

## 1. Check results

| # | Check | Status | Observed | Expected |
| --- | --- | --- | --- | --- |
| 1 | Raw sha256 before processing matches the documented digest | **PASS** | 3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398 | 3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398 |
| 2 | Raw sha256 after processing matches the documented digest | **PASS** | 3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398 | 3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398 |
| 29 | Raw file unchanged by the run (sha256 + size + mtime) | **PASS** | sha256 3463d99be6580df3 / 173788906 bytes / mtime_ns 1790153224451672700 | identical to the pre-run fingerprint |
| 3 | CSV read with a quote-aware parser (embedded commas preserved) | **PASS** | 333784 rows carry a comma inside a quoted company_name; all records parse to 33 fields | quote-aware parse, no field shift |
| 4 | Every parsed record has exactly 33 source fields | **PASS** | header 33 fields; record widths {33: 1000000}; malformed records 0 | 33 for the header and for all 1000000 records |
| 5 | Raw row count | **PASS** | 1,000,000 | 1,000,000 |
| 6 | Staging row count | **PASS** | 1,000,000 | 1,000,000 |
| 7 | Staging column count | **PASS** | 35 | 35 |
| 8 | All 33 original columns retained | **PASS** | 0 missing | 0 missing |
| 9 | Original column order preserved | **PASS** | source columns occupy output positions 1-33 in file order | identical to the raw header order |
| 10 | source_row_id minimum | **PASS** | 1 | 1 |
| 11 | source_row_id maximum | **PASS** | 1,000,000 | 1,000,000 |
| 12 | source_row_id unique | **PASS** | 1000000 distinct, 0 duplicate(s), 1000000 of 1..1000000 covered | 1,000,000 distinct, 0 duplicates, contiguous |
| 13 | source_row_id non-null and out-of-range free | **PASS** | 0 null, 0 out of range | 0 null, 0 out of range |
| 13b | source_row_id ascends with original file order, monotonic across chunks | **PASS** | strictly +1 across all 10 chunk boundaries | strictly ascending, never reset per chunk |
| 14 | posting_date parse failures | **PASS** | 0 in staging, 0 in raw | 0 |
| 14b | posting_date written as ISO YYYY-MM-DD | **PASS** | 0 non-ISO value(s) | 0 |
| 15 | posting_date minimum | **PASS** | 2018-01-01 | 2018-01-01 |
| 16 | posting_date maximum | **PASS** | 2026-12-31 | 2026-12-31 |
| 16b | Distinct posting_date values | **PASS** | 3,287 | 3,287 |
| 17 | is_future_posting domain | **PASS** | [0, 1] | {0, 1} |
| 18 | is_future_posting = 1 count | **PASS** | 30,246 (3.0246%) | 30,246 |
| 18b | is_future_posting reproduces from the fixed cutoff on re-read | **PASS** | 0 mismatch(es) | 0 |
| 19 | company_age missing count | **PASS** | 10,000 (1.0000%) | 10,000 |
| 20 | stipend missing count | **PASS** | 10,000 (1.0000%) | 10,000 |
| 21 | trust_signal_score missing count | **PASS** | 10,000 (1.0000%) | 10,000 |
| 22 | No unexpected source missingness introduced | **PASS** | 0 nulls across the other 30 source columns | 0 |
| 22b | Staging null counts equal raw null counts, column by column | **PASS** | identical for all 33 source columns | identical |
| 23 | All nine binary fields strictly in {0,1}, no nulls | **PASS** | 0 violations, 0 nulls | 0 violations, 0 nulls |
| 23b | unrealistic_salary_flag retained and still constant 0 | **PASS** | present, values [0] | present, {0} |
| 24 | Seven score columns satisfy 0 <= value <= 100 where non-null | **PASS** | 0 out of range | 0 |
| 25 | payment_required == (registration_fee > 0) | **PASS** | 0 | 0 |
| 26 | recruiter_email_type Corporate<->0 and Free<->1 | **PASS** | 0 | 0 |
| 26b | is_fake_posting not derived from fraud_score | **PASS** | label digest identical to source | identical |
| 27 | Exact duplicate source rows (33 source fields only) | **PASS** | 0 duplicate(s), 1,000,000 distinct rows | 0 |
| 28 | Source values preserved through the round trip (element-wise) | **PASS** | 0 differing values across 33,000,000 compared cells | 0 |
| 28b | Per-column order-sensitive value digests match raw | **PASS** | 33 of 33 column digests identical | 33 of 33 |
| T1 | company_age / stipend contain no non-integral non-null values | **PASS** | 0 | 0 |
| T2 | One-decimal columns retain one-decimal precision | **PASS** | 0 off-grid values in recruiter_experience_years, recruiter_response_time_hours, trust_signal_score, fraud_score | 0 |
| T3 | No field failed numeric parsing | **PASS** | 0 | 0 |
| T4 | Identical 35-column schema written for every chunk | **PASS** | 1 schema variant across 10 chunk(s) | 1 |
| T5 | Header written exactly once | **PASS** | 1 header row, 35 columns | 1 header row, 35 columns |
| T6 | No negative value in any numeric column | **PASS** | 0 | 0 |
| T7 | Numeric columns stay inside their documented observed ranges | **PASS** | 0 out of range | 0 |
| T8 | Text columns unpadded, non-empty, no whitespace-only values | **PASS** | padded 0, empty 0, whitespace-only 0 | 0 / 0 / 0 |
| T9 | Categorical distinct counts unchanged vs source | **PASS** | all 8 text columns match | match |
| T10 | Raw stream fully consumed in lockstep with staging | **PASS** | 0 | 0 |

### Notes on individual checks

- **3 &mdash; CSV read with a quote-aware parser (embedded commas preserved):** A naive split(',') would widen these rows and shift every later field.
- **4 &mdash; Every parsed record has exactly 33 source fields:** Any other width is treated as a fatal field-shift error.
- **6 &mdash; Staging row count:** No row removed, including the future-dated ones.
- **7 &mdash; Staging column count:** 33 source + 2 derived
- **9 &mdash; Original column order preserved:** The two derived columns are appended at positions 34-35.
- **14 &mdash; posting_date parse failures:** Failures are reported, never coerced or dropped.
- **18 &mdash; is_future_posting = 1 count:** Expectation only; the cutoff 2026-09-23 is the sole input to the rule.
- **18b &mdash; is_future_posting reproduces from the fixed cutoff on re-read:** Recomputed against 2026-09-23, never the system clock.
- **19 &mdash; company_age missing count:** Preserved as NULL; no imputation.
- **20 &mdash; stipend missing count:** Preserved as NULL; no imputation.
- **21 &mdash; trust_signal_score missing count:** Preserved as NULL; no imputation.
- **22b &mdash; Staging null counts equal raw null counts, column by column:** Proves no fill, no drop and no new null.
- **23 &mdash; All nine binary fields strictly in {0,1}, no nulls:** Kept as 0/1; not converted to Yes/No and not rebalanced.
- **23b &mdash; unrealistic_salary_flag retained and still constant 0:** Constant in this extract; kept because dropping it is a modelling decision.
- **24 &mdash; Seven score columns satisfy 0 <= value <= 100 where non-null:** Checked only; no value clipped.
- **25 &mdash; payment_required == (registration_fee > 0):** Validated, not used to derive either column.
- **26 &mdash; recruiter_email_type Corporate<->0 and Free<->1:** Validated, not used to derive either column.
- **26b &mdash; is_fake_posting not derived from fraud_score:** The two columns remain independently preserved; the audit found disagreement at fraud_score = 50.
- **27 &mdash; Exact duplicate source rows (33 source fields only):** source_row_id and is_future_posting are excluded; including source_row_id would make every row unique by definition. Checked only, never de-duplicated.
- **28 &mdash; Source values preserved through the round trip (element-wise):** Raw and staging are re-read in lockstep and typed by identical code.
- **T1 &mdash; company_age / stipend contain no non-integral non-null values:** Basis for nullable-integer typing; NULL preserved as NULL, never zero-filled.
- **T2 &mdash; One-decimal columns retain one-decimal precision:** Not rounded to integers.
- **T7 &mdash; Numeric columns stay inside their documented observed ranges:** Descriptive check; no value capped, winsorized, scaled or removed.
- **T8 &mdash; Text columns unpadded, non-empty, no whitespace-only values:** Reported, not trimmed: no unconditional TRIM or LOWER is applied.
- **T9 &mdash; Categorical distinct counts unchanged vs source:** No category mapped, merged, case-folded or ordinal-coded; company_size stays categorical.

---

## 2. CSV parsing integrity (fatal-on-failure)

The raw extract contains quoted text fields with embedded commas, for example `"Russell, Medina and Evans"` in `company_name`. Splitting a line on `,` would read that as two fields and shift every subsequent column by one position, silently corrupting 24 downstream columns.

**The pipeline never splits on commas.** Two independent quote-aware readers are used:

1. A structural pre-scan with the stdlib `csv` module (RFC 4180 quote handling), which walks every physical record and counts its fields.
2. `pandas.read_csv()` for the build and for the re-read of the output.

| Measurement | Value |
| --- | --- |
| Header fields | 33 |
| Records scanned | 1,000,000 |
| Distinct record widths | {33: 1000000} |
| Records not 33 fields wide | 0 |
| Records with a comma inside quoted `company_name` | 333,784 |

Every record parses to exactly 33 fields. **No field shift and no malformed parsing was found.** Any other width would be a fatal validation error and would abort the build.

Quoted field contents are preserved exactly: the output is re-read with the same quote-aware parser and compared element-wise against the raw file (check 28), so a mis-quoted write would surface as a value mismatch in `company_name`.

---

## 3. Raw-data immutability

| Item | Before | After |
| --- | --- | --- |
| sha256 | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Size (bytes) | 173,788,906 | 173,788,906 |
| mtime (ns) | 1790153224451672700 | 1790153224451672700 |

Raw file: unchanged. The digest also matches the value documented in `docs/data_dictionary.md`: `match`.

The raw CSV is opened read-only. Nothing is written to `data/raw/`, no file there is rewritten, and no timestamp there is touched. `source_row_id` is added to the **staging** dataset only.

---

## 4. Value preservation evidence

The staging CSV is re-read with `pandas.read_csv()` and walked in lockstep with the raw CSV, chunk for chunk. Both sides are typed by the **same function**, so any surviving difference is a real defect rather than an artefact of the comparison.

- Cells compared: 33,000,000 (1,000,000 rows x 33 source columns)
- Differing values: 0
- Differing null masks: 0

Additionally, an order-sensitive sha256 digest is accumulated per column on both sides (per-row 64-bit value hashes appended in file order, so the digest covers values **and** their sequence):

| Source column | Digest (first 16 hex) | Matches raw |
| --- | --- | --- |
| `posting_date` | `7abb04e2b95d0a88` | yes |
| `internship_title` | `4a70d0c63046493b` | yes |
| `employment_type` | `61dfa2cd9c24542e` | yes |
| `work_mode` | `c5014a5028a89308` | yes |
| `industry` | `2c7ac727b0777b40` | yes |
| `location` | `7df669bf70ae8c0f` | yes |
| `company_name` | `990528ea81d69e13` | yes |
| `company_size` | `1da43f2693bcb872` | yes |
| `company_age` | `5434bba741b795c8` | yes |
| `linkedin_presence` | `7e3a0bcd9626da75` | yes |
| `website_available` | `37b17e9f67299bbb` | yes |
| `domain_age_months` | `a812053cc3672a77` | yes |
| `verification_status` | `0f63c5e49d1aa946` | yes |
| `stipend` | `454a74b87050957c` | yes |
| `unrealistic_salary_flag` | `6506614505e113da` | yes |
| `payment_required` | `932a5648a16362d7` | yes |
| `registration_fee` | `3e4b5b577eb9fd40` | yes |
| `job_description_length` | `6348909b656464da` | yes |
| `grammatical_errors` | `d48479b4b610fd11` | yes |
| `vague_description_score` | `5195f79f39f3cbd5` | yes |
| `urgency_score` | `5ac3beef695122a1` | yes |
| `keyword_spam_score` | `400a8ef9795ffaee` | yes |
| `fake_certificate_offer` | `72fa724ff6788a84` | yes |
| `recruiter_experience_years` | `bec44830c39f0441` | yes |
| `recruiter_email_type` | `c830f447e02c538e` | yes |
| `suspicious_email_domain` | `126c5b4d4a53346d` | yes |
| `recruiter_response_time_hours` | `37b9e97e065f3da8` | yes |
| `social_media_presence` | `623f33709c526620` | yes |
| `emotional_manipulation_score` | `52bf58c5d66c464c` | yes |
| `phishing_language_score` | `8739376a44761272` | yes |
| `trust_signal_score` | `49c2af6657485402` | yes |
| `fraud_score` | `8f725146de7ef400` | yes |
| `is_fake_posting` | `2c8095f4de609aee` | yes |

`posting_date` is digested from its ISO `YYYY-MM-DD` rendering on both sides. That is the one approved representation change, and it is value-preserving: the source is already written as `YYYY-MM-DD`, so no date is re-interpreted, shifted or re-formatted into a different calendar value.

`company_age` and `stipend` are written without the trailing `.0` that pandas produced when reading them as floats. This is a **datatype representation change, not a value change**: check T1 confirms 0 non-integral non-null values across all 1,000,000 rows, and the element-wise comparison in check 28 is numeric, so `43083.0` and `43083` compare equal. NULLs stay NULL and are never replaced by zero.

---

## 5. Unresolved semantic limitation &mdash; `stipend`

**The source documents neither a currency nor a pay period for `stipend`.** Values range from 2,000 to 110,428 across nine locations (Bangalore, Berlin, Dubai, London, New York, San Francisco, Singapore, Sydney, Toronto), and nothing in the extract states whether a value is monthly or annual, or which currency it is denominated in.

Consequently the staging layer:

- preserves `stipend` numerically, exactly as supplied;
- does **not** convert currencies;
- does **not** annualise or otherwise re-base the pay period;
- does **not** normalise across locations;
- does **not** create stipend bands.

**This limitation is unresolved and is carried forward.** Until the currency and pay period are established, `stipend` values from different locations must not be assumed directly comparable, and any cross-location aggregation of `stipend` in the analytical layer would be unsound. The same caveat is recorded in [transformation_log.md](transformation_log.md).

---

## 6. Known relationships &mdash; validated, never used to derive

| Relationship | Violations | Action taken |
| --- | ---: | --- |
| `payment_required == (registration_fee > 0)` | 0 | Both columns kept and preserved independently. Neither is derived from the other. |
| `recruiter_email_type` Corporate&harr;0, Free&harr;1 | 0 | Both columns kept and preserved independently. Neither is derived from the other. |
| `fraud_score` &rarr; `is_fake_posting` | n/a | **Not derived.** The audit found the two disagree at `fraud_score = 50`, so the label is not a function of the score. Both are preserved independently. |

---

## 7. What this run did not do

No imputation, no row deletion, no column deletion, no de-duplication, no category mapping or merging, no ordinal coding, no case folding or trimming, no scaling or standardisation, no outlier removal, capping or winsorizing, no currency conversion, no stipend normalisation or banding, no class rebalancing, and no label derivation. The full list with reasons is in [transformation_log.md](transformation_log.md).

