/*
  DESTRUCTIVE RESET FOR InternshipScamDW ONLY.
  Drops coursework tables and then the stg/dw schemas. It does NOT drop the
  database, any CSV file, the SQL Server instance, or unrelated objects.
*/
USE [InternshipScamDW];
GO

DROP TABLE IF EXISTS [dw].[FactInternshipPosting];
GO

DROP TABLE IF EXISTS [dw].[DimRecruiterEmail];
DROP TABLE IF EXISTS [dw].[DimWorkMode];
DROP TABLE IF EXISTS [dw].[DimEmploymentType];
DROP TABLE IF EXISTS [dw].[DimLocation];
DROP TABLE IF EXISTS [dw].[DimIndustry];
DROP TABLE IF EXISTS [dw].[DimInternshipTitle];
DROP TABLE IF EXISTS [dw].[DimCompanyProfile];
DROP TABLE IF EXISTS [dw].[DimCompanyName];
DROP TABLE IF EXISTS [dw].[DimDate];
GO

DROP TABLE IF EXISTS [stg].[InternshipPosting];
GO

IF SCHEMA_ID(N'dw') IS NOT NULL AND NOT EXISTS (SELECT 1 FROM sys.objects WHERE [schema_id] = SCHEMA_ID(N'dw'))
    EXEC(N'DROP SCHEMA [dw];');
IF SCHEMA_ID(N'stg') IS NOT NULL AND NOT EXISTS (SELECT 1 FROM sys.objects WHERE [schema_id] = SCHEMA_ID(N'stg'))
    EXEC(N'DROP SCHEMA [stg];');
GO
