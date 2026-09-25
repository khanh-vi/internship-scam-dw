# Star Schema v1 — trình bày từ DBML

> Tệp này được sinh tự động bởi `scripts/dbml_to_md.py` từ [`star_schema.dbml`](star_schema.dbml). Không sửa tay: hãy sửa `star_schema.mmd` rồi chạy lại hai script ở mục *Tái tạo tài liệu* cuối trang.

| Mục | Giá trị |
| --- | --- |
| Project DBML | `internship_scam_dw` |
| Hệ quản trị đích | SQL Server |
| Mô tả | Star Schema v1 - internship postings and internship scam analysis |
| Nguồn gốc | `star_schema.mmd` → `star_schema.dbml` → tài liệu này |
| Số bảng | 10 (1 Fact, 9 Dimension) |
| Số quan hệ | 9 |
| Tài liệu thiết kế đầy đủ | [star_schema_design_vi.md](star_schema_design_vi.md) |

## 1. Sơ đồ

![Star Schema v1](star_schema.svg)

Cách đọc sơ đồ:

- Header **đỏ** là bảng Fact, header **xanh** là bảng Dimension.
- Cột in **đậm** là khóa chính (PK).
- Mỗi đường nối đi từ cột khóa ngoại (FK) trong Fact tới PK của Dimension; đầu `*` là phía nhiều (Fact), đầu `1` là phía một (Dimension).
- Sơ đồ được vẽ bằng `@softwaretechnik/dbml-renderer`. Có thể dán nội dung [`star_schema.dbml`](star_schema.dbml) vào <https://dbdiagram.io> để xem và kéo thả tương tác.

## 2. Tổng quan các bảng

| Bảng | Loại | Khóa chính | Số cột | Liên kết |
| --- | --- | --- | --- | --- |
| [FactInternshipPosting](#factinternshipposting) | Fact | `FactPostingKey` | 30 | 9 FK → DimCompanyName, DimCompanyProfile, DimDate, DimEmploymentType, DimIndustry, DimInternshipTitle, DimLocation, DimRecruiterEmail, DimWorkMode |
| [DimDate](#dimdate) | Dimension | `DateKey` | 9 | `FactInternshipPosting.DateKey` |
| [DimCompanyName](#dimcompanyname) | Dimension | `CompanyNameKey` | 2 | `FactInternshipPosting.CompanyNameKey` |
| [DimCompanyProfile](#dimcompanyprofile) | Dimension | `CompanyProfileKey` | 6 | `FactInternshipPosting.CompanyProfileKey` |
| [DimInternshipTitle](#diminternshiptitle) | Dimension | `InternshipTitleKey` | 2 | `FactInternshipPosting.InternshipTitleKey` |
| [DimIndustry](#dimindustry) | Dimension | `IndustryKey` | 2 | `FactInternshipPosting.IndustryKey` |
| [DimLocation](#dimlocation) | Dimension | `LocationKey` | 2 | `FactInternshipPosting.LocationKey` |
| [DimEmploymentType](#dimemploymenttype) | Dimension | `EmploymentTypeKey` | 2 | `FactInternshipPosting.EmploymentTypeKey` |
| [DimWorkMode](#dimworkmode) | Dimension | `WorkModeKey` | 2 | `FactInternshipPosting.WorkModeKey` |
| [DimRecruiterEmail](#dimrecruiteremail) | Dimension | `RecruiterEmailKey` | 3 | `FactInternshipPosting.RecruiterEmailKey` |

## 3. Quan hệ

| # | Phía nhiều (FK) | Phía một (PK) | Bản số |
| --- | --- | --- | --- |
| 1 | `FactInternshipPosting.DateKey` | `DimDate.DateKey` | N : 1 |
| 2 | `FactInternshipPosting.CompanyNameKey` | `DimCompanyName.CompanyNameKey` | N : 1 |
| 3 | `FactInternshipPosting.CompanyProfileKey` | `DimCompanyProfile.CompanyProfileKey` | N : 1 |
| 4 | `FactInternshipPosting.InternshipTitleKey` | `DimInternshipTitle.InternshipTitleKey` | N : 1 |
| 5 | `FactInternshipPosting.IndustryKey` | `DimIndustry.IndustryKey` | N : 1 |
| 6 | `FactInternshipPosting.LocationKey` | `DimLocation.LocationKey` | N : 1 |
| 7 | `FactInternshipPosting.EmploymentTypeKey` | `DimEmploymentType.EmploymentTypeKey` | N : 1 |
| 8 | `FactInternshipPosting.WorkModeKey` | `DimWorkMode.WorkModeKey` | N : 1 |
| 9 | `FactInternshipPosting.RecruiterEmailKey` | `DimRecruiterEmail.RecruiterEmailKey` | N : 1 |

Mọi quan hệ đều là N : 1 từ Fact tới Dimension, và không Dimension nào nối với Dimension khác — đúng dạng star schema (không snowflake).

## 4. Bảng Fact: FactInternshipPosting

<a id="factinternshipposting"></a>

### 4.1 Khóa (10 cột)

| Cột | Kiểu | Vai trò | Tham chiếu |
| --- | --- | --- | --- |
| `FactPostingKey` | `bigint` | PK | — |
| `DateKey` | `int` | FK | `DimDate.DateKey` |
| `CompanyNameKey` | `int` | FK | `DimCompanyName.CompanyNameKey` |
| `CompanyProfileKey` | `int` | FK | `DimCompanyProfile.CompanyProfileKey` |
| `InternshipTitleKey` | `int` | FK | `DimInternshipTitle.InternshipTitleKey` |
| `IndustryKey` | `int` | FK | `DimIndustry.IndustryKey` |
| `LocationKey` | `int` | FK | `DimLocation.LocationKey` |
| `EmploymentTypeKey` | `int` | FK | `DimEmploymentType.EmploymentTypeKey` |
| `WorkModeKey` | `int` | FK | `DimWorkMode.WorkModeKey` |
| `RecruiterEmailKey` | `int` | FK | `DimRecruiterEmail.RecruiterEmailKey` |

### 4.2 Measure và thuộc tính khác (20 cột)

Phân loại theo ghi chú trong DBML: 2 không phải measure, 5 cộng được, 2 bán cộng, 2 chưa xác định, 9 không cộng.

| Cột | Kiểu | Tính cộng | Cho phép NULL | Ghi chú (nguyên văn DBML) |
| --- | --- | --- | --- | --- |
| `SourceRowID` | `int` | Không phải measure |  | lineage only |
| `IsFuturePosting` | `tinyint` | Không phải measure |  | data quality |
| `FakePostingCount` | `tinyint` | Cộng được |  | outcome 0-1 additive |
| `PaymentRequired` | `tinyint` | Cộng được |  | additive |
| `FakeCertificateOffer` | `tinyint` | Cộng được |  | additive |
| `CompanyAge` | `smallint` | Bán cộng | Có | nullable semi-additive |
| `DomainAgeMonths` | `smallint` | Bán cộng |  | semi-additive |
| `Stipend` | `int` | Chưa xác định | Có | nullable UNRESOLVED |
| `RegistrationFee` | `int` | Chưa xác định |  | currency unresolved |
| `JobDescriptionLength` | `smallint` | Cộng được |  | additive |
| `GrammaticalErrors` | `tinyint` | Cộng được |  | additive |
| `VagueDescriptionScore` | `tinyint` | Không cộng |  | non-additive |
| `UrgencyScore` | `tinyint` | Không cộng |  | non-additive |
| `KeywordSpamScore` | `tinyint` | Không cộng |  | non-additive |
| `EmotionalManipulationScore` | `tinyint` | Không cộng |  | non-additive |
| `PhishingLanguageScore` | `tinyint` | Không cộng |  | non-additive |
| `TrustSignalScore` | `decimal` | Không cộng | Có | nullable non-additive |
| `FraudScore` | `decimal` | Không cộng |  | non-additive |
| `RecruiterExperienceYears` | `decimal` | Không cộng |  | non-additive |
| `RecruiterResponseTimeHours` | `decimal` | Không cộng |  | non-additive |

Ý nghĩa cột *Tính cộng*: **Cộng được** — có thể `SUM` theo mọi Dimension; **Bán cộng** — không nên `SUM` dọc theo một số chiều (ví dụ tuổi); **Không cộng** — chỉ dùng `AVG`/`MIN`/`MAX`/phân phối, không `SUM`; **Chưa xác định** — ngữ nghĩa (đơn vị, tiền tệ) chưa được xác lập, chưa nên tổng hợp; **Không phải measure** — cột lineage hoặc cờ chất lượng dữ liệu.

## 5. Các bảng Dimension

### 5.1 DimDate

<a id="dimdate"></a>

Được tham chiếu bởi: `FactInternshipPosting.DateKey`.

| Cột | Kiểu | Khóa | Ghi chú |
| --- | --- | --- | --- |
| `DateKey` | `int` | PK | YYYYMMDD |
| `FullDate` | `date` |  |  |
| `Day` | `tinyint` |  |  |
| `DayOfWeek` | `tinyint` |  |  |
| `DayName` | `varchar` |  |  |
| `Month` | `tinyint` |  |  |
| `MonthName` | `varchar` |  |  |
| `Quarter` | `tinyint` |  |  |
| `Year` | `smallint` |  |  |

### 5.2 DimCompanyName

<a id="dimcompanyname"></a>

Được tham chiếu bởi: `FactInternshipPosting.CompanyNameKey`.

| Cột | Kiểu | Khóa | Ghi chú |
| --- | --- | --- | --- |
| `CompanyNameKey` | `int` | PK |  |
| `CompanyName` | `varchar` |  | name observed on a posting |

### 5.3 DimCompanyProfile

<a id="dimcompanyprofile"></a>

Được tham chiếu bởi: `FactInternshipPosting.CompanyProfileKey`.

| Cột | Kiểu | Khóa | Ghi chú |
| --- | --- | --- | --- |
| `CompanyProfileKey` | `int` | PK |  |
| `CompanySize` | `varchar` |  | nominal not ordinal |
| `LinkedInPresence` | `tinyint` |  |  |
| `WebsiteAvailable` | `tinyint` |  |  |
| `VerificationStatus` | `tinyint` |  |  |
| `SocialMediaPresence` | `tinyint` |  |  |

### 5.4 DimInternshipTitle

<a id="diminternshiptitle"></a>

Được tham chiếu bởi: `FactInternshipPosting.InternshipTitleKey`.

| Cột | Kiểu | Khóa | Ghi chú |
| --- | --- | --- | --- |
| `InternshipTitleKey` | `int` | PK |  |
| `InternshipTitle` | `varchar` |  |  |

### 5.5 DimIndustry

<a id="dimindustry"></a>

Được tham chiếu bởi: `FactInternshipPosting.IndustryKey`.

| Cột | Kiểu | Khóa | Ghi chú |
| --- | --- | --- | --- |
| `IndustryKey` | `int` | PK |  |
| `Industry` | `varchar` |  |  |

### 5.6 DimLocation

<a id="dimlocation"></a>

Được tham chiếu bởi: `FactInternshipPosting.LocationKey`.

| Cột | Kiểu | Khóa | Ghi chú |
| --- | --- | --- | --- |
| `LocationKey` | `int` | PK |  |
| `Location` | `varchar` |  | no hierarchy in source |

### 5.7 DimEmploymentType

<a id="dimemploymenttype"></a>

Được tham chiếu bởi: `FactInternshipPosting.EmploymentTypeKey`.

| Cột | Kiểu | Khóa | Ghi chú |
| --- | --- | --- | --- |
| `EmploymentTypeKey` | `int` | PK |  |
| `EmploymentType` | `varchar` |  |  |

### 5.8 DimWorkMode

<a id="dimworkmode"></a>

Được tham chiếu bởi: `FactInternshipPosting.WorkModeKey`.

| Cột | Kiểu | Khóa | Ghi chú |
| --- | --- | --- | --- |
| `WorkModeKey` | `int` | PK |  |
| `WorkMode` | `varchar` |  |  |

### 5.9 DimRecruiterEmail

<a id="dimrecruiteremail"></a>

Được tham chiếu bởi: `FactInternshipPosting.RecruiterEmailKey`.

| Cột | Kiểu | Khóa | Ghi chú |
| --- | --- | --- | --- |
| `RecruiterEmailKey` | `int` | PK |  |
| `RecruiterEmailType` | `varchar` |  |  |
| `SuspiciousEmailDomain` | `tinyint` |  |  |

## 6. Mã nguồn DBML

```dbml
// Generated by scripts/mmd_to_dbml.py from docs/schema/star_schema.mmd.
// Do not edit by hand: change the .mmd file and re-run the script.

Project internship_scam_dw {
  database_type: 'SQL Server'
  Note: 'Star Schema v1 - internship postings and internship scam analysis'
}

Table FactInternshipPosting [headercolor: #C0392B] {
  FactPostingKey             bigint   [pk]
  DateKey                    int
  CompanyNameKey             int
  CompanyProfileKey          int
  InternshipTitleKey         int
  IndustryKey                int
  LocationKey                int
  EmploymentTypeKey          int
  WorkModeKey                int
  RecruiterEmailKey          int
  SourceRowID                int      [note: 'lineage only']
  IsFuturePosting            tinyint  [note: 'data quality']
  FakePostingCount           tinyint  [note: 'outcome 0-1 additive']
  PaymentRequired            tinyint  [note: 'additive']
  FakeCertificateOffer       tinyint  [note: 'additive']
  CompanyAge                 smallint [note: 'nullable semi-additive']
  DomainAgeMonths            smallint [note: 'semi-additive']
  Stipend                    int      [note: 'nullable UNRESOLVED']
  RegistrationFee            int      [note: 'currency unresolved']
  JobDescriptionLength       smallint [note: 'additive']
  GrammaticalErrors          tinyint  [note: 'additive']
  VagueDescriptionScore      tinyint  [note: 'non-additive']
  UrgencyScore               tinyint  [note: 'non-additive']
  KeywordSpamScore           tinyint  [note: 'non-additive']
  EmotionalManipulationScore tinyint  [note: 'non-additive']
  PhishingLanguageScore      tinyint  [note: 'non-additive']
  TrustSignalScore           decimal  [note: 'nullable non-additive']
  FraudScore                 decimal  [note: 'non-additive']
  RecruiterExperienceYears   decimal  [note: 'non-additive']
  RecruiterResponseTimeHours decimal  [note: 'non-additive']
}

Table DimDate [headercolor: #2E86C1] {
  DateKey   int      [pk, note: 'YYYYMMDD']
  FullDate  date
  Day       tinyint
  DayOfWeek tinyint
  DayName   varchar
  Month     tinyint
  MonthName varchar
  Quarter   tinyint
  Year      smallint
}

Table DimCompanyName [headercolor: #2E86C1] {
  CompanyNameKey int     [pk]
  CompanyName    varchar [note: 'name observed on a posting']
}

Table DimCompanyProfile [headercolor: #2E86C1] {
  CompanyProfileKey   int     [pk]
  CompanySize         varchar [note: 'nominal not ordinal']
  LinkedInPresence    tinyint
  WebsiteAvailable    tinyint
  VerificationStatus  tinyint
  SocialMediaPresence tinyint
}

Table DimInternshipTitle [headercolor: #2E86C1] {
  InternshipTitleKey int     [pk]
  InternshipTitle    varchar
}

Table DimIndustry [headercolor: #2E86C1] {
  IndustryKey int     [pk]
  Industry    varchar
}

Table DimLocation [headercolor: #2E86C1] {
  LocationKey int     [pk]
  Location    varchar [note: 'no hierarchy in source']
}

Table DimEmploymentType [headercolor: #2E86C1] {
  EmploymentTypeKey int     [pk]
  EmploymentType    varchar
}

Table DimWorkMode [headercolor: #2E86C1] {
  WorkModeKey int     [pk]
  WorkMode    varchar
}

Table DimRecruiterEmail [headercolor: #2E86C1] {
  RecruiterEmailKey     int     [pk]
  RecruiterEmailType    varchar
  SuspiciousEmailDomain tinyint
}

// Relationships: Fact (many) -> Dimension (one).
// `A.x > B.y` and `B.y < A.x` mean the same; they alternate for layout.
Ref: FactInternshipPosting.DateKey > DimDate.DateKey
Ref: DimCompanyName.CompanyNameKey < FactInternshipPosting.CompanyNameKey
Ref: FactInternshipPosting.CompanyProfileKey > DimCompanyProfile.CompanyProfileKey
Ref: DimInternshipTitle.InternshipTitleKey < FactInternshipPosting.InternshipTitleKey
Ref: FactInternshipPosting.IndustryKey > DimIndustry.IndustryKey
Ref: DimLocation.LocationKey < FactInternshipPosting.LocationKey
Ref: FactInternshipPosting.EmploymentTypeKey > DimEmploymentType.EmploymentTypeKey
Ref: DimWorkMode.WorkModeKey < FactInternshipPosting.WorkModeKey
Ref: FactInternshipPosting.RecruiterEmailKey > DimRecruiterEmail.RecruiterEmailKey
```

## 7. Tái tạo tài liệu

```bash
python scripts/mmd_to_dbml.py   # star_schema.mmd -> star_schema.dbml + star_schema.svg
python scripts/dbml_to_md.py    # star_schema.dbml -> star_schema_dbml_vi.md
```

Bước vẽ SVG cần Node.js (`npx`); lần chạy đầu sẽ tải `@softwaretechnik/dbml-renderer`. Dùng `python scripts/mmd_to_dbml.py --no-svg` nếu chỉ cần tệp DBML.
