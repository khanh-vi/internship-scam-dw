/* Read-only validation queries to run after the eventual ETL load. */
USE [InternshipScamDW];
GO
SET NOCOUNT ON;

/* 1. Row counts. First full posting load expects staging=fact=1,000,000. */
SELECT N'stg.InternshipPosting' AS [ObjectName], COUNT_BIG(*) AS [ActualRows],
       CONVERT(BIGINT, 1000000) AS [ExpectedRows]
FROM [stg].[InternshipPosting]
UNION ALL
SELECT N'dw.FactInternshipPosting', COUNT_BIG(*), CONVERT(BIGINT, 1000000)
FROM [dw].[FactInternshipPosting];

/* 2. Dimension counts: TotalRows includes key 0; KnownRows excludes it. */
SELECT N'dw.DimDate' AS [Dimension], COUNT_BIG(*) AS [TotalRows],
       SUM(CASE WHEN [DateKey] <> 0 THEN CONVERT(BIGINT, 1) ELSE 0 END) AS [KnownRows],
       CONVERT(BIGINT, 3287) AS [ExpectedKnownRows]
FROM [dw].[DimDate]
UNION ALL SELECT N'dw.DimCompanyName', COUNT_BIG(*), SUM(CASE WHEN [CompanyNameKey] <> 0 THEN CONVERT(BIGINT,1) ELSE 0 END), 535938 FROM [dw].[DimCompanyName]
UNION ALL SELECT N'dw.DimCompanyProfile', COUNT_BIG(*), SUM(CASE WHEN [CompanyProfileKey] <> 0 THEN CONVERT(BIGINT,1) ELSE 0 END), 64 FROM [dw].[DimCompanyProfile]
UNION ALL SELECT N'dw.DimInternshipTitle', COUNT_BIG(*), SUM(CASE WHEN [InternshipTitleKey] <> 0 THEN CONVERT(BIGINT,1) ELSE 0 END), 9 FROM [dw].[DimInternshipTitle]
UNION ALL SELECT N'dw.DimIndustry', COUNT_BIG(*), SUM(CASE WHEN [IndustryKey] <> 0 THEN CONVERT(BIGINT,1) ELSE 0 END), 9 FROM [dw].[DimIndustry]
UNION ALL SELECT N'dw.DimLocation', COUNT_BIG(*), SUM(CASE WHEN [LocationKey] <> 0 THEN CONVERT(BIGINT,1) ELSE 0 END), 9 FROM [dw].[DimLocation]
UNION ALL SELECT N'dw.DimEmploymentType', COUNT_BIG(*), SUM(CASE WHEN [EmploymentTypeKey] <> 0 THEN CONVERT(BIGINT,1) ELSE 0 END), 4 FROM [dw].[DimEmploymentType]
UNION ALL SELECT N'dw.DimWorkMode', COUNT_BIG(*), SUM(CASE WHEN [WorkModeKey] <> 0 THEN CONVERT(BIGINT,1) ELSE 0 END), 3 FROM [dw].[DimWorkMode]
UNION ALL SELECT N'dw.DimRecruiterEmail', COUNT_BIG(*), SUM(CASE WHEN [RecruiterEmailKey] <> 0 THEN CONVERT(BIGINT,1) ELSE 0 END), 2 FROM [dw].[DimRecruiterEmail];

/* 3. Orphan checks. Every result must be 0 (FKs also enforce this). */
SELECT N'DateKey' AS [ForeignKey], COUNT_BIG(*) AS [OrphanRows]
FROM [dw].[FactInternshipPosting] f LEFT JOIN [dw].[DimDate] d ON d.[DateKey]=f.[DateKey] WHERE d.[DateKey] IS NULL
UNION ALL SELECT N'CompanyNameKey', COUNT_BIG(*) FROM [dw].[FactInternshipPosting] f LEFT JOIN [dw].[DimCompanyName] d ON d.[CompanyNameKey]=f.[CompanyNameKey] WHERE d.[CompanyNameKey] IS NULL
UNION ALL SELECT N'CompanyProfileKey', COUNT_BIG(*) FROM [dw].[FactInternshipPosting] f LEFT JOIN [dw].[DimCompanyProfile] d ON d.[CompanyProfileKey]=f.[CompanyProfileKey] WHERE d.[CompanyProfileKey] IS NULL
UNION ALL SELECT N'InternshipTitleKey', COUNT_BIG(*) FROM [dw].[FactInternshipPosting] f LEFT JOIN [dw].[DimInternshipTitle] d ON d.[InternshipTitleKey]=f.[InternshipTitleKey] WHERE d.[InternshipTitleKey] IS NULL
UNION ALL SELECT N'IndustryKey', COUNT_BIG(*) FROM [dw].[FactInternshipPosting] f LEFT JOIN [dw].[DimIndustry] d ON d.[IndustryKey]=f.[IndustryKey] WHERE d.[IndustryKey] IS NULL
UNION ALL SELECT N'LocationKey', COUNT_BIG(*) FROM [dw].[FactInternshipPosting] f LEFT JOIN [dw].[DimLocation] d ON d.[LocationKey]=f.[LocationKey] WHERE d.[LocationKey] IS NULL
UNION ALL SELECT N'EmploymentTypeKey', COUNT_BIG(*) FROM [dw].[FactInternshipPosting] f LEFT JOIN [dw].[DimEmploymentType] d ON d.[EmploymentTypeKey]=f.[EmploymentTypeKey] WHERE d.[EmploymentTypeKey] IS NULL
UNION ALL SELECT N'WorkModeKey', COUNT_BIG(*) FROM [dw].[FactInternshipPosting] f LEFT JOIN [dw].[DimWorkMode] d ON d.[WorkModeKey]=f.[WorkModeKey] WHERE d.[WorkModeKey] IS NULL
UNION ALL SELECT N'RecruiterEmailKey', COUNT_BIG(*) FROM [dw].[FactInternshipPosting] f LEFT JOIN [dw].[DimRecruiterEmail] d ON d.[RecruiterEmailKey]=f.[RecruiterEmailKey] WHERE d.[RecruiterEmailKey] IS NULL;

/* 4. SourceRowID uniqueness/idempotency. DuplicateRows must be 0. */
SELECT N'stg.InternshipPosting' AS [ObjectName], COUNT_BIG(*) AS [Rows],
       COUNT_BIG(DISTINCT [source_row_id]) AS [DistinctSourceRowIDs],
       COUNT_BIG(*) - COUNT_BIG(DISTINCT [source_row_id]) AS [DuplicateRows]
FROM [stg].[InternshipPosting]
UNION ALL
SELECT N'dw.FactInternshipPosting', COUNT_BIG(*), COUNT_BIG(DISTINCT [SourceRowID]),
       COUNT_BIG(*) - COUNT_BIG(DISTINCT [SourceRowID])
FROM [dw].[FactInternshipPosting];

SELECT COUNT_BIG(*) AS [DuplicateGroups]
FROM (SELECT [SourceRowID] FROM [dw].[FactInternshipPosting] GROUP BY [SourceRowID] HAVING COUNT_BIG(*) > 1) AS [x];

/* 5. Binary-domain violations in staging and fact. Each count must be 0. */
SELECT N'stg.InternshipPosting' AS [ObjectName], [v].[ColumnName], COUNT_BIG(*) AS [ViolationRows]
FROM [stg].[InternshipPosting] AS [s]
CROSS APPLY (VALUES
    (N'linkedin_presence', [s].[linkedin_presence]), (N'website_available', [s].[website_available]),
    (N'verification_status', [s].[verification_status]), (N'unrealistic_salary_flag', [s].[unrealistic_salary_flag]),
    (N'payment_required', [s].[payment_required]), (N'fake_certificate_offer', [s].[fake_certificate_offer]),
    (N'suspicious_email_domain', [s].[suspicious_email_domain]), (N'social_media_presence', [s].[social_media_presence]),
    (N'is_fake_posting', [s].[is_fake_posting]), (N'is_future_posting', [s].[is_future_posting])
) AS [v]([ColumnName], [Value])
WHERE [v].[Value] NOT IN (0,1)
GROUP BY [v].[ColumnName]
UNION ALL
SELECT N'dw.FactInternshipPosting', [v].[ColumnName], COUNT_BIG(*)
FROM [dw].[FactInternshipPosting] AS [f]
CROSS APPLY (VALUES
    (N'IsFuturePosting', [f].[IsFuturePosting]), (N'FakePostingCount', [f].[FakePostingCount]),
    (N'PaymentRequired', [f].[PaymentRequired]), (N'FakeCertificateOffer', [f].[FakeCertificateOffer])
) AS [v]([ColumnName], [Value])
WHERE [v].[Value] NOT IN (0,1)
GROUP BY [v].[ColumnName]
UNION ALL
SELECT N'dw.DimCompanyProfile', [v].[ColumnName], COUNT_BIG(*)
FROM [dw].[DimCompanyProfile] AS [d]
CROSS APPLY (VALUES
    (N'LinkedInPresence', [d].[LinkedInPresence]), (N'WebsiteAvailable', [d].[WebsiteAvailable]),
    (N'VerificationStatus', [d].[VerificationStatus]), (N'SocialMediaPresence', [d].[SocialMediaPresence])
) AS [v]([ColumnName], [Value])
WHERE [v].[Value] NOT IN (0,1)
GROUP BY [v].[ColumnName]
UNION ALL
SELECT N'dw.DimRecruiterEmail', N'SuspiciousEmailDomain', COUNT_BIG(*)
FROM [dw].[DimRecruiterEmail]
WHERE [SuspiciousEmailDomain] NOT IN (0,1);

/* 6. Score-range violations in staging and Fact. Each count must be 0. */
SELECT N'stg.InternshipPosting' AS [ObjectName], [v].[ColumnName], COUNT_BIG(*) AS [ViolationRows]
FROM [stg].[InternshipPosting] AS [s]
CROSS APPLY (VALUES
    (N'vague_description_score', CONVERT(DECIMAL(4,1),[s].[vague_description_score])),
    (N'urgency_score', CONVERT(DECIMAL(4,1),[s].[urgency_score])),
    (N'keyword_spam_score', CONVERT(DECIMAL(4,1),[s].[keyword_spam_score])),
    (N'emotional_manipulation_score', CONVERT(DECIMAL(4,1),[s].[emotional_manipulation_score])),
    (N'phishing_language_score', CONVERT(DECIMAL(4,1),[s].[phishing_language_score])),
    (N'trust_signal_score', [s].[trust_signal_score]), (N'fraud_score', [s].[fraud_score])
) AS [v]([ColumnName], [Value])
WHERE [v].[Value] NOT BETWEEN 0 AND 100
GROUP BY [v].[ColumnName]
UNION ALL
SELECT N'dw.FactInternshipPosting', [v].[ColumnName], COUNT_BIG(*)
FROM [dw].[FactInternshipPosting] AS [f]
CROSS APPLY (VALUES
    (N'VagueDescriptionScore', CONVERT(DECIMAL(4,1),[f].[VagueDescriptionScore])),
    (N'UrgencyScore', CONVERT(DECIMAL(4,1),[f].[UrgencyScore])),
    (N'KeywordSpamScore', CONVERT(DECIMAL(4,1),[f].[KeywordSpamScore])),
    (N'EmotionalManipulationScore', CONVERT(DECIMAL(4,1),[f].[EmotionalManipulationScore])),
    (N'PhishingLanguageScore', CONVERT(DECIMAL(4,1),[f].[PhishingLanguageScore])),
    (N'TrustSignalScore', [f].[TrustSignalScore]), (N'FraudScore', [f].[FraudScore])
) AS [v]([ColumnName], [Value])
WHERE [v].[Value] NOT BETWEEN 0 AND 100
GROUP BY [v].[ColumnName];

/* 7. Quality/outcome totals and overall fake-posting rate. */
SELECT COUNT_BIG(*) AS [PostingCount],
       SUM(CONVERT(BIGINT, [IsFuturePosting])) AS [FuturePostingCount],
       CONVERT(BIGINT, 30246) AS [ExpectedFuturePostingCount],
       SUM(CONVERT(BIGINT, [FakePostingCount])) AS [FakePostingCount],
       CONVERT(BIGINT, 221958) AS [ExpectedFakePostingCount],
       CAST(SUM(CONVERT(DECIMAL(19,6), [FakePostingCount])) / NULLIF(COUNT_BIG(*), 0) AS DECIMAL(19,6)) AS [FakePostingRate]
FROM [dw].[FactInternshipPosting];

/* 8. Counts and fake rates by year, industry and work mode. */
SELECT [d].[YearNumber], COUNT_BIG(*) AS [PostingCount], SUM(CONVERT(BIGINT,[f].[FakePostingCount])) AS [FakePostingCount],
       CAST(SUM(CONVERT(DECIMAL(19,6),[f].[FakePostingCount])) / NULLIF(COUNT_BIG(*),0) AS DECIMAL(19,6)) AS [FakePostingRate]
FROM [dw].[FactInternshipPosting] [f] JOIN [dw].[DimDate] [d] ON [d].[DateKey]=[f].[DateKey]
GROUP BY [d].[YearNumber] ORDER BY [d].[YearNumber];

SELECT [d].[Industry], COUNT_BIG(*) AS [PostingCount], SUM(CONVERT(BIGINT,[f].[FakePostingCount])) AS [FakePostingCount],
       CAST(SUM(CONVERT(DECIMAL(19,6),[f].[FakePostingCount])) / NULLIF(COUNT_BIG(*),0) AS DECIMAL(19,6)) AS [FakePostingRate]
FROM [dw].[FactInternshipPosting] [f] JOIN [dw].[DimIndustry] [d] ON [d].[IndustryKey]=[f].[IndustryKey]
GROUP BY [d].[Industry] ORDER BY [PostingCount] DESC;

SELECT [d].[WorkMode], COUNT_BIG(*) AS [PostingCount], SUM(CONVERT(BIGINT,[f].[FakePostingCount])) AS [FakePostingCount],
       CAST(SUM(CONVERT(DECIMAL(19,6),[f].[FakePostingCount])) / NULLIF(COUNT_BIG(*),0) AS DECIMAL(19,6)) AS [FakePostingRate]
FROM [dw].[FactInternshipPosting] [f] JOIN [dw].[DimWorkMode] [d] ON [d].[WorkModeKey]=[f].[WorkModeKey]
GROUP BY [d].[WorkMode] ORDER BY [PostingCount] DESC;
GO
