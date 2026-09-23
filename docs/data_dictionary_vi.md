# Data Dictionary — `fake_internship_detection_dataset.csv`

| Hạng mục | Giá trị |
| --- | --- |
| File nguồn | `data/raw/fake_internship_detection_dataset.csv` |
| sha256 nguồn | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Số dòng | 1,000,000 |
| Số cột nguồn | 33 |
| Ngày audit / tham chiếu | **2026-09-23** |
| Bằng chứng | `results/profiling/` (tạo lúc 2026-09-23 16:35:25), `results/audit/` (tạo lúc 2026-09-23 16:55:24) |
| Trạng thái của file raw | Bất biến. Không bao giờ bị ghi vào. Xem [cleaning_rules_vi.md](cleaning_rules_vi.md). |

Tài liệu này chỉ mô tả **33 cột nguồn gốc**. Hai cột bổ sung được tạo ra ở tầng
staging và được tài liệu hóa riêng ở
[§4 Các cột suy dẫn ở tầng staging](#4-các-cột-suy-dẫn-ở-tầng-staging); chúng
**không** tồn tại trong file raw.

Mọi con số trong tài liệu này là một phép đo lấy từ các đầu ra profiling và audit
đã liệt kê ở trên, hoặc là một lần kiểm chứng lại đối chiếu với file CSV raw.
Không có ý nghĩa nghiệp vụ nào được khẳng định vượt ra ngoài những gì mà tên cột,
miền giá trị quan sát được và bằng chứng audit hỗ trợ. Ở những nơi không thể xác
lập được ý nghĩa dự kiến của một cột từ dữ liệu, tài liệu này nói rõ điều đó thay
vì phỏng đoán.

---

## 1. Các quy ước dùng trong tài liệu này

**Phân loại ngữ nghĩa** là một trong các loại sau:

| Phân loại | Ý nghĩa trong project này |
| --- | --- |
| Identifier | Định danh duy nhất một dòng hoặc một thực thể nghiệp vụ. |
| Date | Một ngày dương lịch, cơ sở cho một Dimension thời gian. |
| Ứng viên Dimension | Giá trị mô tả có cardinality thấp đến cao, phù hợp để slicing. |
| Thuộc tính mô tả | Mô tả một thực thể nhưng khó có khả năng được dùng để slicing trực tiếp. |
| Ứng viên measure | Đại lượng numeric phù hợp để tổng hợp trong một Fact table. |
| Flag | Chỉ báo mang giá trị boolean, nghiêm ngặt trong `{0,1}`. |
| Outcome | Kết quả được gán nhãn mà Data Warehouse được lập ra để phân tích. |

Đây là **các ứng viên, không phải các quyết định**. Cột nào trở thành thuộc tính
Dimension, measure trong Fact hay một Dimension degenerate được quyết định trong
bước dimensional modelling, không phải ở đây.

**Không cột nguồn nào là Identifier.** Phân tích key trong bước profiling
(`results/profiling/potential_key_analysis.csv`) đã kiểm tra cả 33 cột cùng các
tổ hợp: 0 cột thỏa phép kiểm tra tính duy nhất, và 0 cột gần-duy nhất
(tỷ lệ ≥ 0.99). Cột đặc trưng nhất, `company_name`, có 53.5938% giá trị duy
nhất. Do đó định danh dòng được cung cấp bởi `source_row_id` suy dẫn ở tầng
staging (§4).

**% thiếu** được đo trên toàn bộ 1,000,000 dòng. Các cột text không chứa chuỗi
rỗng và không chứa giá trị chỉ gồm whitespace, nên với những cột đó thì số null
mà pandas đếm là toàn bộ bức tranh về việc thiếu dữ liệu
(`results/profiling/string_quality.csv`).

**Kiểu staging dự kiến** được viết bằng SQL chung. `NULL` / `NOT NULL` phản ánh
điều mà dữ liệu thực sự cho phép, không phải một sự ưa thích. Các kiểu được định
cỡ từ những khoảng giá trị quan sát được và từ một lần kiểm chứng lại trực tiếp độ
chính xác thập phân đối chiếu với file CSV raw; `company_age` và `stipend` được
pandas serialise với phần `.0` ở cuối nhưng chứa **không** giá trị không nguyên
nào trên 1,000,000 dòng, nên chúng được định kiểu là integer.

---

## 2. Tổng hợp toàn bộ 33 cột nguồn

| # | Cột | Kiểu nguồn (khi load) | Phân loại ngữ nghĩa | % thiếu | Phân biệt | Kiểu staging dự kiến |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | `posting_date` | str (`YYYY-MM-DD`) | Date | 0.0000% | 3,287 | `DATE NOT NULL` |
| 2 | `internship_title` | str | Ứng viên Dimension | 0.0000% | 9 | `VARCHAR(32) NOT NULL` |
| 3 | `employment_type` | str | Ứng viên Dimension | 0.0000% | 4 | `VARCHAR(16) NOT NULL` |
| 4 | `work_mode` | str | Ứng viên Dimension | 0.0000% | 3 | `VARCHAR(16) NOT NULL` |
| 5 | `industry` | str | Ứng viên Dimension | 0.0000% | 9 | `VARCHAR(24) NOT NULL` |
| 6 | `location` | str | Ứng viên Dimension | 0.0000% | 9 | `VARCHAR(24) NOT NULL` |
| 7 | `company_name` | str | Ứng viên Dimension | 0.0000% | 535,938 | `VARCHAR(64) NOT NULL` |
| 8 | `company_size` | str | Ứng viên Dimension | 0.0000% | 4 | `VARCHAR(16) NOT NULL` |
| 9 | `company_age` | float64 | Ứng viên measure | 1.0000% | 39 | `SMALLINT NULL` |
| 10 | `linkedin_presence` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 11 | `website_available` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 12 | `domain_age_months` | int64 | Ứng viên measure | 0.0000% | 500 | `SMALLINT NOT NULL` |
| 13 | `verification_status` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 14 | `stipend` | float64 | Ứng viên measure | 1.0000% | 73,830 | `INTEGER NULL` |
| 15 | `unrealistic_salary_flag` | int64 | Flag (hằng số) | 0.0000% | 1 | `SMALLINT NOT NULL` |
| 16 | `payment_required` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 17 | `registration_fee` | int64 | Ứng viên measure | 0.0000% | 4,951 | `INTEGER NOT NULL` |
| 18 | `job_description_length` | int64 | Ứng viên measure | 0.0000% | 3,946 | `SMALLINT NOT NULL` |
| 19 | `grammatical_errors` | int64 | Ứng viên measure | 0.0000% | 15 | `SMALLINT NOT NULL` |
| 20 | `vague_description_score` | int64 | Ứng viên measure | 0.0000% | 101 | `SMALLINT NOT NULL` |
| 21 | `urgency_score` | int64 | Ứng viên measure | 0.0000% | 101 | `SMALLINT NOT NULL` |
| 22 | `keyword_spam_score` | int64 | Ứng viên measure | 0.0000% | 101 | `SMALLINT NOT NULL` |
| 23 | `fake_certificate_offer` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 24 | `recruiter_experience_years` | float64 | Ứng viên measure | 0.0000% | 183 | `DECIMAL(3,1) NOT NULL` |
| 25 | `recruiter_email_type` | str | Ứng viên Dimension | 0.0000% | 2 | `VARCHAR(16) NOT NULL` |
| 26 | `suspicious_email_domain` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 27 | `recruiter_response_time_hours` | float64 | Ứng viên measure | 0.0000% | 595 | `DECIMAL(3,1) NOT NULL` |
| 28 | `social_media_presence` | int64 | Flag | 0.0000% | 2 | `SMALLINT NOT NULL` |
| 29 | `emotional_manipulation_score` | int64 | Ứng viên measure | 0.0000% | 101 | `SMALLINT NOT NULL` |
| 30 | `phishing_language_score` | int64 | Ứng viên measure | 0.0000% | 100 | `SMALLINT NOT NULL` |
| 31 | `trust_signal_score` | float64 | Ứng viên measure | 1.0000% | 1,001 | `DECIMAL(4,1) NULL` |
| 32 | `fraud_score` | float64 | Ứng viên measure | 0.0000% | 1,001 | `DECIMAL(4,1) NOT NULL` |
| 33 | `is_fake_posting` | int64 | Outcome | 0.0000% | 2 | `SMALLINT NOT NULL` |

`SMALLINT` được dùng cho chín flag thay vì một kiểu boolean thuần để quy tắc đã
được chấp thuận "giữ nguyên cách biểu diễn 0/1" được tôn trọng đúng theo nghĩa
chữ trong schema staging.

---

## 3. Chi tiết từng cột

### 3.1 Thời gian

#### `posting_date`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `str`, định dạng `YYYY-MM-DD` |
| Diễn giải nghiệp vụ | Ngày tin tuyển dụng thực tập được công bố. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 3,287 date phân biệt |
| Kiểu staging dự kiến | `DATE NOT NULL` |
| Phân loại ngữ nghĩa | Date |

**Quan sát về chất lượng dữ liệu**

- 100.00% giá trị parse được theo `%Y-%m-%d`; **0 giá trị không parse được** theo định dạng đó hay theo bất kỳ định dạng nào (audit §1).
- Khoảng giá trị: **2018-01-01 đến 2026-12-31**, một độ trải 3,286 ngày bao phủ 3,287 date phân biệt — tức là **mọi ngày dương lịch trong khoảng đều có dữ liệu**, không có ngày trống nào.
- Số dòng mỗi date: min 247, max 366, mean 304.2288, hệ số biến thiên 0.0558. Tỷ lệ theo ngày trong tuần chạy từ 14.2196%–14.3617% so với mức đều 14.2857%.
- **30,246 dòng (3.0246%) mang ngày đăng tin muộn hơn ngày tham chiếu audit 2026-09-23**, trên 99 date tương lai phân biệt: 2026-09 (2,195 dòng), 2026-10 (9,435), 2026-11 (9,195), 2026-12 (9,421). Trong số đó, 23,503 dòng được gán nhãn `is_fake_posting = 0` và 6,743 dòng được gán nhãn 1 (22.2939%, so với tỷ lệ 22.1958% trên toàn dataset).
- Không dòng nào nằm trước 2018-01-01.
- Cardinality cao so với các cột categorical khác, nhưng với một star schema thì đây là câu hỏi về thiết kế Dimension, không phải một lỗi.

**Hành động làm sạch**

- Parse thành một `DATE` thực sự; xuất ra dạng ISO `YYYY-MM-DD`. Mọi lần parse thất bại phải được báo cáo, không được âm thầm coerce.
- **Các dòng có ngày ở tương lai được giữ lại.** Chúng được gắn cờ bởi `is_future_posting` suy dẫn ở tầng staging (§4.2), không bị loại bỏ.
- Việc nạp dữ liệu đồng đều theo ngày và độ phủ dương lịch trọn vẹn được ghi lại như các quan sát về provenance (audit §12); chúng không được coi là lỗi chất lượng dữ liệu và không kích hoạt thay đổi nào.

---

### 3.2 Thuộc tính về vai trò và vị trí

Cả năm cột trong nhóm này đã được kiểm chứng là không có whitespace đệm, chuỗi
rỗng, giá trị chỉ gồm whitespace, ký tự non-ASCII, dấu cách đôi và bản trùng khác
nhau về chữ hoa/thường (`results/profiling/string_quality.csv`; số giá trị phân
biệt, số phân biệt không phân biệt hoa/thường, và số phân biệt sau khi
trim+không phân biệt hoa/thường đều giống hệt nhau với mọi cột). **Do đó giá trị
của chúng được giữ nguyên đúng như tìm thấy: không trim, không chuyển thành chữ
thường, không mapping category, không gộp category.**

#### `internship_title`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `str` |
| Diễn giải nghiệp vụ | Chức danh vai trò được quảng cáo cho kỳ thực tập. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 9 giá trị phân biệt (độ dài tối đa 21 ký tự) |
| Kiểu staging dự kiến | `VARCHAR(32) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên Dimension |

**Quan sát về chất lượng dữ liệu**

- Miền giá trị đầy đủ: `Marketing Intern` (11.158%), `Cloud Engineer` (11.148%), `AI Research Intern` (11.144%), `Cybersecurity Analyst` (11.140%), `UI/UX Designer` (11.139%), `Backend Developer` (11.093%), `ML Engineer` (11.069%), `Frontend Developer` (11.059%), `Data Science Intern` (11.050%).
- Gần đồng đều: độ lệch lớn nhất so với tỷ lệ đều 11.1111% là 0.0609 pp. Chỉ được ghi lại như một quan sát về provenance.
- Chỉ 4 trong 9 chức danh có chứa từ "Intern"; cột này là một nhãn vai trò, và việc năm chức danh còn lại có phải là vai trò thực tập hay không thì dữ liệu không xác lập được.

**Hành động làm sạch** — Giữ nguyên văn. Không biến đổi.

#### `employment_type`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `str` |
| Diễn giải nghiệp vụ | Cơ sở hợp đồng theo đó vai trò được đề nghị. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 4 giá trị phân biệt (độ dài tối đa 10 ký tự) |
| Kiểu staging dự kiến | `VARCHAR(16) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên Dimension |

**Quan sát về chất lượng dữ liệu**

- Miền giá trị đầy đủ: `Part-Time` (25.070%), `Internship` (25.000%), `Contract` (24.967%), `Full-Time` (24.963%).
- Gần đồng đều: độ lệch lớn nhất so với 25.0000% là 0.0700 pp.
- `employment_type = 'Internship'` chỉ áp dụng cho 25% số dòng dù mọi dòng đều là một tin tuyển thực tập theo chính cách đặt vấn đề của dataset. Hai khái niệm này không được dữ liệu dung hòa và không có phép dung hòa nào được thử.

**Hành động làm sạch** — Giữ nguyên văn. Không biến đổi.

#### `work_mode`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `str` |
| Diễn giải nghiệp vụ | Nơi công việc được thực hiện. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 3 giá trị phân biệt (độ dài tối đa 6 ký tự) |
| Kiểu staging dự kiến | `VARCHAR(16) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên Dimension |

**Quan sát về chất lượng dữ liệu**

- Miền giá trị đầy đủ: `Remote` (54.934%), `Hybrid` (25.053%), `Onsite` (20.014%).
- **Không** gần đồng đều (độ lệch 21.6006 pp so với một phép chia đều) — được ghi lại như bằng chứng đối lập trong mục về provenance.

**Hành động làm sạch** — Giữ nguyên văn. Không biến đổi.

#### `industry`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `str` |
| Diễn giải nghiệp vụ | Lĩnh vực mà công ty tuyển dụng được liệt vào. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 9 giá trị phân biệt (độ dài tối đa 13 ký tự) |
| Kiểu staging dự kiến | `VARCHAR(24) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên Dimension |

**Quan sát về chất lượng dữ liệu**

- Miền giá trị đầy đủ: `AI` (11.180%), `EdTech` (11.142%), `Healthcare` (11.136%), `FinTech` (11.102%), `E-Commerce` (11.102%), `Marketing` (11.101%), `Gaming` (11.097%), `Cybersecurity` (11.088%), `Software` (11.053%).
- Gần đồng đều: độ lệch lớn nhất so với 11.1111% là 0.0692 pp.

**Hành động làm sạch** — Giữ nguyên văn. Không biến đổi.

#### `location`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `str` |
| Diễn giải nghiệp vụ | Thành phố gắn với tin tuyển dụng. Việc đây là địa điểm của công ty, địa điểm làm việc hay địa điểm của nhà tuyển dụng thì **không** được dữ liệu xác lập. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 9 giá trị phân biệt (độ dài tối đa 13 ký tự) |
| Kiểu staging dự kiến | `VARCHAR(24) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên Dimension |

**Quan sát về chất lượng dữ liệu**

- Miền giá trị đầy đủ: `Sydney` (11.152%), `Toronto` (11.148%), `Bangalore` (11.144%), `San Francisco` (11.139%), `Berlin` (11.099%), `Dubai` (11.099%), `Singapore` (11.088%), `London` (11.075%), `New York` (11.056%).
- Gần đồng đều: độ lệch lớn nhất so với 11.1111% là 0.0552 pp.
- Cả chín giá trị đều chỉ là tên thành phố; không tồn tại cột quốc gia, khu vực hay mã quốc gia nào trong nguồn. Mọi phân cấp địa lý sẽ phải được thêm vào từ ngoài dataset này.
- 54.934% số dòng có `work_mode = 'Remote'`, nên không thể mặc định `location` là nơi công việc được thực hiện về mặt vật lý.

**Hành động làm sạch** — Giữ nguyên văn. Không biến đổi. Không làm giàu dữ liệu địa lý ở staging.

---

### 3.3 Thuộc tính về công ty

#### `company_name`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `str` (được đặt trong ngoặc kép trong CSV; giá trị có thể chứa dấu phẩy, ví dụ `"Russell, Medina and Evans"`) |
| Diễn giải nghiệp vụ | Tên công ty đã công bố tin tuyển dụng. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 535,938 giá trị phân biệt (53.5938% duy nhất; độ dài tối đa 38 ký tự) |
| Kiểu staging dự kiến | `VARCHAR(64) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên Dimension |

**Quan sát về chất lượng dữ liệu**

- Cột có cardinality cao nhất trong dataset, nhưng **không** phải một key: giá trị phổ biến nhất, `Smith PLC`, xuất hiện 1,248 lần, và 20 giá trị hàng đầu chỉ bao phủ 1.90% số dòng.
- Không có lỗi về whitespace, chữ hoa/thường, chuỗi rỗng hay non-ASCII; số giá trị phân biệt và số phân biệt sau khi trim+không phân biệt hoa/thường đều là 535,938.
- Các giá trị theo mẫu `<Họ> <Hậu tố>` (`Smith PLC`, `Smith and Sons`, `Smith Ltd`, `Smith Inc`, `Smith LLC`, `Smith Group`, `Johnson LLC`, …). Vì cùng một họ lặp lại qua nhiều hậu tố, **sự tương đồng về tên không được coi là đồng nhất về danh tính công ty**.
- **Dấu phẩy nhúng bên trong có nghĩa là file CSV phải được đọc bằng một parser CSV nhận biết dấu ngoặc kép.** Việc tách theo delimiter một cách ngây thơ sẽ đẩy lệch mọi trường sau `company_name` và đã được xác nhận trong quá trình làm việc này là làm hỏng các cột phía sau.
- Không có cột định danh công ty nào. Việc hai dòng cùng chia sẻ một `company_name` có trỏ tới cùng một công ty thực hay không thì không thể xác định từ dataset này.

**Hành động làm sạch** — Giữ nguyên văn. Không trim, không đổi chữ hoa/thường, không fuzzy matching, không entity resolution, không nhóm lại. Đọc bằng một parser CSV nhận biết dấu ngoặc kép.

#### `company_size`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `str` |
| Diễn giải nghiệp vụ | Quy mô của công ty tuyển dụng theo dải. Các ngưỡng số nhân sự nền tảng **không** được nguồn cung cấp. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 4 giá trị phân biệt (độ dài tối đa 10 ký tự) |
| Kiểu staging dự kiến | `VARCHAR(16) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên Dimension |

**Quan sát về chất lượng dữ liệu**

- Miền giá trị đầy đủ: `Small` (30.018%), `Startup` (29.986%), `Medium` (24.959%), `Enterprise` (15.036%).
- **Không** gần đồng đều (độ lệch 9.9640 pp).
- Bốn giá trị này không phải một thứ tự quy mô nghiêm ngặt: `Startup` mô tả độ trưởng thành của công ty trong khi ba giá trị còn lại mô tả quy mô. Do đó một thứ hạng ordinal sẽ là một giả định, không phải một dữ kiện, và **không thứ hạng nào bị áp đặt ở đây**.

**Hành động làm sạch** — Giữ nguyên văn. Không biến đổi, không mã hóa ordinal, không gộp category.

#### `company_age`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `float64` (được serialise với phần `.0` ở cuối; đã kiểm chứng **0 giá trị không nguyên** trên 1,000,000 dòng) |
| Diễn giải nghiệp vụ | Tuổi của công ty tính theo **năm**. |
| Thiếu | 10,000 (1.0000%) |
| Cardinality | 39 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 1 đến 39; mean 20.000174, std 11.252082, median 20, các tứ phân vị 10 / 20 / 30.
- Không có giá trị âm, không có zero, **0 outlier theo IQR**.
- Trong số 10,000 dòng có giá trị thiếu, 7,800 dòng được gán nhãn `is_fake_posting = 0` và 2,200 dòng được gán nhãn 1 — tỷ lệ gian lận 22.0000% so với 22.1978% ở các dòng có giá trị, một khoảng cách **-0.1978 pp**. Đây là bằng chứng cho thấy việc thiếu dữ liệu mang rất ít thông tin về nhãn; nó không phải là chứng minh.
- Việc thiếu dữ liệu **không** phải một lần rơi dữ liệu chung ở mức bản ghi: chỉ 88 dòng cũng thiếu `stipend` và 96 dòng cũng thiếu `trust_signal_score` (tính độc lập dự báo 100 cho mỗi trường hợp), và **không dòng nào thiếu cả ba**.
- Việc giá trị này thiếu mang tính cấu trúc (công ty không có tuổi được ghi nhận) hay là một lỗ hổng thu thập thì **không thể xác định từ dữ liệu**.
- Xem `domain_age_months` cho quan hệ về tuổi giữa các cột.

**Hành động làm sạch** — Giữ nguyên. Giá trị thiếu vẫn là `NULL`. **Không imputation dưới bất kỳ hình thức nào** (không mean, không median, không zero, không forward-fill). Không dòng nào bị bỏ vì khoảng trống này.

#### `domain_age_months`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Tuổi của domain web của công ty tính theo **tháng**. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 500 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 1 đến 500 tháng (0.1 đến 41.7 năm); mean 239.541209, std 135.737891, median 240.
- Không có giá trị âm, không có zero, **0 outlier theo IQR**.
- Tương quan với `company_age` khi quy về tháng: **Pearson r = 0.9940**.
- **469,297 dòng (46.9297% toàn bộ số dòng; 47.4037% trong số 990,000 dòng so sánh được) có `domain_age_months > company_age * 12`.** Mức vượt chạy từ 1 đến 73 tháng, median 10, mean 12.0821. Trong số các dòng đó tỷ lệ gian lận là 22.2137%, về cơ bản là mức nền của dataset.
- **Các dòng này dứt khoát không được coi là không hợp lệ.** Một domain có thể chính đáng có trước công ty đang dùng nó — domain được mua lại, việc đổi thương hiệu, domain đỗ (parked) và việc đăng ký bởi công ty mẹ đều tạo ra mẫu này. Sự lệch đơn vị (năm so với tháng) cũng có nghĩa là `company_age` là phép đo thô hơn, nên những mức vượt nhỏ là điều dự kiến chỉ từ việc làm tròn.

**Hành động làm sạch** — Giữ nguyên. **Không bản ghi nào bị sửa đổi, hiệu chỉnh hay loại bỏ trên cơ sở quan hệ này**; audit đã kết luận bằng chứng không đủ để gọi các dòng đó là không hợp lệ.

---

### 3.4 Thù lao và thanh toán

#### `stipend`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `float64` (được serialise với phần `.0` ở cuối; đã kiểm chứng **0 giá trị không nguyên** trên 1,000,000 dòng) |
| Diễn giải nghiệp vụ | Khoản trợ cấp được đề nghị cho kỳ thực tập. **Đơn vị tiền tệ và kỳ trả lương (theo tháng, theo năm, tổng) không được nguồn tài liệu hóa** và không thể suy ra từ dữ liệu. |
| Thiếu | 10,000 (1.0000%) |
| Cardinality | 73,830 giá trị phân biệt |
| Kiểu staging dự kiến | `INTEGER NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 2,000 đến 110,428; mean 35,066.20, std 14,830.06, median 34,984, các tứ phân vị 24,841 / 34,984 / 45,124.
- Không có giá trị âm, **không có zero** — nên zero không được dùng làm placeholder ở đây.
- 3,348 dòng (0.3348%) nằm trên ngưỡng trên 1.5×IQR là 75,548.50. Đây là một đuôi phải dài, điều bình thường với một phân phối về thù lao.
- Tỷ lệ gian lận trong số 10,000 dòng thiếu stipend: 21.9600%, so với 22.1982% ở nơi có giá trị — một khoảng cách **-0.2382 pp**, lớn nhất trong ba cột không đầy đủ và vẫn không đáng kể.
- Vì các dòng trải trên 9 thành phố thuộc các vùng tiền tệ khác nhau, việc tổng hợp `stipend` xuyên `location` mà không có đơn vị tiền tệ được tài liệu hóa sẽ cho ra một con số vô nghĩa. Được gắn cờ cho giai đoạn dimensional modelling; **không có phép chuyển đổi nào được thực hiện**.
- `unrealistic_salary_flag` là hằng số 0 và do đó không đánh dấu giá trị nào trong số này là bất thường.

**Hành động làm sạch** — Giữ nguyên. Giá trị thiếu vẫn là `NULL`. **Không imputation, không chặn ngưỡng, không winsorise, không scaling.** Không dòng nào bị bỏ.

#### `unrealistic_salary_flag`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Được dự kiến là một chỉ báo rằng mức thù lao quảng cáo là không hợp lý. **Quy tắc kích hoạt của nó là không rõ và không quan sát được trong lần extract này.** |
| Thiếu | 0 (0.0000%) |
| Cardinality | **1 giá trị phân biệt** |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Flag (hằng số) |

**Quan sát về chất lượng dữ liệu**

- **Hằng số: 0 ở cả 1,000,000 dòng.** Số lượng giá trị `1` là zero.
- Nghiêm ngặt trong `{0,1}`, không có null.
- Một cột hằng số không mang thông tin để slicing và sẽ tạo ra một Dimension degenerate chỉ có một thành viên.
- Audit **không** đề xuất loại bỏ: một giá trị là hằng số trong lần extract này vẫn có thể có ý nghĩa trong hệ thống nguồn, và một lần extract về sau có thể chứa các giá trị `1`.

**Hành động làm sạch** — **Giữ lại ở staging**, được bảo toàn dạng 0/1 và được validation. Được tài liệu hóa ở đây như một **ứng viên để loại khỏi Data Warehouse phân tích**; việc loại đó là một quyết định thuộc dimensional modelling và được cố ý hoãn lại.

#### `payment_required`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Cho biết ứng viên bị yêu cầu trả tiền để ứng tuyển hoặc để nhận vai trò. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 2 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Flag |

**Quan sát về chất lượng dữ liệu**

- `0`: 900,095 dòng (90.0095%); `1`: 99,905 dòng (9.9905%). Nghiêm ngặt trong `{0,1}`, không có null.
- **Hoàn toàn dư thừa với `registration_fee` trên lần extract này.** Trên cả 1,000,000 dòng: 0 dòng có `payment_required = 0` kèm phí dương, và 0 dòng có `payment_required = 1` kèm phí bằng zero. Invariant `payment_required == (registration_fee > 0)` đúng một cách chính xác. Xem §5.1.

**Hành động làm sạch** — Giữ nguyên cách biểu diễn 0/1. **Cả hai cột đều được giữ ở staging; không cột nào được suy ra từ cột kia.** Invariant được validation lại ở mọi lần load. Sự dư thừa được tài liệu hóa để dimensional model xem xét, không được giải quyết ở đây.

#### `registration_fee`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Khoản phí mà ứng viên được yêu cầu trả. Đơn vị tiền tệ **không** được nguồn tài liệu hóa. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 4,951 giá trị phân biệt |
| Kiểu staging dự kiến | `INTEGER NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0 đến 4,999; mean 252.083069, std 881.467489, median 0.
- **900,095 dòng (90.0095%) bằng zero**, và ở đây zero là **có ý nghĩa, không phải một placeholder**: nó có nghĩa là không có phí nào được yêu cầu, điều mà sự khớp chính xác với `payment_required = 0` xác nhận.
- Trong số 99,905 dòng có thu phí: min 50, p25 1,284, median 2,520, p75 3,763, max 4,999, mean 2,523.23, std 1,430.61. Không có giá trị zero nào xuất hiện trong nhóm này.
- Không có giá trị âm.
- Con số được báo cáo "99,905 outlier theo IQR (9.9905%)" là một **sản phẩm phụ**: Q1 và Q3 đều bằng 0, nên khoảng tứ phân vị thu về 0 và mọi giá trị khác zero đều bị gắn cờ theo cách cấu tạo. Hãy đọc con số đó là "số dòng có phí khác zero", **không** phải là các quan sát cực trị.

**Hành động làm sạch** — Giữ nguyên mọi giá trị, kể cả các giá trị zero. **Không xử lý outlier** — ngưỡng IQR vô nghĩa với cột này. Validation `registration_fee >= 0` và invariant của `payment_required`.

---

### 3.5 Chất lượng nội dung tin tuyển dụng

#### `job_description_length`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Độ dài của văn bản mô tả công việc. **Đơn vị (ký tự hay từ) không được tài liệu hóa**; khoảng 100–5,000 nhất quán với đơn vị ký tự. Bản thân văn bản mô tả **không** có trong dataset. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 3,946 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 100 đến 5,000; mean 1,799.538324, std 598.563156, median 1,799, các tứ phân vị 1,395 / 1,799 / 2,203.
- Không có giá trị âm, không có zero. Mức sàn đúng bằng 100 và mức trần đúng bằng 5,000 gợi ý các biên đã được áp dụng ở phía trên.
- 7,040 dòng (0.7040%) nằm ngoài các ngưỡng 1.5×IQR là 183 / 3,415.

**Hành động làm sạch** — Giữ nguyên. Không chặn ngưỡng, không scaling. Không có xử lý văn bản nào là khả thi hay cần thiết: **không tồn tại cột văn bản tự do nào trong dataset này**.

#### `grammatical_errors`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Số lỗi ngữ pháp được phát hiện trong tin tuyển dụng. Phương pháp phát hiện **không** được tài liệu hóa. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 15 giá trị phân biệt (các giá trị 0–14) |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0 đến 14; mean 2.998825, std 1.731828, median 3.
- 49,716 dòng (4.9716%) bằng zero. Một giá trị zero ở đây hợp lý là một phép đo thực (không tìm thấy lỗi nào), nhưng không thể phân biệt nó với một placeholder chỉ bằng dữ liệu.
- **Tỷ lệ outlier theo IQR lớn nhất trong mọi cột của dataset: 11,891 dòng (1.1891%)**, nằm trên ngưỡng trên là 7. Xét việc cột này là một phép đếm nhỏ có biên, đây là một đuôi dài thực sự chứ không phải một lỗi.

**Hành động làm sạch** — Giữ nguyên. **Không loại bỏ hay chặn ngưỡng outlier.**

#### `vague_description_score`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Điểm cho mức độ mơ hồ của phần mô tả trong tin tuyển dụng. Cách suy dẫn **không** được tài liệu hóa. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 101 giá trị phân biệt (mọi số nguyên 0–100) |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0 đến 100, nằm hoàn toàn trong biên: **0 giá trị dưới 0, 0 giá trị trên 100**.
- Mean 30.132072, std 18.814980, median 30; 73,938 dòng (7.3938%) bằng zero.
- 3,472 dòng (0.3472%) nằm ngoài các ngưỡng IQR.

**Hành động làm sạch** — Giữ nguyên. Validation `0 <= giá trị <= 100`.

#### `urgency_score`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Điểm cho ngôn ngữ mang tính cấp bách/gây áp lực trong tin tuyển dụng. Cách suy dẫn **không** được tài liệu hóa. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 101 giá trị phân biệt (mọi số nguyên 0–100) |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0 đến 100, nằm hoàn toàn trong biên: 0 giá trị ngoài khoảng.
- Mean 40.047191, std 23.612605, median 39; 59,153 dòng (5.9153%) bằng zero.
- **0 outlier theo IQR** — cột trải rộng nhất trong các điểm về nội dung.

**Hành động làm sạch** — Giữ nguyên. Validation `0 <= giá trị <= 100`.

#### `keyword_spam_score`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Điểm cho việc nhồi nhét từ khóa trong tin tuyển dụng. Cách suy dẫn **không** được tài liệu hóa. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 101 giá trị phân biệt (mọi số nguyên 0–100) |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0 đến 100, nằm hoàn toàn trong biên: 0 giá trị ngoài khoảng.
- Mean 25.573860, std 18.116422, median 25; 114,428 dòng (11.4428%) bằng zero.
- 3,451 dòng (0.3451%) nằm ngoài các ngưỡng IQR.

**Hành động làm sạch** — Giữ nguyên. Validation `0 <= giá trị <= 100`.

#### `emotional_manipulation_score`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Điểm cho ngôn ngữ mang tính thao túng cảm xúc trong tin tuyển dụng. Cách suy dẫn **không** được tài liệu hóa. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 101 giá trị phân biệt (mọi số nguyên 0–100) |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0 đến 100, nằm hoàn toàn trong biên: 0 giá trị ngoài khoảng.
- Mean 25.563839, std 18.129998, median 24; 114,946 dòng (11.4946%) bằng zero.
- 3,516 dòng (0.3516%) nằm ngoài các ngưỡng IQR.

**Hành động làm sạch** — Giữ nguyên. Validation `0 <= giá trị <= 100`.

#### `phishing_language_score`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Điểm cho ngôn ngữ mang kiểu phishing trong tin tuyển dụng. Cách suy dẫn **không** được tài liệu hóa. |
| Thiếu | 0 (0.0000%) |
| Cardinality | **100 giá trị phân biệt** — một số nguyên trong 0–100 không được quan sát thấy |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0 đến 100, nằm hoàn toàn trong biên: 0 giá trị ngoài khoảng.
- Mean 20.749288, std 15.884219, median 19; 145,727 dòng (14.5727%) bằng zero — tỷ lệ zero cao nhất trong sáu điểm nội dung dạng số nguyên.
- 2,650 dòng (0.2650%) nằm ngoài các ngưỡng IQR.
- Số nguyên duy nhất không được quan sát thấy là một lỗ hổng lấy mẫu trong một lần extract 1,000,000 dòng, **không** phải một lỗi; không giá trị nào được chèn vào và ràng buộc 0–100 vẫn áp dụng.

**Hành động làm sạch** — Giữ nguyên. Validation `0 <= giá trị <= 100`.

#### `fake_certificate_offer`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Cho biết tin tuyển dụng đề nghị một chứng chỉ gian lận hoặc không có giá trị. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 2 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Flag |

**Quan sát về chất lượng dữ liệu**

- `0`: 920,170 dòng (92.0170%); `1`: 79,830 dòng (7.9830%). Nghiêm ngặt trong `{0,1}`, không có null.
- Phép chia 92/8 là mất cân bằng lớp thông thường với một chỉ báo gian lận, không phải một lỗi.

**Hành động làm sạch** — Giữ nguyên cách biểu diễn 0/1. **Không cân bằng lại dưới bất kỳ hình thức nào.** Validation việc thuộc `{0,1}`.

---

### 3.6 Thuộc tính về nhà tuyển dụng

#### `recruiter_experience_years`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `float64`, một chữ số thập phân (856,914 giá trị không nguyên) |
| Diễn giải nghiệp vụ | Kinh nghiệm của nhà tuyển dụng tính theo năm. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 183 giá trị phân biệt |
| Kiểu staging dự kiến | `DECIMAL(3,1) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0.0 đến 19.6; mean 5.052660, std 2.871692, median 5, các tứ phân vị 3 / 5 / 7.
- 49,615 dòng (4.9615%) đúng bằng 0. Việc 0 có nghĩa là "không có kinh nghiệm" hay "không được ghi nhận" thì **không thể xác định từ dữ liệu**; dù sao nó cũng được để nguyên là 0.
- 3,585 dòng (0.3585%) nằm trên ngưỡng trên IQR là 13.
- **Cột này khớp với heuristic tên-dạng-date của bộ profiler** (tên nó chứa `years`) nhưng **không** phải là một date: tỷ lệ parse thành công là 0.00% và các giá trị là một measure về khoảng thời gian. Được ghi lại để heuristic vẫn có thể audit được; không có phép parse date nào được thử.

**Hành động làm sạch** — Giữ nguyên, kể cả các giá trị zero. Không parse như một date. Không xử lý outlier.

#### `recruiter_email_type`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `str` |
| Diễn giải nghiệp vụ | Địa chỉ email của nhà tuyển dụng thuộc một domain doanh nghiệp hay một nhà cung cấp email miễn phí. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 2 giá trị phân biệt (độ dài tối đa 9 ký tự) |
| Kiểu staging dự kiến | `VARCHAR(16) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên Dimension |

**Quan sát về chất lượng dữ liệu**

- Miền giá trị đầy đủ: `Corporate` (749,433 dòng, 74.9433%), `Free` (250,567 dòng, 25.0567%).
- Không có lỗi về whitespace, chữ hoa/thường hay chuỗi rỗng.
- **Song ánh hoàn hảo với `suspicious_email_domain`** — xem §5.2. `Corporate` ↔ 0 và `Free` ↔ 1, với 0 dòng vi phạm trên 1,000,000 dòng và Cramér's V = 1.000000.
- Vì là một nhãn chứ không phải một boolean, nó có khoảng trống dự phòng mà flag không có: một lần extract trong tương lai có thể chứa một loại thứ ba.

**Hành động làm sạch** — Giữ nguyên văn. **Không bị xóa**, dù đã chứng minh được sự dư thừa; quan hệ này được tài liệu hóa và quyết định về sự dư thừa được hoãn tới bước dimensional modelling.

#### `suspicious_email_domain`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Cho biết domain email của nhà tuyển dụng là đáng nghi. Trên lần extract này nó chính xác là chỉ báo cho `recruiter_email_type = 'Free'`. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 2 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Flag |

**Quan sát về chất lượng dữ liệu**

- `0`: 749,433 dòng (74.9433%); `1`: 250,567 dòng (25.0567%). Nghiêm ngặt trong `{0,1}`, không có null.
- Các số lượng khớp chính xác với `recruiter_email_type`. Xem §5.2 cho bằng chứng song ánh đầy đủ.

**Hành động làm sạch** — Giữ nguyên cách biểu diễn 0/1. **Không bị xóa.** Validation việc thuộc `{0,1}` và validation lại tính song ánh ở mỗi lần load.

#### `recruiter_response_time_hours`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `float64`, một chữ số thập phân (860,182 giá trị không nguyên) |
| Diễn giải nghiệp vụ | Nhà tuyển dụng mất bao lâu để phản hồi, tính theo giờ. **Khoảng thời gian này được đo từ sự kiện nào thì không được tài liệu hóa.** |
| Thiếu | 0 (0.0000%) |
| Cardinality | 595 giá trị phân biệt |
| Kiểu staging dự kiến | `DECIMAL(3,1) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 1.0 đến 63.9 giờ; mean 18.180467, std 9.611051, median 18, các tứ phân vị 11.2 / 18.0 / 24.8.
- Không có giá trị âm và **không có zero**, nên zero không được dùng làm placeholder.
- 3,217 dòng (0.3217%) nằm trên ngưỡng trên IQR là 45.2 — một đuôi phải dài thông thường với phân phối về thời gian phản hồi.
- **Cột này khớp với heuristic tên-dạng-date của bộ profiler** (tên nó chứa `time`) nhưng **không** phải là một date: tỷ lệ parse thành công là 0.00% và các giá trị là một measure về khoảng thời gian. Được ghi lại để heuristic vẫn có thể audit được.

**Hành động làm sạch** — Giữ nguyên. Không parse như một date hay một timestamp. Không chặn ngưỡng.

#### `social_media_presence`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Cho biết công ty có sự hiện diện trên mạng xã hội có thể phát hiện được. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 2 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Flag |

**Quan sát về chất lượng dữ liệu**

- `0`: 250,200 dòng (25.0200%); `1`: 749,800 dòng (74.9800%). Nghiêm ngặt trong `{0,1}`, không có null.
- Tương quan với `trust_signal_score` là **+0.001566** — thực tế là không có (xem §5.4).

**Hành động làm sạch** — Giữ nguyên cách biểu diễn 0/1. Validation việc thuộc `{0,1}`.

---

### 3.7 Các flag về độ tin cậy và sự hiện diện của công ty

#### `linkedin_presence`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Cho biết công ty có sự hiện diện trên LinkedIn. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 2 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Flag |

**Quan sát về chất lượng dữ liệu**

- `0`: 199,236 dòng (19.9236%); `1`: 800,764 dòng (80.0764%). Nghiêm ngặt trong `{0,1}`, không có null.
- Một trong chỉ hai flag có mối liên hệ đáng kể với `trust_signal_score`: Pearson r = **0.243830**, giá trị trung bình theo nhóm 48.5577 (flag 0) so với 58.5459 (flag 1), chênh lệch 9.9882.

**Hành động làm sạch** — Giữ nguyên cách biểu diễn 0/1. Validation việc thuộc `{0,1}`.

#### `website_available`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Cho biết công ty có một website truy cập được. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 2 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Flag |

**Quan sát về chất lượng dữ liệu**

- `0`: 150,403 dòng (15.0403%); `1`: 849,597 dòng (84.9597%). Nghiêm ngặt trong `{0,1}`, không có null.
- Tương quan với `trust_signal_score` là **-0.001497** — thực tế là không có, và mang dấu âm, dù ý nghĩa bề mặt của cột. Được ghi lại như một quan sát; nó không bị hiệu chỉnh.
- `domain_age_months` có giá trị ở cả 1,000,000 dòng, bao gồm 150,403 dòng có `website_available = 0`. Hai điều này không được nguồn dung hòa và **không có phép dung hòa nào được thử**.

**Hành động làm sạch** — Giữ nguyên cách biểu diễn 0/1. Validation việc thuộc `{0,1}`.

#### `verification_status`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Cho biết công ty hoặc tin tuyển dụng đã được xác minh. **Bên thực hiện xác minh và các tiêu chí không được tài liệu hóa.** |
| Thiếu | 0 (0.0000%) |
| Cardinality | 2 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Flag |

**Quan sát về chất lượng dữ liệu**

- `0`: 300,287 dòng (30.0287%); `1`: 699,713 dòng (69.9713%). Nghiêm ngặt trong `{0,1}`, không có null.
- Biến tương quan đơn mạnh nhất với `trust_signal_score`: Pearson r = **0.278794**, giá trị trung bình theo nhóm 49.5913 (flag 0) so với 59.5437 (flag 1), chênh lệch 9.9524.

**Hành động làm sạch** — Giữ nguyên cách biểu diễn 0/1. Validation việc thuộc `{0,1}`.

---

### 3.8 Các điểm tổng hợp và outcome

#### `trust_signal_score`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `float64`, một chữ số thập phân (888,982 giá trị không nguyên) |
| Diễn giải nghiệp vụ | Một điểm tổng hợp tóm lược các tín hiệu tin cậy của tin tuyển dụng. **Cách suy dẫn không được tài liệu hóa và có thể chứng minh được là không tái lập được từ bốn flag về sự hiện diện/xác minh.** |
| Thiếu | 10,000 (1.0000%) |
| Cardinality | 1,001 giá trị phân biệt (0.0–100.0 với một chữ số thập phân) |
| Kiểu staging dự kiến | `DECIMAL(4,1) NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0.0 đến 100.0, nằm hoàn toàn trong biên: 0 giá trị ngoài khoảng. Mean 56.555847, std 16.362310, median 56.9, các tứ phân vị 45.6 / 56.9 / 67.9.
- 479 dòng đúng bằng 0; 4,510 dòng (0.4510%) nằm ngoài các ngưỡng IQR.
- **Không tất định từ `verification_status`, `linkedin_presence`, `website_available` và `social_media_presence`** (§5.4): cả 16 tổ hợp flag đều xuất hiện, khoảng biến thiên lớn nhất trong một tổ hợp là 100.0, độ lệch chuẩn lớn nhất trong một tổ hợp là 15.5713, và một tổ hợp chứa 986 điểm phân biệt. Mô hình saturated chỉ giải thích R² = 0.137190.
- Tỷ lệ gian lận trong số 10,000 dòng thiếu điểm: 22.3800%, so với 22.1939% ở nơi có giá trị — một khoảng cách **+0.1861 pp**, trường hợp duy nhất trong ba cột không đầy đủ mà các dòng bị thiếu lại *thường xuyên hơn* là gian lận.
- Tương quan với `is_fake_posting`: **-0.386458**.

**Hành động làm sạch** — Giữ nguyên. Giá trị thiếu vẫn là `NULL`; **không imputation**, và đặc biệt nó **không** được tái dựng từ bốn flag, vì audit đã chứng minh phép tái dựng đó là không thể. Validation `0 <= giá trị <= 100` ở nơi không null.

#### `fraud_score`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `float64`, một chữ số thập phân (849,582 giá trị không nguyên) |
| Diễn giải nghiệp vụ | Một điểm tổng hợp về rủi ro gian lận của tin tuyển dụng. Cách suy dẫn **không** được tài liệu hóa. |
| Thiếu | 0 (0.0000%) |
| Cardinality | 1,001 giá trị phân biệt (0.0–100.0 với một chữ số thập phân) |
| Kiểu staging dự kiến | `DECIMAL(4,1) NOT NULL` |
| Phân loại ngữ nghĩa | Ứng viên measure |

**Quan sát về chất lượng dữ liệu**

- Khoảng 0.0 đến 100.0, nằm hoàn toàn trong biên: 0 giá trị ngoài khoảng. Mean 34.012258, std 21.371783, median 32.3, các tứ phân vị 18.1 / 32.3 / 47.8.
- 51,586 dòng (5.1586%) đúng bằng 0; 8,881 dòng (0.8881%) nằm ngoài các ngưỡng IQR.
- Theo nhãn: mean 25.2939 (std 14.2375) ở nơi `is_fake_posting = 0`, mean 64.5733 (std 12.1187) ở nơi bằng 1.
- **Sát với nhãn, nhưng không bằng nhãn** (§5.3). Một lượt quét vét cạn mọi điểm quan sát được cho thấy ngưỡng tốt nhất là `fraud_score >= 50.0`, để lại **607 trường hợp lệch** (0.0607% — 607 false positive, 0 false negative; độ chính xác 99.939300%). **Không ngưỡng nào tái lập chính xác nhãn.**
- Sự bất đồng tập trung tại **một giá trị duy nhất**: tại `fraud_score = 50.0` đúng bằng, 607 dòng mang nhãn 0 và 620 dòng mang nhãn 1 (1,227 dòng, 0.1227%). Ở mọi điểm quan sát được khác, nhãn là hằng số.

**Hành động làm sạch** — Giữ nguyên. Validation `0 <= giá trị <= 100`. **`is_fake_posting` không được suy ra từ cột này, và cột này không được suy ra từ nhãn.** Không giá trị nào bị sửa đổi.

#### `is_fake_posting`

| Thuộc tính | Giá trị |
| --- | --- |
| Kiểu nguồn | `int64` |
| Diễn giải nghiệp vụ | Outcome được gán nhãn: tin tuyển dụng có phải là một tin thực tập giả/lừa đảo hay không. **Quy trình gán nhãn không được tài liệu hóa.** |
| Thiếu | 0 (0.0000%) |
| Cardinality | 2 giá trị phân biệt |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Outcome |

**Quan sát về chất lượng dữ liệu**

- `0`: 778,042 dòng (77.8042%); `1`: 221,958 dòng (22.1958%). Nghiêm ngặt trong `{0,1}`, không có null.
- Phép chia 78/22 là mức cân bằng lớp tự nhiên của lần extract này.
- Không tái lập được từ `fraud_score` bằng bất kỳ ngưỡng nào (xem ở trên).
- Tỷ lệ gian lận trong các dòng có ngày ở tương lai là 22.2939%, so với 22.1958% trên tổng thể — việc có ngày ở tương lai **không** liên hệ với nhãn.

**Hành động làm sạch** — Giữ nguyên cách biểu diễn 0/1. **Không resampling, không cân bằng lại, không SMOTE, không đánh trọng số lớp.** Validation việc thuộc `{0,1}`.

---

## 4. Các cột suy dẫn ở tầng staging

Hai cột dưới đây **không có trong file CSV raw**. Chúng được tạo ra bởi bước load
staging và chỉ tồn tại trong dataset staging. File raw giữ 33 cột; dataset
staging có 35 cột.

### 4.1 `source_row_id`

| Thuộc tính | Giá trị |
| --- | --- |
| Nguồn gốc | **Suy dẫn ở staging** — không có trong nguồn |
| Diễn giải nghiệp vụ | Tay cầm phục vụ data lineage, trỏ trở lại một dòng vật lý của lần extract này. |
| Định nghĩa | Vị trí của dòng trong file CSV gốc, tăng dần, bắt đầu từ **1**, được gán theo thứ tự file gốc **trước mọi phép lọc, sắp xếp hay biến đổi**. |
| Khoảng giá trị | 1 đến 1,000,000, liên tục |
| Thiếu | 0 |
| Cardinality | 1,000,000 giá trị phân biệt (100% duy nhất) |
| Kiểu staging dự kiến | `INTEGER NOT NULL` — primary key của staging |
| Phân loại ngữ nghĩa | Identifier |

**Vì sao nó tồn tại** — phân tích key trong bước profiling không tìm thấy
**natural key dạng cột đơn nào và không tìm thấy tổ hợp duy nhất nào** trong 33
cột nguồn. Một surrogate key là cách duy nhất để định địa chỉ một dòng riêng lẻ.

**Các ràng buộc về cách dùng nó**

- Nó là một **tay cầm phục vụ data lineage, không phải một business key.** Nó chỉ
  có ý nghĩa khi kết hợp với sha256 của file nguồn, và cả hai phải được ghi cùng
  nhau trong bản ghi audit của lần load.
- Nó **không** được dùng để join giữa các lần extract: cùng một `source_row_id`
  trong một file khác trỏ tới một tin tuyển dụng khác.
- Nó **không** được thêm vào file CSV raw.
- Nó không mang ý nghĩa nghiệp vụ nào và không được coi là một số thứ tự, một ID
  tin tuyển dụng hay một thứ tự có ý nghĩa phân tích.

### 4.2 `is_future_posting`

| Thuộc tính | Giá trị |
| --- | --- |
| Nguồn gốc | **Suy dẫn ở staging** — không có trong nguồn |
| Diễn giải nghiệp vụ | Đánh dấu một tin tuyển dụng có ngày sau ngày tham chiếu của audit. |
| Định nghĩa | `1` khi `posting_date > 2026-09-23`; ngược lại `0`. |
| Ngày tham chiếu | **2026-09-23** — ngày audit/tham chiếu, cố định và đã tài liệu hóa |
| Thiếu | 0 |
| Phân phối giá trị kỳ vọng | `1`: 30,246 dòng (3.0246%); `0`: 969,754 dòng (96.9754%) |
| Kiểu staging dự kiến | `SMALLINT NOT NULL` |
| Phân loại ngữ nghĩa | Flag |

**Ghi chú**

- Cờ này **đánh dấu** các dòng có ngày ở tương lai; nó **không** lọc chúng. Cả
  30,246 dòng đều còn lại trong staging.
- `2026-09-23` là một **hằng số cố định**, không phải "hôm nay". Việc tính cờ này
  theo ngày hiện tại sẽ làm dataset staging không tái lập được: các số dòng ở trên
  sẽ trôi đi ở mỗi lần chạy. Mốc cắt được ghim cố định để đầu ra là tất định.
- Cờ này là một dấu hiệu về chất lượng dữ liệu, không phải một tín hiệu gian lận.
  Các dòng có ngày ở tương lai mang tỷ lệ gian lận 22.2939% so với 22.1958% trên
  tổng thể.

---

## 5. Các quan hệ giữa các cột được audit xác lập

Đây là các phụ thuộc đã được đo giữa các cột nguồn. **Không quan hệ nào trong số
đó khiến một cột bị bỏ hay bị suy dẫn ở giai đoạn staging.** Mỗi quan hệ được ghi
lại để giai đoạn dimensional modelling có thể ra quyết định trên cơ sở thông tin
đầy đủ.

### 5.1 `payment_required` ↔ `registration_fee` — chính xác, dư thừa

| Phép kiểm tra | Số dòng | % |
| --- | ---: | ---: |
| `payment_required = 0` VÀ `registration_fee > 0` | **0** | 0.0000% |
| `payment_required = 1` VÀ `registration_fee = 0` | **0** | 0.0000% |
| `payment_required = 0` VÀ `registration_fee = 0` (nhất quán) | 900,095 | 90.0095% |
| `payment_required = 1` VÀ `registration_fee > 0` (nhất quán) | 99,905 | 9.9905% |

`payment_required == (registration_fee > 0)` đúng với **cả 1,000,000 dòng**.
Flag hoàn toàn phục hồi được từ phí trên lần extract này.

**Trạng thái** — cả hai cột được giữ; invariant là một quy tắc validation (§10 của
[cleaning_rules_vi.md](cleaning_rules_vi.md)); sự dư thừa được hoãn tới bước
dimensional modelling. Audit đã lưu ý rằng điều này chứng minh ràng buộc trên
*lần extract này*, không phải rằng hệ thống nguồn thực thi nó.

### 5.2 `recruiter_email_type` ↔ `suspicious_email_domain` — song ánh hoàn hảo

| `recruiter_email_type` \ `suspicious_email_domain` | 0 | 1 | Tổng |
| --- | ---: | ---: | ---: |
| `Corporate` | 749,433 | **0** | 749,433 |
| `Free` | **0** | 250,567 | 250,567 |
| **Tổng** | 749,433 | 250,567 | 1,000,000 |

Functional dependency đúng theo **cả hai** chiều với 0 dòng vi phạm;
Cramér's V = **1.000000**; chi-square = 1,000,000.00. Phép mapping là
`Corporate ↔ 0` và `Free ↔ 1`.

**Trạng thái** — cả hai cột được giữ và bảo toàn; không cột nào bị xóa tự động.
Lập luận của audit: cột text là một nhãn còn chỗ cho một giá trị thứ ba trong một
lần extract tương lai, trong khi flag là boolean, nên việc mang cả hai gần như
không tốn gì và giữ lại khoảng trống dự phòng đó.

### 5.3 `fraud_score` → `is_fake_posting` — sát nhưng **không** tất định

| Chỉ số | Giá trị |
| --- | ---: |
| Ngưỡng tốt nhất | `fraud_score >= 50.0` |
| Số trường hợp lệch tại ngưỡng tốt nhất | **607** |
| — false positive (nhãn 0, score ≥ 50) | 607 |
| — false negative (nhãn 1, score < 50) | 0 |
| Độ chính xác tại ngưỡng tốt nhất | 99.939300% |
| **Có thể tái lập hoàn hảo** | **KHÔNG** |
| `fraud_score` lớn nhất trong nhóm nhãn 0 | 50.00 |
| `fraud_score` nhỏ nhất trong nhóm nhãn 1 | 50.00 |
| Số điểm phân biệt mà cả hai lớp cùng xuất hiện | **1** (đúng bằng 50.0) |
| Số dòng tại điểm đó | 1,227 (0.1227%) — 607 nhãn 0, 620 nhãn 1 |

Dưới 50.0 mọi dòng đều mang nhãn 0; trên 50.0 mọi dòng đều mang nhãn 1. Toàn bộ
sự bất đồng nằm đúng trên giá trị biên duy nhất đó. Đó là dấu hiệu của một quy tắc
được giải quyết tại biên bằng một tiêu chí thứ hai nào đó, bằng phép làm tròn,
hoặc một cách tùy ý — trường hợp nào áp dụng thì **không thể đọc ra từ dữ liệu**.

**Trạng thái** — cả hai cột được bảo toàn; nhãn **không** được suy ra từ điểm số,
và điểm số **không** được suy ra từ nhãn.

### 5.4 Các tín hiệu tin cậy → `trust_signal_score` — **không** tất định

Được đo trên 990,000 dòng có điểm số.

| Chỉ báo | Pearson r | Mean @ 0 | Mean @ 1 | Chênh lệch |
| --- | ---: | ---: | ---: | ---: |
| `verification_status` | 0.278794 | 49.5913 | 59.5437 | 9.9524 |
| `linkedin_presence` | 0.243830 | 48.5577 | 58.5459 | 9.9882 |
| `website_available` | -0.001497 | 56.6141 | 56.5455 | -0.0686 |
| `social_media_presence` | 0.001566 | 56.5115 | 56.5706 | 0.0592 |

| Chỉ số | Giá trị |
| --- | ---: |
| Số tổ hợp flag quan sát được | 16 trên 16 |
| Khoảng biến thiên lớn nhất trong một tổ hợp | **100.000000** |
| Độ lệch chuẩn lớn nhất trong một tổ hợp | 15.571299 |
| Số điểm phân biệt nhiều nhất trong một tổ hợp | 986 |
| R², mô hình saturated | **0.13719010** |
| R², mô hình cộng tính | 0.13718609 |

Nếu điểm số là một hàm của bốn flag thì khoảng biến thiên trong mỗi tổ hợp sẽ
bằng 0 ở mọi nơi. Nó là 100.0 — toàn bộ thang đo. **Điểm số không tái dựng được
từ các flag này**, và khoảng 86% phương sai của nó phụ thuộc vào thứ gì đó ngoài
tập cột này.

**Trạng thái** — cả năm cột được bảo toàn không thay đổi. Điểm số không bao giờ
được impute từ các flag.

### 5.5 `company_age` so với `domain_age_months` — không đủ bằng chứng về tính không hợp lệ

469,297 dòng (47.4037% trong số 990,000 dòng so sánh được) có domain già hơn công
ty, chênh từ 1 đến 73 tháng (median 10). Pearson r giữa hai cột, trên một thang
đo chung, là 0.9940.

**Trạng thái** — không bản ghi nào bị sửa đổi. Domain được mua lại, việc đổi
thương hiệu và domain đỗ (parked) tạo ra điều này một cách chính đáng, và chỉ
riêng sự khác biệt về độ mịn năm-so-với-tháng đã giải thích được những mức vượt
nhỏ.

### 5.6 Cấu trúc của việc thiếu dữ liệu — ba khoảng trống độc lập

| Cặp | Thiếu ở cả hai | Kỳ vọng nếu độc lập | Jaccard | Hai mặt nạ giống hệt nhau |
| --- | ---: | ---: | ---: | --- |
| `company_age` & `stipend` | 88 | 100.00 | 0.004419 | không |
| `company_age` & `trust_signal_score` | 96 | 100.00 | 0.004823 | không |
| `stipend` & `trust_signal_score` | 88 | 100.00 | 0.004419 | không |

- Số dòng thiếu ít nhất một trong ba: **29,728**.
- Số dòng thiếu cả ba: **0** (tính độc lập dự báo ~1).
- Không có hai mặt nạ nào giống hệt nhau.

Ba khoảng trống này **không** phải một lần rơi dữ liệu ở mức bản ghi, nên chúng
không thể được xử lý như một điều kiện "bản ghi không đầy đủ" duy nhất.

---

## 6. Chỉ mục bằng chứng

| Khẳng định trong tài liệu này | File bằng chứng |
| --- | --- |
| Số dòng/cột, dtype, bản trùng, sha256 | `results/profiling/dataset_overview.txt` |
| Số null, số giá trị phân biệt theo từng cột | `results/profiling/column_profile.csv` |
| min/max/mean/std/tứ phân vị/số zero của numeric | `results/profiling/numeric_summary.csv` |
| Số giá trị phân biệt và mode của categorical | `results/profiling/categorical_summary.csv` |
| Miền giá trị category đầy đủ | `results/profiling/categorical_top_values.txt` |
| Các phép kiểm tra whitespace / rỗng / biến thể hoa-thường | `results/profiling/string_quality.csv` |
| Tỷ lệ parse date và khoảng giá trị | `results/profiling/date_analysis.csv` |
| Tính ứng viên key cho cả 33 cột | `results/profiling/potential_key_analysis.csv` |
| Báo cáo profiling dạng diễn giải | `results/profiling/summary.md` |
| Số lượng và phân rã ngày ở tương lai | `results/audit/future_dates.csv`, `future_dates_by_month.csv`, `date_bounds.csv` |
| Chồng lấp việc thiếu dữ liệu và liên hệ với nhãn | `results/audit/missing_overlap.csv`, `missing_combination_counts.csv`, `missing_value_relationship.csv` |
| Validation các binary flag | `results/audit/binary_flags.csv`, `binary_flag_value_counts.csv` |
| Invariant về thanh toán | `results/audit/payment_consistency.csv` |
| Song ánh về email | `results/audit/email_crosstab.csv` |
| Quan hệ giữa fraud score và nhãn | `results/audit/fraud_score_relationship.csv`, `fraud_score_class_stats.csv`, `fraud_score_threshold_scan.csv` |
| Kiểm định tính tất định của trust signal | `results/audit/trust_signal_relationship.csv`, `trust_signal_correlations.csv` |
| Tuổi công ty so với tuổi domain | `results/audit/company_domain_age.csv` |
| Validation khoảng 0–100 | `results/audit/score_range_validation.csv` |
| Giá trị âm, zero, ngưỡng IQR | `results/audit/numeric_sanity.csv` |
| Tính ứng viên key và đề xuất `source_row_id` | `results/audit/key_candidates.csv` |
| Các quan sát về provenance | `results/audit/provenance_indicators.csv` |
| Báo cáo audit dạng diễn giải | `results/audit/audit_summary.md` |

Độ chính xác thập phân, tính nguyên của `company_age` và `stipend`, độ dài text
tối đa và phát hiện về dấu phẩy nhúng trong `company_name` đã được kiểm chứng lại
trực tiếp đối chiếu với file CSV raw trong quá trình viết tài liệu này, ở chế độ
chỉ đọc.

---

## 7. Phạm vi của tài liệu này

- Nó mô tả và phân loại. Nó **không** sửa đổi dataset.
- Các phân loại ngữ nghĩa là **các ứng viên**, không phải các quyết định về
  modelling.
- Ở những nơi nguồn không tài liệu hóa một ý nghĩa — đơn vị tiền tệ và kỳ trả
  lương của `stipend`, đơn vị tiền tệ của `registration_fee`, đơn vị của
  `job_description_length`, các tiêu chí đằng sau `verification_status`, cách suy
  dẫn của sáu điểm về nội dung, của `trust_signal_score` và `fraud_score`, quy
  trình gán nhãn đằng sau `is_fake_posting`, và quy tắc kích hoạt của
  `unrealistic_salary_flag` — tài liệu này ghi lại rằng ý nghĩa đó không được tài
  liệu hóa, chứ không cung cấp một ý nghĩa thay thế.
- Các hành động làm sạch được tóm lược theo từng cột được trình bày đầy đủ, kèm
  lý do và các yêu cầu validation của chúng, trong
  [cleaning_rules_vi.md](cleaning_rules_vi.md).
