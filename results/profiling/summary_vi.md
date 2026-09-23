# Báo cáo Data Profiling

- **File nguồn**: `E:/project/internship-scam-dw/data/raw/fake_internship_detection_dataset.csv`
- **Thời điểm tạo**: 2026-09-23 16:35:25
- **sha256 nguồn**: `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398`
- **Phạm vi**: chỉ profiling. Không có gì trong `data/raw/` bị ghi vào, và không giá trị nào trong dataset bị làm sạch, impute, đổi kiểu, encode hay loại bỏ.

Các tiểu mục có tiêu đề **Dữ kiện quan sát được** là những phép đo lấy trực tiếp từ dữ liệu. Các tiểu mục có tiêu đề **Các vấn đề tiềm ẩn cần con người xem xét** là giả thuyết mà con người phải xác nhận trước khi bất kỳ quyết định nào được đưa ra. Ở giai đoạn này không có cột nào được đề xuất xóa hay sửa đổi.

## 1. Kích thước dataset

**Dữ kiện quan sát được**

| Chỉ số | Giá trị |
| --- | --- |
| Số dòng | 1,000,000 |
| Số cột | 33 |
| Số ô (cell) | 33,000,000 |
| Kích thước file trên đĩa | 165.74 MB |
| Kích thước trong bộ nhớ (pandas, deep) | 687.48 MB |
| Số cột numeric | 24 |
| Số cột text / categorical | 9 |
| Số cột có dtype datetime | 0 |
| Số cột boolean | 0 |
| Số cột khác | 0 |

Không cột nào đến từ CSV với dtype datetime; các cột mang dạng date được đọc là text và được phân tích ở mục 6.

## 2. Dữ liệu thiếu

**Dữ kiện quan sát được**

- Tổng số ô bị thiếu: **30,000** (0.0909% tổng số ô).
- Số cột có ít nhất một giá trị thiếu: **3 trên 33**.
- Số cột không có giá trị thiếu nào: **30**.

| Cột | dtype | Số thiếu | % thiếu |
| --- | --- | ---: | ---: |
| `company_age` | float64 | 10,000 | 1.0000% |
| `stipend` | float64 | 10,000 | 1.0000% |
| `trust_signal_score` | float64 | 10,000 | 1.0000% |

**Các vấn đề tiềm ẩn cần con người xem xét**

- `company_age` có tỷ lệ giá trị thiếu cao nhất (1.0000%). Việc đây là thiếu mang tính cấu trúc (dữ kiện đó không tồn tại với tin tuyển dụng ấy) hay là một lỗ hổng trong quá trình thu thập thì không thể quyết định chỉ từ dữ liệu và cần phán xét của con người.
- Tính thiếu dữ liệu **chưa** được kiểm định về mối liên hệ với biến mục tiêu `is_fake_posting`. Nếu bản thân việc thiếu dữ liệu mang thông tin, một quyết định imputation về sau có thể phá hủy tín hiệu đó. Được gắn cờ, chưa xử lý.
- Chuỗi rỗng trong các cột text không được pandas tính là thiếu; xem mục 7 cho các trường hợp đó.

## 3. Dòng trùng lặp

**Dữ kiện quan sát được**

- Số dòng trùng khớp chính xác (cả 33 cột giống nhau, chỉ tính các bản sao thừa): **0** (0.0000% số dòng).
- Số dòng phân biệt: **1,000,000**.
- Được đếm bằng `DataFrame.duplicated(keep='first')`, nên lần xuất hiện đầu tiên của một dòng lặp lại không bị tính. **Không dòng nào bị loại bỏ.**

**Các vấn đề tiềm ẩn cần con người xem xét**

- Không tìm thấy dòng trùng khớp chính xác nào.
- Các bản gần-trùng (dòng giống nhau ở mọi cột trừ một hoặc hai cột) **chưa** được tìm kiếm: một phép so sánh toàn bộ cặp là O(n^2) và không khả thi ở số dòng này. Nếu điều đó quan trọng, hãy làm về sau với một blocking key trên vài cột.

## 4. Các cột numeric và bất thường

**Dữ kiện quan sát được**

| Cột | min | median | max | số zero | số âm | outlier theo IQR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `company_age` | 1 | 20 | 39 | 0 | 0 | 0 (0.00%) |
| `linkedin_presence` | 0 | 1 | 1 | 199,236 | 0 | 0 (0.00%) |
| `website_available` | 0 | 1 | 1 | 150,403 | 0 | 0 (0.00%) |
| `domain_age_months` | 1 | 240 | 500 | 0 | 0 | 0 (0.00%) |
| `verification_status` | 0 | 1 | 1 | 300,287 | 0 | 0 (0.00%) |
| `stipend` | 2,000 | 3.498e+04 | 1.104e+05 | 0 | 0 | 3,348 (0.34%) |
| `unrealistic_salary_flag` | 0 | 0 | 0 | 1,000,000 | 0 | 0 (0.00%) |
| `payment_required` | 0 | 0 | 1 | 900,095 | 0 | 0 (0.00%) |
| `registration_fee` | 0 | 0 | 4,999 | 900,095 | 0 | 0 (0.00%) |
| `job_description_length` | 100 | 1,799 | 5,000 | 0 | 0 | 7,040 (0.70%) |
| `grammatical_errors` | 0 | 3 | 14 | 49,716 | 0 | 11,891 (1.19%) |
| `vague_description_score` | 0 | 30 | 100 | 73,938 | 0 | 3,472 (0.35%) |
| `urgency_score` | 0 | 39 | 100 | 59,153 | 0 | 0 (0.00%) |
| `keyword_spam_score` | 0 | 25 | 100 | 114,428 | 0 | 3,451 (0.35%) |
| `fake_certificate_offer` | 0 | 0 | 1 | 920,170 | 0 | 0 (0.00%) |
| `recruiter_experience_years` | 0 | 5 | 19.6 | 49,615 | 0 | 3,585 (0.36%) |
| `suspicious_email_domain` | 0 | 0 | 1 | 749,433 | 0 | 0 (0.00%) |
| `recruiter_response_time_hours` | 1 | 18 | 63.9 | 0 | 0 | 3,217 (0.32%) |
| `social_media_presence` | 0 | 1 | 1 | 250,200 | 0 | 0 (0.00%) |
| `emotional_manipulation_score` | 0 | 24 | 100 | 114,946 | 0 | 3,516 (0.35%) |
| `phishing_language_score` | 0 | 19 | 100 | 145,727 | 0 | 2,650 (0.27%) |
| `trust_signal_score` | 0 | 56.9 | 100 | 479 | 0 | 4,510 (0.46%) |
| `fraud_score` | 0 | 32.3 | 100 | 51,586 | 0 | 8,881 (0.89%) |
| `is_fake_posting` | 0 | 0 | 1 | 778,042 | 0 | 0 (0.00%) |

Thống kê đầy đủ - count, mean, độ lệch chuẩn, các tứ phân vị - nằm trong `numeric_summary.csv`. Outlier theo IQR dùng ngưỡng 1.5x khoảng tứ phân vị theo thông lệ và là một công cụ sàng lọc, không phải một kết luận.

**Các vấn đề tiềm ẩn cần con người xem xét**

- Không cột numeric nào chứa giá trị âm.
- Hơn một nửa tổng số dòng có giá trị zero ở: `unrealistic_salary_flag`, `payment_required`, `registration_fee`, `fake_certificate_offer`, `suspicious_email_domain`, `is_fake_posting`. Với một chỉ báo 0/1 thì đó là mất cân bằng lớp thông thường; với một đại lượng được đo thì nó có thể báo hiệu một giá trị mặc định hoặc placeholder. Sự phân biệt này không thể thực hiện tự động.
- (Các) cột numeric là hằng số (chỉ một giá trị): `unrealistic_salary_flag`. Chỉ gắn cờ - **không** đề xuất loại bỏ ở đây.
- Được lưu với dtype numeric nhưng chỉ chứa hai giá trị phân biệt: `linkedin_presence`, `website_available`, `verification_status`, `payment_required`, `fake_certificate_offer`, `suspicious_email_domain`, `social_media_presence`, `is_fake_posting`. Rất có khả năng đây là các flag chứ không phải measure, điều này quan trọng khi quyết định cái gì trở thành thuộc tính Dimension và cái gì trở thành measure trong Fact. Cần xác nhận thủ công.
- `grammatical_errors` có tỷ lệ outlier theo IQR lớn nhất (1.19%, max 14). Đây có thể là một đuôi dài thực sự chứ không phải lỗi; không giá trị nào bị chặn ngưỡng hay loại bỏ.

## 5. Cardinality của các cột categorical

**Dữ kiện quan sát được**

| Cột | Số giá trị phân biệt | Giá trị phổ biến nhất | Số lượng | % số dòng |
| --- | ---: | --- | ---: | ---: |
| `company_name` | 535,938 | Smith PLC | 1,248 | 0.125% |
| `posting_date` | 3,287 | 2020-10-10 | 366 | 0.037% |
| `internship_title` | 9 | Marketing Intern | 111,577 | 11.158% |
| `location` | 9 | Sydney | 111,520 | 11.152% |
| `industry` | 9 | AI | 111,803 | 11.180% |
| `company_size` | 4 | Small | 300,184 | 30.018% |
| `employment_type` | 4 | Part-Time | 250,700 | 25.070% |
| `work_mode` | 3 | Remote | 549,339 | 54.934% |
| `recruiter_email_type` | 2 | Corporate | 749,433 | 74.943% |

20 giá trị hàng đầu của mỗi cột categorical, bao gồm cả giá trị thiếu, được liệt kê trong `categorical_top_values.txt`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- `posting_date` có cardinality cao (3,287 giá trị phân biệt). Với một star schema thì đây là câu hỏi về thiết kế Dimension - Dimension riêng, thuộc tính degenerate hay được nhóm lại - chứ không phải một lỗi chất lượng dữ liệu.
- `company_name` có cardinality cao (535,938 giá trị phân biệt). Với một star schema thì đây là câu hỏi về thiết kế Dimension - Dimension riêng, thuộc tính degenerate hay được nhóm lại - chứ không phải một lỗi chất lượng dữ liệu.

## 6. Độ phủ của dữ liệu ngày tháng

**Dữ kiện quan sát được**

Các cột ứng viên date/time được phát hiện từ dtype của pandas và từ tên cột có chứa `date`, `time`, `year`, `timestamp`. Việc parse chỉ được thử trên một bản sao của các giá trị phân biệt; bản thân dataframe không bị chuyển đổi.

| Cột | dtype | Phát hiện qua | Tỷ lệ parse thành công | Min | Max | Không hợp lệ |
| --- | --- | --- | ---: | --- | --- | ---: |
| `posting_date` | str | tên cột | 100.00% | 2018-01-01 00:00:00 | 2026-12-31 00:00:00 | 0 |
| `recruiter_experience_years` | float64 | tên cột | 0.00% | - | - | 0 |
| `recruiter_response_time_hours` | float64 | tên cột | 0.00% | - | - | 0 |

- `posting_date` trải từ **2018-01-01 đến 2026-12-31**, trên 3,287 giá trị phân biệt đã parse được.

**Các vấn đề tiềm ẩn cần con người xem xét**

- `recruiter_experience_years` khớp với heuristic tên-dạng-date nhưng **không** phải là một date: dtype numeric chỉ khớp qua tên cột; các giá trị không mang dạng date (không phải số nguyên trong khoảng năm hợp lý), nên không thử parse - có khả năng là một duration/measure, cần con người xem xét. Được ghi lại để heuristic vẫn có thể audit được.
- `recruiter_response_time_hours` khớp với heuristic tên-dạng-date nhưng **không** phải là một date: dtype numeric chỉ khớp qua tên cột; các giá trị không mang dạng date (không phải số nguyên trong khoảng năm hợp lý), nên không thử parse - có khả năng là một duration/measure, cần con người xem xét. Được ghi lại để heuristic vẫn có thể audit được.
- Các tin có ngày ở tương lai và ở quá khứ xa không bị lọc bỏ. Khoảng giá trị ở trên nên được đối chiếu với giai đoạn mà dataset dự kiến bao phủ; một ngày sau ngày extract sẽ là một bất thường thực sự. Chưa xử lý.
- Một cột date dùng được là điều quan trọng với Data Warehouse: nó là cơ sở tự nhiên cho một Dimension thời gian và cho mọi phép roll-up ở grain ngày, nên độ phủ và độ mịn của nó đáng được kiểm tra một cách có chủ đích.

## 7. Chất lượng text và chuỗi

**Dữ kiện quan sát được**

| Cột | Có whitespace đệm | Chuỗi rỗng | Chỉ gồm whitespace | Phân biệt | Phân biệt (không phân biệt hoa/thường) | Phân biệt (đã trim + không phân biệt hoa/thường) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `posting_date` | 0 | 0 | 0 | 3,287 | 3,287 | 3,287 |
| `internship_title` | 0 | 0 | 0 | 9 | 9 | 9 |
| `employment_type` | 0 | 0 | 0 | 4 | 4 | 4 |
| `work_mode` | 0 | 0 | 0 | 3 | 3 | 3 |
| `industry` | 0 | 0 | 0 | 9 | 9 | 9 |
| `location` | 0 | 0 | 0 | 9 | 9 | 9 |
| `company_name` | 0 | 0 | 0 | 535,938 | 535,938 | 535,938 |
| `company_size` | 0 | 0 | 0 | 4 | 4 | 4 |
| `recruiter_email_type` | 0 | 0 | 0 | 2 | 2 | 2 |

Không giá trị chuỗi nào bị trim, chuyển thành chữ thường hay biến đổi cách nào khác; các số đếm không phân biệt hoa/thường được lấy từ một bản sao tạm thời của các giá trị phân biệt.

**Các vấn đề tiềm ẩn cần con người xem xét**

- Không phát hiện whitespace đệm, chuỗi rỗng, giá trị chỉ gồm whitespace hay bản trùng khác nhau về chữ hoa/thường nào trong bất kỳ cột text nào.
- Các số đếm về biến thể hoa/thường và whitespace chỉ cho thấy các bản trùng *tiềm năng*. Hai cách viết khác nhau về chữ hoa/thường vẫn có thể là hai thực thể thực khác nhau; điều này cần một quyết định của con người, đặc biệt với tên công ty và tên địa điểm.

## 8. Các cột có thể là identifier

**Dữ kiện quan sát được**

Một cột chỉ được báo cáo là unique key *tiềm năng* khi nó không có giá trị thiếu nào và số giá trị phân biệt của nó bằng số dòng. **Script này không khai báo primary key nào.**

- Số cột thỏa phép kiểm tra tính duy nhất nghiêm ngặt: **0**.
- Số cột gần-duy nhất (tỷ lệ >= 0.99) nhưng không duy nhất nghiêm ngặt: **0**.

Năm cột có cardinality cao nhất:

| Cột | Phân biệt | Số null | Tỷ lệ duy nhất | Unique key tiềm năng |
| --- | ---: | ---: | ---: | --- |
| `company_name` | 535,938 | 0 | 0.535938 | False |
| `stipend` | 73,830 | 10,000 | 0.073830 | False |
| `registration_fee` | 4,951 | 0 | 0.004951 | False |
| `job_description_length` | 3,946 | 0 | 0.003946 | False |
| `posting_date` | 3,287 | 0 | 0.003287 | False |

Mọi cột đều được liệt kê trong `potential_key_analysis.csv`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- **Không cột đơn nào định danh duy nhất một dòng.** Ở trạng thái được load, dataset không có natural primary key. Với Data Warehouse, điều đó nghĩa là sẽ phải đưa vào một surrogate key, hoặc thống nhất một business key dạng tổ hợp sau khi kiểm tra. Quyết định đó được cố ý để mở ở đây.

## 9. Các cột đáng được con người xem xét

Được liệt kê vì một phép đo đã đặt ra câu hỏi, không phải vì đã biết có gì sai. Không có mục nào ở đây là đề xuất xóa hay thay đổi một cột.

| Cột | Lý do được liệt kê |
| --- | --- |
| `posting_date` | cardinality cao (3,287 giá trị phân biệt); khoảng ngày 2018-01-01 đến 2026-12-31 cần được validation đối chiếu với kỳ báo cáo dự kiến |
| `company_name` | cardinality cao (535,938 giá trị phân biệt) |
| `company_age` | 1.000% thiếu |
| `linkedin_presence` | dtype numeric nhưng chỉ có 2 giá trị phân biệt - flag hay measure? |
| `website_available` | dtype numeric nhưng chỉ có 2 giá trị phân biệt - flag hay measure? |
| `verification_status` | dtype numeric nhưng chỉ có 2 giá trị phân biệt - flag hay measure? |
| `stipend` | 1.000% thiếu |
| `unrealistic_salary_flag` | dtype numeric nhưng chỉ có 1 giá trị phân biệt - flag hay measure? |
| `payment_required` | dtype numeric nhưng chỉ có 2 giá trị phân biệt - flag hay measure? |
| `grammatical_errors` | 1.19% outlier theo IQR |
| `fake_certificate_offer` | dtype numeric nhưng chỉ có 2 giá trị phân biệt - flag hay measure? |
| `recruiter_experience_years` | khớp quy tắc tên-dạng-date nhưng không phải cột date |
| `suspicious_email_domain` | dtype numeric nhưng chỉ có 2 giá trị phân biệt - flag hay measure? |
| `recruiter_response_time_hours` | khớp quy tắc tên-dạng-date nhưng không phải cột date |
| `social_media_presence` | dtype numeric nhưng chỉ có 2 giá trị phân biệt - flag hay measure? |
| `trust_signal_score` | 1.000% thiếu |
| `is_fake_posting` | dtype numeric nhưng chỉ có 2 giá trị phân biệt - flag hay measure? |

## 10. Những gì báo cáo này cố ý không làm

- Nó không làm sạch, impute, chuẩn hóa, loại trùng, đổi kiểu hay bỏ bất cứ thứ gì.
- Nó không đề xuất loại bỏ hay thay đổi bất kỳ cột nào.
- Nó không thực hiện tiền xử lý ML nào: không encoding, scaling, TF-IDF, resampling, stemming hay lemmatisation.
- Nó không khai báo primary key.
- Nó không ghi vào `data/raw/`, thư mục này vẫn giống hệt đến từng byte.
