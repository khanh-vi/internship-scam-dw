# SQL Server Physical Design — Star Schema v1

## 1. Scope

This document specifies the physical SQL Server implementation of the approved posting-record grain. It creates scripts only: no raw or staging file is changed, no posting data is loaded, and no SSIS package is built. The database is `InternshipScamDW`; analytical objects use `dw`, and the source-aligned landing table uses `stg`.

## 2. Logical-to-physical mapping

The model remains one Fact and nine Dimensions. Each `FactInternshipPosting` row is one observed source record, not necessarily one unique real-world posting. All 35 staging columns are retained. The only analytical exclusion is `unrealistic_salary_flag`, which stays in staging but has constant value zero and therefore no analytical variance.

`is_fake_posting` maps exactly to stored `FakePostingCount`. Its sum counts labelled-fake records. `PostingCount` is not stored because `COUNT_BIG(*)` is exactly equivalent at this grain. `FakePostingRate` is not stored and is calculated as `SUM(FakePostingCount) / COUNT_BIG(*)` with a zero-denominator guard.

Physical date attribute names follow the requested contract: logical `Day`, `Month`, `Quarter`, and `Year` become `DayOfMonth`, `MonthNumber`, `QuarterNumber`, and `YearNumber`.

## 3. Schema organization

| Schema | Object role |
| --- | --- |
| `stg` | Source-aligned `InternshipPosting` with 35 columns and no analytical reshaping |
| `dw` | Nine Dimensions and `FactInternshipPosting` |

`dbo` owns the schemas but contains no analytical table.

## 4. Datatype choices

SQL Server native `DATE`, integer, and fixed precision `DECIMAL` types preserve the documented domains. Nullable source measures remain nullable. The Fact surrogate key is `BIGINT`; source lineage and Dimension keys are `INT`. Staging flags remain `SMALLINT` as documented, while bounded 0/1 and 0–100 analytical columns use `TINYINT`.

All text is `NVARCHAR` for future Unicode compatibility. Lengths retain the approved capacities: 16/24/32/64 as applicable, with 64 characters for a measured company-name maximum of 38. `NVARCHAR(MAX)` is not used. This changes storage encoding, not source values or semantics.

## 5. Primary-key strategy

Dimension surrogate keys are `INT`; all except `DimDate` use `IDENTITY(1,1)`. `DateKey` uses `YYYYMMDD`. `FactPostingKey` is `BIGINT IDENTITY(1,1)` and a nonclustered primary key so the Fact can use a clustered columnstore index. `stg.InternshipPosting.source_row_id` is its clustered primary key.

Natural attributes or approved attribute combinations have unique constraints. `DimCompanyName.CompanyName` uniqueness is string uniqueness under the database collation; it does not assert that identical strings are a verified company entity.

## 6. Foreign-key strategy

The Fact has nine checked, trusted foreign keys, one to every Dimension. Dimensions must load before the Fact. No cascading delete or update is enabled. A failed lookup is assigned key 0 by the future ETL; valid source values must never be mapped to Unknown.

## 7. Unknown members

Every Dimension reserves surrogate key 0. Text members use `Unknown`. Profile and email flags use 0 only as part of their technical Unknown row. `DimDate` uses `DateKey = 0`, text `Unknown`, numeric attributes 0, and `FullDate = 1900-01-01` because `FullDate` is required and unique. That date is a technical sentinel outside the supported business calendar and must not be interpreted as an observed posting date.

The calendar is generated continuously from 2018-01-01 through 2026-12-31 (3,287 known dates), rather than harvested from observations. With the Unknown member, `DimDate` contains 3,288 rows after reference seeding. `IDENTITY_INSERT` is enabled only around each key-0 insert.

## 8. Constraints

There are 34 named `CHECK` constraints: 17 on staging (10 binary and 7 score checks), 6 on Dimensions (one calendar rule and five binary checks), and 11 on the Fact (4 binary and 7 score checks). Binary values are restricted to `{0,1}` and scores to 0–100. Nullable `TrustSignalScore` remains valid when NULL because SQL Server `CHECK` permits UNKNOWN.

No speculative currency, annualization, stipend, registration-fee, or company/domain-age relationship constraint is added. The 64 observed company-profile combinations are not hard-coded.

## 9. Index strategy

| Index source | Physical index | Purpose |
| --- | --- | --- |
| Dimension PK constraints | Clustered rowstore indexes | Compact surrogate-key joins |
| Dimension unique constraints | Nonclustered unique indexes | ETL natural-key lookup and duplicate prevention |
| Fact PK constraint | Nonclustered unique index on `FactPostingKey` | Stable row handle without consuming clustered storage |
| Fact lineage constraint | Nonclustered unique index on `SourceRowID` | Single-source idempotency and traceability |
| `06_create_indexes.sql` | `CCI_FactInternshipPosting` | Compressed scan-oriented OLAP storage |

No index is created blindly for every Fact FK. Columnstore scans and hash joins suit the expected analytical workload; redundant rowstore indexes would increase load and storage cost. Workload evidence may justify selective rowstore indexes later.

## 10. Columnstore decision

Star Schema v1 uses a clustered columnstore index on `FactInternshipPosting`. Approximately 1,000,000 rows are enough to benefit from column elimination, batch-mode scans, and compression, while the workload is aggregation-heavy and is expected to use bulk/batch loads. The nonclustered PK and unique lineage index remain supported alongside the columnstore on SQL Server 2019+.

The alternative is a clustered rowstore PK on `FactPostingKey`, which is simpler and can be preferable for small, singleton-write or lookup-heavy workloads. It is not selected because this project is an OLAP warehouse. Loads should be set-based and preferably occur in batches large enough to form compressed rowgroups; frequent tiny inserts can leave delta-store rows and reduce the benefit.

## 11. Fact idempotency and lineage

`UQ_FactInternshipPosting_SourceRowID` prevents the same staging record from being inserted twice in the current single-source design. `SourceRowID` is an ETL lineage handle, not a business identifier and not proof of a unique real posting. Multi-source ingestion will require replacing this uniqueness scope with `(SourceSystemKey, SourceRowID)`; `SourceSystemKey` is deliberately not implemented in v1.

## 12. Monetary-field limitations

`Stipend INT NULL` preserves the source number without imputation, currency conversion, normalization, or annualization. Both currency and pay period are unresolved, so it is hidden from a validated default measure set and must not be aggregated across locations as though units were common.

`RegistrationFee INT NOT NULL` preserves the source numeric value, including zero as “no fee.” Its currency is unresolved. No currency-based `CHECK` constraint is present, and cross-location monetary aggregation is not validated.

## 13. Load sequence

Execute SQL files `00` through `08` in numeric order. The logical data order is staging, calendar, all other Dimensions, then Fact. Each staging row is looked up by date, company-name string, company-profile combination, title, industry, location, employment type, work mode, and recruiter-email combination before its Fact insert. Fact loads last because all nonzero keys must already exist and every FK is checked. See `load_order_en.md`.

## 14. Deferred physical decisions

- Source-system scoping for lineage when a second source arrives.
- Stipend currency and pay period, and registration-fee currency.
- Any selective rowstore Fact indexes, partitioning, or columnstore ordering after real query/load evidence.
- Production filegroups, compression maintenance, backup/recovery, security roles, and SQL Agent/SSIS orchestration.
- An explicit production collation if the deployment default is not acceptable. Natural-key uniqueness currently follows the database collation.

## 15. SQL Server assumptions and caveats

Scripts target SQL Server 2019 or later and set compatibility level 150. They use `GO`, `CREATE CLUSTERED COLUMNSTORE INDEX`, `DROP TABLE IF EXISTS`, and nonclustered constraint indexes on a columnstore table. The executing principal needs permission to create a database, schemas, tables, constraints, and indexes. `07_seed_unknown_members.sql` sets `us_english` while generating English day and month names. No live SQL Server execution is part of this deliverable.

## 16. Complete physical column matrix

`—` means no default. `IDENTITY` is generation metadata, not a default constraint.

| Table | Column | SQL Server datatype | Nullable | PK/FK | Default | Constraint | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `stg.InternshipPosting` | `posting_date` | `DATE` | No | — | — | — | `posting_date` |
| `stg.InternshipPosting` | `internship_title` | `NVARCHAR(32)` | No | — | — | — | `internship_title` |
| `stg.InternshipPosting` | `employment_type` | `NVARCHAR(16)` | No | — | — | — | `employment_type` |
| `stg.InternshipPosting` | `work_mode` | `NVARCHAR(16)` | No | — | — | — | `work_mode` |
| `stg.InternshipPosting` | `industry` | `NVARCHAR(24)` | No | — | — | — | `industry` |
| `stg.InternshipPosting` | `location` | `NVARCHAR(24)` | No | — | — | — | `location` |
| `stg.InternshipPosting` | `company_name` | `NVARCHAR(64)` | No | — | — | — | `company_name` |
| `stg.InternshipPosting` | `company_size` | `NVARCHAR(16)` | No | — | — | — | `company_size` |
| `stg.InternshipPosting` | `company_age` | `SMALLINT` | Yes | — | — | — | `company_age` |
| `stg.InternshipPosting` | `linkedin_presence` | `SMALLINT` | No | — | — | 0/1 | `linkedin_presence` |
| `stg.InternshipPosting` | `website_available` | `SMALLINT` | No | — | — | 0/1 | `website_available` |
| `stg.InternshipPosting` | `domain_age_months` | `SMALLINT` | No | — | — | — | `domain_age_months` |
| `stg.InternshipPosting` | `verification_status` | `SMALLINT` | No | — | — | 0/1 | `verification_status` |
| `stg.InternshipPosting` | `stipend` | `INT` | Yes | — | — | — | `stipend` |
| `stg.InternshipPosting` | `unrealistic_salary_flag` | `SMALLINT` | No | — | — | 0/1 | `unrealistic_salary_flag` |
| `stg.InternshipPosting` | `payment_required` | `SMALLINT` | No | — | — | 0/1 | `payment_required` |
| `stg.InternshipPosting` | `registration_fee` | `INT` | No | — | — | — | `registration_fee` |
| `stg.InternshipPosting` | `job_description_length` | `SMALLINT` | No | — | — | — | `job_description_length` |
| `stg.InternshipPosting` | `grammatical_errors` | `SMALLINT` | No | — | — | — | `grammatical_errors` |
| `stg.InternshipPosting` | `vague_description_score` | `SMALLINT` | No | — | — | 0–100 | `vague_description_score` |
| `stg.InternshipPosting` | `urgency_score` | `SMALLINT` | No | — | — | 0–100 | `urgency_score` |
| `stg.InternshipPosting` | `keyword_spam_score` | `SMALLINT` | No | — | — | 0–100 | `keyword_spam_score` |
| `stg.InternshipPosting` | `fake_certificate_offer` | `SMALLINT` | No | — | — | 0/1 | `fake_certificate_offer` |
| `stg.InternshipPosting` | `recruiter_experience_years` | `DECIMAL(3,1)` | No | — | — | — | `recruiter_experience_years` |
| `stg.InternshipPosting` | `recruiter_email_type` | `NVARCHAR(16)` | No | — | — | — | `recruiter_email_type` |
| `stg.InternshipPosting` | `suspicious_email_domain` | `SMALLINT` | No | — | — | 0/1 | `suspicious_email_domain` |
| `stg.InternshipPosting` | `recruiter_response_time_hours` | `DECIMAL(3,1)` | No | — | — | — | `recruiter_response_time_hours` |
| `stg.InternshipPosting` | `social_media_presence` | `SMALLINT` | No | — | — | 0/1 | `social_media_presence` |
| `stg.InternshipPosting` | `emotional_manipulation_score` | `SMALLINT` | No | — | — | 0–100 | `emotional_manipulation_score` |
| `stg.InternshipPosting` | `phishing_language_score` | `SMALLINT` | No | — | — | 0–100 | `phishing_language_score` |
| `stg.InternshipPosting` | `trust_signal_score` | `DECIMAL(4,1)` | Yes | — | — | 0–100 | `trust_signal_score` |
| `stg.InternshipPosting` | `fraud_score` | `DECIMAL(4,1)` | No | — | — | 0–100 | `fraud_score` |
| `stg.InternshipPosting` | `is_fake_posting` | `SMALLINT` | No | — | — | 0/1 | `is_fake_posting` |
| `stg.InternshipPosting` | `source_row_id` | `INT` | No | PK | — | Unique | staging-derived lineage |
| `stg.InternshipPosting` | `is_future_posting` | `SMALLINT` | No | — | — | 0/1 | staging-derived vs 2026-09-23 |
| `dw.DimDate` | `DateKey` | `INT` | No | PK | — | 0 or YYYYMMDD | generated calendar |
| `dw.DimDate` | `FullDate` | `DATE` | No | — | — | Unique | generated calendar |
| `dw.DimDate` | `DayOfMonth` | `TINYINT` | No | — | — | calendar rule | `FullDate` |
| `dw.DimDate` | `DayOfWeek` | `TINYINT` | No | — | — | 0 or 1–7 | `FullDate`, Monday=1 |
| `dw.DimDate` | `DayName` | `NVARCHAR(10)` | No | — | — | — | `FullDate` (`us_english`) |
| `dw.DimDate` | `MonthNumber` | `TINYINT` | No | — | — | calendar rule | `FullDate` |
| `dw.DimDate` | `MonthName` | `NVARCHAR(10)` | No | — | — | — | `FullDate` (`us_english`) |
| `dw.DimDate` | `QuarterNumber` | `TINYINT` | No | — | — | calendar rule | `FullDate` |
| `dw.DimDate` | `YearNumber` | `SMALLINT` | No | — | — | calendar rule | `FullDate` |
| `dw.DimCompanyName` | `CompanyNameKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimCompanyName` | `CompanyName` | `NVARCHAR(64)` | No | — | — | Unique | `company_name` |
| `dw.DimCompanyProfile` | `CompanyProfileKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimCompanyProfile` | `CompanySize` | `NVARCHAR(16)` | No | — | — | Composite unique | `company_size` |
| `dw.DimCompanyProfile` | `LinkedInPresence` | `TINYINT` | No | — | — | 0/1; composite unique | `linkedin_presence` |
| `dw.DimCompanyProfile` | `WebsiteAvailable` | `TINYINT` | No | — | — | 0/1; composite unique | `website_available` |
| `dw.DimCompanyProfile` | `VerificationStatus` | `TINYINT` | No | — | — | 0/1; composite unique | `verification_status` |
| `dw.DimCompanyProfile` | `SocialMediaPresence` | `TINYINT` | No | — | — | 0/1; composite unique | `social_media_presence` |
| `dw.DimInternshipTitle` | `InternshipTitleKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimInternshipTitle` | `InternshipTitle` | `NVARCHAR(32)` | No | — | — | Unique | `internship_title` |
| `dw.DimIndustry` | `IndustryKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimIndustry` | `Industry` | `NVARCHAR(24)` | No | — | — | Unique | `industry` |
| `dw.DimLocation` | `LocationKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimLocation` | `Location` | `NVARCHAR(24)` | No | — | — | Unique | `location` |
| `dw.DimEmploymentType` | `EmploymentTypeKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimEmploymentType` | `EmploymentType` | `NVARCHAR(16)` | No | — | — | Unique | `employment_type` |
| `dw.DimWorkMode` | `WorkModeKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimWorkMode` | `WorkMode` | `NVARCHAR(16)` | No | — | — | Unique | `work_mode` |
| `dw.DimRecruiterEmail` | `RecruiterEmailKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimRecruiterEmail` | `RecruiterEmailType` | `NVARCHAR(16)` | No | — | — | Composite unique | `recruiter_email_type` |
| `dw.DimRecruiterEmail` | `SuspiciousEmailDomain` | `TINYINT` | No | — | — | 0/1; composite unique | `suspicious_email_domain` |
| `dw.FactInternshipPosting` | `FactPostingKey` | `BIGINT IDENTITY(1,1)` | No | PK | IDENTITY | Unique | warehouse-generated |
| `dw.FactInternshipPosting` | `DateKey` | `INT` | No | FK | — | FK to `DimDate` | `posting_date` lookup |
| `dw.FactInternshipPosting` | `CompanyNameKey` | `INT` | No | FK | — | FK to `DimCompanyName` | `company_name` lookup |
| `dw.FactInternshipPosting` | `CompanyProfileKey` | `INT` | No | FK | — | FK to `DimCompanyProfile` | 5-column profile lookup |
| `dw.FactInternshipPosting` | `InternshipTitleKey` | `INT` | No | FK | — | FK to `DimInternshipTitle` | `internship_title` lookup |
| `dw.FactInternshipPosting` | `IndustryKey` | `INT` | No | FK | — | FK to `DimIndustry` | `industry` lookup |
| `dw.FactInternshipPosting` | `LocationKey` | `INT` | No | FK | — | FK to `DimLocation` | `location` lookup |
| `dw.FactInternshipPosting` | `EmploymentTypeKey` | `INT` | No | FK | — | FK to `DimEmploymentType` | `employment_type` lookup |
| `dw.FactInternshipPosting` | `WorkModeKey` | `INT` | No | FK | — | FK to `DimWorkMode` | `work_mode` lookup |
| `dw.FactInternshipPosting` | `RecruiterEmailKey` | `INT` | No | FK | — | FK to `DimRecruiterEmail` | 2-column email lookup |
| `dw.FactInternshipPosting` | `SourceRowID` | `INT` | No | — | — | Unique | `source_row_id` |
| `dw.FactInternshipPosting` | `IsFuturePosting` | `TINYINT` | No | — | — | 0/1 | `is_future_posting` |
| `dw.FactInternshipPosting` | `FakePostingCount` | `TINYINT` | No | — | — | 0/1 | `is_fake_posting` |
| `dw.FactInternshipPosting` | `PaymentRequired` | `TINYINT` | No | — | — | 0/1 | `payment_required` |
| `dw.FactInternshipPosting` | `FakeCertificateOffer` | `TINYINT` | No | — | — | 0/1 | `fake_certificate_offer` |
| `dw.FactInternshipPosting` | `CompanyAge` | `SMALLINT` | Yes | — | — | — | `company_age` |
| `dw.FactInternshipPosting` | `DomainAgeMonths` | `SMALLINT` | No | — | — | — | `domain_age_months` |
| `dw.FactInternshipPosting` | `Stipend` | `INT` | Yes | — | — | — | `stipend` |
| `dw.FactInternshipPosting` | `RegistrationFee` | `INT` | No | — | — | — | `registration_fee` |
| `dw.FactInternshipPosting` | `JobDescriptionLength` | `SMALLINT` | No | — | — | — | `job_description_length` |
| `dw.FactInternshipPosting` | `GrammaticalErrors` | `TINYINT` | No | — | — | — | `grammatical_errors` |
| `dw.FactInternshipPosting` | `VagueDescriptionScore` | `TINYINT` | No | — | — | 0–100 | `vague_description_score` |
| `dw.FactInternshipPosting` | `UrgencyScore` | `TINYINT` | No | — | — | 0–100 | `urgency_score` |
| `dw.FactInternshipPosting` | `KeywordSpamScore` | `TINYINT` | No | — | — | 0–100 | `keyword_spam_score` |
| `dw.FactInternshipPosting` | `EmotionalManipulationScore` | `TINYINT` | No | — | — | 0–100 | `emotional_manipulation_score` |
| `dw.FactInternshipPosting` | `PhishingLanguageScore` | `TINYINT` | No | — | — | 0–100 | `phishing_language_score` |
| `dw.FactInternshipPosting` | `TrustSignalScore` | `DECIMAL(4,1)` | Yes | — | — | 0–100 | `trust_signal_score` |
| `dw.FactInternshipPosting` | `FraudScore` | `DECIMAL(4,1)` | No | — | — | 0–100 | `fraud_score` |
| `dw.FactInternshipPosting` | `RecruiterExperienceYears` | `DECIMAL(3,1)` | No | — | — | — | `recruiter_experience_years` |
| `dw.FactInternshipPosting` | `RecruiterResponseTimeHours` | `DECIMAL(3,1)` | No | — | — | — | `recruiter_response_time_hours` |
