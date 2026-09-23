# Load Order — InternshipScamDW

## Scope

This is the approved logical load order for Star Schema v1. It describes a future ETL process; the current deliverable creates SQL objects and reference members only and does not load the staging CSV.

## Prerequisite script order

Run `sql/00_create_database.sql` through `sql/08_validation_queries.sql` in numeric order. `07_seed_unknown_members.sql` creates the key-0 Dimension members and the continuous 2018-01-01 through 2026-12-31 calendar before any posting Fact load. `09_drop_all.sql` is a separate, destructive reset and is never part of a normal load.

## Logical data load order

| Step | Target | Reason |
| ---: | --- | --- |
| 1 | `stg.InternshipPosting` | Land all 35 source-aligned columns and validate source types/domains. |
| 2 | `dw.DimDate` | Seed Unknown and the full calendar before date lookup. |
| 3 | `dw.DimCompanyName` | Insert distinct observed company-name strings; do not perform entity resolution. |
| 4 | `dw.DimCompanyProfile` | Insert distinct five-attribute profile combinations; do not hard-code 64. |
| 5 | `dw.DimInternshipTitle` | Insert distinct title values. |
| 6 | `dw.DimIndustry` | Insert distinct industry values. |
| 7 | `dw.DimLocation` | Insert distinct location values without inferred geography/currency. |
| 8 | `dw.DimEmploymentType` | Insert distinct employment-type values. |
| 9 | `dw.DimWorkMode` | Insert distinct work-mode values. |
| 10 | `dw.DimRecruiterEmail` | Insert distinct `(RecruiterEmailType, SuspiciousEmailDomain)` combinations. |
| 11 | `dw.FactInternshipPosting` | Resolve all nine keys and insert measures, lineage, and quality flag. |

Fact loads last because each nonzero foreign key must resolve to a previously loaded Dimension row. A genuinely missing/unresolved Dimension attribute uses the existing key-0 member; a valid value must not be sent to Unknown. Checked foreign keys reject orphan rows.

## ETL lookup flow

```text
staging row
  -> Date lookup (posting_date -> DateKey)
  -> CompanyName lookup (company_name -> CompanyNameKey)
  -> CompanyProfile lookup (company_size + four flags -> CompanyProfileKey)
  -> InternshipTitle lookup
  -> Industry lookup
  -> Location lookup
  -> EmploymentType lookup
  -> WorkMode lookup
  -> RecruiterEmail lookup (email type + suspicious-domain flag)
  -> Fact insert
```

The Fact insert copies approved measures without imputation or re-scaling, maps `is_fake_posting` to `FakePostingCount`, carries `SourceRowID` and `IsFuturePosting`, and omits `unrealistic_salary_flag`. `PostingCount` is later obtained with `COUNT_BIG(*)`; `FakePostingRate` is `SUM(FakePostingCount) / COUNT_BIG(*)`.

## Idempotency and failure handling

The current single-source load must treat `SourceRowID` as an idempotency key. `UQ_FactInternshipPosting_SourceRowID` makes an accidental repeat fail instead of silently duplicating rows. ETL should run Dimension upserts and the Fact batch in controlled transactions, report lookup/data-quality failures, and never “repair” source values silently. A future second source requires `(SourceSystemKey, SourceRowID)` and a reviewed schema revision.

## Post-load validation

Run `sql/08_validation_queries.sql`. The first full load expects 1,000,000 staging rows and 1,000,000 Fact rows, zero orphans, zero duplicate `SourceRowID` values, zero binary/score violations, 30,246 future-posting rows, and 221,958 labelled-fake rows. Known current-extract Dimension counts are comparisons in the script, not table constraints.
