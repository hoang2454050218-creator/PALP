---
name: openapi-update
description: OpenAPI schema baseline workflow with breaking-change detection via oasdiff. Use when adding/modifying any DRF view, serializer, or URL pattern that affects /api/schema/.
---

# OpenAPI Schema — Baseline + Breaking-Change Workflow

## When to use

- Adding/modifying a DRF view, serializer, or URL pattern
- Renaming a field, changing required status, or removing a route
- CI `openapi` job failed with `oasdiff breaking` error
- Quarterly baseline refresh

## Stack

- **drf-spectacular** generates `/api/schema/` (OpenAPI 3.1)
- **oasdiff** in CI compares PR schema vs `backend/openapi/schema-baseline.yaml`
- Breaking change blocks merge unless intentional + versioned

## What counts as breaking?

| Change | Breaking? | Mitigation |
|--------|-----------|------------|
| Add new endpoint | NO | — |
| Add new optional field | NO | — |
| Add new required field | YES | Make it optional, or version the endpoint |
| Remove field | YES | Deprecate first (mark optional, document, remove next major) |
| Rename field | YES | Add new field, keep old, document, remove next major |
| Change field type (str -> int) | YES | New endpoint or version bump |
| Remove endpoint | YES | Deprecate, document, remove next major |
| Change HTTP method | YES | Version bump |
| Tighten validation (max_length: 200 -> 100) | YES | Discuss with FE, may break clients |
| Loosen validation (max_length: 100 -> 200) | NO | Forward-compatible |
| Add response field | NO | Forward-compatible |
| Change throttle scope | NO (not in schema) | Document in CHANGELOG |

## Workflow when adding/modifying a view

### 1. Document custom actions with `@extend_schema`

```python
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

class PathwayViewSet(ModelViewSet):
    @extend_schema(
        summary="Get next micro-task in adaptive pathway",
        description="Returns the next unmastered concept's micro-task based on BKT state.",
        parameters=[
            OpenApiParameter(name="course_id", type=int, required=True, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: NextTaskSerializer,
            404: OpenApiResponse(description="No more micro-tasks (mastery complete)"),
        },
        tags=["adaptive"],
    )
    @action(detail=False, methods=["get"], url_path="next-task")
    def next_task(self, request):
        ...
```

### 2. Run schema generation locally

```bash
just openapi
# Or manually:
docker exec cnhnha-backend-1 python manage.py spectacular --file /tmp/schema.yaml
docker cp cnhnha-backend-1:/tmp/schema.yaml backend/openapi/schema-baseline.yaml
```

### 3. Run oasdiff locally before push

```bash
# Install oasdiff once
curl -sSL "https://github.com/tufin/oasdiff/releases/download/v1.10.21/oasdiff_1.10.21_linux_amd64.tar.gz" | sudo tar xz -C /usr/local/bin

# Compare new schema against committed baseline
docker exec cnhnha-backend-1 python manage.py spectacular --file /tmp/schema-new.yaml
git show HEAD:backend/openapi/schema-baseline.yaml > /tmp/schema-old.yaml
oasdiff breaking /tmp/schema-old.yaml /tmp/schema-new.yaml
```

If clean: commit both code + updated `schema-baseline.yaml`.
If breaking: see "Handling breaking change" below.

### 4. Commit baseline with code

The baseline lives at `backend/openapi/schema-baseline.yaml` — commit it in the same PR as the code change so CI's `oasdiff breaking` passes.

## Handling intentional breaking change

1. Discussion in issue + ADR (`docs/adr/00X-<slug>.md`) explaining why
2. PO + maintainer approval before merge
3. Bump API version (`/api/v2/` for major change, or deprecate field with timeline)
4. Add `OPENAPI_RELAXED=1` env var to CI step temporarily — document in PR body
5. Update `docs/API.md` with migration guide for clients
6. Notify FE team + external API consumers

For deprecation:

```python
class OldSerializer(ModelSerializer):
    legacy_field = serializers.CharField(
        help_text="DEPRECATED: use `new_field` instead. Will be removed in v2.0 (2026-Q4).",
    )
    new_field = serializers.CharField()
```

## Schema testing

```python
@pytest.mark.contract
class TestSchemaContract:
    def test_schema_endpoint_accessible(self, admin_api):
        # In prod, schema is admin-only
        response = admin_api.get("/api/schema/")
        assert response.status_code == 200

    def test_my_endpoint_in_schema(self, admin_api):
        response = admin_api.get("/api/schema/")
        schema = yaml.safe_load(response.content)
        assert "/api/adaptive/pathway/next-task/" in schema["paths"]

    def test_response_matches_serializer(self, student_api):
        response = student_api.get("/api/adaptive/pathway/next-task/")
        # Validate response shape matches NextTaskSerializer
        ...
```

Mark with `@pytest.mark.contract` (CI runs separately).

## Common pitfalls

- Forgetting to commit updated `schema-baseline.yaml` -> CI passes locally, fails on PR
- `@extend_schema(responses={200: dict})` -> opaque schema, FE can't generate types
- Custom action without `@extend_schema` -> appears as `Operation_*` placeholder
- Renaming serializer class -> breaks schema component name -> false-positive breaking change. Use `extend_schema(component_name="...")` to keep stable name.
- Changing `serializer.Meta.fields` order -> usually not breaking but can churn baseline. Keep alphabetical or by importance, document choice.

## Reference

- drf-spectacular docs: <https://drf-spectacular.readthedocs.io>
- oasdiff: <https://github.com/tufin/oasdiff>
- PALP API doc: `docs/API.md`, `docs/API_CONTRACT.md`
- ADR-007 (drf-spectacular + oasdiff): `docs/adr/007-spectacular-oasdiff.md`
- Baseline: `backend/openapi/schema-baseline.yaml`
- CI job: `.github/workflows/ci.yml::openapi`
