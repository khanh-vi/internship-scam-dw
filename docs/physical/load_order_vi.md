# Trình tự nạp — InternshipScamDW

## Phạm vi

Đây là trình tự nạp logic đã phê duyệt cho Star Schema v1. Tài liệu mô tả quy trình ETL tương lai; deliverable hiện tại chỉ tạo đối tượng SQL và dữ liệu tham chiếu, không nạp CSV staging.

## Thứ tự script tiên quyết

Chạy từ `sql/00_create_database.sql` đến `sql/08_validation_queries.sql` theo thứ tự số. `07_seed_unknown_members.sql` tạo Unknown member có key 0 và lịch liên tục từ 2018-01-01 đến 2026-12-31 trước mọi lần nạp Fact. `09_drop_all.sql` là script reset phá hủy riêng biệt và không bao giờ thuộc luồng nạp bình thường.

## Thứ tự nạp dữ liệu logic

| Bước | Target | Lý do |
| ---: | --- | --- |
| 1 | `stg.InternshipPosting` | Tiếp nhận đủ 35 cột đồng dạng nguồn và kiểm tra kiểu/miền nguồn. |
| 2 | `dw.DimDate` | Seed Unknown và toàn bộ lịch trước lookup ngày. |
| 3 | `dw.DimCompanyName` | Chèn các chuỗi tên công ty quan sát được riêng biệt; không entity resolution. |
| 4 | `dw.DimCompanyProfile` | Chèn các tổ hợp profile năm thuộc tính riêng biệt; không hard-code 64. |
| 5 | `dw.DimInternshipTitle` | Chèn các giá trị chức danh riêng biệt. |
| 6 | `dw.DimIndustry` | Chèn các giá trị ngành riêng biệt. |
| 7 | `dw.DimLocation` | Chèn location riêng biệt mà không suy diễn geography/currency. |
| 8 | `dw.DimEmploymentType` | Chèn các giá trị loại việc làm riêng biệt. |
| 9 | `dw.DimWorkMode` | Chèn các giá trị work mode riêng biệt. |
| 10 | `dw.DimRecruiterEmail` | Chèn các tổ hợp `(RecruiterEmailType, SuspiciousEmailDomain)` riêng biệt. |
| 11 | `dw.FactInternshipPosting` | Giải quyết đủ chín key rồi chèn measure, lineage và quality flag. |

Fact nạp cuối vì mỗi foreign key khác 0 phải giải quyết được tới một dòng Dimension đã nạp trước. Thuộc tính Dimension thực sự thiếu/không giải quyết được dùng member key 0 hiện có; không được đưa giá trị hợp lệ vào Unknown. Các foreign key được kiểm tra sẽ từ chối orphan row.

## Luồng ETL lookup

```text
staging row
  -> Date lookup (posting_date -> DateKey)
  -> CompanyName lookup (company_name -> CompanyNameKey)
  -> CompanyProfile lookup (company_size + four flags -> CompanyProfileKey)
  -> InternshipTitle lookup
  -> Industry lookup
  -> Location lookup
  -> EmploymentType lookup
  -> WorkMode lookup
  -> RecruiterEmail lookup (email type + suspicious-domain flag)
  -> Fact insert
```

Thao tác chèn Fact sao chép các measure đã phê duyệt mà không imputation hay re-scaling, ánh xạ `is_fake_posting` sang `FakePostingCount`, mang theo `SourceRowID` và `IsFuturePosting`, đồng thời bỏ `unrealistic_salary_flag`. Sau này lấy `PostingCount` bằng `COUNT_BIG(*)`; `FakePostingRate` là `SUM(FakePostingCount) / COUNT_BIG(*)`.

## Idempotency và xử lý lỗi

Luồng một nguồn hiện tại phải coi `SourceRowID` là idempotency key. `UQ_FactInternshipPosting_SourceRowID` khiến lần nạp lặp ngoài ý muốn bị lỗi thay vì âm thầm nhân đôi dòng. ETL nên thực hiện Dimension upsert và batch Fact trong transaction có kiểm soát, báo lỗi lookup/chất lượng dữ liệu và không âm thầm “sửa” giá trị nguồn. Nguồn thứ hai trong tương lai yêu cầu `(SourceSystemKey, SourceRowID)` và một lần sửa schema có phê duyệt.

## Kiểm tra sau nạp

Chạy `sql/08_validation_queries.sql`. Lần nạp đầy đủ đầu tiên kỳ vọng 1,000,000 dòng staging và 1,000,000 dòng Fact, không orphan, không trùng `SourceRowID`, không vi phạm miền nhị phân/score, 30,246 dòng future posting và 221,958 dòng được gắn nhãn giả. Số dòng Dimension đã biết của extract hiện tại chỉ là số so sánh trong script, không phải table constraint.
