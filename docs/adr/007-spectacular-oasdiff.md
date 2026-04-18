# ADR-007: drf-spectacular + oasdiff thay vì manual OpenAPI

* Status: Accepted
* Date: 2026-04
* Deciders: Backend Lead, QA Lead
* Tags: api, contract-testing, ci

## Context

PALP cần OpenAPI 3.0 spec cho:
* Frontend type generation (TypeScript client).
* API docs cho lecturer/researcher consume data.
* Contract testing chặn breaking changes accidentally.

## Decision

* Sử dụng **drf-spectacular** auto-generate spec từ DRF view + serializer.
* Baseline `backend/openapi/schema-baseline.yaml` commit vào git.
* CI step `oasdiff breaking baseline.yaml current.yaml` reject mọi
  breaking change (remove field, change type, narrow enum).
* Document manual `@extend_schema` decorator cho custom view không inferable.

## Consequences

### Positive

* Spec luôn đồng bộ với code thực, không lệch như manual write.
* CI gate breaking change → an toàn cho frontend consumer.
* Swagger UI + Redoc embed vào docs site cho researcher tự khám phá.

### Negative

* `@extend_schema` cho non-trivial view tốn boilerplate.
* drf-spectacular cảnh báo nhiều cho serializer dùng `SerializerMethodField`
  không có type hint. Mitigation: `OPENAPI_RELAXED=1` cho dev, strict cho CI.

## References

* `backend/openapi/schema-baseline.yaml`
* `.github/workflows/ci.yml` `openapi` job
* `backend/palp/settings/base.py` `SPECTACULAR_SETTINGS`
