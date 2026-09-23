/*
  InternshipScamDW - database creation
  Target: Microsoft SQL Server 2019 or later (compatibility level 150+).
  Safe to rerun: the database is created only when absent.
*/
USE [master];
GO

IF DB_ID(N'InternshipScamDW') IS NULL
BEGIN
    EXEC(N'CREATE DATABASE [InternshipScamDW];');
END;
GO

ALTER DATABASE [InternshipScamDW] SET COMPATIBILITY_LEVEL = 150;
GO

USE [InternshipScamDW];
GO
