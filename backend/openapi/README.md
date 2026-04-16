# OpenAPI baseline

- **Committed file:** `schema-baseline.yaml` — contract reference for CI breaking-change detection.
- **Regenerate locally** (after dependency install):

  ```bash
  cd backend
  export OPENAPI_RELAXED=1   # allow export while @extend_schema coverage grows
  export DJANGO_SETTINGS_MODULE=palp.settings.development
  python manage.py spectacular --file openapi/schema-baseline.yaml
  ```

- **CI:** `oasdiff breaking openapi/schema-baseline.yaml` against a freshly generated schema. Intentional API changes must update this file in the same PR.
