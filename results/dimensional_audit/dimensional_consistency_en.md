# Dimensional Consistency / Functional Dependency Audit

## 1. Purpose

This audit asks one question: **which attributes can safely be grouped together into a dimension?** It answers it with measurements, not with a design.

Grouping attributes into a dimension is a claim about dependency. Putting `company_size` next to `company_name` claims that a company has a size; putting `industry` next to `internship_title` claims that a title belongs to an industry. Those claims are testable before any schema is drawn, and this audit tests them.

**What this audit does not do.** It does not design the star schema, does not fix the grain, does not create SQL, does not choose surrogate keys, and does not decide which of two redundant columns to keep. Where the evidence is ambiguous the ambiguity is recorded rather than resolved. Sections 10 and 11 list exactly what is left open.

**Reading rule.** A differing value inside a group is reported as *variation*, not as an *error*. This dataset carries no company identifier, no recruiter identifier and no posting identifier, so a disagreement between two rows may mean bad data, or it may mean the two rows were never about the same thing. Nothing below assumes which.

## 2. Data basis

| Item | Value |
| --- | --- |
| Source file | `E:/project/internship-scam-dw/data/staging/internship_postings_staging.csv` |
| Rows x columns | 1,000,000 x 33 |
| File size | 170.4 MB |
| sha256 before the audit | `e86ab0983fa456d24e0a8403e2af7cb4d19adf69fc7995f641af9d85b7adefa3` |
| sha256 after the audit | `e86ab0983fa456d24e0a8403e2af7cb4d19adf69fc7995f641af9d85b7adefa3` |
| Staging file unchanged | **YES** |
| Generated at | 2026-09-23 18:17:28 |
| Script | `scripts/audit_dimensional_consistency.py` |
| Rows analysed | 1,000,000 |
| posting_date range | 2018-01-01 -> 2026-12-31 (3,287 distinct dates) |

Authoritative documentation used for the semantics of every column: `docs/data_dictionary.md` and `docs/cleaning_rules.md`. Prior evidence reused rather than re-derived: `results/profiling/`, `results/audit/`, `results/staging/`.

**Integrity.** The staging CSV was opened read-only. No value was cleaned, imputed, capped, dropped, normalised, encoded, resolved or de-duplicated. Two working columns (a date ordinal and a posting year) were derived in memory for the time-series checks and were never written anywhere. The sha256 above was measured before the run started and again after every output had been written.

**A note on the CSV outputs.** The companion CSV files in this directory use English column names and English evidence text, because they are machine-readable artefacts shared by both language versions of this report. Every number they contain also appears in both reports.

## 3. Company consistency

### 3.1 How company_name behaves as a group

`company_name` is used here purely as a **grouping attribute**. It is not assumed to be a company ID, and the data dictionary is explicit that no company identifier exists in this source.

| Metric | Value |
| --- | ---: |
| Distinct company_name values | 535,938 |
| Appearing on exactly one row | 471,992 (88.0684%) |
| Appearing on more than one row | 63,946 (11.9316%) |
| Rows covered by repeated names | 528,008 (52.8008%) |
| Mean postings per company_name | 1.865887 |
| Most postings for one company_name | 1,248 (`Smith PLC`) |

Distribution of postings per `company_name`:

| Postings | company_name values | % of names | Rows covered | % of rows |
| --- | ---: | ---: | ---: | ---: |
| 1 | 471,992 | 88.0684 | 471,992 | 47.1992 |
| 2 | 33,422 | 6.2362 | 66,844 | 6.6844 |
| 3 | 11,021 | 2.0564 | 33,063 | 3.3063 |
| 4 | 5,055 | 0.9432 | 20,220 | 2.0220 |
| 5-9 | 6,516 | 1.2158 | 40,369 | 4.0369 |
| 10-19 | 2,612 | 0.4874 | 37,000 | 3.7000 |
| 20-49 | 3,563 | 0.6648 | 107,616 | 10.7616 |
| 50+ | 1,757 | 0.3278 | 222,896 | 22.2896 |

### 3.2 Stability of the dependent attributes

For each attribute the table below counts, among the 63,946 `company_name` values that appear on more than one row, how many carry exactly one distinct value and how many carry several. Single-row names are excluded because they are stable by construction and would inflate every percentage towards 100%. Missing values are excluded from the distinct-value count rather than treated as a value of their own.

| Attribute | Repeated names | Exactly 1 distinct value | Multiple distinct values | % stable | Max distinct for one name | Distinct in dataset |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `company_size` | 63,946 | 9,782 | 54,164 | 15.2973 | 4 | 4 |
| `company_age` | 63,946 | 1,531 | 62,411 | 2.3942 | 39 | 39 |
| `linkedin_presence` | 63,946 | 32,453 | 31,493 | 50.7506 | 2 | 2 |
| `website_available` | 63,946 | 36,943 | 27,003 | 57.7722 | 2 | 2 |
| `domain_age_months` | 63,946 | 75 | 63,871 | 0.1173 | 451 | 500 |
| `verification_status` | 63,946 | 25,362 | 38,584 | 39.6616 | 2 | 2 |
| `social_media_presence` | 63,946 | 28,599 | 35,347 | 44.7237 | 2 | 2 |
| `location` | 63,946 | 3,927 | 60,019 | 6.1411 | 9 | 9 |
| `industry` | 63,946 | 3,812 | 60,134 | 5.9613 | 9 | 9 |

The most stable attribute is `website_available` at 57.7722%; the least stable is `domain_age_months` at 0.1173%.

**How to read this.** A low stability percentage does **not** establish that the data is wrong. Two readings fit the same numbers equally well: either a single company genuinely changed its recorded attributes between postings, or rows sharing a `company_name` are simply different companies with the same name. The data dictionary already warns that the names follow a `<Surname> <Suffix>` pattern and that name similarity must not be read as company identity. Nothing in this dataset settles the question, and nothing here is corrected on the basis of it.

### 3.3 Selected examples

The `company_name` values below show the widest spread of distinct values across the nine attributes. They are listed as evidence to inspect, not as defects.

| company_name | Postings | `size` | `age` | `li` | `web` | `dom` | `ver` | `soc` | `loc` | `ind` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Smith LLC` | 1,198 | 4 | 39 | 2 | 2 | 451 | 2 | 2 | 9 | 9 |
| `Smith and Sons` | 1,244 | 4 | 39 | 2 | 2 | 449 | 2 | 2 | 9 | 9 |
| `Smith Inc` | 1,203 | 4 | 39 | 2 | 2 | 449 | 2 | 2 | 9 | 9 |
| `Smith PLC` | 1,248 | 4 | 39 | 2 | 2 | 443 | 2 | 2 | 9 | 9 |
| `Smith Group` | 1,186 | 4 | 39 | 2 | 2 | 440 | 2 | 2 | 9 | 9 |
| `Smith Ltd` | 1,205 | 4 | 39 | 2 | 2 | 439 | 2 | 2 | 9 | 9 |
| `Johnson Group` | 914 | 4 | 39 | 2 | 2 | 418 | 2 | 2 | 9 | 9 |
| `Johnson LLC` | 984 | 4 | 39 | 2 | 2 | 416 | 2 | 2 | 9 | 9 |
| `Johnson and Sons` | 928 | 4 | 39 | 2 | 2 | 414 | 2 | 2 | 9 | 9 |
| `Johnson Ltd` | 943 | 4 | 39 | 2 | 2 | 413 | 2 | 2 | 9 | 9 |
| `Johnson Inc` | 916 | 4 | 39 | 2 | 2 | 409 | 2 | 2 | 9 | 9 |
| `Johnson PLC` | 940 | 4 | 39 | 2 | 2 | 408 | 2 | 2 | 9 | 9 |

Column abbreviations: `size` = `company_size`, `age` = `company_age`, `li` = `linkedin_presence`, `web` = `website_available`, `dom` = `domain_age_months`, `ver` = `verification_status`, `soc` = `social_media_presence`, `loc` = `location`, `ind` = `industry`. Each cell is the number of distinct values that `company_name` takes for that attribute.

### 3.4 The combination test

Attribute-by-attribute stability is the generous test. The strict test asks whether `company_name` alone determines the **whole combination** of `company_size`, `linkedin_presence`, `website_available`, `verification_status`, `social_media_presence` at once - which is exactly what a single row in a `DimCompany` would assert.

| Metric | Value |
| --- | ---: |
| Distinct combinations observed | 64 / 64 |
| company_names with exactly one combination | 473,664 (88.3804%) |
| company_names with multiple combinations | 62,274 |
| Repeated names with exactly one combination | 1,672 / 63,946 (2.6147%) |
| Repeated names with multiple combinations | 62,274 |
| Max combinations for one name | 61 |
| company_name -> combination is a functional dependency | **No** |
| Rows inside violating groups | 524,627 (52.4627%) |

Distribution of the number of distinct combinations per `company_name`:

| Combinations | company_name values | % of names | Rows covered | % of rows |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 473,664 | 88.3804 | 475,373 | 47.5373 |
| 2 | 33,419 | 6.2356 | 68,604 | 6.8604 |
| 3 | 10,890 | 2.0320 | 34,301 | 3.4301 |
| 4 | 4,788 | 0.8934 | 20,489 | 2.0489 |
| 5 | 2,517 | 0.4696 | 13,806 | 1.3806 |
| 6 | 1,490 | 0.2780 | 10,115 | 1.0115 |
| 7 | 962 | 0.1795 | 7,741 | 0.7741 |
| 8 | 650 | 0.1213 | 6,366 | 0.6366 |
| 9 | 477 | 0.0890 | 5,531 | 0.5531 |
| 10 | 445 | 0.0830 | 5,973 | 0.5973 |
| 11 | 447 | 0.0834 | 6,876 | 0.6876 |
| 12 | 472 | 0.0881 | 8,130 | 0.8130 |
| 13 | 473 | 0.0883 | 9,050 | 0.9050 |
| 14 | 432 | 0.0806 | 9,064 | 0.9064 |
| 15 | 454 | 0.0847 | 10,370 | 1.0370 |
| 16 | 460 | 0.0858 | 11,659 | 1.1659 |
| 17 | 355 | 0.0662 | 9,785 | 0.9785 |
| 18 | 360 | 0.0672 | 10,618 | 1.0618 |
| 19 | 306 | 0.0571 | 9,972 | 0.9972 |
| 20 | 256 | 0.0478 | 8,920 | 0.8920 |
| 21 | 259 | 0.0483 | 9,680 | 0.9680 |
| 22 | 246 | 0.0459 | 10,151 | 1.0151 |
| 23 | 192 | 0.0358 | 8,363 | 0.8363 |
| 24 | 195 | 0.0364 | 9,606 | 0.9606 |
| 25 | 156 | 0.0291 | 8,073 | 0.8073 |
| 26 | 166 | 0.0310 | 9,745 | 0.9745 |
| 27 | 143 | 0.0267 | 8,802 | 0.8802 |
| 28 | 111 | 0.0207 | 7,470 | 0.7470 |
| 29 | 99 | 0.0185 | 7,034 | 0.7034 |
| 30 | 97 | 0.0181 | 7,533 | 0.7533 |
| 31 | 111 | 0.0207 | 8,946 | 0.8946 |
| 32 | 71 | 0.0132 | 6,202 | 0.6202 |
| 33 | 95 | 0.0177 | 8,553 | 0.8553 |
| 34 | 78 | 0.0146 | 7,817 | 0.7817 |
| 35 | 67 | 0.0125 | 7,003 | 0.7003 |
| 36 | 48 | 0.0090 | 5,315 | 0.5315 |
| 37 | 43 | 0.0080 | 5,278 | 0.5278 |
| 38 | 49 | 0.0091 | 6,432 | 0.6432 |
| 39 | 33 | 0.0062 | 4,657 | 0.4657 |
| 40 | 33 | 0.0062 | 4,937 | 0.4937 |
| 41 | 35 | 0.0065 | 5,414 | 0.5414 |
| 42 | 21 | 0.0039 | 3,788 | 0.3788 |
| 43 | 32 | 0.0060 | 5,745 | 0.5745 |
| 44 | 26 | 0.0049 | 5,434 | 0.5434 |
| 45 | 26 | 0.0049 | 5,981 | 0.5981 |
| 46 | 25 | 0.0047 | 6,428 | 0.6428 |
| 47 | 18 | 0.0034 | 5,258 | 0.5258 |
| 48 | 21 | 0.0039 | 6,233 | 0.6233 |
| 49 | 24 | 0.0045 | 7,549 | 0.7549 |
| 50 | 14 | 0.0026 | 5,000 | 0.5000 |
| 51 | 14 | 0.0026 | 4,975 | 0.4975 |
| 52 | 9 | 0.0017 | 3,426 | 0.3426 |
| 53 | 13 | 0.0024 | 5,161 | 0.5161 |
| 54 | 11 | 0.0021 | 5,090 | 0.5090 |
| 55 | 9 | 0.0017 | 5,137 | 0.5137 |
| 56 | 8 | 0.0015 | 5,041 | 0.5041 |
| 57 | 2 | 0.0004 | 1,459 | 0.1459 |
| 58 | 7 | 0.0013 | 5,094 | 0.5094 |
| 59 | 4 | 0.0007 | 4,316 | 0.4316 |
| 60 | 6 | 0.0011 | 4,814 | 0.4814 |
| 61 | 4 | 0.0007 | 4,317 | 0.4317 |

**This is the single most consequential measurement in the audit.** It is the direct test of whether a simple `DimCompany` keyed on `company_name` is defensible, and the answer is that it is not defensible on this evidence alone. That does not make a company dimension impossible - it makes it a decision that needs a stated assumption, not a decision the data supports by itself.

## 4. Time-varying company attributes

Sections 3.2 and 3.4 measured whether attributes differ. This section measures whether they differ **plausibly over calendar time**. For each `company_name` its rows are sorted by `posting_date` and consecutive postings are compared: the change in the stated age is set against the time that actually elapsed between the two postings.

### 4.1 company_age over time

| Metric | Value |
| --- | ---: |
| Repeated company_names with one distinct company_age | 1,531 (2.3942%) |
| Repeated company_names with several | 62,411 |
| Max distinct company_age for one name | 39 |
| Consecutive posting pairs examined | 458,854 |
| Pairs where company_age increases | 225,123 (49.0620%) |
| Pairs where it is unchanged | 11,591 (2.5261%) |
| Pairs where it **decreases** over time | **222,140** (48.4119%) |
| company_names showing at least one decrease | 44,130 |
| Same name, same day, conflicting company_age | 8,675 |
| (company_name, year) groups with >1 row | 72,173 |
| ... of those, with multiple company_age values | 70,872 (98.1974%) |
| Pairs outside a +/-1.0 year tolerance vs elapsed time | 435,828 (94.9818%) |
| Largest single decrease (years) | -38.0 |

**Evidence only.** A company's age cannot fall as the calendar advances, so 222,140 decreasing pairs and 70,872 (company, year) groups holding several ages are inconsistent with `company_age` being a property of a stable entity tracked over time. They are equally consistent with `company_name` not identifying a single entity. **No value is corrected, and no row is flagged as invalid.**

### 4.2 domain_age_months over time

| Metric | Value |
| --- | ---: |
| Repeated company_names with one distinct domain_age_months | 75 (0.1173%) |
| Repeated company_names with several | 63,871 |
| Max distinct domain_age_months for one name | 451 |
| Consecutive posting pairs examined | 464,062 |
| Pairs where it increases over time | 233,185 (50.2487%) |
| Pairs where it is unchanged | 969 (0.2088%) |
| Pairs where it **decreases** | **229,908** (49.5425%) |
| company_names showing at least one decrease | 45,197 |
| Same name, same day, conflicting value | 9,063 |
| Pairs outside a +/-6.0 month tolerance vs elapsed time | 452,442 (97.4960%) |
| company_names involved in those pairs | 63,125 |
| Largest single decrease (months) | -499.0 |
| Residual (change minus elapsed months): min / median / max | -565.36 / -5.41 / 498.93 |

A domain's age in months should rise by roughly the number of months that pass between two postings. The residual column above measures exactly that gap. As with `company_age`, the observed behaviour is reported and nothing is corrected: the data dictionary already records that `domain_age_months` exceeding `company_age * 12` is **not** treated as invalid, since acquired domains, rebrands and parked registrations all produce it legitimately.

**Modelling consequence.** If `company_name` were adopted as a company key, both ages would be time-varying attributes of that key, which is the textbook trigger for an SCD Type 2 design. The measurements above show the variation is not monotonic and therefore does not look like an entity history, so an SCD design would be recording version changes that may not correspond to anything real. This is stated as a risk, not as a recommendation either way.

## 5. Categorical dependencies

### 5.1 internship_title against the placement attributes

No dependency is assumed in either direction. The table reports association and cardinality only. Cramer's V is bias-corrected; a value near 0 means the two attributes vary independently.

| Pair | Levels | Observed / possible cells | Cramer's V | title -> attribute | attribute -> title | Values per title |
| --- | ---: | ---: | ---: | :---: | :---: | ---: |
| `internship_title` x `industry` | 9 x 9 | 81 / 81 | 0.001236 | no | no | 9-9 |
| `internship_title` x `employment_type` | 9 x 4 | 36 / 36 | 0.000000 | no | no | 4-4 |
| `internship_title` x `work_mode` | 9 x 3 | 27 / 27 | 0.001536 | no | no | 3-3 |
| `internship_title` x `location` | 9 x 9 | 81 / 81 | 0.000000 | no | no | 9-9 |

Row shares of the 9 titles run from 11.0502% to 11.1577%. The largest association measured is 0.001536. **`internship_title` determines none of the four attributes, and none of them determines it.** Every title x attribute grid is fully populated, which is the pattern of independent labels rather than of a hierarchy.

### 5.2 industry against internship_title

| Metric | Value |
| --- | ---: |
| Industries x titles | 9 x 9 = 81 cells |
| Populated cells | 81 (100.0000%) |
| Titles per industry (min-max) | 9-9 |
| Industries per title (min-max) | 9-9 |
| Cramer's V | 0.001236 |
| industry -> internship_title | no |
| internship_title -> industry | no |
| Smallest / largest cell | 11,980 / 12,635 |
| Expected cell under independence | 12,345.68 |

**No deterministic relationship exists in either direction.** Every industry carries all 9 titles and every title appears in all 9 industries; observed cell counts sit close to the 12,346 expected under independence. The two attributes are therefore **not** forced into a shared dimension here. Whether they end up together is a design decision about query convenience, and it must be made in the knowledge that it creates a 81-row cross product with no functional dependency behind it.

### 5.3 location

| location | Rows | % of rows | Distinct company_names | Rows per name | Industries | Titles | Fake postings | Fake rate % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Bangalore` | 111,441 | 11.1441 | 75,340 | 1.4792 | 9 | 9 | 25,155 | 22.5725 |
| `Berlin` | 110,990 | 11.0990 | 75,029 | 1.4793 | 9 | 9 | 24,651 | 22.2101 |
| `Dubai` | 110,987 | 11.0987 | 75,008 | 1.4797 | 9 | 9 | 24,699 | 22.2540 |
| `London` | 110,754 | 11.0754 | 75,016 | 1.4764 | 9 | 9 | 24,481 | 22.1039 |
| `New York` | 110,559 | 11.0559 | 74,712 | 1.4798 | 9 | 9 | 24,548 | 22.2035 |
| `San Francisco` | 111,390 | 11.1390 | 75,379 | 1.4777 | 9 | 9 | 24,732 | 22.2031 |
| `Singapore` | 110,882 | 11.0882 | 75,243 | 1.4737 | 9 | 9 | 24,636 | 22.2182 |
| `Sydney` | 111,520 | 11.1520 | 75,544 | 1.4762 | 9 | 9 | 24,624 | 22.0803 |
| `Toronto` | 111,477 | 11.1477 | 75,735 | 1.4719 | 9 | 9 | 24,432 | 21.9166 |

Fake-posting rates run from 21.9166% to 22.5725% against a dataset baseline of 22.1958% - a spread of 0.6559 percentage points. The association between `location` and `industry` is 0.000000.

Note also that the nine per-location `company_name` counts sum to 677,006 against 535,938 distinct names overall - the same name appears in more than one city, which is further evidence that `company_name` does not behave as an entity key.

> **Limitation preserved: stipend is deliberately not reported by location.** The currency and the pay period of `stipend` are undocumented in the source, and the nine cities sit in different currency areas. Any average, total or comparison of `stipend` across `location` would add or compare different units and would look authoritative while meaning nothing. This limitation is unresolved and is carried forward to sections 7, 10 and 11.

### 5.4 employment_type and work_mode

| employment_type \ work_mode | Hybrid | Onsite | Remote | Total |
| --- | ---: | ---: | ---: | ---: |
| `Contract` | 62,499 | 50,033 | 137,137 | 249,669 |
| `Full-Time` | 62,201 | 50,077 | 137,355 | 249,633 |
| `Internship` | 62,943 | 49,832 | 137,223 | 249,998 |
| `Part-Time` | 62,883 | 50,193 | 137,624 | 250,700 |
| **Total** | 250,526 | 200,135 | 549,339 | 1,000,000 |

| Metric | Value |
| --- | ---: |
| Possible combinations | 12 |
| Observed combinations | 12 |
| All combinations occur | **Yes** |
| Smallest / largest cell | 49,832 (4.9832%) / 137,624 (13.7624%) |
| Cramer's V | 0.000000 |
| employment_type -> work_mode | no |
| work_mode -> employment_type | no |

Neither attribute functionally determines the other and the grid is complete, so the pair is two independent labels. They can be kept as two dimensions or merged into one small combined dimension; both are defensible and neither is chosen here.

### 5.5 Email attributes

| Metric | Value |
| --- | ---: |
| recruiter_email_type -> suspicious_email_domain | holds (0 violating rows) |
| suspicious_email_domain -> recruiter_email_type | holds (0 violating rows) |
| Perfect bijection | **CONFIRMED** |
| Populated cells | 2 / 4 |
| Cramer's V | 1.000000 |

| recruiter_email_type | suspicious_email_domain | Rows | % of rows |
| --- | ---: | ---: | ---: |
| `Corporate` | 0 | 749,433 | 74.9433 |
| `Corporate` | 1 | 0 | 0.0000 |
| `Free` | 0 | 0 | 0.0000 |
| `Free` | 1 | 250,567 | 25.0567 |

**Confirmed in staging.** The bijection established by the earlier audit still holds exactly. For dimensional modelling this means that storing both attributes in the same small dimension would store one attribute's information twice: given either value, the other is known with certainty. **That redundancy is documented here, not acted on.** Dropping one of them is a schema decision, and it has a real cost - the two columns are not interchangeable in meaning, one being a human-readable label and the other a flag, and a later extract could break the bijection.

### 5.6 Payment attributes

| Check | Value |
| --- | ---: |
| Rows examined | 1,000,000 |
| payment_required == (registration_fee > 0) | **HOLDS EXACTLY** |
| Rows disagreeing | 0 |
| payment_required = 0 with a positive fee | 0 |
| payment_required = 1 with fee = 0 | 0 |
| Rows with payment_required = 1 | 99,905 (9.9905%) |
| Rows with registration_fee = 0 | 900,095 (90.0095%) |
| Distinct fee values (all rows / rows with fee > 0) | 4,951 / 4,950 |
| Fee > 0: min / median / max | 50 / 2,520.0 / 4,999 |

**Confirmed again on staging.** Structurally the two columns are not the same kind of thing: `payment_required` is a **flag** with two states, suited to being a dimension attribute or a junk-dimension member, while `registration_fee` is a **numeric amount** that can be summed and averaged, suited to being a fact measure. The flag is a coarsening of the amount - it can always be recomputed from it, but the amount can never be recovered from the flag.

**Neither column is removed and no decision is made here** about whether one is stored as a measure, the other as a derived field, or both are kept. That choice belongs to the star-schema stage and is listed in section 10.

### 5.7 Low-cardinality bundles

How many combinations each candidate bundle actually takes. A small observed count means a junk dimension is technically feasible; it says nothing about whether one is appropriate.

| Bundle | Attributes | Observed / possible | Largest combination |
| --- | --- | ---: | ---: |
| `trust_presence_flags` | `linkedin_presence + website_available + verification_status + social_media_presence` | 16 / 16 | 357,337 (35.7337%) |
| `fraud_flags` | `payment_required + fake_certificate_offer + suspicious_email_domain + unrealistic_salary_flag` | 8 / 8 | 620,594 (62.0594%) |
| `employment_arrangement` | `employment_type + work_mode` | 12 / 12 | 137,624 (13.7624%) |
| `company_presence_5` | `company_size + linkedin_presence + website_available + verification_status + social_media_presence` | 64 / 64 | 107,190 (10.7190%) |
| `recruiter_email_pair` | `recruiter_email_type + suspicious_email_domain` | 2 / 4 | 749,433 (74.9433%) |

## 6. Candidate dimensions

### 6.1 Provisional field classification

Each field in the three logical groups named in the brief - content quality, trust/company, and fraud/outcome - is classified **provisionally**. No dimension is created from a group merely because its members sound related. The column *% stable* is the share of multi-row `company_name` values for which the field takes a single distinct value; it is the main evidence separating company attributes from posting-level values.

**Content quality**

| Field | Provisional class | Distinct | Missing % | % stable within company_name | Evidence |
| --- | --- | ---: | ---: | ---: | --- |
| `emotional_manipulation_score` | **candidate measure** | 101 | 0.0000 | 1.4528 | Bounded 0-100 score recorded per posting; the construction rule is undocumented. |
| `grammatical_errors` | **candidate measure** | 15 | 0.0000 | 9.3814 | A count (0-14). Additive as a count; could alternatively be banded into a dimension attribute, which is not decided here. |
| `job_description_length` | **candidate measure** | 3,946 | 0.0000 | 0.0297 | Numeric, wide range, varies row by row inside the same company_name; nothing about it is a label to slice by. |
| `keyword_spam_score` | **candidate measure** | 101 | 0.0000 | 1.3683 | Bounded 0-100 score recorded per posting; the construction rule is undocumented. |
| `phishing_language_score` | **candidate measure** | 100 | 0.0000 | 1.9782 | Bounded 0-100 score recorded per posting; the construction rule is undocumented. |
| `urgency_score` | **candidate measure** | 101 | 0.0000 | 0.7381 | Bounded 0-100 score recorded per posting; the construction rule is undocumented. |
| `vague_description_score` | **candidate measure** | 101 | 0.0000 | 1.0571 | Bounded 0-100 score recorded per posting; the construction rule is undocumented. |

**Trust / company**

| Field | Provisional class | Distinct | Missing % | % stable within company_name | Evidence |
| --- | --- | ---: | ---: | ---: | --- |
| `domain_age_months` | **unresolved** | 500 | 0.0000 | 0.1173 | Numeric and company-flavoured at the same time: it would be a slowly changing company attribute if company_name were an entity key, and a per-posting measure otherwise. The instability measured below leaves both readings open. |
| `linkedin_presence` | **candidate flag** | 2 | 0.0000 | 50.7506 | Binary 0/1. Reads as a company property, but it is not stable across rows sharing a company_name, so it cannot be attached to a company entity on this evidence. |
| `social_media_presence` | **candidate flag** | 2 | 0.0000 | 44.7237 | Binary 0/1. Same situation as linkedin_presence. |
| `trust_signal_score` | **candidate measure** | 1,001 | 1.0000 | 1.0556 | Bounded composite score, 1% missing, established by the earlier audit as NOT deterministic from the four trust flags. |
| `verification_status` | **candidate flag** | 2 | 0.0000 | 39.6616 | Binary 0/1. Same situation as linkedin_presence. |
| `website_available` | **candidate flag** | 2 | 0.0000 | 57.7722 | Binary 0/1. Same situation as linkedin_presence. |

**Fraud / outcome**

| Field | Provisional class | Distinct | Missing % | % stable within company_name | Evidence |
| --- | --- | ---: | ---: | ---: | --- |
| `fake_certificate_offer` | **candidate flag** | 2 | 0.0000 | 71.6089 | Binary 0/1 describing what the posting offers. |
| `fraud_score` | **candidate measure** | 1,001 | 0.0000 | 0.2189 | Bounded 0-100 composite; the earlier audit established it does NOT determine is_fake_posting. |
| `is_fake_posting` | **outcome** | 2 | 0.0000 | 48.0921 | The labelled result of a posting. It is what the warehouse is built to analyse, not a slicing attribute chosen independently of it. |
| `payment_required` | **candidate flag** | 2 | 0.0000 | 67.1395 | Binary 0/1, and exactly reproducible from registration_fee > 0. Storing it is a redundancy question, not an information question. |
| `registration_fee` | **candidate measure** | 4,951 | 0.0000 | 66.6171 | Numeric and genuinely a quantity; 0 is meaningful (no fee), not a placeholder. Currency is undocumented. |
| `suspicious_email_domain` | **candidate flag** | 2 | 0.0000 | 44.5126 | Binary 0/1, in perfect bijection with recruiter_email_type; the pair carries one attribute's worth of information. |
| `unrealistic_salary_flag` | **degenerate attribute** | 1 | 0.0000 | 100.0000 | Constant across all rows. A single-valued attribute produces a one-member dimension and cannot slice anything; it is kept in staging and its warehouse treatment is deferred. |

Fields outside the three groups, classified on the same evidence:

| Field | Provisional class | Distinct | Missing % | % stable within company_name | Evidence |
| --- | --- | ---: | ---: | ---: | --- |
| `company_age` | **unresolved** | 39 | 1.0000 | 2.3942 | Numeric, but semantically a company property measured in years. Same ambiguity as domain_age_months. |
| `company_size` | **candidate dimension attribute** | 4 | 0.0000 | 15.2973 | Four-valued label with no natural order; a textbook slicing attribute, subject to the company-identity problem below. |
| `employment_type` | **candidate dimension attribute** | 4 | 0.0000 | 14.2308 | Four-valued contractual label. |
| `industry` | **candidate dimension attribute** | 9 | 0.0000 | 5.9613 | Nine-valued label, complete and near-uniform. |
| `internship_title` | **candidate dimension attribute** | 9 | 0.0000 | 6.1052 | Nine-valued label describing the role advertised. |
| `is_future_posting` | **candidate flag** | 2 | 0.0000 | 85.4612 | Staging-derived data-quality marker against a fixed reference date; not a business attribute. |
| `location` | **candidate dimension attribute** | 9 | 0.0000 | 6.1411 | Nine-valued label, complete and near-uniform. What it locates - work, company or recruiter - is not established by the source. |
| `recruiter_email_type` | **candidate dimension attribute** | 2 | 0.0000 | 44.5126 | Two-valued label; carries the same information as suspicious_email_domain. |
| `recruiter_experience_years` | **candidate measure** | 183 | 0.0000 | 0.6396 | Numeric level recorded per posting. There is no recruiter identifier, so it cannot be attached to a recruiter entity. |
| `recruiter_response_time_hours` | **candidate measure** | 595 | 0.0000 | 0.2612 | Numeric duration recorded per posting; same absence of a recruiter identifier. |
| `stipend` | **unresolved** | 73,830 | 1.0000 | 1.0571 | Numeric, but currency and pay period are undocumented, so it cannot yet be called a measure of anything specific. |
| `work_mode` | **candidate dimension attribute** | 3 | 0.0000 | 25.5278 | Three-valued label describing where the work happens. |

### 6.2 Candidate dimension groups

**These are candidates for later review. No star schema is proposed, and the list below is not a design.** Confidence states how well the evidence supports the grouping, not how useful the dimension would be.

#### Date - confidence: **High**

| Aspect | Finding |
| --- | --- |
| Possible attributes | `posting_date`, `is_future_posting` - plus calendar attributes derived from posting_date (year, quarter, month, day of week) |
| Evidence supporting the grouping | posting_date is present and parseable on all 1,000,000 rows, with 3,287 distinct dates spanning 2018-01-01 to 2026-12-31. A date dimension is generated from the calendar, not inferred from the data, so its attributes need no evidence of stability. |
| Consistency problems | 30,246 rows (3.0246%) are dated after the fixed reference date 2026-09-23 and are flagged, not filtered. A date dimension must therefore cover future dates or those rows lose their join. |
| Cardinality concerns | 3,287 rows if built at day grain over the observed range - trivially small. |
| Time-variance concerns | None. Calendar attributes of a given date do not change. |
| SCD consideration | Not applicable. |
| Confidence | **High** |

#### Internship / Role - confidence: **Medium**

| Aspect | Finding |
| --- | --- |
| Possible attributes | `internship_title` - and possibly industry |
| Evidence supporting the grouping | internship_title takes 9 values, shares of rows from 11.0502% to 11.1577%. Against industry, all 81 of 81 cells are populated and Cramer's V is 0.001236, i.e. the two vary independently. |
| Consistency problems | internship_title does NOT determine industry (9 industries per title) and industry does NOT determine internship_title (9 titles per industry). Folding both into one dimension would create a cross product of 81 rows with no functional dependency to justify it. |
| Cardinality concerns | 9 rows alone, or 81 if industry is folded in. |
| Time-variance concerns | The nine labels are stable strings; no attribute of a title changes over time in this extract. |
| SCD consideration | Not needed at this cardinality if the dimension is a plain lookup of the labels. |
| Confidence | **Medium** |

#### Company - confidence: **Low**

| Aspect | Finding |
| --- | --- |
| Possible attributes | `company_name`, `company_size`, `company_age`, `linkedin_presence`, `website_available`, `domain_age_months`, `verification_status`, `social_media_presence` |
| Evidence supporting the grouping | company_name is the only company handle in the dataset: 535,938 distinct values over 1,000,000 rows, of which 63,946 (11.9316%) appear on more than one row, covering 528,008 rows (52.8008%). |
| Consistency problems | Severe. Only 1,672 of 63,946 repeated company_names (2.6147%) carry a single combination of the five presence attributes. The weakest single attribute is domain_age_months at 0.1173% stable. Either company_name is not a company identifier, or a company's recorded attributes change between postings; the data cannot tell the two apart. |
| Cardinality concerns | 535,938 members - 53.5938% of the fact row count. A dimension at that size is close to storing the fact table twice. |
| Time-variance concerns | Measured directly: of 458,854 consecutive posting pairs inside one company_name, company_age decreases in 222,140 (48.4119%) and domain_age_months decreases in 229,908 (49.5425%). These attributes do not behave like a monotonic company history. |
| SCD consideration | SCD Type 2 would be the textbook answer to changing company attributes, but SCD presupposes a stable business key. There is none here, so an SCD design would version an identifier that may not identify anything. |
| Confidence | **Low** |

#### Location - confidence: **Medium**

| Aspect | Finding |
| --- | --- |
| Possible attributes | `location` |
| Evidence supporting the grouping | 9 values, each between 11.0559% and 11.1520% of rows, complete on every row. Fake-posting rate runs from 21.9166% to 22.5725% against a 22.1958% baseline - a spread of 0.6559 pp. |
| Consistency problems | Semantic, not structural. The source does not say whether location is the work location, the company location or the recruiter location, and there is no country, region or country-code column, so no geographic hierarchy can be built from this dataset alone. |
| Cardinality concerns | 9 rows. |
| Time-variance concerns | None observed. |
| SCD consideration | Not needed unless a hierarchy is imported from outside and later revised. |
| Confidence | **Medium** |

#### Employment / Work Arrangement - confidence: **High**

| Aspect | Finding |
| --- | --- |
| Possible attributes | `employment_type`, `work_mode` |
| Evidence supporting the grouping | All 12 of 12 employment_type x work_mode combinations occur, cell sizes from 4.9832% to 13.7624% of rows, and Cramer's V is 0.000000. Neither attribute determines the other, so the pair is a small complete grid rather than a hierarchy. |
| Consistency problems | Only that employment_type contains values (Full-Time, Part-Time, Contract) that sit oddly beside the word internship in a dataset about internship postings. That is a source-semantics question, not a data defect. |
| Cardinality concerns | 12 rows as a combined dimension, or 4 + 3 as two. |
| Time-variance concerns | None observed. |
| SCD consideration | Not needed. |
| Confidence | **High** |

#### Recruiter - confidence: **Medium**

| Aspect | Finding |
| --- | --- |
| Possible attributes | `recruiter_email_type`, `suspicious_email_domain` |
| Evidence supporting the grouping | The bijection recruiter_email_type <-> suspicious_email_domain still holds exactly in staging: 0 forward and 0 reverse violating rows, 2 of 4 cells populated, Cramer's V 1.000000. A two-row dimension is trivially cheap. |
| Consistency problems | There is no recruiter identifier anywhere in the dataset. recruiter_experience_years and recruiter_response_time_hours therefore cannot be attached to a recruiter entity and behave as per-posting numbers. Storing both email attributes in one dimension duplicates a single attribute's information. |
| Cardinality concerns | 2 rows. |
| Time-variance concerns | None observed. |
| SCD consideration | Not needed. |
| Confidence | **Medium** |

#### Fraud / Risk attributes - confidence: **Low**

| Aspect | Finding |
| --- | --- |
| Possible attributes | `payment_required`, `fake_certificate_offer`, `suspicious_email_domain`, `unrealistic_salary_flag` - and, as a separate bundle, the trust flags linkedin_presence, website_available, verification_status and social_media_presence |
| Evidence supporting the grouping | The four fraud flags take 8 of 8 possible combinations; the four trust flags take 16 of 16. Both bundles are small enough to be technically feasible as junk dimensions. |
| Consistency problems | Feasible is not the same as correct. is_fake_posting is the analytical outcome and does not belong in a slicing dimension alongside its own predictors; unrealistic_salary_flag is constant and would add a column that never varies; suspicious_email_domain already appears in the Recruiter candidate, so the same information would be reachable by two paths. |
| Cardinality concerns | 8 and 16 rows respectively. |
| Time-variance concerns | The trust flags are unstable within company_name (see the company section), which is why they are treated as posting-level flags here rather than company attributes. |
| SCD consideration | Not applicable to a junk dimension of flag combinations. |
| Confidence | **Low** |

## 7. Candidate measures

Additivity is classified per candidate. **Scores are not treated as additive by default**: a bounded score is not a quantity that accumulates, and summing two scores can exceed the maximum of the scale they are drawn from.

| Measure candidate | Additivity | Measured basis | Why |
| --- | --- | --- | --- |
| `posting_count` | **additive** | Not a stored column: the count of fact rows, 1 per posting, 1,000,000 in total. | Sums correctly across every dimension. The safest measure in the dataset. |
| `registration_fee` | **unresolved** | Range 0 to 4,999, mean 252.083069, 900,095 rows at 0 (90.0095%) where 0 means no fee. | Structurally additive - it is a money amount and the 0 values are real. Marked unresolved because the currency is undocumented, so a sum across the nine cities adds different units together. |
| `stipend` | **unresolved** | Range 2,000 to 110,428, mean 35,066.1992, median 34,984.0, 10,000 missing rows. | SEMANTICALLY UNRESOLVED. Neither the currency nor the pay period (monthly, annual, total) is documented, and rows span nine cities in different currency areas. Summing or averaging stipend across location would produce a number with no defensible meaning. No stipend figure is reported per location anywhere in this audit. |
| `job_description_length` | **additive** | Range 100 to 5,000, mean 1,799.5383, 3,946 distinct values. | A length in characters; a total length over a set of postings is a real quantity. The average is the more useful aggregate in practice. |
| `grammatical_errors` | **additive** | Integer count from 0 to 14, mean 2.998825. | A count of occurrences, so totals are meaningful. |
| `vague_description_score` | **non-additive** | Bounded score 0 to 100, 101 distinct values, mean 30.132072. | A bounded score is not a quantity that accumulates: adding two scores can exceed the scale's own maximum. Only averages, medians and distributions are defensible, and even those assume the undocumented scoring rule is comparable across rows. |
| `urgency_score` | **non-additive** | Bounded score 0 to 100, 101 distinct values, mean 40.047191. | A bounded score is not a quantity that accumulates: adding two scores can exceed the scale's own maximum. Only averages, medians and distributions are defensible, and even those assume the undocumented scoring rule is comparable across rows. |
| `keyword_spam_score` | **non-additive** | Bounded score 0 to 100, 101 distinct values, mean 25.573860. | A bounded score is not a quantity that accumulates: adding two scores can exceed the scale's own maximum. Only averages, medians and distributions are defensible, and even those assume the undocumented scoring rule is comparable across rows. |
| `emotional_manipulation_score` | **non-additive** | Bounded score 0 to 100, 101 distinct values, mean 25.563839. | A bounded score is not a quantity that accumulates: adding two scores can exceed the scale's own maximum. Only averages, medians and distributions are defensible, and even those assume the undocumented scoring rule is comparable across rows. |
| `phishing_language_score` | **non-additive** | Bounded score 0 to 100, 100 distinct values, mean 20.749288. | A bounded score is not a quantity that accumulates: adding two scores can exceed the scale's own maximum. Only averages, medians and distributions are defensible, and even those assume the undocumented scoring rule is comparable across rows. |
| `trust_signal_score` | **non-additive** | Bounded composite 0.0 to 100.0, mean 56.555847, 10,000 missing rows. | Composite and bounded, so not additive. The earlier audit established it is not reproducible from the four trust flags, so it also cannot be recomputed if dropped. |
| `fraud_score` | **non-additive** | Bounded composite 0.0 to 100.0, mean 34.012257, 1,001 distinct values. | Same reasoning as the other scores. It is also close to, but not deterministic of, is_fake_posting, so the two must not be treated as interchangeable. |
| `recruiter_experience_years` | **non-additive** | Range 0.0 to 19.6, mean 5.052660. | A level attached to a person, not a flow. Summing years of experience across postings counts the same recruiter repeatedly - and with no recruiter identifier, there is no way to know how often. |
| `recruiter_response_time_hours` | **non-additive** | Range 1.0 to 63.9 hours, mean 18.180468. | A duration per posting; averages are meaningful, totals are not. |
| `company_age` | **semi-additive** | Range 1 to 39 years, 10,000 missing rows, 39 distinct values. | A stock, not a flow: it can be averaged across any dimension but never summed over time, which is the defining behaviour of a semi-additive measure. Whether it belongs in the fact at all depends on the unresolved company-identity question. |
| `domain_age_months` | **semi-additive** | Range 1 to 500 months, 500 distinct values, mean 239.541209. | Same reasoning as company_age. |
| `is_fake_posting` | **additive** | Binary outcome; 221,958 positive rows (22.1958% of all rows). | Additive when summed as a counter of fake postings. It is the outcome being analysed, so it is listed here as a measure and NOT as a slicing attribute. |
| `payment_required` | **additive** | Binary 0/1; 99,905 rows carry 1 (9.9905%). | Additive only in the narrow sense that summing the flag counts the rows where it is set. Whether it is stored as a fact counter or as a dimension attribute is a schema decision left open. |
| `fake_certificate_offer` | **additive** | Binary 0/1; 79,830 rows carry 1 (7.9830%). | Additive only in the narrow sense that summing the flag counts the rows where it is set. Whether it is stored as a fact counter or as a dimension attribute is a schema decision left open. |
| `suspicious_email_domain` | **additive** | Binary 0/1; 250,567 rows carry 1 (25.0567%). | Additive only in the narrow sense that summing the flag counts the rows where it is set. Whether it is stored as a fact counter or as a dimension attribute is a schema decision left open. |
| `linkedin_presence` | **additive** | Binary 0/1; 800,764 rows carry 1 (80.0764%). | Additive only in the narrow sense that summing the flag counts the rows where it is set. Whether it is stored as a fact counter or as a dimension attribute is a schema decision left open. |
| `website_available` | **additive** | Binary 0/1; 849,597 rows carry 1 (84.9597%). | Additive only in the narrow sense that summing the flag counts the rows where it is set. Whether it is stored as a fact counter or as a dimension attribute is a schema decision left open. |
| `verification_status` | **additive** | Binary 0/1; 699,713 rows carry 1 (69.9713%). | Additive only in the narrow sense that summing the flag counts the rows where it is set. Whether it is stored as a fact counter or as a dimension attribute is a schema decision left open. |
| `social_media_presence` | **additive** | Binary 0/1; 749,800 rows carry 1 (74.9800%). | Additive only in the narrow sense that summing the flag counts the rows where it is set. Whether it is stored as a fact counter or as a dimension attribute is a schema decision left open. |
| `unrealistic_salary_flag` | **non-additive** | Constant: 1 distinct value over 1,000,000 rows, sum 0. | Its sum is 0 by construction on this extract, so aggregating it carries no information. It is neither removed nor relied upon. |

> **`stipend` remains semantically unresolved.** It is listed as a measure candidate because it is numeric, but neither its currency nor its pay period (monthly, annual or total) is documented, so what it measures is unknown. Until that is settled, no aggregate of `stipend` - and in particular no comparison across `location` - can be defended.

## 8. Grain evidence

The proposition under test is: **one row represents one internship posting.** It is evaluated, not adopted.

**Evidence supporting this grain**

| Evidence | Value |
| --- | ---: |
| Rows in staging | 1,000,000 |
| Exact duplicate rows (all 34 business attributes) | 0 |
| source_row_id distinct values | 1,000,000 |
| source_row_id contiguous 1..N | yes |
| Every row carries a posting_date, a title, a company_name and a location | yes |

No two rows are identical across all business attributes (0 exact duplicates), so no row is a redundant copy of another, and every row carries a complete set of posting-describing attributes. Nothing measured in this audit contradicts the posting-level grain.

**Absence of a natural posting ID**

| Composite tested | Attributes | Distinct combinations | Duplicate rows | % of rows | Unique key |
| --- | ---: | ---: | ---: | ---: | :---: |
| `company_name + posting_date` | 2 | 990,918 | 9,082 | 0.9082 | no |
| `company_name + posting_date + internship_title` | 3 | 998,936 | 1,064 | 0.1064 | no |
| `company_name + posting_date + internship_title + location` | 4 | 999,869 | 131 | 0.0131 | no |
| `company_name + posting_date + internship_title + location + industry + employment_type + work_mode` | 7 | 999,999 | 1 | 0.0001 | no |

**There is no natural posting identifier in this dataset, and no composite of business attributes is unique.** Even the widest composite tested (`company_name + posting_date + internship_title + location + industry + employment_type + work_mode`) still produces duplicates: 1 of 1,000,000 rows (0.0001%). A row therefore cannot be addressed by its business content alone.

**The role of `source_row_id`**

`source_row_id` is a staging-derived **lineage handle only**. It is the position of the row in the original extract, meaningful only together with that file's sha256. It is not a business key, not a posting ID, and not an ordering with analytic significance; the same value in a different extract refers to a different posting. It can therefore support traceability back to the source, but it cannot be used to decide whether two rows describe the same posting, and it must not be reused as a surrogate key in the warehouse without that decision being made explicitly.

**Unresolved concerns**

1. Without a posting ID, "one row = one posting" cannot be *proved*; it can only be shown to be un-contradicted. Two genuinely distinct postings and one posting loaded twice would look the same to every test available here.
2. Rows that collide on a business composite are where this matters most: the narrowest composite tested leaves 9,082 such rows and the widest leaves 1. The data cannot say which reading is right for any of them.
3. The company-identity problem in section 3 sits underneath this: if `company_name` does not identify a company, then "the same company posting twice" is not an observable event in this dataset.
4. The grain is therefore **not finalised here.** It is recorded as plausible and un-contradicted, pending the questions in section 11.

## 9. Modelling risks

| Risk | Evidence | Consequence |
| --- | --- | --- |
| Company identity | 62,274 of 63,946 repeated company_names carry more than one attribute combination | A DimCompany keyed on company_name would silently merge rows that may belong to different companies, or split one company across versions. Every company-level figure would inherit that ambiguity. |
| Dimension cardinality | 535,938 distinct company_name values over 1,000,000 rows | A dimension holding roughly half as many rows as the fact table gives up most of the storage and join benefit of a star schema. |
| Non-monotonic time behaviour | company_age decreases in 222,140 pairs; domain_age_months in 229,908 | SCD Type 2 assumes attribute changes are a history. Here the changes do not form a history, so versioning them would encode noise as fact. |
| Redundant attribute pairs | recruiter_email_type <-> suspicious_email_domain bijection; payment_required == (registration_fee > 0) | Storing both members of a pair lets two query paths produce the same number by different routes, and lets a future load break the invariant without any query noticing. |
| Undocumented units | stipend has no documented currency or pay period; registration_fee has no documented currency | Any monetary aggregate across the nine cities sums different units. The result is presentable and wrong, which is the dangerous combination. |
| Outcome leakage | is_fake_posting and fraud_score are the analysis target, not independent descriptors | Placing either in a slicing dimension invites analyses that explain the outcome with itself. |
| Degenerate attribute | unrealistic_salary_flag is constant across all 1,000,000 rows | It would produce a one-member dimension that can never slice anything, while still costing a join. |
| Location semantics | location is one of 9 cities with no country or region column, and the source does not say what it locates | A geographic hierarchy cannot be built from this dataset alone, and any imported hierarchy imports an assumption with it. |

## 10. Deferred decisions

Every item below is deliberately left open by this audit. Each is a decision for the star-schema stage, and each needs a stated assumption rather than more measurement of this extract.

| # | Deferred decision | Why it is deferred |
| ---: | --- | --- |
| 1 | Whether a DimCompany exists at all, and what it is keyed on | Only 2.6147% of repeated company_names carry a single attribute combination; the data cannot distinguish a changing company from two companies sharing a name. |
| 2 | Whether company attributes need SCD treatment, and which type | SCD presupposes a stable business key, which has not been established. |
| 3 | Whether industry joins the Internship dimension or stands alone | No functional dependency in either direction; Cramer's V 0.001236. |
| 4 | Whether employment_type and work_mode become one dimension or two | Both are defensible: the grid is complete and neither determines the other. |
| 5 | Which of recruiter_email_type / suspicious_email_domain is stored | The bijection makes them redundant, but they are not interchangeable in meaning and a later extract could break it. |
| 6 | Whether payment_required is stored, derived, or both | The invariant holds on all 1,000,000 rows, so either choice is currently lossless. |
| 7 | Whether registration_fee is a fact measure or a dimension attribute | It is numeric and additive in form, but its currency is undocumented. |
| 8 | Whether stipend can be used at all | Currency and pay period are both undocumented; no aggregate is defensible until they are established. |
| 9 | Whether the trust and fraud flags become junk dimensions | Technically feasible at the observed combination counts, but is_fake_posting is an outcome and unrealistic_salary_flag is constant. |
| 10 | Whether unrealistic_salary_flag enters the warehouse | Constant on this extract, but a later extract could contain a value of 1; the cleaning rules keep it in staging for that reason. |
| 11 | Whether score fields stay numeric or are also banded | Banding creates dimension attributes but imposes thresholds the source does not document. |
| 12 | The final grain statement and its surrogate key | Posting-level grain is un-contradicted but unprovable without a posting ID; source_row_id is lineage only. |
| 13 | Whether is_future_posting rows are included in analytical queries | 30,246 rows are dated after the fixed reference date and are flagged, not filtered. |

## 11. Recommended questions to resolve before the final star schema

These questions cannot be answered by measuring this extract further. They need the source system, its documentation, or an explicit modelling assumption agreed and written down.

| # | Question | What it unblocks |
| ---: | --- | --- |
| 1 | Is there a company identifier in the source system that did not survive into this extract? | Everything about DimCompany: its existence, its key, its grain and whether SCD applies. |
| 2 | If not, may company_name be treated as a company key by explicit assumption, and is that assumption acceptable to the coursework? | A defensible DimCompany built on a stated assumption rather than on evidence the data does not provide. |
| 3 | What currency is stipend denominated in, and over what pay period? | Any use of stipend at all, and in particular any comparison across location. |
| 4 | What currency is registration_fee denominated in? | Whether registration_fee can be summed across locations as a fact measure. |
| 5 | Does location refer to the work location, the company location or the recruiter location? | Whether DimLocation can be conformed with any other dimension, and whether a geographic hierarchy may be imported. |
| 6 | How are the seven 0-100 scores computed, and is the scale comparable across rows and over time? | Whether averaging them is defensible, and whether banding them into dimension attributes is legitimate. |
| 7 | Is there a recruiter identifier in the source system? | Whether DimRecruiter can hold recruiter_experience_years and recruiter_response_time_hours instead of leaving them in the fact. |
| 8 | Is there a posting identifier in the source system? | A provable grain statement and a business-meaningful key for the fact table. |
| 9 | Why does company_age fall between later postings by the same company_name? | Whether company attributes are a genuine history worth versioning, or noise that must not be versioned. |
| 10 | Is the bijection between recruiter_email_type and suspicious_email_domain guaranteed by the source, or an accident of this extract? | Whether one of the two may safely be dropped from the model. |
| 11 | Is payment_required guaranteed by the source to equal registration_fee > 0, or is that an accident of this extract? | Whether the flag may be derived rather than stored. |
| 12 | Will unrealistic_salary_flag ever take a value other than 0 in a future extract? | Whether it is a degenerate column to exclude or a real flag to keep. |
| 13 | Should future-dated postings be included in, excluded from, or reported separately in analytical queries? | How the date dimension is bounded and how every time-series figure is read. |

---

*Generated by `scripts/audit_dimensional_consistency.py` on 2026-09-23 18:17:28 from 1,000,000 staging rows. Staging sha256 unchanged: yes. No data was modified.*
