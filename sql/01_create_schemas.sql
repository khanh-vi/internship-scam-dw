/* Run after 00_create_database.sql. */
USE [InternshipScamDW];
GO

IF SCHEMA_ID(N'stg') IS NULL
    EXEC(N'CREATE SCHEMA [stg] AUTHORIZATION [dbo];');
GO

IF SCHEMA_ID(N'dw') IS NULL
    EXEC(N'CREATE SCHEMA [dw] AUTHORIZATION [dbo];');
GO
