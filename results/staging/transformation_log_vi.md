# Nhật ký Biến đổi &mdash; Tầng Staging

| Hạng mục | Giá trị |
| --- | --- |
| Thời điểm tạo | 2026-09-23 17:23:06 |
| Script | `scripts/build_staging.py` |
| Đầu vào | `data/raw/fake_internship_detection_dataset.csv` |
| sha256 đầu vào | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Số dòng vào / ra | 1,000,000 / 1,000,000 |
| Số cột vào / ra | 33 / 35 |
| Thời gian chạy | 68.0s |

Mọi quy tắc được dẫn chiếu dưới đây đều lấy từ [docs/cleaning_rules_vi.md](../../docs/cleaning_rules_vi.md). **Không có quyết định làm sạch mới nào được đưa ra ở tầng này** và không có ý nghĩa nghiệp vụ nào bị diễn giải lại vượt ra ngoài bằng chứng đã được tài liệu hóa.

---

## 1. Các biến đổi đã thực hiện

Đúng ba biến đổi. Không có gì khác bị thay đổi.

### 1.1 Phân tích cú pháp và chuẩn hóa `posting_date`

| Hạng mục | Chi tiết |
| --- | --- |
| Quy tắc | R4.2.1, R4.2.2 |
| Hành động | Được parse bằng định dạng tường minh `%Y-%m-%d` thành một date thực sự, rồi ghi trở lại dưới dạng ISO `YYYY-MM-DD`. |
| Số lần parse thất bại | 0 &mdash; các trường hợp thất bại được báo cáo, không bao giờ bị coerce, gán giá trị mặc định hay loại bỏ (R4.2.3) |
| Khoảng giá trị thu được | 2018-01-01 đến 2026-12-31 |
| Số date phân biệt | 3,287 |
| Số dòng bị loại bỏ | 0 |

Nguồn vốn đã ghi cột này ở dạng `YYYY-MM-DD`, nên bước này thay đổi **cách biểu diễn** (từ text sang date có kiểu rồi trở lại text ISO) chứ không thay đổi ý nghĩa: không date nào bị dịch chuyển, đổi mốc gốc hay diễn giải lại, và không dòng nào có ngày ở tương lai bị loại bỏ (R4.2.4).

### 1.2 Thêm `source_row_id`

| Hạng mục | Chi tiết |
| --- | --- |
| Quy tắc | R4.1.1 &ndash; R4.1.4 |
| Hành động | Số nguyên tuần tự được gán theo đúng thứ tự gốc trong CSV, trước mọi phép lọc, sắp xếp hay biến đổi. |
| Khoảng giá trị | 1 đến 1,000,000, liên tục |
| Số giá trị phân biệt / số null | 1,000,000 / 0 |
| Số chunk đã đi qua | 10 &mdash; bộ đếm là toàn cục và không bao giờ bị reset theo từng chunk |
| Có thêm vào file raw không | **Không.** Chỉ ở staging (R4.1.3). |

**Đây là một định danh phục vụ data lineage ở tầng staging, không phải natural key hay business key.** Quá trình profiling không tìm thấy cột đơn nào là duy nhất và cũng không tìm thấy tổ hợp nào là duy nhất trong 33 trường nguồn, nên một surrogate key là cách duy nhất để định địa chỉ một dòng riêng lẻ. Nó chỉ có ý nghĩa khi đi kèm sha256 của file nguồn, không được dùng để join giữa các lần extract khác nhau, và không mang ý nghĩa thứ tự phân tích nào.

### 1.3 Thêm `is_future_posting`

| Hạng mục | Chi tiết |
| --- | --- |
| Quy tắc | R4.2.5, R4.2.6 |
| Định nghĩa | `1` khi `posting_date > 2026-09-23`, ngược lại `0` |
| Ngày tham chiếu | **2026-09-23** &mdash; một hằng số cố định đã được tài liệu hóa, không bao giờ lấy từ đồng hồ hệ thống |
| Số dòng được gắn cờ | 30,246 (3.0246%) |
| Số dòng bị loại bỏ | 0 &mdash; cờ này đánh dấu, nó không lọc |

Mốc cắt được ghim cố định để đầu ra có thể tái lập: nếu tính cờ này từ ngày hiện tại thì số dòng được gắn cờ sẽ trôi đi ở mỗi lần chạy và không thể so sánh được hai lần load nào với nhau. Con số kỳ vọng 30,246 **chỉ** xuất hiện như một assertion hậu biến đổi trong [staging_validation_vi.md](staging_validation_vi.md); nó không phải là đầu vào của quy tắc.

### 1.4 Hiện thực hóa datatype (không phải thay đổi giá trị)

Việc định kiểu quyết định cách các giá trị được biểu diễn, không phải ý nghĩa của chúng. Ghi lại ở đây cho đầy đủ:

- `company_age` và `stipend` dùng kiểu integer nullable của pandas (`Int64`). Quá trình audit đo được **0 giá trị non-null không nguyên** ở cả hai cột, nên không mất độ chính xác. NULL được giữ nguyên là NULL và **không bao giờ** bị thay bằng zero. Do đó CSV được ghi ra hiển thị `23` ở nơi mà phép đọc dạng float hiển thị `23.0`.
- `recruiter_experience_years`, `recruiter_response_time_hours`, `trust_signal_score` và `fraud_score` giữ độ chính xác một chữ số thập phân dưới dạng `float64`. Chúng **không** bị làm tròn thành số nguyên.
- Chín trường binary vẫn giữ là integer `0`/`1`.
- Tám cột text vẫn giữ là text, nguyên văn.
- Datatype SQL dự kiến cho từng cột được ghi trong [staging_column_profile.csv](staging_column_profile.csv), vì một file CSV không mang theo metadata về datatype.

---

## 2. Các biến đổi CỐ Ý KHÔNG thực hiện

Mỗi mục đều đã được xem xét và bị loại bỏ dựa trên bằng chứng đã tài liệu hóa. Mục này tồn tại để người đọc sau này phân biệt được *đã quyết định không làm* với *bị bỏ sót*.

| Không thực hiện | Lý do |
| --- | --- |
| **Không imputation** | 10,000 giá trị null ở mỗi cột `company_age`, `stipend` và `trust_signal_score` đều được giữ nguyên. Không dùng mean, median, mode, zero, forward/backward fill hay điền dựa trên mô hình. Việc impute sẽ tạo ra những giá trị mà nguồn không chứa và sẽ làm sai lệch mọi phép tổng hợp phía sau. |
| **Không xóa dòng** | Giữ toàn bộ 1,000,000 dòng. Không dòng nào bị loại bỏ vì thiếu dữ liệu, vì có ngày ở tương lai, hay vì là outlier. |
| **Không xóa cột** | Giữ toàn bộ 33 cột nguồn, bao gồm `unrealistic_salary_flag` (hằng số `0` trong lần extract này) và cả hai phía của hai cặp dư thừa. Việc bỏ một cột là quyết định thuộc dimensional modelling, được cố ý hoãn lại. |
| **Không loại trùng** | Tìm thấy 0 bản trùng khớp chính xác và dữ kiện này được kiểm chứng lại sau staging, **chỉ trên 33 trường nguồn gốc**. `source_row_id` và `is_future_posting` bị loại khỏi phép kiểm tra đó vì `source_row_id` theo định nghĩa sẽ làm mọi dòng trở nên duy nhất. |
| **Không mapping hay gộp category** | `internship_title`, `employment_type`, `work_mode`, `industry`, `location`, `company_name`, `company_size` và `recruiter_email_type` được giữ nguyên văn. |
| **Không mã hóa thứ tự (ordinal) cho `company_size`** | Cột này vẫn là categorical. Miền giá trị trộn một nhãn về độ trưởng thành (`Startup`) với các nhãn về quy mô (`Small`, `Medium`, `Enterprise`), nên không chứng minh được `Startup` thuộc một thang quy mô và không thể biện minh cho bất kỳ thứ hạng ordinal nào từ bằng chứng hiện có. |
| **Không chuyển đổi chữ hoa/thường, không cắt khoảng trắng, không chuẩn hóa whitespace** | Đo được 0 giá trị có khoảng trắng đệm, 0 chuỗi rỗng, 0 giá trị chỉ gồm whitespace, 0 bản trùng khác nhau về chữ hoa/thường. Không có lỗi nào cần sửa, và một phép `TRIM`/`LOWER` vô điều kiện sẽ che đi thay đổi trong hành vi của nguồn thay vì làm nó lộ ra. Chất lượng text được kiểm tra lại và **báo cáo**, không sửa chữa. |
| **Không scaling hay standardisation** | Không min-max, z-score, log hay bất kỳ phép tái tỉ lệ nào khác. Staging giữ nguyên đơn vị của nguồn. |
| **Không loại bỏ, chặn ngưỡng hay winsorize outlier** | Các phát hiện theo IQR chỉ mang tính chẩn đoán. Không giá trị nào bị loại bỏ, cắt hay thay thế. |
| **Không chuyển đổi tiền tệ** | Nguồn không tài liệu hóa đơn vị tiền tệ nào cho `stipend` hay `registration_fee`. |
| **Không chuẩn hóa hay phân dải (banding) `stipend`** | Không quy đổi theo năm, không đổi mốc gốc giữa các địa điểm, không chia dải. Xem phần hạn chế bên dưới. |
| **Không suy dẫn nhãn** | `is_fake_posting` **không** được suy ra từ `fraud_score`. Audit phát hiện hai đại lượng này bất đồng tại `fraud_score = 50`, nên nhãn không phải là một hàm của điểm số. Cả hai được giữ độc lập với nhau. |
| **Không suy dẫn từ các invariant đã được validation** | `payment_required` không được tính lại từ `registration_fee`, và `suspicious_email_domain` không được tính lại từ `recruiter_email_type`. Các quan hệ này **chỉ được validation**. |
| **Không cân bằng lại lớp** | Phân phối của `is_fake_posting` không bị can thiệp. |
| **Không encoding** | Không one-hot, ordinal, target hay hash encoding. Việc đó thuộc bước modelling, không thuộc staging. |
| **Không làm giàu dữ liệu** | Không làm giàu theo địa lý, ngành hay công ty; không fuzzy matching hay entity resolution trên `company_name`. Mẫu `<Họ> <Hậu tố>` xuất hiện lặp lại có nghĩa là sự tương đồng về tên không được coi là đồng nhất về danh tính công ty. |
| **Không thay đổi file raw** | `data/raw/` là chỉ đọc. Không có gì được ghi, ghi lại hay đóng dấu thời gian lại ở đó, và `source_row_id` không được thêm vào đó. |

---

## 3. Hạn chế được chuyển tiếp &mdash; ngữ nghĩa của `stipend`

Nguồn không tài liệu hóa **đơn vị tiền tệ** cũng như **kỳ trả lương** cho `stipend`. Các giá trị trải từ 2,000 đến 110,428 trên chín địa điểm thuộc các vùng tiền tệ khác nhau, và không có gì trong lần extract này cho biết một con số là theo tháng hay theo năm.

Đây là vấn đề **chưa được giải quyết**, không phải đã ngã ngũ. Do đó staging giữ nguyên các con số như được cung cấp và không thực hiện chuyển đổi, quy đổi theo năm, chuẩn hóa giữa các địa điểm hay phân dải nào. Cho đến khi đơn vị tiền tệ và kỳ trả lương được xác lập từ hệ thống nguồn, các giá trị `stipend` từ những địa điểm khác nhau **không được mặc định là có thể so sánh trực tiếp**, và việc tổng hợp `stipend` xuyên địa điểm sẽ không có cơ sở vững chắc.
