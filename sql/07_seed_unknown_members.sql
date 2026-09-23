/*
  Seeds surrogate key 0 unknown members and the complete 2018-01-01..2026-12-31
  calendar. This is reference-data seeding only; it does not load postings.
*/
USE [InternshipScamDW];
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LANGUAGE us_english;
GO

BEGIN TRANSACTION;

IF NOT EXISTS (SELECT 1 FROM [dw].[DimDate] WHERE [DateKey] = 0)
BEGIN
    INSERT [dw].[DimDate]
        ([DateKey], [FullDate], [DayOfMonth], [DayOfWeek], [DayName],
         [MonthNumber], [MonthName], [QuarterNumber], [YearNumber])
    VALUES
        (0, CONVERT(DATE, '19000101', 112), 0, 0, N'Unknown',
         0, N'Unknown', 0, 0);
END;

DECLARE @StartDate DATE = CONVERT(DATE, '20180101', 112);
DECLARE @EndDate   DATE = CONVERT(DATE, '20261231', 112);

;WITH [Numbers] AS
(
    SELECT TOP (DATEDIFF(DAY, @StartDate, @EndDate) + 1)
           ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS [n]
    FROM sys.all_objects AS [a]
    CROSS JOIN sys.all_objects AS [b]
),
[Calendar] AS
(
    SELECT DATEADD(DAY, [n], @StartDate) AS [FullDate]
    FROM [Numbers]
)
INSERT [dw].[DimDate]
    ([DateKey], [FullDate], [DayOfMonth], [DayOfWeek], [DayName],
     [MonthNumber], [MonthName], [QuarterNumber], [YearNumber])
SELECT
    CONVERT(INT, CONVERT(CHAR(8), [c].[FullDate], 112)),
    [c].[FullDate],
    CONVERT(TINYINT, DAY([c].[FullDate])),
    CONVERT(TINYINT, (DATEDIFF(DAY, CONVERT(DATE, '19000101', 112), [c].[FullDate]) % 7) + 1),
    CONVERT(NVARCHAR(10), DATENAME(WEEKDAY, [c].[FullDate])),
    CONVERT(TINYINT, MONTH([c].[FullDate])),
    CONVERT(NVARCHAR(10), DATENAME(MONTH, [c].[FullDate])),
    CONVERT(TINYINT, DATEPART(QUARTER, [c].[FullDate])),
    CONVERT(SMALLINT, YEAR([c].[FullDate]))
FROM [Calendar] AS [c]
WHERE NOT EXISTS
(
    SELECT 1 FROM [dw].[DimDate] AS [d] WHERE [d].[FullDate] = [c].[FullDate]
);

SET IDENTITY_INSERT [dw].[DimCompanyName] ON;
IF NOT EXISTS (SELECT 1 FROM [dw].[DimCompanyName] WHERE [CompanyNameKey] = 0)
    INSERT [dw].[DimCompanyName] ([CompanyNameKey], [CompanyName]) VALUES (0, N'Unknown');
SET IDENTITY_INSERT [dw].[DimCompanyName] OFF;

SET IDENTITY_INSERT [dw].[DimCompanyProfile] ON;
IF NOT EXISTS (SELECT 1 FROM [dw].[DimCompanyProfile] WHERE [CompanyProfileKey] = 0)
    INSERT [dw].[DimCompanyProfile]
        ([CompanyProfileKey], [CompanySize], [LinkedInPresence], [WebsiteAvailable], [VerificationStatus], [SocialMediaPresence])
    VALUES (0, N'Unknown', 0, 0, 0, 0);
SET IDENTITY_INSERT [dw].[DimCompanyProfile] OFF;

SET IDENTITY_INSERT [dw].[DimInternshipTitle] ON;
IF NOT EXISTS (SELECT 1 FROM [dw].[DimInternshipTitle] WHERE [InternshipTitleKey] = 0)
    INSERT [dw].[DimInternshipTitle] ([InternshipTitleKey], [InternshipTitle]) VALUES (0, N'Unknown');
SET IDENTITY_INSERT [dw].[DimInternshipTitle] OFF;

SET IDENTITY_INSERT [dw].[DimIndustry] ON;
IF NOT EXISTS (SELECT 1 FROM [dw].[DimIndustry] WHERE [IndustryKey] = 0)
    INSERT [dw].[DimIndustry] ([IndustryKey], [Industry]) VALUES (0, N'Unknown');
SET IDENTITY_INSERT [dw].[DimIndustry] OFF;

SET IDENTITY_INSERT [dw].[DimLocation] ON;
IF NOT EXISTS (SELECT 1 FROM [dw].[DimLocation] WHERE [LocationKey] = 0)
    INSERT [dw].[DimLocation] ([LocationKey], [Location]) VALUES (0, N'Unknown');
SET IDENTITY_INSERT [dw].[DimLocation] OFF;

SET IDENTITY_INSERT [dw].[DimEmploymentType] ON;
IF NOT EXISTS (SELECT 1 FROM [dw].[DimEmploymentType] WHERE [EmploymentTypeKey] = 0)
    INSERT [dw].[DimEmploymentType] ([EmploymentTypeKey], [EmploymentType]) VALUES (0, N'Unknown');
SET IDENTITY_INSERT [dw].[DimEmploymentType] OFF;

SET IDENTITY_INSERT [dw].[DimWorkMode] ON;
IF NOT EXISTS (SELECT 1 FROM [dw].[DimWorkMode] WHERE [WorkModeKey] = 0)
    INSERT [dw].[DimWorkMode] ([WorkModeKey], [WorkMode]) VALUES (0, N'Unknown');
SET IDENTITY_INSERT [dw].[DimWorkMode] OFF;

SET IDENTITY_INSERT [dw].[DimRecruiterEmail] ON;
IF NOT EXISTS (SELECT 1 FROM [dw].[DimRecruiterEmail] WHERE [RecruiterEmailKey] = 0)
    INSERT [dw].[DimRecruiterEmail]
        ([RecruiterEmailKey], [RecruiterEmailType], [SuspiciousEmailDomain])
    VALUES (0, N'Unknown', 0);
SET IDENTITY_INSERT [dw].[DimRecruiterEmail] OFF;

COMMIT TRANSACTION;
GO
