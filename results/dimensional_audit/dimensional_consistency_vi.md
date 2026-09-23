# Audit Tính nhất quán Chiều / Phụ thuộc Hàm

## 1. Mục đích

Audit này đặt đúng một câu hỏi: **những thuộc tính nào có thể được gom an toàn vào cùng một dimension?** Và trả lời bằng phép đo, không phải bằng một thiết kế.

Việc gom thuộc tính vào một dimension là một khẳng định về sự phụ thuộc. Đặt `company_size` cạnh `company_name` là khẳng định rằng một công ty có một quy mô; đặt `industry` cạnh `internship_title` là khẳng định rằng một title thuộc về một ngành. Những khẳng định đó kiểm chứng được trước khi vẽ bất kỳ schema nào, và audit này kiểm chứng chúng.

**Những gì audit này không làm.** Nó không thiết kế star schema, không chốt grain, không tạo SQL, không chọn surrogate key, và không quyết định giữ cột nào trong hai cột dư thừa. Ở đâu bằng chứng còn mơ hồ thì sự mơ hồ được ghi nhận chứ không được giải quyết. Mục 10 và 11 liệt kê chính xác những gì còn bỏ ngỏ.

**Nguyên tắc đọc.** Một giá trị khác biệt bên trong một nhóm được báo cáo là *biến thiên*, không phải *lỗi*. Dataset này không có định danh công ty, định danh nhà tuyển dụng hay định danh tin đăng, nên sự bất đồng giữa hai dòng có thể là dữ liệu sai, mà cũng có thể là hai dòng vốn chưa bao giờ nói về cùng một đối tượng. Không phần nào bên dưới giả định điều nào đúng.

## 2. Cơ sở dữ liệu

| Mục | Giá trị |
| --- | --- |
| File nguồn | `E:/project/internship-scam-dw/data/staging/internship_postings_staging.csv` |
| Số dòng x số cột | 1,000,000 x 33 |
| Kích thước file | 170.4 MB |
| sha256 trước khi audit | `e86ab0983fa456d24e0a8403e2af7cb4d19adf69fc7995f641af9d85b7adefa3` |
| sha256 sau khi audit | `e86ab0983fa456d24e0a8403e2af7cb4d19adf69fc7995f641af9d85b7adefa3` |
| File staging không thay đổi | **CÓ** |
| Thời điểm tạo | 2026-09-23 18:17:28 |
| Script | `scripts/audit_dimensional_consistency.py` |
| Số dòng được phân tích | 1,000,000 |
| Khoảng posting_date | 2018-01-01 -> 2026-12-31 (3,287 date phân biệt) |

Tài liệu chuẩn được dùng cho ngữ nghĩa của từng cột: `docs/data_dictionary.md` và `docs/cleaning_rules.md`. Bằng chứng trước đó được tái sử dụng thay vì suy lại: `results/profiling/`, `results/audit/`, `results/staging/`.

**Tính toàn vẹn.** File CSV staging được mở ở chế độ chỉ đọc. Không giá trị nào bị làm sạch, impute, chặn ngưỡng, loại bỏ, chuẩn hóa, encode, hợp nhất thực thể hay khử trùng lặp. Hai cột làm việc (một số thứ tự ngày và một năm đăng tin) được sinh ra trong bộ nhớ để phục vụ các kiểm tra chuỗi thời gian và không bao giờ được ghi ra đâu cả. Giá trị sha256 ở trên được đo trước khi chạy và đo lại sau khi mọi kết quả đã được ghi.

**Ghi chú về các file CSV kèm theo.** Các file CSV trong thư mục này dùng tên cột và phần diễn giải bằng tiếng Anh, vì chúng là các artefact máy đọc được dùng chung cho cả hai bản ngôn ngữ của báo cáo. Mọi con số trong đó cũng đều xuất hiện trong cả hai bản báo cáo.

## 3. Tính nhất quán của thực thể công ty

### 3.1 company_name hành xử thế nào khi dùng làm khóa gom nhóm

`company_name` ở đây chỉ được dùng thuần túy như một **thuộc tính gom nhóm**. Nó không được giả định là company ID, và data dictionary nói rõ rằng nguồn này không có định danh công ty nào.

| Chỉ số | Giá trị |
| --- | ---: |
| Số company_name phân biệt | 535,938 |
| Chỉ xuất hiện đúng một dòng | 471,992 (88.0684%) |
| Xuất hiện ở nhiều hơn một dòng | 63,946 (11.9316%) |
| Số dòng thuộc các tên lặp lại | 528,008 (52.8008%) |
| Trung bình số tin đăng mỗi company_name | 1.865887 |
| Số tin đăng nhiều nhất của một company_name | 1,248 (`Smith PLC`) |

Phân phối số tin đăng trên mỗi `company_name`:

| Số tin đăng | Số company_name | % số tên | Số dòng bao phủ | % số dòng |
| --- | ---: | ---: | ---: | ---: |
| 1 | 471,992 | 88.0684 | 471,992 | 47.1992 |
| 2 | 33,422 | 6.2362 | 66,844 | 6.6844 |
| 3 | 11,021 | 2.0564 | 33,063 | 3.3063 |
| 4 | 5,055 | 0.9432 | 20,220 | 2.0220 |
| 5-9 | 6,516 | 1.2158 | 40,369 | 4.0369 |
| 10-19 | 2,612 | 0.4874 | 37,000 | 3.7000 |
| 20-49 | 3,563 | 0.6648 | 107,616 | 10.7616 |
| 50+ | 1,757 | 0.3278 | 222,896 | 22.2896 |

### 3.2 Tính ổn định của các thuộc tính phụ thuộc

Với mỗi thuộc tính, bảng dưới đây đếm trong số 63,946 giá trị `company_name` xuất hiện ở nhiều hơn một dòng, bao nhiêu giá trị mang đúng một giá trị phân biệt và bao nhiêu mang nhiều giá trị. Các tên chỉ có một dòng bị loại khỏi phép tính vì chúng ổn định theo cấu tạo và sẽ đẩy mọi tỷ lệ về sát 100%. Giá trị thiếu bị loại khỏi phép đếm giá trị phân biệt chứ không được coi là một giá trị riêng.

| Thuộc tính | Số tên lặp lại | Đúng 1 giá trị phân biệt | Nhiều giá trị phân biệt | % ổn định | Số giá trị phân biệt tối đa cho một tên | Số giá trị phân biệt toàn dataset |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `company_size` | 63,946 | 9,782 | 54,164 | 15.2973 | 4 | 4 |
| `company_age` | 63,946 | 1,531 | 62,411 | 2.3942 | 39 | 39 |
| `linkedin_presence` | 63,946 | 32,453 | 31,493 | 50.7506 | 2 | 2 |
| `website_available` | 63,946 | 36,943 | 27,003 | 57.7722 | 2 | 2 |
| `domain_age_months` | 63,946 | 75 | 63,871 | 0.1173 | 451 | 500 |
| `verification_status` | 63,946 | 25,362 | 38,584 | 39.6616 | 2 | 2 |
| `social_media_presence` | 63,946 | 28,599 | 35,347 | 44.7237 | 2 | 2 |
| `location` | 63,946 | 3,927 | 60,019 | 6.1411 | 9 | 9 |
| `industry` | 63,946 | 3,812 | 60,134 | 5.9613 | 9 | 9 |

Thuộc tính ổn định nhất là `website_available` với 57.7722%; kém ổn định nhất là `domain_age_months` với 0.1173%.

**Cách đọc.** Tỷ lệ ổn định thấp **không** chứng minh rằng dữ liệu sai. Có hai cách đọc khớp với cùng các con số này như nhau: hoặc một công ty thực sự đã thay đổi thuộc tính ghi nhận giữa các lần đăng tin, hoặc các dòng cùng `company_name` đơn giản là những công ty khác nhau trùng tên. Data dictionary đã cảnh báo rằng các tên tuân theo mẫu `<Họ> <Hậu tố>` và sự giống nhau về tên không được đọc thành sự đồng nhất về công ty. Không gì trong dataset này giải quyết được câu hỏi đó, và không gì ở đây bị sửa dựa trên nó.

### 3.3 Một số ví dụ được chọn

Các giá trị `company_name` dưới đây có mức phân tán giá trị phân biệt rộng nhất trên chín thuộc tính. Chúng được liệt kê như bằng chứng để xem xét, không phải như lỗi.

| company_name | Số tin đăng | `size` | `age` | `li` | `web` | `dom` | `ver` | `soc` | `loc` | `ind` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Smith LLC` | 1,198 | 4 | 39 | 2 | 2 | 451 | 2 | 2 | 9 | 9 |
| `Smith and Sons` | 1,244 | 4 | 39 | 2 | 2 | 449 | 2 | 2 | 9 | 9 |
| `Smith Inc` | 1,203 | 4 | 39 | 2 | 2 | 449 | 2 | 2 | 9 | 9 |
| `Smith PLC` | 1,248 | 4 | 39 | 2 | 2 | 443 | 2 | 2 | 9 | 9 |
| `Smith Group` | 1,186 | 4 | 39 | 2 | 2 | 440 | 2 | 2 | 9 | 9 |
| `Smith Ltd` | 1,205 | 4 | 39 | 2 | 2 | 439 | 2 | 2 | 9 | 9 |
| `Johnson Group` | 914 | 4 | 39 | 2 | 2 | 418 | 2 | 2 | 9 | 9 |
| `Johnson LLC` | 984 | 4 | 39 | 2 | 2 | 416 | 2 | 2 | 9 | 9 |
| `Johnson and Sons` | 928 | 4 | 39 | 2 | 2 | 414 | 2 | 2 | 9 | 9 |
| `Johnson Ltd` | 943 | 4 | 39 | 2 | 2 | 413 | 2 | 2 | 9 | 9 |
| `Johnson Inc` | 916 | 4 | 39 | 2 | 2 | 409 | 2 | 2 | 9 | 9 |
| `Johnson PLC` | 940 | 4 | 39 | 2 | 2 | 408 | 2 | 2 | 9 | 9 |

Viết tắt cột: `size` = `company_size`, `age` = `company_age`, `li` = `linkedin_presence`, `web` = `website_available`, `dom` = `domain_age_months`, `ver` = `verification_status`, `soc` = `social_media_presence`, `loc` = `location`, `ind` = `industry`. Mỗi ô là số giá trị phân biệt mà `company_name` đó nhận cho thuộc tính tương ứng.

### 3.4 Kiểm tra tổ hợp thuộc tính

Kiểm tra từng thuộc tính riêng lẻ là phép thử dễ dãi. Phép thử nghiêm ngặt hỏi liệu `company_name` một mình có quyết định **toàn bộ tổ hợp** của `company_size`, `linkedin_presence`, `website_available`, `verification_status`, `social_media_presence` cùng lúc hay không - đó chính là điều mà một dòng trong `DimCompany` khẳng định.

| Chỉ số | Giá trị |
| --- | ---: |
| Số tổ hợp quan sát được | 64 / 64 |
| Số company_name có đúng một tổ hợp | 473,664 (88.3804%) |
| Số company_name có nhiều tổ hợp | 62,274 |
| Tên lặp lại có đúng một tổ hợp | 1,672 / 63,946 (2.6147%) |
| Tên lặp lại có nhiều tổ hợp | 62,274 |
| Số tổ hợp tối đa của một tên | 61 |
| company_name -> tổ hợp có phải functional dependency | **Không** |
| Số dòng nằm trong các nhóm vi phạm | 524,627 (52.4627%) |

Phân phối số tổ hợp phân biệt trên mỗi `company_name`:

| Số tổ hợp | Số company_name | % số tên | Số dòng bao phủ | % số dòng |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 473,664 | 88.3804 | 475,373 | 47.5373 |
| 2 | 33,419 | 6.2356 | 68,604 | 6.8604 |
| 3 | 10,890 | 2.0320 | 34,301 | 3.4301 |
| 4 | 4,788 | 0.8934 | 20,489 | 2.0489 |
| 5 | 2,517 | 0.4696 | 13,806 | 1.3806 |
| 6 | 1,490 | 0.2780 | 10,115 | 1.0115 |
| 7 | 962 | 0.1795 | 7,741 | 0.7741 |
| 8 | 650 | 0.1213 | 6,366 | 0.6366 |
| 9 | 477 | 0.0890 | 5,531 | 0.5531 |
| 10 | 445 | 0.0830 | 5,973 | 0.5973 |
| 11 | 447 | 0.0834 | 6,876 | 0.6876 |
| 12 | 472 | 0.0881 | 8,130 | 0.8130 |
| 13 | 473 | 0.0883 | 9,050 | 0.9050 |
| 14 | 432 | 0.0806 | 9,064 | 0.9064 |
| 15 | 454 | 0.0847 | 10,370 | 1.0370 |
| 16 | 460 | 0.0858 | 11,659 | 1.1659 |
| 17 | 355 | 0.0662 | 9,785 | 0.9785 |
| 18 | 360 | 0.0672 | 10,618 | 1.0618 |
| 19 | 306 | 0.0571 | 9,972 | 0.9972 |
| 20 | 256 | 0.0478 | 8,920 | 0.8920 |
| 21 | 259 | 0.0483 | 9,680 | 0.9680 |
| 22 | 246 | 0.0459 | 10,151 | 1.0151 |
| 23 | 192 | 0.0358 | 8,363 | 0.8363 |
| 24 | 195 | 0.0364 | 9,606 | 0.9606 |
| 25 | 156 | 0.0291 | 8,073 | 0.8073 |
| 26 | 166 | 0.0310 | 9,745 | 0.9745 |
| 27 | 143 | 0.0267 | 8,802 | 0.8802 |
| 28 | 111 | 0.0207 | 7,470 | 0.7470 |
| 29 | 99 | 0.0185 | 7,034 | 0.7034 |
| 30 | 97 | 0.0181 | 7,533 | 0.7533 |
| 31 | 111 | 0.0207 | 8,946 | 0.8946 |
| 32 | 71 | 0.0132 | 6,202 | 0.6202 |
| 33 | 95 | 0.0177 | 8,553 | 0.8553 |
| 34 | 78 | 0.0146 | 7,817 | 0.7817 |
| 35 | 67 | 0.0125 | 7,003 | 0.7003 |
| 36 | 48 | 0.0090 | 5,315 | 0.5315 |
| 37 | 43 | 0.0080 | 5,278 | 0.5278 |
| 38 | 49 | 0.0091 | 6,432 | 0.6432 |
| 39 | 33 | 0.0062 | 4,657 | 0.4657 |
| 40 | 33 | 0.0062 | 4,937 | 0.4937 |
| 41 | 35 | 0.0065 | 5,414 | 0.5414 |
| 42 | 21 | 0.0039 | 3,788 | 0.3788 |
| 43 | 32 | 0.0060 | 5,745 | 0.5745 |
| 44 | 26 | 0.0049 | 5,434 | 0.5434 |
| 45 | 26 | 0.0049 | 5,981 | 0.5981 |
| 46 | 25 | 0.0047 | 6,428 | 0.6428 |
| 47 | 18 | 0.0034 | 5,258 | 0.5258 |
| 48 | 21 | 0.0039 | 6,233 | 0.6233 |
| 49 | 24 | 0.0045 | 7,549 | 0.7549 |
| 50 | 14 | 0.0026 | 5,000 | 0.5000 |
| 51 | 14 | 0.0026 | 4,975 | 0.4975 |
| 52 | 9 | 0.0017 | 3,426 | 0.3426 |
| 53 | 13 | 0.0024 | 5,161 | 0.5161 |
| 54 | 11 | 0.0021 | 5,090 | 0.5090 |
| 55 | 9 | 0.0017 | 5,137 | 0.5137 |
| 56 | 8 | 0.0015 | 5,041 | 0.5041 |
| 57 | 2 | 0.0004 | 1,459 | 0.1459 |
| 58 | 7 | 0.0013 | 5,094 | 0.5094 |
| 59 | 4 | 0.0007 | 4,316 | 0.4316 |
| 60 | 6 | 0.0011 | 4,814 | 0.4814 |
| 61 | 4 | 0.0007 | 4,317 | 0.4317 |

**Đây là phép đo có hệ quả lớn nhất trong toàn bộ audit.** Nó là phép thử trực tiếp xem một `DimCompany` đơn giản khóa theo `company_name` có bảo vệ được hay không, và câu trả lời là chỉ với bằng chứng này thì không. Điều đó không làm cho một dimension công ty trở nên bất khả thi - nó khiến việc tạo dimension đó thành một quyết định cần nêu rõ giả định, chứ không phải quyết định được dữ liệu tự nó ủng hộ.

## 4. Thuộc tính công ty biến thiên theo thời gian

Mục 3.2 và 3.4 đo xem các thuộc tính có khác nhau hay không. Mục này đo xem chúng có khác nhau **một cách hợp lý theo thời gian lịch** hay không. Với mỗi `company_name`, các dòng được sắp theo `posting_date` và các tin đăng liên tiếp được so sánh: mức thay đổi của tuổi được ghi nhận được đặt cạnh khoảng thời gian thực tế đã trôi qua giữa hai tin đăng.

### 4.1 company_age theo thời gian

| Chỉ số | Giá trị |
| --- | ---: |
| Tên lặp lại có một giá trị company_age | 1,531 (2.3942%) |
| Tên lặp lại có nhiều giá trị | 62,411 |
| Số company_age phân biệt tối đa cho một tên | 39 |
| Số cặp tin đăng liên tiếp được xét | 458,854 |
| Cặp có company_age tăng | 225,123 (49.0620%) |
| Cặp có giá trị không đổi | 11,591 (2.5261%) |
| Cặp có giá trị **giảm** theo thời gian | **222,140** (48.4119%) |
| Số tên có ít nhất một lần giảm | 44,130 |
| Cùng tên, cùng ngày, company_age mâu thuẫn | 8,675 |
| Nhóm (company_name, năm) có >1 dòng | 72,173 |
| ... trong đó, có nhiều giá trị company_age | 70,872 (98.1974%) |
| Cặp nằm ngoài dung sai +/-1.0 năm so với thời gian trôi qua | 435,828 (94.9818%) |
| Mức giảm lớn nhất (năm) | -38.0 |

**Chỉ là bằng chứng.** Tuổi của một công ty không thể giảm khi lịch tiến lên, nên 222,140 cặp giảm và 70,872 nhóm (công ty, năm) chứa nhiều giá trị tuổi là không nhất quán với giả thiết rằng `company_age` là thuộc tính của một thực thể ổn định được theo dõi theo thời gian. Chúng cũng nhất quán không kém với giả thiết rằng `company_name` không định danh một thực thể duy nhất. **Không giá trị nào bị sửa, và không dòng nào bị đánh dấu là không hợp lệ.**

### 4.2 domain_age_months theo thời gian

| Chỉ số | Giá trị |
| --- | ---: |
| Tên lặp lại có một giá trị domain_age_months | 75 (0.1173%) |
| Tên lặp lại có nhiều giá trị | 63,871 |
| Số domain_age_months phân biệt tối đa cho một tên | 451 |
| Số cặp tin đăng liên tiếp được xét | 464,062 |
| Cặp tăng theo thời gian | 233,185 (50.2487%) |
| Cặp không đổi | 969 (0.2088%) |
| Cặp **giảm** | **229,908** (49.5425%) |
| Số tên có ít nhất một lần giảm | 45,197 |
| Cùng tên, cùng ngày, giá trị mâu thuẫn | 9,063 |
| Cặp nằm ngoài dung sai +/-6.0 tháng so với thời gian trôi qua | 452,442 (97.4960%) |
| Số tên liên quan tới các cặp đó | 63,125 |
| Mức giảm lớn nhất (tháng) | -499.0 |
| Phần dư (mức thay đổi trừ số tháng trôi qua): nhỏ nhất / trung vị / lớn nhất | -565.36 / -5.41 / 498.93 |

Tuổi domain tính theo tháng lẽ ra phải tăng xấp xỉ bằng số tháng trôi qua giữa hai tin đăng. Cột phần dư ở trên đo đúng khoảng chênh đó. Cũng như với `company_age`, hành vi quan sát được chỉ được báo cáo và không gì bị sửa: data dictionary đã ghi nhận rằng việc `domain_age_months` vượt `company_age * 12` **không** bị coi là không hợp lệ, vì domain mua lại, đổi thương hiệu và tên miền đăng ký để đó đều tạo ra hiện tượng này một cách chính đáng.

**Hệ quả với mô hình hóa.** Nếu `company_name` được chọn làm khóa công ty thì cả hai giá trị tuổi sẽ là thuộc tính biến thiên theo thời gian của khóa đó, và đây đúng là dấu hiệu kinh điển dẫn tới thiết kế SCD Type 2. Nhưng các phép đo ở trên cho thấy biến thiên không đơn điệu và do đó không giống một lịch sử thực thể, nên một thiết kế SCD sẽ ghi lại những thay đổi phiên bản có thể không tương ứng với điều gì có thật. Đây được nêu như một rủi ro, không phải khuyến nghị theo hướng nào.

## 5. Phụ thuộc giữa các thuộc tính phân loại

### 5.1 internship_title so với các thuộc tính vị trí công việc

Không giả định phụ thuộc theo bất kỳ chiều nào. Bảng chỉ báo cáo mức liên hệ và cardinality. Cramer's V đã hiệu chỉnh độ chệch; giá trị gần 0 nghĩa là hai thuộc tính biến thiên độc lập.

| Cặp | Số mức | Số ô quan sát / khả dĩ | Cramer's V | title -> thuộc tính | thuộc tính -> title | Số giá trị mỗi title |
| --- | ---: | ---: | ---: | :---: | :---: | ---: |
| `internship_title` x `industry` | 9 x 9 | 81 / 81 | 0.001236 | không | không | 9-9 |
| `internship_title` x `employment_type` | 9 x 4 | 36 / 36 | 0.000000 | không | không | 4-4 |
| `internship_title` x `work_mode` | 9 x 3 | 27 / 27 | 0.001536 | không | không | 3-3 |
| `internship_title` x `location` | 9 x 9 | 81 / 81 | 0.000000 | không | không | 9-9 |

Tỷ trọng dòng của 9 title chạy từ 11.0502% đến 11.1577%. Mức liên hệ lớn nhất đo được là 0.001536. **`internship_title` không quyết định thuộc tính nào trong bốn thuộc tính, và không thuộc tính nào quyết định nó.** Mọi lưới title x thuộc tính đều đầy đủ, đó là dấu hiệu của các nhãn độc lập chứ không phải của một phân cấp.

### 5.2 industry so với internship_title

| Chỉ số | Giá trị |
| --- | ---: |
| Số industry x số title | 9 x 9 = 81 ô |
| Số ô có dữ liệu | 81 (100.0000%) |
| Số title mỗi industry (nhỏ nhất-lớn nhất) | 9-9 |
| Số industry mỗi title (nhỏ nhất-lớn nhất) | 9-9 |
| Cramer's V | 0.001236 |
| industry -> internship_title | không |
| internship_title -> industry | không |
| Ô nhỏ nhất / lớn nhất | 11,980 / 12,635 |
| Giá trị ô kỳ vọng nếu độc lập | 12,345.68 |

**Không tồn tại quan hệ tất định theo bất kỳ chiều nào.** Mỗi industry đều chứa cả 9 title và mỗi title đều xuất hiện ở cả 9 industry; số đếm ô quan sát được nằm sát mức 12,346 kỳ vọng khi độc lập. Do đó ở đây hai thuộc tính **không** bị ép vào chung một dimension. Việc chúng có được gộp lại hay không là quyết định thiết kế vì sự tiện lợi khi truy vấn, và phải được đưa ra với hiểu biết rằng nó tạo ra một tích Descartes 81 dòng không có functional dependency nào đứng sau.

### 5.3 location

| location | Số dòng | % số dòng | Số company_name phân biệt | Số dòng mỗi tên | Số industry | Số title | Số tin giả | Tỷ lệ tin giả % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Bangalore` | 111,441 | 11.1441 | 75,340 | 1.4792 | 9 | 9 | 25,155 | 22.5725 |
| `Berlin` | 110,990 | 11.0990 | 75,029 | 1.4793 | 9 | 9 | 24,651 | 22.2101 |
| `Dubai` | 110,987 | 11.0987 | 75,008 | 1.4797 | 9 | 9 | 24,699 | 22.2540 |
| `London` | 110,754 | 11.0754 | 75,016 | 1.4764 | 9 | 9 | 24,481 | 22.1039 |
| `New York` | 110,559 | 11.0559 | 74,712 | 1.4798 | 9 | 9 | 24,548 | 22.2035 |
| `San Francisco` | 111,390 | 11.1390 | 75,379 | 1.4777 | 9 | 9 | 24,732 | 22.2031 |
| `Singapore` | 110,882 | 11.0882 | 75,243 | 1.4737 | 9 | 9 | 24,636 | 22.2182 |
| `Sydney` | 111,520 | 11.1520 | 75,544 | 1.4762 | 9 | 9 | 24,624 | 22.0803 |
| `Toronto` | 111,477 | 11.1477 | 75,735 | 1.4719 | 9 | 9 | 24,432 | 21.9166 |

Tỷ lệ tin giả chạy từ 21.9166% đến 22.5725% so với mức nền toàn dataset 22.1958% - chênh lệch 0.6559 điểm phần trăm. Mức liên hệ giữa `location` và `industry` là 0.000000.

Cũng lưu ý rằng tổng số `company_name` của chín thành phố là 677,006 trong khi toàn bộ chỉ có 535,938 tên phân biệt - cùng một tên xuất hiện ở nhiều thành phố, thêm một bằng chứng nữa rằng `company_name` không hành xử như một khóa thực thể.

> **Giới hạn được giữ nguyên: stipend cố ý không được báo cáo theo location.** Đơn vị tiền tệ và kỳ trả của `stipend` không được tài liệu hóa trong nguồn, và chín thành phố thuộc các vùng tiền tệ khác nhau. Mọi giá trị trung bình, tổng hay so sánh `stipend` theo `location` sẽ là cộng hoặc so sánh các đơn vị khác nhau, trông có vẻ đáng tin nhưng không mang ý nghĩa gì. Giới hạn này chưa được giải quyết và được chuyển tiếp sang mục 7, 10 và 11.

### 5.4 employment_type và work_mode

| employment_type \ work_mode | Hybrid | Onsite | Remote | Tổng |
| --- | ---: | ---: | ---: | ---: |
| `Contract` | 62,499 | 50,033 | 137,137 | 249,669 |
| `Full-Time` | 62,201 | 50,077 | 137,355 | 249,633 |
| `Internship` | 62,943 | 49,832 | 137,223 | 249,998 |
| `Part-Time` | 62,883 | 50,193 | 137,624 | 250,700 |
| **Tổng** | 250,526 | 200,135 | 549,339 | 1,000,000 |

| Chỉ số | Giá trị |
| --- | ---: |
| Số tổ hợp khả dĩ | 12 |
| Số tổ hợp quan sát được | 12 |
| Mọi tổ hợp đều xuất hiện | **Có** |
| Ô nhỏ nhất / lớn nhất | 49,832 (4.9832%) / 137,624 (13.7624%) |
| Cramer's V | 0.000000 |
| employment_type -> work_mode | không |
| work_mode -> employment_type | không |

Không thuộc tính nào quyết định hàm thuộc tính kia và lưới là đầy đủ, nên cặp này là hai nhãn độc lập. Có thể giữ thành hai dimension hoặc gộp thành một dimension kết hợp nhỏ; cả hai đều bảo vệ được và ở đây không chọn phương án nào.

### 5.5 Các thuộc tính email

| Chỉ số | Giá trị |
| --- | ---: |
| recruiter_email_type -> suspicious_email_domain | đúng (0 dòng vi phạm) |
| suspicious_email_domain -> recruiter_email_type | đúng (0 dòng vi phạm) |
| Song ánh hoàn hảo | **ĐÃ XÁC NHẬN** |
| Số ô có dữ liệu | 2 / 4 |
| Cramer's V | 1.000000 |

| recruiter_email_type | suspicious_email_domain | Số dòng | % số dòng |
| --- | ---: | ---: | ---: |
| `Corporate` | 0 | 749,433 | 74.9433 |
| `Corporate` | 1 | 0 | 0.0000 |
| `Free` | 0 | 0 | 0.0000 |
| `Free` | 1 | 250,567 | 25.0567 |

**Đã xác nhận trong staging.** Song ánh mà audit trước xác lập vẫn đúng chính xác. Với mô hình hóa chiều, điều này nghĩa là lưu cả hai thuộc tính trong cùng một dimension nhỏ sẽ lưu thông tin của một thuộc tính hai lần: biết một giá trị là biết chắc giá trị kia. **Sự dư thừa đó được ghi nhận ở đây, không được xử lý.** Việc bỏ một trong hai là quyết định schema, và nó có chi phí thật - hai cột không thay thế được cho nhau về ý nghĩa, một bên là nhãn người đọc được còn một bên là cờ, và một bản trích sau này có thể phá vỡ song ánh.

### 5.6 Các thuộc tính thanh toán

| Kiểm tra | Giá trị |
| --- | ---: |
| Số dòng được kiểm | 1,000,000 |
| payment_required == (registration_fee > 0) | **ĐÚNG CHÍNH XÁC** |
| Số dòng bất đồng | 0 |
| payment_required = 0 nhưng có phí dương | 0 |
| payment_required = 1 nhưng phí bằng 0 | 0 |
| Số dòng payment_required = 1 | 99,905 (9.9905%) |
| Số dòng registration_fee = 0 | 900,095 (90.0095%) |
| Số giá trị phí phân biệt (mọi dòng / dòng khác 0) | 4,951 / 4,950 |
| Phí khác 0: nhỏ nhất / trung vị / lớn nhất | 50 / 2,520.0 / 4,999 |

**Đã xác nhận lại trên staging.** Về cấu trúc, hai cột không cùng một loại: `payment_required` là một **cờ** hai trạng thái, phù hợp làm thuộc tính dimension hoặc phần tử của junk dimension, trong khi `registration_fee` là một **lượng số** có thể cộng và lấy trung bình, phù hợp làm measure trong fact. Cờ là dạng thô hóa của lượng - luôn tính lại được từ lượng, nhưng lượng thì không bao giờ khôi phục được từ cờ.

**Không cột nào bị xóa và không quyết định nào được đưa ra ở đây** về việc lưu cột nào như measure, cột nào như trường dẫn xuất, hay giữ cả hai. Lựa chọn đó thuộc về giai đoạn star schema và được liệt kê ở mục 10.

### 5.7 Các bó thuộc tính cardinality thấp

Mỗi bó ứng viên thực sự nhận bao nhiêu tổ hợp. Số tổ hợp quan sát được nhỏ nghĩa là một junk dimension khả thi về mặt kỹ thuật; điều đó không nói gì về việc có nên dùng hay không.

| Bó | Thuộc tính | Quan sát / khả dĩ | Tổ hợp lớn nhất |
| --- | --- | ---: | ---: |
| `trust_presence_flags` | `linkedin_presence + website_available + verification_status + social_media_presence` | 16 / 16 | 357,337 (35.7337%) |
| `fraud_flags` | `payment_required + fake_certificate_offer + suspicious_email_domain + unrealistic_salary_flag` | 8 / 8 | 620,594 (62.0594%) |
| `employment_arrangement` | `employment_type + work_mode` | 12 / 12 | 137,624 (13.7624%) |
| `company_presence_5` | `company_size + linkedin_presence + website_available + verification_status + social_media_presence` | 64 / 64 | 107,190 (10.7190%) |
| `recruiter_email_pair` | `recruiter_email_type + suspicious_email_domain` | 2 / 4 | 749,433 (74.9433%) |

## 6. Các dimension ứng viên

### 6.1 Phân loại tạm thời cho từng trường

Mỗi trường trong ba nhóm logic mà đề bài nêu - chất lượng nội dung, trust/công ty, và gian lận/kết quả - được phân loại **tạm thời**. Không dimension nào được tạo ra từ một nhóm chỉ vì các thành viên nghe có vẻ liên quan. Cột *% ổn định* là tỷ lệ các `company_name` nhiều dòng mà tại đó trường chỉ nhận một giá trị phân biệt; đây là bằng chứng chính để tách thuộc tính công ty khỏi giá trị mức tin đăng.

**Chất lượng nội dung**

| Trường | Phân loại tạm thời | Số giá trị phân biệt | % thiếu | % ổn định trong company_name | Bằng chứng |
| --- | --- | ---: | ---: | ---: | --- |
| `emotional_manipulation_score` | **candidate measure** | 101 | 0.0000 | 1.4528 | Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa. |
| `grammatical_errors` | **candidate measure** | 15 | 0.0000 | 9.3814 | Là một đại lượng đếm (0-14). Additive khi cộng dồn; cũng có thể chia dải thành một dimension attribute, nhưng điều đó không được quyết định ở đây. |
| `job_description_length` | **candidate measure** | 3,946 | 0.0000 | 0.0297 | Dạng số, biên độ rộng, thay đổi theo từng dòng trong cùng một company_name; không có tính chất nhãn để cắt lát. |
| `keyword_spam_score` | **candidate measure** | 101 | 0.0000 | 1.3683 | Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa. |
| `phishing_language_score` | **candidate measure** | 100 | 0.0000 | 1.9782 | Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa. |
| `urgency_score` | **candidate measure** | 101 | 0.0000 | 0.7381 | Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa. |
| `vague_description_score` | **candidate measure** | 101 | 0.0000 | 1.0571 | Điểm số giới hạn 0-100 ghi nhận theo từng tin đăng; quy tắc tính không được tài liệu hóa. |

**Trust / công ty**

| Trường | Phân loại tạm thời | Số giá trị phân biệt | % thiếu | % ổn định trong company_name | Bằng chứng |
| --- | --- | ---: | ---: | ---: | --- |
| `domain_age_months` | **unresolved** | 500 | 0.0000 | 0.1173 | Vừa mang tính số vừa mang tính công ty: nó sẽ là một thuộc tính công ty thay đổi chậm nếu company_name là khóa thực thể, và là measure theo tin đăng nếu không. Mức bất ổn đo được bên dưới để ngỏ cả hai cách đọc. |
| `linkedin_presence` | **candidate flag** | 2 | 0.0000 | 50.7506 | Nhị phân 0/1. Về ngữ nghĩa giống thuộc tính công ty, nhưng không ổn định giữa các dòng cùng company_name, nên không thể gắn vào một thực thể công ty với bằng chứng hiện có. |
| `social_media_presence` | **candidate flag** | 2 | 0.0000 | 44.7237 | Nhị phân 0/1. Tình huống giống linkedin_presence. |
| `trust_signal_score` | **candidate measure** | 1,001 | 1.0000 | 1.0556 | Điểm tổng hợp có giới hạn, thiếu 1%, audit trước đã xác lập rằng nó KHÔNG được suy ra tất định từ bốn cờ trust. |
| `verification_status` | **candidate flag** | 2 | 0.0000 | 39.6616 | Nhị phân 0/1. Tình huống giống linkedin_presence. |
| `website_available` | **candidate flag** | 2 | 0.0000 | 57.7722 | Nhị phân 0/1. Tình huống giống linkedin_presence. |

**Gian lận / kết quả**

| Trường | Phân loại tạm thời | Số giá trị phân biệt | % thiếu | % ổn định trong company_name | Bằng chứng |
| --- | --- | ---: | ---: | ---: | --- |
| `fake_certificate_offer` | **candidate flag** | 2 | 0.0000 | 71.6089 | Nhị phân 0/1 mô tả nội dung mà tin đăng đưa ra. |
| `fraud_score` | **candidate measure** | 1,001 | 0.0000 | 0.2189 | Điểm tổng hợp giới hạn 0-100; audit trước đã xác lập rằng nó KHÔNG quyết định is_fake_posting. |
| `is_fake_posting` | **outcome** | 2 | 0.0000 | 48.0921 | Là kết quả được gán nhãn của một tin đăng. Đây là thứ mà warehouse được xây để phân tích, không phải một thuộc tính cắt lát chọn độc lập. |
| `payment_required` | **candidate flag** | 2 | 0.0000 | 67.1395 | Nhị phân 0/1, và tái tạo chính xác được từ registration_fee > 0. Việc lưu nó là câu hỏi về dư thừa, không phải câu hỏi về thông tin. |
| `registration_fee` | **candidate measure** | 4,951 | 0.0000 | 66.6171 | Dạng số và thực sự là một đại lượng; giá trị 0 có nghĩa (không thu phí), không phải giá trị thay thế. Đơn vị tiền tệ không được tài liệu hóa. |
| `suspicious_email_domain` | **candidate flag** | 2 | 0.0000 | 44.5126 | Nhị phân 0/1, song ánh hoàn hảo với recruiter_email_type; cặp này chỉ mang lượng thông tin của một thuộc tính. |
| `unrealistic_salary_flag` | **degenerate attribute** | 1 | 0.0000 | 100.0000 | Hằng số trên toàn bộ các dòng. Một thuộc tính chỉ có một giá trị tạo ra dimension một phần tử và không cắt lát được gì; nó vẫn được giữ trong staging và cách xử lý trong warehouse được hoãn lại. |

Các trường ngoài ba nhóm trên, phân loại theo cùng bằng chứng:

| Trường | Phân loại tạm thời | Số giá trị phân biệt | % thiếu | % ổn định trong company_name | Bằng chứng |
| --- | --- | ---: | ---: | ---: | --- |
| `company_age` | **unresolved** | 39 | 1.0000 | 2.3942 | Dạng số, nhưng về ngữ nghĩa là thuộc tính công ty tính bằng năm. Cùng sự nhập nhằng như domain_age_months. |
| `company_size` | **candidate dimension attribute** | 4 | 0.0000 | 15.2973 | Nhãn bốn giá trị không có thứ tự tự nhiên; là thuộc tính cắt lát điển hình, nhưng vướng vấn đề định danh công ty nêu bên dưới. |
| `employment_type` | **candidate dimension attribute** | 4 | 0.0000 | 14.2308 | Nhãn bốn giá trị về hình thức hợp đồng. |
| `industry` | **candidate dimension attribute** | 9 | 0.0000 | 5.9613 | Nhãn chín giá trị, đầy đủ và gần như đều. |
| `internship_title` | **candidate dimension attribute** | 9 | 0.0000 | 6.1052 | Nhãn chín giá trị mô tả vai trò được đăng tuyển. |
| `is_future_posting` | **candidate flag** | 2 | 0.0000 | 85.4612 | Cờ đánh dấu chất lượng dữ liệu sinh ở staging so với một ngày tham chiếu cố định; không phải thuộc tính nghiệp vụ. |
| `location` | **candidate dimension attribute** | 9 | 0.0000 | 6.1411 | Nhãn chín giá trị, đầy đủ và gần như đều. Nó định vị cái gì - nơi làm việc, công ty hay nhà tuyển dụng - không được nguồn xác lập. |
| `recruiter_email_type` | **candidate dimension attribute** | 2 | 0.0000 | 44.5126 | Nhãn hai giá trị; mang cùng thông tin với suspicious_email_domain. |
| `recruiter_experience_years` | **candidate measure** | 183 | 0.0000 | 0.6396 | Mức số ghi nhận theo từng tin đăng. Không có định danh nhà tuyển dụng nên không thể gắn vào một thực thể recruiter. |
| `recruiter_response_time_hours` | **candidate measure** | 595 | 0.0000 | 0.2612 | Khoảng thời gian dạng số ghi nhận theo từng tin đăng; cũng thiếu định danh nhà tuyển dụng. |
| `stipend` | **unresolved** | 73,830 | 1.0000 | 1.0571 | Dạng số, nhưng đơn vị tiền tệ và kỳ trả không được tài liệu hóa, nên chưa thể gọi nó là measure của một đại lượng cụ thể nào. |
| `work_mode` | **candidate dimension attribute** | 3 | 0.0000 | 25.5278 | Nhãn ba giá trị mô tả nơi thực hiện công việc. |

### 6.2 Các nhóm dimension ứng viên

**Đây là các ứng viên để xem xét về sau. Không star schema nào được đề xuất, và danh sách dưới đây không phải một thiết kế.** Mức tin cậy nói lên bằng chứng ủng hộ cách gom nhóm đến đâu, không phải dimension đó sẽ hữu ích đến mức nào.

#### Date - mức tin cậy: **Cao**

| Khía cạnh | Kết luận |
| --- | --- |
| Thuộc tính có thể đưa vào | `posting_date`, `is_future_posting` - cộng các thuộc tính lịch dẫn xuất từ posting_date (năm, quý, tháng, thứ trong tuần) |
| Bằng chứng ủng hộ cách gom nhóm | posting_date có mặt và parse được trên toàn bộ 1,000,000 dòng, với 3,287 date phân biệt trải từ 2018-01-01 đến 2026-12-31. Một dimension ngày được sinh ra từ lịch chứ không suy ra từ dữ liệu, nên các thuộc tính của nó không cần bằng chứng về tính ổn định. |
| Vấn đề về tính nhất quán | 30,246 dòng (3.0246%) có ngày sau ngày tham chiếu cố định 2026-09-23 và chỉ được đánh cờ, không bị lọc bỏ. Do đó dimension ngày phải bao phủ cả các ngày tương lai, nếu không những dòng đó mất liên kết join. |
| Lo ngại về cardinality | 3,287 dòng nếu xây ở grain ngày trên khoảng quan sát được - rất nhỏ. |
| Lo ngại về biến thiên theo thời gian | Không có. Các thuộc tính lịch của một ngày cho trước không thay đổi. |
| Cân nhắc về SCD | Không áp dụng. |
| Mức tin cậy | **Cao** |

#### Internship / Role - mức tin cậy: **Trung bình**

| Khía cạnh | Kết luận |
| --- | --- |
| Thuộc tính có thể đưa vào | `internship_title` - và có thể cả industry |
| Bằng chứng ủng hộ cách gom nhóm | internship_title nhận 9 giá trị, tỷ trọng dòng từ 11.0502% đến 11.1577%. So với industry, cả 81 trên 81 ô đều có dữ liệu và Cramer's V bằng 0.001236, tức hai thuộc tính biến thiên độc lập. |
| Vấn đề về tính nhất quán | internship_title KHÔNG quyết định industry (9 industry cho mỗi title) và industry KHÔNG quyết định internship_title (9 title cho mỗi industry). Gộp cả hai vào một dimension sẽ tạo tích Descartes 81 dòng mà không có functional dependency nào biện minh. |
| Lo ngại về cardinality | 9 dòng nếu đứng riêng, hoặc 81 nếu gộp industry vào. |
| Lo ngại về biến thiên theo thời gian | Chín nhãn là các chuỗi ổn định; không thuộc tính nào của một title thay đổi theo thời gian trong bản trích này. |
| Cân nhắc về SCD | Không cần ở mức cardinality này nếu dimension chỉ là bảng tra cứu nhãn. |
| Mức tin cậy | **Trung bình** |

#### Company - mức tin cậy: **Thấp**

| Khía cạnh | Kết luận |
| --- | --- |
| Thuộc tính có thể đưa vào | `company_name`, `company_size`, `company_age`, `linkedin_presence`, `website_available`, `domain_age_months`, `verification_status`, `social_media_presence` |
| Bằng chứng ủng hộ cách gom nhóm | company_name là handle công ty duy nhất trong dataset: 535,938 giá trị phân biệt trên 1,000,000 dòng, trong đó 63,946 (11.9316%) xuất hiện ở nhiều hơn một dòng, bao phủ 528,008 dòng (52.8008%). |
| Vấn đề về tính nhất quán | Nghiêm trọng. Chỉ 1,672 trong 63,946 company_name lặp lại (2.6147%) mang một tổ hợp duy nhất của năm thuộc tính hiện diện. Thuộc tính yếu nhất là domain_age_months với 0.1173% ổn định. Hoặc company_name không phải định danh công ty, hoặc thuộc tính ghi nhận của một công ty thay đổi giữa các lần đăng tin; dữ liệu không phân biệt được hai khả năng. |
| Lo ngại về cardinality | 535,938 phần tử - 53.5938% số dòng fact. Một dimension cỡ đó gần như lưu bảng fact hai lần. |
| Lo ngại về biến thiên theo thời gian | Đo trực tiếp: trong 458,854 cặp tin đăng liên tiếp cùng một company_name, company_age giảm ở 222,140 cặp (48.4119%) và domain_age_months giảm ở 229,908 cặp (49.5425%). Các thuộc tính này không hành xử như một lịch sử công ty đơn điệu. |
| Cân nhắc về SCD | SCD Type 2 là câu trả lời kinh điển cho thuộc tính công ty thay đổi, nhưng SCD giả định có một business key ổn định. Ở đây không có, nên thiết kế SCD sẽ version hóa một định danh có thể không định danh gì cả. |
| Mức tin cậy | **Thấp** |

#### Location - mức tin cậy: **Trung bình**

| Khía cạnh | Kết luận |
| --- | --- |
| Thuộc tính có thể đưa vào | `location` |
| Bằng chứng ủng hộ cách gom nhóm | 9 giá trị, mỗi giá trị chiếm từ 11.0559% đến 11.1520% số dòng, đầy đủ trên mọi dòng. Tỷ lệ tin giả chạy từ 21.9166% đến 22.5725% so với mức nền 22.1958% - chênh lệch 0.6559 pp. |
| Vấn đề về tính nhất quán | Vấn đề thuộc về ngữ nghĩa, không phải cấu trúc. Nguồn không nói rõ location là nơi làm việc, địa chỉ công ty hay vị trí nhà tuyển dụng, và không có cột quốc gia, khu vực hay mã quốc gia, nên không thể xây phân cấp địa lý chỉ từ dataset này. |
| Lo ngại về cardinality | 9 dòng. |
| Lo ngại về biến thiên theo thời gian | Không quan sát thấy. |
| Cân nhắc về SCD | Không cần, trừ khi nhập phân cấp từ nguồn ngoài rồi sau đó sửa đổi. |
| Mức tin cậy | **Trung bình** |

#### Employment / Work Arrangement - mức tin cậy: **Cao**

| Khía cạnh | Kết luận |
| --- | --- |
| Thuộc tính có thể đưa vào | `employment_type`, `work_mode` |
| Bằng chứng ủng hộ cách gom nhóm | Cả 12 trên 12 tổ hợp employment_type x work_mode đều xuất hiện, kích thước ô từ 4.9832% đến 13.7624% số dòng, và Cramer's V bằng 0.000000. Không thuộc tính nào quyết định thuộc tính kia, nên cặp này là một lưới đầy đủ nhỏ chứ không phải một phân cấp. |
| Vấn đề về tính nhất quán | Chỉ là employment_type chứa các giá trị (Full-Time, Part-Time, Contract) nghe không khớp với chữ internship trong một dataset về tin tuyển thực tập. Đây là câu hỏi ngữ nghĩa của nguồn, không phải lỗi dữ liệu. |
| Lo ngại về cardinality | 12 dòng nếu gộp thành một dimension, hoặc 4 + 3 nếu tách đôi. |
| Lo ngại về biến thiên theo thời gian | Không quan sát thấy. |
| Cân nhắc về SCD | Không cần. |
| Mức tin cậy | **Cao** |

#### Recruiter - mức tin cậy: **Trung bình**

| Khía cạnh | Kết luận |
| --- | --- |
| Thuộc tính có thể đưa vào | `recruiter_email_type`, `suspicious_email_domain` |
| Bằng chứng ủng hộ cách gom nhóm | Song ánh recruiter_email_type <-> suspicious_email_domain vẫn đúng chính xác trong staging: 0 dòng vi phạm chiều thuận và 0 dòng vi phạm chiều ngược, 2 trên 4 ô có dữ liệu, Cramer's V 1.000000. Một dimension hai dòng thì cực rẻ. |
| Vấn đề về tính nhất quán | Không có định danh nhà tuyển dụng ở bất kỳ đâu trong dataset. Do đó recruiter_experience_years và recruiter_response_time_hours không thể gắn vào một thực thể recruiter và hành xử như các con số theo từng tin đăng. Lưu cả hai thuộc tính email trong cùng một dimension là nhân đôi thông tin của một thuộc tính duy nhất. |
| Lo ngại về cardinality | 2 dòng. |
| Lo ngại về biến thiên theo thời gian | Không quan sát thấy. |
| Cân nhắc về SCD | Không cần. |
| Mức tin cậy | **Trung bình** |

#### Fraud / Risk attributes - mức tin cậy: **Thấp**

| Khía cạnh | Kết luận |
| --- | --- |
| Thuộc tính có thể đưa vào | `payment_required`, `fake_certificate_offer`, `suspicious_email_domain`, `unrealistic_salary_flag` - và, như một bó riêng, các cờ trust linkedin_presence, website_available, verification_status và social_media_presence |
| Bằng chứng ủng hộ cách gom nhóm | Bốn cờ fraud nhận 8 trong 8 tổ hợp khả dĩ; bốn cờ trust nhận 16 trong 16. Cả hai bó đều đủ nhỏ để khả thi về mặt kỹ thuật như junk dimension. |
| Vấn đề về tính nhất quán | Khả thi không đồng nghĩa với đúng. is_fake_posting là kết quả phân tích và không nên nằm trong một dimension cắt lát cùng với chính các biến dự báo của nó; unrealistic_salary_flag là hằng số và sẽ thêm một cột không bao giờ biến thiên; suspicious_email_domain đã xuất hiện trong ứng viên Recruiter, nên cùng một thông tin sẽ tới được bằng hai đường. |
| Lo ngại về cardinality | Lần lượt 8 và 16 dòng. |
| Lo ngại về biến thiên theo thời gian | Các cờ trust không ổn định trong cùng company_name (xem phần công ty), đó là lý do ở đây chúng được xem là cờ mức tin đăng chứ không phải thuộc tính công ty. |
| Cân nhắc về SCD | Không áp dụng cho một junk dimension gồm các tổ hợp cờ. |
| Mức tin cậy | **Thấp** |

## 7. Các measure ứng viên

Tính additive được phân loại cho từng ứng viên. **Các điểm số không mặc định được coi là additive**: một điểm số có giới hạn không phải đại lượng tích lũy, và cộng hai điểm có thể vượt quá cực đại của chính thang đo.

| Measure ứng viên | Tính additive | Cơ sở đo được | Vì sao |
| --- | --- | --- | --- |
| `posting_count` | **additive** | Không phải cột lưu sẵn: là số dòng fact, mỗi tin đăng 1 dòng, tổng cộng 1,000,000. | Cộng đúng trên mọi dimension. Là measure an toàn nhất trong dataset. |
| `registration_fee` | **unresolved** | Biên độ 0 đến 4,999, trung bình 252.083069, 900,095 dòng bằng 0 (90.0095%) trong đó 0 nghĩa là không thu phí. | Về cấu trúc là additive - đây là số tiền và các giá trị 0 là thật. Đánh dấu unresolved vì đơn vị tiền tệ không được tài liệu hóa, nên tổng qua chín thành phố là cộng các đơn vị khác nhau. |
| `stipend` | **unresolved** | Biên độ 2,000 đến 110,428, trung bình 35,066.1992, trung vị 34,984.0, 10,000 dòng thiếu giá trị. | CHƯA GIẢI QUYẾT VỀ NGỮ NGHĨA. Cả đơn vị tiền tệ lẫn kỳ trả (tháng, năm, trọn gói) đều không được tài liệu hóa, và các dòng trải trên chín thành phố thuộc các vùng tiền tệ khác nhau. Cộng hay lấy trung bình stipend theo location sẽ cho ra một con số không bảo vệ được về mặt ý nghĩa. Không có số liệu stipend nào theo location được báo cáo ở bất kỳ đâu trong audit này. |
| `job_description_length` | **additive** | Biên độ 100 đến 5,000, trung bình 1,799.5383, 3,946 giá trị phân biệt. | Là độ dài tính theo ký tự; tổng độ dài trên một tập tin đăng là một đại lượng có thật. Trong thực tế, giá trị trung bình mới là tổng hợp hữu dụng hơn. |
| `grammatical_errors` | **additive** | Số đếm nguyên từ 0 đến 14, trung bình 2.998825. | Là số lần xuất hiện, nên tổng có ý nghĩa. |
| `vague_description_score` | **non-additive** | Điểm có giới hạn từ 0 đến 100, 101 giá trị phân biệt, trung bình 30.132072. | Một điểm số có giới hạn không phải là đại lượng tích lũy: cộng hai điểm có thể vượt quá cực đại của chính thang đo. Chỉ trung bình, trung vị và phân phối là bảo vệ được, và ngay cả thế vẫn giả định rằng quy tắc chấm điểm không được tài liệu hóa là so sánh được giữa các dòng. |
| `urgency_score` | **non-additive** | Điểm có giới hạn từ 0 đến 100, 101 giá trị phân biệt, trung bình 40.047191. | Một điểm số có giới hạn không phải là đại lượng tích lũy: cộng hai điểm có thể vượt quá cực đại của chính thang đo. Chỉ trung bình, trung vị và phân phối là bảo vệ được, và ngay cả thế vẫn giả định rằng quy tắc chấm điểm không được tài liệu hóa là so sánh được giữa các dòng. |
| `keyword_spam_score` | **non-additive** | Điểm có giới hạn từ 0 đến 100, 101 giá trị phân biệt, trung bình 25.573860. | Một điểm số có giới hạn không phải là đại lượng tích lũy: cộng hai điểm có thể vượt quá cực đại của chính thang đo. Chỉ trung bình, trung vị và phân phối là bảo vệ được, và ngay cả thế vẫn giả định rằng quy tắc chấm điểm không được tài liệu hóa là so sánh được giữa các dòng. |
| `emotional_manipulation_score` | **non-additive** | Điểm có giới hạn từ 0 đến 100, 101 giá trị phân biệt, trung bình 25.563839. | Một điểm số có giới hạn không phải là đại lượng tích lũy: cộng hai điểm có thể vượt quá cực đại của chính thang đo. Chỉ trung bình, trung vị và phân phối là bảo vệ được, và ngay cả thế vẫn giả định rằng quy tắc chấm điểm không được tài liệu hóa là so sánh được giữa các dòng. |
| `phishing_language_score` | **non-additive** | Điểm có giới hạn từ 0 đến 100, 100 giá trị phân biệt, trung bình 20.749288. | Một điểm số có giới hạn không phải là đại lượng tích lũy: cộng hai điểm có thể vượt quá cực đại của chính thang đo. Chỉ trung bình, trung vị và phân phối là bảo vệ được, và ngay cả thế vẫn giả định rằng quy tắc chấm điểm không được tài liệu hóa là so sánh được giữa các dòng. |
| `trust_signal_score` | **non-additive** | Điểm tổng hợp có giới hạn từ 0.0 đến 100.0, trung bình 56.555847, 10,000 dòng thiếu giá trị. | Vừa tổng hợp vừa có giới hạn nên không additive. Audit trước đã xác lập rằng nó không tái tạo được từ bốn cờ trust, nên cũng không thể tính lại nếu bị bỏ đi. |
| `fraud_score` | **non-additive** | Điểm tổng hợp có giới hạn từ 0.0 đến 100.0, trung bình 34.012257, 1,001 giá trị phân biệt. | Lý do giống các điểm số khác. Nó cũng gần nhưng không tất định với is_fake_posting, nên hai cái không được coi là thay thế cho nhau. |
| `recruiter_experience_years` | **non-additive** | Biên độ 0.0 đến 19.6, trung bình 5.052660. | Là một mức gắn với một con người, không phải một dòng chảy. Cộng số năm kinh nghiệm qua các tin đăng là đếm lặp cùng một nhà tuyển dụng - và vì không có định danh recruiter, không có cách nào biết lặp bao nhiêu lần. |
| `recruiter_response_time_hours` | **non-additive** | Biên độ 1.0 đến 63.9 giờ, trung bình 18.180468. | Là khoảng thời gian theo từng tin đăng; trung bình có ý nghĩa, tổng thì không. |
| `company_age` | **semi-additive** | Biên độ 1 đến 39 năm, 10,000 dòng thiếu giá trị, 39 giá trị phân biệt. | Là một đại lượng tồn kho chứ không phải dòng chảy: có thể lấy trung bình theo mọi dimension nhưng không bao giờ cộng dồn theo thời gian, đúng đặc trưng của measure semi-additive. Việc nó có nên nằm trong fact hay không phụ thuộc vào câu hỏi định danh công ty còn bỏ ngỏ. |
| `domain_age_months` | **semi-additive** | Biên độ 1 đến 500 tháng, 500 giá trị phân biệt, trung bình 239.541209. | Lý do giống company_age. |
| `is_fake_posting` | **additive** | Kết quả nhị phân; 221,958 dòng dương (22.1958% tổng số dòng). | Additive khi cộng như một bộ đếm số tin giả. Đây là kết quả đang được phân tích, nên nó được liệt kê ở đây như một measure và KHÔNG phải thuộc tính cắt lát. |
| `payment_required` | **additive** | Nhị phân 0/1; 99,905 dòng mang giá trị 1 (9.9905%). | Additive chỉ theo nghĩa hẹp rằng cộng cờ lại chính là đếm số dòng có cờ bật. Việc lưu nó như bộ đếm trong fact hay như thuộc tính dimension là quyết định schema còn để ngỏ. |
| `fake_certificate_offer` | **additive** | Nhị phân 0/1; 79,830 dòng mang giá trị 1 (7.9830%). | Additive chỉ theo nghĩa hẹp rằng cộng cờ lại chính là đếm số dòng có cờ bật. Việc lưu nó như bộ đếm trong fact hay như thuộc tính dimension là quyết định schema còn để ngỏ. |
| `suspicious_email_domain` | **additive** | Nhị phân 0/1; 250,567 dòng mang giá trị 1 (25.0567%). | Additive chỉ theo nghĩa hẹp rằng cộng cờ lại chính là đếm số dòng có cờ bật. Việc lưu nó như bộ đếm trong fact hay như thuộc tính dimension là quyết định schema còn để ngỏ. |
| `linkedin_presence` | **additive** | Nhị phân 0/1; 800,764 dòng mang giá trị 1 (80.0764%). | Additive chỉ theo nghĩa hẹp rằng cộng cờ lại chính là đếm số dòng có cờ bật. Việc lưu nó như bộ đếm trong fact hay như thuộc tính dimension là quyết định schema còn để ngỏ. |
| `website_available` | **additive** | Nhị phân 0/1; 849,597 dòng mang giá trị 1 (84.9597%). | Additive chỉ theo nghĩa hẹp rằng cộng cờ lại chính là đếm số dòng có cờ bật. Việc lưu nó như bộ đếm trong fact hay như thuộc tính dimension là quyết định schema còn để ngỏ. |
| `verification_status` | **additive** | Nhị phân 0/1; 699,713 dòng mang giá trị 1 (69.9713%). | Additive chỉ theo nghĩa hẹp rằng cộng cờ lại chính là đếm số dòng có cờ bật. Việc lưu nó như bộ đếm trong fact hay như thuộc tính dimension là quyết định schema còn để ngỏ. |
| `social_media_presence` | **additive** | Nhị phân 0/1; 749,800 dòng mang giá trị 1 (74.9800%). | Additive chỉ theo nghĩa hẹp rằng cộng cờ lại chính là đếm số dòng có cờ bật. Việc lưu nó như bộ đếm trong fact hay như thuộc tính dimension là quyết định schema còn để ngỏ. |
| `unrealistic_salary_flag` | **non-additive** | Hằng số: 1 giá trị phân biệt trên 1,000,000 dòng, tổng 0. | Tổng của nó bằng 0 theo cấu tạo trong bản trích này, nên việc tổng hợp không mang thông tin nào. Nó không bị xóa và cũng không được dựa vào. |

> **`stipend` vẫn chưa được giải quyết về ngữ nghĩa.** Nó được liệt kê như measure ứng viên vì nó là số, nhưng cả đơn vị tiền tệ lẫn kỳ trả (tháng, năm hay trọn gói) đều không được tài liệu hóa, nên không rõ nó đo cái gì. Chừng nào điều đó chưa được làm rõ, không phép tổng hợp nào của `stipend` - và đặc biệt là không phép so sánh nào theo `location` - bảo vệ được.

## 8. Bằng chứng về grain

Mệnh đề được kiểm chứng là: **một dòng đại diện cho một tin tuyển thực tập.** Nó được đánh giá, chứ không được chấp nhận sẵn.

**Bằng chứng ủng hộ grain này**

| Bằng chứng | Giá trị |
| --- | ---: |
| Số dòng trong staging | 1,000,000 |
| Số dòng trùng lặp hoàn toàn (cả 34 thuộc tính nghiệp vụ) | 0 |
| Số giá trị source_row_id phân biệt | 1,000,000 |
| source_row_id liên tục 1..N | có |
| Mọi dòng đều có posting_date, title, company_name và location | có |

Không có hai dòng nào giống hệt nhau trên toàn bộ thuộc tính nghiệp vụ (0 bản trùng tuyệt đối), nên không dòng nào là bản sao thừa của dòng khác, và mọi dòng đều mang đủ bộ thuộc tính mô tả một tin đăng. Không phép đo nào trong audit này mâu thuẫn với grain mức tin đăng.

**Không có ID tin đăng tự nhiên**

| Tổ hợp được kiểm | Số thuộc tính | Số tổ hợp phân biệt | Số dòng trùng | % số dòng | Là khóa duy nhất |
| --- | ---: | ---: | ---: | ---: | :---: |
| `company_name + posting_date` | 2 | 990,918 | 9,082 | 0.9082 | không |
| `company_name + posting_date + internship_title` | 3 | 998,936 | 1,064 | 0.1064 | không |
| `company_name + posting_date + internship_title + location` | 4 | 999,869 | 131 | 0.0131 | không |
| `company_name + posting_date + internship_title + location + industry + employment_type + work_mode` | 7 | 999,999 | 1 | 0.0001 | không |

**Dataset này không có định danh tin đăng tự nhiên, và không tổ hợp thuộc tính nghiệp vụ nào là duy nhất.** Ngay cả tổ hợp rộng nhất được kiểm (`company_name + posting_date + internship_title + location + industry + employment_type + work_mode`) vẫn tạo ra trùng lặp: 1 trên 1,000,000 dòng (0.0001%). Do đó không thể định vị một dòng chỉ bằng nội dung nghiệp vụ của nó.

**Vai trò của `source_row_id`**

`source_row_id` chỉ là một **handle truy vết nguồn gốc** sinh ra ở staging. Nó là vị trí của dòng trong bản trích gốc, chỉ có nghĩa khi đi kèm sha256 của file đó. Nó không phải business key, không phải ID tin đăng, và không phải một thứ tự có ý nghĩa phân tích; cùng một giá trị ở một bản trích khác trỏ tới một tin đăng khác. Do đó nó hỗ trợ truy vết ngược về nguồn, nhưng không thể dùng để quyết định hai dòng có mô tả cùng một tin đăng hay không, và không được tái sử dụng làm surrogate key trong warehouse nếu quyết định đó chưa được nêu rõ ràng.

**Những băn khoăn chưa giải quyết**

1. Không có ID tin đăng thì "một dòng = một tin đăng" không thể được *chứng minh*; chỉ có thể cho thấy nó không bị bác bỏ. Hai tin đăng thực sự khác nhau và một tin đăng bị nạp hai lần sẽ trông giống hệt nhau dưới mọi phép thử khả dụng ở đây.
2. Các dòng va chạm trên một tổ hợp nghiệp vụ là nơi điều này quan trọng nhất: tổ hợp hẹp nhất được kiểm để lại 9,082 dòng như vậy và tổ hợp rộng nhất để lại 1. Dữ liệu không thể nói cách đọc nào là đúng.
3. Vấn đề định danh công ty ở mục 3 nằm bên dưới chuyện này: nếu `company_name` không định danh một công ty thì "cùng một công ty đăng tin hai lần" không phải một sự kiện quan sát được trong dataset này.
4. Do đó grain **không được chốt ở đây.** Nó được ghi nhận là hợp lý và chưa bị bác bỏ, chờ các câu hỏi ở mục 11.

## 9. Rủi ro khi mô hình hóa

| Rủi ro | Bằng chứng | Hệ quả |
| --- | --- | --- |
| Định danh công ty | 62,274 trên 63,946 company_name lặp lại mang nhiều hơn một tổ hợp thuộc tính | Một DimCompany khóa theo company_name sẽ âm thầm gộp các dòng có thể thuộc về những công ty khác nhau, hoặc chẻ một công ty thành nhiều phiên bản. Mọi con số ở mức công ty sẽ thừa hưởng sự mơ hồ đó. |
| Cardinality của dimension | 535,938 giá trị company_name phân biệt trên 1,000,000 dòng | Một dimension chứa số dòng xấp xỉ một nửa bảng fact sẽ đánh mất phần lớn lợi ích về lưu trữ và join của star schema. |
| Hành vi thời gian không đơn điệu | company_age giảm ở 222,140 cặp; domain_age_months giảm ở 229,908 | SCD Type 2 giả định rằng thay đổi thuộc tính là một lịch sử. Ở đây các thay đổi không tạo thành lịch sử, nên version hóa chúng sẽ mã hóa nhiễu thành sự thật. |
| Cặp thuộc tính dư thừa | song ánh recruiter_email_type <-> suspicious_email_domain; payment_required == (registration_fee > 0) | Lưu cả hai thành viên của một cặp khiến hai đường truy vấn cho ra cùng một con số theo hai lối khác nhau, và khiến một lần nạp dữ liệu sau này có thể phá vỡ bất biến mà không truy vấn nào nhận ra. |
| Đơn vị không được tài liệu hóa | stipend không có đơn vị tiền tệ hay kỳ trả được tài liệu hóa; registration_fee không có đơn vị tiền tệ được tài liệu hóa | Mọi tổng hợp tiền tệ qua chín thành phố là cộng các đơn vị khác nhau. Kết quả trình bày được nhưng sai, và đó là sự kết hợp nguy hiểm. |
| Rò rỉ biến kết quả | is_fake_posting và fraud_score là mục tiêu phân tích, không phải các mô tả độc lập | Đặt bất kỳ cái nào trong một dimension cắt lát sẽ dẫn tới các phân tích giải thích kết quả bằng chính nó. |
| Thuộc tính suy biến | unrealistic_salary_flag là hằng số trên toàn bộ 1,000,000 dòng | Nó sẽ tạo ra một dimension chỉ có một phần tử, không bao giờ cắt lát được gì mà vẫn tốn một phép join. |
| Ngữ nghĩa của location | location là một trong 9 thành phố, không có cột quốc gia hay khu vực, và nguồn không nói nó định vị cái gì | Không thể xây phân cấp địa lý chỉ từ dataset này, và mọi phân cấp nhập từ ngoài đều kéo theo một giả định. |

## 10. Các quyết định được hoãn lại

Mọi mục dưới đây đều được audit này cố ý để ngỏ. Mỗi mục là một quyết định thuộc giai đoạn star schema, và mỗi mục cần một giả định được nêu rõ chứ không phải thêm phép đo trên bản trích này.

| # | Quyết định được hoãn | Vì sao hoãn |
| ---: | --- | --- |
| 1 | Có tồn tại DimCompany hay không, và khóa theo cái gì | Chỉ 2.6147% company_name lặp lại mang một tổ hợp thuộc tính duy nhất; dữ liệu không phân biệt được một công ty đang thay đổi với hai công ty trùng tên. |
| 2 | Thuộc tính công ty có cần xử lý SCD hay không, và loại nào | SCD giả định có một business key ổn định, điều chưa được xác lập. |
| 3 | industry có gia nhập dimension Internship hay đứng riêng | Không có functional dependency theo chiều nào; Cramer's V 0.001236. |
| 4 | employment_type và work_mode thành một dimension hay hai | Cả hai đều bảo vệ được: lưới là đầy đủ và không cái nào quyết định cái kia. |
| 5 | Lưu cột nào trong recruiter_email_type / suspicious_email_domain | Song ánh khiến chúng dư thừa, nhưng chúng không thay thế được cho nhau về ý nghĩa và một bản trích sau có thể phá vỡ nó. |
| 6 | payment_required được lưu, được dẫn xuất, hay cả hai | Bất biến đúng trên cả 1,000,000 dòng, nên hiện tại lựa chọn nào cũng không mất thông tin. |
| 7 | registration_fee là measure trong fact hay thuộc tính dimension | Nó là số và về hình thức là additive, nhưng đơn vị tiền tệ không được tài liệu hóa. |
| 8 | stipend có dùng được hay không | Cả đơn vị tiền tệ lẫn kỳ trả đều không được tài liệu hóa; không phép tổng hợp nào bảo vệ được cho tới khi hai điều đó được xác lập. |
| 9 | Các cờ trust và fraud có trở thành junk dimension hay không | Khả thi về kỹ thuật với số tổ hợp quan sát được, nhưng is_fake_posting là biến kết quả và unrealistic_salary_flag là hằng số. |
| 10 | unrealistic_salary_flag có vào warehouse hay không | Hằng số trên bản trích này, nhưng bản trích sau có thể chứa giá trị 1; cleaning rules giữ nó trong staging vì lý do đó. |
| 11 | Các trường điểm số giữ nguyên dạng số hay còn được chia dải | Chia dải tạo ra thuộc tính dimension nhưng áp đặt các ngưỡng mà nguồn không tài liệu hóa. |
| 12 | Phát biểu grain cuối cùng và surrogate key của nó | Grain mức tin đăng chưa bị bác bỏ nhưng không chứng minh được nếu không có ID tin đăng; source_row_id chỉ dùng để truy vết nguồn. |
| 13 | Các dòng is_future_posting có được đưa vào truy vấn phân tích hay không | 30,246 dòng có ngày sau ngày tham chiếu cố định và chỉ được đánh cờ, không bị lọc. |

## 11. Các câu hỏi cần giải quyết trước khi thiết kế star schema cuối cùng

Những câu hỏi này không thể trả lời bằng cách đo thêm bản trích hiện có. Chúng cần hệ thống nguồn, tài liệu của nó, hoặc một giả định mô hình hóa được thống nhất và ghi lại rõ ràng.

| # | Câu hỏi | Nó mở khóa điều gì |
| ---: | --- | --- |
| 1 | Trong hệ thống nguồn có định danh công ty nào mà bản trích này không giữ lại không? | Toàn bộ vấn đề về DimCompany: sự tồn tại, khóa, grain và việc có áp dụng SCD hay không. |
| 2 | Nếu không, có được phép coi company_name là khóa công ty theo một giả định nêu rõ, và giả định đó có được chấp nhận trong bài tập không? | Một DimCompany bảo vệ được, dựa trên một giả định được nêu rõ thay vì dựa trên bằng chứng mà dữ liệu không có. |
| 3 | stipend được tính bằng đơn vị tiền tệ nào, và theo kỳ trả nào? | Mọi cách sử dụng stipend, và đặc biệt là mọi so sánh theo location. |
| 4 | registration_fee được tính bằng đơn vị tiền tệ nào? | Việc registration_fee có được cộng qua các location như một measure trong fact hay không. |
| 5 | location chỉ nơi làm việc, địa chỉ công ty hay vị trí nhà tuyển dụng? | Việc DimLocation có thể conform với dimension khác hay không, và có được nhập một phân cấp địa lý hay không. |
| 6 | Bảy điểm số 0-100 được tính thế nào, và thang đo có so sánh được giữa các dòng và theo thời gian không? | Việc lấy trung bình chúng có bảo vệ được không, và việc chia dải chúng thành thuộc tính dimension có chính đáng không. |
| 7 | Hệ thống nguồn có định danh nhà tuyển dụng không? | Việc DimRecruiter có thể chứa recruiter_experience_years và recruiter_response_time_hours thay vì để chúng trong fact hay không. |
| 8 | Hệ thống nguồn có định danh tin đăng không? | Một phát biểu grain chứng minh được và một khóa có ý nghĩa nghiệp vụ cho bảng fact. |
| 9 | Vì sao company_age lại giảm ở các tin đăng sau của cùng một company_name? | Việc thuộc tính công ty có phải một lịch sử thật đáng version hóa hay chỉ là nhiễu không được phép version hóa. |
| 10 | Song ánh giữa recruiter_email_type và suspicious_email_domain được nguồn bảo đảm, hay chỉ là ngẫu nhiên của bản trích này? | Việc có thể an toàn bỏ một trong hai khỏi mô hình hay không. |
| 11 | Nguồn có bảo đảm payment_required luôn bằng registration_fee > 0, hay đó chỉ là ngẫu nhiên của bản trích này? | Việc có thể dẫn xuất cờ thay vì lưu nó hay không. |
| 12 | unrealistic_salary_flag có bao giờ khác 0 ở một bản trích tương lai không? | Việc nó là một cột suy biến cần loại bỏ hay một cờ thật cần giữ lại. |
| 13 | Các tin đăng ngày tương lai nên được đưa vào, loại ra, hay báo cáo riêng trong truy vấn phân tích? | Cách giới hạn dimension ngày và cách đọc mọi con số theo chuỗi thời gian. |

---

*Được tạo bởi `scripts/audit_dimensional_consistency.py` lúc 2026-09-23 18:17:28 từ 1,000,000 dòng staging. sha256 của staging không đổi: có. Không dữ liệu nào bị thay đổi.*
