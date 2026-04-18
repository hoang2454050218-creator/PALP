# ADR-004: Fernet field-level encryption thay vì pgcrypto

* Status: Accepted
* Date: 2026-04
* Deciders: Security Lead, Privacy Officer
* Tags: security, privacy, pii

## Context

PALP lưu PII của sinh viên: `student_id` (mã sinh viên DAU 8-10 ký tự),
`phone`, `email`. Theo PDPA Việt Nam (draft 2024) và GDPR (cho potential EU
collaboration), PII phải được bảo vệ at-rest.

Hai phương án:
1. **pgcrypto** trong Postgres: `pgp_sym_encrypt()` — encryption ở DB layer,
   transparent với app.
2. **Fernet (cryptography lib)**: encryption ở app layer, custom Django field.

## Decision

Sử dụng **Fernet** với custom `EncryptedCharField` trong
`accounts/encryption.py`. Lý do:

* App layer encryption cho phép key rotation không cần `UPDATE` toàn bộ rows.
* Backend Postgres dump/restore không expose plaintext (giảm attack surface
  cho ops team).
* `MultiFernet` hỗ trợ rotation: thêm key mới đầu tuple, decrypt với mọi
  key cũ, encrypt với key mới.
* Đi kèm `student_id_hash` SHA256 cho lookup nhanh không cần decrypt.

Key management:
* `PII_ENCRYPTION_KEY` env var, base64-encoded 32 bytes.
* Production: rotate 90 ngày qua HashiCorp Vault hoặc Doppler (xem
  `docs/POST_PILOT_ROADMAP.md` SSO/Vault section).
* Pilot: rotate manual với `MultiFernet` qua `manage.py rotate_pii_keys`.

## Consequences

### Positive

* PII không bao giờ ghi plaintext vào disk (Postgres files, backups).
* Key rotation không cần downtime hoặc full table rewrite.
* Lookup nhanh qua `student_id_hash` (indexed).

### Negative

* Mọi query lọc theo `student_id` thực phải đi qua hash hoặc decrypt-then-filter.
* Key management trở thành single point of failure: mất key = mất toàn bộ PII.
  Mitigation: backup key trong sealed envelope offline + Shamir secret sharing.
* App phải có key trong memory → memory dump tấn công khả thi.
  Mitigation: container limited memory + AppArmor profile + container scan.

## Alternatives considered

* **pgcrypto + symmetric key in Postgres**: key cũng phải lưu đâu đó,
  thường trong app config — không cải thiện security mấy.
* **AWS KMS / Google Cloud KMS**: vendor lock-in + chi phí + cần network
  call mỗi encrypt/decrypt.
* **Hashing-only (one-way)**: không phục hồi được PII cho export/admin.

## References

* `backend/accounts/encryption.py` `EncryptedCharField`, `MultiFernet`
* `backend/accounts/models.py` `User.student_id` (encrypted), `student_id_hash`
* RFC 4880 (OpenPGP), Fernet spec
