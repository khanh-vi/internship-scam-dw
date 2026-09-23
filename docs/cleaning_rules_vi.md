# Quy tắc Làm sạch — `internship-scam-dw`

| Hạng mục | Giá trị |
| --- | --- |
| File nguồn | `data/raw/fake_internship_detection_dataset.csv` |
| sha256 nguồn | `3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398` |
| Số dòng × số cột của nguồn | 1,000,000 × 33 |
| Ngày audit / tham chiếu | **2026-09-23** |
| Cơ sở bằng chứng | `results/profiling/`, `results/audit/` |
| Tài liệu đi kèm | [data_dictionary_vi.md](data_dictionary_vi.md) |
| Trạng thái | **Đã phê duyệt.** Đã được chủ project rà soát và ký xác nhận. |

Các quy tắc này có tính ràng buộc với bước load staging. Chúng được rút ra từ các
giai đoạn profiling và audit đã hoàn tất và đã được một con người phê duyệt.
**Chúng không được mở rộng, diễn giải lại hay bổ sung bằng các quyết định làm sạch
mới trong quá trình triển khai.** Một lỗi mà các quy tắc này không bao phủ sẽ được
báo lên cấp trên để có quyết định; nó không được sửa ngay tại chỗ.

---

## Từ vựng về các tầng được dùng xuyên suốt

Ba loại trường được phân biệt ở mọi nơi trong tài liệu này, và sự phân biệt này
mang tính then chốt:

| Thuật ngữ | Ý nghĩa |
| --- | --- |
| **Trường nguồn** | Một trong 33 cột hiện diện về mặt vật lý trong file CSV raw. |
| **Trường suy dẫn ở staging** | Một trường được tạo ra bởi bước load staging. Nó chỉ tồn tại trong staging, không bao giờ trong file raw. Có đúng **hai** trường: `source_row_id` và `is_future_posting`. |
| **Quyết định thuộc dimensional model** | Một lựa chọn được hoãn lại một cách tường minh cho bước thiết kế star schema về sau. Được ghi lại ở đây như một câu hỏi mở, **không** được xử lý. |

Một quy tắc áp dụng cho một trường nguồn không bao giờ cho phép thay đổi file raw.
Một trường suy dẫn ở staging luôn được đánh dấu rõ như vậy. Một quyết định được
hoãn lại không bao giờ bị âm thầm giải quyết.

---

## 1. Mục đích

Tài liệu này nêu rõ, với mọi cột nguồn và mọi nhóm cột, chính xác điều mà bước load
staging làm và không làm, và tại sao.

Nó tồn tại để làm cho pipeline **có thể audit và tái lập được**. Cụ thể:

1. Nó ghi lại các quyết định làm sạch đã được phê duyệt, để việc triển khai là
   sao chép lại chứ không phải phán xét.
2. Nó ghi lại các biến đổi đã bị **dứt khoát loại bỏ**, để một người đọc về sau
   phân biệt được giữa "không làm" và "bị quên".
   Đây là mục đích của §11.
3. Nó gắn mỗi quyết định với phép đo biện minh cho quyết định đó, để một phản biện
   với một quyết định có thể được giải quyết bằng cách chạy lại bằng chứng chứ
   không phải bằng tranh luận.
4. Nó xác định ranh giới giữa staging và dimensional modelling, để các lựa chọn về
   modelling không bị đưa lậu vào tầng làm sạch.

Phạm vi của tài liệu này là bước **raw → staging**. Nó không bao phủ dimensional
model, việc điều phối ETL hay bất kỳ định nghĩa OLAP cube nào.

---

## 2. Chính sách bất biến của dữ liệu raw

**`data/raw/` là bất biến. Quy tắc này không có ngoại lệ.**

| Quy tắc | Chi tiết |
| --- | --- |
| R2.1 | File CSV raw **không bao giờ** bị sửa đổi, ghi đè, lưu lại, encode lại, sắp xếp hay đổi thứ tự. |
| R2.2 | File CSV raw được mở ở chế độ **chỉ đọc**. Không tiến trình nào trong project này giữ một write handle tới nó. |
| R2.3 | **Không cột nào được thêm vào file raw** — đặc biệt là không thêm `source_row_id`, cột này chỉ tồn tại ở staging (§9). |
| R2.4 | Toàn bộ **1,000,000 dòng nguồn được bảo toàn** vào staging. Không dòng nào bị bỏ, lọc, lấy mẫu hay loại trùng vì bất kỳ lý do nào. |
| R2.5 | Toàn bộ **33 cột nguồn được bảo toàn** vào staging, bao gồm các cột đã được chứng minh dư thừa (§8) và cột hằng số `unrealistic_salary_flag`. |
| R2.6 | sha256 của file được kiểm chứng **trước và sau** mỗi lần chạy. Một sự không khớp là lỗi nghiêm trọng, không phải một cảnh báo. |
| R2.7 | Đầu ra của việc làm sạch được ghi vào một **dataset staging riêng biệt**. Staging không bao giờ ghi trở lại vào `data/raw/`. |

sha256 kỳ vọng là
`3463d99be6580df352928d982eac995ac466c10f037c4f9252a5ceeb8f3b1398`. Cả lần chạy
profiling và lần chạy audit đều đã kiểm chứng nó và để lại file giống hệt đến từng
byte.

**Yêu cầu về việc đọc.** `company_name` chứa dấu phẩy nhúng bên trong và được đặt
trong ngoặc kép trong CSV (ví dụ `"Russell, Medina and Evans"`). File **phải** được
đọc bằng một parser CSV nhận biết dấu ngoặc kép. Việc tách theo delimiter một cách
ngây thơ sẽ đẩy lệch mọi trường sau `company_name` và âm thầm làm hỏng toàn bộ các
cột phía sau — điều này đã được xác nhận trên thực tế, không phải giả định.

---

## 3. Triết lý làm sạch

Nguyên tắc chi phối là **bảo toàn hơn là hiệu chỉnh**.

Đây là một pipeline Data Warehouse và OLAP. Công việc của staging là làm cho nguồn
trở nên load được, có kiểu và truy vết được — không phải cải thiện nó. Mọi biến đổi
đều là một sự mất thông tin mà một nhà phân tích về sau không thể hoàn tác.

Năm quy tắc suy ra từ đó:

**3.1 — Bằng chứng đi trước hành động.** Không cột nào bị làm sạch chỉ vì nó *trông*
có vẻ bẩn. Các giai đoạn profiling và audit đã đo dataset, và chỉ một lỗi đã được đo
mới biện minh cho một thay đổi. Ở nơi phép đo không tìm thấy lỗi nào, cột được
truyền qua mà không bị chạm tới.

**3.2 — Một bất thường không phải là một lỗi.** Nhiều mẫu thực sự đáng ngạc nhiên đã
được tìm thấy: domain già hơn công ty của nó, một flag hằng số, tỷ lệ 46.9% trên một
bất đẳng thức giữa các trường, các phân phối categorical gần đồng đều, một đuôi dài
ở `grammatical_errors`. Không mẫu nào là *bằng chứng về tính không hợp lệ*. Một giá
trị chưa được giải thích thì được bảo toàn và tài liệu hóa; nó không bị hiệu chỉnh
thành một thứ gì đó giải thích được.

**3.3 — Sự dư thừa được tài liệu hóa, không được giải quyết.** Hai cặp cột đã được
chứng minh dư thừa về mặt toán học trên lần extract này (§8). Không cặp nào bị bỏ.
Một tính chất đúng trên 1,000,000 dòng của một lần extract không chứng minh rằng hệ
thống nguồn thực thi nó, và việc bỏ một cột là không thể hoàn tác trong khi việc
mang nó theo gần như miễn phí. Quyết định đó thuộc về dimensional modelling.

**3.4 — Thiếu nghĩa là thiếu.** Một NULL là một dữ kiện về dữ liệu. Việc thay nó
bằng một mean, một median hay một zero tạo ra một giá trị chưa bao giờ được quan sát
và che khoảng trống đó khỏi mọi bên tiêu thụ phía sau (§5).

**3.5 — Staging không phải feature engineering.** Không có encoding, scaling,
resampling hay xử lý văn bản nào diễn ra ở đây (§11). Những việc đó thuộc về một
workflow modelling, mà đây thì không phải.

**Hệ quả.** Dataset staging là một bản thể hiện **trung thực, có kiểu, có thể định
địa chỉ** của lần extract raw: cùng 1,000,000 dòng, cùng 33 cột nguồn, cùng các giá
trị, cộng thêm hai trường về data lineage/chất lượng và một báo cáo validation.

---

## 4. Quy tắc làm sạch theo cột và nhóm cột

### 4.1 Định danh dòng — suy dẫn ở staging

Xem §9 cho chính sách data lineage đầy đủ.

| Quy tắc | Chi tiết |
| --- | --- |
| R4.1.1 | Thêm **`source_row_id`** chỉ vào dataset **staging**. |
| R4.1.2 | Nó bắt đầu từ **1** và theo **thứ tự dòng gốc trong CSV**, được gán trước mọi phép lọc, sắp xếp hay biến đổi. |
| R4.1.3 | Nó **không** được thêm vào file raw. |
| R4.1.4 | Kết quả kỳ vọng: các giá trị 1…1,000,000, liên tục, duy nhất, không null. |

**Vì sao** — profiling đã kiểm tra cả 33 cột cùng các tổ hợp: **không tồn tại
natural key dạng cột đơn nào** và không cột nào gần-duy nhất (tỷ lệ ≥ 0.99). Cột
đặc trưng nhất, `company_name`, chỉ duy nhất 53.5938%. Không có một surrogate key
thì không có cách nào để định địa chỉ một dòng riêng lẻ.

### 4.2 `posting_date`

| Quy tắc | Chi tiết |
| --- | --- |
| R4.2.1 | Parse `posting_date` thành một **date thực sự**, không phải text. |
| R4.2.2 | Lưu và xuất nó ở dạng **ISO `YYYY-MM-DD`**. |
| R4.2.3 | Mọi giá trị parse thất bại **phải được báo cáo** trong đầu ra validation. Nó không bị coerce, gán giá trị mặc định hay âm thầm loại bỏ. |
| R4.2.4 | **Các ngày ở tương lai KHÔNG bị loại bỏ.** |
| R4.2.5 | Thêm flag suy dẫn ở staging **`is_future_posting`**: `1` khi `posting_date > 2026-09-23`, ngược lại `0`. |
| R4.2.6 | Mốc cắt **2026-09-23** là **ngày audit/tham chiếu** — một hằng số cố định đã được tài liệu hóa. |

**Bằng chứng** — 100.00% giá trị parse được theo `%Y-%m-%d`; 0 giá trị không parse
được. Khoảng 2018-01-01 đến 2026-12-31. **30,246 dòng (3.0246%)** có ngày sau ngày
tham chiếu, trên 99 date phân biệt.

**Vì sao các ngày ở tương lai được giữ lại** — chúng không phải một lần parse thất
bại và không phải một sự hỏng dữ liệu; chúng chỉ đơn giản có ngày ở phía trước ngày
tham chiếu. Tỷ lệ gian lận của chúng (22.2939%) không phân biệt được với tỷ lệ tổng
thể (22.1958%), nên việc loại bỏ chúng sẽ bỏ đi 3% dataset mà không loại bỏ được bất
kỳ lỗi nhận diện được nào. Việc gắn cờ bảo toàn thông tin và cho phép mọi phép phân
tích loại trừ chúng một cách tường minh.

**Vì sao mốc cắt là một hằng số cố định, không phải "hôm nay"** — việc suy ra cờ này
từ ngày hiện tại sẽ làm dataset staging không tái lập được: số dòng được gắn cờ sẽ
trôi đi ở mỗi lần chạy và không đầu ra nào có thể so sánh được với đầu ra khác. Việc
ghim nó vào 2026-09-23 làm cho `is_future_posting` trở nên tất định và tái lập được,
và nó khớp với ngày mà bằng chứng audit được tạo ra.

### 4.3 Các cột text và categorical

Áp dụng cho: `internship_title`, `employment_type`, `work_mode`, `industry`,
`location`, `company_name`, `company_size`, `recruiter_email_type`.

| Quy tắc | Chi tiết |
| --- | --- |
| R4.3.1 | **Bảo toàn các giá trị gốc nguyên văn.** |
| R4.3.2 | **Không** chuyển thành chữ thường hay thay đổi chữ hoa/thường theo bất kỳ cách nào. |
| R4.3.3 | **Không** trim — **trừ khi** validation bất ngờ tìm thấy một lỗi, khi đó lỗi được báo lên cấp trên, không được âm thầm sửa. |
| R4.3.4 | **Không** mapping category. |
| R4.3.5 | **Không** gộp category. |

**Bằng chứng** — cả tám cột đều được đo là sạch trên mọi chiều của chất lượng chuỗi:

| Phép kiểm tra | Kết quả trên cả 8 cột |
| --- | ---: |
| Giá trị có whitespace đệm | **0** |
| Chuỗi rỗng | **0** |
| Giá trị chỉ gồm whitespace | **0** |
| Ký tự non-ASCII | **0** |
| Dấu cách đôi | **0** |
| Bản trùng khác nhau về chữ hoa/thường | **0** |

Với mỗi cột trong số này, `phân biệt` = `phân biệt (không phân biệt hoa/thường)` =
`phân biệt (đã trim + không phân biệt hoa/thường)`. Không có lỗi nào để làm sạch.

**Vì sao việc trim vẫn bị cấm theo mặc định** — một phép `TRIM` hay `LOWER` được áp
dụng "cho chắc" là một biến đổi vô điều kiện không có biện minh nào từ phép đo. Nếu
một lần extract trong tương lai thực sự có whitespace đệm, R4.3.3 đòi hỏi bước
validation phải **làm nó lộ ra** để một con người quyết định, thay vì để pipeline
âm thầm hấp thụ một thay đổi trong hành vi của nguồn.

**Vì sao các category không bị gộp** — các miền giá trị đều nhỏ và được liệt kê đầy
đủ trong data dictionary. Việc gộp sẽ đòi hỏi một phán xét nghiệp vụ mà chưa ai đưa
ra. Cụ thể hai trường hợp:
`company_size` trộn một nhãn về độ trưởng thành (`Startup`) với các nhãn về quy mô
(`Small`/`Medium`/`Enterprise`), nên **không thứ hạng ordinal nào bị áp đặt**; và
mẫu `<Họ> <Hậu tố>` xuất hiện lặp lại của `company_name` có nghĩa là **sự tương đồng
về tên không được coi là đồng nhất về danh tính công ty** — không có fuzzy matching
hay entity resolution nào được thực hiện.

### 4.4 Giá trị numeric bị thiếu

Được bao phủ bởi chính sách về giá trị thiếu ở §5. Áp dụng cho `company_age`,
`stipend` và `trust_signal_score`.

### 4.5 Các chỉ báo binary

Áp dụng cho: `linkedin_presence`, `website_available`, `verification_status`,
`unrealistic_salary_flag`, `payment_required`, `fake_certificate_offer`,
`suspicious_email_domain`, `social_media_presence`, `is_fake_posting`.

| Quy tắc | Chi tiết |
| --- | --- |
| R4.5.1 | **Bảo toàn cách biểu diễn 0/1.** Không chuyển thành boolean, `Y`/`N`, `true`/`false` hay bất kỳ nhãn nào. |
| R4.5.2 | **Validation** rằng các giá trị vẫn nằm nghiêm ngặt trong `{0,1}`. |
| R4.5.3 | **Không** cân bằng lại, resample hay đánh lại trọng số. |
| R4.5.4 | **Không** loại bỏ dòng trên cơ sở bất kỳ giá trị flag nào. |

**Bằng chứng** — cả chín cột đều nghiêm ngặt trong `{0,1}` với **không** null nào và
không giá trị ngoài miền nào:

| Cột | Số lượng 0 | Số lượng 1 | % = 1 |
| --- | ---: | ---: | ---: |
| `linkedin_presence` | 199,236 | 800,764 | 80.0764% |
| `website_available` | 150,403 | 849,597 | 84.9597% |
| `verification_status` | 300,287 | 699,713 | 69.9713% |
| `unrealistic_salary_flag` | 1,000,000 | **0** | 0.0000% |
| `payment_required` | 900,095 | 99,905 | 9.9905% |
| `fake_certificate_offer` | 920,170 | 79,830 | 7.9830% |
| `suspicious_email_domain` | 749,433 | 250,567 | 25.0567% |
| `social_media_presence` | 250,200 | 749,800 | 74.9800% |
| `is_fake_posting` | 778,042 | 221,958 | 22.1958% |

Kiểu staging là `SMALLINT`, không phải một boolean thuần, để R4.5.1 được tôn trọng
đúng theo nghĩa chữ trong schema.

**`unrealistic_salary_flag` — hằng số zero.**

| Quy tắc | Chi tiết |
| --- | --- |
| R4.5.5 | Nó là **hằng số 0** trên cả 1,000,000 dòng trong lần extract này. |
| R4.5.6 | **Giữ nó ở staging.** |
| R4.5.7 | Tài liệu hóa nó như một **ứng viên để loại khỏi Data Warehouse phân tích** — một quyết định được hoãn tới bước dimensional modelling (§8.4). |

**Vì sao nó được giữ** — một cột hằng số không mang thông tin để slicing và sẽ tạo
ra một Dimension degenerate chỉ có một thành viên, nên nó là một ứng viên hợp lý để
loại bỏ *về sau*. Nhưng hằng số *trong lần extract này* không đồng nghĩa với hằng số
*trong hệ thống nguồn*: một lần extract về sau có thể chứa các giá trị `1`. Việc bỏ
nó ở staging sẽ che đi thay đổi đó; việc giữ nó làm thay đổi đó hiện ra.

**Vì sao mất cân bằng lớp không bị can thiệp** — phép chia 78/22 của
`is_fake_posting` là mức cân bằng lớp thực của tổng thể này. Việc resample nó sẽ làm
hỏng mọi phép tổng hợp OLAP xây trên Fact table, điều trái ngược với mục đích tồn
tại của pipeline này (xem §11).

### 4.6 `payment_required` / `registration_fee`

| Quy tắc | Chi tiết |
| --- | --- |
| R4.6.1 | **Giữ cả hai trường** ở staging. |
| R4.6.2 | **Không** suy ra trường này từ trường kia, theo bất kỳ chiều nào. |
| R4.6.3 | **Validation** rằng invariant vẫn đúng ở mỗi lần load. |
| R4.6.4 | Tài liệu hóa sự dư thừa để dimensional model xem xét về sau (§8.1). |

**Invariant đã được chứng minh** — `payment_required == (registration_fee > 0)` với
**cả 1,000,000 dòng nguồn**: 0 dòng có `payment_required = 0` kèm phí dương, 0 dòng
có `payment_required = 1` kèm phí bằng zero.

Các giá trị zero của `registration_fee` là **có ý nghĩa, không phải placeholder**:
sự khớp chính xác với `payment_required = 0` trên 900,095 dòng xác nhận rằng zero có
nghĩa là "không yêu cầu phí nào".

### 4.7 `recruiter_email_type` / `suspicious_email_domain`

| Quy tắc | Chi tiết |
| --- | --- |
| R4.7.1 | **Bảo toàn cả hai trường** ở staging. |
| R4.7.2 | Tài liệu hóa quan hệ chính xác (§8.2). |
| R4.7.3 | **KHÔNG** tự động xóa bất kỳ trường nào trong hai trường. |
| R4.7.4 | Hoãn việc xử lý sự dư thừa tới bước dimensional modelling. |

**Song ánh đã được chứng minh** — `Corporate ↔ 0` và `Free ↔ 1`, với **không vi phạm
nào** trên 1,000,000 dòng, functional dependency đúng theo **cả hai** chiều, và
Cramér's V = **1.000000**.

### 4.8 `fraud_score` / `is_fake_posting`

| Quy tắc | Chi tiết |
| --- | --- |
| R4.8.1 | **Bảo toàn cả hai cột.** |
| R4.8.2 | **Không** suy ra `is_fake_posting` từ `fraud_score`. |
| R4.8.3 | **Không** sửa đổi giá trị của cột nào trong hai cột. |

**Bằng chứng rằng không ngưỡng nào hoạt động được** — một lượt quét vét cạn mọi giá
trị `fraud_score` quan sát được cho thấy quy tắc tốt nhất là `fraud_score >= 50`,
vẫn để lại **607 trường hợp lệch** (607 false positive, 0 false negative). **Việc
tái lập hoàn hảo là không thể.** Sự bất đồng nằm tại đúng một giá trị điểm: tại
`fraud_score = 50.0`, 607 dòng được gán nhãn 0 và 620 dòng được gán nhãn 1.

**Vì sao điều này quan trọng** — một pipeline suy ra nhãn từ một ngưỡng sẽ gán nhãn
sai 607 dòng đó và, tệ hơn, sẽ trình bày một giá trị suy dẫn như thể nó được quan
sát. Cả hai cột được mang theo đúng như hiện trạng.

### 4.9 `trust_signal_score` và các flag về độ tin cậy

| Quy tắc | Chi tiết |
| --- | --- |
| R4.9.1 | `trust_signal_score` **không** tất định từ `verification_status`, `linkedin_presence`, `website_available`, `social_media_presence`. |
| R4.9.2 | **Giữ cả năm trường không thay đổi.** |
| R4.9.3 | Không bao giờ tái dựng hay impute điểm số từ các flag. |

**Bằng chứng** — cả 16 tổ hợp flag đều xuất hiện; khoảng biến thiên lớn nhất của
điểm số trong một tổ hợp là **100.0** (toàn bộ thang đo); độ lệch chuẩn lớn nhất
trong một tổ hợp là 15.5713; một tổ hợp chứa 986 điểm phân biệt. Mô hình saturated
chỉ giải thích **R² = 0.137190**. Hai trong bốn flag
(`website_available` với r = -0.001497, `social_media_presence` với r = 0.001566)
thực tế **không** có quan hệ nào với điểm số cả.

### 4.10 `company_age` / `domain_age_months`

| Quy tắc | Chi tiết |
| --- | --- |
| R4.10.1 | Một số tuổi domain vượt quá tuổi công ty. |
| R4.10.2 | **KHÔNG sửa đổi các bản ghi này** — quan hệ này **không phải bằng chứng đủ về tính không hợp lệ**. |

**Bằng chứng** — 469,297 dòng (46.9297% toàn bộ số dòng; 47.4037% trong số 990,000
dòng so sánh được) có `domain_age_months > company_age * 12`. Mức vượt trải từ 1 đến
73 tháng, median 10. Pearson r giữa hai cột trên một thang đo chung là 0.9940.

**Vì sao không có gì bị thay đổi** — một domain có thể chính đáng có trước công ty
đang dùng nó: domain được mua lại, việc đổi thương hiệu, domain đỗ (parked) và việc
đăng ký bởi công ty mẹ đều tạo ra đúng mẫu này. Sự khác biệt về đơn vị (năm so với
tháng) cũng làm `company_age` trở thành phép đo thô hơn, nên những mức vượt nhỏ là
điều dự kiến chỉ từ việc làm tròn. Gần một nửa dataset thể hiện mẫu này; việc coi nó
là một lỗi sẽ có nghĩa là viết lại một nửa lần extract dựa trên một giả định.

### 4.11 Các cột score — validation khoảng giá trị

Áp dụng cho: `vague_description_score`, `urgency_score`, `keyword_spam_score`,
`emotional_manipulation_score`, `phishing_language_score`, `trust_signal_score`,
`fraud_score`.

| Quy tắc | Chi tiết |
| --- | --- |
| R4.11.1 | **Bảo toàn các giá trị.** |
| R4.11.2 | **Validation `0 <= giá trị <= 100`** ở nơi giá trị không null. |

**Bằng chứng** — cả bảy cột đều nằm hoàn toàn trong 0–100:
**0 giá trị dưới 0 và 0 giá trị trên 100**, trong mọi trường hợp. Do đó khoảng 0–100
an toàn để khai báo thành một check constraint ở staging.

Điều kiện `ở nơi không null` chỉ quan trọng với đúng một cột:
`trust_signal_score` có 10,000 null. Sáu cột còn lại không có null nào.

**Ghi chú** — việc nằm trong 0–100 chỉ validation *khoảng giá trị*, không validation
tính đúng đắn.

### 4.12 Outlier numeric

| Quy tắc | Chi tiết |
| --- | --- |
| R4.12.1 | **Không** xóa outlier. |
| R4.12.2 | **Không** winsorize. |
| R4.12.3 | **Không** chặn ngưỡng hay cắt. |
| R4.12.4 | **Không** normalize. |
| R4.12.5 | **Không** standardize. |
| R4.12.6 | Các kết quả IQR **chỉ mang tính mô tả**. |

Chi tiết và lý do ở §7.

### 4.13 Dòng trùng lặp

| Quy tắc | Chi tiết |
| --- | --- |
| R4.13.1 | Có **không dòng trùng khớp chính xác nào**. |
| R4.13.2 | **Thực hiện phép validation**, nhưng **không loại trùng bất cứ thứ gì.** |

**Bằng chứng** — trên 1,000,000 dòng và cả 33 cột, số bản trùng khớp chính xác
(các bản sao thừa, `duplicated(keep='first')`) = **0**. Số dòng phân biệt =
1,000,000.

**Vì sao phép kiểm tra vẫn được chạy** — nó là một phép kiểm tra hồi quy trên nguồn,
không phải một bước làm sạch. Nếu một lần extract trong tương lai có chứa bản trùng,
bước load phải làm điều đó lộ ra chứ không hấp thụ nó. Và vì việc loại trùng với
`keep='first'` sẽ âm thầm phá hủy các dòng, R4.13.2 làm cho phép kiểm tra này
nghiêm ngặt là chỉ đọc.

**Ghi chú** — các bản gần-trùng đã cố ý **không** được tìm kiếm: một phép so sánh
toàn bộ cặp là O(n²) và không khả thi ở số dòng này. Đây là một khoảng trống đã biết
và đã được tài liệu hóa, không phải một sự bỏ sót.

---

## 5. Chính sách về giá trị thiếu

**Chỉ ba cột có giá trị thiếu**, mỗi cột ở đúng 1.0000%:

| Cột | Số thiếu | % thiếu | Kiểu staging |
| --- | ---: | ---: | --- |
| `company_age` | 10,000 | 1.0000% | `SMALLINT NULL` |
| `stipend` | 10,000 | 1.0000% | `INTEGER NULL` |
| `trust_signal_score` | 10,000 | 1.0000% | `DECIMAL(4,1) NULL` |

30 cột còn lại là đầy đủ. Tổng số ô bị thiếu: 30,000 trên 33,000,000
(0.0909%).

Các cột text **không chứa chuỗi rỗng và không chứa giá trị chỉ gồm whitespace**, nên
với những cột đó thì số null là toàn bộ bức tranh về việc thiếu dữ liệu — không có
việc thiếu dữ liệu ẩn nào được ngụy trang thành text.

### Các quy tắc

| Quy tắc | Chi tiết |
| --- | --- |
| R5.1 | **Bảo toàn giá trị thiếu dưới dạng NULL/NaN.** |
| R5.2 | **KHÔNG** impute bằng mean. |
| R5.3 | **KHÔNG** impute bằng median. |
| R5.4 | **KHÔNG** thay bằng zero. |
| R5.5 | **KHÔNG** loại bỏ dòng vì các giá trị thiếu này. |
| R5.6 | **Không** thêm một giá trị sentinel "missing" hay một thành viên "unknown" ở tầng staging. |
| R5.7 | Ba cột này được khai báo cho phép `NULL` ở staging; 30 cột còn lại là `NOT NULL`. |

### Vì sao

**Imputation phá hủy một dữ kiện đã được đo.** Mỗi khoảng trống đúng bằng 1.0000% —
việc thiếu dữ liệu là một tính chất thực của lần extract này, và nó đã được đo, không
phải được phỏng đoán.

**Zero sẽ là sai một cách chủ động** trong cả ba trường hợp. `stipend` **không có
giá trị zero nào cả** (nhỏ nhất 2,000) và `company_age` **không có giá trị zero nào
cả** (nhỏ nhất 1), nên việc chèn zero sẽ tạo ra những giá trị không xuất hiện ở đâu
trong miền giá trị quan sát được và sẽ nằm rất thấp dưới mức nhỏ nhất thực.
`trust_signal_score` thì có 479 giá trị zero thực sự, nên việc điền zero sẽ làm
10,000 dòng không rõ trở thành không phân biệt được với 479 dòng thực sự bằng zero.

**Mean hay median sẽ chế tạo ra độ chính xác giả.** Nó sẽ kéo 10,000 dòng về một
điểm duy nhất, làm co phương sai và làm lệch mọi phép tổng hợp OLAP chạm tới cột đó
— một cách âm thầm, vì không có gì ở phía sau cho thấy các giá trị đó đã được bịa ra.

**Việc bỏ dòng sẽ mất nhiều hơn là sửa được.** Ba khoảng trống này **không** phải một
lần rơi dữ liệu duy nhất ở mức bản ghi. Không dòng nào thiếu cả ba giá trị, không có
hai mặt nạ nào giống hệt nhau, và các mức chồng lấp theo cặp (88, 96, 88) nằm về cơ
bản đúng ở mức mà tính độc lập dự báo (100). **29,728 dòng phân biệt** thiếu ít nhất
một giá trị — việc bỏ chúng sẽ bỏ đi gần 3% dataset, bao gồm cả những cột có dữ liệu
hoàn hảo ở các dòng đó.

**Việc thiếu dữ liệu mang gần như không có thông tin về nhãn**, nên cũng không có
lập luận nào về việc bảo toàn tín hiệu để biện minh cho một cách xử lý đặc biệt:

| Cột | Tỷ lệ gian lận, các dòng bị thiếu | Tỷ lệ gian lận, các dòng có giá trị | Khoảng cách |
| --- | ---: | ---: | ---: |
| `company_age` | 22.0000% | 22.1978% | -0.1978 pp |
| `stipend` | 21.9600% | 22.1982% | -0.2382 pp |
| `trust_signal_score` | 22.3800% | 22.1939% | +0.1861 pp |

Cả ba khoảng cách đều dưới một phần tư điểm phần trăm. Đây là bằng chứng cho thấy
việc thiếu dữ liệu không mang thông tin; nó **không** phải là chứng minh, và nó
không nói gì về mối liên hệ với các cột khác.

**Việc đây là thiếu mang tính cấu trúc hay là các lỗ hổng thu thập thì không thể
quyết định từ dữ liệu.** Sự phân biệt đó quyết định liệu Data Warehouse cuối cùng
dùng một NULL, một thành viên Dimension "unknown", hay một measure trống trong Fact
— một **quyết định thuộc dimensional model**, được hoãn lại một cách tường minh.
Staging giữ NULL để cả ba lựa chọn đều còn để mở.

---

## 6. Chính sách về chất lượng ngày tháng

### Các quy tắc

| Quy tắc | Chi tiết |
| --- | --- |
| R6.1 | Parse `posting_date` thành một date thực sự. |
| R6.2 | Lưu/xuất ở dạng ISO **`YYYY-MM-DD`**. |
| R6.3 | **Việc parse không hợp lệ phải được báo cáo** — không bao giờ âm thầm coerce, gán mặc định hay điền null. |
| R6.4 | **KHÔNG loại bỏ các ngày ở tương lai.** |
| R6.5 | Thêm `is_future_posting` suy dẫn ở staging: `1` khi `posting_date > 2026-09-23`, ngược lại `0`. |
| R6.6 | Mốc cắt **2026-09-23** là **ngày audit/tham chiếu** đã được tài liệu hóa. |

### Chất lượng ngày tháng đã được đo

| Chỉ số | Giá trị |
| --- | ---: |
| Tỷ lệ parse thành công (`%Y-%m-%d`) | **100.00%** |
| Số giá trị không parse được theo định dạng đó | **0** |
| Số giá trị không parse được theo bất kỳ định dạng nào | **0** |
| Nhỏ nhất | 2018-01-01 |
| Lớn nhất | 2026-12-31 |
| Số date phân biệt | 3,287 |
| Độ trải theo ngày | 3,286 |
| Số ngày dương lịch có ít nhất một dòng | **100%** — không có ngày trống |
| Số dòng trước 2018-01-01 | 0 |
| **Số dòng sau 2026-09-23** | **30,246 (3.0246%)** |
| Số date tương lai phân biệt | 99 |

Các dòng ở tương lai theo tháng: 2026-09 → 2,195; 2026-10 → 9,435; 2026-11 → 9,195;
2026-12 → 9,421.

### Vì sao các ngày ở tương lai được gắn cờ thay vì bị loại bỏ

Chúng **không** phải một lần parse thất bại — mỗi ngày đều là một date hợp lệ, đúng
dạng. Việc muộn hơn ngày tham chiếu làm một dòng trở nên *đáng chú ý*, không phải
*không hợp lệ*.

Tỷ lệ gian lận của chúng là **22.2939%** so với **22.1958%** trên toàn dataset — một
chênh lệch dưới 0.1 pp. Việc có ngày ở tương lai không mang tín hiệu nào về nhãn,
nên việc loại bỏ sẽ tốn 3% dữ liệu mà không đổi lại được gì.

Việc gắn cờ hữu ích hơn hẳn việc lọc bỏ: mọi phép phân tích đều có thể loại trừ
`is_future_posting = 1` khi cần, còn không phép phân tích nào có thể phục hồi những
dòng mà staging đã xóa.

### Vì sao mốc cắt là một hằng số cố định

`2026-09-23` được hard-code, **không** được tính từ đồng hồ hệ thống. Việc dùng "hôm
nay" sẽ làm dataset staging không tái lập được — số dòng được gắn cờ sẽ trôi đi ở mỗi
lần chạy và hai lần load cùng một file sẽ không khớp nhau. Việc ghim hằng số này làm
`is_future_posting` trở nên tất định và làm con số 30,246 trở thành một kỳ vọng kiểm
chứng được. Ngày này là ngày mà bằng chứng profiling và audit được tạo ra đối chiếu
với nó.

### Các quan sát khác về ngày tháng — được ghi lại, không được xử lý

- Mọi ngày dương lịch trong khoảng đều có dữ liệu, với các dòng phân bố gần như
  đồng đều (hệ số biến thiên 0.0558) và tỷ lệ theo ngày trong tuần từ
  14.2196%–14.3617% so với mức đều 14.2857%.
- Việc nạp dữ liệu gần như đồng đều trên mọi ngày kể cả cuối tuần và ngày lễ không
  điển hình cho hoạt động đăng tin tuyển dụng thực.

Đây là **các quan sát về provenance** cần tài liệu về nguồn để giải quyết. Chúng
không phải lỗi chất lượng dữ liệu và **không** kích hoạt biến đổi nào.

### Các cột trông giống date nhưng không phải

`recruiter_experience_years` và `recruiter_response_time_hours` khớp với heuristic
tên-dạng-date của bộ profiler (tên của chúng chứa `years` và `time`) nhưng là
**các measure về khoảng thời gian**, với tỷ lệ parse thành công 0.00%. Chúng **không**
được parse như date. Điều này được ghi lại để heuristic vẫn có thể audit được.

---

## 7. Chính sách về outlier

### Các quy tắc

| Quy tắc | Chi tiết |
| --- | --- |
| R7.1 | **KHÔNG** xóa outlier. |
| R7.2 | **KHÔNG** winsorize. |
| R7.3 | **KHÔNG** chặn ngưỡng hay cắt. |
| R7.4 | **KHÔNG** normalize. |
| R7.5 | **KHÔNG** standardize. |
| R7.6 | Các kết quả IQR **chỉ mang tính mô tả** — một công cụ sàng lọc, không bao giờ là một kết luận. |

### Số outlier đã đo (ngưỡng 1.5 × IQR)

| Cột | Ngưỡng dưới | Ngưỡng trên | Outlier theo IQR | % |
| --- | ---: | ---: | ---: | ---: |
| `company_age` | -20.00 | 60.00 | **0** | 0.0000% |
| `stipend` | -5,583.50 | 75,548.50 | 3,348 | 0.3348% |
| `registration_fee` | 0.00 | 0.00 | 99,905 | 9.9905% |
| `job_description_length` | 183.00 | 3,415.00 | 7,040 | 0.7040% |
| `grammatical_errors` | -1.00 | 7.00 | **11,891** | **1.1891%** |
| `recruiter_experience_years` | -3.00 | 13.00 | 3,585 | 0.3585% |
| `recruiter_response_time_hours` | -9.20 | 45.20 | 3,217 | 0.3217% |

Cũng được gắn cờ trong các cột score: `vague_description_score` 3,472 (0.3472%),
`keyword_spam_score` 3,451 (0.3451%), `emotional_manipulation_score` 3,516
(0.3516%), `phishing_language_score` 2,650 (0.2650%), `trust_signal_score` 4,510
(0.4510%), `fraud_score` 8,881 (0.8881%). `urgency_score` có **0**.

Tổng số được gắn cờ: 128,986 quan sát. Nếu loại các cột có ngưỡng suy biến:
**29,081**.

### Vì sao không có gì được xử lý

**Không tồn tại giá trị âm nào ở bất cứ đâu trong dataset.** Không một cột numeric
nào chứa giá trị âm, nên không có lỗi dấu nào cần hiệu chỉnh.

**Các giá trị được gắn cờ là những đuôi dài thông thường.** Một mức stipend cao, một
phản hồi chậm của nhà tuyển dụng và một mô tả công việc dài đều thực sự có thể xảy
ra. Tỷ lệ của chúng rất nhỏ — phần lớn quanh 0.3%.

**`grammatical_errors` có tỷ lệ lớn nhất (1.1891%) và bị chặn trong 0–14.** Mức tối
đa 14 lỗi ngữ pháp là hoàn toàn hợp lý với một tin tuyển dụng thực. Ngưỡng tại 7 là
một sản phẩm phụ của một phân phối số nguyên nhỏ và chặt, không phải dấu hiệu của sự
hỏng dữ liệu.

**Ngưỡng của `registration_fee` là vô nghĩa.** Q1 và Q3 đều bằng 0, nên khoảng tứ
phân vị thu về 0 và cả hai ngưỡng đều rơi vào 0 — mọi giá trị khác zero đều bị gắn
cờ **theo cách cấu tạo**. Hãy đọc con số 99,905 đó là "số dòng có phí khác zero",
không phải là các quan sát cực trị. Việc hành động theo nó sẽ xóa mọi dòng có trả
phí trong dataset, phá hủy đúng tổng thể mà một Data Warehouse về phát hiện lừa đảo
tồn tại để nghiên cứu.

**Scaling và standardizing không có chỗ ở đây.** Chúng là các bước chuẩn bị cho
modelling. Một `stipend` đã được standardize là không đọc được trong một báo cáo
OLAP và không thể tổng, lấy trung bình hay drill xuống một cách có ý nghĩa, và phép
biến đổi sẽ phải bị đảo ngược cho mọi truy vấn.

---

## 8. Các quan sát về sự dư thừa

Bốn phát hiện về sự dư thừa. **Không phát hiện nào khiến một cột bị bỏ hay bị suy
dẫn ở tầng staging.** Mỗi phát hiện được ghi lại như một câu hỏi mở cho dimensional
model.

### 8.1 `payment_required` ≡ `registration_fee > 0` — chính xác

| Phép kiểm tra | Số dòng | % |
| --- | ---: | ---: |
| `payment_required = 0` VÀ `registration_fee > 0` | **0** | 0.0000% |
| `payment_required = 1` VÀ `registration_fee = 0` | **0** | 0.0000% |
| Nhất quán, cả hai bằng zero | 900,095 | 90.0095% |
| Nhất quán, flag được bật và phí dương | 99,905 | 9.9905% |

`payment_required` hoàn toàn phục hồi được từ `registration_fee`.

**Staging** — giữ cả hai, không suy ra cột nào, validation invariant ở mỗi lần load.
**Hoãn tới dimensional modelling** — liệu flag trở thành một thuộc tính Dimension và
phí trở thành một measure trong Fact, hay chỉ mang theo phí.

### 8.2 `recruiter_email_type` ↔ `suspicious_email_domain` — song ánh hoàn hảo

| | `suspicious_email_domain` = 0 | = 1 | Tổng |
| --- | ---: | ---: | ---: |
| `Corporate` | 749,433 | **0** | 749,433 |
| `Free` | **0** | 250,567 | 250,567 |

Functional dependency đúng theo **cả hai** chiều, 0 dòng vi phạm trên 1,000,000
dòng, Cramér's V = **1.000000**. Hai cột mang thông tin y hệt nhau trên lần extract
này.

**Staging** — bảo toàn cả hai; **không** tự động xóa cột nào.
**Hoãn tới dimensional modelling** — cách giải quyết sự trùng lặp.

**Vì sao không cột nào bị xóa lúc này** — phép chứng minh bao phủ *lần extract này*,
không phải hệ thống nguồn. `recruiter_email_type` là một **nhãn** còn chỗ cho các
giá trị vượt quá hai; một lần extract trong tương lai có thể chứa một loại email thứ
ba, điều mà flag boolean không thể biểu diễn. Việc mang cả hai bảo toàn khoảng trống
dự phòng đó với chi phí không đáng kể, và việc xóa là không thể hoàn tác trong khi
sự dư thừa thì không gây hại.

### 8.3 `fraud_score` so với `is_fake_posting` — **không** dư thừa

Được liệt kê ở đây vì rất dễ *cho rằng* có sự dư thừa. Audit phản bác điều đó.

| Chỉ số | Giá trị |
| --- | ---: |
| Ngưỡng tốt nhất | `fraud_score >= 50` |
| **Số trường hợp lệch** | **607** |
| Độ chính xác | 99.939300% |
| **Có thể tái lập hoàn hảo** | **KHÔNG** |
| Số điểm phân biệt mà cả hai lớp cùng xuất hiện | **1** (đúng bằng 50.0) |

**Staging** — bảo toàn cả hai; không suy ra cột nào.
**Hoãn tới dimensional modelling** — cột nào trở thành measure trong Fact và cột nào
trở thành thuộc tính Dimension. Hành vi tại biên ở `fraud_score = 50.0` là một
**câu hỏi dành cho chủ sở hữu nguồn**, không phải điều mà dữ liệu có thể giải quyết.

### 8.4 `unrealistic_salary_flag` — hằng số, không có thông tin

Hằng số `0` trên cả 1,000,000 dòng. Nó sẽ tạo ra một Dimension degenerate chỉ có một
thành viên và không thể hỗ trợ bất kỳ phép slicing nào.

**Staging** — giữ và validation.
**Hoãn tới dimensional modelling** — **ứng viên để loại khỏi Data Warehouse phân
tích.** Được giữ ở staging vì hằng-số-trong-lần-extract-này không phải
hằng-số-trong-hệ-thống-nguồn.

### 8.5 Tính không dư thừa đã được xác lập một cách tường minh

Được ghi lại để không ai mở lại những điều này như những phép đơn giản hóa "hiển
nhiên":

- **`trust_signal_score` KHÔNG suy dẫn được** từ `verification_status`,
  `linkedin_presence`, `website_available`, `social_media_presence`. Khoảng biến
  thiên lớn nhất trong một tổ hợp là 100.0 (toàn bộ thang đo); R² saturated =
  0.137190. Cả năm cột đều được giữ.
- **`domain_age_months` KHÔNG phải một cách phát biểu lại của `company_age`.** Dù
  r = 0.9940, có 469,297 dòng có domain già hơn công ty. Cả hai đều được giữ.

---

## 9. Chính sách về data lineage của dòng

### Các quy tắc

| Quy tắc | Chi tiết |
| --- | --- |
| R9.1 | **Không có natural key dạng cột đơn nào** trong nguồn. |
| R9.2 | Thêm **`source_row_id`** vào dataset **STAGING**. |
| R9.3 | Nó bắt đầu từ **1** và theo **thứ tự dòng gốc trong CSV**. |
| R9.4 | Nó được gán **trước** mọi phép lọc, sắp xếp hay biến đổi. |
| R9.5 | **KHÔNG thêm `source_row_id` vào file raw.** |
| R9.6 | Ghi nó cùng với **sha256** của file nguồn trong bản ghi audit của lần load. |
| R9.7 | Nó là một **tay cầm phục vụ data lineage, không phải một business key**. Nó **không** được dùng để join giữa các lần extract. |

### Bằng chứng

Profiling đã kiểm tra cả 33 cột và các tổ hợp:

| Phép kiểm tra | Kết quả |
| --- | ---: |
| Số cột thỏa tính duy nhất nghiêm ngặt | **0** |
| Số cột gần-duy nhất (tỷ lệ ≥ 0.99) | **0** |
| Cột có cardinality cao nhất | `company_name` — 535,938 giá trị phân biệt (53.5938%) |
| Giá trị phổ biến nhất của nó | `Smith PLC`, 1,248 lần xuất hiện |
| Số tổ hợp duy nhất tìm thấy | **không có** |

**Không primary key nào được các script profiling hay audit khai báo, và không key
nào được thêm vào dữ liệu raw.** `source_row_id` là đề xuất duy nhất mà các giai
đoạn đó đưa ra, và nó chỉ áp dụng cho tầng staging.

### Vì sao dùng thứ tự file

Vì nguồn không cung cấp gì khác. Khi không có natural key, vị trí trong file là cách
ổn định duy nhất để trỏ từ một dòng trong Data Warehouse trở về một dòng cụ thể của
lần extract này.

### Vì sao nó không phải một business key

Ý nghĩa của nó phụ thuộc hoàn toàn vào **file nào** mà nó đến từ. Dòng 5 của lần
extract này và dòng 5 của một lần extract được phát hành lại là những tin tuyển dụng
khác nhau. Đó là lý do R9.6 đòi hỏi sha256 phải được lưu cùng nó — cặp
`(sha256, source_row_id)` mới là định danh thực sự — và là lý do R9.7 cấm việc join
xuyên các lần extract. Nó không mang ý nghĩa nghiệp vụ nào và không phải một ID tin
tuyển dụng.

### Kết quả kỳ vọng

Các giá trị 1…1,000,000, liên tục, duy nhất, không null — một giá trị cho mỗi dòng
nguồn được bảo toàn.

---

## 10. Các yêu cầu validation

Bước load staging phải chạy mọi phép kiểm tra dưới đây và phát ra một báo cáo
validation. Một phép kiểm tra thất bại sẽ được **báo cáo**; pipeline **không** âm
thầm sửa chữa dữ liệu. Các giá trị kỳ vọng được lấy từ bằng chứng profiling và audit,
nên mọi sai lệch đều có nghĩa là nguồn đã thay đổi.

### 10.1 Tính toàn vẹn và data lineage

| # | Phép kiểm tra | Kỳ vọng |
| --- | --- | --- |
| V1 | sha256 của file raw trước và sau lần chạy | `3463d99b…f3b1398`, không thay đổi |
| V2 | File raw không bị sửa đổi | giống hệt đến từng byte |
| V3 | Số dòng của nguồn | **1,000,000** |
| V4 | Số cột của nguồn | **33** |
| V5 | Số dòng staging bằng số dòng nguồn | **1,000,000** |
| V6 | Cả 33 cột nguồn có mặt ở staging | có |
| V7 | `source_row_id` duy nhất, không null, liên tục 1…1,000,000 | có |
| V8 | Thứ tự `source_row_id` khớp thứ tự file gốc | có |
| V9 | CSV được đọc bằng parser nhận biết dấu ngoặc kép | bắt buộc (`company_name` có dấu phẩy nhúng) |

### 10.2 Ngày tháng

| # | Phép kiểm tra | Kỳ vọng |
| --- | --- | --- |
| V10 | Số lần parse `posting_date` thất bại | **0** — mọi thất bại **phải được báo cáo** |
| V11 | Định dạng đầu ra | ISO `YYYY-MM-DD` |
| V12 | Min / max | 2018-01-01 / 2026-12-31 |
| V13 | Số date phân biệt | 3,287 |
| V14 | Số dòng có `is_future_posting = 1` | **30,246** (3.0246%) |
| V15 | `is_future_posting` được tính đối chiếu với hằng số cố định 2026-09-23 | có — không bao giờ theo đồng hồ hệ thống |
| V16 | Không dòng nào bị loại bỏ vì có ngày ở tương lai | giữ lại 1,000,000 |

### 10.3 Giá trị thiếu

| # | Phép kiểm tra | Kỳ vọng |
| --- | --- | --- |
| V17 | Số null của `company_age` | **10,000** (1.0000%) |
| V18 | Số null của `stipend` | **10,000** (1.0000%) |
| V19 | Số null của `trust_signal_score` | **10,000** (1.0000%) |
| V20 | Số null ở 30 cột còn lại | **0** |
| V21 | Không có imputation nào được áp dụng | số null không đổi so với nguồn |
| V22 | Số dòng thiếu ít nhất một trong ba | 29,728 |
| V23 | Số dòng thiếu cả ba | **0** |

### 10.4 Các binary flag

| # | Phép kiểm tra | Kỳ vọng |
| --- | --- | --- |
| V24 | Cả chín flag nằm nghiêm ngặt trong `{0,1}` | có, 0 vi phạm |
| V25 | Không có null trong bất kỳ flag nào | **0** |
| V26 | Cách biểu diễn 0/1 được bảo toàn (không phải boolean/text) | có |
| V27 | Số lượng theo từng flag khớp §4.5 | khớp chính xác |
| V28 | `unrealistic_salary_flag` vẫn là hằng số 0 | 1,000,000 giá trị zero — **báo cáo nếu nó thay đổi** |

### 10.5 Các invariant giữa các cột

| # | Phép kiểm tra | Kỳ vọng |
| --- | --- | --- |
| V29 | `payment_required == (registration_fee > 0)` | **0 vi phạm** |
| V30 | `registration_fee >= 0` | **0 giá trị âm** |
| V31 | `recruiter_email_type='Corporate'` ⟺ `suspicious_email_domain=0` | **0 vi phạm** |
| V32 | `recruiter_email_type='Free'` ⟺ `suspicious_email_domain=1` | **0 vi phạm** |
| V33 | Không cột nào của cả hai cặp bị bỏ | cả hai đều có mặt |
| V34 | `is_fake_posting` không được suy ra từ `fraud_score` | các giá trị nhãn giống hệt nguồn đến từng byte |

### 10.6 Khoảng giá trị và miền giá trị

| # | Phép kiểm tra | Kỳ vọng |
| --- | --- | --- |
| V35 | Bảy cột score thỏa `0 <= giá trị <= 100` ở nơi không null | **0 ngoài khoảng** |
| V36 | Không có giá trị âm trong bất kỳ cột numeric nào | **0** |
| V37 | `company_age` nằm trong 1–39 | có |
| V38 | `domain_age_months` nằm trong 1–500 | có |
| V39 | `stipend` nằm trong 2,000–110,428 ở nơi không null | có |
| V40 | `registration_fee` nằm trong 0–4,999 | có |
| V41 | `job_description_length` nằm trong 100–5,000 | có |
| V42 | `grammatical_errors` nằm trong 0–14 | có |
| V43 | `recruiter_experience_years` nằm trong 0.0–19.6 | có |
| V44 | `recruiter_response_time_hours` nằm trong 1.0–63.9 | có |

### 10.7 Chất lượng text

| # | Phép kiểm tra | Kỳ vọng |
| --- | --- | --- |
| V45 | Giá trị có whitespace đệm trên 8 cột text | **0** — **báo cáo, không trim** |
| V46 | Chuỗi rỗng | **0** |
| V47 | Giá trị chỉ gồm whitespace | **0** |
| V48 | Số giá trị phân biệt không đổi so với nguồn | `internship_title` 9, `employment_type` 4, `work_mode` 3, `industry` 9, `location` 9, `company_size` 4, `recruiter_email_type` 2, `company_name` 535,938 |
| V49 | Không có phép đổi chữ hoa/thường nào được áp dụng | phân biệt = phân biệt không phân biệt hoa/thường |
| V50 | Miền giá trị category không đổi | đúng các giá trị trong data dictionary |

V45 là điều kiện kích hoạt cho R4.3.3: nếu whitespace đệm bất ngờ xuất hiện,
validation **làm nó lộ ra để một con người quyết định**. Pipeline không tự trim.

### 10.8 Bản trùng và outlier

| # | Phép kiểm tra | Kỳ vọng |
| --- | --- | --- |
| V51 | Số dòng trùng khớp chính xác | **0** — chỉ kiểm tra, **không bao giờ loại trùng** |
| V52 | Số dòng phân biệt | 1,000,000 |
| V53 | Không outlier nào bị xóa, chặn ngưỡng hay winsorize | các phân phối khớp nguồn |
| V54 | Thống kê IQR được tính lại chỉ như đầu ra mô tả | không giá trị nào bị biến đổi |

### 10.9 Định kiểu

| # | Phép kiểm tra | Kỳ vọng |
| --- | --- | --- |
| V55 | `posting_date` là một `DATE` thực sự | có |
| V56 | `company_age`, `stipend` load thành integer không mất dữ liệu | **0 giá trị không nguyên** trong nguồn |
| V57 | Các cột một chữ số thập phân giữ nguyên độ chính xác | `recruiter_experience_years`, `recruiter_response_time_hours`, `trust_signal_score`, `fraud_score` |
| V58 | Không giá trị nào bị thay đổi bởi một phép chuyển kiểu | so sánh vòng ghi-đọc đối chiếu với nguồn |

---

## 11. Các biến đổi KHÔNG được thực hiện, một cách tường minh

Mọi mục dưới đây đều đã được **xem xét và dứt khoát loại bỏ**. Mục này tồn tại để
một người đọc về sau phân biệt được *đã quyết định không làm* với *bị bỏ sót*.
Việc thực hiện bất kỳ mục nào trong số này sẽ là một sự đi lệch khỏi các quy tắc đã
được phê duyệt.

### 11.1 Dữ liệu raw

- ❌ Sửa đổi, ghi đè hay lưu lại file CSV raw
- ❌ Thêm bất kỳ cột nào vào file raw, kể cả `source_row_id`
- ❌ Bỏ, lọc hay lấy mẫu bất kỳ dòng nào trong 1,000,000 dòng
- ❌ Đổi thứ tự hay sắp xếp nguồn

### 11.2 Giá trị thiếu

- ❌ Imputation bằng mean
- ❌ Imputation bằng median
- ❌ Thay bằng zero
- ❌ Điền bằng mode / hằng số / sentinel
- ❌ Forward-fill, back-fill hay nội suy
- ❌ Imputation dựa trên mô hình (kNN, MICE, hồi quy)
- ❌ Bỏ các dòng có giá trị thiếu
- ❌ Bỏ `company_age`, `stipend` hay `trust_signal_score` vì không đầy đủ
- ❌ Tái dựng `trust_signal_score` từ bốn flag về độ tin cậy

### 11.3 Text và categorical

- ❌ Chuyển thành chữ thường hay bất kỳ phép đổi chữ hoa/thường nào
- ❌ Trim hay chuẩn hóa whitespace (không tồn tại lỗi nào; V45 báo cáo thay thế)
- ❌ Mapping, đổi tên hay mã hóa lại category
- ❌ Gộp category hay nhóm các giá trị hiếm
- ❌ Áp đặt một thứ hạng ordinal lên `company_size`
- ❌ Fuzzy matching, entity resolution hay nhóm `company_name`
- ❌ Chuẩn hóa `location` thành quốc gia/khu vực hay làm giàu dữ liệu địa lý

### 11.4 Ngày tháng

- ❌ Loại bỏ các dòng có ngày ở tương lai
- ❌ Cắt `posting_date` về ngày tham chiếu
- ❌ Âm thầm coerce hay điền null cho một date không parse được
- ❌ Tính `is_future_posting` từ đồng hồ hệ thống thay vì từ 2026-09-23
- ❌ Parse `recruiter_experience_years` hay `recruiter_response_time_hours` như date

### 11.5 Outlier và phân phối

- ❌ Xóa outlier
- ❌ Winsorize
- ❌ Chặn ngưỡng hay cắt
- ❌ Normalize
- ❌ Standardize
- ❌ Biến đổi log hay lũy thừa
- ❌ Chia dải hay rời rạc hóa các measure liên tục
- ❌ Hành động theo ngưỡng IQR suy biến của `registration_fee`

### 11.6 Sự dư thừa

- ❌ Bỏ `payment_required` vì nó bằng `registration_fee > 0`
- ❌ Bỏ `registration_fee` để ưu tiên flag
- ❌ Bỏ `recruiter_email_type` hay `suspicious_email_domain`
- ❌ Suy ra `is_fake_posting` từ một ngưỡng `fraud_score`
- ❌ Suy ra `fraud_score` từ nhãn
- ❌ Bỏ `unrealistic_salary_flag` khỏi staging vì nó là hằng số
- ❌ Bỏ `company_age` hay `domain_age_months` vì cho là trùng lặp

### 11.7 Các bản ghi được gắn cờ nhưng không bị biến đổi

- ❌ Sửa đổi 469,297 dòng có domain già hơn công ty
- ❌ Xóa hay hiệu chỉnh 30,246 dòng có ngày ở tương lai
- ❌ Điều chỉnh 1,227 dòng tại `fraud_score = 50.0`
- ❌ Loại trùng bất cứ thứ gì (không có bản trùng khớp chính xác nào)

### 11.8 Tiền xử lý cho machine learning

**Không mục nào trong số này thuộc về một pipeline Data Warehouse và OLAP.**

- ❌ One-hot encoding
- ❌ Label encoding cho các Dimension
- ❌ Ordinal encoding
- ❌ `MinMaxScaler`
- ❌ `StandardScaler`
- ❌ Bất kỳ scaler hay normalizer nào khác
- ❌ SMOTE
- ❌ Undersampling
- ❌ Oversampling
- ❌ Đánh trọng số lớp hay cân bằng lại `is_fake_posting`
- ❌ TF-IDF
- ❌ Stemming
- ❌ Lemmatization
- ❌ Loại bỏ stop-word, tokenisation hay bất kỳ bước NLP nào
- ❌ Lựa chọn đặc trưng hay giảm chiều (PCA và tương tự)
- ❌ Chia train/test

Lưu ý rằng các mục về xử lý văn bản là không áp dụng được ở mức độ kép: dataset
**không chứa cột văn bản tự do nào cả**. `job_description_length` là một độ dài
numeric; bản thân phần mô tả không có trong dữ liệu.

### 11.9 Không được thử, và vì sao

- **Phát hiện bản gần-trùng.** Một phép so sánh toàn bộ cặp là O(n²) và không khả
  thi ở 1,000,000 dòng. Một cách tiếp cận có blocking có thể được thêm về sau nếu
  điều đó quan trọng. Đây là một khoảng trống đã biết và đã được tài liệu hóa.
- **Kiểm định việc thiếu dữ liệu đối chiếu với các cột khác ngoài nhãn.** Việc thiếu
  dữ liệu chỉ được kiểm định về mối liên hệ với `is_fake_posting`.
- **Giải quyết vấn đề provenance.** Số dòng tròn chính xác, các phép chia categorical
  gần đồng đều, độ phủ dương lịch 100%, ba tỷ lệ thiếu dữ liệu đúng bằng 1.0000%,
  việc không có bản trùng nào và độ sạch hoàn hảo của text đều được
  **ghi lại như các quan sát**. Chúng **không** xác lập rằng dữ liệu là dữ liệu tổng
  hợp — mỗi mục đều nhất quán ngang nhau với một dataset thực đã được làm sạch và lấy
  mẫu từ phía trên. Việc giải quyết điều này cần tài liệu về nguồn, không cần thêm
  phân tích. Cho đến lúc đó, tính thực tế của dataset là **chưa được kiểm chứng**,
  chứ không phải đã được xác nhận hay bị phủ nhận.

---

## 12. Các quyết định được hoãn tới bước dimensional modelling

Được tập hợp cho giai đoạn tiếp theo. **Không quyết định nào trong số này được giải
quyết ở đây.**

| # | Câu hỏi mở | Bằng chứng |
| --- | --- | --- |
| D1 | Giải quyết sự dư thừa `payment_required` / `registration_fee` — flag làm thuộc tính Dimension và phí làm measure, hay chỉ phí? | §8.1 |
| D2 | Giải quyết song ánh `recruiter_email_type` / `suspicious_email_domain` — giữ nhãn, giữ flag, hay giữ cả hai? | §8.2 |
| D3 | Loại `unrealistic_salary_flag` khỏi Data Warehouse phân tích? (hằng số, Dimension degenerate một thành viên) | §8.4 |
| D4 | Cột nào trong `fraud_score` / `is_fake_posting` trở thành measure trong Fact và cột nào trở thành thuộc tính Dimension? | §8.3 |
| D5 | Hỏi chủ sở hữu nguồn xem `fraud_score = 50.0` được giải quyết thành nhãn ra sao | §8.3 |
| D6 | Giữ `trust_signal_score` song song với bốn flag về độ tin cậy? (một measure suy dẫn vẫn có thể đáng lưu) | §8.5 |
| D7 | `posting_date` — Dimension thời gian riêng, thuộc tính degenerate, hay được nhóm lại? (3,287 giá trị phân biệt) | data dictionary §3.1 |
| D8 | `company_name` — Dimension riêng, thuộc tính degenerate, hay được nhóm lại? (535,938 giá trị phân biệt, không có company key) | data dictionary §3.3 |
| D9 | NULL so với một thành viên Dimension "unknown" so với một measure trống trong Fact, cho ba cột không đầy đủ | §5 |
| D10 | Liệu `stipend` có thể được tổng hợp xuyên `location` mà không có đơn vị tiền tệ được tài liệu hóa | data dictionary §3.4 |
| D11 | Flag nào trở thành thuộc tính Dimension và flag nào trở thành flag degenerate trong Fact table | §4.5 |

---

## 13. Khả năng truy vết từ quy tắc tới bằng chứng

| Nhóm quy tắc | Bằng chứng |
| --- | --- |
| §2 tính bất biến, số dòng/cột, bản trùng | `results/profiling/dataset_overview.txt` |
| §4.1 / §9 data lineage, không có natural key | `results/profiling/potential_key_analysis.csv`, `results/audit/key_candidates.csv` |
| §4.2 / §6 ngày tháng | `results/profiling/date_analysis.csv`, `results/audit/date_bounds.csv`, `future_dates.csv`, `future_dates_by_month.csv` |
| §4.3 chất lượng text | `results/profiling/string_quality.csv`, `categorical_summary.csv`, `categorical_top_values.txt` |
| §4.5 các binary flag | `results/audit/binary_flags.csv`, `binary_flag_value_counts.csv` |
| §4.6 / §8.1 invariant về thanh toán | `results/audit/payment_consistency.csv` |
| §4.7 / §8.2 song ánh về email | `results/audit/email_crosstab.csv` |
| §4.8 / §8.3 fraud score so với nhãn | `results/audit/fraud_score_threshold_scan.csv`, `fraud_score_relationship.csv`, `fraud_score_class_stats.csv` |
| §4.9 / §8.5 trust signal | `results/audit/trust_signal_relationship.csv`, `trust_signal_correlations.csv` |
| §4.10 tuổi công ty so với tuổi domain | `results/audit/company_domain_age.csv` |
| §4.11 khoảng giá trị của các score | `results/audit/score_range_validation.csv` |
| §5 giá trị thiếu | `results/profiling/column_profile.csv`, `results/audit/missing_overlap.csv`, `missing_combination_counts.csv`, `missing_value_relationship.csv` |
| §7 outlier | `results/audit/numeric_sanity.csv`, `results/profiling/numeric_summary.csv` |
| §11.9 provenance | `results/audit/provenance_indicators.csv` |
| Các báo cáo dạng diễn giải | `results/profiling/summary.md`, `results/audit/audit_summary.md` |

---

## 14. Kiểm soát thay đổi

- Các quy tắc này đã được **phê duyệt**. Việc triển khai sao chép lại chúng; nó
  không mở rộng chúng.
- Một lỗi không được bao phủ ở đây sẽ được **báo lên cấp trên**, không được sửa tại
  thời điểm triển khai.
- Mọi quyết định làm sạch mới đòi hỏi một vòng bằng chứng mới và một lần phê duyệt
  mới, và được ghi lại ở đây trước khi nó được triển khai.
- Tài liệu này chỉ mô tả bước **raw → staging**. Các quyết định thuộc dimensional
  model được liệt kê ở §12 và được giải quyết trong giai đoạn tiếp theo.
