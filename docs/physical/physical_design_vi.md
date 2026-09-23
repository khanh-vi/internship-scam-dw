# Thiết kế vật lý SQL Server — Star Schema v1

## 1. Phạm vi

Tài liệu này đặc tả việc triển khai vật lý trên SQL Server cho grain đã phê duyệt: một dòng là một bản ghi tin đăng. Sản phẩm chỉ gồm các script; không sửa file raw hay staging, không nạp dữ liệu tin đăng và không xây dựng gói SSIS. Database là `InternshipScamDW`; các đối tượng phân tích dùng schema `dw`, còn bảng tiếp nhận đồng dạng nguồn dùng `stg`.

## 2. Ánh xạ logic sang vật lý

Mô hình vẫn gồm một Fact và chín Dimension. Mỗi dòng `FactInternshipPosting` là một bản ghi nguồn quan sát được, không nhất thiết là một tin đăng duy nhất trong thế giới thực. Toàn bộ 35 cột staging được giữ lại. Trường duy nhất bị loại khỏi schema phân tích là `unrealistic_salary_flag`; trường này vẫn nằm trong staging nhưng luôn bằng 0 nên không có phương sai phân tích.

`is_fake_posting` ánh xạ nguyên trạng sang `FakePostingCount` được lưu vật lý. Tổng của cột này đếm số bản ghi được gắn nhãn giả. Không lưu `PostingCount` vì `COUNT_BIG(*)` tương đương hoàn toàn tại grain này. Không lưu `FakePostingRate`; chỉ tính bằng `SUM(FakePostingCount) / COUNT_BIG(*)` với cơ chế tránh chia cho 0.

Tên thuộc tính ngày vật lý tuân theo hợp đồng yêu cầu: các tên logic `Day`, `Month`, `Quarter`, `Year` trở thành `DayOfMonth`, `MonthNumber`, `QuarterNumber`, `YearNumber`.

## 3. Tổ chức schema

| Schema | Vai trò đối tượng |
| --- | --- |
| `stg` | `InternshipPosting` đồng dạng nguồn, gồm 35 cột và không tái cấu trúc theo mô hình phân tích |
| `dw` | Chín Dimension và `FactInternshipPosting` |

`dbo` sở hữu hai schema nhưng không chứa bảng phân tích.

## 4. Lựa chọn datatype

Các kiểu SQL Server `DATE`, số nguyên và `DECIMAL` có độ chính xác cố định bảo toàn miền giá trị đã được ghi nhận. Measure nullable của nguồn vẫn nullable. Surrogate key của Fact dùng `BIGINT`; lineage nguồn và khóa Dimension dùng `INT`. Các flag staging giữ `SMALLINT` như tài liệu dữ liệu, còn các cột phân tích có miền 0/1 và 0–100 dùng `TINYINT`.

Mọi chuỗi dùng `NVARCHAR` để tương thích Unicode trong tương lai. Độ dài vẫn theo thiết kế đã duyệt: 16/24/32/64 tùy cột; tên công ty dùng 64 ký tự khi cực đại đo được là 38. Không dùng `NVARCHAR(MAX)`. Lựa chọn này thay đổi cách lưu mã ký tự, không thay đổi giá trị hay ngữ nghĩa nguồn.

## 5. Chiến lược primary key

Surrogate key của Dimension dùng `INT`; tất cả ngoại trừ `DimDate` dùng `IDENTITY(1,1)`. `DateKey` theo quy ước `YYYYMMDD`. `FactPostingKey` là `BIGINT IDENTITY(1,1)` và là nonclustered primary key để Fact có thể dùng clustered columnstore index. `stg.InternshipPosting.source_row_id` là clustered primary key của bảng staging.

Các thuộc tính tự nhiên hoặc tổ hợp thuộc tính đã duyệt có UNIQUE constraint. Tính duy nhất của `DimCompanyName.CompanyName` là tính duy nhất của chuỗi theo collation của database; điều đó không khẳng định các chuỗi giống nhau là một pháp nhân công ty đã được xác minh.

## 6. Chiến lược foreign key

Fact có chín foreign key được kiểm tra và trusted, mỗi khóa nối tới một Dimension. Các Dimension phải được nạp trước Fact. Không bật cascading delete hoặc update. ETL tương lai gán key 0 khi lookup thất bại; không được ánh xạ giá trị nguồn hợp lệ sang Unknown.

## 7. Unknown member

Mỗi Dimension dành surrogate key 0. Dimension chuỗi dùng `Unknown`. Các flag của profile và email dùng 0 chỉ trong dòng Unknown kỹ thuật. `DimDate` dùng `DateKey = 0`, chuỗi `Unknown`, thuộc tính số bằng 0 và `FullDate = 1900-01-01` vì `FullDate` bắt buộc và duy nhất. Đây là sentinel kỹ thuật nằm ngoài lịch nghiệp vụ được hỗ trợ và không được hiểu là ngày đăng quan sát được.

Lịch được sinh liên tục từ 2018-01-01 đến 2026-12-31 (3,287 ngày đã biết), không thu hoạch riêng các ngày xuất hiện trong dữ liệu. Sau khi seed cả Unknown, `DimDate` có 3,288 dòng. Chỉ bật `IDENTITY_INSERT` xung quanh từng thao tác chèn key 0.

## 8. Constraint

Có 34 `CHECK` constraint được đặt tên: 17 trên staging (10 kiểm tra nhị phân và 7 kiểm tra score), 6 trên Dimension (một quy tắc lịch và năm kiểm tra nhị phân), và 11 trên Fact (4 kiểm tra nhị phân và 7 kiểm tra score). Giá trị nhị phân bị giới hạn trong `{0,1}`, score trong 0–100. `TrustSignalScore` nullable vẫn chấp nhận NULL vì `CHECK` của SQL Server chấp nhận kết quả UNKNOWN.

Không thêm constraint suy đoán về currency, annualization, stipend, registration fee hay quan hệ giữa tuổi công ty và tuổi domain. Không hard-code 64 tổ hợp company profile quan sát được.

## 9. Chiến lược index

| Nguồn index | Index vật lý | Mục đích |
| --- | --- | --- |
| PK constraint của Dimension | Clustered rowstore index | Join bằng surrogate key nhỏ gọn |
| UNIQUE constraint của Dimension | Nonclustered unique index | Lookup natural key trong ETL và ngăn trùng |
| PK constraint của Fact | Nonclustered unique index trên `FactPostingKey` | Định danh dòng ổn định mà không chiếm clustered storage |
| Constraint lineage của Fact | Nonclustered unique index trên `SourceRowID` | Idempotency một nguồn và truy vết |
| `06_create_indexes.sql` | `CCI_FactInternshipPosting` | Lưu trữ OLAP nén, tối ưu scan |

Không tạo index một cách máy móc cho từng FK của Fact. Columnstore scan và hash join phù hợp workload phân tích dự kiến; các rowstore index dư thừa làm tăng chi phí nạp và lưu trữ. Sau này chỉ bổ sung index chọn lọc khi có bằng chứng workload.

## 10. Quyết định columnstore

Star Schema v1 dùng clustered columnstore index trên `FactInternshipPosting`. Khoảng 1,000,000 dòng đủ để hưởng lợi từ column elimination, batch-mode scan và compression; workload thiên về aggregate và dự kiến nạp theo batch/bulk. Nonclustered PK và unique lineage index vẫn được hỗ trợ cùng columnstore trên SQL Server 2019+.

Phương án thay thế là clustered rowstore PK trên `FactPostingKey`, đơn giản hơn và có thể phù hợp workload nhỏ, ghi từng dòng hoặc lookup nhiều. Phương án này không được chọn vì đây là Data Warehouse OLAP. Nên nạp theo tập hợp và batch đủ lớn để tạo compressed rowgroup; nhiều insert rất nhỏ có thể để dữ liệu trong delta store và làm giảm lợi ích.

## 11. Idempotency và lineage của Fact

`UQ_FactInternshipPosting_SourceRowID` ngăn cùng một bản ghi staging bị chèn hai lần trong thiết kế một nguồn hiện tại. `SourceRowID` là ETL lineage handle, không phải business identifier và không chứng minh tin đăng thực là duy nhất. Khi có nhiều nguồn, phạm vi duy nhất phải đổi thành `(SourceSystemKey, SourceRowID)`; `SourceSystemKey` chủ ý chưa được triển khai trong v1.

## 12. Giới hạn của trường tiền tệ

`Stipend INT NULL` bảo toàn số nguồn mà không imputation, currency conversion, normalization hay annualization. Cả currency và pay period đều chưa được giải quyết, vì vậy trường này bị ẩn khỏi bộ measure mặc định đã kiểm chứng và không được aggregate xuyên location như thể các đơn vị giống nhau.

`RegistrationFee INT NOT NULL` bảo toàn giá trị số nguồn, gồm cả 0 với nghĩa “không có phí”. Currency chưa được giải quyết. Không có `CHECK` constraint dựa trên currency và việc aggregate tiền tệ xuyên location chưa được xác nhận.

## 13. Trình tự nạp

Thực thi các file SQL từ `00` đến `08` theo thứ tự số. Thứ tự dữ liệu logic là staging, lịch, các Dimension còn lại, rồi Fact. Mỗi dòng staging lần lượt lookup ngày, chuỗi tên công ty, tổ hợp company profile, chức danh, ngành, location, loại việc làm, work mode và tổ hợp recruiter email trước khi chèn Fact. Fact nạp cuối vì mọi key khác 0 phải tồn tại trước và mọi FK đều được kiểm tra. Xem `load_order_vi.md`.

## 14. Quyết định vật lý hoãn lại

- Phạm vi theo source system cho lineage khi xuất hiện nguồn thứ hai.
- Currency và pay period của stipend, cùng currency của registration fee.
- Rowstore index chọn lọc trên Fact, partitioning hoặc columnstore ordering sau khi có bằng chứng query/load thực tế.
- Filegroup production, bảo trì compression, backup/recovery, security role và điều phối bằng SQL Agent/SSIS.
- Collation production tường minh nếu mặc định triển khai không phù hợp. Tính duy nhất natural key hiện theo collation của database.

## 15. Giả định và lưu ý SQL Server

Các script nhắm tới SQL Server 2019 trở lên và đặt compatibility level 150. Script dùng `GO`, `CREATE CLUSTERED COLUMNSTORE INDEX`, `DROP TABLE IF EXISTS` và constraint index nonclustered trên bảng columnstore. Principal thực thi cần quyền tạo database, schema, bảng, constraint và index. `07_seed_unknown_members.sql` đặt `us_english` khi sinh tên thứ và tháng bằng tiếng Anh. Deliverable này không chạy trên SQL Server thật.

## 16. Ma trận đầy đủ các cột vật lý

`—` nghĩa là không có default. `IDENTITY` là metadata sinh giá trị, không phải default constraint.

| Table | Column | SQL Server datatype | Nullable | PK/FK | Default | Constraint | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `stg.InternshipPosting` | `posting_date` | `DATE` | No | — | — | — | `posting_date` |
| `stg.InternshipPosting` | `internship_title` | `NVARCHAR(32)` | No | — | — | — | `internship_title` |
| `stg.InternshipPosting` | `employment_type` | `NVARCHAR(16)` | No | — | — | — | `employment_type` |
| `stg.InternshipPosting` | `work_mode` | `NVARCHAR(16)` | No | — | — | — | `work_mode` |
| `stg.InternshipPosting` | `industry` | `NVARCHAR(24)` | No | — | — | — | `industry` |
| `stg.InternshipPosting` | `location` | `NVARCHAR(24)` | No | — | — | — | `location` |
| `stg.InternshipPosting` | `company_name` | `NVARCHAR(64)` | No | — | — | — | `company_name` |
| `stg.InternshipPosting` | `company_size` | `NVARCHAR(16)` | No | — | — | — | `company_size` |
| `stg.InternshipPosting` | `company_age` | `SMALLINT` | Yes | — | — | — | `company_age` |
| `stg.InternshipPosting` | `linkedin_presence` | `SMALLINT` | No | — | — | 0/1 | `linkedin_presence` |
| `stg.InternshipPosting` | `website_available` | `SMALLINT` | No | — | — | 0/1 | `website_available` |
| `stg.InternshipPosting` | `domain_age_months` | `SMALLINT` | No | — | — | — | `domain_age_months` |
| `stg.InternshipPosting` | `verification_status` | `SMALLINT` | No | — | — | 0/1 | `verification_status` |
| `stg.InternshipPosting` | `stipend` | `INT` | Yes | — | — | — | `stipend` |
| `stg.InternshipPosting` | `unrealistic_salary_flag` | `SMALLINT` | No | — | — | 0/1 | `unrealistic_salary_flag` |
| `stg.InternshipPosting` | `payment_required` | `SMALLINT` | No | — | — | 0/1 | `payment_required` |
| `stg.InternshipPosting` | `registration_fee` | `INT` | No | — | — | — | `registration_fee` |
| `stg.InternshipPosting` | `job_description_length` | `SMALLINT` | No | — | — | — | `job_description_length` |
| `stg.InternshipPosting` | `grammatical_errors` | `SMALLINT` | No | — | — | — | `grammatical_errors` |
| `stg.InternshipPosting` | `vague_description_score` | `SMALLINT` | No | — | — | 0–100 | `vague_description_score` |
| `stg.InternshipPosting` | `urgency_score` | `SMALLINT` | No | — | — | 0–100 | `urgency_score` |
| `stg.InternshipPosting` | `keyword_spam_score` | `SMALLINT` | No | — | — | 0–100 | `keyword_spam_score` |
| `stg.InternshipPosting` | `fake_certificate_offer` | `SMALLINT` | No | — | — | 0/1 | `fake_certificate_offer` |
| `stg.InternshipPosting` | `recruiter_experience_years` | `DECIMAL(3,1)` | No | — | — | — | `recruiter_experience_years` |
| `stg.InternshipPosting` | `recruiter_email_type` | `NVARCHAR(16)` | No | — | — | — | `recruiter_email_type` |
| `stg.InternshipPosting` | `suspicious_email_domain` | `SMALLINT` | No | — | — | 0/1 | `suspicious_email_domain` |
| `stg.InternshipPosting` | `recruiter_response_time_hours` | `DECIMAL(3,1)` | No | — | — | — | `recruiter_response_time_hours` |
| `stg.InternshipPosting` | `social_media_presence` | `SMALLINT` | No | — | — | 0/1 | `social_media_presence` |
| `stg.InternshipPosting` | `emotional_manipulation_score` | `SMALLINT` | No | — | — | 0–100 | `emotional_manipulation_score` |
| `stg.InternshipPosting` | `phishing_language_score` | `SMALLINT` | No | — | — | 0–100 | `phishing_language_score` |
| `stg.InternshipPosting` | `trust_signal_score` | `DECIMAL(4,1)` | Yes | — | — | 0–100 | `trust_signal_score` |
| `stg.InternshipPosting` | `fraud_score` | `DECIMAL(4,1)` | No | — | — | 0–100 | `fraud_score` |
| `stg.InternshipPosting` | `is_fake_posting` | `SMALLINT` | No | — | — | 0/1 | `is_fake_posting` |
| `stg.InternshipPosting` | `source_row_id` | `INT` | No | PK | — | Unique | staging-derived lineage |
| `stg.InternshipPosting` | `is_future_posting` | `SMALLINT` | No | — | — | 0/1 | staging-derived vs 2026-09-23 |
| `dw.DimDate` | `DateKey` | `INT` | No | PK | — | 0 or YYYYMMDD | generated calendar |
| `dw.DimDate` | `FullDate` | `DATE` | No | — | — | Unique | generated calendar |
| `dw.DimDate` | `DayOfMonth` | `TINYINT` | No | — | — | calendar rule | `FullDate` |
| `dw.DimDate` | `DayOfWeek` | `TINYINT` | No | — | — | 0 or 1–7 | `FullDate`, Monday=1 |
| `dw.DimDate` | `DayName` | `NVARCHAR(10)` | No | — | — | — | `FullDate` (`us_english`) |
| `dw.DimDate` | `MonthNumber` | `TINYINT` | No | — | — | calendar rule | `FullDate` |
| `dw.DimDate` | `MonthName` | `NVARCHAR(10)` | No | — | — | — | `FullDate` (`us_english`) |
| `dw.DimDate` | `QuarterNumber` | `TINYINT` | No | — | — | calendar rule | `FullDate` |
| `dw.DimDate` | `YearNumber` | `SMALLINT` | No | — | — | calendar rule | `FullDate` |
| `dw.DimCompanyName` | `CompanyNameKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimCompanyName` | `CompanyName` | `NVARCHAR(64)` | No | — | — | Unique | `company_name` |
| `dw.DimCompanyProfile` | `CompanyProfileKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimCompanyProfile` | `CompanySize` | `NVARCHAR(16)` | No | — | — | Composite unique | `company_size` |
| `dw.DimCompanyProfile` | `LinkedInPresence` | `TINYINT` | No | — | — | 0/1; composite unique | `linkedin_presence` |
| `dw.DimCompanyProfile` | `WebsiteAvailable` | `TINYINT` | No | — | — | 0/1; composite unique | `website_available` |
| `dw.DimCompanyProfile` | `VerificationStatus` | `TINYINT` | No | — | — | 0/1; composite unique | `verification_status` |
| `dw.DimCompanyProfile` | `SocialMediaPresence` | `TINYINT` | No | — | — | 0/1; composite unique | `social_media_presence` |
| `dw.DimInternshipTitle` | `InternshipTitleKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimInternshipTitle` | `InternshipTitle` | `NVARCHAR(32)` | No | — | — | Unique | `internship_title` |
| `dw.DimIndustry` | `IndustryKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimIndustry` | `Industry` | `NVARCHAR(24)` | No | — | — | Unique | `industry` |
| `dw.DimLocation` | `LocationKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimLocation` | `Location` | `NVARCHAR(24)` | No | — | — | Unique | `location` |
| `dw.DimEmploymentType` | `EmploymentTypeKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimEmploymentType` | `EmploymentType` | `NVARCHAR(16)` | No | — | — | Unique | `employment_type` |
| `dw.DimWorkMode` | `WorkModeKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimWorkMode` | `WorkMode` | `NVARCHAR(16)` | No | — | — | Unique | `work_mode` |
| `dw.DimRecruiterEmail` | `RecruiterEmailKey` | `INT IDENTITY(1,1)` | No | PK | IDENTITY | — | warehouse-generated |
| `dw.DimRecruiterEmail` | `RecruiterEmailType` | `NVARCHAR(16)` | No | — | — | Composite unique | `recruiter_email_type` |
| `dw.DimRecruiterEmail` | `SuspiciousEmailDomain` | `TINYINT` | No | — | — | 0/1; composite unique | `suspicious_email_domain` |
| `dw.FactInternshipPosting` | `FactPostingKey` | `BIGINT IDENTITY(1,1)` | No | PK | IDENTITY | Unique | warehouse-generated |
| `dw.FactInternshipPosting` | `DateKey` | `INT` | No | FK | — | FK to `DimDate` | `posting_date` lookup |
| `dw.FactInternshipPosting` | `CompanyNameKey` | `INT` | No | FK | — | FK to `DimCompanyName` | `company_name` lookup |
| `dw.FactInternshipPosting` | `CompanyProfileKey` | `INT` | No | FK | — | FK to `DimCompanyProfile` | 5-column profile lookup |
| `dw.FactInternshipPosting` | `InternshipTitleKey` | `INT` | No | FK | — | FK to `DimInternshipTitle` | `internship_title` lookup |
| `dw.FactInternshipPosting` | `IndustryKey` | `INT` | No | FK | — | FK to `DimIndustry` | `industry` lookup |
| `dw.FactInternshipPosting` | `LocationKey` | `INT` | No | FK | — | FK to `DimLocation` | `location` lookup |
| `dw.FactInternshipPosting` | `EmploymentTypeKey` | `INT` | No | FK | — | FK to `DimEmploymentType` | `employment_type` lookup |
| `dw.FactInternshipPosting` | `WorkModeKey` | `INT` | No | FK | — | FK to `DimWorkMode` | `work_mode` lookup |
| `dw.FactInternshipPosting` | `RecruiterEmailKey` | `INT` | No | FK | — | FK to `DimRecruiterEmail` | 2-column email lookup |
| `dw.FactInternshipPosting` | `SourceRowID` | `INT` | No | — | — | Unique | `source_row_id` |
| `dw.FactInternshipPosting` | `IsFuturePosting` | `TINYINT` | No | — | — | 0/1 | `is_future_posting` |
| `dw.FactInternshipPosting` | `FakePostingCount` | `TINYINT` | No | — | — | 0/1 | `is_fake_posting` |
| `dw.FactInternshipPosting` | `PaymentRequired` | `TINYINT` | No | — | — | 0/1 | `payment_required` |
| `dw.FactInternshipPosting` | `FakeCertificateOffer` | `TINYINT` | No | — | — | 0/1 | `fake_certificate_offer` |
| `dw.FactInternshipPosting` | `CompanyAge` | `SMALLINT` | Yes | — | — | — | `company_age` |
| `dw.FactInternshipPosting` | `DomainAgeMonths` | `SMALLINT` | No | — | — | — | `domain_age_months` |
| `dw.FactInternshipPosting` | `Stipend` | `INT` | Yes | — | — | — | `stipend` |
| `dw.FactInternshipPosting` | `RegistrationFee` | `INT` | No | — | — | — | `registration_fee` |
| `dw.FactInternshipPosting` | `JobDescriptionLength` | `SMALLINT` | No | — | — | — | `job_description_length` |
| `dw.FactInternshipPosting` | `GrammaticalErrors` | `TINYINT` | No | — | — | — | `grammatical_errors` |
| `dw.FactInternshipPosting` | `VagueDescriptionScore` | `TINYINT` | No | — | — | 0–100 | `vague_description_score` |
| `dw.FactInternshipPosting` | `UrgencyScore` | `TINYINT` | No | — | — | 0–100 | `urgency_score` |
| `dw.FactInternshipPosting` | `KeywordSpamScore` | `TINYINT` | No | — | — | 0–100 | `keyword_spam_score` |
| `dw.FactInternshipPosting` | `EmotionalManipulationScore` | `TINYINT` | No | — | — | 0–100 | `emotional_manipulation_score` |
| `dw.FactInternshipPosting` | `PhishingLanguageScore` | `TINYINT` | No | — | — | 0–100 | `phishing_language_score` |
| `dw.FactInternshipPosting` | `TrustSignalScore` | `DECIMAL(4,1)` | Yes | — | — | 0–100 | `trust_signal_score` |
| `dw.FactInternshipPosting` | `FraudScore` | `DECIMAL(4,1)` | No | — | — | 0–100 | `fraud_score` |
| `dw.FactInternshipPosting` | `RecruiterExperienceYears` | `DECIMAL(3,1)` | No | — | — | — | `recruiter_experience_years` |
| `dw.FactInternshipPosting` | `RecruiterResponseTimeHours` | `DECIMAL(3,1)` | No | — | — | — | `recruiter_response_time_hours` |
