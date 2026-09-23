/* Creates the empty posting-grain fact table. */
USE [InternshipScamDW];
GO

IF OBJECT_ID(N'dw.FactInternshipPosting', N'U') IS NULL
BEGIN
    CREATE TABLE [dw].[FactInternshipPosting]
    (
        [FactPostingKey]              BIGINT IDENTITY(1,1) NOT NULL,
        [DateKey]                     INT                  NOT NULL,
        [CompanyNameKey]              INT                  NOT NULL,
        [CompanyProfileKey]           INT                  NOT NULL,
        [InternshipTitleKey]          INT                  NOT NULL,
        [IndustryKey]                 INT                  NOT NULL,
        [LocationKey]                 INT                  NOT NULL,
        [EmploymentTypeKey]           INT                  NOT NULL,
        [WorkModeKey]                 INT                  NOT NULL,
        [RecruiterEmailKey]           INT                  NOT NULL,
        [SourceRowID]                 INT                  NOT NULL,
        [IsFuturePosting]             TINYINT              NOT NULL,
        [FakePostingCount]            TINYINT              NOT NULL,
        [PaymentRequired]             TINYINT              NOT NULL,
        [FakeCertificateOffer]        TINYINT              NOT NULL,
        [CompanyAge]                  SMALLINT              NULL,
        [DomainAgeMonths]             SMALLINT             NOT NULL,
        [Stipend]                     INT                   NULL,
        [RegistrationFee]             INT                  NOT NULL,
        [JobDescriptionLength]        SMALLINT             NOT NULL,
        [GrammaticalErrors]           TINYINT              NOT NULL,
        [VagueDescriptionScore]       TINYINT              NOT NULL,
        [UrgencyScore]                TINYINT              NOT NULL,
        [KeywordSpamScore]            TINYINT              NOT NULL,
        [EmotionalManipulationScore]  TINYINT              NOT NULL,
        [PhishingLanguageScore]       TINYINT              NOT NULL,
        [TrustSignalScore]            DECIMAL(4,1)          NULL,
        [FraudScore]                  DECIMAL(4,1)         NOT NULL,
        [RecruiterExperienceYears]    DECIMAL(3,1)         NOT NULL,
        [RecruiterResponseTimeHours]  DECIMAL(3,1)         NOT NULL
    );
END;
GO
