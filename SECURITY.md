# Security Policy

PALP coi trọng bảo mật của hệ thống và dữ liệu sinh viên. Tài liệu này
mô tả cách báo cáo lỗ hổng và policy hỗ trợ phiên bản.

## Supported Versions

Phiên bản hiện được active hỗ trợ vá lỗi bảo mật:

| Version | Supported | End of Life |
|---------|-----------|-------------|
| 1.x (pilot) | Yes | TBD (sau pilot W10) |
| 0.x (beta) | No | 2026-04 |

## Reporting a Vulnerability

**KHÔNG** mở GitHub Issue công khai cho lỗ hổng bảo mật.

### Cách báo cáo

1. Email `security@palp.dau.edu.vn` với:
   * Mô tả lỗ hổng (loại, tác động, mức độ).
   * Reproduction step chi tiết.
   * Proof-of-concept (nếu có) — không thực hiện trên production.
   * Phiên bản bị ảnh hưởng.
   * Suggested fix (nếu có).

2. PGP encrypt message với key dưới đây (optional nhưng khuyến nghị
   cho sensitive disclosure):

```
PGP fingerprint: TBD (publish khi setup HashiCorp Vault Sprint 5)
```

3. Hoặc dùng GitHub Security Advisory private (nếu repo public):
   `Security` tab → `Report a vulnerability`.

### SLA

| Severity | Acknowledgment | Patch | Disclosure |
|----------|---------------|-------|------------|
| **Critical** (RCE, auth bypass, PII leak) | 24h | 7 days | 14 days post-patch |
| **High** (XSS, CSRF, IDOR) | 48h | 14 days | 30 days post-patch |
| **Medium** (info disclosure, denial of service) | 72h | 30 days | 60 days post-patch |
| **Low** (best practice violation) | 1 week | next release | with release notes |

### Process

1. **Triage** trong SLA acknowledgment timeframe.
2. **Investigation** với reporter, có thể request thêm thông tin.
3. **Fix** trên branch private + test private staging.
4. **CVE assignment** (nếu Critical/High) qua MITRE.
5. **Release** patch + advisory.
6. **Disclosure** sau timeline thỏa thuận với reporter.

### Bug Bounty

Pilot phase 1 chưa có bug bounty chính thức. Critical/High issue được
ghi nhận trong `docs/security/HALL_OF_FAME.md` (sau pilot).

Phase 2 plan: tham gia HackerOne hoặc Intigriti private invite-only,
reward range $100-$1000 USD theo severity.

## Safe Harbor

Chúng tôi cam kết không pursue legal action với security researcher who:

1. Test trên môi trường staging hoặc local của họ, không production.
2. Không expose, modify, hoặc destroy data của user khác.
3. Không thực hiện DoS hoặc spam trên production.
4. Disclosure responsibly theo SLA trên.
5. Không phát hành PoC công khai trước khi patch released.

## Out of Scope

Các finding KHÔNG được coi là security vulnerability:

* Best practice không tuân theo (ví dụ thiếu DMARC) — gửi qua issue thường.
* Lỗi hiển thị (UI bug không liên quan permission).
* Self-XSS yêu cầu social engineering.
* Đoán mật khẩu trên login form (đã có rate limit).
* Phiên bản dependency có CVE nhưng không có lỗ hổng exploitable trong PALP.

## Security Practices Trong Code

Khi đóng góp code:

* **Không** commit secret (key, password, token). Dùng `.env` + ignore.
* **Validation** mọi user input trên backend (DRF serializer).
* **Authorization** check trên view, không chỉ frontend hide.
* **Idempotency** cho POST/PUT/PATCH critical (xem `palp/idempotency.py`).
* **Audit log** cho action sensitive (xem `accounts/audit.py`).

## Security Stack

* **Encryption**: Fernet (PII) + TLS 1.3 (transport) + HSTS preload.
* **Auth**: JWT httpOnly cookie + refresh rotation + blacklist.
* **CSRF**: SameSite=Strict cookie + CSRF middleware.
* **CORS**: explicit allowlist, no wildcard.
* **Rate limit**: DRF throttle + Nginx limit_req + django-axes brute force.
* **Headers**: CSP + X-Frame-Options DENY + nosniff + referrer-policy.
* **Audit**: AuthAuditMiddleware + AuditMiddleware + structured log.
* **Backup**: GPG AES256 encrypt + S3 off-site + weekly restore drill.
* **Supply chain**: Trivy + Syft SBOM + Cosign sign + CodeQL + Semgrep.
* **CSP**: connect-src 'self' (proxy through Next.js).

## Acknowledgments

Cảm ơn các security researcher đã đóng góp việc bảo vệ PALP. Hall of Fame
sẽ được publish tại `docs/security/HALL_OF_FAME.md` sau pilot.
