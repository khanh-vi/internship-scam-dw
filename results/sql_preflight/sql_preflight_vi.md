# Kiểm tra trước triển khai SQL Server — InternshipScamDW

## Phạm vi và kết luận

Đây là lần review tĩnh văn bản SQL thực tế từ `sql/00_create_database.sql` đến `sql/09_drop_all.sql`, đối chiếu với `docs/schema/`, `docs/physical/` và `docs/data_dictionary.md`. Không kết nối SQL Server; không đọc hoặc sửa CSV.

**Mức sẵn sàng triển khai cuối cùng: READY**

- Finding BLOCKING: **0**
- Finding IMPORTANT: **1**
- File SQL đã thay đổi: **không có**
- Cơ sở: chuỗi `00` đến `07` trên instance sạch có thể thực thi nội tại trên SQL Server 2019+, `08` chỉ đọc, và `09` là reset giới hạn trong database nhưng không drop database.

Chỉ finding BLOCKING mới ngăn trạng thái `READY`. Finding IMPORTANT duy nhất là độ lệch tài liệu và không làm chuỗi SQL đã review mất an toàn.

## Danh mục finding

| ID | Mức độ | Finding | Bằng chứng | Khuyến nghị |
| --- | --- | --- | --- | --- |
| PF-01 | IMPORTANT | Tài liệu logical schema vẫn mô tả dòng Unknown của `DimDate` là `FullDate = NULL`, trong khi physical design đã phê duyệt, yêu cầu của tác vụ, định nghĩa bảng, CHECK constraint và seed đều dùng sentinel không null `1900-01-01`. Catalog cũng ghi 3.287 dòng ngày v1 mà chưa phân biệt rõ số dòng ngày đã biết với tổng 3.288 dòng sau khi seed Unknown. Điều này không chặn triển khai vì các artifact vật lý thống nhất với nhau. | `docs/schema/star_schema_design_vi.md:220,415`; `docs/schema/dimension_catalog.csv:2`; `docs/physical/physical_design_vi.md:42-44`; `sql/03_create_dimensions.sql:9-17`; `sql/05_create_constraints.sql:34-49`; `sql/07_seed_unknown_members.sql:14-56` | Đồng bộ tài liệu logical schema Anh/Việt và dimension catalog bằng một thay đổi chỉ ở tài liệu: ghi `FullDate = 1900-01-01`, 3.287 dòng lịch đã biết và 3.288 dòng tổng cộng gồm key 0. Không đổi sentinel trong SQL hoặc nới lỏng constraint. |
| PF-02 | INFORMATIONAL | Các script tạo object dùng tạo có điều kiện, nhưng `05_create_constraints.sql` chủ ý chỉ chạy một lần. Chạy lại `05` ngoài ý muốn sẽ lỗi vì các object PK/UQ/CHECK/FK đã tồn tại. Các script tạo bảng có điều kiện cũng không sửa hoặc xác minh một object hiện hữu sai cấu trúc. | `sql/02_create_staging.sql:8-48`; `sql/03_create_dimensions.sql:5-104`; `sql/04_create_fact.sql:5-40`; `sql/05_create_constraints.sql:9-133` | Khi redeploy toàn bộ, chạy reset đã review rồi chạy `00`–`07`. Sau lỗi một phần trong `05`, hãy kiểm tra/reset thay vì giả định chạy lại mọi script sẽ tự sửa. Không cần viết lại toàn bộ để idempotent cho lần triển khai coursework này. |
| PF-03 | INFORMATIONAL | Phiên bản tối thiểu thực tế là SQL Server 2019 vì script `00` đặt compatibility level 150. Principal thực thi cũng cần quyền database/schema/table/constraint/index. | `sql/00_create_database.sql:3,9-18`; `sql/06_create_indexes.sql:19-21`; `sql/09_drop_all.sql:9-29` | Triển khai trên SQL Server 2019 trở lên với các quyền đã nêu. Riêng `DROP TABLE IF EXISTS` và columnstore có mức tối thiểu cũ hơn, nhưng compatibility level 150 khiến 2019 là ngưỡng hiệu lực. |

## 1. Thứ tự thực thi và phụ thuộc object

Thứ tự triển khai sạch bắt buộc là hợp lệ:

| Script | Tạo/tác động | Điều kiện trước | Kết quả |
| --- | --- | --- | --- |
| `00_create_database.sql` | Database `InternshipScamDW`; compatibility 150 | `master`; quyền create/alter database | PASS |
| `01_create_schemas.sql` | `stg`, `dw` | Database từ `00` | PASS |
| `02_create_staging.sql` | `stg.InternshipPosting` | schema `stg` | PASS |
| `03_create_dimensions.sql` | 9 bảng Dimension | schema `dw` | PASS |
| `04_create_fact.sql` | `dw.FactInternshipPosting` | schema `dw`; Dimension đã có cho các FK ở bước sau | PASS |
| `05_create_constraints.sql` | 11 PK, 10 unique constraint, 34 CHECK, 9 FK | Đủ bảng staging, Dimension và Fact | PASS |
| `06_create_indexes.sql` | Một clustered columnstore index trên Fact | Fact tồn tại; PK và unique SourceRowID là nonclustered | PASS |
| `07_seed_unknown_members.sql` | 9 Unknown member key 0 và 3.287 ngày bình thường | Constraint Dimension tồn tại | PASS |
| `08_validation_queries.sql` | Các result set validation chỉ SELECT | Object đã triển khai; so sánh có ý nghĩa sau ETL | PASS, chỉ validation |
| `09_drop_all.sql` | Drop bảng dự án rồi drop schema dự án nếu rỗng | Database phải tồn tại | PASS, chỉ reset |

Không object dự án nào bị tham chiếu trước khi tạo trong `00`–`07`. `08` không thuộc luồng tạo object, và `09` không thuộc luồng triển khai/nạp bình thường.

## 2. Database context và schema

- `00` chủ ý bắt đầu trong `[master]` để tạo database, sau đó chuyển sang `[InternshipScamDW]` trong batch riêng.
- Mỗi script `01`–`09` bắt đầu bằng `USE [InternshipScamDW]; GO`. Do đó script sau không kế thừa `master` hoặc database tùy ý của caller.
- `stg` và `dw` được tạo có điều kiện trước mọi bảng.
- Tất cả bảng dự án, tham chiếu FK, mục tiêu index và mục tiêu DML đều được định danh đầy đủ bằng `[stg]` hoặc `[dw]`.
- Các tham chiếu system catalog (`sys.indexes`, `sys.objects`, `sys.all_objects`) chủ ý nằm trong context `InternshipScamDW` đang hoạt động.

**Trạng thái database context: PASS.**

## 3. Audit bảng staging

Đối chiếu cơ học tìm thấy **35 dòng mapping, 35 cột staging trong SQL, 0 thiếu và 0 thừa**. Bảng chứa 33 cột nguồn cộng với `source_row_id` và `is_future_posting` được dẫn xuất.

- Tên và thứ tự khớp hợp đồng staging đã phê duyệt.
- Kiểu triển khai SQL Server khớp physical design: `NVARCHAR` có kích thước phù hợp, `DATE`, `SMALLINT`, `INT` và `DECIMAL` fixed-precision.
- Ba trường nguồn nullable là chính xác: `company_age SMALLINT NULL`, `stipend INT NULL` và `trust_signal_score DECIMAL(4,1) NULL`.
- Không DEFAULT nào âm thầm đổi giá trị nullable thành 0.
- Các CHECK staging chỉ giới hạn các flag 0/1 và score 0–100 đã được ghi nhận. Không có check về currency, payment period, company age so với domain age hoặc business semantic tự suy diễn khác.
- `source_row_id` là clustered PK của staging, phù hợp lineage dòng duy nhất trong extract hiện tại đã phê duyệt.

**Trạng thái cột staging: PASS — đúng 35/35 cột đã phê duyệt.**

## 4. PK Dimension, IDENTITY, natural key và Unknown member

| Dimension | Surrogate PK | IDENTITY | Uniqueness đã phê duyệt | Seed key 0 |
| --- | --- | ---: | --- | ---: |
| `DimDate` | `DateKey INT` | Không; YYYYMMDD/key 0 được ghi rõ | `FullDate` unique | Có |
| `DimCompanyName` | `CompanyNameKey INT` | Có | `CompanyName` | Có |
| `DimCompanyProfile` | `CompanyProfileKey INT` | Có | Profile năm thuộc tính | Có |
| `DimInternshipTitle` | `InternshipTitleKey INT` | Có | `InternshipTitle` | Có |
| `DimIndustry` | `IndustryKey INT` | Có | `Industry` | Có |
| `DimLocation` | `LocationKey INT` | Có | `Location` | Có |
| `DimEmploymentType` | `EmploymentTypeKey INT` | Có | `EmploymentType` | Có |
| `DimWorkMode` | `WorkModeKey INT` | Có | `WorkMode` | Có |
| `DimRecruiterEmail` | `RecruiterEmailKey INT` | Có | Cặp email-type/binary | Có |

Có **9 PK Dimension**. 8 surrogate key được sinh là `INT IDENTITY(1,1)`; `DimDate.DateKey` chủ ý được ghi trực tiếp. Script `07` có **8 câu `IDENTITY_INSERT ON` và 8 câu `OFF` tương ứng**, ghép cặp theo từng bảng trong transaction.

Tất cả dòng Unknown thỏa `NOT NULL`, uniqueness và CHECK constraint:

- `DimCompanyProfile` dùng `CompanySize = N'Unknown'` và bốn giá trị binary bằng `0`. `0` nằm trong mọi constraint `IN (0,1)`; size `Unknown` giữ natural key tổ hợp tách biệt khỏi 64 profile quan sát được.
- `DimRecruiterEmail` dùng `RecruiterEmailType = N'Unknown'` và `SuspiciousEmailDomain = 0`. Giá trị này thỏa `NOT NULL` và `IN (0,1)`, đồng thời khác hai email profile quan sát được.
- Không Dimension nào cố dùng `-1`, `NULL` hoặc sentinel binary ngoài miền khác.

**Trạng thái PK Dimension: PASS. Trạng thái Unknown member: PASS; không có xung đột Unknown/binary BLOCKING.**

## 5. Unknown của DimDate và lịch

- Dòng Unknown đúng là `DateKey = 0`, `FullDate = 1900-01-01`, text `Unknown` và các thành phần lịch số bằng 0.
- `CK_DimDate_CalendarParts` có nhánh Unknown rõ ràng và nhánh ngày bình thường riêng.
- Unique constraint trên `FullDate` cho phép sentinel đúng một lần.
- Việc sinh lịch bình thường được giới hạn rõ từ `2018-01-01` đến `2026-12-31`, nên không bao giờ sinh `1900-01-01`.
- Khoảng bình thường bao gồm hai đầu có **3.287 ngày**; sau dòng Unknown, Dimension đã seed có **3.288 dòng tổng cộng** trên một bảng ban đầu rỗng.
- Seed kiểm tra `FullDate` trước khi thêm mỗi ngày bình thường nên chạy lại không nhân đôi lịch.

**Trạng thái DimDate: PASS.** Độ lệch tài liệu là PF-01, không phải xung đột SQL.

## 6. Physical design Fact, index và idempotency

`dw.FactInternshipPosting` có đúng tổ hợp đã phê duyệt:

- `FactPostingKey BIGINT IDENTITY(1,1) NOT NULL`.
- `PK_FactInternshipPosting` được ghi rõ là **NONCLUSTERED**.
- `UQ_FactInternshipPosting_SourceRowID` là đúng một constraint **UNIQUE NONCLUSTERED**.
- `CCI_FactInternshipPosting` được tạo đúng một lần và là clustered structure duy nhất.
- Không có clustered rowstore PK của Fact trước CCI.
- Không có bộ index một-index-mỗi-FK hoặc index Fact trùng lặp.
- Index natural key của Dimension do constraint tạo cung cấp đường lookup cần thiết.

Uniqueness trên `SourceRowID INT` tương thích với 1.000.000 dòng và với thiết kế clustered columnstore của SQL Server 2019. Tài liệu nhất quán mô tả nó là handle lineage/idempotency một nguồn, không phải business key. Dòng nguồn trùng sẽ lỗi thay vì được nạp lặp âm thầm.

**Trạng thái tương thích Fact/CCI: PASS. Trạng thái idempotency dòng nguồn: PASS.**

## 7. Audit foreign key của Fact

Đủ **9 FK dự kiến**; mọi cột Fact và cột Dimension được tham chiếu đều là `INT NOT NULL`, và mọi đích đều là PK Dimension:

| Cột Fact | Khóa được tham chiếu | Kiểu khớp | Tên FK duy nhất |
| --- | --- | --- | --- |
| `DateKey` | `DimDate.DateKey` | Có | Có |
| `CompanyNameKey` | `DimCompanyName.CompanyNameKey` | Có | Có |
| `CompanyProfileKey` | `DimCompanyProfile.CompanyProfileKey` | Có | Có |
| `InternshipTitleKey` | `DimInternshipTitle.InternshipTitleKey` | Có | Có |
| `IndustryKey` | `DimIndustry.IndustryKey` | Có | Có |
| `LocationKey` | `DimLocation.LocationKey` | Có | Có |
| `EmploymentTypeKey` | `DimEmploymentType.EmploymentTypeKey` | Có | Có |
| `WorkModeKey` | `DimWorkMode.WorkModeKey` | Có | Có |
| `RecruiterEmailKey` | `DimRecruiterEmail.RecruiterEmailKey` | Có | Có |

Các FK được thêm bằng `WITH CHECK`; trên Fact sạch đang rỗng, chúng trở thành constraint đã check/trusted. Không có cascade.

**Trạng thái FK: PASS — 9/9.**

## 8. Audit CHECK constraint

Có đúng **34 CHECK constraint**, tất cả có tên duy nhất:

| Phạm vi | Binary | Score | Calendar | Tổng |
| --- | ---: | ---: | ---: | ---: |
| Staging | 10 | 7 | 0 | 17 |
| Dimension | 5 | 0 | 1 | 6 |
| Fact | 4 | 7 | 0 | 11 |
| **Tổng** | **19** | **14** | **1** | **34** |

- Mọi rule binary dùng `IN (0,1)`.
- Mọi rule score có giới hạn dùng `BETWEEN 0 AND 100`.
- `trust_signal_score` / `TrustSignalScore` vẫn nullable. Trong SQL Server, CHECK chỉ từ chối `FALSE`; predicate trả về `UNKNOWN` cho NULL, nên NULL đã phê duyệt được chấp nhận mà không nới rule 0–100 cho giá trị non-null.
- Không có CHECK không được hỗ trợ cho stipend currency, registration-fee currency, payment period hoặc company age so với domain age.

**Trạng thái CHECK constraint: PASS — 34/34.**

## 9. Ngữ nghĩa NULL và tiền tệ

- Staging và Fact đều bảo toàn NULL cho `company_age`/`CompanyAge`, `stipend`/`Stipend` và `trust_signal_score`/`TrustSignalScore`.
- Không có default trên các trường đó và không có câu seed/load nào impute 0.
- SQL đã review không convert hoặc annualize stipend, thêm currency, suy diễn payment period, convert registration fee hoặc suy diễn quan hệ giữa company age và domain age.

**Ngữ nghĩa NULL: PASS. Ngữ nghĩa tiền tệ: PASS (chủ ý chưa giải quyết).**

## 10. Script validation

`08_validation_queries.sql` chứa `USE`, `SET NOCOUNT`, `SELECT`, derived query, join, aggregate và `GO`. Nó không chứa thao tác `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `DROP` hoặc `ALTER` dữ liệu/schema.

Các literal 1.000.000 dòng, số lượng Dimension, 30.246 dòng tương lai và 221.958 dòng giả chỉ là cột output để so sánh. Chúng không phải constraint, giả định DDL hoặc filter làm biến đổi kết quả.

**Trạng thái chỉ đọc của script validation: PASS.**

## 11. Script drop/reset

- Drop Fact trước, loại bỏ mọi phụ thuộc FK.
- Drop Dimension tiếp theo, staging sau cùng, rồi chỉ drop `dw` và `stg` nếu từng schema không còn object.
- Dùng `USE [InternshipScamDW]`, nên được giới hạn trong database dự kiến.
- Không chứa `DROP DATABASE`, DDL cấp server, dò tìm/xóa object động hoặc thao tác CSV/file.
- Nếu có object không liên quan trong `dw` hoặc `stg`, kiểm tra schema rỗng sẽ giữ schema; script chỉ drop các bảng coursework được ghi tên rõ.

**Trạng thái an toàn script drop: PASS. Không có database drop.**

## 12. Hành vi chạy lại

| Script | Phân loại | Hành vi khi vô tình chạy lại |
| --- | --- | --- |
| `00` | Tạo có điều kiện; chạy lại an toàn | Bỏ qua create database; đặt lại compatibility 150. |
| `01` | Tạo có điều kiện; chạy lại an toàn | Bỏ qua schema đã tồn tại. |
| `02` | Tạo có điều kiện; no-op an toàn nếu bảng tồn tại | Không xác minh hoặc sửa cấu trúc hiện hữu sai. |
| `03` | Tạo có điều kiện; no-op an toàn cho từng Dimension hiện hữu | Không sửa định nghĩa sai/một phần. |
| `04` | Tạo có điều kiện; no-op an toàn nếu Fact tồn tại | Không sửa định nghĩa hiện hữu sai. |
| `05` | Chủ ý chỉ chạy một lần; cần các bảng đã tạo nhưng chưa có constraint | Chạy lại sẽ lỗi trên constraint/index đã tồn tại, thông thường ở PK đầu tiên. |
| `06` | Có điều kiện theo tên CCI; an toàn trong deployment đã phê duyệt | Bỏ qua CCI cùng tên; clustered structure khác tên sẽ khiến SQL Server từ chối clustered structure thứ hai. |
| `07` | Seed tham chiếu được thiết kế để chạy lại | Insert key 0 và lịch đều có guard; mọi cặp IDENTITY_INSERT cân bằng khi thực thi bình thường. |
| `08` | Chỉ đọc và chạy lại được | Trả về trạng thái hiện tại; giá trị trước ETL chỉ khác kỳ vọng. |
| `09` | Reset phá hủy; chạy lại được khi database tồn tại | Object có tên được drop có điều kiện; không bao giờ drop database. |

## 13. Giả định phiên bản SQL Server

Mức tối thiểu hiệu lực là **Microsoft SQL Server 2019**:

- compatibility level `150` được đặt rõ;
- dùng clustered columnstore cùng các rowstore constraint index nonclustered;
- reset dùng `DROP TABLE IF EXISTS`;
- CCI chỉ định `COMPRESSION_DELAY`;
- không dùng `CREATE OR ALTER` hoặc string function mới hơn.

`GO` là batch separator phía client, nên phải triển khai bằng client hiểu SQL Server như SSMS, Azure Data Studio hoặc sqlcmd thay vì gửi cả file như một API batch chưa tách.

## Khối trạng thái cuối

| Kết quả bắt buộc | Trạng thái |
| --- | --- |
| Readiness status | **READY** |
| Blocking issue count | **0** |
| Important issue count | **1** |
| Database context status | **PASS** |
| Staging column status | **PASS — 35/35** |
| Dimension PK status | **PASS — 9/9** |
| Unknown-member status | **PASS — 9/9; không xung đột binary** |
| Fact/CCI compatibility status | **PASS** |
| FK status | **PASS — 9/9** |
| CHECK constraint status | **PASS — 34/34** |
| Validation-script read-only status | **PASS** |
| Drop-script safety status | **PASS; không database drop** |
| File đã thay đổi | `results/sql_preflight/sql_preflight_en.md`; `results/sql_preflight/sql_preflight_vi.md` |
| Thay đổi SQL/CSV | **Không có** |
