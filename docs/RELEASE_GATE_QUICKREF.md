# PALP Release Gate — Quick Reference

> Pin this. Read before every release candidate.
> Full details: [QA_STANDARD.md](QA_STANDARD.md) | [TEST_TRACEABILITY.md](TEST_TRACEABILITY.md)

---

## 5 absolutes — violate any one = NO-GO

| # | Rule | If violated |
|---|------|-------------|
| 1 | **Khong duoc sai logic hoc tap** | BKT sai, pathway sai, intervention sai concept, alert sai = SV bi can thiep sai |
| 2 | **Khong duoc sai du lieu** | Mat data, orphan, duplicate, progress gia = quyet dinh pilot sai |
| 3 | **Khong duoc sai phan quyen** | SV thay lop khac, GV thay lop khac, export khong kiem quyen = vi pham privacy |
| 4 | **Khong duoc khong do duoc** | Event khong ban, KPI null, tracking gap = khong biet pilot thanh cong hay that bai |
| 5 | **Khong duoc khong rollback duoc** | Backup fail, rollback fail = rui ro mat toan bo du lieu |

---

## 5 modules phai test sau nhat

| Module | Tai sao | Key tests | Coverage |
|--------|---------|-----------|----------|
| **Assessment** | Diem sai = profile sai = lo trinh sai tu dau | ASSESS-001..012, AS-01..10, F1-01..08 | >= 90% |
| **Adaptive + BKT** | Logic hoc tap sai = can thiep su pham sai | BKT-001..008, PATH-001..004, AD-01..10, LI-F01..06 | >= 90% |
| **Progress / Backward Design** | Progress gia = SV tuong dat khi chua dat | CURR-001..010, BD-01..10, F3-01..06 | >= 90% |
| **Early Warning Dashboard** | Alert sai = GV can thiep sai = hai SV | EW-001..009, GV-01..10, F4-01..06 | >= 90% |
| **ETL + Privacy** | Du lieu ban = KPI sai; privacy loi = vi pham phap luat | DC-01..06, PRI-01..12, PP-01..06, F5-01..06 | >= 90% |

---

## 5 thu phai co truoc pilot

| # | Item | Verify bang | Sign-off |
|---|------|------------|----------|
| 1 | **Backup/restore drill pass** | `scripts/backup_db.sh` -> drop -> restore -> verify counts + login + mastery | DevOps |
| 2 | **Security checklist 21/21 pass** | SEC-01..21 + SK-01..06 = 0 violations | Tech Lead |
| 3 | **Event tracking hoan chinh** | 8 event types fire + EC-01..08 pass + completeness >= 99.5% | QA |
| 4 | **UAT pass voi SV/GV** | 2 vong, 15 tasks, SUS >= 80, task success >= 90%, 0 dead-end | PO + GV |
| 5 | **Go/No-Go checklist co chu ky** | NG-01..08 = 0 fail, G-01..10 = all pass, 5 vai tro ky | All |

---

## Lenh chay nhanh

```bash
# Release gate (tu dong kiem tra NG + G conditions)
python scripts/release_gate.py

# Chi kiem tra DB + infra (khong chay test suite)
python scripts/release_gate.py --skip-tests

# In pre/post release checklist
python scripts/release_checklist.py --phase both

# Chay tat ca backend tests theo marker
pytest -m "not load"                    # Unit + integration (khong load)
pytest -m integration                   # Integration only
pytest -m security                      # Security only
pytest -m data_qa                       # Data QA only
pytest -m recovery                      # Recovery only
pytest -m contract                      # API contract only

# Frontend
npm run test:run                        # Vitest unit
npm run test:e2e                        # Playwright E2E (J1-J7 + Privacy)
```

---

## Khi nghi ngo — hoi 3 cau

1. **Neu BKT sai, SV se bi anh huong the nao?** -> Neu co -> P0, dung sprint fix ngay
2. **Neu du lieu nay mat, co khoi phuc duoc khong?** -> Neu khong -> chay backup drill truoc
3. **Neu GV nhan canh bao nay, ho se lam gi?** -> Neu khong hanh dong duoc -> fix reason/evidence

---

> `python scripts/release_gate.py` -> PASS thi release. FAIL thi fix.
> Khong co ngoai le. Khong co trade-off.
