# Universal Coding Standards

Apply to all languages, all files. Override only if a language-specific rule contradicts.

## Style

- Clean, readable, consistent style across the project.
- Prefer self-explanatory code over comments. Comments only explain non-obvious **intent**, **trade-offs**, or **constraints** — never narrate what the code does.
- Bad comments to avoid: `// Import the module`, `// Define the function`, `// Increment the counter`, `# Loop through items`, `# Return result`.

## Structure & Reusability

- **Single responsibility**: each function/class/module does one clear task.
- **No duplication**: extract shared logic into utilities (`backend/<app>/utils.py`, `frontend/src/lib/`, `frontend/src/hooks/`). If you copy-paste, refactor instead.
- **Modular**: prefer small, composable units. Avoid god-objects, mega-functions, or files >500 LOC.
- **Reusable components/utilities**: when adding a UI primitive or backend helper, check existing `frontend/src/components/ui/` and `backend/<app>/utils.py` first.

## Naming

- Consistent across layers: a database column `mastery_p` should appear as `mastery_p` in serializer, `masteryP` in TypeScript DTO. Document the mapping in the serializer.
- Python: `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- TypeScript: `camelCase` for variables/functions, `PascalCase` for components/types/interfaces, `UPPER_SNAKE_CASE` for constants.
- Files: `snake_case.py`, `kebab-case.tsx` for components, `PascalCase.tsx` for component-as-default-export (project default).
- Database: `snake_case` for tables and columns, plural for tables (`event_logs`, `bkt_states`).

## No Hard-coding

- Magic numbers, URLs, API paths, secrets — extract into:
  - Backend: `backend/palp/settings/*.py`, `os.environ.get("KEY", default)`
  - Frontend: `process.env.NEXT_PUBLIC_*`, `frontend/src/lib/config.ts`
  - Constants module: `backend/<app>/constants.py`, `frontend/src/lib/constants.ts`
- Reuse existing components/utilities before writing a new one.
- Reference existing config (e.g. `PALP_BKT_DEFAULTS`, `PALP_PRIVACY`, throttle scopes in `palp/settings/base.py`).

## Backward Compatibility

- Do not break existing flow or logic.
- Do not remove API routes, change response types, add required fields, or change HTTP methods without versioning.
- Migrations must be backward-compatible (see `migration-runbook` skill).
- Environment variable defaults: keep old default working when adding new var.

## Side Effects

- Predictable behavior: given the same inputs, function returns the same output (where possible).
- I/O at the edges (views, tasks, scripts), pure logic in the middle (`engine.py`, `services.py`, `utils.py`).
- Avoid hidden global state. Pass dependencies explicitly.
- Idempotent Celery tasks: re-running must produce the same result.

## Architecture & Naming Convention Adherence

- Follow the existing module structure (`backend/<app>/{models,views,serializers,urls,services,tasks,permissions}.py`).
- New endpoints go under `/api/<app>/<resource>/` (kebab-case URL).
- New Celery task lives in `backend/<app>/tasks.py`.
- New React component lives in `frontend/src/components/<feature>/<ComponentName>.tsx` or `frontend/src/components/ui/<primitive>.tsx`.
- New Zustand store: `frontend/src/stores/<domain>Store.ts`.

## When in doubt

1. Search for an existing pattern (`Grep` "similar feature").
2. Read the relevant rule file (`02-django-backend.md`, `03-nextjs-frontend.md`, ...).
3. Check the closest existing file for naming/structure conventions.
4. Ask in PR or issue if still unsure.
