# Audit Chất lượng Dữ liệu / Ngữ nghĩa

- **File nguồn**: `E:/project/internship-scam-dw/data/raw/fake_internship_detection_dataset.csv`
- **Thời điểm tạo**: 2026-09-23 16:55:24
- **sha256 nguồn**: `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398`
- **Số dòng x số cột**: 1,000,000 x 33
- **Ngày tham chiếu của audit**: 2026-09-23 (biên dưới hợp lý được dùng: 2018-01-01)
- **Phạm vi**: chỉ audit. Không có gì trong `data/raw/` bị ghi vào. Không giá trị nào bị làm sạch, impute, chặn ngưỡng, loại bỏ, chuẩn hóa, encode hay loại trùng. `posting_date` được parse vào một Series tạm thời trong bộ nhớ; DataFrame đã load không bao giờ bị thay đổi.

Mọi bảng dưới đây là một phép đo. Ở những mục nêu ra một giả thuyết ("liệu X có được suy ra từ Y?") thì bằng chứng ủng hộ và phản bác đều được trình bày, và quyết định được để mở. Không có cột nào được đề xuất xóa hay sửa đổi.

## 1. Audit ngày đăng tin

**Dữ kiện quan sát được**

| Chỉ số | Giá trị |
| --- | ---: |
| `posting_date` nhỏ nhất | 2018-01-01 |
| `posting_date` lớn nhất | 2026-12-31 |
| Độ trải (số ngày) | 3,286 |
| Số date phân biệt | 3,287 |
| Số giá trị không parse được theo `%Y-%m-%d` | 0 |
| Số giá trị không parse được theo bất kỳ định dạng nào | 0 |
| Số dòng trước 2018-01-01 | 0 |
| Số dòng sau 2026-09-23 (dòng ở tương lai) | 30,246 |
| Dòng ở tương lai theo % dataset | 3.0246% |
| Số date phân biệt ở tương lai | 99 |

Các dòng ở tương lai theo năm và tháng:

| Năm | Tháng | Số dòng | Số date phân biệt | `is_fake_posting`=0 | `is_fake_posting`=1 | % số dòng tương lai | % toàn bộ số dòng |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026 | 9 | 2,195 | 7 | 1,685 | 510 | 7.2572% | 0.2195% |
| 2026 | 10 | 9,435 | 31 | 7,370 | 2,065 | 31.1942% | 0.9435% |
| 2026 | 11 | 9,195 | 30 | 7,140 | 2,055 | 30.4007% | 0.9195% |
| 2026 | 12 | 9,421 | 31 | 7,308 | 2,113 | 31.1479% | 0.9421% |

Các dòng ở tương lai theo `is_fake_posting`:

| `is_fake_posting` | Số dòng | % số dòng tương lai |
| ---: | ---: | ---: |
| 0 | 23,503 | 77.7061% |
| 1 | 6,743 | 22.2939% |

Để so sánh, tỷ lệ nhãn trên toàn bộ dataset là 22.1958%.

Chi tiết theo từng date cho khối dữ liệu tương lai nằm trong `future_dates.csv`; phép tổng hợp theo tháng nằm trong `future_dates_by_month.csv`; các chỉ số biên nằm trong `date_bounds.csv`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- 30,246 dòng (3.0246%) mang ngày đăng tin muộn hơn ngày tham chiếu của audit là 2026-09-23, phân bố trên 99 date phân biệt. Một ngày đăng tin ở tương lai hoặc là sản phẩm phụ của quá trình nhập/sinh dữ liệu, hoặc là một ngữ nghĩa "bắt đầu sau" hợp lệ nhưng bị lưu sai cột. Chỉ riêng dữ liệu thì không thể phân biệt hai khả năng này. **Không dòng tương lai nào bị xóa.**
- Việc Dimension thời gian của Fact table nên trải qua các date này, chặn ngưỡng chúng, hay chuyển chúng về một thành viên late-arriving/unknown-date là một quyết định thuộc staging, không phải một phát hiện của audit.
- Không dòng nào nằm trước 2018-01-01.

## 2. Audit quan hệ của giá trị thiếu

**Dữ kiện quan sát được**

| Cột | Số thiếu | % thiếu | thiếu: nhãn 0 | thiếu: nhãn 1 | thiếu: tỷ lệ nhãn 1 | có giá trị: nhãn 0 | có giá trị: nhãn 1 | có giá trị: tỷ lệ nhãn 1 | Chênh lệch (pp) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `company_age` | 10,000 | 1.0000% | 7,800 | 2,200 | 22.0000% | 770,242 | 219,758 | 22.1978% | -0.1978 |
| `stipend` | 10,000 | 1.0000% | 7,804 | 2,196 | 21.9600% | 770,238 | 219,762 | 22.1982% | -0.2382 |
| `trust_signal_score` | 10,000 | 1.0000% | 7,762 | 2,238 | 22.3800% | 770,280 | 219,720 | 22.1939% | +0.1861 |

Mức chồng lấp theo từng cặp của các mặt nạ giá trị thiếu:

| Thiếu ở \ cũng thiếu ở | `company_age` | `stipend` | `trust_signal_score` |
| --- | ---: | ---: | ---: |
| `company_age` | 10,000 | 88 | 96 |
| `stipend` | 88 | 10,000 | 88 |
| `trust_signal_score` | 96 | 88 | 10,000 |

Số lượng cùng-thiếu quan sát được, đối chiếu với con số mà tính độc lập thống kê sẽ dự báo:

| Cặp | Thiếu ở cả hai | Kỳ vọng nếu độc lập | Quan sát - kỳ vọng | Jaccard | Hai mặt nạ giống hệt nhau |
| --- | ---: | ---: | ---: | ---: | ---: |
| `company_age` & `stipend` | 88 | 100.00 | -12.00 | 0.004419 | không |
| `company_age` & `trust_signal_score` | 96 | 100.00 | -4.00 | 0.004823 | không |
| `stipend` & `trust_signal_score` | 88 | 100.00 | -12.00 | 0.004419 | không |

- Số dòng thiếu ít nhất một trong ba cột: **29,728**.
- Số dòng thiếu cả ba: **0** (tính độc lập sẽ dự báo khoảng 1.00).
- Có cặp mặt nạ nào giống hệt nhau đến từng bit: **không**.
- Mức chồng lấp Jaccard theo cặp cao nhất: **0.004823**.

Bảng tổ hợp đầy đủ, bao gồm số lượng kỳ vọng dưới giả thiết độc lập cho từng mẫu thiếu dữ liệu quan sát được, nằm trong `missing_combination_counts.csv`. Ma trận theo cặp nằm trong `missing_overlap.csv`, phần chia nhỏ theo nhãn cho từng cột nằm trong `missing_value_relationship.csv`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- Khoảng cách lớn nhất giữa tỷ lệ gian lận ở các dòng bị thiếu và ở các dòng có giá trị là 0.2382 điểm phần trăm. Một khoảng cách gần bằng không là bằng chứng cho thấy tính thiếu dữ liệu không mang thông tin về nhãn; nó không phải là chứng minh, và nó không nói gì về mối liên hệ với các cột khác.
- Không dòng nào thiếu cả ba giá trị, và không có hai mặt nạ nào giống hệt nhau, nên ba khoảng trống này không phải là một lần rơi dữ liệu ở mức bản ghi.
- **Không có gì bị impute.** Việc đây là thiếu mang tính cấu trúc (dữ kiện đó không tồn tại với tin tuyển dụng ấy) hay là các lỗ hổng thu thập thì không thể quyết định từ dữ liệu; điều đó quyết định liệu tầng staging giữ một NULL, dùng một thành viên Dimension "unknown", hay để measure trống trong Fact table.

## 3. Validation các binary flag

**Dữ kiện quan sát được**

| Cột | dtype | Các giá trị phân biệt | Số lượng 0 | Số lượng 1 | Khác / null | % số dòng = 1 | Nghiêm ngặt {0,1} | Hằng số |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `linkedin_presence` | int64 | 0, 1 | 199,236 | 800,764 | 0 | 80.0764% | có | không |
| `website_available` | int64 | 0, 1 | 150,403 | 849,597 | 0 | 84.9597% | có | không |
| `verification_status` | int64 | 0, 1 | 300,287 | 699,713 | 0 | 69.9713% | có | không |
| `unrealistic_salary_flag` | int64 | 0 | 1,000,000 | 0 | 0 | 0.0000% | có | có |
| `payment_required` | int64 | 0, 1 | 900,095 | 99,905 | 0 | 9.9905% | có | không |
| `fake_certificate_offer` | int64 | 0, 1 | 920,170 | 79,830 | 0 | 7.9830% | có | không |
| `suspicious_email_domain` | int64 | 0, 1 | 749,433 | 250,567 | 0 | 25.0567% | có | không |
| `social_media_presence` | int64 | 0, 1 | 250,200 | 749,800 | 0 | 74.9800% | có | không |
| `is_fake_posting` | int64 | 0, 1 | 778,042 | 221,958 | 0 | 22.1958% | có | không |

Số lượng theo từng giá trị nằm trong `binary_flags.csv` (một dòng cho mỗi cột) và `binary_flag_value_counts.csv` (một dòng cho mỗi cặp cột/giá trị).

**Các vấn đề tiềm ẩn cần con người xem xét**

- Cả chín cột đều nhận giá trị nghiêm ngặt trong {0,1} và không có null, nên mỗi cột có thể được mô hình hóa thành một thuộc tính mang giá trị boolean.
- (Các) cột hằng số: `unrealistic_salary_flag`. Một cột hằng số không mang thông tin để slicing và sẽ tạo ra một Dimension degenerate chỉ có một thành viên. Chỉ gắn cờ - **không** đề xuất loại bỏ ở đây, vì một hằng số trong lần extract này vẫn có thể có ý nghĩa trong hệ thống nguồn.

## 4. Audit tính nhất quán về thanh toán

**Dữ kiện quan sát được**

| Phép kiểm tra | Số dòng | % số dòng |
| --- | ---: | ---: |
| payment_required = 0 VÀ registration_fee > 0 | 0 | 0.0000% |
| payment_required = 1 VÀ registration_fee = 0 | 0 | 0.0000% |
| payment_required = 0 VÀ registration_fee = 0 (nhất quán) | 900,095 | 90.0095% |
| payment_required = 1 VÀ registration_fee > 0 (nhất quán) | 99,905 | 9.9905% |
| registration_fee < 0 | 0 | 0.0000% |
| registration_fee là null | 0 | 0.0000% |

Thống kê `registration_fee` theo `payment_required`:

| `payment_required` | Số dòng | Phí = 0 | Phí > 0 | min | p25 | median | p75 | max | mean | std |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 900,095 | 900,095 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 1 | 99,905 | 0 | 99,905 | 50.00 | 1,284.00 | 2,520.00 | 3,763.00 | 4,999.00 | 2,523.23 | 1,430.61 |

Cả hai bảng nằm trong `payment_consistency.csv`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- Hai cột không bao giờ mâu thuẫn với nhau: không có dòng nào với `payment_required = 0` mà có phí dương, và không có dòng nào với `payment_required = 1` mà có phí bằng zero. Do đó `payment_required` có thể phục hồi được từ `registration_fee > 0` trên lần extract này.
- Điều đó làm cặp cột này hoàn toàn dư thừa **trên lần extract này**, điều quan trọng khi chọn xem flag sẽ trở thành một thuộc tính Dimension và phí trở thành một measure trong Fact, hay chỉ mang theo phí. Nó không chứng minh rằng hệ thống nguồn thực thi ràng buộc này, và không cột nào bị bỏ ở đây.
- Không tồn tại giá trị `registration_fee` âm nào.

## 5. Audit tính nhất quán về email

**Dữ kiện quan sát được**

| `recruiter_email_type` \ `suspicious_email_domain` | 0 | 1 | Tổng |
| --- | ---: | ---: | ---: |
| Corporate | 749,433 | 0 | 749,433 |
| Free | 0 | 250,567 | 250,567 |
| **Tổng** | 749,433 | 250,567 | 1,000,000 |

Cùng bảng trên, tính theo tỷ lệ trên toàn bộ số dòng:

| `recruiter_email_type` | `suspicious_email_domain` = 0 | `suspicious_email_domain` = 1 |
| --- | ---: | ---: |
| Corporate | 74.9433% | 0.0000% |
| Free | 0.0000% | 25.0567% |

Kiểm định functional dependency, theo cả hai chiều:

| Chiều | Số giá trị phân biệt của biến quyết định | Số giá trị phụ thuộc phân biệt tối đa trên mỗi khóa | Là hàm chính xác | Số dòng vi phạm | % số dòng |
| --- | ---: | ---: | ---: | ---: | ---: |
| `recruiter_email_type` -> `suspicious_email_domain` | 2 | 1 | có | 0 | 0.000000% |
| `suspicious_email_domain` -> `recruiter_email_type` | 2 | 1 | có | 0 | 0.000000% |

- Chi-square: 1,000,000.00. Cramer's V: 1.000000 (1.0 nghĩa là hai cột tương ứng một-một hoàn hảo với nhau).
- Số dòng nằm ngoài phép mapping theo mode: **0**.

Các số lượng và cả ba cơ sở tính phần trăm nằm trong `email_crosstab.csv`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- Phép mapping là **chính xác và song ánh theo cả hai chiều**: mỗi giá trị của `recruiter_email_type` tương ứng đúng một giá trị của `suspicious_email_domain` và ngược lại, với 0 dòng vi phạm trên 1,000,000 dòng và Cramer's V = 1.000000. Đây là một chứng minh toán học trên lần extract này, nên hai cột mang thông tin y hệt nhau ở đây.
- Điều nó **không** chứng minh: rằng hệ thống nguồn bảo đảm phép mapping này. `recruiter_email_type` là một nhãn có nhiều giá trị khả dĩ hơn một boolean; một lần extract trong tương lai có thể chứa một loại thứ ba. Việc mang cả hai như một thuộc tính Dimension gần như không tốn gì và giữ lại khoảng trống dự phòng đó. **Không có quyết định bỏ cột nào được đưa ra ở đây.**

## 6. Audit quan hệ của nhãn gian lận

**Dữ kiện quan sát được**

| `is_fake_posting` | Số dòng | % số dòng | min | p05 | p25 | median | p75 | p95 | max | mean | std |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 778,042 | 77.8042% | 0.00 | 0.00 | 14.40 | 26.20 | 37.00 | 47.00 | 50.00 | 25.2939 | 14.2375 |
| 1 | 221,958 | 22.1958% | 50.00 | 50.90 | 55.00 | 61.40 | 71.10 | 90.00 | 100.00 | 64.5733 | 12.1187 |

`fraud_score` được chia thành các decile, giao với nhãn:

| Dải `fraud_score` | nhãn 0 | nhãn 1 | Tổng | % số dòng | tỷ lệ nhãn 1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| (-0.001, 10.0] | 139,153 | 0 | 139,153 | 13.9153% | 0.0000% |
| (10.0, 20.0] | 142,756 | 0 | 142,756 | 14.2756% | 0.0000% |
| (20.0, 30.0] | 177,858 | 0 | 177,858 | 17.7858% | 0.0000% |
| (30.0, 40.0] | 175,390 | 0 | 175,390 | 17.5390% | 0.0000% |
| (40.0, 50.0] | 142,885 | 620 | 143,505 | 14.3505% | 0.4320% |
| (50.0, 60.0] | 0 | 100,407 | 100,407 | 10.0407% | 100.0000% |
| (60.0, 70.0] | 0 | 60,761 | 60,761 | 6.0761% | 100.0000% |
| (70.0, 80.0] | 0 | 32,915 | 32,915 | 3.2915% | 100.0000% |
| (80.0, 90.0] | 0 | 16,224 | 16,224 | 1.6224% | 100.0000% |
| (90.0, 100.0] | 0 | 11,031 | 11,031 | 1.1031% | 100.0000% |

Quét ngưỡng vét cạn trên mọi giá trị `fraud_score` quan sát được, cho quy tắc *dự đoán `is_fake_posting` = 1 khi `fraud_score` >= t*:

| Chỉ số | Giá trị |
| --- | ---: |
| Ngưỡng t tốt nhất | 50.0000 |
| Số trường hợp lệch tại t tốt nhất | 607 |
|   trong đó false positive (nhãn 0, score >= t) | 607 |
|   trong đó false negative (nhãn 1, score < t) | 0 |
| Độ chính xác tại t tốt nhất | 99.939300% |
| Có thể tái lập hoàn hảo | KHÔNG |
| `fraud_score` lớn nhất trong nhóm nhãn 0 | 50.00 |
| `fraud_score` nhỏ nhất trong nhóm nhãn 1 | 50.00 |
| Số dòng trong khoảng score chồng lấp | 1,227 |
| Mức chồng lấp theo % dataset | 0.1227% |
| Số giá trị `fraud_score` phân biệt mà cả hai lớp cùng xuất hiện | 1 |

Bảng crosstab theo decile nằm trong `fraud_score_relationship.csv`, thống kê theo từng lớp nằm trong `fraud_score_class_stats.csv`, và toàn bộ lượt quét ngưỡng (một dòng cho mỗi ngưỡng ứng viên) nằm trong `fraud_score_threshold_scan.csv`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- Ngưỡng đơn tốt nhất là `fraud_score` >= 50.0000, để lại **607 trường hợp lệch** (0.060700% số dòng: 607 false positive và 0 false negative). Không ngưỡng nào tái lập chính xác nhãn, nên `is_fake_posting` không phải là một phép cắt thuần túy của `fraud_score`.
- Sự bất đồng này không trải trên một khoảng: cả hai lớp cùng xuất hiện tại **đúng một** giá trị `fraud_score`, là 50.0000, nơi 607 dòng mang nhãn 0 và 620 dòng mang nhãn 1 (tổng cộng 1,227 dòng, 0.1227%). Ở mọi giá trị score quan sát được khác, nhãn là hằng số.
- Đó là dấu hiệu của một quy tắc biên có dạng `fraud_score` > 50.0000 (hoặc >=) với bản thân giá trị 50.0000 được giải quyết theo một cách khác - bằng một tiêu chí thứ hai, bằng phép làm tròn trước khi so sánh, hoặc một cách tùy ý. Trường hợp nào áp dụng thì không thể đọc ra từ dữ liệu và là câu hỏi dành cho nguồn. Cho đến khi có câu trả lời, hãy coi `fraud_score` = 50.0000 là vùng duy nhất mà hai cột thực sự khác nhau.
- **Không cột nào bị loại bỏ.** Cả hai vẫn khả dụng; cột nào trở thành measure trong Fact và cột nào trở thành thuộc tính Dimension là một quyết định thuộc modelling.

## 7. Audit trust signal

**Dữ kiện quan sát được**

`trust_signal_score` được phân tích đối chiếu với `verification_status`, `linkedin_presence`, `website_available`, `social_media_presence`. 990,000 dòng có đủ cả năm giá trị; 10,000 dòng bị loại khỏi mục này vì `trust_signal_score` là null. **Các dòng bị loại không được điền giá trị.**

Tương quan point-biserial và các giá trị trung bình theo nhóm:

| Chỉ báo | Pearson r | Điểm trung bình khi bằng 0 | Điểm trung bình khi bằng 1 | Chênh lệch | Hệ số OLS cộng tính |
| --- | ---: | ---: | ---: | ---: | ---: |
| `verification_status` | 0.278794 | 49.5913 | 59.5437 | 9.9524 | 9.952744 |
| `linkedin_presence` | 0.243830 | 48.5577 | 58.5459 | 9.9882 | 9.988511 |
| `website_available` | -0.001497 | 56.6141 | 56.5455 | -0.0686 | -0.042025 |
| `social_media_presence` | 0.001566 | 56.5115 | 56.5706 | 0.0592 | 0.035713 |
| `(hệ số chặn)` | n/a | n/a | n/a | n/a | 41.601641 |

Mọi tổ hợp quan sát được của bốn chỉ báo (đây là mô hình saturated - nếu khoảng biến thiên trong mỗi nhóm đều bằng không ở mọi nơi thì điểm số là một hàm tất định của bốn flag):

| `verification_status` | `linkedin_presence` | `website_available` | `social_media_presence` | Số dòng | % số dòng | mean | std | min | max | khoảng biến thiên | số điểm phân biệt |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 | 2,231 | 0.2254% | 41.2713 | 15.571299 | 0.0000 | 90.0000 | 90.000000 | 633 |
| 0 | 0 | 0 | 1 | 6,549 | 0.6615% | 41.7213 | 15.272969 | 0.0000 | 93.4000 | 93.400000 | 779 |
| 0 | 0 | 1 | 0 | 12,724 | 1.2853% | 41.6875 | 15.208161 | 0.0000 | 88.6000 | 88.600000 | 813 |
| 0 | 1 | 0 | 0 | 9,021 | 0.9112% | 51.5934 | 15.197238 | 0.0000 | 100.0000 | 100.000000 | 801 |
| 1 | 0 | 0 | 0 | 5,255 | 0.5308% | 51.5982 | 15.146531 | 0.0000 | 97.3000 | 97.300000 | 748 |
| 0 | 0 | 1 | 1 | 37,707 | 3.8088% | 41.5668 | 15.140824 | 0.0000 | 95.5000 | 95.500000 | 869 |
| 0 | 1 | 1 | 0 | 50,368 | 5.0877% | 51.5454 | 15.159028 | 0.0000 | 100.0000 | 100.000000 | 949 |
| 0 | 1 | 0 | 1 | 26,725 | 2.6995% | 51.5563 | 15.234000 | 0.0000 | 100.0000 | 100.000000 | 915 |
| 1 | 0 | 1 | 0 | 29,580 | 2.9879% | 51.4180 | 15.319693 | 0.0000 | 100.0000 | 100.000000 | 917 |
| 1 | 0 | 0 | 1 | 15,428 | 1.5584% | 51.6471 | 15.155436 | 0.0000 | 100.0000 | 100.000000 | 866 |
| 1 | 1 | 0 | 0 | 21,196 | 2.1410% | 61.5809 | 15.105733 | 2.9000 | 100.0000 | 97.100000 | 847 |
| 0 | 1 | 1 | 1 | 151,888 | 15.3422% | 51.5944 | 15.246157 | 0.0000 | 100.0000 | 100.000000 | 986 |
| 1 | 0 | 1 | 1 | 87,778 | 8.8665% | 51.5631 | 15.207905 | 0.0000 | 100.0000 | 100.000000 | 974 |
| 1 | 1 | 0 | 1 | 62,410 | 6.3040% | 61.5802 | 15.155975 | 0.0000 | 100.0000 | 100.000000 | 915 |
| 1 | 1 | 1 | 0 | 117,285 | 11.8470% | 61.5092 | 15.173402 | 0.0000 | 100.0000 | 100.000000 | 937 |
| 1 | 1 | 1 | 1 | 353,855 | 35.7429% | 61.5323 | 15.194943 | 0.0000 | 100.0000 | 100.000000 | 979 |

| Chỉ số | Giá trị |
| --- | ---: |
| Số tổ hợp chỉ báo quan sát được | 16 trên 16 tổ hợp khả dĩ |
| Khoảng biến thiên lớn nhất của điểm số trong một tổ hợp | 100.000000 |
| Độ lệch chuẩn lớn nhất trong một tổ hợp | 15.571299 |
| Số điểm phân biệt nhiều nhất trong một tổ hợp | 986 |
| R^2, mô hình saturated (tổ hợp -> điểm số) | 0.13719010 |
| R^2, mô hình cộng tính (tổng có trọng số của bốn flag) | 0.13718609 |
| Độ lệch chuẩn phần dư, mô hình cộng tính | 15.198586 |
| Phần dư tuyệt đối lớn nhất, mô hình cộng tính | 61.578609 |
| Tương quan của điểm số với `is_fake_posting` | -0.386458 |

Bảng theo nhóm nằm trong `trust_signal_relationship.csv` và các tương quan nằm trong `trust_signal_correlations.csv`.

**Bằng chứng, không phải một quyết định**

- Điểm số biến thiên ngay trong từng tổ hợp flag (khoảng biến thiên trong nhóm lớn nhất 100.000000, độ lệch chuẩn trong nhóm lớn nhất 15.571299), nên nó **không** phải là một hàm tất định chỉ của bốn chỉ báo này.
- Bốn flag cùng nhau giải thích R^2 = 0.137190 phương sai của điểm số trong mô hình saturated, và R^2 = 0.137186 khi dùng một tổng cộng tính có trọng số đơn giản. Khoảng cách giữa hai con số là phần phụ thuộc vào tương tác giữa các flag; phần còn lại phụ thuộc vào thứ gì đó không nằm trong tập cột này.
- Điều mục này **không** quyết định: liệu `trust_signal_score` có nên được giữ song song với các chỉ báo. Một measure suy dẫn vẫn có thể đáng lưu trong Fact table vì sự thuận tiện khi truy vấn. Đó là một quyết định thuộc modelling.

## 8. Audit tính hợp lý của tuổi công ty / tuổi domain

**Dữ kiện quan sát được**

| Chỉ số | Giá trị |
| --- | ---: |
| `company_age_min` | 1 |
| `company_age_max` | 39 |
| `company_age_median` | 20 |
| `company_age_null` | 10,000 |
| `domain_age_months_min` | 1 |
| `domain_age_months_max` | 500 |
| `domain_age_months_median` | 240 |
| `domain_age_months_null` | 0 |
| `rows_comparable` | 990,000 |
| `rows_domain_older_than_company` | 469,297 |
| `pct_of_all_rows` | 46.9297 |
| `pct_of_comparable_rows` | 47.4037 |
| `excess_months_min` | 1 |
| `excess_months_median` | 10 |
| `excess_months_max` | 73 |
| `excess_months_mean` | 12.0821 |
| `pearson_r_company_months_vs_domain_months` | 0.9940 |
| `domain_older_label_0` | 365,049 |
| `domain_older_label_1` | 104,248 |
| `domain_older_label_1_rate_pct` | 22.2137 |

Bảng đầy đủ trong `company_domain_age.csv`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- `company_age` trải từ 1 đến 39 (năm); `domain_age_months` trải từ 1 đến 500 (tháng, tức 0.1 đến 41.7 năm).
- 469,297 dòng (46.9297% toàn bộ số dòng, 47.4037% số dòng có cả hai giá trị) có `domain_age_months` lớn hơn `company_age * 12`.
- **Những dòng này không bị gọi là không hợp lệ.** Một domain có thể chính đáng có trước công ty đang dùng nó: domain được mua lại, việc đổi thương hiệu, domain đỗ (parked) và việc đăng ký bởi công ty mẹ đều tạo ra mẫu này. Con số được báo cáo để một con người có thể quyết định liệu độ lớn đó có hợp lý với nguồn này hay không.
- Mức vượt lớn nhất là 73 tháng (6.1 năm) so với tuổi của công ty. Việc một mức vượt cỡ đó có hợp lý hay không là một phán xét về nguồn, không phải điều mà dữ liệu giải quyết được.

## 9. Validation khoảng giá trị của các điểm số

**Dữ kiện quan sát được**

| Cột | Min quan sát được | Max quan sát được | < 0 | > 100 | Ngoài 0-100 | Số null | Số giá trị phân biệt | Nằm trong 0-100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `vague_description_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 101 | có |
| `urgency_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 101 | có |
| `keyword_spam_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 101 | có |
| `emotional_manipulation_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 101 | có |
| `phishing_language_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 100 | có |
| `trust_signal_score` | 0.00 | 100.00 | 0 | 0 | 0 | 10,000 | 1,001 | có |
| `fraud_score` | 0.00 | 100.00 | 0 | 0 | 0 | 0 | 1,001 | có |

Bảng đầy đủ trong `score_range_validation.csv`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- Cả bảy cột score đều nằm trong 0-100. **0 giá trị ngoài khoảng.** Do đó khoảng 0-100 an toàn để khai báo thành một check constraint ở tầng staging.
- Một giá trị nằm trong 0-100 không đồng nghĩa với việc giá trị đó là đúng; mục này chỉ validation khoảng giá trị.

## 10. Các phép kiểm tra tính hợp lý về số học

**Dữ kiện quan sát được**

| Cột | Số âm | Số zero | % zero | min | median | max | Ngưỡng dưới | Ngưỡng trên | Outlier theo IQR | % outlier | Số null |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `company_age` | 0 | 0 | 0.0000% | 1.00 | 20.00 | 39.00 | -20.00 | 60.00 | 0 | 0.0000% | 10,000 |
| `stipend` | 0 | 0 | 0.0000% | 2,000.00 | 34,984.00 | 110,428.00 | -5,583.50 | 75,548.50 | 3,348 | 0.3348% | 10,000 |
| `registration_fee` | 0 | 900,095 | 90.0095% | 0.00 | 0.00 | 4,999.00 | 0.00 | 0.00 | 99,905 | 9.9905% | 0 |
| `job_description_length` | 0 | 0 | 0.0000% | 100.00 | 1,799.00 | 5,000.00 | 183.00 | 3,415.00 | 7,040 | 0.7040% | 0 |
| `grammatical_errors` | 0 | 49,716 | 4.9716% | 0.00 | 3.00 | 14.00 | -1.00 | 7.00 | 11,891 | 1.1891% | 0 |
| `recruiter_experience_years` | 0 | 49,615 | 4.9615% | 0.00 | 5.00 | 19.60 | -3.00 | 13.00 | 3,585 | 0.3585% | 0 |
| `recruiter_response_time_hours` | 0 | 0 | 0.0000% | 1.00 | 18.00 | 63.90 | -9.20 | 45.20 | 3,217 | 0.3217% | 0 |

Các ngưỡng là biên 1.5x khoảng tứ phân vị theo thông lệ. Thống kê đầy đủ (mean, std, các tứ phân vị, số outlier theo từng phía) nằm trong `numeric_sanity.csv`.

**Các vấn đề tiềm ẩn cần con người xem xét**

- Không cột nào trong tập này chứa giá trị âm.
- (Các) cột có chứa zero: `registration_fee`, `grammatical_errors`, `recruiter_experience_years`. Một giá trị zero có thể là một phép đo thực hoặc một placeholder cho "không rõ"; không thể phân biệt hai điều này từ dữ liệu. Điều này quan trọng nhất với `registration_fee`, nơi zero có ý nghĩa (xem mục 4).
- Tổng cộng 128,986 quan sát nằm ngoài ngưỡng 1.5x IQR. Ngưỡng IQR là một công cụ sàng lọc, không phải một kết luận: một đuôi phải dài ở stipend hay ở thời gian phản hồi là chuyện thường. **Không outlier nào bị loại bỏ hay chặn ngưỡng.**
- Ngưỡng này **vô nghĩa** với `registration_fee`, nơi tứ phân vị thứ nhất và thứ ba đều bằng 0, nên khoảng tứ phân vị bằng 0 và cả hai ngưỡng thu về 0. Khi đó mọi giá trị khác zero đều bị đếm là outlier theo cách cấu tạo. Hãy đọc những con số đó là "số dòng có giá trị khác zero", không phải là các quan sát cực trị. Nếu loại các cột này ra, có 29,081 quan sát nằm ngoài ngưỡng.

## 11. Ứng viên cho định danh dòng

**Dữ kiện quan sát được**

| Cột | Số giá trị phân biệt | Tính duy nhất | Giá trị phổ biến nhất xuất hiện | Số null | Unique key |
| --- | ---: | ---: | ---: | ---: | --- |
| `company_name` | 535,938 | 53.5938% | 1,248 | 0 | không |
| `stipend` | 73,830 | 7.3830% | 13,752 | 10,000 | không |
| `registration_fee` | 4,951 | 0.4951% | 900,095 | 0 | không |
| `job_description_length` | 3,946 | 0.3946% | 2,325 | 0 | không |
| `posting_date` | 3,287 | 0.3287% | 366 | 0 | không |
| `fraud_score` | 1,001 | 0.1001% | 51,586 | 0 | không |
| `trust_signal_score` | 1,001 | 0.1001% | 2,495 | 10,000 | không |
| `recruiter_response_time_hours` | 595 | 0.0595% | 44,700 | 0 | không |
| `domain_age_months` | 500 | 0.0500% | 8,630 | 0 | không |
| `recruiter_experience_years` | 183 | 0.0183% | 49,615 | 0 | không |

Mười ứng viên có cardinality cao nhất được trình bày ở đây; toàn bộ 33 cột cùng các tổ hợp đã kiểm tra nằm trong `key_candidates.csv`.

- **Không có natural key dạng cột đơn nào.** Cột đặc trưng nhất, `company_name`, có 535,938 giá trị phân biệt trên 1,000,000 dòng (53.5938% duy nhất), nên nó có lặp lại.
- Không tổ hợp cột nào đã được kiểm tra là duy nhất.

**Đề xuất (chỉ dành cho tầng staging về sau)**

- **Không key nào được tạo ra và không có gì được thêm vào dữ liệu raw.** File CSV raw không thay đổi.
- Cho tầng staging: sinh một `source_row_id` từ thứ tự dòng gốc trong file (1..N theo thứ tự đọc, tăng dần, trước mọi phép lọc hay sắp xếp) và mang nó theo như một cột phục vụ data lineage. Đó là cách ổn định duy nhất để trỏ từ một dòng trong Data Warehouse trở về một dòng cụ thể của lần extract này, xét việc không tồn tại natural key nào.
- Vì nó đến từ thứ tự file, `source_row_id` chỉ có ý nghĩa khi đi cùng sha256 của file; hãy ghi cả hai vào bảng audit của lần load. Nó là một tay cầm phục vụ data lineage, không phải một business key, và không nên được dùng để join giữa các lần extract.

## 12. Các chỉ báo cần kiểm chứng về provenance của nguồn

Mục này chỉ liệt kê **những quy luật khách quan, đo được**. Nó **không** kết luận liệu dataset là dữ liệu tổng hợp hay dữ liệu thực - câu hỏi đó không thể trả lời từ dữ liệu và cần tài liệu về nguồn, phương pháp thu thập và giấy phép. Mỗi mục dưới đây là một tính chất bất thường trong dữ liệu được thu thập một cách tự nhiên và do đó đáng được xác nhận lại với nguồn.

**Dữ kiện quan sát được**

*Số dòng*

| Quan sát | Giá trị | Ghi chú |
| --- | ---: | --- |
| số dòng | 1,000,000 | đúng bằng 1,000,000 |

*Mật độ phủ của ngày tháng*

| Quan sát | Giá trị | Ghi chú |
| --- | ---: | --- |
| số date phân biệt quan sát được | 3,287 |  |
| số ngày dương lịch trong khoảng trải | 3,287 |  |
| tỷ lệ ngày dương lịch có ít nhất một dòng | 100 | 100% nghĩa là không có ngày trống nào trong khoảng |
| số dòng mỗi date - min | 247 |  |
| số dòng mỗi date - max | 366 |  |
| số dòng mỗi date - mean | 304.2288 |  |
| số dòng mỗi date - std | 16.9621 |  |
| số dòng mỗi date - hệ số biến thiên | 0.0558 | giá trị thấp nghĩa là các date được nạp gần như đồng đều |
| tỷ lệ ngày trong tuần nhỏ nhất | 14.2196 | phân bố đều trên 7 ngày trong tuần sẽ là 14.2857% |
| tỷ lệ ngày trong tuần lớn nhất | 14.3617 |  |

*Mức cân bằng của các cột categorical*

| Quan sát | Giá trị | Ghi chú |
| --- | ---: | --- |
| internship_title: số giá trị phân biệt | 9 |  |
| internship_title: độ lệch lớn nhất so với tỷ lệ đều (pp) | 0.0609 | tỷ lệ đều sẽ là 11.1111% |
| employment_type: số giá trị phân biệt | 4 |  |
| employment_type: độ lệch lớn nhất so với tỷ lệ đều (pp) | 0.0700 | tỷ lệ đều sẽ là 25.0000% |
| work_mode: số giá trị phân biệt | 3 |  |
| work_mode: độ lệch lớn nhất so với tỷ lệ đều (pp) | 21.6006 | tỷ lệ đều sẽ là 33.3333% |
| industry: số giá trị phân biệt | 9 |  |
| industry: độ lệch lớn nhất so với tỷ lệ đều (pp) | 0.0692 | tỷ lệ đều sẽ là 11.1111% |
| location: số giá trị phân biệt | 9 |  |
| location: độ lệch lớn nhất so với tỷ lệ đều (pp) | 0.0552 | tỷ lệ đều sẽ là 11.1111% |
| company_size: số giá trị phân biệt | 4 |  |
| company_size: độ lệch lớn nhất so với tỷ lệ đều (pp) | 9.9640 | tỷ lệ đều sẽ là 25.0000% |
| recruiter_email_type: số giá trị phân biệt | 2 |  |
| recruiter_email_type: độ lệch lớn nhất so với tỷ lệ đều (pp) | 24.9433 | tỷ lệ đều sẽ là 50.0000% |

*Mẫu thiếu dữ liệu*

| Quan sát | Giá trị | Ghi chú |
| --- | ---: | --- |
| số cột có giá trị thiếu | 3 |  |
| số lượng thiếu | 10000, 10000, 10000 | số lượng giống hệt nhau giữa các cột sẽ là một mẫu, không phải sự trùng hợp |
| tất cả số lượng thiếu đều giống hệt nhau | có |  |
| phần trăm thiếu | 1.0000%, 1.0000%, 1.0000% |  |
| số dòng thiếu ở cả ba cột | 0 | tính độc lập sẽ dự báo khoảng 1.00 |

*Bản trùng*

| Quan sát | Giá trị | Ghi chú |
| --- | ---: | --- |
| số dòng trùng khớp chính xác (cả 33 cột) | 0 | đếm bằng duplicated(keep='first'); không dòng nào bị loại bỏ |

*Độ sạch của chuỗi*

- Số cột text được kiểm tra: 9.
- Số dòng bị ảnh hưởng bởi whitespace ở đầu/cuối, giá trị rỗng-sau-khi-strip, ký tự non-ASCII hay dấu cách đôi, tính tổng trên mọi cột text: **0**.
- Mọi cột text đều không có cả bốn lỗi trên. Không có whitespace ở đầu hay cuối, không có giá trị rỗng-sau-khi-strip, không có ký tự non-ASCII và không có dấu cách đôi ở bất kỳ đâu trong các cột text.

Danh sách quan sát đầy đủ nằm trong `provenance_indicators.csv`.

**Những gì cần được xác nhận từ nguồn, không phải từ dữ liệu**

- Số dòng đúng bằng 1,000,000. Các lần extract được thu thập tự nhiên rất ít khi là số chẵn tròn; một con số tròn thường có nghĩa là một mức chặn khi lấy mẫu, một tham số sinh dữ liệu, hoặc một phép cắt ngắn có chủ đích. Trường hợp nào áp dụng là câu hỏi dành cho người đã tạo ra file này.
- Các dòng phân bố trên các date với hệ số biến thiên 0.0558 và 100.00% số ngày dương lịch trong khoảng đều có dữ liệu. Việc nạp dữ liệu gần như đồng đều trên mọi ngày dương lịch, kể cả cuối tuần và ngày lễ, không điển hình cho hoạt động đăng tin tuyển dụng.
- 4 trên 7 cột categorical có cardinality thấp nằm trong khoảng một điểm phần trăm so với một phép chia hoàn toàn đồng đều (độ lệch lớn nhất trong số đó: 0.0700 pp): `employment_type`, `industry`, `internship_title`, `location`. Một phân bố đồng đều trên mọi giá trị category là hiếm trong dữ liệu quan sát được, nơi một số chức danh, ngành và thành phố luôn chiếm ưu thế.
- Các cột cardinality thấp còn lại **không** gần đồng đều: `company_size` (9.9640 pp), `recruiter_email_type` (24.9433 pp), `work_mode` (21.6006 pp). Chúng được liệt kê cho đầy đủ, như bằng chứng đối lập với luận điểm ở trên.
- Ba cột không đầy đủ bị thiếu ở đúng cùng một số dòng, ở đúng 1.0000% mỗi cột, với các mức chồng lấp khớp với điều mà tính độc lập dự báo (mục 2). Việc thiếu dữ liệu rơi đúng vào một tỷ lệ phần trăm tròn một cách độc lập ở ba cột là một mẫu, không phải một sự tình cờ trong thu thập.
- Trên 1,000,000 dòng và 33 cột không có một dòng trùng khớp chính xác nào.
- Các trường text hoàn toàn không có lỗi về whitespace, encoding hay chữ hoa/thường. Các trường văn bản tự do do con người nhập thường có ít nhiều lỗi như vậy.

**Điều dứt khoát không kết luận**: không mục nào ở trên xác lập rằng dữ liệu là dữ liệu tổng hợp. Mỗi mục đều nhất quán ngang nhau với một dataset thực đã được làm sạch, lấy mẫu và chuẩn hóa từ phía trên. Hãy giải quyết điều này bằng cách hỏi về provenance của file; cho đến lúc đó, hãy coi tính thực tế của dataset là chưa được kiểm chứng, chứ không phải là đã được xác nhận hay đã bị phủ nhận.

## Tuyên bố phạm vi

- `fake_internship_detection_dataset.csv` được mở ở chế độ chỉ đọc. sha256 của nó được kiểm chứng trước và sau lần chạy này.
- Không dòng nào bị xóa, kể cả các dòng có ngày ở tương lai. Không giá trị nào bị impute, chặn ngưỡng, cắt, làm tròn, đổi kiểu hay encode. Không cột nào bị bỏ, kể cả những cột đã được chỉ ra ở trên là có thể suy ra từ cột khác. Không key nào được thêm vào dữ liệu raw.
- Đề xuất duy nhất trong tài liệu này là `source_row_id` ở mục 11, và nó áp dụng cho tầng staging, không áp dụng cho file raw.
