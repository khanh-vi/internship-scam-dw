/*
  Keys, referential integrity, uniqueness and domain checks.
  Run after 04_create_fact.sql and before indexes/seeding.
*/
USE [InternshipScamDW];
GO

/* Staging key and source-domain checks. */
ALTER TABLE [stg].[InternshipPosting]
    ADD CONSTRAINT [PK_InternshipPosting] PRIMARY KEY CLUSTERED ([source_row_id]);
GO

ALTER TABLE [stg].[InternshipPosting] ADD
    CONSTRAINT [CK_InternshipPosting_LinkedInPresence] CHECK ([linkedin_presence] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_WebsiteAvailable] CHECK ([website_available] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_VerificationStatus] CHECK ([verification_status] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_UnrealisticSalaryFlag] CHECK ([unrealistic_salary_flag] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_PaymentRequired] CHECK ([payment_required] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_FakeCertificateOffer] CHECK ([fake_certificate_offer] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_SuspiciousEmailDomain] CHECK ([suspicious_email_domain] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_SocialMediaPresence] CHECK ([social_media_presence] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_IsFakePosting] CHECK ([is_fake_posting] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_IsFuturePosting] CHECK ([is_future_posting] IN (0,1)),
    CONSTRAINT [CK_InternshipPosting_VagueDescriptionScore] CHECK ([vague_description_score] BETWEEN 0 AND 100),
    CONSTRAINT [CK_InternshipPosting_UrgencyScore] CHECK ([urgency_score] BETWEEN 0 AND 100),
    CONSTRAINT [CK_InternshipPosting_KeywordSpamScore] CHECK ([keyword_spam_score] BETWEEN 0 AND 100),
    CONSTRAINT [CK_InternshipPosting_EmotionalManipulationScore] CHECK ([emotional_manipulation_score] BETWEEN 0 AND 100),
    CONSTRAINT [CK_InternshipPosting_PhishingLanguageScore] CHECK ([phishing_language_score] BETWEEN 0 AND 100),
    CONSTRAINT [CK_InternshipPosting_TrustSignalScore] CHECK ([trust_signal_score] BETWEEN 0 AND 100),
    CONSTRAINT [CK_InternshipPosting_FraudScore] CHECK ([fraud_score] BETWEEN 0 AND 100);
GO

/* Dimension primary keys and natural-key uniqueness. */
ALTER TABLE [dw].[DimDate]
    ADD CONSTRAINT [PK_DimDate] PRIMARY KEY CLUSTERED ([DateKey]),
        CONSTRAINT [UQ_DimDate_FullDate] UNIQUE NONCLUSTERED ([FullDate]),
        CONSTRAINT [CK_DimDate_CalendarParts] CHECK
        (
            ([DateKey] = 0 AND [FullDate] = CONVERT(DATE, '19000101', 112)
             AND [DayOfMonth] = 0 AND [DayOfWeek] = 0 AND [MonthNumber] = 0
             AND [QuarterNumber] = 0 AND [YearNumber] = 0)
            OR
            ([DateKey] = CONVERT(INT, CONVERT(CHAR(8), [FullDate], 112))
             AND [DayOfMonth] = DAY([FullDate])
             AND [DayOfWeek] BETWEEN 1 AND 7
             AND [MonthNumber] = MONTH([FullDate])
             AND [QuarterNumber] = DATEPART(QUARTER, [FullDate])
             AND [YearNumber] = YEAR([FullDate]))
        );
GO

ALTER TABLE [dw].[DimCompanyName]
    ADD CONSTRAINT [PK_DimCompanyName] PRIMARY KEY CLUSTERED ([CompanyNameKey]),
        CONSTRAINT [UQ_DimCompanyName_CompanyName] UNIQUE NONCLUSTERED ([CompanyName]);
GO

ALTER TABLE [dw].[DimCompanyProfile]
    ADD CONSTRAINT [PK_DimCompanyProfile] PRIMARY KEY CLUSTERED ([CompanyProfileKey]),
        CONSTRAINT [UQ_DimCompanyProfile_Profile] UNIQUE NONCLUSTERED
            ([CompanySize], [LinkedInPresence], [WebsiteAvailable], [VerificationStatus], [SocialMediaPresence]),
        CONSTRAINT [CK_DimCompanyProfile_LinkedInPresence] CHECK ([LinkedInPresence] IN (0,1)),
        CONSTRAINT [CK_DimCompanyProfile_WebsiteAvailable] CHECK ([WebsiteAvailable] IN (0,1)),
        CONSTRAINT [CK_DimCompanyProfile_VerificationStatus] CHECK ([VerificationStatus] IN (0,1)),
        CONSTRAINT [CK_DimCompanyProfile_SocialMediaPresence] CHECK ([SocialMediaPresence] IN (0,1));
GO

ALTER TABLE [dw].[DimInternshipTitle]
    ADD CONSTRAINT [PK_DimInternshipTitle] PRIMARY KEY CLUSTERED ([InternshipTitleKey]),
        CONSTRAINT [UQ_DimInternshipTitle_InternshipTitle] UNIQUE NONCLUSTERED ([InternshipTitle]);
GO

ALTER TABLE [dw].[DimIndustry]
    ADD CONSTRAINT [PK_DimIndustry] PRIMARY KEY CLUSTERED ([IndustryKey]),
        CONSTRAINT [UQ_DimIndustry_Industry] UNIQUE NONCLUSTERED ([Industry]);
GO

ALTER TABLE [dw].[DimLocation]
    ADD CONSTRAINT [PK_DimLocation] PRIMARY KEY CLUSTERED ([LocationKey]),
        CONSTRAINT [UQ_DimLocation_Location] UNIQUE NONCLUSTERED ([Location]);
GO

ALTER TABLE [dw].[DimEmploymentType]
    ADD CONSTRAINT [PK_DimEmploymentType] PRIMARY KEY CLUSTERED ([EmploymentTypeKey]),
        CONSTRAINT [UQ_DimEmploymentType_EmploymentType] UNIQUE NONCLUSTERED ([EmploymentType]);
GO

ALTER TABLE [dw].[DimWorkMode]
    ADD CONSTRAINT [PK_DimWorkMode] PRIMARY KEY CLUSTERED ([WorkModeKey]),
        CONSTRAINT [UQ_DimWorkMode_WorkMode] UNIQUE NONCLUSTERED ([WorkMode]);
GO

ALTER TABLE [dw].[DimRecruiterEmail]
    ADD CONSTRAINT [PK_DimRecruiterEmail] PRIMARY KEY CLUSTERED ([RecruiterEmailKey]),
        CONSTRAINT [UQ_DimRecruiterEmail_Profile] UNIQUE NONCLUSTERED ([RecruiterEmailType], [SuspiciousEmailDomain]),
        CONSTRAINT [CK_DimRecruiterEmail_SuspiciousEmailDomain] CHECK ([SuspiciousEmailDomain] IN (0,1));
GO

/* Fact key, single-source idempotency, domain checks and nine star joins. */
ALTER TABLE [dw].[FactInternshipPosting]
    ADD CONSTRAINT [PK_FactInternshipPosting] PRIMARY KEY NONCLUSTERED ([FactPostingKey]),
        CONSTRAINT [UQ_FactInternshipPosting_SourceRowID] UNIQUE NONCLUSTERED ([SourceRowID]),
        CONSTRAINT [CK_FactInternshipPosting_IsFuturePosting] CHECK ([IsFuturePosting] IN (0,1)),
        CONSTRAINT [CK_FactInternshipPosting_FakePostingCount] CHECK ([FakePostingCount] IN (0,1)),
        CONSTRAINT [CK_FactInternshipPosting_PaymentRequired] CHECK ([PaymentRequired] IN (0,1)),
        CONSTRAINT [CK_FactInternshipPosting_FakeCertificateOffer] CHECK ([FakeCertificateOffer] IN (0,1)),
        CONSTRAINT [CK_FactInternshipPosting_VagueDescriptionScore] CHECK ([VagueDescriptionScore] BETWEEN 0 AND 100),
        CONSTRAINT [CK_FactInternshipPosting_UrgencyScore] CHECK ([UrgencyScore] BETWEEN 0 AND 100),
        CONSTRAINT [CK_FactInternshipPosting_KeywordSpamScore] CHECK ([KeywordSpamScore] BETWEEN 0 AND 100),
        CONSTRAINT [CK_FactInternshipPosting_EmotionalManipulationScore] CHECK ([EmotionalManipulationScore] BETWEEN 0 AND 100),
        CONSTRAINT [CK_FactInternshipPosting_PhishingLanguageScore] CHECK ([PhishingLanguageScore] BETWEEN 0 AND 100),
        CONSTRAINT [CK_FactInternshipPosting_TrustSignalScore] CHECK ([TrustSignalScore] BETWEEN 0 AND 100),
        CONSTRAINT [CK_FactInternshipPosting_FraudScore] CHECK ([FraudScore] BETWEEN 0 AND 100);
GO

ALTER TABLE [dw].[FactInternshipPosting] WITH CHECK ADD
    CONSTRAINT [FK_FactInternshipPosting_DimDate]
        FOREIGN KEY ([DateKey]) REFERENCES [dw].[DimDate] ([DateKey]),
    CONSTRAINT [FK_FactInternshipPosting_DimCompanyName]
        FOREIGN KEY ([CompanyNameKey]) REFERENCES [dw].[DimCompanyName] ([CompanyNameKey]),
    CONSTRAINT [FK_FactInternshipPosting_DimCompanyProfile]
        FOREIGN KEY ([CompanyProfileKey]) REFERENCES [dw].[DimCompanyProfile] ([CompanyProfileKey]),
    CONSTRAINT [FK_FactInternshipPosting_DimInternshipTitle]
        FOREIGN KEY ([InternshipTitleKey]) REFERENCES [dw].[DimInternshipTitle] ([InternshipTitleKey]),
    CONSTRAINT [FK_FactInternshipPosting_DimIndustry]
        FOREIGN KEY ([IndustryKey]) REFERENCES [dw].[DimIndustry] ([IndustryKey]),
    CONSTRAINT [FK_FactInternshipPosting_DimLocation]
        FOREIGN KEY ([LocationKey]) REFERENCES [dw].[DimLocation] ([LocationKey]),
    CONSTRAINT [FK_FactInternshipPosting_DimEmploymentType]
        FOREIGN KEY ([EmploymentTypeKey]) REFERENCES [dw].[DimEmploymentType] ([EmploymentTypeKey]),
    CONSTRAINT [FK_FactInternshipPosting_DimWorkMode]
        FOREIGN KEY ([WorkModeKey]) REFERENCES [dw].[DimWorkMode] ([WorkModeKey]),
    CONSTRAINT [FK_FactInternshipPosting_DimRecruiterEmail]
        FOREIGN KEY ([RecruiterEmailKey]) REFERENCES [dw].[DimRecruiterEmail] ([RecruiterEmailKey]);
GO
