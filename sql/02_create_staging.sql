/*
  Source-aligned, 35-column staging table.
  This script creates an empty table; it does not read or alter any CSV file.
*/
USE [InternshipScamDW];
GO

IF OBJECT_ID(N'stg.InternshipPosting', N'U') IS NULL
BEGIN
    CREATE TABLE [stg].[InternshipPosting]
    (
        [posting_date]                  DATE           NOT NULL,
        [internship_title]              NVARCHAR(32)   NOT NULL,
        [employment_type]               NVARCHAR(16)   NOT NULL,
        [work_mode]                     NVARCHAR(16)   NOT NULL,
        [industry]                      NVARCHAR(24)   NOT NULL,
        [location]                      NVARCHAR(24)   NOT NULL,
        [company_name]                  NVARCHAR(64)   NOT NULL,
        [company_size]                  NVARCHAR(16)   NOT NULL,
        [company_age]                   SMALLINT       NULL,
        [linkedin_presence]             SMALLINT       NOT NULL,
        [website_available]             SMALLINT       NOT NULL,
        [domain_age_months]             SMALLINT       NOT NULL,
        [verification_status]           SMALLINT       NOT NULL,
        [stipend]                       INT            NULL,
        [unrealistic_salary_flag]       SMALLINT       NOT NULL,
        [payment_required]              SMALLINT       NOT NULL,
        [registration_fee]              INT            NOT NULL,
        [job_description_length]        SMALLINT       NOT NULL,
        [grammatical_errors]            SMALLINT       NOT NULL,
        [vague_description_score]       SMALLINT       NOT NULL,
        [urgency_score]                 SMALLINT       NOT NULL,
        [keyword_spam_score]            SMALLINT       NOT NULL,
        [fake_certificate_offer]        SMALLINT       NOT NULL,
        [recruiter_experience_years]    DECIMAL(3,1)   NOT NULL,
        [recruiter_email_type]          NVARCHAR(16)   NOT NULL,
        [suspicious_email_domain]       SMALLINT       NOT NULL,
        [recruiter_response_time_hours] DECIMAL(3,1)   NOT NULL,
        [social_media_presence]         SMALLINT       NOT NULL,
        [emotional_manipulation_score]  SMALLINT       NOT NULL,
        [phishing_language_score]       SMALLINT       NOT NULL,
        [trust_signal_score]            DECIMAL(4,1)   NULL,
        [fraud_score]                   DECIMAL(4,1)   NOT NULL,
        [is_fake_posting]               SMALLINT       NOT NULL,
        [source_row_id]                 INT            NOT NULL,
        [is_future_posting]             SMALLINT       NOT NULL
    );
END;
GO
