# Internship Scam Data Warehouse & OLAP

Data Warehouse & OLAP coursework project using an Internship Scam Detection dataset.

## Project Structure

- `data/` - local raw/staging datasets (not committed)
- `scripts/` - profiling, auditing, staging and verification scripts
- `docs/` - bilingual project documentation
- `results/` - profiling and audit outputs
- `notebooks/` - exploratory notebooks
- `sql/` - SQL Server physical design and ETL scripts

## Current Progress

- [x] Data profiling
- [x] Data quality audit
- [x] Data dictionary
- [x] Cleaning rules
- [x] Staging layer
- [x] Dimensional consistency audit
- [x] Star Schema v1
- [ ] SQL Server physical design
- [ ] ETL / SSIS
- [ ] SSAS / OLAP

## Dataset

The original dataset is not included in this repository because of file size and data-management considerations.

Source:
Kaggle - Internship Scam Detection Dataset

## Star Schema

The current logical model consists of:

- 1 Fact table: `FactInternshipPosting`
- 9 Dimensions

See:

`docs/schema/star_schema_design_en.md`

and:

`docs/schema/star_schema_design_vi.md`