# SQL Server Deployment Preflight — InternshipScamDW

## Scope and conclusion

This is a static review of the actual SQL text in `sql/00_create_database.sql` through `sql/09_drop_all.sql`, reconciled with `docs/schema/`, `docs/physical/`, and `docs/data_dictionary.md`. No SQL Server connection was made and no CSV was read or modified.

**Final deployment readiness: READY**

- Blocking findings: **0**
- Important findings: **1**
- SQL files changed: **none**
- Basis: the clean-instance sequence `00` through `07` is internally executable on SQL Server 2019+, `08` is read-only, and `09` is a database-scoped reset that does not drop the database.

Only BLOCKING findings prevent `READY`. The one IMPORTANT finding is documentation drift and does not make the reviewed SQL sequence unsafe.

## Finding register

| ID | Severity | Finding | Evidence | Recommendation |
| --- | --- | --- | --- | --- |
| PF-01 | IMPORTANT | The logical-schema documents still describe the `DimDate` Unknown row as `FullDate = NULL`, while the approved physical design, task requirement, table definition, CHECK constraint, and seed use the non-null sentinel `1900-01-01`. The catalog also lists 3,287 v1 date rows without clearly distinguishing known rows from the 3,288 total rows after Unknown seeding. This does not block deployment because the physical artifacts agree with each other. | `docs/schema/star_schema_design_en.md:220,415`; `docs/schema/dimension_catalog.csv:2`; `docs/physical/physical_design_en.md:42-44`; `sql/03_create_dimensions.sql:9-17`; `sql/05_create_constraints.sql:34-49`; `sql/07_seed_unknown_members.sql:14-56` | Reconcile the logical-schema English/Vietnamese documents and dimension catalog in a documentation-only change: state `FullDate = 1900-01-01`, 3,287 known calendar rows, and 3,288 total rows including key 0. Do not change the SQL sentinel or weaken the constraints. |
| PF-02 | INFORMATIONAL | Object-creation scripts use conditional creation, but `05_create_constraints.sql` is intentionally one-time. An accidental rerun of `05` fails on existing PK/UQ/CHECK/FK objects. Conditional table scripts also do not repair or validate an existing object with the wrong shape. | `sql/02_create_staging.sql:8-48`; `sql/03_create_dimensions.sql:5-104`; `sql/04_create_fact.sql:5-40`; `sql/05_create_constraints.sql:9-133` | For a complete redeployment, run the reviewed reset and then `00`–`07`. After a partial failure in `05`, inspect/reset rather than assuming that rerunning every script will self-heal. A blanket idempotency rewrite is not required for this coursework deployment. |
| PF-03 | INFORMATIONAL | The practical minimum is SQL Server 2019 because script `00` sets compatibility level 150. The executing principal also needs database/schema/table/constraint/index permissions. | `sql/00_create_database.sql:3,9-18`; `sql/06_create_indexes.sql:19-21`; `sql/09_drop_all.sql:9-29` | Deploy on SQL Server 2019 or later with the stated permissions. `DROP TABLE IF EXISTS` and columnstore support alone have older minimums, but compatibility level 150 makes 2019 the effective floor. |

## 1. Execution order and object dependencies

The required clean deployment order is valid:

| Script | Creates/acts on | Prerequisites | Result |
| --- | --- | --- | --- |
| `00_create_database.sql` | Database `InternshipScamDW`; compatibility 150 | `master`; create/alter database permission | PASS |
| `01_create_schemas.sql` | `stg`, `dw` | Database from `00` | PASS |
| `02_create_staging.sql` | `stg.InternshipPosting` | `stg` schema | PASS |
| `03_create_dimensions.sql` | 9 Dimension tables | `dw` schema | PASS |
| `04_create_fact.sql` | `dw.FactInternshipPosting` | `dw` schema; Dimensions are already present for later FKs | PASS |
| `05_create_constraints.sql` | 11 PKs, 10 unique constraints, 34 CHECKs, 9 FKs | All staging, Dimension, and Fact tables | PASS |
| `06_create_indexes.sql` | One clustered columnstore index on the Fact | Fact exists; its PK and SourceRowID uniqueness are nonclustered | PASS |
| `07_seed_unknown_members.sql` | 9 key-0 Unknown members and 3,287 normal dates | Dimension constraints exist | PASS |
| `08_validation_queries.sql` | SELECT-only validation result sets | Deployed objects; meaningful comparisons after ETL | PASS, validation-only |
| `09_drop_all.sql` | Drops project tables and then empty project schemas | Database must exist | PASS, reset-only |

No project object is referenced before creation in `00`–`07`. `08` is not part of object creation, and `09` is not part of normal deployment/load.

## 2. Database and schema context

- `00` deliberately begins in `[master]` to create the database, then switches to `[InternshipScamDW]` in a separate batch.
- Every script `01`–`09` begins with `USE [InternshipScamDW]; GO`. A later script therefore does not inherit `master` or an arbitrary caller database.
- `stg` and `dw` are conditionally created before any tables.
- All project tables, FK references, index targets, and DML targets are explicitly qualified with `[stg]` or `[dw]`.
- System catalog references (`sys.indexes`, `sys.objects`, `sys.all_objects`) are intentionally in the active `InternshipScamDW` context.

**Database context status: PASS.**

## 3. Staging table audit

Mechanical comparison found **35 mapping rows, 35 SQL staging columns, 0 missing, and 0 extra**. The table contains the 33 source columns plus derived `source_row_id` and `is_future_posting`.

- Names and order match the approved staging contract.
- SQL Server implementation types match the physical design: appropriately sized `NVARCHAR`, `DATE`, `SMALLINT`, `INT`, and fixed-precision `DECIMAL`.
- The three nullable source fields are correct: `company_age SMALLINT NULL`, `stipend INT NULL`, and `trust_signal_score DECIMAL(4,1) NULL`.
- No default silently converts any nullable value to 0.
- The staging CHECKs are limited to documented 0/1 flags and 0–100 scores. There is no check on currency, payment period, company age versus domain age, or other invented business semantics.
- `source_row_id` is the clustered staging PK, consistent with unique row lineage in the approved current extract.

**Staging column status: PASS — exactly 35/35 approved columns.**

## 4. Dimension PK, IDENTITY, natural keys, and Unknown members

| Dimension | Surrogate PK | IDENTITY | Approved uniqueness | Key-0 seed |
| --- | --- | ---: | --- | ---: |
| `DimDate` | `DateKey INT` | No; YYYYMMDD/key 0 is explicit | `FullDate` unique | Yes |
| `DimCompanyName` | `CompanyNameKey INT` | Yes | `CompanyName` | Yes |
| `DimCompanyProfile` | `CompanyProfileKey INT` | Yes | Five-attribute profile | Yes |
| `DimInternshipTitle` | `InternshipTitleKey INT` | Yes | `InternshipTitle` | Yes |
| `DimIndustry` | `IndustryKey INT` | Yes | `Industry` | Yes |
| `DimLocation` | `LocationKey INT` | Yes | `Location` | Yes |
| `DimEmploymentType` | `EmploymentTypeKey INT` | Yes | `EmploymentType` | Yes |
| `DimWorkMode` | `WorkModeKey INT` | Yes | `WorkMode` | Yes |
| `DimRecruiterEmail` | `RecruiterEmailKey INT` | Yes | Email-type/binary pair | Yes |

There are **9 Dimension PKs**. The 8 generated surrogate keys are `INT IDENTITY(1,1)`; `DimDate.DateKey` is intentionally explicit. Script `07` has **8 `IDENTITY_INSERT ON` and 8 matching `OFF` statements**, paired table by table within the transaction.

All Unknown rows satisfy `NOT NULL`, uniqueness, and CHECK constraints:

- `DimCompanyProfile` uses `CompanySize = N'Unknown'` and four binary values of `0`. `0` is within every `IN (0,1)` constraint; the `Unknown` size keeps the composite natural key separate from the 64 observed profiles.
- `DimRecruiterEmail` uses `RecruiterEmailType = N'Unknown'` and `SuspiciousEmailDomain = 0`. This satisfies `NOT NULL` and `IN (0,1)` and is distinct from the two observed email profiles.
- No dimension attempts to use `-1`, `NULL`, or another out-of-domain binary sentinel.

**Dimension PK status: PASS. Unknown-member status: PASS; no blocking Unknown/binary conflict.**

## 5. DimDate Unknown and calendar

- The Unknown row is exactly `DateKey = 0`, `FullDate = 1900-01-01`, text `Unknown`, and numeric calendar parts 0.
- `CK_DimDate_CalendarParts` has an explicit Unknown branch and a separate normal-date branch.
- The unique `FullDate` constraint accepts the sentinel once.
- Normal generation is explicitly bounded from `2018-01-01` through `2026-12-31` and therefore never generates `1900-01-01`.
- The inclusive normal range is **3,287 dates**; after the Unknown row the seeded dimension has **3,288 total rows** on an otherwise empty table.
- The seed checks `FullDate` before adding each normal date, so rerunning does not duplicate the calendar.

**DimDate status: PASS.** The documentation drift is PF-01, not a SQL conflict.

## 6. Fact physical design, indexes, and idempotency

`dw.FactInternshipPosting` has the approved combination:

- `FactPostingKey BIGINT IDENTITY(1,1) NOT NULL`.
- `PK_FactInternshipPosting` is explicitly **NONCLUSTERED**.
- `UQ_FactInternshipPosting_SourceRowID` is one **UNIQUE NONCLUSTERED** constraint.
- `CCI_FactInternshipPosting` is created exactly once as the only clustered structure.
- No clustered rowstore Fact PK is created before the CCI.
- No one-index-per-FK set or duplicate Fact index is present.
- Constraint-backed Dimension natural-key indexes provide the required lookup access.

The `INT` `SourceRowID` uniqueness is compatible with 1,000,000 rows and with the SQL Server 2019 clustered columnstore design. Documentation consistently describes it as a single-source lineage/idempotency handle, not a business key. Duplicate source rows fail rather than silently loading twice.

**Fact/CCI compatibility status: PASS. Source-row idempotency status: PASS.**

## 7. Fact foreign-key audit

All **9 expected FKs** exist; every Fact column and referenced Dimension column is `INT NOT NULL`, and every target is a Dimension PK:

| Fact column | Referenced key | Type match | FK name unique |
| --- | --- | --- | --- |
| `DateKey` | `DimDate.DateKey` | Yes | Yes |
| `CompanyNameKey` | `DimCompanyName.CompanyNameKey` | Yes | Yes |
| `CompanyProfileKey` | `DimCompanyProfile.CompanyProfileKey` | Yes | Yes |
| `InternshipTitleKey` | `DimInternshipTitle.InternshipTitleKey` | Yes | Yes |
| `IndustryKey` | `DimIndustry.IndustryKey` | Yes | Yes |
| `LocationKey` | `DimLocation.LocationKey` | Yes | Yes |
| `EmploymentTypeKey` | `DimEmploymentType.EmploymentTypeKey` | Yes | Yes |
| `WorkModeKey` | `DimWorkMode.WorkModeKey` | Yes | Yes |
| `RecruiterEmailKey` | `DimRecruiterEmail.RecruiterEmailKey` | Yes | Yes |

The FKs are added with `WITH CHECK`; on a clean empty Fact they become checked/trusted constraints. There are no cascades.

**FK status: PASS — 9/9.**

## 8. CHECK constraint audit

There are exactly **34 CHECK constraints**, all with unique names:

| Scope | Binary | Score | Calendar | Total |
| --- | ---: | ---: | ---: | ---: |
| Staging | 10 | 7 | 0 | 17 |
| Dimensions | 5 | 0 | 1 | 6 |
| Fact | 4 | 7 | 0 | 11 |
| **Total** | **19** | **14** | **1** | **34** |

- Every binary rule uses `IN (0,1)`.
- Every bounded score rule uses `BETWEEN 0 AND 100`.
- `trust_signal_score` / `TrustSignalScore` remains nullable. In SQL Server a CHECK rejects only `FALSE`; the predicate evaluates `UNKNOWN` for NULL, so approved NULLs pass without weakening the 0–100 rule for non-null values.
- No unsupported CHECK exists for stipend currency, registration-fee currency, payment period, or company age versus domain age.

**CHECK constraint status: PASS — 34/34.**

## 9. Null and monetary semantics

- Staging and Fact both preserve NULL for `company_age`/`CompanyAge`, `stipend`/`Stipend`, and `trust_signal_score`/`TrustSignalScore`.
- There are no defaults on those fields and no seed/load statement that imputes 0.
- The reviewed SQL does not convert or annualize stipend, add a currency, infer a payment period, convert registration fee, or infer any relationship between company age and domain age.

**Null semantics: PASS. Monetary semantics: PASS (intentionally unresolved).**

## 10. Validation script

`08_validation_queries.sql` contains `USE`, `SET NOCOUNT`, `SELECT`, CTE-free derived queries, joins, aggregations, and `GO`. It contains no `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `DROP`, or data/schema `ALTER` operation.

The literals for 1,000,000 rows, Dimension counts, 30,246 future rows, and 221,958 fake rows are output columns for comparison only. They are not constraints, DDL assumptions, or filters that mutate results.

**Validation-script read-only status: PASS.**

## 11. Drop/reset script

- Drops the Fact first, removing all FK dependencies.
- Drops Dimensions next, staging last, then drops `dw` and `stg` only if each schema has no remaining objects.
- Uses `USE [InternshipScamDW]`, so it is scoped to the intended database.
- Does not contain `DROP DATABASE`, server-level DDL, dynamic object discovery/deletion, or CSV/file operations.
- If unrelated objects exist inside `dw` or `stg`, the schema emptiness check preserves the schema; the script only drops the explicitly named coursework tables.

**Drop-script safety status: PASS. No database drop exists.**

## 12. Rerun behavior

| Script | Classification | Accidental rerun behavior |
| --- | --- | --- |
| `00` | Conditional create; safe to rerun | Database create is skipped; compatibility 150 is reasserted. |
| `01` | Conditional create; safe to rerun | Existing schemas are skipped. |
| `02` | Conditional create; safe no-op for an existing table | Does not verify or repair an incorrect existing shape. |
| `03` | Conditional create; safe no-op per existing Dimension | Does not repair partial/incorrect definitions. |
| `04` | Conditional create; safe no-op for an existing Fact | Does not repair an incorrect existing definition. |
| `05` | Intentionally one-time; requires unconstrained created tables | Rerun fails on already existing constraints/indexes, normally at the first PK. |
| `06` | Conditional by CCI name; safe in the approved deployment | Same named CCI is skipped; a differently named clustered structure would cause SQL Server to reject a second clustered structure. |
| `07` | Reference seed designed to rerun | Key-0 and calendar inserts are guarded; all IDENTITY_INSERT pairs are balanced on normal execution. |
| `08` | Read-only and rerunnable | Returns current state; pre-ETL values simply differ from expectations. |
| `09` | Destructive reset; rerunnable while the database exists | Named objects are conditionally dropped; it never drops the database. |

## 13. SQL Server version assumption

The effective minimum is **Microsoft SQL Server 2019**:

- compatibility level `150` is explicitly set;
- clustered columnstore and nonclustered rowstore constraint indexes are used together;
- `DROP TABLE IF EXISTS` is used by reset;
- `COMPRESSION_DELAY` is specified on the CCI;
- no `CREATE OR ALTER` or newer string function is used.

`GO` is a client batch separator, so deployment must use a SQL Server-aware client such as SSMS, Azure Data Studio, or sqlcmd rather than sending each file as one unparsed API batch.

## Final status block

| Required result | Status |
| --- | --- |
| Readiness status | **READY** |
| Blocking issue count | **0** |
| Important issue count | **1** |
| Database context status | **PASS** |
| Staging column status | **PASS — 35/35** |
| Dimension PK status | **PASS — 9/9** |
| Unknown-member status | **PASS — 9/9; no binary conflict** |
| Fact/CCI compatibility status | **PASS** |
| FK status | **PASS — 9/9** |
| CHECK constraint status | **PASS — 34/34** |
| Validation-script read-only status | **PASS** |
| Drop-script safety status | **PASS; no database drop** |
| Files changed | `results/sql_preflight/sql_preflight_en.md`; `results/sql_preflight/sql_preflight_vi.md` |
| SQL/CSV changes | **None** |
