/* Creates empty Star Schema v1 dimension tables. */
USE [InternshipScamDW];
GO

IF OBJECT_ID(N'dw.DimDate', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[DimDate]
    (
        [DateKey]       INT           NOT NULL,
        [FullDate]      DATE          NOT NULL,
        [DayOfMonth]    TINYINT       NOT NULL,
        [DayOfWeek]     TINYINT       NOT NULL,
        [DayName]       NVARCHAR(10)  NOT NULL,
        [MonthNumber]   TINYINT       NOT NULL,
        [MonthName]     NVARCHAR(10)  NOT NULL,
        [QuarterNumber] TINYINT       NOT NULL,
        [YearNumber]    SMALLINT      NOT NULL
    );
END;
GO
IF OBJECT_ID(N'dw.DimCompanyName', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[DimCompanyName]
    (
        [CompanyNameKey] INT IDENTITY(1,1) NOT NULL,
        [CompanyName]    NVARCHAR(64)      NOT NULL
    );
END;
GO

IF OBJECT_ID(N'dw.DimCompanyProfile', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[DimCompanyProfile]
    (
        [CompanyProfileKey]  INT IDENTITY(1,1) NOT NULL,
        [CompanySize]        NVARCHAR(16)      NOT NULL,
        [LinkedInPresence]   TINYINT           NOT NULL,
        [WebsiteAvailable]   TINYINT           NOT NULL,
        [VerificationStatus] TINYINT           NOT NULL,
        [SocialMediaPresence] TINYINT          NOT NULL
    );
END;
GO

IF OBJECT_ID(N'dw.DimInternshipTitle', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[DimInternshipTitle]
    (
        [InternshipTitleKey] INT IDENTITY(1,1) NOT NULL,
        [InternshipTitle]    NVARCHAR(32)      NOT NULL
    );
END;
GO

IF OBJECT_ID(N'dw.DimIndustry', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[DimIndustry]
    (
        [IndustryKey] INT IDENTITY(1,1) NOT NULL,
        [Industry]    NVARCHAR(24)      NOT NULL
    );
END;
GO

IF OBJECT_ID(N'dw.DimLocation', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[DimLocation]
    (
        [LocationKey] INT IDENTITY(1,1) NOT NULL,
        [Location]    NVARCHAR(24)      NOT NULL
    );
END;
GO

IF OBJECT_ID(N'dw.DimEmploymentType', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[DimEmploymentType]
    (
        [EmploymentTypeKey] INT IDENTITY(1,1) NOT NULL,
        [EmploymentType]    NVARCHAR(16)      NOT NULL
    );
END;
GO

IF OBJECT_ID(N'dw.DimWorkMode', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[DimWorkMode]
    (
        [WorkModeKey] INT IDENTITY(1,1) NOT NULL,
        [WorkMode]    NVARCHAR(16)      NOT NULL
    );
END;
GO

IF OBJECT_ID(N'dw.DimRecruiterEmail', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[DimRecruiterEmail]
    (
        [RecruiterEmailKey]     INT IDENTITY(1,1) NOT NULL,
        [RecruiterEmailType]    NVARCHAR(16)      NOT NULL,
        [SuspiciousEmailDomain] TINYINT           NOT NULL
    );
END;
GO
