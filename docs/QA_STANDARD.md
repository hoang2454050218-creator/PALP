# PALP Quality Standard v1.0

> **Classification**: Internal -- Dev / QA / PO / Tech Lead
> **Scope**: MVP pilot (1 mon, 60-90 SV, 10 tuan)
> **Effective**: Tu Sprint 4 tro di; bat buoc cho moi release candidate
> **Owner**: Tech Lead -- sign-off boi PO + GV representative

---

## 1. Framework Overview -- 6 Quality Layers

PALP chi duoc xem la **dat chuan release** khi thoa dong thoi **6 lop chat luong** duoi day. Day la san pham EdTech co tac dong truc tiep den quyet dinh hoc tap va can thiep su pham -- tieu chuan khong chi la "khong crash" ma la **khong duoc dua ra hanh vi sai gay hieu sai nang luc hoac can thiep sai cho sinh vien va giang vien**.

### 1.1. Ma tran 6 lop

| Lop | Ten | Dinh nghia | Module chiu trach nhiem |
|-----|-----|-----------|------------------------|
| L1 | Dung chuc nang | Moi feature hoat dong dung AC trong PRD | Tat ca 8 Django apps + frontend |
| L2 | Dung logic hoc tap | BKT update dung, pathway decision dung, early warning phan loai dung, intervention ghi nhan dung | `adaptive/engine.py`, `dashboard/services.py`, `assessment/services.py` |
| L3 | Dung du lieu | Khong mat du lieu, khong du lieu mo coi, khong duplicate, FK consistency, BKT bounds hop le | PostgreSQL schema, `analytics/services.py`, ETL scripts |
| L4 | Dung bao mat va quyen rieng tu | PII duoc ma hoa, RBAC dung, consent gate hoat dong, audit log day du | `accounts/`, RBAC matrix, TLS config |
| L5 | Dung van hanh | Deploy on dinh, backup/restore hoat dong, monitoring bat loi, rollback kha thi | Docker, Celery, Sentry, health endpoint |
| L6 | Dung kha nang do luong va mo rong | Moi KPI do duoc, moi event tracking duoc, schema khong khoa cung scale | `events/`, `analytics/`, event taxonomy |

### 1.2. Nguyen tac ap dung

Moi lop **khong duoc phep trade-off** voi lop khac. Vi du:
- Khong duoc hy sinh L2 (logic hoc tap) de dat L1 (chuc nang chay duoc)
- Khong duoc hy sinh L4 (bao mat) de dat L5 (deploy nhanh)
- Khong duoc hy sinh L3 (du lieu) de dat L6 (do luong)

Nguyen tac nay phu hop voi 5 Design Principles cua PRD:

| Design Principle | Lop chat luong tuong ung |
|-----------------|------------------------|
| Learning before Gamification | L2 -- logic hoc tap phai dung truoc khi them game hoa |
| Human-in-the-loop | L1 + L2 -- GV luon co quyen dismiss/override, he thong khong tu quyet |
| Explainable interventions | L2 + L6 -- moi canh bao giai thich duoc logic, do luong duoc hieu qua |
| Privacy by design | L4 -- thu thap toi thieu, pseudonymization, phan quyen |
| MVP first, intelligence later | L1 + L5 -- rule-based + BKT on dinh truoc, khong them ML khi chua chac L1-L5 |

### 1.3. Definition of Done (per ticket)

Moi ticket PALP chi duoc danh dau **Done** khi thoa **dong thoi** checklist 12 tieu chi (code review, unit/integration/negative tests, analytics, audit khi can, UI/copy, a11y co ban, monitoring hook, docs, PO + QA sign-off) — xem chi tiet va ma tran N/A trong [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md).

- **DoD (ticket)**: chat luong tung work item truoc/sau merge; PR template tai [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md).
- **Release (Section 12)**: chat luong toan phien ban (R-01 -> R-20, drill, UAT).
- **Quy uoc**: Moi ticket trong mot release candidate phai **Done (DoD)** truoc khi gom release va chay du Go/No-Go (Section 13).

### 1.4. Product Correctness Standard

PALP chi duoc xem la **dung** khi trien khai tron cac luong da chot trong PRD. Day la tieu chuan **cap san pham**, cao hon tieu chuan cap chuc nang (L1) vi no yeu cau toan bo chuoi flow hoat dong lien mach, nhat quan, va co the giai thich duoc.

#### 1.4.1. 5 Golden Flows (bat buoc hoat dong dung 100%)

| # | Golden Flow | Mo ta chi tiet | Journey ref | Test cases lien quan |
|---|------------|----------------|-------------|---------------------|
| GF-01 | Student Onboarding | SV dang nhap -> consent -> lam assessment 10-15 phut -> xem ket qua (diem + strengths/weaknesses) -> nhan lo trinh -> bat dau micro-task dau tien | J1 | AUTH-001, CONSENT-001, ASSESS-001..012, FE-001..004 |
| GF-02 | Adaptive Learning Loop | BKT cap nhat theo cau tra loi; P(mastery) < 0.60 -> chen noi dung bo tro va giam do kho; P(mastery) > 0.85 -> tang do kho va advance concept; moi lan submit -> mastery + pathway response day du | J2, J3 | BKT-001..008, PATH-001..004, SUBMIT-001..003, RETRY-001..003 |
| GF-03 | Early Warning -> Intervention | SV sai nhieu lan hoac inactive -> he thong day canh bao sang dashboard GV -> GV co 3 action: gui tin nhan, goi y bai tap, dat lich/hop nhom -> action duoc log va tracking | J4, J5 | EW-001..009, ALERT-001..003, ACTION-001..004, DASH-001..002 |
| GF-04 | Backward Design Progress | Do an chia thanh milestones -> milestones chia thanh micro-tasks -> progress tinh dung (khong double-count, khong mat) -> student thay tien do chinh xac -> GV thay tong quan dung | J1 (A5-A8) | CURR-001..010, FE-005..006 |
| GF-05 | Data -> Insight Pipeline | Event tracking bat day du -> nightly batch tinh KPI -> weekly report -> dashboard GV hien so lieu doi chieu duoc -> decision gate W16 co du lieu dang tin | J7 | EVT-001..010, KPI-001..005, REPORT-001..002, KPIINT-001..013 |

#### 1.4.2. 5 Anti-patterns -- KHONG DUOC ton tai

| # | Anti-pattern | Dinh nghia | Hau qua | Verify bang | Muc do |
|---|-------------|-----------|---------|------------|--------|
| AP-01 | Dead-end flow | SV o bat ky trang thai nao ma khong co buoc tiep theo (khong co task, khong co pathway, khong co redirect) | SV bi ket, mat dong luc, bo he thong | J1 (A6-A7): verify luon co task hoac redirect; J3: verify retry luon dua ra supplementary; RETRY-001: task fail -> supplementary | **P0** |
| AP-02 | Unexplainable state | He thong dua ra ket qua ma khong giai thich duoc tai sao (vi du: alert RED ma khong co reason, pathway advance ma mastery chua du) | GV khong tin dashboard, SV khong hieu lo trinh | EW-008..009: alert co reason human-readable; PATH-001..003: pathway decision nhat quan voi nguong; FE-021: severity co icon + text | **P1** |
| AP-03 | Lost state mid-flow | SV dang lam assessment/task -> dong tab/mat ket noi -> quay lai -> du lieu truoc do bi mat | SV mat cong, frustrated, du lieu khong nhat quan | ASSESS-006: save progress dong tab quay lai; J1 (A3): assessment persistence; AS-02 (E2E): reload mid-assessment | **P0** |
| AP-04 | Double-count completion | Cung 1 task duoc tinh la completed 2 lan; cung 1 attempt duoc dem 2 lan trong progress; completion rate bi inflated | KPI sai, progress khong phan anh thuc te, quyet dinh pilot sai | RETRY-003: attempt_number tang dung (khong duplicate); DI-04: unique MasteryState(student, concept); DI-05: max 1 session in_progress; EVT-008: event idempotency | **P1** |
| AP-05 | False alert do bug logic | Alert RED/YELLOW tao ra khong phai vi SV thuc su gap kho, ma vi bug trong logic early warning (vi du: query sai thoi gian, threshold sai, batch job skip SV) | GV can thiep sai, SV bi phien, mat long tin | EW-001..006: classification dung theo rule; J4: khong false positive (SV binh thuong khong bi RED); DASH-001: overview counts khop; NG-01: adaptive rules dung | **P0** |

#### 1.4.3. Tieu chuan verification

Moi release candidate phai chung minh **khong vi pham bat ky anti-pattern nao** bang cach:

1. **E2E journey pass 100%**: J1-J7 deu pass, moi journey kiem tra khong co dead-end va state duoc giu
2. **Negative test cho anti-patterns**: Moi AP-01..AP-05 co it nhat 2 test case chuyen biet (da liet ke trong bang tren)
3. **Data integrity pass 100%**: DI-01..DI-12 dam bao khong double-count, khong orphan, khong duplicate
4. **Logic correctness pass 100%**: BKT golden vectors, pathway rules, early warning classification deu dung

Mapping vao Go/No-Go (Section 13):

| Anti-pattern | Blocker condition | No-Go condition |
|-------------|-------------------|-----------------|
| AP-01 Dead-end | B1 (P0) | NG-02 (progress), NG-01 (adaptive) |
| AP-02 Unexplainable | B6 (logic sai) | NG-01 (adaptive rules) |
| AP-03 Lost state | B5 (mat du lieu) | NG-02 (progress update) |
| AP-04 Double-count | B7 (event/KPI sai) | NG-06 (event core) |
| AP-05 False alert | B6 (logic sai) | NG-01 (adaptive), NG-05 (ETL) |

### 1.5. Learning Integrity Standard

Day la lop chat luong **quan trong nhat** cua PALP. Nhieu he thong "dung ky thuat" nhung "sai giao duc". PRD da xac dinh adaptive difficulty, explainable interventions, human-in-the-loop va early warning la **loi he thong**. Vi vay, neu engine dung toan nhung khong dung logic hoc tap thi van tinh la **FAIL**.

#### 1.5.1. 6 tieu chi Learning Integrity

| # | Tieu chi | Chuan rat cao | Verify bang | Muc do |
|---|---------|---------------|------------|--------|
| LI-01 | Goi y noi dung | Phai lien quan **dung concept** dang yeu. Khong duoc chen bo tro concept A khi SV dang yeu concept B | LI-F01 test: supplementary.concept == mastery_state.concept; BKT-004..006 golden vectors | **P0** |
| LI-02 | Dieu chinh do kho | Khong duoc nhay cap vo ly hoac oscillate bat thuong. Chi tang khi P(mastery) > 0.85 va du attempt; chi giam khi P(mastery) < 0.60 | LI-F02 test: advance chi khi mastery du; test oscillation: difficulty khong dao lien tuc | **P0** |
| LI-03 | Retry flow | Retry phai giup **hoc lai**, khong phai chi lap lai cau cu. Supplementary content phai xuat hien truoc khi retry; retry sau supplementary moi co gia tri | RETRY-001..003; LI-F04 test: sau retry thanh cong -> quay lai luong chinh | **P1** |
| LI-04 | Explainability | Moi intervention (alert, pathway change, difficulty change) phai **giai thich duoc ly do** bang ngon ngu con nguoi doc duoc | EW-008..009; AP-02; LI-F06 test: alert.reason khong rong va khong phai error code | **P1** |
| LI-05 | Human override | Giang vien **luon co quyen** dismiss alert, override pathway, tao intervention. He thong khong tu dong hanh dong ma khong cho GV co hoi can thiep | ALERT-002: dismiss voi note; ACTION-001..004: 3 action types; RBAC: GV co quyen action | **P1** |
| LI-06 | Psychological safety | Khong duoc "dan nhan yeu" theo cach gay hai tam ly. Dung "can bo sung" thay "yeu/kem"; dung "gap kho khan" thay "that bai"; severity chi hien icon + text, khong chi mau do | FE-026: copy check; FE-021: severity icon+text; trigger_labels test: no judgmental words | **P2** |

#### 1.5.2. 6 dieu kien fail nghiem trong (Learning Integrity Failures)

| # | Dieu kien fail | Mo ta cu the | Hau qua | Test case | Muc do |
|---|---------------|-------------|---------|-----------|--------|
| LI-F01 | Chen bo tro sai concept | Supplementary content.concept != mastery_state.concept dang yeu | SV hoc sai kien thuc, mat thoi gian, tang hoang mang | `test_learning_integrity.py::TestLIF01WrongConceptIntervention` | **P0** |
| LI-F02 | Tang do kho khi mastery chua du | advance concept hoac difficulty_adjustment=+1 khi P(mastery) < MASTERY_HIGH | SV bi qua tai, mat dong luc, mastery that bai | `test_learning_integrity.py::TestLIF02PrematureDifficultyIncrease` | **P0** |
| LI-F03 | Gan co "can ho tro" sai hang loat | >=3 SV binh thuong bi RED/YELLOW trong cung batch, do bug logic | GV mat tin, can thiep sai, SV bi phien | `test_learning_integrity.py::TestLIF03MassFalseFlagging` | **P0** |
| LI-F04 | Khong cho quay lai luong chinh | SV da hoi phuc (P(mastery) tang tren 0.60 sau retry) nhung he thong van giu o luong supplement | SV bi ket trong vong lap bo tro, mat tien do | `test_learning_integrity.py::TestLIF04NoReturnToMainFlow` | **P0** |
| LI-F05 | Progress gia | progress_pct hoac mastery display cao hon thuc te (do double-count hoac tinh sai) | SV tuong da dat -> khong co gang them -> thi rot | `test_learning_integrity.py::TestLIF05InflatedProgress` | **P1** |
| LI-F06 | Canh bao khong ly do | Alert.reason rong, null, hoac la error code/JSON dump thay vi human-readable text | GV khong hieu canh bao, khong hanh dong duoc | `test_learning_integrity.py::TestLIF06AlertWithoutReason` | **P1** |

#### 1.5.3. Mapping Learning Integrity -> QA Layers va Go/No-Go

| LI failure | QA Layer | Blocker | No-Go |
|-----------|---------|---------|-------|
| LI-F01 Wrong concept | L2 (logic hoc tap) | B6 | NG-01 |
| LI-F02 Premature difficulty | L2 | B6 | NG-01 |
| LI-F03 Mass false flagging | L2 | B6 | NG-01 |
| LI-F04 No return path | L1 + L2 | B1 (P0) | NG-02 |
| LI-F05 Inflated progress | L3 + L6 | B7 | NG-06 |
| LI-F06 No reason | L2 | B6 | NG-01 |

**Nguyen tac**: Neu bat ky LI-F nao con ton tai -> **NO-GO tuyet doi**, vi day la loi **gay hai truc tiep den sinh vien va giang vien**.

### 1.6. Core Feature Quality Standards

Day la tieu chuan **cap chuc nang cot loi**, ap dung cho 5 feature chinh cua MVP. Moi feature co **release criteria rieng** -- tat ca phai PASS truoc khi release.

#### 1.6.1. F1 -- Assessment dau vao

PRD: 15-20 cau, <=15 phut, save giua chung, lam lai lay lan moi nhat, >=90% hoan thanh khong ho tro, thoi gian TB <12 phut.

| # | Tieu chi | Chuan | Test ref |
|---|---------|-------|----------|
| F1-01 | 0 mat du lieu giua chung | Save progress phai persist qua tab close, network loss, refresh | ASSESS-006, AP-03, AS-02 |
| F1-02 | 0 duplicate submission | Cung session khong duoc submit 2 lan -> 400 hoac idempotent | ASSESS-007, ASSESS-008, AP-04 |
| F1-03 | 0 sai score | Score = correct / total * 100, khong sai so | ASSESS-003, `test_feature_criteria.py::TestF1Assessment` |
| F1-04 | 0 sai mapping profile | LearnerProfile.strengths/weaknesses chi chua concept IDs ton tai | ASSESS-004, ASSESS-005, DI-08 |
| F1-05 | Resume dung vi tri | Sau mat mang, SV quay lai dung cau da tra loi cuoi | ASSESS-006, AS-02 |
| F1-06 | 2 tab cung luc -> 1 ket qua | Start session tren tab 2 khi tab 1 dang lam -> reject hoac reuse | ASSESS-007, `test_feature_criteria.py::TestF1Assessment` |
| F1-07 | Deadline 15p nhat quan FE/BE | Timer FE va server-side timeout phai dong bo (sai so <=5s) | ASSESS-010, `test_feature_criteria.py::TestF1Assessment` |
| F1-08 | Moi lan nop co audit trail | Event assessment_completed fire voi score, time_taken | EC-03, EVT-005, ACTION-002 |

**Release criteria F1**: 100% save/resume pass, 100% multiple-submit pass, 100% timeout pass, 100% ownership pass, p95 submit < 800ms, 0 P1 score/persistence.

#### 1.6.2. F2 -- Adaptive Pathway v1

PRD: Rule-based + BKT, response <3s, xu ly guess probability, sync state offline.

| # | Tieu chi | Chuan | Test ref |
|---|---------|-------|----------|
| F2-01 | BKT deterministic | Cung input -> cung output, moi lan | PATH-004, BKT-001..008 |
| F2-02 | Rule engine versioned | ContentIntervention luu rule version, pathway co version tracking | `test_feature_criteria.py::TestF2Adaptive` |
| F2-03 | Intervention day du metadata | Moi intervention luu: concept_id, reason, trigger_rule, mastery_before, mastery_after | `test_feature_criteria.py::TestF2Adaptive` |
| F2-04 | Khong lap intervention >2 lan lien tiep | Neu cung loai intervention xay ra >2 lan ma khong co learning gain -> escalate hoac doi loai | `test_feature_criteria.py::TestF2Adaptive` |
| F2-05 | Khong loop vo han | Sai -> video -> sai -> video khong vuot qua MAX_RETRY (default 5) | RETRY-001..003, LI-F04, `test_feature_criteria.py::TestF2Adaptive` |
| F2-06 | SV luon thay ly do chuyen noi dung | pathway response co message giai thich | PATH-001..003, LI-04, AP-02 |

**Release criteria F2**: 100% rule branch pass, 100% retry/recovery pass, p95 adaptive <1.5s, p99 <2.5s, 0 wrong-concept, 0 progress corruption, 0 orphan state.

#### 1.6.3. F3 -- Backward Design Dashboard

PRD: 5-10 milestones, 3-5 micro-tasks/milestone, flexible ordering, phan hoi <1s.

| # | Tieu chi | Chuan | Test ref |
|---|---------|-------|----------|
| F3-01 | Progress tinh tu du lieu, khong suy dien | progress_pct = completed_tasks / total_tasks, tinh tu DB | `test_feature_criteria.py::TestF3BackwardDesign` |
| F3-02 | Task completion idempotent | Submit cung task 2 lan -> attempt_number tang, completion khong double-count | RETRY-003, AP-04, DI-04 |
| F3-03 | Milestone chi complete khi du tasks | Milestone status = completed chi khi tat ca tasks con da completed | `test_feature_criteria.py::TestF3BackwardDesign` |
| F3-04 | Partial completion co trang thai rieng | in_progress vs completed vs not_started phan biet ro | `test_feature_criteria.py::TestF3BackwardDesign` |
| F3-05 | Khong mat thanh tuu sau refresh | Refresh/doi thiet bi -> progress van dung | AP-03, ASSESS-006 |
| F3-06 | 0 progress sai | Khong double-count, khong am, khong >100% | LI-F05, AP-04 |

**Release criteria F3**: 100% milestone math pass, 100% reorder logic pass, 0 double-count/negative/>100%, p95 progress update <500ms.

#### 1.6.4. F4 -- Dashboard giang vien / Early Warning

PRD: Phan nhom X/V/D, canh bao inactive >=3 ngay hoac mastery giam manh, dismiss + action.

| # | Tieu chi | Chuan | Test ref |
|---|---------|-------|----------|
| F4-01 | Alert co day du 5 truong | danh tinh (dung quyen), ly do, timestamp, evidence snapshot, trang thai xu ly | EW-008, LI-F06, `test_feature_criteria.py::TestF4Dashboard` |
| F4-02 | Dismiss phai co reason | dismiss_note khong rong khi dismiss | ALERT-002, `test_feature_criteria.py::TestF4Dashboard` |
| F4-03 | Action GV co audit | Moi intervention tao event gv_action_taken + ghi InterventionAction | ACTION-002, ACTION-004 |
| F4-04 | Khong false alert tu stale data | Alert chi dua tren du lieu moi nhat, khong dung cache cu qua 24h | LI-F03, EW-003, EW-006 |
| F4-05 | Chua du du lieu -> UI noi ro | data_sufficient=false -> hien "Dang thu thap du lieu" | DASH-001, `test_feature_criteria.py::TestF4Dashboard` |
| F4-06 | 0 cross-class leak | GV chi thay SV trong class minh | RBAC-004, ALERT-003, NG-03 |

**Release criteria F4**: 100% RBAC pass, 100% evidence rendering pass, UAT precision >=80%, 0 cross-class leak, 0 stale alert.

#### 1.6.5. F5 -- Data Cleaning Pipeline

PRD: KNN imputation, Z-score/IQR, outlier tach review, sensitivity analysis MNAR, ETL hoc vu 3 ky.

| # | Tieu chi | Chuan | Test ref |
|---|---------|-------|----------|
| F5-01 | Moi run co metadata day du | run_id, input_version, output_version, checksum, schema_snapshot | ETL-001, `test_feature_criteria.py::TestF5Pipeline` |
| F5-02 | Khong silent coercion | Type mismatch -> loi ro rang, khong tu ep kieu | `test_feature_criteria.py::TestF5Pipeline` |
| F5-03 | >50% missing -> exclude dung rule | Column co >50% missing bi flag hoac excluded | DC-03, imputation.py HIGH_MISSING_THRESHOLD |
| F5-04 | Outlier khong silently drop | Outlier duoc flag va dua vao review queue, khong bi xoa | DC-04, detect_outliers -> review_queue |
| F5-05 | Reproducible | Cung input + cung seed -> cung output checksum | DC-05, pipeline compute_df_checksum |
| F5-06 | Fail giua chung -> khong tao output "nua sach nua ban" | Pipeline dung atomic transaction, fail -> status=FAILED, khong co partial output | `test_feature_criteria.py::TestF5Pipeline` |

**Release criteria F5**: 100% schema validation pass, 100% duplicate key detection pass, 100% outlier queue pass, 100% reproducibility pass, 0 silent corruption, 0 run thieu report.

### 1.7. Test Strategy tong the -- Test Pyramid

PALP la san pham EdTech anh huong truc tiep den learning outcomes. Test strategy phai **cao hon** muc thong thuong -- khong chi dam bao "khong crash" ma dam bao **khong dua ra quyet dinh sai ve hoc tap**.

#### 1.7.1. Test Pyramid -- 9 lop

```
                    +-------+
                    |  UAT  |  Hanh vi that SV+GV (>= 90% task success)
                   +--------+
                  | Recovery |  Backup/restore/retry/rollback (100% pass)
                 +----------+
                | Data QA    |  ETL, analytics, BKT bounds (100% pass)
               +------------+
              |    Load      |  Performance + stability (pass SLO)
             +--------------+
            |   Security     |  Auth/AuthZ/OWASP (100% pass)
           +----------------+
          |      E2E         |  7 core journeys + privacy (100% pass)
         +------------------+
        |     Contract       |  Schema request/response/error (100% API)
       +--------------------+
      |    Integration       |  API + DB + cache + queue + ETL (100% core)
     +----------------------+
    |        Unit            |  Logic, BKT, rules, pure functions (>= 90% core)
    +------------------------+
```

#### 1.7.2. Nguong bat buoc theo lop

| # | Lop test | Muc tieu | Nguong | CI stage | Implementation |
|---|---------|---------|--------|----------|----------------|
| TP-01 | Unit | Logic nho, pure functions, BKT math, pathway rules, scoring | **>= 90% coverage core** (assessment, adaptive, dashboard, accounts) | PR Gate | `pytest -m "not integration..."`, per-app `tests/` |
| TP-02 | Integration | API + DB + cache + queue + ETL, cross-app flows | **100% core endpoint co test** | Pre-merge | `pytest -m integration`, `tests/integration/` |
| TP-03 | Contract | Schema request/response, error codes, OpenAPI diff | **100% public API** | PR Gate | `pytest -m contract`, `tests/contract/`, `oasdiff` |
| TP-04 | E2E | Hanh trinh nguoi dung toan bo (FE + BE) | **100% core journeys pass** (J1-J7) | Pre-merge | `npm run test:e2e`, `e2e/journeys/` |
| TP-05 | Security | Auth, AuthZ, RBAC matrix, injection, IDOR, OWASP | **100% pass** | Pre-merge | `pytest -m security`, `tests/security/` |
| TP-06 | Load | Performance, stability, SLO compliance | **Pass SLO** (Section 8.1) | Pre-release | Locust, `tests/load/`, `slo_assertions.py` |
| TP-07 | Data QA | ETL pipeline, BKT bounds, event completeness, KPI integrity | **100% pass** | Pre-merge | `pytest -m data_qa`, `tests/data_qa/` |
| TP-08 | Recovery | Backup/restore, rollback, cache failure, worker restart | **100% pass** | Pre-release | `pytest -m recovery`, `tests/recovery/` |
| TP-09 | UAT | Hanh vi that cua SV va GV trong moi truong staging | **>= 90% task success**, SUS >= 80 | Pre-release | UAT_SCRIPT.md, 2 vong, 15 tasks |

#### 1.7.3. Cross-cutting test concerns

| # | Concern | Ap dung cho | Verify bang |
|---|---------|------------|------------|
| TC-01 | Product correctness (AP-01..05) | Integration, E2E | `test_product_correctness.py` |
| TC-02 | Learning integrity (LI-F01..06) | Integration | `test_learning_integrity.py` |
| TC-03 | Feature criteria (F1-F5) | Integration | `test_feature_criteria.py` |
| TC-04 | Privacy hardened (PP, PRG) | Integration | `test_privacy_hardened.py` |
| TC-05 | Security hardened (SG, SK) | Security | `test_security_hardened.py` |
| TC-06 | Observability (OB, OD) | Integration | `test_observability.py` |
| TC-07 | Event completeness (EC) | Unit | `test_event_completeness.py` |
| TC-08 | Data cleaning (DC) | Data QA | `test_data_cleaning.py` |

#### 1.7.4. Test execution order va dependencies

```
PR Gate (moi PR, block merge):
  Unit tests ──> Coverage gates ──> Contract tests ──> OpenAPI diff
                                                           |
Pre-merge (sau approve, block merge):                      v
  Integration ──> E2E journeys ──> Security ──> Data QA ──> Docker build
                                                                |
Pre-release (manual trigger, block release):                    v
  Full regression ──> Load test ──> Recovery ──> Security checklist
       |                                              |
       v                                              v
  Backup/restore drill ──> Privacy checklist ──> UAT (2 vong)
                                                      |
                                                      v
                                           Go/No-Go decision gate
                                                      |
                                                      v
Post-deploy:                                    Deploy staging/prod
  Smoke test ──> Sentry verify ──> Notify team
```

#### 1.7.5. Test data strategy

| Moi truong | Data source | Quan ly boi |
|-----------|-------------|-------------|
| Unit tests | In-memory DB (SQLite), factory fixtures (`conftest.py`) | Dev |
| Integration | PostgreSQL test DB, seeded fixtures | Dev + CI |
| E2E | Staging DB, seeded via `scripts/seed_data.py` | DevOps |
| Load | Staging DB, 50-200 simulated users (Locust profiles) | QA |
| UAT | Staging DB, 20-30 SV that + 2-3 GV that | PO + QA |

#### 1.7.6. Tong hop so luong test

| Lop | So test cases/files | Marker/tag |
|-----|--------------------|-----------| 
| Unit | ~170 cases (per-app `tests/`) | default (no marker) |
| Integration | ~80 cases (`tests/integration/`, cross-cutting) | `@pytest.mark.integration` |
| Contract | ~217 cases (`tests/contract/`) | `@pytest.mark.contract` |
| E2E | 8 journey specs + 7 feature specs | Playwright `e2e/` |
| Security | ~40 cases (`tests/security/`) | `@pytest.mark.security` |
| Load | 6 scenarios (Locust) | `@pytest.mark.load` |
| Data QA | ~30 cases (`tests/data_qa/`) | `@pytest.mark.data_qa` |
| Recovery | ~15 cases (`tests/recovery/`) | `@pytest.mark.recovery` |
| Frontend unit | 7 test files (Vitest) | `src/**/*.test.ts` |
| **Tong backend** | **~550 cases** | |
| **Tong FE** | **~60 cases (unit) + ~80 cases (E2E)** | |
| **Grand total** | **~690 cases** | |

---

## 2. Mo hinh phan cap loi va nguong pass/fail

### 2.1. Phan cap loi (Bug Severity)

| Muc | Ten | Dinh nghia | Vi du cu the trong PALP |
|-----|-----|-----------|------------------------|
| P0 | Blocker | Khong the pilot / khong the demo / gay rui ro nghiem trong | He thong khong start duoc; mat toan bo du lieu SV; lo PII ra ngoai |
| P1 | Critical | Chuc nang cot loi chay nhung sai logic, sai du lieu hoac sai phan quyen | BKT tinh sai P(mastery); SV thay du lieu cua SV khac; early warning phan loai sai Red/Yellow; assessment scoring sai |
| P2 | Major | Co workaround nhung anh huong manh den trai nghiem, do tin cay hoac KPI | Dashboard load >10s; event khong duoc tracking; retry logic khong nhat quan; nudge khong xuat hien |
| P3 | Minor | Loi nho, wording, UI lech nhe, khong anh huong quyet dinh hoc tap | Sai chinh ta tren label; icon lech 2px; tooltip khong hien |
| P4 | Cosmetic | Tham my, format, spacing | Font size khong dong deu; shadow khong nhat quan; margin thua |

### 2.2. Dieu kien tuyet doi -- KHONG DUOC RELEASE neu con bat ky loi nao sau:

| # | Dieu kien blocker | Lop | Module lien quan |
|---|-------------------|-----|-----------------|
| B1 | >= 1 loi P0 | L1-L6 | Bat ky |
| B2 | >= 1 loi P1 trong module core | L1, L2 | assessment, adaptive, dashboard |
| B3 | >= 1 loi security high/critical | L4 | accounts, RBAC, TLS |
| B4 | >= 1 loi privacy chua xu ly | L4 | consent flow, pseudonymization |
| B5 | >= 1 loi mat du lieu | L3 | PostgreSQL, migration, backup |
| B6 | >= 1 loi sai logic adaptive / early warning / progress | L2 | adaptive/engine.py, dashboard/services.py |
| B7 | >= 1 loi khong do duoc KPI hoac event core | L6 | events/, analytics/ |
| B8 | Backup/restore drill that bai | L5 | PostgreSQL, Docker |
| B9 | Health endpoint khong respond trong 30s sau deploy | L5 | /api/health/ |

### 2.3. Ty le pass bat buoc

| Nhom test | Nguong toi thieu | Ghi chu |
|-----------|-----------------|---------|
| P0 test cases | **100% pass** | Zero tolerance |
| P1 test cases | **100% pass** | Zero tolerance |
| P2 test cases | **>= 95% pass** | Loi con lai phai co workaround va duoc PO accept |
| Unit tests core logic | **>= 90% coverage** | Do tren `assessment/`, `adaptive/`, `dashboard/`, `accounts/` |
| API integration tests core | **100% endpoint core co test** | Moi endpoint trong API.md co it nhat happy path + error cases |
| E2E core journeys | **100% pass** | 7 journey duoc dinh nghia o Section 4 |
| Security critical checklist | **100% pass** | 15 hang muc o Section 7 |
| Data QA checks | **100% pass** | 12 hang muc o Section 6 |
| Backup/restore drill | **100% pass** | Backup -> destroy -> restore -> verify |
| Performance SLA | **100% dat nguong** | Moi metric o Section 8 |

### 2.4. Quy trinh xu ly loi theo muc do

```
P0 Blocker:
  -> Dung sprint ngay lap tuc
  -> Dev fix trong 4h (gio lam viec)
  -> QA re-verify trong 2h sau fix
  -> Khong merge bat ky PR nao khac cho den khi P0 = 0

P1 Critical:
  -> Uu tien cao nhat trong sprint hien tai
  -> Dev fix trong 24h
  -> QA re-verify trong 4h sau fix
  -> Khong release cho den khi P1 core = 0

P2 Major:
  -> Len ke hoach fix trong sprint hien tai hoac sprint ke tiep
  -> PO quyet dinh co can workaround tam thoi hay khong
  -> Neu >5% P2 fail -> review lai voi PO truoc release

P3-P4:
  -> Ghi nhan vao backlog
  -> Fix khi co bandwidth
  -> Khong block release
```

---

## 3. Test Strategy by Module

### 3.1. accounts (Auth & RBAC)

**Scope**: JWT auth, user model, RBAC 3 roles, consent flow, class management

| Test Group | Mo ta | Loai | Muc do |
|-----------|-------|------|--------|
| AUTH-001 | Login thanh cong voi username/password hop le | Unit + API | P0 |
| AUTH-002 | Login that bai voi sai password -> 401 | API | P0 |
| AUTH-003 | Login that bai voi user khong ton tai -> 401 | API | P1 |
| AUTH-004 | Access protected endpoint khong co token -> 401 | API | P0 |
| AUTH-005 | Access protected endpoint voi token het han -> 401 | API | P0 |
| AUTH-006 | Refresh token thanh cong | API | P0 |
| AUTH-007 | Refresh voi token da revoke -> 401 | API | P1 |
| AUTH-008 | Register user moi thanh cong | API | P1 |
| AUTH-009 | Register voi username trung -> 400 | API | P1 |
| RBAC-001 | Student KHONG truy cap duoc dashboard alerts | API | P0 |
| RBAC-002 | Student KHONG truy cap duoc analytics/KPI | API | P0 |
| RBAC-003 | Student KHONG truy cap duoc student list cua class | API | P0 |
| RBAC-004 | Lecturer CHI thay SV trong class duoc assign | API | P0 |
| RBAC-005 | Lecturer KHONG truy cap duoc user management | API | P1 |
| RBAC-006 | Admin co full access | API | P1 |
| RBAC-007 | RBAC matrix 23 to hop role x resource deu dung | API | P0 |
| CONSENT-001 | User chua consent -> du lieu hoc tap KHONG duoc thu thap | API + Integration | P0 |
| CONSENT-002 | Consent flow luu dung consent_given va consent_given_at | Unit | P1 |
| CONSENT-003 | Rut consent -> du lieu moi KHONG duoc thu thap | API | P1 |

### 3.2. assessment (Entry Assessment)

**Scope**: Assessment lifecycle, scoring, LearnerProfile, save progress, timer

| Test Group | Mo ta | Loai | Muc do |
|-----------|-------|------|--------|
| ASSESS-001 | Start assessment tao session voi status in_progress | API | P0 |
| ASSESS-002 | Submit answer luu dung question_id, answer, time_taken_seconds | API | P0 |
| ASSESS-003 | Complete assessment tinh diem dung (so correct / total * 100) | Unit + API | P0 |
| ASSESS-004 | Complete assessment tao LearnerProfile voi strengths/weaknesses dung | Unit | P0 |
| ASSESS-005 | LearnerProfile.initial_mastery map dung concept -> score | Unit | P0 |
| ASSESS-006 | Save progress -- dong tab va quay lai, cau da tra loi van con | API + E2E | P1 |
| ASSESS-007 | Khong cho start 2 session cung luc cho 1 assessment | API | P1 |
| ASSESS-008 | Complete assessment da completed -> 400 | API | P1 |
| ASSESS-009 | Answer cau da tra loi -> xu ly dung (overwrite hoac reject) | API | P1 |
| ASSESS-010 | Timer do thoi gian tra loi tung cau chinh xac (sai so <=2s) | Unit + E2E | P2 |
| ASSESS-011 | Assessment 15-20 cau, hoan thanh <=15 phut (do duoc) | E2E | P2 |
| ASSESS-012 | >=90% SV hoan thanh khong can ho tro (do tu UAT) | UAT | P1 |

**Assessment Edge-case Matrix (AS-01..AS-10):**

| ID | Tinh huong | Ky vong | Test ref | Muc do |
|----|-----------|--------|----------|--------|
| AS-01 | SV vao lan dau | Assessment mo dung, timer dung | ASSESS-001, FE-004 | P0 |
| AS-02 | Reload giua bai | State giu nguyen | ASSESS-006, `assessment-edge-cases.spec.ts` | P1 |
| AS-03 | Mat mang giua bai | Luu cuc bo / retry sync dung | `assessment-edge-cases.spec.ts` | P1 |
| AS-04 | Nop dung luc het gio | Chi 1 ket qua hop le, khong duplicate | `test_module_edge_cases.py::TestAS04TimeoutSubmit` | P1 |
| AS-05 | 2 tab cung nop | Chi 1 ban ghi canonical | ASSESS-007, F1-06 | P1 |
| AS-06 | Lam lai assessment | Ban moi nhat thang, ban cu archived | `test_module_edge_cases.py::TestAS06Retake` | P1 |
| AS-07 | Chuyen thiet bi giua chung | Resume dung neu policy cho phep | `test_module_edge_cases.py::TestAS07CrossDevice` | P2 |
| AS-08 | Token het han giua bai | Re-auth khong mat du lieu | `test_module_edge_cases.py::TestAS08TokenExpiry` | P1 |
| AS-09 | Cau keo-tha sai format | Khong crash, bao loi dung | `assessment-edge-cases.spec.ts` | P2 |
| AS-10 | Role GV truy cap endpoint SV submit | Bi chan dung | RBAC tests, `test_authz_matrix.py` | P0 |

### 3.3. adaptive (BKT Engine & Pathway)

**Scope**: BKT math, pathway decision rules, mastery state, cache, retry logic

**DAY LA MODULE QUAN TRONG NHAT VE LOGIC HOC TAP. SAI O DAY = SAI CAN THIEP SU PHAM.**

| Test Group | Mo ta | Loai | Muc do |
|-----------|-------|------|--------|
| BKT-001 | P(L\|correct) tinh dung theo cong thuc BKT | Unit | P0 |
| BKT-002 | P(L\|wrong) tinh dung theo cong thuc BKT | Unit | P0 |
| BKT-003 | P(L_new) cap nhat dung voi P(T) | Unit | P0 |
| BKT-004 | Golden vector: 5 cau lien tuc dung -> P(mastery) tang dan monotonic | Unit | P0 |
| BKT-005 | Golden vector: 5 cau lien tuc sai -> P(mastery) khong tang (hoac tang rat cham do P(T)) | Unit | P0 |
| BKT-006 | Golden vector: pattern [D,D,S,D,D] -> P(mastery) phu hop | Unit | P0 |
| BKT-007 | BKT params luon trong [0,1]: P(mastery), P(guess), P(slip), P(transit) | Unit | P0 |
| BKT-008 | BKT khong tra ve NaN, Infinity, hoac gia tri am | Unit | P0 |
| PATH-001 | P(mastery) < 0.60 -> chen noi dung bo tro, difficulty -1 | Unit + API | P0 |
| PATH-002 | 0.60 <= P(mastery) <= 0.85 -> continue, difficulty 0 | Unit + API | P0 |
| PATH-003 | P(mastery) > 0.85 -> advance, difficulty +1 | Unit + API | P0 |
| PATH-004 | Pathway decision nhat quan giua 2 lan goi voi cung input | Unit | P1 |
| CACHE-001 | MasteryState duoc cache trong Redis voi key mastery:{student_id}:{concept_id} | Integration | P1 |
| CACHE-002 | Cache bi invalidate sau moi BKT update | Integration | P1 |
| CACHE-003 | Cache miss -> query DB -> tra ve dung -> cache lai | Integration | P2 |
| RETRY-001 | Task fail -> supplementary content duoc hien thi | API + E2E | P0 |
| RETRY-002 | Retry sau supplementary -> BKT update binh thuong | API | P1 |
| RETRY-003 | attempt_number tang dung sau moi retry | Unit | P1 |
| SUBMIT-001 | Submit task -> tra ve attempt + mastery + pathway response day du | API | P0 |
| SUBMIT-002 | Submit task voi is_correct=true -> mastery tang | API | P0 |
| SUBMIT-003 | Submit task voi is_correct=false -> pathway.action co the la "supplement" | API | P0 |

**Adaptive Edge-case Matrix (AD-01..AD-10):**

| ID | Tinh huong | Ky vong | Test ref | Muc do |
|----|-----------|--------|----------|--------|
| AD-01 | Dung lien tiep 5 cau | Do kho tang dung rule | BKT-004, PATH-003 | P0 |
| AD-02 | Sai 2 cau lien tiep cung concept | Chen intervention dung | PATH-001, LI-F01 | P0 |
| AD-03 | Sai 2 cau o 2 concept khac nhau | Flag dung concept yeu nhat | `test_module_edge_cases.py::TestAD03MultiConcept` | P1 |
| AD-04 | Doan mo dung | Guess probability xu ly dung (P(guess) < 0.5) | BKT-007, `test_bkt_property.py` | P1 |
| AD-05 | Offline truoc intervention | State luu, resume dung | `test_module_edge_cases.py::TestAD05OfflineResume` | P1 |
| AD-06 | Retry xong dung | Quay lai luong chinh | LI-F04, J3 | P0 |
| AD-07 | Retry sai lan 3 | Tao alert GV | EW-004, `test_module_edge_cases.py::TestAD07RetryAlert` | P0 |
| AD-08 | 2 request song song cap nhat mastery | Khong race condition | `test_module_edge_cases.py::TestAD08ConcurrentMastery` | P1 |
| AD-09 | Rule version doi giua session | Session dang chay khong hong | `test_module_edge_cases.py::TestAD09RuleVersionChange` | P2 |
| AD-10 | Intervention content missing | Co fallback an toan | `test_module_edge_cases.py::TestAD10InterventionFallback` | P1 |

### 3.4. curriculum (Course Structure)

**Scope**: Course/concept/milestone/task CRUD, prerequisite graph, content schema

| Test Group | Mo ta | Loai | Muc do |
|-----------|-------|------|--------|
| CURR-001 | List courses tra ve cac course active | API | P1 |
| CURR-002 | Concept co order dung va thuoc dung course | Unit | P1 |
| CURR-003 | ConceptPrerequisite khong co circular dependency | Unit | P1 |
| CURR-004 | Milestone.concepts M2M lien ket dung | Unit | P1 |
| CURR-005 | MicroTask.content JSONField co schema hop le (question, options, correct_answer) | Unit | P1 |
| CURR-006 | MicroTask thuoc dung milestone va concept | Unit | P1 |
| CURR-007 | SupplementaryContent lien ket dung concept | Unit | P2 |
| CURR-008 | Seed data 10 concepts voi prerequisites cho SBVL load thanh cong | Integration | P1 |
| CURR-009 | Filter tasks theo milestone va concept hoat dong dung | API | P2 |
| CURR-010 | Enrollment chi cho phep student enroll course active | API | P2 |

**Backward Design Edge-case Matrix (BD-01..BD-10):**

| ID | Tinh huong | Ky vong | Test ref | Muc do |
|----|-----------|--------|----------|--------|
| BD-01 | Complete 1 task | Progress tang dung | F3-01 | P0 |
| BD-02 | Click hoan thanh 2 lan | Khong double-count | F3-02, AP-04 | P0 |
| BD-03 | Task done roi refresh | State giu dung | AP-03 | P1 |
| BD-04 | Hoan thanh milestone khong theo thu tu | He thong cho phep neu policy cho phep | `test_module_edge_cases.py::TestBD04FlexOrder` | P2 |
| BD-05 | GV doi template giua chung | Mapping state dung | `test_module_edge_cases.py::TestBD05TemplateMigration` | P2 |
| BD-06 | 2 thiet bi cung thao tac | Khong conflict pha progress | `test_module_edge_cases.py::TestBD06ConcurrentProgress` | P2 |
| BD-07 | Undo/mark incomplete | Progress rollback dung | `test_module_edge_cases.py::TestBD07ProgressRollback` | P2 |
| BD-08 | Task khoa truoc dieu kien | Khong truy cap duoc | CURR-003 (prereqs), `test_module_edge_cases.py::TestBD08Prerequisites` | P1 |
| BD-09 | Milestone xong nhung task con chua du | Khong danh dau sai | F3-03 | P0 |
| BD-10 | Progress >100% hoac am | Khong bao gio xay ra | F3-06, LI-F05 | P0 |

### 3.5. dashboard (Early Warning & Intervention)

**Scope**: Nightly batch, alert triggers, severity classification, action log

**SAI LOGIC O DAY = GV NHAN CANH BAO SAI -> CAN THIEP SAI -> HAI SV.**

| Test Group | Mo ta | Loai | Muc do |
|-----------|-------|------|--------|
| EW-001 | Inactivity >= 5 ngay -> alert RED | Unit + Integration | P0 |
| EW-002 | Inactivity 3-4 ngay -> alert YELLOW | Unit + Integration | P0 |
| EW-003 | Inactivity < 3 ngay -> KHONG tao alert | Unit | P0 |
| EW-004 | Retry failures >= 3 tren cung concept -> alert RED | Unit + Integration | P0 |
| EW-005 | Milestone progress tut hau dang ke so voi peers -> alert YELLOW | Unit | P1 |
| EW-006 | SV binh thuong -> GREEN (khong tao alert) | Unit | P0 |
| EW-007 | Nightly batch (Celery) chay thanh cong va tao alerts dung | Integration | P0 |
| EW-008 | Alert co day du: severity, trigger_type, reason, evidence, suggested_action | Unit | P1 |
| EW-009 | reason la human-readable, giai thich duoc logic (Explainable) | Unit | P1 |
| ALERT-001 | List alerts filter theo class_id, severity, status | API | P1 |
| ALERT-002 | Dismiss alert luu dismiss_note va chuyen status | API | P1 |
| ALERT-003 | GV chi thay alerts cua SV trong class minh | API | P0 |
| ACTION-001 | Tao intervention (send_message / suggest_task / schedule_meeting) | API | P1 |
| ACTION-002 | Intervention tao event gv_action_taken | Integration | P1 |
| ACTION-003 | Follow-up status update hoat dong dung | API | P2 |
| ACTION-004 | Intervention history ghi day du who, when, what | API | P1 |
| DASH-001 | Overview tra ve dung: total, on_track, needs_attention, needs_intervention | API | P0 |
| DASH-002 | Overview load < 3s voi Redis cache | Performance | P1 |

**Dashboard GV Edge-case Matrix (GV-01..GV-10):**

| ID | Tinh huong | Ky vong | Test ref | Muc do |
|----|-----------|--------|----------|--------|
| GV-01 | Lop moi chua co data | Hien "Dang thu thap du lieu" | F4-05, `dashboard-edge-cases.spec.ts` | P1 |
| GV-02 | 5 SV inactive 3 ngay | Sinh canh bao dung | EW-001, EW-002 | P0 |
| GV-03 | Mastery giam manh | Flag dung | EW low_mastery | P0 |
| GV-04 | SV nghi phep hop le | Khong flag sai hoac dismiss duoc | `test_module_edge_cases.py::TestGV04LegitimateAbsence` | P2 |
| GV-05 | GV mo lop khac | Bi chan | RBAC, SK-01, `dashboard-edge-cases.spec.ts` | P0 |
| GV-06 | Dismiss alert | Ghi audit + reason | ALERT-002 | P1 |
| GV-07 | Gui tin nhan can thiep | Luu action dung | ACTION-001 | P1 |
| GV-08 | Hanh dong xong do lai sau 1 tuan | Dashboard cap nhat dung | `test_module_edge_cases.py::TestGV08FollowUp` | P2 |
| GV-09 | Alert job chay lai | Khong sinh duplicate alert | LI-F03, `test_early_warning.py::TestInactivityAlert::test_no_duplicate_alerts` | P0 |
| GV-10 | Data stale 24h | UI phai noi ro last updated | `dashboard-edge-cases.spec.ts` | P2 |

### 3.6. analytics (KPI & Reporting)

**Scope**: KPI computation, data quality, weekly reports, nightly batch

| Test Group | Mo ta | Loai | Muc do |
|-----------|-------|------|--------|
| KPI-001 | Active learning time/week tinh dung tu session events | Unit | P1 |
| KPI-002 | Micro-task completion rate tinh dung | Unit | P1 |
| KPI-003 | GV dashboard usage tinh dung tu page_view events | Unit | P1 |
| KPI-004 | Time to detect struggling students tinh duoc | Unit | P2 |
| KPI-005 | 5 KPIs deu co gia tri, khong null/NaN | Unit | P1 |
| REPORT-001 | Weekly report generate thanh cong (Celery beat Sunday) | Integration | P1 |
| REPORT-002 | Report W4 va W10 co day du so lieu doi chieu | Integration | P2 |
| DQ-001 | Data quality score >= 70% | Integration | P1 |
| DQ-002 | Missing data classification hoat dong (MCAR/MAR/MNAR) | Unit | P2 |
| DQ-003 | KNN imputation cho MAR chay dung | Unit | P2 |
| DQ-004 | Z-score/IQR outlier screening phat hien outlier | Unit | P2 |
| ETL-001 | ETL script chay end-to-end khong loi | Integration | P1 |

### 3.7. events (Event Tracking)

**Scope**: Event taxonomy, batch ingestion, schema validation

| Test Group | Mo ta | Loai | Muc do |
|-----------|-------|------|--------|
| EVT-001 | Track single event luu dung event_name, properties, session_id, device | API | P1 |
| EVT-002 | Batch track nhieu events cung luc | API | P1 |
| EVT-003 | Event taxonomy -- 8 event types deu co the fire va persist | Integration | P0 |
| EVT-004 | session_started va session_ended tracking dung | Integration | P1 |
| EVT-005 | micro_task_completed event fire khi submit task | Integration | P1 |
| EVT-006 | gv_action_taken event fire khi GV tao intervention | Integration | P1 |
| EVT-007 | wellbeing_nudge_shown event fire khi nudge hien | Integration | P1 |
| EVT-008 | Event khong duplicate (cung event_name + timestamp + user trong 1s) | Unit | P2 |
| EVT-009 | Event properties validate schema (khong nhan arbitrary data) | Unit | P2 |
| EVT-010 | Student chi xem duoc event cua minh, Lecturer xem duoc event cua SV trong class | API | P1 |

### 3.8. wellbeing (Digital Wellbeing)

**Scope**: Nudge trigger, accept/dismiss tracking, no-flow-break

| Test Group | Mo ta | Loai | Muc do |
|-----------|-------|------|--------|
| WB-001 | Hoc lien tuc > 50 phut -> should_nudge = true | API | P1 |
| WB-002 | Hoc < 50 phut -> should_nudge = false | API | P1 |
| WB-003 | Nudge response (accept/dismiss) duoc luu dung | API | P1 |
| WB-004 | Ty le chap nhan nudge duoc tracking (cho KPI) | Integration | P2 |
| WB-005 | Nudge KHONG lam gian doan flow hoc tap (khong block UI) | E2E | P1 |
| WB-006 | Nudge history xem duoc qua API | API | P2 |

### 3.9. Frontend (Next.js 14)

**Scope**: E2E journeys, responsive, error states, loading states, UX quality, accessibility

| Test Group | Mo ta | Loai | Muc do |
|-----------|-------|------|--------|
| FE-001 | Login page render, submit, redirect thanh cong | E2E | P0 |
| FE-002 | Login sai -> hien error message ro rang voi role="alert" va huong dan xu ly | E2E | P1 |
| FE-003 | Student dashboard hien stats, mastery chart, pathway progress | E2E | P0 |
| FE-004 | Assessment UI: quiz voi timer, save progress, submit | E2E | P0 |
| FE-005 | Pathway page: concept map, current task, progress bar | E2E | P0 |
| FE-006 | Task view: goal, timer, submission form | E2E | P1 |
| FE-007 | Lecturer overview: on-track/watch/urgent counts | E2E | P0 |
| FE-008 | Lecturer alerts: list, filter, detail view voi icon + text severity (khong chi mau) | E2E | P0 |
| FE-009 | Lecturer action buttons: send message, suggest task, schedule meeting + toast xac nhan | E2E | P1 |
| FE-010 | Wellbeing nudge hien va khong block UI | E2E | P1 |
| FE-011 | Responsive: mobile 375px (sidebar drawer), tablet 768px, desktop 1280px (sidebar co dinh) | E2E | P2 |
| FE-012 | Error state: API fail -> hien error message voi huong dan xu ly, khong man hinh trang | E2E | P1 |
| FE-013 | Loading state: skeleton/spinner khi dang fetch data (khong "dang xu ly" qua 2s) | E2E | P2 |
| FE-014 | Token het han -> redirect ve login | E2E | P1 |
| FE-015 | Navigation sidebar hoat dong dung theo role, co aria-current="page" | E2E | P1 |
| FE-016 | Toast notification hien khi user thuc hien action (submit, dismiss, intervention) | E2E | P2 |
| FE-017 | Quiz/assessment options co role="radiogroup" + role="radio" + aria-checked | E2E | P1 |
| FE-018 | Form inputs co label lien ket, error co aria-describedby + aria-invalid | E2E | P1 |
| FE-019 | Skip-to-content link hoat dong (Tab dau tien -> focus main content) | E2E | P2 |
| FE-020 | Modal/dialog co focus trap, Escape dong, role="dialog" + aria-modal (Radix Dialog) | E2E | P1 |
| FE-021 | Severity/mastery/progress co icon + text ben canh mau (khong chi color) | E2E | P1 |
| FE-022 | Contrast ratio >= 4.5:1 cho text, >= 3:1 cho large text (WCAG 2.1 AA) | Lighthouse | P1 |
| FE-023 | Keyboard Tab di qua duoc flow core (login -> dashboard -> task -> submit) | E2E | P1 |
| FE-024 | axe-core WCAG 2.1 AA scan pass tren login, dashboard, task pages | E2E | P1 |
| FE-025 | Mobile sidebar drawer voi hamburger menu, focus trap, Escape close | E2E | P2 |
| FE-026 | Copy khong phan xet nguoi hoc (dung "can bo sung" thay "yeu/kem") | Manual | P2 |
| FE-027 | Empty state co huong dan buoc tiep theo (khong trang trang) | E2E | P2 |

---

## 4. Test Case Matrix -- Core Journeys

7 journey duoi day la "golden paths" phai **100% pass** truoc moi release. Moi journey la E2E, mo phong hanh vi thuc cua user.

**Mapping spec files:**

| Journey | Spec file | Mo ta |
|---------|-----------|-------|
| J1 | `e2e/journeys/journey-a-new-student.spec.ts` | Student Onboarding |
| J2 | `e2e/journeys/journey-b-adaptive.spec.ts` (B1-B3) | Student Learning Loop |
| J3 | `e2e/journeys/journey-b-adaptive.spec.ts` (B4-B8) | Student Retry Flow |
| J4 | `e2e/journeys/journey-c-lecturer.spec.ts` (C0-C4) | Lecturer Early Warning |
| J5 | `e2e/journeys/journey-c-lecturer.spec.ts` (C5-C9) | Lecturer Intervention |
| J6 | `e2e/journeys/journey-e-wellbeing.spec.ts` | Wellbeing Nudge |
| J7 | `e2e/journeys/journey-f-data-pipeline.spec.ts` | Data Pipeline |

Ngoai ra, `e2e/journeys/journey-d-privacy.spec.ts` cover Privacy request flow (khong nam trong 7 core journeys nhung bat buoc cho L4).

### J1: Student Onboarding

```
Precondition: User chua co tai khoan

1. POST /auth/register/ -> 201 (tao user role=student)
2. POST /auth/login/ -> 200 (nhan JWT)
3. POST /auth/consent/ -> 200 (consent_given=true)
4. GET /assessment/ -> 200 (danh sach assessment)
5. POST /assessment/{id}/start/ -> 201 (tao session)
6. POST /assessment/sessions/{sid}/answer/ x 15-20 lan -> 200
7. POST /assessment/sessions/{sid}/complete/ -> 200
8. Verify: LearnerProfile duoc tao voi strengths/weaknesses
9. GET /curriculum/tasks/?concept={weakest} -> 200
10. Verify: SV co task dau tien de bat dau hoc

Pass criteria:
- Moi buoc tra ve dung HTTP status
- LearnerProfile.initial_mastery khong rong
- Assessment score tinh dung
- Thoi gian toan bo flow < 30s (API calls)
```

### J2: Student Learning Loop

```
Precondition: SV da co LearnerProfile, co MasteryState

1. GET /adaptive/pathway/{course_id}/ -> 200 (pathway hien tai)
2. GET /curriculum/tasks/?concept={current} -> 200
3. POST /adaptive/submit/ (is_correct=true) -> 200
4. Verify: mastery.p_mastery tang
5. Verify: pathway.action phu hop voi P(mastery) moi
6. Verify: event micro_task_completed duoc tao
7. Lap lai 3-5 lan -> verify mastery tang dan (monotonic khi lien tuc dung)

Pass criteria:
- BKT update dung theo cong thuc
- Pathway decision nhat quan voi nguong 0.60 / 0.85
- Events duoc fire day du
- Response time < 3s moi lan submit
```

### J3: Student Retry Flow

```
Precondition: SV dang hoc, P(mastery) < 0.60 cho 1 concept

1. POST /adaptive/submit/ (is_correct=false) -> 200
2. Verify: pathway.action = "supplement" (hoac tuong tu)
3. GET /curriculum/concepts/{id}/content/ -> 200 (supplementary)
4. Verify: content_intervention event duoc tao
5. POST /adaptive/submit/ (retry, is_correct=true) -> 200
6. Verify: attempt_number = 2
7. Verify: mastery.p_mastery tang so voi truoc retry

Pass criteria:
- Supplementary content phai xuat hien khi fail
- Retry duoc phep va BKT update binh thuong
- attempt_number tang dung
- Khong co dead-end (SV luon co buoc tiep theo)
```

### J4: Lecturer Early Warning

```
Precondition: Co SV da inactive >= 5 ngay, co SV retry fail >= 3 lan

1. Celery beat trigger nightly batch
2. Verify: Alert RED duoc tao cho SV inactive >= 5 ngay
3. Verify: Alert RED duoc tao cho SV retry fail >= 3
4. Verify: Alert YELLOW duoc tao cho SV inactive 3-4 ngay
5. Verify: GREEN SV KHONG co alert
6. GET /dashboard/class/{id}/overview/ -> 200
7. Verify: on_track + needs_attention + needs_intervention = total_students
8. GET /dashboard/alerts/?severity=red -> 200
9. Verify: alerts co day du severity, reason, evidence, suggested_action

Pass criteria:
- Severity classification dung 100%
- reason la human-readable
- Overview counts dung
- Khong false positive (SV binh thuong bi danh RED)
- Khong false negative (SV nguy co khong duoc canh bao)
```

### J5: Lecturer Intervention

```
Precondition: Co active alerts

1. GET /dashboard/alerts/?status=active -> 200
2. POST /dashboard/interventions/ (action_type=send_message) -> 201
3. Verify: InterventionAction duoc tao voi day du thong tin
4. Verify: event gv_action_taken duoc fire
5. GET /dashboard/interventions/history/ -> 200
6. Verify: lich su ghi dung who, when, what, targets
7. PATCH /dashboard/interventions/{id}/follow-up/ -> 200
8. POST /dashboard/alerts/{id}/dismiss/ -> 200
9. Verify: alert status chuyen thanh dismissed

Pass criteria:
- Action log day du, khong mat entry
- Event tracking hoat dong
- GV chi thay va action duoc tren SV trong class minh
- Follow-up workflow hoan chinh
```

### J6: Wellbeing Nudge

```
Precondition: SV dang hoc lien tuc

1. POST /wellbeing/check/ (continuous_minutes=30) -> should_nudge=false
2. POST /wellbeing/check/ (continuous_minutes=55) -> should_nudge=true
3. Verify: nudge co message va nudge_type
4. POST /wellbeing/nudge/{id}/respond/ (accepted=true) -> 200
5. Verify: event wellbeing_nudge_shown duoc fire
6. GET /wellbeing/my/ -> 200 (lich su nudge)

Pass criteria:
- Nguong 50 phut chinh xac
- Nudge khong block UI (E2E verify)
- Response duoc luu
- Event tracking hoat dong
```

### J7: Data Pipeline

```
Precondition: Co raw data tu ETL hoc vu

1. Chay etl_academic.py -> khong loi
2. Chay data cleaning pipeline
3. Verify: missing data duoc phan loai (MCAR/MAR/MNAR)
4. Verify: KNN imputation chay cho MAR
5. Verify: Z-score/IQR outlier screening hoat dong
6. GET /analytics/data-quality/ -> 200
7. Verify: data_quality_score >= 70%
8. Chay nightly_analytics.py -> KPI duoc tinh
9. GET /analytics/kpi/{class_id}/ -> 200
10. Verify: 5 KPIs deu co gia tri hop le

Pass criteria:
- Pipeline chay end-to-end khong loi
- Data quality score >= 70%
- KPIs khong null/NaN
- Report data doi chieu duoc
```

---

## 5. API Contract Testing

### 5.1. Coverage bat buoc

Moi endpoint trong API.md phai co **toi thieu** cac test case sau:

| Test type | Mo ta | Bat buoc |
|-----------|-------|---------|
| Happy path | Request dung -> response dung | YES |
| 401 Unauthorized | Request khong co token | YES |
| 403 Forbidden | Request voi role khong du quyen | YES (neu endpoint co RBAC) |
| 404 Not Found | Request voi ID khong ton tai | YES |
| 400 Validation | Request voi data khong hop le | YES |
| Pagination | List endpoint tra ve dung count, next, previous | YES (list endpoints) |
| Edge case | Boundary values, empty results, max payload | RECOMMENDED |

### 5.2. Endpoint inventory va test status

| Endpoint Group | So endpoints | Core? | Test bat buoc |
|---------------|-------------|-------|--------------|
| /auth/ | 8 | YES | 5 test types x 8 = 40 cases |
| /assessment/ | 6 | YES | 5 x 6 = 30 cases |
| /adaptive/ | 6 | YES | 5 x 6 = 30 cases |
| /curriculum/ | 8 | YES | 5 x 8 = 40 cases |
| /dashboard/ | 6 | YES | 5 x 6 = 30 cases |
| /events/ | 4 | YES | 5 x 4 = 20 cases |
| /wellbeing/ | 3 | NO | Happy + 401 = 6 cases |
| /analytics/ | 4 | YES | 5 x 4 = 20 cases |
| /health/ | 1 | YES | Happy path = 1 case |
| **Tong** | **46** | | **~217 cases toi thieu** |

### 5.3. OpenAPI Schema Regression

- drf-spectacular generate schema tai `/api/schema/`
- Moi PR phai chay OpenAPI diff -- khong duoc co **breaking change** khong duoc announce:
  - Xoa endpoint
  - Doi kieu response field
  - Them required field vao request
  - Doi HTTP method
- Tool de nghi: `openapi-diff` hoac `oasdiff`

### 5.4. Response Time SLA

| Endpoint Group | P95 Target | P99 Target |
|---------------|-----------|-----------|
| /auth/ | < 500ms | < 1s |
| /assessment/ (submit/complete) | < 2s | < 3s |
| /adaptive/submit/ | < 2s | < 3s |
| /adaptive/mastery/ | < 1s | < 2s |
| /dashboard/overview/ | < 2s | < 3s |
| /dashboard/alerts/ | < 1s | < 2s |
| /events/track/ | < 500ms | < 1s |
| /events/batch/ | < 2s | < 3s |
| /health/ | < 200ms | < 500ms |

---

## 6. Data Quality Assurance

### 6.1. Data Integrity Constraints (12 checks bat buoc)

| # | Check | Query/Logic | Pass criteria |
|---|-------|-------------|---------------|
| DI-01 | Khong orphan MasteryState | Moi MasteryState.student_id ton tai trong User | 0 orphans |
| DI-02 | Khong orphan TaskAttempt | Moi TaskAttempt.student_id va task_id ton tai | 0 orphans |
| DI-03 | Khong orphan Alert | Moi Alert.student_id ton tai trong User | 0 orphans |
| DI-04 | Khong duplicate MasteryState | Unique(student_id, concept_id) | 0 duplicates |
| DI-05 | Khong duplicate active session | Max 1 session in_progress per student per assessment | 0 violations |
| DI-06 | FK consistency: MicroTask -> Milestone, Concept | FK luon resolve | 0 broken FK |
| DI-07 | FK consistency: Alert -> User, InterventionAction -> Alert | FK luon resolve | 0 broken FK |
| DI-08 | LearnerProfile.strengths va weaknesses chi chua Concept IDs ton tai | Moi ID resolve duoc | 0 invalid refs |
| DI-09 | Assessment score trong [0, 100] | Khong co score am hoac >100 | 0 violations |
| DI-10 | TaskAttempt.attempt_number > 0 va tang dan cho cung student+task | Logic dung | 0 violations |
| DI-11 | Event log khong co user_id khong ton tai | FK check | 0 orphans |
| DI-12 | Concept order khong duplicate trong cung course | Unique(course_id, order) | 0 duplicates |

### 6.2. BKT Parameter Bounds

| # | Check | Constraint | Pass criteria |
|---|-------|-----------|---------------|
| BP-01 | P(mastery) | 0.0 <= p_mastery <= 1.0 | 0 violations |
| BP-02 | P(guess) | 0.0 <= p_guess <= 1.0 | 0 violations |
| BP-03 | P(slip) | 0.0 <= p_slip <= 1.0 | 0 violations |
| BP-04 | P(transit) | 0.0 <= p_transit <= 1.0 | 0 violations |
| BP-05 | P(guess) + P(slip) | < 1.0 (otherwise BKT degenerates) | 0 violations |
| BP-06 | P(mastery) monotonicity | Sau chuoi dai cau dung, p_mastery phai tang | Verify tren test data |
| BP-07 | No NaN/Infinity | Tat ca BKT fields la finite numbers | 0 violations |

### 6.3. Event Data Completeness

| # | Event | Required fields | Check |
|---|-------|----------------|-------|
| EC-01 | session_started | user_id, timestamp, device | Khong null |
| EC-02 | session_ended | user_id, duration | duration > 0 |
| EC-03 | assessment_completed | score, time_taken | score trong [0,100] |
| EC-04 | micro_task_completed | task_id, attempts, duration | task_id ton tai |
| EC-05 | content_intervention | concept_id, type, source_rule | concept_id ton tai |
| EC-06 | gv_action_taken | action_type, targets | targets non-empty |
| EC-07 | wellbeing_nudge_shown | nudge_type, accepted | boolean value |
| EC-08 | page_view | page, referrer | page non-empty |

### 6.4. Data Cleaning Pipeline Validation

| # | Check | Mo ta | Pass criteria |
|---|-------|-------|---------------|
| DC-01 | Missing data detection | Pipeline phat hien duoc missing values | So luong khop voi manual count |
| DC-02 | Missing data classification | Phan loai dung MCAR/MAR/MNAR | Verify tren test dataset |
| DC-03 | KNN imputation | Imputed values nam trong range hop le | Khong co outlier moi |
| DC-04 | Outlier screening | Z-score hoac IQR phat hien dung outlier da biet | True positive rate >= 80% |
| DC-05 | Idempotency | Chay pipeline 2 lan cho cung data -> ket qua giong nhau | Diff = 0 |
| DC-06 | Data quality score | Score >= 70% sau cleaning | >= 70% |

---

## 7. Security and Privacy Checklist (Upgraded)

> PRD: ma hoa PII, TLS 1.3, RBAC 3 vai tro, pseudonymization, export/xoa, audit log, rollback su co.
> Competition doc: brute force protection, XSS/SQLi/CSRF, JWT/HttpOnly, OWASP checklist.
> **Tieu chuan nay tong hop ca hai va siet cao hon.**

### 7.1. Security Gate bat buoc (10 nhom, tat ca phai PASS)

| # | Nhom | Chuan bat buoc | SEC ref | Test ref |
|---|------|---------------|---------|----------|
| SG-01 | AuthN | Session/token khong bi reuse sai; logout xoa sach cookies + token; refresh token bi revoke sau logout | SEC-03 | `test_security_hardened.py::TestSG01AuthN` |
| SG-02 | AuthZ | SV khong thay lop khac; GV khong thay lop khac; Admin chi aggregate theo policy | SEC-05, RBAC-001..007 | `test_authz_matrix.py`, `test_idor.py` |
| SG-03 | Input validation | Khong tin FE; moi input validate o BE; reject oversized/malformed payloads | SEC-06, SEC-07 | `test_injection.py`, `test_security_hardened.py::TestSG03InputValidation` |
| SG-04 | Injection | 0 SQLi, 0 XSS (stored + reflected), 0 CSRF, 0 IDOR | SEC-06..08 | `test_injection.py`, `test_idor.py`, `test_security_hardened.py::TestSG04Injection` |
| SG-05 | Secret handling | Khong hardcode secret; rotate duoc; .env KHONG committed | SEC-12 | `detect-secrets` pre-commit, CI `security-audit` |
| SG-06 | Transport | HTTPS only; HTTP redirect 301; HSTS header | SEC-02 | manual verify production |
| SG-07 | Sensitive data | PII ma hoa at-rest (AES-256); log khong chua du lieu nhay cam tho; error response khong leak stack trace | SEC-01, SEC-10 | `test_data_exposure.py`, `test_security_hardened.py::TestSG07SensitiveData` |
| SG-08 | Audit | Xem du lieu, sua rule, export, xoa du lieu, login, logout, role change deu phai log | SEC-13 | `privacy/tests.py`, `test_security_hardened.py::TestSG08Audit` |
| SG-09 | Rate limit | Login, assessment submit, dashboard actions, export data deu co rate limit | SEC-09 | `test_security_hardened.py::TestSG09RateLimit` |
| SG-10 | OWASP Top 10 | Pass checklist OWASP Top 10 2021 (A01-A10) | SEC-01..15 | Tong hop tat ca security tests |

### 7.1.1. Security Checks chi tiet (21 hang muc)

| # | Hang muc | Chi tiet | Cong cu |
|---|---------|---------|--------|
| SEC-01 | PII encrypted at rest | User.email, User.student_id ma hoa AES-256 trong DB | Query DB, verify ciphertext |
| SEC-02 | TLS enforcement | HTTPS only, HTTP redirect 301, HSTS header | curl -I |
| SEC-03 | JWT security | httpOnly cookies, access 5-15min, refresh co rotate | Decode JWT, verify |
| SEC-04 | Token khong trong URL | JWT khong xuat hien trong query params, URL, logs | Grep logs |
| SEC-05 | RBAC enforcement | 23+ to hop role x resource dung | `test_authz_matrix.py` |
| SEC-06 | SQL injection | 0 SQLi qua login, search, filter, form | `test_injection.py` + OWASP ZAP |
| SEC-07 | XSS protection | Stored XSS o notes/feedback/content duoc escape | `test_injection.py` |
| SEC-08 | CSRF protection | POST/PUT/DELETE co CSRF hoac JWT httpOnly exempt | Cross-origin test |
| SEC-09 | Rate limiting | Login: 5/min, submit: 30/min, export: 3/hour | `test_security_hardened.py` |
| SEC-10 | Error khong leak | 500 khong tra stack trace; 404 khong enumerate | Trigger errors, verify |
| SEC-11 | Dependency CVE | 0 critical/high CVE | `pip-audit`, `npm audit` |
| SEC-12 | Secret management | 0 secrets in source; .env.example co, .env khong | `detect-secrets`, git history |
| SEC-13 | Audit log | Login, logout, export, delete, role change, data access | Verify AuditLog entries |
| SEC-14 | CORS | Chi origins trong CORS_ALLOWED_ORIGINS | Cross-origin request test |
| SEC-15 | Debug OFF | DJANGO_DEBUG=False production | Verify settings |
| SEC-16 | Logout sach | Logout -> cookies cleared + refresh revoked + redirect /login | `test_security_hardened.py::TestSG01AuthN` |
| SEC-17 | Token invalidation sau role change | Doi role user -> token cu khong con hop le | `test_security_hardened.py::TestSG01AuthN` |
| SEC-18 | Audit log immutable | AuditLog entries khong sua/xoa duoc qua API | `test_security_hardened.py::TestSG08Audit` |
| SEC-19 | Deleted data not accessible | Du lieu xoa tren UI khong con truy xuat duoc qua API | `test_security_hardened.py::TestSG04Injection` |
| SEC-20 | Export requires auth + ownership | Export data chi cho user so huu, khong cho user khac | `test_security_hardened.py::TestSG07SensitiveData` |
| SEC-21 | Password not in response | Password hash khong bao gio xuat hien trong API response | `test_data_exposure.py` |

### 7.1.2. FAIL NGAY neu co bat ky loi nao (Security Kill Conditions)

| # | Dieu kien FAIL | Hau qua | Muc do | Test ref |
|---|---------------|---------|--------|----------|
| SK-01 | IDOR lay du lieu SV lop khac | Lo thong tin hoc tap, vi pham privacy | **P0** | `test_idor.py`, `test_authz_matrix.py::TestObjectLevelAccess` |
| SK-02 | Export data khong kiem quyen | Bat ky user nao export duoc data cua user khac | **P0** | `test_security_hardened.py::TestSK02ExportAuth` |
| SK-03 | Token con hieu luc sau logout/role change | Session hijack, privilege escalation | **P0** | `test_security_hardened.py::TestSK03TokenInvalidation` |
| SK-04 | Stored XSS o ghi chu/feedback/noi dung GV | Ma doc chay trong browser SV/GV khac | **P0** | `test_injection.py::TestXSSPrevention` |
| SK-05 | Audit log sua/xoa duoc ma khong de vet | Mat kha nang truy vet hanh vi, mat bang chung | **P0** | `test_security_hardened.py::TestSK05AuditImmutable` |
| SK-06 | Du lieu xoa "tren UI" nhung con truy xuat qua API | Vi pham quyen rieng tu, SV tuong da xoa nhung chua | **P0** | `test_security_hardened.py::TestSK06DeletedDataGone` |

**Bat ky SK nao con ton tai -> NO-GO tuyet doi, khong ngoai le.**

### 7.2. Privacy Standard (Upgraded)

> PRD: ma hoa PII, pseudonymization, quyen SV xem/export/xoa, phan biet 3 tier du lieu, xu ly su co 48h.
> **Tieu chuan nay co the hoa tung yeu cau va them cac dieu kien fail nghiem trong.**

#### 7.2.1. Privacy Principles

| # | Nguyen tac | Chuan bat buoc | Test ref |
|---|----------|---------------|----------|
| PP-01 | Consent ro rang | Khong gop chung mo ho; phan biet tung purpose (academic / behavioral / inference); revoke duoc tung loai | `privacy/tests.py::TestConsentFlow` |
| PP-02 | Phan biet 3 tier du lieu | Tier 1: hoc vu lich su (academic); Tier 2: hanh vi hoc tap (behavioral); Tier 3: suy luan (mastery, risk flag, inference) | Export tra ve 3 tiers rieng biet |
| PP-03 | Quyen xoa co policy | Behavioral: hard delete; Inference (mastery, alerts): hard delete; PII: anonymize (not delete -- giu aggregate); Academic: giu theo quy dinh truong | `privacy/tests.py::TestDeleteAnonymizeFlow` |
| PP-04 | Export de doc | JSON voi timestamp, format_version, glossary giai thich tung field, phan chia theo tier | `privacy/tests.py::TestExportFlow` |
| PP-05 | GV chi xem du lieu can thiet | GV xem mastery (p_mastery) nhung KHONG xem BKT internals (p_guess, p_slip, p_transit); GV xem assessment events nhung KHONG xem page_view hoac wellbeing | `privacy/tests.py::TestRBAC::test_lecturer_sees_filtered_*` |
| PP-06 | Khong suy dien vuot muc | Event tracking chi phuc vu muc tieu su pham da cong bo (KPI pilot); khong dung de xep hang SV hoac suy dien nang luc ngoai scope | Policy check; no ranking endpoint; no leaderboard |

#### 7.2.2. Privacy Checks chi tiet (12 hang muc)

| # | Hang muc | Chi tiet kiem tra | Test ref |
|---|---------|-------------------|----------|
| PRI-01 | Consent gate | User chua consent -> he thong KHONG thu thap du lieu hoc tap | `TestRBAC::test_consent_gate_blocks_without_consent` |
| PRI-02 | Consent timestamp | consent_given_at luu dung thoi diem, ConsentRecord co version | `TestConsentFlow::test_consent_sync_to_user_flag` |
| PRI-03 | Minimum data collection | Chi thu thap du lieu can thiet cho chuc nang (khong thu thua) | Code review + PP-06 |
| PRI-04 | Pseudonymization | Analytics queries dung pseudonymized data, khong leak ten/MSSV | `TestPIIScrubbing` |
| PRI-05 | Lecturer data isolation | GV chi thay SV trong class duoc assign | RBAC tests, ALERT-003 |
| PRI-06 | Data retention | Event logs chi giu 6 thang, sau do aggregate + delete | `TestRetention::test_retention_deletes_old_behavioral` |
| PRI-07 | Export/delete request | SV co mechanism xem/export/xoa du lieu ca nhan | `TestExportFlow`, `TestDeleteAnonymizeFlow` |
| PRI-08 | Privacy policy | Consent wording da duoc phe duyet truoc khi collect | Manual PO + Phong DT |
| PRI-09 | Log scrubbing | PII (email, phone, student_id) bi scrub trong logs va Sentry | `TestPIIScrubbing::test_log_filter_scrubs_*` |
| PRI-10 | Error response scrubbing | Exception messages khong chua PII | `TestPIIScrubbing::test_exception_handler_scrubs_pii` |
| PRI-11 | Incident response SLA | Privacy incident phai co SLA deadline (48h), escalation | `TestIncidentResponse::test_incident_sla_deadline_set` |
| PRI-12 | Consent history | Moi thay doi consent duoc giu trong ConsentRecord (khong overwrite) | `TestConsentFlow::test_consent_history_preserved` |

#### 7.2.3. Privacy Release Gate

| # | Dieu kien | Nguong | Nguon verify |
|---|----------|--------|-------------|
| PRG-01 | 100% consent flow pass | Tat ca TestConsentFlow tests PASS | CI test report |
| PRG-02 | 100% export flow pass | Tat ca TestExportFlow tests PASS | CI test report |
| PRG-03 | 100% delete/anonymize flow pass | Tat ca TestDeleteAnonymizeFlow tests PASS | CI test report |
| PRG-04 | 100% RBAC pass | Tat ca TestRBAC tests PASS (bao gom consent gate) | CI test report |
| PRG-05 | 100% audit trail pass | Tat ca TestAuditTrail tests PASS | CI test report |
| PRG-06 | 0 PII leak | Tat ca TestPIIScrubbing tests PASS; 0 PII trong logs, analytics, error report | CI + manual verify |
| PRG-07 | 0 tier confusion | Export tra ve dung 3 tiers; delete chi anh huong tier duoc chon | TestExportFlow + TestDeleteAnonymizeFlow |
| PRG-08 | Incident SLA configured | PrivacyIncident co sla_deadline, is_within_sla property | TestIncidentResponse |

**Bat ky PRG nao FAIL -> NO-GO.**

### 7.3. Observability and Instrumentation Standard

> PRD xac dinh event core: session_started, assessment_completed, micro_task_completed, content_intervention, retry_triggered, gv_dashboard_viewed, gv_action_taken, wellbeing_nudge.
> **Tieu chuan nay nang cap len chuan observability cap van hanh.**

#### 7.3.1. Event Quality Standard

Moi event phai co **toi thieu** cac truong sau:

**Truong bat buoc (tat ca events):**

| # | Field | Mo ta | Constraint |
|---|-------|-------|-----------|
| EF-01 | event_name | Ten event tu EventName choices | NOT NULL, valid choice |
| EF-02 | event_version | Version schema event | NOT NULL, default "1.0" |
| EF-03 | timestamp_utc | Thoi gian event (UTC) | NOT NULL |
| EF-04 | actor_type | student / lecturer / admin / system | NOT NULL, valid choice |
| EF-05 | actor_id | FK den User (nullable cho system) | FK valid hoac NULL |
| EF-06 | session_id | Browser session identifier | String, max 100 |
| EF-07 | course_id | FK den Course | Nullable FK |
| EF-08 | class_id | FK den StudentClass | Nullable FK |
| EF-09 | device_type | desktop / mobile / tablet | String, max 30 |
| EF-10 | source_page | URL/page name | String, max 200 |
| EF-11 | request_id | UUID de correlate logs | UUID, auto-generated |

**Truong bat buoc bo sung (learning events):**

| # | Field | Ap dung cho | Constraint |
|---|-------|------------|-----------|
| EF-12 | concept_id | micro_task_completed, content_intervention | FK valid |
| EF-13 | task_id | micro_task_completed | FK valid |
| EF-14 | difficulty_level | micro_task_completed | 1-3 |
| EF-15 | attempt_number | micro_task_completed, retry_triggered | >= 1 |
| EF-16 | mastery_before | micro_task_completed, content_intervention | [0.0, 1.0] |
| EF-17 | mastery_after | micro_task_completed, content_intervention | [0.0, 1.0] |
| EF-18 | intervention_reason | content_intervention | String, non-empty |

**Confirmation events**: assessment_completed, micro_task_completed, gv_action_taken phai co `confirmed_at` timestamp sau khi BE verify thanh cong.

#### 7.3.2. Observability SLO

| # | Metric | Target | Measurement | Verify |
|---|--------|--------|-------------|--------|
| OB-01 | Event completeness | **>= 99.5%** | (events voi required fields day du) / (tong events) | `test_observability.py`, release_gate G-06 |
| OB-02 | Event duplication rate | **<= 0.1%** | (duplicate events) / (tong events) | Idempotency key check, EVT-008 |
| OB-03 | Clock skew normalized | timestamp_utc la server-side, client_timestamp luu rieng | Verify timestamp_utc = server time | `test_observability.py` |
| OB-04 | 0 orphan event | Moi event co actor map duoc (tru system events) | `actor_id` FK valid | DI-11, EC tests |
| OB-05 | Critical events BE-confirmed | assessment_completed, micro_task_completed, gv_action_taken KHONG chi fire o FE | `confirmed_at` NOT NULL cho confirmation events | `test_observability.py` |

#### 7.3.3. Operations Dashboard bat buoc

Phai co dashboard (Grafana) voi **toi thieu 9 panels** sau:

| # | Panel | Metric | Threshold |
|---|-------|--------|-----------|
| OD-01 | App error rate | `sum(rate(5xx)) / sum(rate(total)) * 100` | < 1% green, < 5% yellow, >= 5% red |
| OD-02 | API latency | p50, p95, p99 per endpoint group | P95 < SLO (Section 8.1.1) |
| OD-03 | Adaptive decision latency | `/adaptive/submit/` p95 | < 1.5s |
| OD-04 | Job success/fail | Celery task results | 0 failures alert |
| OD-05 | ETL data quality score | `DataQualityLog.quality_score` | >= 70% |
| OD-06 | Event ingestion health | Events/min, completeness % | Ingestion rate > 0 |
| OD-07 | Alert generation volume | Alerts created per batch | Spike detection |
| OD-08 | Export/delete requests | GDPR request count + completion rate | Pending > 48h alert |
| OD-09 | Backup freshness | Last backup timestamp | > 12h old = alert |

**Implementation**: `infra/grafana/provisioning/dashboards/palp-operations.json` (da co day du 9 panels + HTTP request rate).

---

## 8. Performance and Load Testing

### 8.1. Performance SLO (Upgraded)

PRD dat MVP la <3s load, <3s adaptive cho 200 concurrent. Bo chuan nang cao **siet hon** de dam bao trai nghiem hoc tap tron tru.

| Metric | MVP PRD | **Chuan rat cao** | Measurement | Tool |
|--------|---------|-------------------|-------------|------|
| Page load (FE) | < 3s P95 | **< 2.0s P95** | First Contentful Paint tren 4G throttled | Lighthouse / Playwright |
| Adaptive decision | < 3s P95 | **< 1.5s P95, < 2.5s P99** | POST /adaptive/submit/ round-trip | Locust / k6 |
| Dashboard load | < 3s P95 | **< 2.0s P95** | GET /dashboard/class/{id}/overview/ | Locust / k6 |
| Assessment submit | < 3s P95 | **< 800ms P95** | POST /assessment/sessions/{sid}/answer/ | Locust / k6 |
| Progress update | < 1s P95 | **< 500ms P95** | POST /adaptive/submit/ (mastery+pathway) | Locust / k6 |
| Health endpoint | < 200ms P99 | **< 100ms P95, < 200ms P99** | GET /api/health/ | curl benchmark |
| DB query budget | < 500ms/query | **< 300ms P95** | Khong co single query vuot 300ms | Django debug toolbar / EXPLAIN |
| Redis cache hit | > 80% | **> 85%** | mastery + dashboard cache | Redis INFO stats |
| FE bundle size | < 500KB | **< 400KB initial JS** | Compressed JS sent on first load | next build + source-map-explorer |
| Error rate | chua dinh nghia | **< 0.5%** | Tong loi / tong request trong load test | Locust / k6 |

### 8.1.1. Per-endpoint SLA (upgraded)

| Endpoint Group | P95 Target | P99 Target |
|---------------|-----------|-----------|
| /auth/ | < 300ms | < 500ms |
| /assessment/ (submit/complete) | < 800ms | < 1.5s |
| /adaptive/submit/ | < 1.5s | < 2.5s |
| /adaptive/mastery/ | < 500ms | < 1s |
| /dashboard/overview/ | < 2s | < 3s |
| /dashboard/alerts/ | < 800ms | < 1.5s |
| /events/track/ | < 300ms | < 500ms |
| /events/batch/ | < 1.5s | < 2.5s |
| /health/ | < 100ms | < 200ms |

### 8.2. Load Test Scenarios (Upgraded)

| Scenario | Mo phong | Concurrent users | Duration | Pass criteria |
|----------|---------|-----------------|----------|---------------|
| LT-01 | Normal usage | 50 users | 10 phut | P95 < 2s, 0 errors |
| LT-02 | Peak hour | 100 users | 10 phut | P95 < 2s, error rate < 0.1% |
| LT-03 | Stress test | 200 users | 15 phut | P95 < 3s, error rate < 0.5% |
| LT-04 | Spike test | 0 -> 300 trong 30s | 5 phut | He thong recover trong 60s, khong crash |
| LT-05 | Endurance | 50 users | 2 gio | Khong memory leak, P95 on dinh, RSS delta < 50MB |
| LT-06 | Sustained peak | 200 users | 30 phut | P95 < 2.5s on dinh, error rate < 0.5% |

### 8.3. Load Test User Profile

```
Student user (70% traffic):
  - Login
  - View pathway
  - Submit 3-5 tasks (voi BKT update)
  - View dashboard
  - Check wellbeing

Lecturer user (20% traffic):
  - Login
  - View class overview
  - View alerts
  - Take 1-2 actions
  - View intervention history

Admin user (10% traffic):
  - Login
  - View analytics
  - View KPI report
```

### 8.4. Celery Batch Performance

| Job | Data volume | Max duration | Pass criteria |
|-----|------------|-------------|---------------|
| Nightly early warning | 90 students x 10 concepts | < 5 phut | Alerts computed dung |
| Weekly report | 10 tuan data x 90 SV | < 10 phut | Report generated day du |
| Data quality check | Full dataset | < 15 phut | Score computed |

---

## 9. Operational Readiness

### 9.1. Infrastructure Checks

| # | Check | Pass criteria |
|---|-------|---------------|
| OPS-01 | `docker-compose up` -> tat ca services healthy | Healthy trong 120s |
| OPS-02 | Health endpoint respond 200 | Trong 5s sau khi backend start |
| OPS-03 | PostgreSQL healthcheck | pg_isready pass |
| OPS-04 | Redis healthcheck | Redis PING -> PONG |
| OPS-05 | Celery worker registered | celery inspect active tra ve workers |
| OPS-06 | Celery Beat scheduled | Verify 2 scheduled tasks (nightly + weekly) |
| OPS-07 | Frontend build thanh cong | next build khong loi |
| OPS-08 | Static files served | collectstatic + verify access |

### 9.2. Backup/Restore Drill (bat buoc pass 100%)

```
Quy trinh drill:

1. TAO BACKUP
   docker-compose exec db pg_dump -U palp palp > backup_drill.sql
   Verify: file > 0 bytes, co CREATE TABLE statements

2. GHI NHAN STATE
   Count so record cac bang chinh:
   - User, MasteryState, TaskAttempt, Alert, EventLog
   Ghi nhan checksums

3. DESTROY DATABASE
   docker-compose exec db dropdb -U palp palp
   docker-compose exec db createdb -U palp palp

4. RESTORE
   docker-compose exec -T db psql -U palp palp < backup_drill.sql

5. VERIFY
   - Count records phai khop voi buoc 2
   - Checksums phai khop
   - API health endpoint respond 200
   - Login thanh cong
   - Query MasteryState tra ve dung data
   - Celery beat van scheduled

6. KET QUA
   PASS: Tat ca verify thanh cong
   FAIL: Bat ky verify that bai -> P0 blocker
```

### 9.3. Rollback Procedure Test

```
Quy trinh test rollback:

1. Tag phien ban hien tai: v1.0.0-rc1
2. Deploy phien ban moi (co intentional change)
3. Verify change hoat dong
4. Thuc hien rollback:
   git checkout v1.0.0-rc1
   docker-compose down
   docker-compose up -d --build
5. Verify: he thong quay lai trang thai cu
6. Verify: du lieu khong bi mat
7. Verify: Celery jobs van chay dung
```

### 9.4. Monitoring Verification

| # | Check | Pass criteria |
|---|-------|---------------|
| MON-01 | Sentry DSN configured | SENTRY_DSN co trong .env production |
| MON-02 | Sentry captures errors | Trigger test error -> xuat hien trong Sentry dashboard |
| MON-03 | Structured logging | Backend logs co timestamp, level, module, message |
| MON-04 | Log rotation | Logs khong day disk (verify rotation config) |
| MON-05 | Uptime monitoring | Health endpoint duoc poll dinh ky (moi 5 phut) |

### 9.5. Availability / Reliability Standard (Upgraded)

#### 9.5.1. Uptime SLO

| Metric | Target | Do luong | Ghi chu |
|--------|--------|---------|---------|
| Uptime gio hoc (7h-22h) | **>= 99.9%** | Tong thoi gian available / tong thoi gian gio hoc | Cho phep max ~43 phut downtime/thang trong gio hoc |
| Uptime ngoai gio | >= 99.0% | Tong thoi gian available / tong ngoai gio | Maintenance window cho phep |
| MTTR (Mean Time to Recovery) | **< 30 phut** | Tu luc phat hien -> he thong hoat dong lai | Doi voi loi P0/P1 |
| RPO (Recovery Point Objective) | **< 1 gio** | Du lieu co the mat toi da khi restore tu backup | Backup schedule phai dam bao |
| RTO (Recovery Time Objective) | **< 2 gio** | Thoi gian toi da de khoi phuc toan bo dich vu | Bao gom restore + verify + smoke test |

#### 9.5.2. No Single Point of Failure

| # | Component | SPOF mitigation | Verify |
|---|-----------|----------------|--------|
| SPOF-01 | PostgreSQL | Backup tu dong moi 6h + manual truoc deploy | `scripts/backup_db.sh` + cron |
| SPOF-02 | Redis | Persistent mode (AOF), fallback to DB khi Redis down | `tests/recovery/test_redis_temporary_loss.py`, `tests/recovery/test_cache_failure.py` |
| SPOF-03 | Celery worker | Worker die -> task retry, supervisor/Docker restart | `tests/recovery/test_worker_die.py`, `tests/recovery/test_celery_retry.py` |
| SPOF-04 | Application server | Health check + Docker restart policy | `tests/recovery/test_backend_restart.py` |
| SPOF-05 | ETL pipeline | Atomic transaction, fail -> FAILED status, retry safe | `tests/recovery/test_etl_failure.py`, F5-06 |

#### 9.5.3. Health Check Matrix

| # | Component | Health check | Frequency | Alert khi |
|---|-----------|-------------|-----------|-----------|
| HC-01 | Django app | `GET /api/health/` -> 200 + JSON | Moi 30s | 2 consecutive failures |
| HC-02 | Celery worker | `celery inspect ping` -> pong | Moi 60s | 1 failure |
| HC-03 | Celery Beat | Verify scheduled tasks co `last_run_at` < 25h | Moi 60s | last_run_at > 25h |
| HC-04 | Redis | `PING` -> `PONG` | Moi 30s | 1 failure |
| HC-05 | PostgreSQL | `pg_isready` | Moi 30s | 1 failure |
| HC-06 | ETL pipeline | ETLRun.status != FAILED cho run gan nhat | Moi 6h | status == FAILED |
| HC-07 | Disk space | `df -h` root partition | Moi 5 phut | > 85% used |

#### 9.5.4. Cron / Batch Job Monitoring

| # | Job | Schedule | Monitor | Alert khi |
|---|-----|---------|---------|-----------|
| CJ-01 | Nightly early warning | 02:00 daily | DataQualityLog entry cho `source=early_warning` | Khong co entry sau 03:00 |
| CJ-02 | Weekly KPI report | Sunday 06:00 | PilotReport created cho tuan hien tai | Khong co report sau 07:00 Sunday |
| CJ-03 | KPI integrity audit | 04:00 daily | DataQualityLog entry cho `source=kpi_integrity_audit` | Khong co entry sau 05:00 |
| CJ-04 | Database backup | Moi 6h | Backup file size > 0 va timestamp moi | File >12h old hoac size=0 |
| CJ-05 | Event log cleanup | Weekly | EventLog count khong vuot retention limit | Count > limit * 1.5 |

#### 9.5.5. Queue Backlog Alerts

| # | Queue | Normal depth | Alert threshold | Action |
|---|-------|-------------|----------------|--------|
| QB-01 | Celery default | 0-10 | **> 50 tasks** | Investigate slow consumer |
| QB-02 | Celery early_warning | 0 (batch) | **> 100 tasks** | Check nightly batch |
| QB-03 | Redis pub/sub | N/A | Connection refused | Restart Redis |

#### 9.5.6. Operational Readiness Checklist (Upgraded)

| # | Check | Pass criteria | Blocker? |
|---|-------|---------------|----------|
| OPS-01 | `docker-compose up` -> tat ca healthy | Healthy trong 120s | YES |
| OPS-02 | Health endpoint respond 200 | Trong 5s sau start | YES |
| OPS-03 | PostgreSQL pg_isready | Pass | YES |
| OPS-04 | Redis PING -> PONG | Pass | YES |
| OPS-05 | Celery worker registered | `celery inspect active` co workers | YES |
| OPS-06 | Celery Beat scheduled | 3 tasks (nightly + weekly + kpi_audit) | YES |
| OPS-07 | Frontend build thanh cong | `next build` khong loi | YES |
| OPS-08 | Static files served | collectstatic + access verify | YES |
| OPS-09 | Backup script hoat dong | `scripts/backup_db.sh` tao file > 0 bytes | YES |
| OPS-10 | Monitoring armed | Sentry + health poll + Prometheus targets | YES |
| OPS-11 | Error rate < 0.5% | Smoke test 100 requests, < 1 fail | YES |
| OPS-12 | No stale cron jobs | Tat ca CJ-01..CJ-05 co last_run < SLA | YES |

---

## 10. UAT Protocol

> **Tieu chuan cao**: PALP la san pham EdTech tac dong truc tiep den quyet dinh hoc tap va can thiep su pham. Tieu chuan UAT duoc dat cao hon muc thong thuong (SUS >= 80 thay vi 68, them 5 PALP-specific metrics, 5 fail conditions). Chi tiet day du xem [docs/UAT_SCRIPT.md](UAT_SCRIPT.md).

### 10.1. Muc tieu UAT

| # | Muc tieu | Metric do luong |
|---|---------|-----------------|
| G1 | SV hieu onboarding | Onboarding stuck rate < 10% |
| G2 | SV chap nhan adaptive intervention | SV understanding score >= 4/5 |
| G3 | SV khong thay progress "gia" | SV progress trust score >= 4/5 |
| G4 | GV hieu dashboard va tin duoc canh bao | GV alert trust >= 4/5; Alert usefulness > 80% |
| G5 | GV thuc hien can thiep khong can dao tao sau | GV intervention ease >= 4/5 |

### 10.2. Tham gia

| Vai tro | So luong | Tieu chi chon |
|---------|---------|---------------|
| Sinh vien | 20-30 SV | Da dang: nam 1 + nam cuoi, gioi/kha/trung binh |
| Giang vien | 2-3 GV | GV day SBVL, co su dung cong nghe |
| Observer | 1-2 | Dev/QA ghi nhan hanh vi va loi |

### 10.3. Cau truc 2 vong

UAT duoc tien hanh qua **2 vong** voi cung nhom nguoi dung, cach nhau 2-3 ngay. Vong 2 do luong su cai thien time-on-task de xac nhan learnability.

| Vong | Noi dung | Muc dich |
|------|---------|---------|
| Vong 1 | SV: 8 tasks (60 phut) + GV: 7 tasks (45 phut) | Do baseline metrics |
| Gap 2-3 ngay | Fix P0 tu Vong 1, deploy len staging | |
| Vong 2 | Cung tasks, cung nguoi | Do time-on-task regression (phai giam) |

### 10.4. Dieu kien tien quyet

| # | Dieu kien | Responsible |
|---|----------|-------------|
| PRE-01 | Tat ca P0/P1 test cases da pass | QA |
| PRE-02 | Test accounts duoc tao (20-30 SV + 2-3 GV) | Dev |
| PRE-03 | Consent flow hoat dong va wording da duyet | PO + Phong DT |
| PRE-04 | Seed data cho course SBVL da load | Dev |
| PRE-05 | Assessment 15-20 cau da co noi dung | GV + PO |
| PRE-06 | Staging environment khop production | DevOps |
| PRE-07 | Monitoring hoat dong (Sentry + health) | Dev |
| PRE-08 | Phieu khao sat PALP-specific da chuan bi (Phu luc A cua UAT_SCRIPT.md) | QA |

### 10.5. UAT Script

Chi tiet 15 tasks (8 SV + 7 GV) duoc dinh nghia trong [docs/UAT_SCRIPT.md](UAT_SCRIPT.md) Section 3-4. Tom tat:

**Sinh vien (45-60 phut)**:
S1 Dang nhap + consent -> S2 Assessment -> S3 Learner profile -> S4 Pathway + micro-tasks -> S5 Supplementary content (+ phieu PALP-SV-01) -> S6 Advance concept -> S7 Wellbeing nudge -> S8 Dashboard (+ phieu PALP-SV-02)

**Giang vien (30-45 phut)**:
L1 Dang nhap -> L2 Class overview -> L3 Verify so lieu -> L4 Alert detail (+ phieu PALP-GV-01) -> L5 Intervention (+ phieu PALP-GV-02) -> L6 Resolve alert -> L7 KPI report

### 10.6. Tieu chi pass UAT

#### 10.6.1. Exit Criteria (tat ca phai PASS)

| # | Tieu chi | Nguong |
|---|---------|--------|
| UAT-PASS-01 | Khong P0 bug tu UAT | 0 P0 |
| UAT-PASS-02 | Khong P1 bug chua fix | 0 P1 open |
| UAT-PASS-03 | Task success rate (tat ca tasks) | >= 90% |
| UAT-PASS-04 | GV danh gia dashboard "de hieu" | >= 80% GV |
| UAT-PASS-05 | Khong SV nao bi "ket" (dead-end) | 0 dead-ends |
| UAT-PASS-06 | CSAT feedback | >= 4.0/5 |
| UAT-PASS-07 | SUS score | >= 80/100 |
| UAT-PASS-08 | GV tin tuong canh bao (PALP-GV-01 cau 1) | >= 4/5 |
| UAT-PASS-09 | SV hieu adaptive intervention (PALP-SV-01 cau 1) | >= 4/5 |
| UAT-PASS-10 | SV progress trust (PALP-SV-02 TB) | >= 4/5 |
| UAT-PASS-11 | Time-on-task core flows giam o Vong 2 | V2 avg < V1 avg |
| UAT-PASS-12 | Privacy incidents | 0 |

#### 10.6.2. Fail Conditions (bat ky 1 cai bi vi pham -> tu dong NO-GO)

| # | Dieu kien | Nguong |
|---|----------|--------|
| UAT-FAIL-01 | SV bi ket o onboarding (S1 hoac S2 fail) | >= 10% SV |
| UAT-FAIL-02 | SV khong hieu vi sao bi chuyen intervention | >= 10% SV cho <= 2/5 |
| UAT-FAIL-03 | GV noi dashboard "kho hieu" | >= 20% GV |
| UAT-FAIL-04 | Canh bao bi danh gia "khong huu ich" | > 20% |
| UAT-FAIL-05 | Loi P1 phat hien trong Vong 2 (vong cuoi) | > 1 loi P1 |

#### 10.6.3. Logic quyet dinh

```
NEU bat ky UAT-FAIL-01 -> UAT-FAIL-05 bi VIOLATED:
  -> NO-GO (tu dong, khong can hop)
  -> Fix root cause + UAT vong bo sung

NEU tat ca FAIL conditions = OK:
  -> Kiem tra UAT-PASS-01 -> UAT-PASS-12
  -> Tat ca PASS -> GO
  -> Bat ky FAIL -> NO-GO (hop de quyet dinh)
```

### 10.7. Post-UAT Actions

| Timeline | Action | Responsible |
|----------|--------|-------------|
| Trong buoi | Observer tong hop bugs realtime | QA |
| Trong 24h (sau Vong 1) | Tong hop feedback, fix P0, deploy staging | Dev + QA |
| Trong 24h (sau Vong 2) | Tinh toan tat ca metrics, hoan thanh UAT Report | QA + PO |
| Trong 48h | Fix tat ca P0 | Dev |
| Trong 1 sprint | Fix tat ca P1 | Dev |
| Truoc release | Re-verify bugs da fix | QA |
| Truoc release | Go/No-go meeting voi PO + GV + Tech Lead | PO |

---

## 11. CI/CD Pipeline Specification

### 11.1. Pipeline Stages

```
                    Developer Workflow
                         |
              +----------+----------+
              |                     |
         Pre-commit              IDE
         (local)              (lint on save)
              |
              v
         Push to branch
              |
              v
    +-------------------+
    |     PR Gate       |
    |  (auto on PR)     |
    +-------------------+
    | - Lint (ruff + eslint)
    | - Type check (mypy + tsc)
    | - Unit tests
    | - Coverage check (>=90% core)
    | - OpenAPI schema diff
    +--------+----------+
             |
             v
    +-------------------+
    |   Pre-merge       |
    |  (on approve)     |
    +-------------------+
    | - Integration tests
    | - E2E core journeys (J1-J7)
    | - Security scan (pip-audit + npm audit)
    | - Build verification (docker-compose build)
    +--------+----------+
             |
             v
    +-------------------+
    |  Pre-release      |
    | (manual trigger)  |
    +-------------------+
    | - Full regression (tat ca test groups)
    | - Performance benchmark
    | - Backup/restore drill
    | - Security checklist sign-off
    | - Privacy checklist sign-off
    +--------+----------+
             |
             v
    +-------------------+
    |   Deploy          |
    +-------------------+
    | - Deploy to staging/production
    | - Run database migrations
    +--------+----------+
             |
             v
    +-------------------+
    |  Post-deploy      |
    | (auto after deploy)|
    +-------------------+
    | - Smoke test: health + 3 core endpoints
    | - Sentry verify: no new errors trong 15 phut
    | - Notify team via Slack/email
    +-------------------+
```

### 11.2. Pre-commit (Local)

| Check | Command | Block commit? |
|-------|---------|--------------|
| Python lint | `ruff check backend/` | YES |
| Python format | `ruff format --check backend/` | YES |
| JS lint | `cd frontend && npm run lint` | YES |
| TS type check | `cd frontend && npx tsc --noEmit` | YES |
| Secrets scan | `detect-secrets scan` | YES |

### 11.3. PR Gate (Automated)

| Check | Command | Block merge? | Timeout |
|-------|---------|-------------|---------|
| Python lint + format | `ruff check && ruff format --check` | YES | 2 min |
| Python type check | `mypy backend/ --ignore-missing-imports` | YES | 5 min |
| Django unit tests | `python manage.py test --parallel` | YES | 10 min |
| Coverage | `coverage run manage.py test && coverage report --fail-under=90` | YES | 10 min |
| JS lint | `npm run lint` | YES | 2 min |
| TS type check | `npx tsc --noEmit` | YES | 3 min |
| OpenAPI diff | `python manage.py spectacular --file schema.yml && oasdiff breaking` | YES (breaking) | 2 min |
| Dependency audit | `pip-audit && npm audit --audit-level=high` | YES (high/critical) | 3 min |

### 11.4. Pre-merge (Automated)

| Check | Command | Block merge? | Timeout |
|-------|---------|-------------|---------|
| Integration tests | `python manage.py test --tag=integration` | YES | 15 min |
| E2E core journeys | Playwright/Cypress chay J1-J7 | YES | 20 min |
| Docker build | `docker-compose build` | YES | 10 min |
| Security scan | `pip-audit && npm audit` | YES (critical) | 5 min |

### 11.5. Pre-release (Manual Trigger)

| Check | Responsible | Block release? |
|-------|------------|---------------|
| Full regression suite | QA | YES |
| Performance benchmark (LT-01 toi LT-03) | QA | YES |
| Backup/restore drill | DevOps | YES |
| Security checklist (15 items) sign-off | Tech Lead | YES |
| Privacy checklist (8 items) sign-off | PO | YES |
| UAT pass (neu lan dau) | PO + GV | YES |
| OpenAPI schema review | Tech Lead | YES |

### 11.6. Post-deploy Smoke Test

```
Smoke test script (auto chay sau deploy):

1. GET /api/health/ -> expect 200 {"status": "ok"}         [BLOCK nếu fail]
2. POST /api/auth/login/ -> expect 200 (test account)      [BLOCK nếu fail]
3. GET /api/curriculum/courses/ -> expect 200               [BLOCK nếu fail]
4. GET /api/dashboard/alerts/?class_id=1 -> expect 200      [BLOCK nếu fail]
5. Sentry: 0 new errors trong 15 phut sau deploy            [WARN nếu fail]

Neu bat ky buoc BLOCK fail -> tu dong rollback
```

---

## 12. Release Sign-off Checklist

### 12.1. Master Checklist (tat ca phai PASS de release)

| # | Hang muc | Nguon verify | Sign-off boi |
|---|---------|-------------|-------------|
| R-01 | Tat ca P0 test cases pass | CI report | QA |
| R-02 | Tat ca P1 test cases pass | CI report | QA |
| R-03 | P2 test cases >= 95% pass | CI report | QA |
| R-04 | Core unit coverage >= 90% | Coverage report | Dev Lead |
| R-05 | 7 E2E core journeys (J1-J7) pass | E2E report | QA |
| R-06 | API integration tests: 46 endpoints covered | Test report | Dev Lead |
| R-07 | OpenAPI schema reviewed, no breaking changes | Schema diff | Tech Lead |
| R-08 | Security checklist 15/15 pass | Checklist doc | Tech Lead |
| R-09 | Privacy checklist 8/8 pass | Checklist doc | PO |
| R-10 | Data QA checks 12/12 pass | Data report | QA |
| R-11 | BKT parameter bounds 7/7 pass | Test report | Dev Lead |
| R-12 | Event data completeness 8/8 pass | Test report | QA |
| R-13 | Performance SLA: tat ca metrics dat nguong | Load test report | QA |
| R-14 | Backup/restore drill pass | Drill log | DevOps |
| R-15 | Rollback procedure tested | Test log | DevOps |
| R-16 | Monitoring operational (Sentry + health) | Verify | DevOps |
| R-17 | UAT pass: 12 exit criteria + 5 fail conditions clear | UAT report | PO |
| R-18 | Consent flow verified va wording approved | Manual verify | PO + Phong DT |
| R-19 | Seed data verified (course, concepts, tasks) | Manual verify | GV |
| R-20 | Docker build + deploy clean | Deploy log | DevOps |

### 12.2. Sign-off Matrix

| Vai tro | Trach nhiem sign-off | Block release? |
|---------|---------------------|---------------|
| QA Lead | R-01 toi R-05, R-10, R-12, R-13 | YES |
| Dev Lead | R-04, R-06, R-07, R-11 | YES |
| Tech Lead | R-07, R-08 | YES |
| PO | R-09, R-17, R-18 | YES |
| DevOps | R-14, R-15, R-16, R-20 | YES |
| GV Representative | R-19 | YES |

### 12.3. Release Decision Flow

```
              Tat ca R-01 -> R-20 PASS?
                      |
              +-------+-------+
              |               |
             YES             NO
              |               |
              v               v
    +----------------+  +------------------+
    | RELEASE READY  |  | IDENTIFY BLOCKERS|
    |                |  |                  |
    | -> Tag version |  | -> List fails    |
    | -> Deploy prod |  | -> Assign fixes  |
    | -> Notify team |  | -> Re-run after  |
    +----------------+  |    fix           |
                        +------------------+
```

### 12.4. Version Tagging Convention

```
Format: v{major}.{minor}.{patch}-{qualifier}

MVP pilot:
  v1.0.0-rc1    Release candidate 1
  v1.0.0-rc2    Release candidate 2 (sau fix)
  v1.0.0        Production release

Hotfix:
  v1.0.1        Hotfix sau pilot

Pre-release:
  v0.9.0-beta   Feature-complete, chua qua UAT
```

---

## 13. Go / No-Go Decision Gate

Day la **bang quyet dinh cuoi cung** truoc khi release. Tat ca cac dieu kien o day la tong hop tu 6 lop chat luong (Section 1), blocker conditions (Section 2.2), release sign-off (Section 12), va UAT exit criteria. **Khong co ngoai le, khong co trade-off.**

### 13.1. Bang dieu kien Go

Moi nhom phai dat nguong tuong ung. **Tat ca 10 nhom phai PASS** de ra quyet dinh GO.

| # | Nhom | Dieu kien Go | Nguong | Nguon verify | Lop | Tham chieu |
|---|------|-------------|--------|-------------|-----|-----------|
| G-01 | Core flows | 7 E2E journeys (J1-J7) deu pass | **100% pass** | Playwright report | L1 | R-05, Section 4 |
| G-02 | P0/P1 bugs | Khong con bat ky loi P0 hoac P1 nao open | **0** | CI report + QA tracker | L1-L2 | B1-B2, R-01, R-02 |
| G-03 | Security high+ | Khong con loi security muc high hoac critical | **0** | SEC-01 -> SEC-15, pip-audit, npm audit | L4 | B3, R-08 |
| G-04 | Privacy issues | Khong con loi privacy chua xu ly | **0** | PRI-01 -> PRI-08 | L4 | B4, R-09 |
| G-05 | Data corruption | Khong loi mat du lieu, orphan, duplicate, FK broken | **0** | DI-01 -> DI-12, BP-01 -> BP-07 | L3 | B5, R-10, R-11 |
| G-06 | Event completeness | Event core day du va co du required fields | **>= 99.5%** | EC-01 -> EC-08, EVT-003 | L6 | B7, R-12 |
| G-07 | Backup restore | Backup/restore drill pass hoan toan | **Pass** | Drill log (Section 9.2) | L5 | B8, R-14 |
| G-08 | UAT | Sinh vien hoan thanh tasks khong can ho tro | **>= 90% task success** | UAT report (Section 10.5) | L1-L2 | EXIT-01, R-17 |
| G-09 | Monitoring | Sentry + health + Prometheus deu live, alerts da arm | **Live + alerts armed** | MON-01 -> MON-05 | L5 | R-16 |
| G-10 | KPI instrumentation | Tat ca 5 KPIs do duoc, khong null/NaN | **100% do duoc** | KPI-001 -> KPI-005 | L6 | B7, R-13 |

### 13.2. Dieu kien No-Go tuyet doi

**Bat ky 1 trong 8 dieu kien duoi day con ton tai -> NO-GO ngay lap tuc**, khong can xet cac dieu kien khac. Day la nhung loi **gay hau qua nghiem trong truc tiep den sinh vien va giang vien**.

| # | Dieu kien No-Go | Hau qua neu release | Phat hien boi | Blocker Ref |
|---|----------------|---------------------|---------------|-------------|
| NG-01 | Sai adaptive rule (BKT tinh sai, pathway decision sai) | SV duoc dua vao luong hoc sai, can thiep sai nang luc | BKT-001 -> BKT-008, PATH-001 -> PATH-004 | B6 |
| NG-02 | Sai progress (mastery khong update, attempt_number sai) | SV thay tien bo gia hoac mat tien bo, mat dong luc | SUBMIT-001 -> SUBMIT-003, RETRY-003 | B6 |
| NG-03 | Sai dashboard RBAC (GV thay SV ngoai class, SV truy cap dashboard GV) | Lo thong tin hoc tap SV, vi pham privacy | RBAC-001 -> RBAC-007, ALERT-003 | B3 |
| NG-04 | Xoa/export du lieu loi (xoa nhung khong xoa het, export thieu, export PII raw) | Vi pham quyen rieng tu, mat du lieu SV | PRI-07, privacy/export tests | B5 |
| NG-05 | ETL silent failure (pipeline fail nhung khong bao loi) | KPI sai, bao cao sai, quyet dinh dua tren du lieu sai | ETL-001, nightly batch logs, Sentry | B7 |
| NG-06 | Event core khong ban (micro_task_completed, gv_action_taken, assessment_completed khong fire) | KPI khong tinh duoc, mat du lieu hoc tap, dashboard GV sai | EVT-003, EVT-005, EVT-006 | B7 |
| NG-07 | Backup restore khong pass (restore bi loi, du lieu khong khop) | Rui ro mat toan bo du lieu khi co su co | Backup drill (Section 9.2) | B8 |
| NG-08 | Release khong rollback duoc (rollback fail, du lieu bi corrupt sau rollback) | Khong the phuc hoi khi phat hien loi nghiem trong tren production | Rollback test (Section 9.3) | B9 |

### 13.3. Quy trinh ra quyet dinh

```
              +-------------------------------+
              |  KIEM TRA NO-GO TRUOC         |
              |  (NG-01 -> NG-08)             |
              +---------------+---------------+
                              |
                    Con bat ky NG nao?
                              |
                  +-----------+-----------+
                  |                       |
                 YES                     NO
                  |                       |
                  v                       v
         +----------------+    +-------------------------+
         | NO-GO NGAY     |    | KIEM TRA 10 DIEU KIEN   |
         | LAP TUC        |    | GO (G-01 -> G-10)       |
         |                |    +------------+------------+
         | -> Xac dinh NG |                |
         | -> Assign fix  |      Tat ca 10 nhom PASS?
         | -> Re-test     |                |
         +----------------+    +-----------+-----------+
                               |                       |
                              YES                     NO
                               |                       |
                               v                       v
                    +------------------+   +---------------------+
                    | >>> GO <<<       |   | NO-GO CO DIEU KIEN  |
                    |                  |   |                     |
                    | 1. Tag version   |   | -> List fails       |
                    | 2. Deploy prod   |   | -> Classify:        |
                    | 3. Notify team   |   |    Fixable < 48h?   |
                    | 4. Arm monitors  |   |    Waivable by PO?  |
                    | 5. Standby 2h    |   | -> Fix & re-gate    |
                    +------------------+   +---------------------+
```

### 13.4. Ma tran trach nhiem Go/No-Go

| Vai tro | Xac nhan nhom | Quyen veto? |
|---------|---------------|-------------|
| QA Lead | G-01, G-02, G-05, G-06, G-08 | YES -- bat ky nhom nao fail |
| Tech Lead | G-03, G-04, G-09, NG-01 -> NG-06 | YES -- bao mat, logic, data |
| DevOps | G-07, G-09, NG-07, NG-08 | YES -- infra va recovery |
| PO | G-04, G-08, G-10 | YES -- privacy va UAT |
| GV Representative | G-08 | YES -- chi voi G-08 (UAT) |

**Quyet dinh GO chi co hieu luc khi tat ca vai tro co quyen veto deu dong y.**

### 13.5. Checklist dien truoc release

```
PALP Go/No-Go Checklist
Phien ban: v____.____.____
Ngay:      ____/____/______
Moi truong: [ ] Staging  [ ] Production

=== KIEM TRA NO-GO (dung ngay neu bat ky muc nao FAIL) ===

[ ] NG-01  Adaptive rules (BKT + pathway) dung        Verified by: ________
[ ] NG-02  Progress update dung                        Verified by: ________
[ ] NG-03  Dashboard RBAC dung                         Verified by: ________
[ ] NG-04  Xoa/export du lieu hoat dong                Verified by: ________
[ ] NG-05  ETL khong silent failure                    Verified by: ________
[ ] NG-06  Event core deu fire                         Verified by: ________
[ ] NG-07  Backup restore pass                         Verified by: ________
[ ] NG-08  Rollback kha thi                            Verified by: ________

No-Go kiem tra: [ ] PASS (0 fail)  /  [ ] FAIL (list: ________________)

=== DIEU KIEN GO (chi kiem tra khi No-Go = PASS) ===

[ ] G-01  Core flows 100% pass         Ket qua: ___/7 journeys   Verified by: ________
[ ] G-02  P0/P1 bugs = 0               Ket qua: P0=___ P1=___    Verified by: ________
[ ] G-03  Security high+ = 0           Ket qua: ___/15 pass      Verified by: ________
[ ] G-04  Privacy issues = 0           Ket qua: ___/8 pass       Verified by: ________
[ ] G-05  Data corruption = 0          Ket qua: DI ___/12        Verified by: ________
                                                 BP ___/7
[ ] G-06  Event completeness >= 99.5%  Ket qua: ___.___%         Verified by: ________
[ ] G-07  Backup restore pass          Ket qua: [ ] Pass         Verified by: ________
[ ] G-08  UAT >= 90% task success      Ket qua: ___.__%          Verified by: ________
[ ] G-09  Monitoring live + armed      Ket qua: [ ] Sentry       Verified by: ________
                                                 [ ] Health
                                                 [ ] Prometheus
                                                 [ ] Alerts armed
[ ] G-10  KPI 100% do duoc            Ket qua: ___/5 KPIs       Verified by: ________

Go kiem tra: [ ] PASS (10/10)  /  [ ] FAIL (list: ________________)

=== QUYET DINH ===

[ ] GO   -> Tien hanh release
[ ] NO-GO -> Ly do: _______________________________________________

Chu ky:
  QA Lead:    __________________  Ngay: ____/____/______
  Tech Lead:  __________________  Ngay: ____/____/______
  DevOps:     __________________  Ngay: ____/____/______
  PO:         __________________  Ngay: ____/____/______
  GV Rep:     __________________  Ngay: ____/____/______
```

### 13.6. Tu dong hoa kiem tra Go/No-Go

Cac dieu kien co the tu dong kiem tra bang script `scripts/release_gate.py`:

| # | Dieu kien | Tu dong? | Cach kiem tra |
|---|----------|----------|---------------|
| NG-01 | Adaptive rules | YES | `pytest -m "not load" -k "BKT or PATH"` |
| NG-02 | Progress update | YES | `pytest -k "SUBMIT or RETRY"` |
| NG-03 | Dashboard RBAC | YES | `pytest -m security -k "RBAC or ALERT"` |
| NG-04 | Xoa/export du lieu | YES | `pytest -k "privacy or export or delete"` |
| NG-05 | ETL silent failure | YES | `pytest -m data_qa -k "ETL"` |
| NG-06 | Event core | YES | `pytest -k "EVT"` + DB query 8 event types |
| NG-07 | Backup restore | MANUAL | Drill procedure (Section 9.2) |
| NG-08 | Rollback | MANUAL | Rollback procedure (Section 9.3) |
| G-01 | Core flows | YES | `npm run test:e2e` (Playwright J1-J7) |
| G-02 | P0/P1 bugs | SEMI | Query bug tracker API |
| G-03 | Security | YES | `pytest -m security` + `pip-audit` + `npm audit` |
| G-04 | Privacy | YES | `pytest -k "PRI or consent or privacy"` |
| G-05 | Data corruption | YES | DB integrity queries (DI-01 -> DI-12) |
| G-06 | Event completeness | YES | DB query required fields (EC-01 -> EC-08) |
| G-07 | Backup restore | MANUAL | Drill procedure |
| G-08 | UAT | MANUAL | UAT report |
| G-09 | Monitoring | YES | Health + Sentry DSN + Prometheus check |
| G-10 | KPI instrumentation | YES | DB query 5 KPIs non-null |

Chay: `python scripts/release_gate.py` -> output report voi PASS/FAIL cho tung muc.

---

## 14. KPI Integrity Standard

PRD PALP chot 5 KPI cho pilot: +20% thoi gian hoc/tuan, >=70% completion micro-task, CSAT >=4.0/5, GV dung dashboard >=2x/tuan, giam 50% thoi gian phat hien SV kho. Decision gate mo rong/dung o W16.

**Day la tieu chuan nghiem ngat nhat** -- mot KPI khong dang tin con nguy hiem hon khong co KPI, vi no dua den quyet dinh pilot sai (mo rong khi chua san sang, hoac dung khi dang thanh cong).

### 14.1. Chuan bat buoc cho moi KPI

Moi KPI trong he thong phai thoa dong thoi **6 dieu kien** sau. Khong co ngoai le.

| # | Dieu kien | Dinh nghia chi tiet | Verify boi |
|---|----------|---------------------|-----------|
| KI-01 | Co owner | Moi KPI co `KPIDefinition.owner` FK den User cu the. Owner chiu trach nhiem dam bao KPI do dung va bao cao khi co bat thuong. | DB query: `KPIDefinition.objects.filter(owner__isnull=True).count() == 0` |
| KI-02 | Truy ra event/source data | `KPIDefinition.source_events` liet ke chinh xac cac event types trong `EventLog.EventName` (tru CSAT la external survey). Moi KPI value phai co `KPILineageLog` ghi lai event_count, sample_event_ids, event_date_range. | `kpi_integrity_audit` task: check traceability |
| KI-03 | Co query/reproducible definition | `KPIDefinition.query_function` la dotted import path den ham compute. `KPIDefinition.query_sql` la SQL tuong duong. Chay lai ham voi cung input phai cho cung output. | Test KPIINT-003: verify importable + callable |
| KI-04 | Khong uoc luong cam tinh | Moi KPI value den tu `EventLog`, `TaskAttempt`, `Alert`, hoac source co the audit. KPI "CSAT" den tu khao sat co structured form. Khong chap nhan gia tri nhap tay khong co bang chung. | Code review + `KPILineageLog.event_count > 0` |
| KI-05 | Baseline va intervention tach bach | `KPIDefinition.baseline_period_start/end` va `intervention_period_start/end` khong overlap. Baseline duoc lock (`lock_baseline()`) truoc khi bat dau intervention. So sanh chi hop le giua cung period type. | Validation trong `KPIDefinition.clean()` |
| KI-06 | Dashboard KPI versioned | Moi `PilotReport` co `schema_version` va `kpi_definitions_snapshot`. Khi dinh nghia KPI thay doi, `KPIVersion` ghi lai snapshot cu. Report cu van doi chieu duoc vi no luu dinh nghia tai thoi diem tao. | Test KPIINT-006 + KPIINT-011 |

### 14.2. KPI Registry -- 5 Pilot KPIs

| Code | Ten | Owner | Target | Direction | Source Events | Compute Function |
|------|-----|-------|--------|-----------|--------------|-----------------|
| `active_learning_time` | Thoi gian hoc chu dong/tuan | PO | +20% vs baseline | increase | `session_started`, `session_ended` | `_compute_active_learning_time_with_lineage` |
| `micro_task_completion` | Ty le hoan thanh micro-task | Tech Lead | >=70% | absolute | `micro_task_completed` | `_compute_completion_rate_with_lineage` |
| `csat_score` | CSAT | PO | >=4.0/5 | absolute | External survey | `_compute_csat_with_lineage` |
| `gv_dashboard_usage` | GV su dung dashboard | UX/PO | >=2x/tuan | absolute | `gv_dashboard_viewed` | `_compute_dashboard_usage_with_lineage` |
| `time_to_detect_struggling` | Thoi gian phat hien SV kho | PO + GV | -50% vs baseline | decrease | Alert creation + event timestamps | `_compute_detection_time_with_lineage` |

### 14.3. Integrity Validation Pipeline

`kpi_integrity_audit` (Celery task, chay daily) thuc hien 4 kiem tra:

| # | Check | Logic | Fail condition |
|---|-------|-------|---------------|
| IV-01 | Raw Data Traceability | Voi moi KPI, query `EventLog` trong 7 ngay cho `source_events`. Count phai > 0. | `event_count == 0` cho bat ky source event nao |
| IV-02 | Definition Drift Detection | So sanh current `KPIDefinition` fields voi `KPIVersion` snapshot moi nhat. Neu `is_locked=True`, khong field nao trong `LOCKED_FIELDS` duoc thay doi. | Field khac nhau sau khi locked |
| IV-03 | Event Tracking Gap Detection | Voi moi source event, kiem tra khoang cach giua 2 event lien tiep. Gap > 24h = unreliable. | Gap > 24h trong event stream |
| IV-04 | Tracking Bug Detection | So sanh KPI trend voi event volume trend (tu `KPILineageLog`). Neu KPI tot len nhung event giam >30%, nghi tracking bug. | KPI improved + event volume drop > 30% |

### 14.4. FAIL conditions -- KPI bi tuyen bo khong dang tin

| # | Dieu kien FAIL | Hau qua | Xu ly |
|---|---------------|---------|-------|
| KF-01 | Khong truy duoc raw data cua KPI | KPI value la gia, khong the verify | **P0 blocker** -- fix event tracking truoc khi tiep tuc pilot |
| KF-02 | KPI thay doi dinh nghia giua pilot | So sanh truoc-sau mat y nghia thong ke | **P0 blocker** -- rollback dinh nghia, tinh lai tu dau |
| KF-03 | Event tracking thieu khien KPI khong dang tin | Gap > 24h = mat du lieu, KPI bi skew | **P1** -- dieu tra gap, impute hoac loai tru period bi anh huong |
| KF-04 | Chi so tot len do bug tracking chu khong phai hanh vi that | Quyet dinh pilot sai (tuong thanh cong nhung khong phai) | **P0 blocker** -- dieu tra root cause, fix bug, tinh lai KPI |

### 14.5. KPI Lineage Model

Moi lan tinh KPI, he thong ghi `KPILineageLog`:

```
KPILineageLog:
  kpi              -> FK den KPIDefinition
  report           -> FK den PilotReport (nullable)
  week_number      -> Tuan tinh
  class_id         -> Lop hoc
  computed_value   -> Gia tri tinh duoc
  event_count      -> So event da dung de tinh
  event_date_range -> {"start": ..., "end": ...}
  sample_event_ids -> [id1, id2, ...] (10 event dau tien, de truy vet)
  computation_params -> {"max_session_minutes": 180, "cohort_size": 45, ...}
  data_quality_flags -> {"no_raw_data": true, "suspicious_improvement": {...}}
  definition_version -> Version cua KPIDefinition tai thoi diem tinh
  computed_at      -> Timestamp
```

### 14.6. Lock Protocol

```
1. THIET LAP (truoc pilot)
   - Tao KPIDefinition cho 5 KPIs voi owner, source_events, query_function
   - Cau hinh baseline_period va intervention_period
   - Review va accept bang PO + Tech Lead

2. BASELINE (W1-W2)
   - Thu thap du lieu baseline trong baseline_period
   - Chay lock_baseline(kpi_code, class_id) cho tung KPI
   - Verify: is_locked=True, baseline_value co gia tri, KPILineageLog week_number=0
   - Sau buoc nay: KHONG THE thay doi code, source_events, query_function, target_value

3. INTERVENTION (W3-W10)
   - generate_kpi_snapshot_with_integrity() tu dong:
     a. Tinh KPI value
     b. Ghi lineage
     c. Detect anomalies (flags)
     d. Tag period = "intervention"
   - Weekly report luu schema_version + kpi_definitions_snapshot

4. AUDIT (daily)
   - kpi_integrity_audit() chay tu dong
   - Ket qua ghi vao DataQualityLog(source="kpi_integrity_audit")
   - FAIL -> alert team ngay lap tuc

5. DECISION GATE (W16)
   - So sanh intervention period vs baseline
   - Chi so sanh khi: definition_version khong doi, event coverage >= 99.5%
   - KPI co data_quality_flags -> loai tru hoac giai thich trong bao cao
```

### 14.7. Test Cases cho KPI Integrity

| Test ID | Mo ta | Loai | Muc do |
|---------|-------|------|--------|
| KPIINT-001 | Moi KPI co owner (FK not null) | Unit | P0 |
| KPIINT-002 | Moi KPI truy ra source events trong EventLog | Unit | P0 |
| KPIINT-003 | query_function importable va callable | Unit | P0 |
| KPIINT-004 | Locked KPI reject thay doi definition | Unit | P0 |
| KPIINT-005 | Baseline va intervention period khong overlap | Unit | P0 |
| KPIINT-006 | PilotReport co schema_version va definitions snapshot | Unit | P1 |
| KPIINT-007 | KPI voi zero raw events -> integrity FAIL | Integration | P0 |
| KPIINT-008 | Definition change mid-pilot detected | Integration | P0 |
| KPIINT-009 | Event gap > 24h flag KPI unreliable | Integration | P1 |
| KPIINT-010 | Tracking bug pattern (KPI up, events down) flagged | Integration | P0 |
| KPIINT-011 | KPIVersion created khi thay doi definition pre-lock | Unit | P1 |
| KPIINT-012 | KPILineageLog ghi sample event IDs | Integration | P1 |
| KPIINT-013 | Baseline value locked sau lock_baseline() | Integration | P0 |

### 14.8. Mapping KPI Integrity -> QA Layers

| Dieu kien KI | Lop QA | Blocker ref |
|-------------|--------|-------------|
| KI-01 (owner) | L6 | B7 |
| KI-02 (traceability) | L6 | B7 |
| KI-03 (reproducible) | L6 | B7 |
| KI-04 (khong cam tinh) | L6 | B7 |
| KI-05 (period tach bach) | L3 + L6 | B5, B7 |
| KI-06 (versioned) | L6 | B7 |

---

## 15. Appendix

### A. Glossary

| Term | Dinh nghia |
|------|-----------|
| BKT | Bayesian Knowledge Tracing -- mo hinh xac suat uoc luong muc do thong hieu kien thuc cua SV |
| P(mastery) | Xac suat SV da nam vung 1 concept, tinh boi BKT |
| P(guess) | Xac suat SV tra loi dung khi chua thong hieu |
| P(slip) | Xac suat SV tra loi sai khi da thong hieu |
| P(transit) | Xac suat SV hoc duoc sau moi co hoi luyen tap |
| Golden vector | Chuoi input da biet ket qua dung, dung de verify BKT implementation |
| E2E | End-to-End test -- test toan bo flow tu frontend den database |
| UAT | User Acceptance Testing -- test voi nguoi dung thuc |
| NFR | Non-Functional Requirements -- yeu cau phi chuc nang |
| RBAC | Role-Based Access Control -- phan quyen theo vai tro |
| PII | Personally Identifiable Information -- du lieu ca nhan |
| SLA | Service Level Agreement -- cam ket chat luong dich vu |
| ETL | Extract, Transform, Load -- pipeline du lieu |
| CSAT | Customer Satisfaction Score |
| KPI | Key Performance Indicator |
| RACI | Responsible, Accountable, Consulted, Informed |
| Decision Gate | Diem ra quyet dinh Go/No-go trong pilot (Section 13) |

### B. Test Environment Requirements

| Thanh phan | Yeu cau |
|-----------|---------|
| Docker Engine | >= 24.0 |
| Docker Compose | >= v2.0 |
| RAM | >= 8GB (4GB minimum) |
| Disk | >= 20GB free |
| Network | Internet access (cho pip/npm install) |
| Test data | Seed data SBVL (10 concepts, 50+ tasks, 3 assessments) |
| Test accounts | 5 student, 2 lecturer, 1 admin |
| Browser | Chrome >= 120 (cho E2E tests) |

### C. PRD Requirement -> Test Group Mapping

| PRD Requirement | Test Groups | AC Verification |
|----------------|------------|-----------------|
| F1: Assessment dau vao | ASSESS-001 -> ASSESS-012, J1 | >=90% SV hoan thanh khong can ho tro |
| F2: Adaptive Pathway v1 | BKT-001 -> BKT-008, PATH-001 -> PATH-004, J2, J3 | Response <3s, retry nhat quan |
| F3: Micro-task & Milestone | CURR-001 -> CURR-010, FE-005, FE-006 | 100% task hien thi thoi luong, feedback <1s |
| F4: Wellbeing nudge | WB-001 -> WB-006, J6 | Khong gian doan flow, tracking acceptance |
| F5: Early Warning Dashboard | EW-001 -> EW-009, DASH-001 -> DASH-002, J4 | Load <3s, GV danh gia "de hieu" |
| F6: Intervention action log | ACTION-001 -> ACTION-004, J5 | Action tao event, hien thi follow-up |
| F7: Data cleaning pipeline | DQ-001 -> DQ-006, DC-001 -> DC-006, J7 | Data quality score >=70% |
| F8: Pilot analytics | KPI-001 -> KPI-005, REPORT-001 -> REPORT-002 | Bao cao W4/W10, so lieu doi chieu duoc |

### D. Test Case ID Convention

```
Format: {MODULE}-{NUMBER}

Module prefixes:
  AUTH     accounts/auth
  RBAC     accounts/RBAC
  CONSENT  accounts/consent
  ASSESS   assessment
  BKT      adaptive/BKT engine
  PATH     adaptive/pathway
  CACHE    adaptive/cache
  RETRY    adaptive/retry
  SUBMIT   adaptive/submit
  CURR     curriculum
  EW       dashboard/early warning
  ALERT    dashboard/alerts
  ACTION   dashboard/interventions
  DASH     dashboard/overview
  KPI      analytics/KPI
  REPORT   analytics/reports
  DQ       analytics/data quality
  ETL      analytics/ETL
  EVT      events
  WB       wellbeing
  FE       frontend
  SEC      security
  PRI      privacy
  DI       data integrity
  BP       BKT parameter bounds
  EC       event completeness
  DC       data cleaning
  OPS      operations
  MON      monitoring
  LT       load test
  KPIINT   KPI integrity

Example: BKT-004 = "Golden vector: 5 cau lien tuc dung -> P(mastery) tang dan"
```

### E. Tong hop so luong test cases

| Category | So test cases | Core? | Implementation file |
|----------|-------------|-------|---------------------|
| accounts (AUTH + RBAC + CONSENT) | 19 | YES | `accounts/tests/test_auth_api.py`, `accounts/tests/test_models.py` |
| assessment (ASSESS) | 12 | YES | `assessment/tests/test_assessment_api.py`, `assessment/tests/test_services.py`, `assessment/tests/test_assessment_matrix.py` |
| adaptive (BKT + PATH + CACHE + RETRY + SUBMIT) | 19 | YES | `adaptive/tests/test_bkt_engine.py`, `adaptive/tests/test_pathway_api.py`, `adaptive/tests/test_bkt_property.py`, `adaptive/tests/test_adaptive_matrix.py` |
| curriculum (CURR) | 10 | YES | `curriculum/tests/test_curriculum_api.py`, `curriculum/tests/test_models.py`, `curriculum/tests/test_progress_matrix.py` |
| dashboard (EW + ALERT + ACTION + DASH) | 18 | YES | `dashboard/tests/test_dashboard_api.py`, `dashboard/tests/test_early_warning.py`, `dashboard/tests/test_dashboard_matrix.py` |
| analytics (KPI + REPORT + DQ + ETL) | 12 | YES | `analytics/tests/test_kpi.py`, `analytics/tests/test_tasks.py` |
| events (EVT) | 10 | YES | `events/tests/test_tracking.py`, `events/tests/test_event_completeness.py` |
| wellbeing (WB) | 6 | NO | `wellbeing/tests/test_nudge.py` |
| frontend (FE) | 27 | YES | `e2e/*.spec.ts`, `src/**/*.test.ts` |
| Data integrity (DI) | 12 | YES | `tests/data_qa/test_analytics_integrity.py` |
| BKT bounds (BP) | 7 | YES | `adaptive/tests/test_bkt_engine.py` |
| Event completeness (EC) | 8 | YES | `events/tests/test_event_completeness.py` |
| Data cleaning (DC) | 6 | YES | `tests/data_qa/test_data_cleaning.py` |
| Security (SEC) | 15 | YES | `tests/security/test_authz_matrix.py`, `tests/security/test_auth.py`, `tests/security/test_idor.py`, `tests/security/test_injection.py`, `tests/security/test_data_exposure.py` |
| Privacy (PRI) | 8 | YES | `privacy/tests.py` |
| Operations (OPS) | 8 | YES | `tests/recovery/test_db_restore.py`, `tests/recovery/test_rollback.py` |
| Monitoring (MON) | 5 | YES | `tests/recovery/test_backend_restart.py` |
| KPI integrity (KPIINT) | 13 | YES | `analytics/tests/test_kpi_integrity.py` |
| Load test (LT) | 5 | YES | `tests/load/locustfile.py`, `tests/load/slo_assertions.py` |
| E2E Journeys (J1-J7) | 7 | YES | `e2e/journeys/journey-{a..f}*.spec.ts` |
| API contract (estimated) | ~217 | YES | `tests/contract/test_api_contract.py`, `tests/contract/test_negative.py`, `tests/contract/test_idempotency.py`, `tests/contract/test_request_validation.py`, `tests/contract/test_api_schema.py` |
| Product correctness (AP) | 5 | YES | `tests/integration/test_product_correctness.py` |
| Learning integrity (LI-F) | 7 | YES | `tests/integration/test_learning_integrity.py` |
| Feature criteria (F1-F5) | 18 | YES | `tests/integration/test_feature_criteria.py` |
| Security hardened (SG+SK) | 11 | YES | `tests/security/test_security_hardened.py` |
| Privacy hardened (PP+PRG) | 6 | YES | `tests/integration/test_privacy_hardened.py` |
| Observability (OB+OD) | 6 | YES | `tests/integration/test_observability.py` |
| Module edge cases (AS+AD+BD+GV) | 15 | YES | `tests/integration/test_module_edge_cases.py` |
| **Tong** | **~500 + ~217 API** | |

### F. Tham chieu tai lieu

| Tai lieu | Duong dan | Lien quan |
|---------|----------|-----------|
| PRD | [docs/PRD.md](PRD.md) | Requirements, NFRs, KPIs, Design Principles |
| Architecture | [docs/ARCHITECTURE.md](ARCHITECTURE.md) | BKT formula, caching, RBAC matrix, security |
| API Reference | [docs/API.md](API.md) | Endpoint contracts, request/response schemas |
| Data Model | [docs/DATA_MODEL.md](DATA_MODEL.md) | Entity schema, event taxonomy, privacy tiers |
| Sprint Plan | [docs/SPRINT_PLAN.md](SPRINT_PLAN.md) | Timeline, RACI, risk register, success criteria |
| Deployment | [docs/DEPLOYMENT.md](DEPLOYMENT.md) | Environments, Docker, backup, monitoring |
| Definition of Done (ticket) | [docs/DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) | Checklist D1-D12, N/A matrix, lien ket Section 1.3 |
| Test Traceability | [docs/TEST_TRACEABILITY.md](TEST_TRACEABILITY.md) | Moi test case ID -> implementation file + test function |
| UAT Script | [docs/UAT_SCRIPT.md](UAT_SCRIPT.md) | 15 tasks SV+GV, metrics, exit criteria |
| Pre-commit config | [.pre-commit-config.yaml](../.pre-commit-config.yaml) | Section 11.2 local hooks: ruff, eslint, tsc, secrets |

---

> **Document control**
> - Version: 2.3
> - Created: 2026-04-16
> - Updated: 2026-04-16 -- Them 4 edge-case matrices: AS-01..10, AD-01..10, BD-01..10, GV-01..10 (40 scenarios); them test_module_edge_cases.py (15 test classes); grand total ~717 cases
> - Author: Tech Lead
> - Reviewers: PO, QA Lead, Dev Lead, GV Representative
> - Next review: Truoc Sprint 4 kick-off
