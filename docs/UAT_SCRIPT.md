# PALP UAT Script

> **Phien ban**: 2.0
> **Moi truong**: Staging (staging.palp.dau.edu.vn)
> **Thoi luong du kien**: 2 vong, moi vong 2 buoi (SV 60 phut + GV 45 phut)
> **Lien he ky thuat**: Dev team (co mat tai phong UAT)
> **Nguong chat luong**: Tieu chuan cao -- SUS >= 80, zero tolerance P0/P1

---

## 1. Tong Quan

### 1.1 Muc dich

UAT (User Acceptance Testing) nham xac nhan PALP hoat dong dung voi nguoi dung thuc truoc khi trien khai pilot. Ket qua UAT la co so de quyet dinh Go/No-go cho pilot 10 tuan.

PALP la san pham EdTech tac dong truc tiep den quyet dinh hoc tap va can thiep su pham. Tieu chuan UAT duoc dat **cao hon muc thong thuong** vi sai sot co the dan den: SV nhan can thiep sai, GV mat niem tin vao he thong, hoac tien trinh hoc tap bi bop meo.

### 1.2 Muc tieu UAT

5 muc tieu dinh tinh duoi day la kim chi nam cho toan bo quy trinh UAT. Moi muc tieu duoc do luong bang cac metric cu the va kiem chung qua cac task tuong ung.

| # | Muc tieu | Metric do luong | Tasks kiem chung |
|---|---------|-----------------|------------------|
| G1 | SV hieu onboarding -- tu dang nhap, consent, den bat dau hoc tap ma khong can ho tro | Onboarding stuck rate < 10%; Task success rate S1+S2 >= 90% | S1, S2 |
| G2 | SV chap nhan adaptive intervention -- hieu vi sao he thong goi y noi dung bo tro va khong cam thay bi ep buoc | SV understanding score >= 4/5 | S5, PALP-SV-01 |
| G3 | SV khong thay progress "gia" -- tien trinh phan anh dung nang luc thuc te, khong tang ao | SV progress trust score >= 4/5 | S6, S8, PALP-SV-02 |
| G4 | GV hieu dashboard va tin duoc canh bao -- phan loai severity chinh xac, ly do ro rang | GV alert trust score >= 4/5; Alert usefulness > 80% | L2, L3, L4, PALP-GV-01 |
| G5 | GV thuc hien duoc hanh dong can thiep ma khong can dao tao sau -- flow intervention truc quan | GV intervention ease score >= 4/5; Task success L5 >= 90% | L5, L6, PALP-GV-02 |

### 1.3 Thanh phan tham gia

| Vai tro | So luong | Tieu chi chon |
|---------|---------|---------------|
| Sinh vien (SV) | 20-30 | Da dang: nam 1 + nam cuoi, gioi/kha/trung binh |
| Giang vien (GV) | 2-3 | GV day SBVL, co su dung cong nghe |
| Observer | 1-2 | Dev/QA ghi nhan hanh vi va loi |

### 1.4 Cau truc 2 vong

UAT duoc tien hanh qua **2 vong** voi cung nhom nguoi dung. Vong 2 do luong su cai thien time-on-task de xac nhan he thong co learnability tot.

| Thoi gian | Noi dung | Muc dich |
|-----------|---------|---------|
| **Vong 1 -- Ngay 1** | | |
| Buoi sang (60 phut) | SV: S1-S8 + Feedback | Do baseline task success + time-on-task |
| Buoi chieu (45 phut) | GV: L1-L7 + Feedback | Do baseline GV metrics |
| Ngay 2 | Tong hop bugs vong 1, fix P0 | Dev team xu ly |
| Ngay 3 | Fix P0 hoan tat, staging cap nhat | QA verify |
| **Vong 2 -- Ngay 4** | | |
| Buoi sang (45 phut) | SV: S1-S8 (cung tasks) | Do time-on-task regression (phai giam) |
| Buoi chieu (30 phut) | GV: L1-L7 (cung tasks) | Verify fix + do improvement |
| Sau 24h | Final report + Go/No-go | PO + Tech Lead quyet dinh |

**Luu y**: Vong 2 su dung **cung nhom SV/GV** va **cung tasks** de so sanh duoc. Tai khoan va du lieu duoc reset giua 2 vong.

---

## 2. Dieu Kien Tien Quyet

Truoc khi bat dau UAT, xac nhan tat ca dieu kien sau:

| # | Dieu kien | Responsible | Status |
|---|----------|-------------|--------|
| PRE-01 | Tat ca P0/P1 test cases da pass trong CI | QA | [ ] |
| PRE-02 | 20-30 tai khoan SV + 2-3 tai khoan GV da tao | Dev | [ ] |
| PRE-03 | Consent flow hoat dong, wording da duoc GV/PO duyet | PO | [ ] |
| PRE-04 | Seed data cho course SBVL da load (10 concepts, 50+ tasks) | Dev | [ ] |
| PRE-05 | Assessment 15-20 cau da co noi dung (GV da review) | GV + PO | [ ] |
| PRE-06 | Staging environment on dinh, khop production config | DevOps | [ ] |
| PRE-07 | Sentry + health monitoring hoat dong | Dev | [ ] |
| PRE-08 | Wifi phong UAT on dinh, moi nguoi co laptop/may tinh | Logistics | [ ] |
| PRE-09 | Form khao sat PALP-specific da in/chuan bi (Phu luc A) | QA | [ ] |
| PRE-10 | Observer sheet da in, dong ho bam gio da san sang | QA | [ ] |

---

## 3. Kich Ban Sinh Vien (8 tasks)

**Thoi luong tong**: 45-60 phut
**Moi truong**: Staging -- truy cap qua trinh duyet Chrome/Edge

> **Huong dan Observer**: Voi moi task, ghi nhan (1) pass/fail, (2) thoi gian thuc te (dong ho bam gio), (3) SV co can ho tro khong, (4) SV co bieu hien boi roi/do du khong. Dung can thiep tru khi SV yeu cau.

### S1: Dang nhap va chap nhan consent

**Thoi gian du kien**: 3-5 phut
**Lien ket muc tieu**: G1 (onboarding)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Mo trinh duyet, truy cap `staging.palp.dau.edu.vn` | Trang login hien thi |
| 2 | Nhap tai khoan va mat khau duoc cap | Dang nhap thanh cong |
| 3 | Doc noi dung consent (thu thap du lieu hoc tap) | Noi dung hien thi day du, ro rang |
| 4 | Nhan nut "Dong y" | Chuyen sang trang student dashboard |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Can ho tro?** | Co [ ] / Khong [ ] |
| **SV doc consent truoc khi dong y?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

---

### S2: Lam assessment dau vao (10-15 cau)

**Thoi gian du kien**: 10-15 phut
**Lien ket muc tieu**: G1 (onboarding)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Tu dashboard, nhan "Bat dau Assessment" | Trang assessment hien thi, co timer |
| 2 | Doc cau hoi va chon dap an cho cau 1 | Dap an duoc ghi nhan, chuyen sang cau tiep |
| 3 | Tra loi lan luot den cau cuoi cung | Progress bar cap nhat, timer chay |
| 4 | Nhan "Nop bai" | Ket qua hien thi: diem so, strengths, weaknesses |
| 5 | Verify: thoi gian hoan thanh <= 15 phut | Khong bi timeout |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Can ho tro?** | Co [ ] / Khong [ ] |
| **SV hieu cau hoi khong can giai thich?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

---

### S3: Xem learner profile

**Thoi gian du kien**: 3 phut
**Lien ket muc tieu**: G3 (progress trust)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Sau assessment, xem trang ket qua | Hien thi diem tong, cac concept manh/yeu |
| 2 | Xem chi tiet strengths | Danh sach concepts SV gioi, co % |
| 3 | Xem chi tiet weaknesses | Danh sach concepts can cai thien, co % |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **SV dong y voi danh gia strengths/weaknesses?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

---

### S4: Vao pathway, lam 3 micro-task

**Thoi gian du kien**: 10-15 phut
**Lien ket muc tieu**: G2 (adaptive), G3 (progress)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Tu dashboard, vao "Lo trinh hoc tap" | Trang pathway hien thi concept map |
| 2 | Chon concept dau tien (duoc goi y) | Danh sach micro-tasks hien thi |
| 3 | Lam micro-task 1 (tra loi dung) | Feedback "Dung!", mastery tang, chuyen task tiep |
| 4 | Lam micro-task 2 (tra loi dung) | Mastery tiep tuc tang |
| 5 | Lam micro-task 3 (tra loi sai) | Feedback "Chua dung", goi y xem noi dung bo tro |
| 6 | Verify: progress bar cap nhat sau moi task | Thanh tien trinh thay doi |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Flow co tu nhien?** | Co [ ] / Khong [ ] |
| **SV biet minh dang o dau trong lo trinh?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

---

### S5: Verify supplementary content

**Thoi gian du kien**: 5 phut
**Lien ket muc tieu**: G2 (adaptive intervention acceptance)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Sau khi tra loi sai, he thong goi y noi dung bo tro | Xuat hien noi dung giai thich lien quan den concept |
| 2 | Doc noi dung bo tro | Noi dung ro rang, de hieu, dung concept |
| 3 | Quay lai lam lai task (retry) | Cho phep lam lai, attempt_number tang |
| 4 | Tra loi dung lan nay | Mastery tang, pathway tiep tuc |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Noi dung bo tro co huu ich?** | Co [ ] / Khong [ ] |
| **SV hieu vi sao he thong goi y noi dung nay?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

> **Sau task S5**: Phat phieu PALP-SV-01 cho SV dien ngay (xem Phu luc A).

---

### S6: Dat mastery cao, verify advance

**Thoi gian du kien**: 5-8 phut
**Lien ket muc tieu**: G3 (progress trust)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Tiep tuc lam cac task (tra loi dung lien tiep) | Mastery tang dan |
| 2 | Khi mastery vuot nguong (>85%) | He thong thong bao "Chuyen sang concept tiep theo" |
| 3 | Verify: concept moi xuat hien trong pathway | Concept tiep theo duoc mo khoa |
| 4 | Verify: concept cu duoc danh dau hoan thanh | Trang thai "Da thong hieu" |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **SV nhan thay mastery tang sau moi cau dung?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

---

### S7: Kiem tra wellbeing nudge

**Thoi gian du kien**: 3-5 phut
**Lien ket muc tieu**: (supplementary -- khong thuoc G1-G5 nhung xac nhan UX)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Sau khi hoc lien tuc >= 50 phut | Nudge xuat hien: "Ban da hoc 50 phut, nen nghi ngoi!" |
| 2 | Verify: nudge KHONG block giao dien | Van co the tiep tuc hoc neu muon |
| 3 | Nhan "Nghi ngoi" hoac "Tiep tuc" | Phan hoi duoc ghi nhan |
| 4 | Neu chua du 50 phut, Observer ghi nhan | Khong co nudge -- dung logic |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Nudge co lam phien?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

---

### S8: Xem dashboard ca nhan

**Thoi gian du kien**: 3-5 phut
**Lien ket muc tieu**: G3 (progress trust)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Quay ve trang dashboard | Dashboard hien thi day du thong tin |
| 2 | Xem tong quan: mastery cac concept | Bieu do/chart phan anh dung tien trinh |
| 3 | Xem lich su hoc tap: so task da lam | So lieu khop voi thuc te |
| 4 | Xem trang thai pathway | Tien trinh dung voi nhung gi da lam |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Dashboard co de hieu?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

> **Sau task S8**: Phat phieu PALP-SV-02 cho SV dien ngay (xem Phu luc A).

---

## 4. Kich Ban Giang Vien (7 tasks)

**Thoi luong tong**: 30-45 phut
**Moi truong**: Staging -- sau khi SV da hoan thanh buoi UAT

> **Huong dan Observer**: Voi moi task, ghi nhan (1) pass/fail, (2) thoi gian thuc te, (3) GV co can giai thich them khong, (4) GV co tu tin khi thao tac. Chu y dac biet den phan ung cua GV voi alert -- ho tin hay nghi ngo?

### L1: Dang nhap

**Thoi gian du kien**: 2 phut
**Lien ket muc tieu**: (baseline)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Truy cap `staging.palp.dau.edu.vn` | Trang login hien thi |
| 2 | Dang nhap bang tai khoan GV | Chuyen sang GV dashboard |
| 3 | Verify: giao dien khac voi SV | Menu va layout dung role GV |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Ghi chu Observer** | |

---

### L2: Xem class overview

**Thoi gian du kien**: 5 phut
**Lien ket muc tieu**: G4 (dashboard comprehension)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Tai trang class overview | Hien thi danh sach lop duoc phan cong |
| 2 | Chon lop SBVL-01 | Tong quan lop hien thi |
| 3 | Xem so lieu: total SV, on-track, watch, urgent | Cac con so hien thi ro rang |
| 4 | Verify: tong on-track + watch + urgent = total | Phep tinh dung |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Dashboard co de hieu?** | Co [ ] / Khong [ ] |
| **GV can giai thich gi them?** | |
| **Ghi chu Observer** | |

---

### L3: Verify so lieu on-track / watch / urgent

**Thoi gian du kien**: 5 phut
**Lien ket muc tieu**: G4 (alert trust)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Xem SV duoc danh dau "on-track" (GREEN) | SV dang hoat dong binh thuong |
| 2 | Xem SV duoc danh dau "watch" (YELLOW) | SV co dau hieu can chu y (inactive 3-4 ngay hoac progress cham) |
| 3 | Xem SV duoc danh dau "urgent" (RED) | SV can can thiep (inactive >= 5 ngay hoac fail >= 3 lan) |
| 4 | Doi chieu voi du lieu thuc (Observer cung cap) | Phan loai chinh xac, khong false positive/negative |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **So lieu co chinh xac?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

---

### L4: Click alert RED, xem chi tiet

**Thoi gian du kien**: 5 phut
**Lien ket muc tieu**: G4 (alert trust, comprehension)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Vao tab "Canh bao" | Danh sach alerts hien thi |
| 2 | Filter theo severity = RED | Chi hien thi canh bao do |
| 3 | Click vao 1 alert RED | Chi tiet hien thi: ten SV, ly do, bang chung, hanh dong goi y |
| 4 | Verify: "ly do" de hieu (human-readable) | GV hieu duoc tai sao SV bi canh bao |
| 5 | Verify: "hanh dong goi y" co ich | Goi y cu the va co the thuc hien |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Ly do canh bao co de hieu?** | Co [ ] / Khong [ ] |
| **GV tin vao do chinh xac cua canh bao?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

> **Sau task L4**: Phat phieu PALP-GV-01 cho GV dien ngay (xem Phu luc A).

---

### L5: Tao intervention

**Thoi gian du kien**: 5-8 phut
**Lien ket muc tieu**: G5 (intervention ease)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Tu chi tiet alert, nhan "Thuc hien hanh dong" | Form action hien thi |
| 2 | Chon loai action: "Gui tin nhan" | Form nhap noi dung tin nhan |
| 3 | Nhap noi dung va gui | Thanh cong, thong bao xac nhan |
| 4 | Verify: intervention xuat hien trong lich su | Ghi day du: ai, khi nao, hanh dong gi |
| 5 | Thu them: "Goi y bai tap" hoac "Hen gap" | Cac loai action hoat dong |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Flow co nhanh va ro rang?** | Co [ ] / Khong [ ] |
| **GV can huong dan de thuc hien?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

> **Sau task L5**: Phat phieu PALP-GV-02 cho GV dien ngay (xem Phu luc A).

---

### L6: Verify alert resolved

**Thoi gian du kien**: 3-5 phut
**Lien ket muc tieu**: G5 (intervention workflow)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Quay lai danh sach alerts | Alert da xu ly van hien thi |
| 2 | Nhan "Dismiss" tren alert da xu ly | Form nhap ghi chu hien thi |
| 3 | Nhap ghi chu va dismiss | Alert chuyen trang thai "da xu ly" |
| 4 | Verify: alert khong con trong danh sach active | Filter active khong hien thi alert da dismiss |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Ghi chu Observer** | |

---

### L7: Xem KPI report

**Thoi gian du kien**: 5 phut
**Lien ket muc tieu**: G4 (dashboard comprehension)

| Buoc | Hanh dong | Ket qua mong doi |
|------|----------|-----------------|
| 1 | Vao tab "Bao cao" hoac "KPI" | Trang bao cao hien thi |
| 2 | Xem cac chi so: active learning time, completion rate, GV usage | So lieu hien thi, khong null/NaN |
| 3 | Xem bieu do/chart tien trinh lop | Bieu do render dung, co du lieu |
| 4 | Verify: du lieu co y nghia (khop voi UAT session) | So lieu phan anh hoat dong thuc |

| Ket qua | |
|---------|---|
| **Pass** | [ ] |
| **Fail** | [ ] |
| **Thoi gian thuc te** | _____ phut _____ giay |
| **Bao cao co huu ich cho GV?** | Co [ ] / Khong [ ] |
| **Ghi chu Observer** | |

---

## 5. Thu Thap Metrics

### 5.1 Task Success Rate

**Muc tieu**: >= 90% tasks thanh cong (khong can ho tro)

| Task | Tong nguoi thu | Thanh cong | That bai | Ty le | Can ho tro |
|------|---------------|-----------|---------|-------|-----------|
| S1: Dang nhap + consent | | | | % | |
| S2: Assessment | | | | % | |
| S3: Learner profile | | | | % | |
| S4: Pathway + micro-tasks | | | | % | |
| S5: Supplementary content | | | | % | |
| S6: Advance concept | | | | % | |
| S7: Wellbeing nudge | | | | % | |
| S8: Dashboard ca nhan | | | | % | |
| L1: GV dang nhap | | | | % | |
| L2: Class overview | | | | % | |
| L3: Verify so lieu | | | | % | |
| L4: Alert chi tiet | | | | % | |
| L5: Intervention | | | | % | |
| L6: Resolve alert | | | | % | |
| L7: KPI report | | | | % | |
| **Tong** | | | | **___%** | |

**Onboarding stuck rate** (tinh rieng): So SV fail S1 hoac S2 / Tong SV = ___%
- Nguong fail: >= 10% -> FAIL-01 triggered

### 5.2 Time on Task (Vong 1 vs Vong 2)

Muc tieu: Thoi gian trung binh o Vong 2 **phai giam** so voi Vong 1 cho cac core flow (S2, S4, S5, S6).

| Task | Du kien | V1 Trung binh | V1 Min | V1 Max | V2 Trung binh | V2 Min | V2 Max | Delta (%) |
|------|---------|--------------|--------|--------|--------------|--------|--------|-----------|
| S1: Dang nhap + consent | 3-5 phut | | | | | | | |
| S2: Assessment | 10-15 phut | | | | | | | |
| S3: Learner profile | 3 phut | | | | | | | |
| S4: Pathway + micro-tasks | 10-15 phut | | | | | | | |
| S5: Supplementary | 5 phut | | | | | | | |
| S6: Advance | 5-8 phut | | | | | | | |
| S7: Wellbeing | 3-5 phut | | | | | | | |
| S8: Dashboard | 3-5 phut | | | | | | | |
| L1: GV dang nhap | 2 phut | | | | | | | |
| L2: Class overview | 5 phut | | | | | | | |
| L3: Verify so lieu | 5 phut | | | | | | | |
| L4: Alert chi tiet | 5 phut | | | | | | | |
| L5: Intervention | 5-8 phut | | | | | | | |
| L6: Resolve alert | 3-5 phut | | | | | | | |
| L7: KPI report | 5 phut | | | | | | | |

**Cach tinh Delta**: `(V2 - V1) / V1 * 100`. Gia tri am = cai thien. Gia tri duong = thoai lui.

### 5.3 SUS -- System Usability Scale

Moi nguoi tham gia dien bang cau hoi SUS sau khi hoan thanh. Thang diem: 1 (Hoan toan khong dong y) den 5 (Hoan toan dong y).

| # | Cau hoi | 1 | 2 | 3 | 4 | 5 |
|---|--------|---|---|---|---|---|
| 1 | Toi nghi rang toi se su dung he thong nay thuong xuyen | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2 | Toi thay he thong nay phuc tap khong can thiet | [ ] | [ ] | [ ] | [ ] | [ ] |
| 3 | Toi thay he thong nay de su dung | [ ] | [ ] | [ ] | [ ] | [ ] |
| 4 | Toi nghi rang toi se can ho tro ky thuat de su dung he thong nay | [ ] | [ ] | [ ] | [ ] | [ ] |
| 5 | Toi thay cac chuc nang trong he thong duoc tich hop tot | [ ] | [ ] | [ ] | [ ] | [ ] |
| 6 | Toi thay co qua nhieu su khong nhat quan trong he thong nay | [ ] | [ ] | [ ] | [ ] | [ ] |
| 7 | Toi tuong tuong rang hau het moi nguoi se hoc cach su dung he thong nay rat nhanh | [ ] | [ ] | [ ] | [ ] | [ ] |
| 8 | Toi thay he thong nay rat ruom ra khi su dung | [ ] | [ ] | [ ] | [ ] | [ ] |
| 9 | Toi cam thay rat tu tin khi su dung he thong nay | [ ] | [ ] | [ ] | [ ] | [ ] |
| 10 | Toi can hoc nhieu thu truoc khi co the su dung he thong nay | [ ] | [ ] | [ ] | [ ] | [ ] |

**Cach tinh diem SUS:**
- Cau le (1,3,5,7,9): diem = gia tri chon - 1
- Cau chan (2,4,6,8,10): diem = 5 - gia tri chon
- Tong 10 cau x 2.5 = diem SUS (0-100)
- **Muc tieu: SUS >= 80** (muc "Good" -- tren trung binh nganh)

**Tham chieu thang diem SUS:**

| Diem | Xep hang | Y nghia |
|------|---------|---------|
| < 51 | F | Khong chap nhan duoc |
| 51-67 | D | Duoi trung binh |
| 68-79 | C | Trung binh (muc cu) |
| **80-89** | **B** | **Tot -- muc tieu PALP** |
| 90-100 | A | Xuat sac |

### 5.4 CSAT -- Customer Satisfaction Score

**Muc tieu**: >= 4.0 / 5.0

| Cau hoi | 1 | 2 | 3 | 4 | 5 |
|---------|---|---|---|---|---|
| Tong the, ban hai long voi PALP o muc nao? | [ ] | [ ] | [ ] | [ ] | [ ] |
| PALP giup ban hoc tap / giang day hieu qua hon? | [ ] | [ ] | [ ] | [ ] | [ ] |
| Ban co gioi thieu PALP cho ban be / dong nghiep? | [ ] | [ ] | [ ] | [ ] | [ ] |

### 5.5 PALP-specific Quality Metrics

Day la cac metric **dac thu cho PALP**, do luong truc tiep 5 muc tieu UAT (G1-G5). Cac metric nay khong the thay the bang SUS/CSAT vi chung do nhung khia canh EdTech ma thang do chung khong bao phu.

#### PALP-SV-01: Hieu biet ve adaptive intervention (phat sau S5)

**Muc tieu**: Trung binh >= 4/5 cho moi cau

| # | Cau hoi | 1 | 2 | 3 | 4 | 5 |
|---|--------|---|---|---|---|---|
| 1 | Toi hieu vi sao he thong goi y noi dung bo tro cho toi | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2 | Noi dung bo tro giup toi hieu bai tot hon khi lam lai | [ ] | [ ] | [ ] | [ ] | [ ] |
| 3 | Toi khong cam thay bi ep buoc khi he thong dieu chinh lo trinh | [ ] | [ ] | [ ] | [ ] | [ ] |

- Nguong fail (FAIL-02): >= 10% SV cho diem <= 2 o cau 1

#### PALP-SV-02: Do tin cay cua progress (phat sau S8)

**Muc tieu**: Trung binh >= 4/5 cho moi cau

| # | Cau hoi | 1 | 2 | 3 | 4 | 5 |
|---|--------|---|---|---|---|---|
| 1 | Tien trinh hoc tap tren dashboard phan anh dung nang luc thuc te cua toi | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2 | Mastery % toi thay tren man hinh khop voi cam nhan cua toi ve muc do hieu bai | [ ] | [ ] | [ ] | [ ] | [ ] |
| 3 | Toi tin rang he thong dang danh gia dung suc hoc cua toi | [ ] | [ ] | [ ] | [ ] | [ ] |

#### PALP-GV-01: Do tin cay cua canh bao (phat sau L4)

**Muc tieu**: Trung binh >= 4/5 cho moi cau

| # | Cau hoi | 1 | 2 | 3 | 4 | 5 |
|---|--------|---|---|---|---|---|
| 1 | Toi tin vao do chinh xac cua canh bao (RED/YELLOW) | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2 | Ly do canh bao duoc giai thich ro rang, toi hieu duoc | [ ] | [ ] | [ ] | [ ] | [ ] |
| 3 | Hanh dong goi y la huu ich va co the thuc hien trong thuc te | [ ] | [ ] | [ ] | [ ] | [ ] |
| 4 | Canh bao phan loai dung muc do nghiem trong (RED vs YELLOW) | [ ] | [ ] | [ ] | [ ] | [ ] |

- **Tinh alert usefulness**: So cau 3 duoc danh gia >= 4 / Tong cau 3 = ___%
- Nguong fail (FAIL-04): > 20% danh gia cau 3 <= 2

#### PALP-GV-02: Do de dang can thiep (phat sau L5)

**Muc tieu**: Trung binh >= 4/5 cho moi cau

| # | Cau hoi | 1 | 2 | 3 | 4 | 5 |
|---|--------|---|---|---|---|---|
| 1 | Toi co the thuc hien hanh dong can thiep ma khong can dao tao them | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2 | Cac buoc tu xem canh bao den thuc hien hanh dong la nhanh va ro rang | [ ] | [ ] | [ ] | [ ] | [ ] |
| 3 | Toi biet theo doi ket qua can thiep cua minh o dau | [ ] | [ ] | [ ] | [ ] | [ ] |

### 5.6 Tong hop PALP Metrics

| Metric | Nguon | Ket qua | Nguong | Status |
|--------|-------|---------|--------|--------|
| SV intervention understanding | PALP-SV-01 cau 1 TB | ___/5 | >= 4/5 | [ ] Pass / [ ] Fail |
| SV progress trust | PALP-SV-02 TB | ___/5 | >= 4/5 | [ ] Pass / [ ] Fail |
| GV alert trust | PALP-GV-01 cau 1 TB | ___/5 | >= 4/5 | [ ] Pass / [ ] Fail |
| GV alert usefulness | PALP-GV-01 cau 3 rate | ___% | > 80% | [ ] Pass / [ ] Fail |
| GV intervention ease | PALP-GV-02 cau 1 TB | ___/5 | >= 4/5 | [ ] Pass / [ ] Fail |
| Onboarding stuck rate | S1+S2 fail rate | ___% | < 10% | [ ] Pass / [ ] Fail |
| Time-on-task regression | V2 core avg < V1 | ___% | < 0% | [ ] Pass / [ ] Fail |

### 5.7 Bug Tracking

Moi loi phat hien trong UAT duoc ghi nhan theo mau:

| # | Mo ta loi | Buoc tai hien | Muc do | Task | Vong | Anh chup | Nguoi bao |
|---|----------|--------------|--------|------|------|----------|----------|
| 1 | | | P0 / P1 / P2 / P3 | | V1 / V2 | | |
| 2 | | | P0 / P1 / P2 / P3 | | V1 / V2 | | |
| 3 | | | P0 / P1 / P2 / P3 | | V1 / V2 | | |
| 4 | | | P0 / P1 / P2 / P3 | | V1 / V2 | | |
| 5 | | | P0 / P1 / P2 / P3 | | V1 / V2 | | |

Dinh nghia muc do:
- **P0 Blocker**: Khong the su dung chuc nang chinh
- **P1 Critical**: Sai logic, sai du lieu, sai phan quyen
- **P2 Major**: Loi anh huong trai nghiem, co workaround
- **P3 Minor**: Loi nho, UI, wording

**Thong ke bugs theo vong:**

| Muc do | Vong 1 | Vong 2 | Da fix |
|--------|--------|--------|--------|
| P0 | | | |
| P1 | | | |
| P2 | | | |
| P3 | | | |

---

## 6. Tieu Chi Exit (Go/No-go)

UAT chi duoc xem la **PASS** khi thoa **dong thoi** tat ca tieu chi exit **VA** khong vi pham bat ky fail condition nao.

### 6.1 Exit Criteria

| # | Tieu chi | Nguong | Ket qua | Status |
|---|---------|--------|---------|--------|
| EXIT-01 | Task success rate (tat ca tasks) | >= 90% | ___% | [ ] Pass / [ ] Fail |
| EXIT-02 | Diem SUS | >= 80/100 | ___ | [ ] Pass / [ ] Fail |
| EXIT-03 | So loi P0 | 0 | ___ | [ ] Pass / [ ] Fail |
| EXIT-04 | So loi P1 chua fix | 0 | ___ | [ ] Pass / [ ] Fail |
| EXIT-05 | Privacy incidents | 0 | ___ | [ ] Pass / [ ] Fail |
| EXIT-06 | CSAT score | >= 4.0/5 | ___/5 | [ ] Pass / [ ] Fail |
| EXIT-07 | GV danh gia dashboard "de hieu" | >= 80% GV | ___/___ GV | [ ] Pass / [ ] Fail |
| EXIT-08 | SV bi ket (dead-end) | 0 | ___ | [ ] Pass / [ ] Fail |
| EXIT-09 | GV tin tuong canh bao (PALP-GV-01 cau 1) | >= 4/5 | ___/5 | [ ] Pass / [ ] Fail |
| EXIT-10 | SV hieu adaptive intervention (PALP-SV-01 cau 1) | >= 4/5 | ___/5 | [ ] Pass / [ ] Fail |
| EXIT-11 | Time-on-task giam o Vong 2 (core flows) | V2 avg < V1 avg | ___% | [ ] Pass / [ ] Fail |
| EXIT-12 | SV progress trust (PALP-SV-02 TB) | >= 4/5 | ___/5 | [ ] Pass / [ ] Fail |

### 6.2 Fail Conditions (Hard Stop)

Bat ky fail condition nao bi vi pham -> **tu dong NO-GO**, bat ke exit criteria.

| # | Dieu kien | Nguon do | Nguong | Ket qua | Status |
|---|----------|---------|--------|---------|--------|
| FAIL-01 | SV bi ket o onboarding (S1 hoac S2 fail) | Observer sheet | >= 10% SV | ___% | [ ] OK / [ ] VIOLATED |
| FAIL-02 | SV khong hieu vi sao bi chuyen intervention | PALP-SV-01 cau 1 <= 2 | >= 10% SV | ___% | [ ] OK / [ ] VIOLATED |
| FAIL-03 | GV noi dashboard "kho hieu" | L2 + PALP-GV-01 | >= 20% GV | ___/___ GV | [ ] OK / [ ] VIOLATED |
| FAIL-04 | Canh bao bi danh gia "khong huu ich" | PALP-GV-01 cau 3 <= 2 | > 20% | ___% | [ ] OK / [ ] VIOLATED |
| FAIL-05 | Loi P1 phat hien trong Vong 2 (vong cuoi) | Bug tracker | > 1 loi P1 | ___ | [ ] OK / [ ] VIOLATED |

**Logic quyet dinh:**

```
NEU bat ky FAIL-01 -> FAIL-05 bi VIOLATED:
  -> NO-GO (tu dong, khong can hop)
  -> Xac dinh root cause
  -> Fix + to chuc UAT vong bo sung

NEU tat ca FAIL conditions = OK:
  -> Kiem tra EXIT-01 -> EXIT-12
  -> NEU tat ca EXIT = Pass -> GO
  -> NEU bat ky EXIT = Fail -> NO-GO (hop de quyet dinh)
```

---

## 7. Quy Trinh Sau UAT

### 7.1 Vong 1

| Timeline | Hanh dong | Responsible |
|----------|----------|-------------|
| Trong buoi | Observer tong hop bugs realtime | QA |
| Trong 24h | Tong hop feedback Vong 1 + bugs | QA + PO |
| Trong 48h | Fix tat ca P0 tu Vong 1 | Dev |
| Truoc Vong 2 | Deploy fix len staging, QA verify | DevOps + QA |

### 7.2 Vong 2

| Timeline | Hanh dong | Responsible |
|----------|----------|-------------|
| Trong buoi | Observer tong hop bugs + so sanh time-on-task | QA |
| Trong 24h | Tinh toan tat ca metrics (SUS, CSAT, PALP-specific) | QA + PO |
| Trong 24h | Hoan thanh UAT Report (Section 8) | QA + PO |
| Trong 48h | Fix tat ca P0 (neu co) | Dev |
| Trong 1 sprint | Fix tat ca P1 | Dev |
| Truoc pilot | Re-verify bugs da fix | QA |
| Truoc pilot | Go/No-go meeting voi PO + GV + Tech Lead | PO |

---

## 8. Template Bao Cao UAT

```
# PALP UAT Report v2.0
Ngay: ____/____/______
Phien ban: v____

---

## 1. Tham gia

| Vai tro | So luong | Ghi chu |
|---------|---------|---------|
| Sinh vien | ____ | |
| Giang vien | ____ | |
| Observer | ____ | |

---

## 2. Ket qua Exit Criteria

| # | Tieu chi | Nguong | Ket qua | Status |
|---|---------|--------|---------|--------|
| EXIT-01 | Task success rate | >= 90% | ___% | PASS / FAIL |
| EXIT-02 | SUS | >= 80 | ___ | PASS / FAIL |
| EXIT-03 | P0 bugs | 0 | ___ | PASS / FAIL |
| EXIT-04 | P1 bugs chua fix | 0 | ___ | PASS / FAIL |
| EXIT-05 | Privacy incidents | 0 | ___ | PASS / FAIL |
| EXIT-06 | CSAT | >= 4.0/5 | ___/5 | PASS / FAIL |
| EXIT-07 | GV dashboard comprehension | >= 80% | ___% | PASS / FAIL |
| EXIT-08 | SV dead-ends | 0 | ___ | PASS / FAIL |
| EXIT-09 | GV alert trust | >= 4/5 | ___/5 | PASS / FAIL |
| EXIT-10 | SV intervention understanding | >= 4/5 | ___/5 | PASS / FAIL |
| EXIT-11 | Time-on-task regression | V2 < V1 | ___% | PASS / FAIL |
| EXIT-12 | SV progress trust | >= 4/5 | ___/5 | PASS / FAIL |

---

## 3. Fail Conditions

| # | Dieu kien | Nguong | Ket qua | Status |
|---|----------|--------|---------|--------|
| FAIL-01 | Onboarding stuck rate | < 10% | ___% | OK / VIOLATED |
| FAIL-02 | SV khong hieu intervention | < 10% | ___% | OK / VIOLATED |
| FAIL-03 | GV "kho hieu" dashboard | < 20% | ___% | OK / VIOLATED |
| FAIL-04 | Alert "khong huu ich" | <= 20% | ___% | OK / VIOLATED |
| FAIL-05 | P1 bugs Vong 2 | <= 1 | ___ | OK / VIOLATED |

---

## 4. PALP-specific Metrics

| Metric | Ket qua | Nguong | Status |
|--------|---------|--------|--------|
| SV intervention understanding (PALP-SV-01) | ___/5 | >= 4/5 | PASS / FAIL |
| SV progress trust (PALP-SV-02) | ___/5 | >= 4/5 | PASS / FAIL |
| GV alert trust (PALP-GV-01) | ___/5 | >= 4/5 | PASS / FAIL |
| GV alert usefulness | ___% | > 80% | PASS / FAIL |
| GV intervention ease (PALP-GV-02) | ___/5 | >= 4/5 | PASS / FAIL |

---

## 5. Time-on-task Regression (Core Flows)

| Task | V1 Avg | V2 Avg | Delta (%) | Improved? |
|------|--------|--------|-----------|-----------|
| S2: Assessment | | | | Y / N |
| S4: Pathway + micro-tasks | | | | Y / N |
| S5: Supplementary | | | | Y / N |
| S6: Advance | | | | Y / N |
| L4: Alert chi tiet | | | | Y / N |
| L5: Intervention | | | | Y / N |

---

## 6. Bug Summary

| Muc do | Vong 1 | Vong 2 | Da fix | Con lai |
|--------|--------|--------|--------|---------|
| P0 | | | | |
| P1 | | | | |
| P2 | | | | |
| P3 | | | | |
| **Tong** | | | | |

---

## 7. Quyet dinh

[ ] GO -- Tat ca exit criteria PASS, khong fail condition bi violated
[ ] NO-GO -- Chi tiet ben duoi

Ly do (neu NO-GO):
_______________________________

Hanh dong tiep theo:
1. ____
2. ____
3. ____

---

## 8. Chu ky

PO: ________________  Ngay: ____/____/______
Tech Lead: __________  Ngay: ____/____/______
GV: _________________  Ngay: ____/____/______
QA Lead: ____________  Ngay: ____/____/______
```

---

## Phu luc A: Phieu Khao Sat PALP-specific

### PALP-SV-01: Hieu biet ve adaptive intervention

**Phat cho SV ngay sau task S5 (Supplementary content)**

```
Ho ten (hoac ma SV): ____________
Ngay: ____/____/______
Vong: [ ] 1  [ ] 2

Xin hay cho diem tu 1 (Hoan toan khong dong y) den 5 (Hoan toan dong y):

1. Toi hieu vi sao he thong goi y noi dung bo tro cho toi
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

2. Noi dung bo tro giup toi hieu bai tot hon khi lam lai
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

3. Toi khong cam thay bi ep buoc khi he thong dieu chinh lo trinh
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

Y kien them (tuy chon):
_______________________________
```

### PALP-SV-02: Do tin cay cua progress

**Phat cho SV ngay sau task S8 (Dashboard ca nhan)**

```
Ho ten (hoac ma SV): ____________
Ngay: ____/____/______
Vong: [ ] 1  [ ] 2

Xin hay cho diem tu 1 (Hoan toan khong dong y) den 5 (Hoan toan dong y):

1. Tien trinh hoc tap tren dashboard phan anh dung nang luc thuc te cua toi
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

2. Mastery % toi thay tren man hinh khop voi cam nhan cua toi ve muc do hieu bai
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

3. Toi tin rang he thong dang danh gia dung suc hoc cua toi
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

Y kien them (tuy chon):
_______________________________
```

### PALP-GV-01: Do tin cay cua canh bao

**Phat cho GV ngay sau task L4 (Alert detail)**

```
Ho ten GV: ____________
Ngay: ____/____/______
Vong: [ ] 1  [ ] 2

Xin hay cho diem tu 1 (Hoan toan khong dong y) den 5 (Hoan toan dong y):

1. Toi tin vao do chinh xac cua canh bao (RED/YELLOW)
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

2. Ly do canh bao duoc giai thich ro rang, toi hieu duoc
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

3. Hanh dong goi y la huu ich va co the thuc hien trong thuc te
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

4. Canh bao phan loai dung muc do nghiem trong (RED vs YELLOW)
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

So alert da xem: ____
So alert thay "khong huu ich": ____

Y kien them (tuy chon):
_______________________________
```

### PALP-GV-02: Do de dang can thiep

**Phat cho GV ngay sau task L5 (Intervention)**

```
Ho ten GV: ____________
Ngay: ____/____/______
Vong: [ ] 1  [ ] 2

Xin hay cho diem tu 1 (Hoan toan khong dong y) den 5 (Hoan toan dong y):

1. Toi co the thuc hien hanh dong can thiep ma khong can dao tao them
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

2. Cac buoc tu xem canh bao den thuc hien hanh dong la nhanh va ro rang
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

3. Toi biet theo doi ket qua can thiep cua minh o dau
   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5

Y kien them (tuy chon):
_______________________________
```

---

## Phu luc B: Observer Sheet Template

```
# Observer Sheet -- PALP UAT
Ngay: ____/____/______
Vong: [ ] 1  [ ] 2
Observer: ____________
Nguoi duoc quan sat: ____________ (SV / GV)

## Ghi nhan theo task

| Task | Bat dau | Ket thuc | Pass/Fail | Can ho tro? | Bieu hien dac biet |
|------|---------|---------|-----------|-------------|-------------------|
| | : | : | P / F | Y / N | |
| | : | : | P / F | Y / N | |
| | : | : | P / F | Y / N | |
| | : | : | P / F | Y / N | |
| | : | : | P / F | Y / N | |
| | : | : | P / F | Y / N | |
| | : | : | P / F | Y / N | |
| | : | : | P / F | Y / N | |

## Onboarding Observation (S1 + S2)

- SV bi ket tai buoc nao? ____________
- SV hoi gi? ____________
- Mat bao lau de tu giai quyet? ____________

## Intervention Observation (S5)

- SV co doc noi dung bo tro? [ ] Co  [ ] Khong  [ ] Luot qua
- SV co bieu hien boi roi khi thay "goi y noi dung"? [ ] Co  [ ] Khong
- SV co noi gi ve viec bi chuyen huong? ____________

## General Notes

_______________________________
_______________________________
_______________________________
```

---

## Phu luc C: Traceability Matrix -- Muc tieu -> Metric -> Task -> Fail Condition

| Muc tieu | Metric chinh | Tasks | Exit Criteria | Fail Condition |
|---------|-------------|-------|---------------|---------------|
| G1: SV hieu onboarding | Onboarding stuck rate < 10% | S1, S2 | EXIT-01, EXIT-08 | FAIL-01 |
| G2: SV chap nhan adaptive | SV understanding >= 4/5 | S5, PALP-SV-01 | EXIT-10 | FAIL-02 |
| G3: SV khong thay progress gia | SV progress trust >= 4/5 | S6, S8, PALP-SV-02 | EXIT-12 | -- |
| G4: GV hieu dashboard, tin canh bao | GV alert trust >= 4/5; usefulness > 80% | L2, L3, L4, PALP-GV-01 | EXIT-07, EXIT-09 | FAIL-03, FAIL-04 |
| G5: GV can thiep khong can dao tao | GV intervention ease >= 4/5 | L5, L6, PALP-GV-02 | EXIT-01 (L5 task success) | -- |
| (Cross-cutting) | Time-on-task giam Vong 2 | All tasks | EXIT-11 | -- |
| (Cross-cutting) | P1 bugs Vong 2 <= 1 | Bug tracker | EXIT-04 | FAIL-05 |

---

## References

| Tai lieu | Duong dan |
|---------|----------|
| QA Standard | [docs/QA_STANDARD.md](QA_STANDARD.md) |
| Testing Guide | [docs/TESTING.md](TESTING.md) |
| API Reference | [docs/API.md](API.md) |
| PRD | [docs/PRD.md](PRD.md) |
