# Báo cáo Validation Tầng Staging

**Kết quả tổng thể: PASS** &mdash; 47 trên 47 phép kiểm tra đạt.

| Hạng mục | Giá trị |
| --- | --- |
| Thời điểm tạo | 2026-09-23 17:23:06 |
| Script | `scripts/build_staging.py` |
| Nguồn | `data/raw/fake_internship_detection_dataset.csv` |
| Đầu ra staging | `data/staging/internship_postings_staging.csv` |
| sha256 nguồn | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Số dòng vào / số dòng ra | 1,000,000 / 1,000,000 |
| Số cột vào / số cột ra | 33 / 35 |
| Ngày tham chiếu (cố định) | **2026-09-23** |
| Kích thước chunk / số chunk | 100,000 / 10 |
| Thời gian chạy | 68.0s |
| Kích thước đầu ra | 170.44 MB |

Các giá trị kỳ vọng đến từ giai đoạn profiling và audit đã hoàn tất (`results/profiling/`, `results/audit/`) và từ [docs/data_dictionary_vi.md](../../docs/data_dictionary_vi.md). Chúng là **những assertion về đầu ra**, không bao giờ là đầu vào cho logic biến đổi. Một phép kiểm tra thất bại sẽ được báo cáo tại đây; pipeline không bao giờ âm thầm sửa chữa dữ liệu.

---

## 1. Kết quả các phép kiểm tra

| # | Phép kiểm tra | Trạng thái | Quan sát được | Kỳ vọng |
| --- | --- | --- | --- | --- |
| 1 | sha256 của raw trước khi xử lý khớp với digest đã tài liệu hóa | **PASS** | 3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398 | 3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398 |
| 2 | sha256 của raw sau khi xử lý khớp với digest đã tài liệu hóa | **PASS** | 3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398 | 3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398 |
| 29 | File raw không bị lần chạy này thay đổi (sha256 + size + mtime) | **PASS** | sha256 3463d99be6580df3 / 173788906 bytes / mtime_ns 1790153224451672700 | giống hệt fingerprint trước khi chạy |
| 3 | CSV được đọc bằng parser nhận biết dấu ngoặc kép (giữ nguyên dấu phẩy nhúng bên trong) | **PASS** | 333784 dòng có dấu phẩy bên trong company_name được đặt trong ngoặc kép; mọi record parse ra 33 trường | parse nhận biết ngoặc kép, không lệch trường |
| 4 | Mọi record đã parse có đúng 33 trường nguồn | **PASS** | header 33 trường; độ rộng record {33: 1000000}; record dị dạng 0 | 33 cho header và cho toàn bộ 1000000 record |
| 5 | Số dòng của raw | **PASS** | 1,000,000 | 1,000,000 |
| 6 | Số dòng của staging | **PASS** | 1,000,000 | 1,000,000 |
| 7 | Số cột của staging | **PASS** | 35 | 35 |
| 8 | Giữ lại toàn bộ 33 cột gốc | **PASS** | 0 cột thiếu | 0 cột thiếu |
| 9 | Thứ tự cột gốc được giữ nguyên | **PASS** | các cột nguồn chiếm vị trí 1-33 trong đầu ra theo thứ tự file | giống hệt thứ tự header của raw |
| 10 | Giá trị nhỏ nhất của source_row_id | **PASS** | 1 | 1 |
| 11 | Giá trị lớn nhất của source_row_id | **PASS** | 1,000,000 | 1,000,000 |
| 12 | source_row_id là duy nhất | **PASS** | 1000000 giá trị phân biệt, 0 bản trùng, phủ 1000000 trong khoảng 1..1000000 | 1,000,000 giá trị phân biệt, 0 bản trùng, liên tục |
| 13 | source_row_id không null và không nằm ngoài khoảng | **PASS** | 0 null, 0 ngoài khoảng | 0 null, 0 ngoài khoảng |
| 13b | source_row_id tăng theo thứ tự file gốc, đơn điệu xuyên các chunk | **PASS** | tăng đúng +1 qua toàn bộ 10 ranh giới chunk | tăng nghiêm ngặt, không bao giờ reset theo chunk |
| 14 | Số lần parse thất bại của posting_date | **PASS** | 0 ở staging, 0 ở raw | 0 |
| 14b | posting_date được ghi ở dạng ISO YYYY-MM-DD | **PASS** | 0 giá trị không theo ISO | 0 |
| 15 | Giá trị nhỏ nhất của posting_date | **PASS** | 2018-01-01 | 2018-01-01 |
| 16 | Giá trị lớn nhất của posting_date | **PASS** | 2026-12-31 | 2026-12-31 |
| 16b | Số giá trị posting_date phân biệt | **PASS** | 3,287 | 3,287 |
| 17 | Miền giá trị của is_future_posting | **PASS** | [0, 1] | {0, 1} |
| 18 | Số dòng có is_future_posting = 1 | **PASS** | 30,246 (3.0246%) | 30,246 |
| 18b | is_future_posting tái lập được từ mốc cắt cố định khi đọc lại | **PASS** | 0 trường hợp lệch | 0 |
| 19 | Số giá trị thiếu của company_age | **PASS** | 10,000 (1.0000%) | 10,000 |
| 20 | Số giá trị thiếu của stipend | **PASS** | 10,000 (1.0000%) | 10,000 |
| 21 | Số giá trị thiếu của trust_signal_score | **PASS** | 10,000 (1.0000%) | 10,000 |
| 22 | Không phát sinh giá trị thiếu ngoài dự kiến ở các cột nguồn | **PASS** | 0 null trên 30 cột nguồn còn lại | 0 |
| 22b | Số null ở staging bằng số null ở raw, theo từng cột | **PASS** | giống hệt với cả 33 cột nguồn | giống hệt |
| 23 | Cả chín trường binary nằm nghiêm ngặt trong {0,1}, không có null | **PASS** | 0 vi phạm, 0 null | 0 vi phạm, 0 null |
| 23b | unrealistic_salary_flag được giữ lại và vẫn là hằng số 0 | **PASS** | có mặt, các giá trị [0] | có mặt, {0} |
| 24 | Bảy cột score thỏa 0 <= giá trị <= 100 ở nơi không null | **PASS** | 0 ngoài khoảng | 0 |
| 25 | payment_required == (registration_fee > 0) | **PASS** | 0 | 0 |
| 26 | recruiter_email_type Corporate<->0 và Free<->1 | **PASS** | 0 | 0 |
| 26b | is_fake_posting không được suy ra từ fraud_score | **PASS** | digest của nhãn giống hệt nguồn | giống hệt |
| 27 | Số dòng nguồn trùng khớp chính xác (chỉ 33 trường nguồn) | **PASS** | 0 bản trùng, 1,000,000 dòng phân biệt | 0 |
| 28 | Giá trị nguồn được bảo toàn qua vòng ghi-đọc (so sánh theo từng phần tử) | **PASS** | 0 giá trị khác biệt trên 33,000,000 ô được so sánh | 0 |
| 28b | Digest giá trị theo từng cột có xét thứ tự khớp với raw | **PASS** | 33 trên 33 digest cột giống hệt | 33 trên 33 |
| T1 | company_age / stipend không chứa giá trị non-null không nguyên | **PASS** | 0 | 0 |
| T2 | Các cột một chữ số thập phân giữ nguyên độ chính xác một chữ số thập phân | **PASS** | 0 giá trị lệch lưới ở recruiter_experience_years, recruiter_response_time_hours, trust_signal_score, fraud_score | 0 |
| T3 | Không trường nào thất bại khi parse numeric | **PASS** | 0 | 0 |
| T4 | Cùng một schema 35 cột được ghi cho mọi chunk | **PASS** | 1 biến thể schema trên 10 chunk | 1 |
| T5 | Header được ghi đúng một lần | **PASS** | 1 dòng header, 35 cột | 1 dòng header, 35 cột |
| T6 | Không có giá trị âm trong bất kỳ cột numeric nào | **PASS** | 0 | 0 |
| T7 | Các cột numeric nằm trong khoảng quan sát đã tài liệu hóa | **PASS** | 0 ngoài khoảng | 0 |
| T8 | Các cột text không có whitespace đệm, không rỗng, không có giá trị chỉ gồm whitespace | **PASS** | có đệm 0, rỗng 0, chỉ whitespace 0 | 0 / 0 / 0 |
| T9 | Số giá trị phân biệt của các cột categorical không đổi so với nguồn | **PASS** | cả 8 cột text đều khớp | khớp |
| T10 | Luồng raw được tiêu thụ hoàn toàn, đồng bộ từng bước với staging | **PASS** | 0 | 0 |

### Ghi chú cho từng phép kiểm tra

- **3 &mdash; CSV được đọc bằng parser nhận biết dấu ngoặc kép (giữ nguyên dấu phẩy nhúng bên trong):** Một phép split(',') ngây thơ sẽ làm các dòng này rộng ra và đẩy lệch mọi trường phía sau.
- **4 &mdash; Mọi record đã parse có đúng 33 trường nguồn:** Bất kỳ độ rộng nào khác đều được coi là lỗi lệch trường nghiêm trọng.
- **6 &mdash; Số dòng của staging:** Không dòng nào bị loại bỏ, kể cả các dòng có ngày ở tương lai.
- **7 &mdash; Số cột của staging:** 33 cột nguồn + 2 cột suy dẫn
- **9 &mdash; Thứ tự cột gốc được giữ nguyên:** Hai cột suy dẫn được thêm vào cuối, ở vị trí 34-35.
- **14 &mdash; Số lần parse thất bại của posting_date:** Các trường hợp thất bại được báo cáo, không bao giờ bị coerce hay loại bỏ.
- **18 &mdash; Số dòng có is_future_posting = 1:** Chỉ là kỳ vọng; mốc cắt 2026-09-23 là đầu vào duy nhất của quy tắc.
- **18b &mdash; is_future_posting tái lập được từ mốc cắt cố định khi đọc lại:** Được tính lại đối chiếu với 2026-09-23, không bao giờ theo đồng hồ hệ thống.
- **19 &mdash; Số giá trị thiếu của company_age:** Giữ nguyên là NULL; không imputation.
- **20 &mdash; Số giá trị thiếu của stipend:** Giữ nguyên là NULL; không imputation.
- **21 &mdash; Số giá trị thiếu của trust_signal_score:** Giữ nguyên là NULL; không imputation.
- **22b &mdash; Số null ở staging bằng số null ở raw, theo từng cột:** Chứng minh không điền giá trị, không loại bỏ và không phát sinh null mới.
- **23 &mdash; Cả chín trường binary nằm nghiêm ngặt trong {0,1}, không có null:** Giữ dạng 0/1; không chuyển thành Yes/No và không cân bằng lại.
- **23b &mdash; unrealistic_salary_flag được giữ lại và vẫn là hằng số 0:** Là hằng số trong lần extract này; được giữ lại vì việc bỏ nó là một quyết định thuộc modelling.
- **24 &mdash; Bảy cột score thỏa 0 <= giá trị <= 100 ở nơi không null:** Chỉ kiểm tra; không giá trị nào bị cắt.
- **25 &mdash; payment_required == (registration_fee > 0):** Được validation, không dùng để suy ra cột nào.
- **26 &mdash; recruiter_email_type Corporate<->0 và Free<->1:** Được validation, không dùng để suy ra cột nào.
- **26b &mdash; is_fake_posting không được suy ra từ fraud_score:** Hai cột vẫn được bảo toàn độc lập; audit đã phát hiện sự bất đồng tại fraud_score = 50.
- **27 &mdash; Số dòng nguồn trùng khớp chính xác (chỉ 33 trường nguồn):** source_row_id và is_future_posting bị loại trừ; nếu tính cả source_row_id thì theo định nghĩa mọi dòng đều duy nhất. Chỉ kiểm tra, không bao giờ loại trùng.
- **28 &mdash; Giá trị nguồn được bảo toàn qua vòng ghi-đọc (so sánh theo từng phần tử):** Raw và staging được đọc lại đồng bộ từng bước và được định kiểu bằng cùng một đoạn code.
- **T1 &mdash; company_age / stipend không chứa giá trị non-null không nguyên:** Cơ sở cho việc định kiểu nullable-integer; NULL được giữ nguyên là NULL, không bao giờ bị điền zero.
- **T2 &mdash; Các cột một chữ số thập phân giữ nguyên độ chính xác một chữ số thập phân:** Không bị làm tròn thành số nguyên.
- **T7 &mdash; Các cột numeric nằm trong khoảng quan sát đã tài liệu hóa:** Phép kiểm tra mang tính mô tả; không giá trị nào bị chặn ngưỡng, winsorize, scale hay loại bỏ.
- **T8 &mdash; Các cột text không có whitespace đệm, không rỗng, không có giá trị chỉ gồm whitespace:** Được báo cáo, không bị trim: không áp dụng phép TRIM hay LOWER vô điều kiện nào.
- **T9 &mdash; Số giá trị phân biệt của các cột categorical không đổi so với nguồn:** Không category nào bị mapping, gộp, đổi chữ hoa/thường hay mã hóa ordinal; company_size vẫn là categorical.

---

## 2. Tính toàn vẹn khi parse CSV (thất bại là nghiêm trọng)

Lần extract raw có chứa các trường text được đặt trong ngoặc kép với dấu phẩy nhúng bên trong, ví dụ `"Russell, Medina and Evans"` ở `company_name`. Việc tách một dòng theo `,` sẽ đọc đó thành hai trường và đẩy mọi cột phía sau lệch đi một vị trí, âm thầm làm hỏng 24 cột phía sau.

**Pipeline không bao giờ tách theo dấu phẩy.** Hai reader nhận biết dấu ngoặc kép độc lập được sử dụng:

1. Một lượt tiền quét về mặt cấu trúc bằng module `csv` của thư viện chuẩn (xử lý ngoặc kép theo RFC 4180), đi qua từng record vật lý và đếm số trường của nó.
2. `pandas.read_csv()` cho bước build và cho bước đọc lại đầu ra.

| Phép đo | Giá trị |
| --- | --- |
| Số trường ở header | 33 |
| Số record đã quét | 1,000,000 |
| Các độ rộng record phân biệt | {33: 1000000} |
| Số record không rộng 33 trường | 0 |
| Số record có dấu phẩy bên trong `company_name` được đặt trong ngoặc kép | 333,784 |

Mọi record parse ra đúng 33 trường. **Không phát hiện lệch trường và không phát hiện parse dị dạng nào.** Bất kỳ độ rộng nào khác sẽ là lỗi validation nghiêm trọng và sẽ hủy bỏ bước build.

Nội dung các trường trong ngoặc kép được bảo toàn chính xác: đầu ra được đọc lại bằng cùng parser nhận biết ngoặc kép và so sánh theo từng phần tử với file raw (phép kiểm tra 28), nên một phép ghi sai ngoặc kép sẽ lộ ra dưới dạng lệch giá trị ở `company_name`.

---

## 3. Tính bất biến của dữ liệu raw

| Hạng mục | Trước | Sau |
| --- | --- | --- |
| sha256 | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Kích thước (bytes) | 173,788,906 | 173,788,906 |
| mtime (ns) | 1790153224451672700 | 1790153224451672700 |

File raw: không thay đổi. Digest cũng khớp với giá trị được tài liệu hóa trong `docs/data_dictionary.md`: `match`.

File CSV raw được mở ở chế độ chỉ đọc. Không có gì được ghi vào `data/raw/`, không file nào ở đó bị ghi lại, và không timestamp nào ở đó bị chạm tới. `source_row_id` chỉ được thêm vào dataset **staging**.

---

## 4. Bằng chứng về việc bảo toàn giá trị

File CSV staging được đọc lại bằng `pandas.read_csv()` và được đi qua đồng bộ từng bước với file CSV raw, từng chunk một. Cả hai phía đều được định kiểu bằng **cùng một hàm**, nên bất kỳ khác biệt nào còn sót lại đều là lỗi thực sự chứ không phải sản phẩm phụ của phép so sánh.

- Số ô được so sánh: 33,000,000 (1,000,000 dòng x 33 cột nguồn)
- Số giá trị khác biệt: 0
- Số mặt nạ null khác biệt: 0

Ngoài ra, một digest sha256 có xét thứ tự được tích lũy cho từng cột ở cả hai phía (các hash giá trị 64-bit theo từng dòng được nối vào theo thứ tự file, nên digest bao trùm cả các giá trị **và** trình tự của chúng):

| Cột nguồn | Digest (16 ký tự hex đầu) | Khớp với raw |
| --- | --- | --- |
| `posting_date` | `7abb04e2b95d0a88` | có |
| `internship_title` | `4a70d0c63046493b` | có |
| `employment_type` | `61dfa2cd9c24542e` | có |
| `work_mode` | `c5014a5028a89308` | có |
| `industry` | `2c7ac727b0777b40` | có |
| `location` | `7df669bf70ae8c0f` | có |
| `company_name` | `990528ea81d69e13` | có |
| `company_size` | `1da43f2693bcb872` | có |
| `company_age` | `5434bba741b795c8` | có |
| `linkedin_presence` | `7e3a0bcd9626da75` | có |
| `website_available` | `37b17e9f67299bbb` | có |
| `domain_age_months` | `a812053cc3672a77` | có |
| `verification_status` | `0f63c5e49d1aa946` | có |
| `stipend` | `454a74b87050957c` | có |
| `unrealistic_salary_flag` | `6506614505e113da` | có |
| `payment_required` | `932a5648a16362d7` | có |
| `registration_fee` | `3e4b5b577eb9fd40` | có |
| `job_description_length` | `6348909b656464da` | có |
| `grammatical_errors` | `d48479b4b610fd11` | có |
| `vague_description_score` | `5195f79f39f3cbd5` | có |
| `urgency_score` | `5ac3beef695122a1` | có |
| `keyword_spam_score` | `400a8ef9795ffaee` | có |
| `fake_certificate_offer` | `72fa724ff6788a84` | có |
| `recruiter_experience_years` | `bec44830c39f0441` | có |
| `recruiter_email_type` | `c830f447e02c538e` | có |
| `suspicious_email_domain` | `126c5b4d4a53346d` | có |
| `recruiter_response_time_hours` | `37b9e97e065f3da8` | có |
| `social_media_presence` | `623f33709c526620` | có |
| `emotional_manipulation_score` | `52bf58c5d66c464c` | có |
| `phishing_language_score` | `8739376a44761272` | có |
| `trust_signal_score` | `49c2af6657485402` | có |
| `fraud_score` | `8f725146de7ef400` | có |
| `is_fake_posting` | `2c8095f4de609aee` | có |

`posting_date` được tính digest từ cách thể hiện ISO `YYYY-MM-DD` của nó ở cả hai phía. Đó là thay đổi biểu diễn duy nhất được chấp thuận, và nó bảo toàn giá trị: nguồn vốn đã được ghi ở dạng `YYYY-MM-DD`, nên không date nào bị diễn giải lại, dịch chuyển hay định dạng lại thành một giá trị lịch khác.

`company_age` và `stipend` được ghi ra mà không có phần `.0` ở cuối như khi pandas đọc chúng dưới dạng float. Đây là một **thay đổi biểu diễn datatype, không phải thay đổi giá trị**: phép kiểm tra T1 xác nhận 0 giá trị non-null không nguyên trên toàn bộ 1,000,000 dòng, và phép so sánh theo từng phần tử ở phép kiểm tra 28 là so sánh numeric, nên `43083.0` và `43083` được coi là bằng nhau. Các giá trị NULL vẫn là NULL và không bao giờ bị thay bằng zero.

---

## 5. Hạn chế ngữ nghĩa chưa được giải quyết &mdash; `stipend`

**Nguồn không tài liệu hóa đơn vị tiền tệ cũng không tài liệu hóa kỳ trả lương cho `stipend`.** Các giá trị trải từ 2,000 đến 110,428 trên chín địa điểm (Bangalore, Berlin, Dubai, London, New York, San Francisco, Singapore, Sydney, Toronto), và không có gì trong lần extract này cho biết một giá trị là theo tháng hay theo năm, hay nó được định danh bằng đơn vị tiền tệ nào.

Do đó tầng staging:

- bảo toàn `stipend` về mặt số học, đúng như được cung cấp;
- **không** chuyển đổi tiền tệ;
- **không** quy đổi theo năm hay đổi mốc gốc cho kỳ trả lương theo cách nào khác;
- **không** chuẩn hóa giữa các địa điểm;
- **không** tạo các dải stipend.

**Hạn chế này chưa được giải quyết và được chuyển tiếp.** Cho đến khi đơn vị tiền tệ và kỳ trả lương được xác lập, các giá trị `stipend` từ những địa điểm khác nhau không được mặc định là có thể so sánh trực tiếp, và bất kỳ phép tổng hợp `stipend` xuyên địa điểm nào ở tầng phân tích cũng sẽ không có cơ sở vững chắc. Cùng lưu ý này được ghi trong [transformation_log_vi.md](transformation_log_vi.md).

---

## 6. Các quan hệ đã biết &mdash; được validation, không bao giờ dùng để suy dẫn

| Quan hệ | Số vi phạm | Hành động đã thực hiện |
| --- | ---: | --- |
| `payment_required == (registration_fee > 0)` | 0 | Cả hai cột đều được giữ và bảo toàn độc lập. Không cột nào được suy ra từ cột kia. |
| `recruiter_email_type` Corporate&harr;0, Free&harr;1 | 0 | Cả hai cột đều được giữ và bảo toàn độc lập. Không cột nào được suy ra từ cột kia. |
| `fraud_score` &rarr; `is_fake_posting` | n/a | **Không suy dẫn.** Audit phát hiện hai đại lượng này bất đồng tại `fraud_score = 50`, nên nhãn không phải là một hàm của điểm số. Cả hai được bảo toàn độc lập. |

---

## 7. Những gì lần chạy này không làm

Không imputation, không xóa dòng, không xóa cột, không loại trùng, không mapping hay gộp category, không mã hóa ordinal, không đổi chữ hoa/thường hay cắt khoảng trắng, không scaling hay standardisation, không loại bỏ / chặn ngưỡng / winsorize outlier, không chuyển đổi tiền tệ, không chuẩn hóa hay phân dải stipend, không cân bằng lại lớp, và không suy dẫn nhãn. Danh sách đầy đủ kèm lý do nằm trong [transformation_log_vi.md](transformation_log_vi.md).
