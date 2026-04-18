# PALP Governance

Tài liệu này mô tả cấu trúc quản trị, vai trò, và quy trình ra quyết
định cho dự án PALP.

## Mission

Cung cấp nền tảng học tập thích ứng cá nhân hóa miễn phí, mã nguồn mở,
respecting privacy của sinh viên Việt Nam, bắt đầu từ pilot tại Đại học
Kiến trúc Đà Nẵng và mở rộng cho cộng đồng EdTech Việt Nam.

## Roles

### Maintainer
Người được chỉ định có quyền merge PR, manage release, và đại diện
project trong public space.

**Responsibilities**:
* Review PR trong 48h business hour.
* Triage issue trong 24h.
* Maintain CI green trên `master` branch.
* Tham gia weekly sync (1h/tuần).
* Tham gia release planning (2h/release).

**Becoming a Maintainer**:
* ≥10 PR merged trong 6 tháng.
* ≥3 substantive code review trong 3 tháng.
* Sponsor từ existing maintainer.
* Approval từ ≥2 existing maintainer.

### Core Contributor
Contributor có ≥3 PR merged và đang active trong project.

**Responsibilities**:
* Tham gia design discussion.
* Self-assign issue và PR.
* Review PR trong area expertise.

**Becoming Core Contributor**:
* ≥3 PR merged.
* Tự sign-up qua issue "I want to be a core contributor".

### Contributor
Bất kỳ ai đã merge ≥1 PR.

### User
Người sử dụng PALP — sinh viên, giảng viên, researcher.

## Current Maintainers

| Name | GitHub | Role | Area | Email |
|------|--------|------|------|-------|
| TBD (post-pilot) | @palp-team | Lead | Architecture | tech@palp.dau.edu.vn |

## Decision Making

### Lazy Consensus
Mặc định: PR open ≥3 ngày, không có objection từ maintainer → có thể merge
sau 1 review.

### Lazy Majority
Decision lớn (ADR, major refactor, breaking change): vote +1/-1/+0 trong
issue trong 7 ngày, simple majority quyết định.

### Veto
Maintainer có quyền veto PR với justification cụ thể (security risk,
architectural conflict). Veto override bằng 2/3 maintainer vote.

### Tie-breaker
Khi tie 50/50, Lead Maintainer quyết định (TBD).

## Release Process

* **Cadence**: theo demand, mặc định mỗi 4 tuần.
* **Versioning**: SemVer 2.0 (`major.minor.patch`).
* **Process**:
  1. Cut branch `release/X.Y` từ `master`.
  2. Run `scripts/release_gate.py` — phải PASS toàn bộ.
  3. Tag `vX.Y.Z`, semantic-release tự generate `CHANGELOG.md`.
  4. Build + sign image, upload SBOM.
  5. Deploy staging → soak 2 ngày → deploy production.
  6. Post-mortem tại weekly sync nếu rollback.

## Code of Conduct

Mọi participant phải tuân theo `CODE_OF_CONDUCT.md`. Maintainer enforce
qua warning → temporary ban → permanent ban.

## Privacy & Data

PALP xử lý PII của sinh viên. Mọi maintainer phải:
1. Sign Data Processing Agreement (DPA) với PALP.
2. Hoàn thành privacy training (đầu năm).
3. Không export production data sang local/personal device.

## Conflict Resolution

1. **Direct discussion** giữa các bên (24h).
2. **Maintainer mediation** nếu không resolve (72h).
3. **Code of Conduct committee** nếu involve harassment.

## Funding & Resources

Pilot tài trợ bởi DAU. Phase 2 dự kiến từ:
* Bộ Giáo dục Đào tạo (đề án EdTech 2026-2030).
* Open Collective public donation.
* Industry sponsor (FPT, VNG, CMC).

Maintainer KHÔNG nhận compensation cá nhân từ project funding (volunteer).

## Trademark

"PALP" và logo là registered trademark của Đại học Kiến trúc Đà Nẵng. Sử
dụng cho fork hoặc derivative phải có permission bằng văn bản.

## Forking

Code Apache 2.0 → có thể fork tự do. Để giữ tên "PALP", maintain link upstream
và tuân theo trademark policy.

## Changes to This Document

Sửa governance qua PR + lazy majority vote 14 ngày.

## Contact

* General: `palp@dau.edu.vn`
* Security: `security@palp.dau.edu.vn`
* Conduct: `conduct@palp.dau.edu.vn`
