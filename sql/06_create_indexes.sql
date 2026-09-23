/*
  OLAP storage index. Constraint-backed indexes already provide:
  - clustered rowstore PKs on staging and dimensions;
  - unique natural-key lookup indexes on dimensions;
  - nonclustered FactPostingKey PK and SourceRowID idempotency/lineage indexes.
  No redundant index-per-FK set is created.
*/
USE [InternshipScamDW];
GO

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE [object_id] = OBJECT_ID(N'dw.FactInternshipPosting')
      AND [name] = N'CCI_FactInternshipPosting'
)
BEGIN
    CREATE CLUSTERED COLUMNSTORE INDEX [CCI_FactInternshipPosting]
        ON [dw].[FactInternshipPosting]
        WITH (COMPRESSION_DELAY = 0);
END;
GO
