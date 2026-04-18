# ADR-005: docker-compose cho pilot, K8s cho phase 2

* Status: Accepted
* Date: 2026-04
* Deciders: Tech Lead, Platform Lead
* Tags: infrastructure, deployment, scalability

## Context

PALP cần platform deployment đơn giản cho pilot 10 tuần ở DAU (60-90 SV,
1 server VPS), nhưng cũng có roadmap mở rộng đa trường (phase 2: 5 trường,
~2500 SV).

## Decision

* **Pilot (W1-W10)**: `docker-compose` single-host trên VPS, blue-green
  deploy qua container suffix.
* **Phase 2**: K8s (Helm chart starter trong `infra/k8s/helm/palp/`),
  External Secrets Operator, HPA cho backend + celery worker, multi-AZ.

Foundation chuẩn bị sẵn:
* Image multi-stage non-root → ready for K8s pod security policies.
* Health endpoints liveness/readiness/deep → mapped sang K8s probes.
* Settings env-driven 100% → 12-factor compatible.
* Helm chart starter scaffold trong Sprint 4 (deferred trong pilot).

Migration plan: documented trong `docs/POST_PILOT_ROADMAP.md` `K8s migration`
section.

## Consequences

### Positive

* Pilot deploy <30 phút từ git push đến live, ops team không cần học K8s.
* Cost VPS pilot ~$30/tháng vs K8s cluster ~$200+/tháng cho cùng workload.
* Easier debugging với `docker logs` + shell exec.

### Negative

* Pilot không có HA: VPS down = system down. Mitigation: monitoring + on-call,
  recovery runbook (`docs/RELEASE_RUNBOOK.md`).
* Manual scaling: thêm trường = upgrade VPS, không auto-scale.
* Single host = single point of failure. Mitigation: hourly DB backup
  off-site (Wave 1 done), restore drill weekly (Wave 1 done).

## Alternatives considered

* **K8s từ đầu**: over-engineered, ops team chưa quen, làm tăng nguy cơ
  pilot bị block bởi infra issues thay vì pedagogy issues.
* **Serverless (Lambda + Aurora)**: vendor lock-in, cold start gây UX kém
  cho student làm bài (latency spike).
* **Bare-metal Django + systemd**: quá thủ công, khó reproduce env.

## References

* `docker-compose.yml` (dev), `docker-compose.prod.yml` (production)
* `backend/Dockerfile` (multi-stage non-root)
* `docs/DEPLOYMENT.md`
* `infra/k8s/helm/palp/` (scaffold trong Sprint 4)
