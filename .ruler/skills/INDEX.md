# Skills Index

Quick discovery for AI agents. Read the relevant `SKILL.md` when the trigger applies.

## Foundational skills (existing)

| Skill | Trigger | Reads |
|-------|---------|-------|
| **bkt-engine** | Editing `backend/adaptive/engine.py`, BKT params, mastery state | `backend/adaptive/`, `PALP_BKT_DEFAULTS` |
| **privacy-gate** | New endpoint touching PII, consent flow, audit prefix | `backend/privacy/`, `AUDIT_SENSITIVE_PREFIXES` |
| **rbac-check** | New `APIView` / `ViewSet`, `get_queryset` change | `backend/<app>/views.py`, `accounts/permissions.py` |
| **release-gate** | Preparing release, running `scripts/release_gate.py`, D1-D12 review | `docs/DEFINITION_OF_DONE.md`, `scripts/release_gate.py` |
| **event-taxonomy** | Calling `events.services.audit_log`, adding new event_name | `backend/events/`, `EventLog.EVENT_CHOICES` |
| **migration-runbook** | `python manage.py makemigrations`, model field add/drop/rename | `backend/*/migrations/`, `docs/MIGRATION_RUNBOOK.md` |
| **frontend-component** | New component in `frontend/src/components/`, Radix wrapper | `frontend/src/components/ui/`, `cn()` helper |
| **celery-task** | New task in `backend/<app>/tasks.py`, beat schedule | `backend/palp/celery.py`, retry/timeout config |
| **incident-response** | Privacy/security alert, P0/P1 triage, post-mortem | `docs/PRIVACY_INCIDENT.md`, `PALP_PRIVACY.SLA_HOURS` |
| **openapi-update** | DRF view/serializer change, `oasdiff breaking` failure | `backend/openapi/schema-baseline.yaml`, `@extend_schema` |
| **pr-review** | Reviewing teammate PR or self-review | `.github/PULL_REQUEST_TEMPLATE.md`, all D-items |

## v3 Roadmap skills (P0–P6)

Skills introduced for the AI-Coach upgrade roadmap (v3.0). See [`docs/AI_COACH_ARCHITECTURE.md`](../../docs/AI_COACH_ARCHITECTURE.md) for context.

### Foundation Science (P0)

| Skill | Trigger | Reads |
|-------|---------|-------|
| **causal-experiment** | Proposing/running A/B with uplift, CUPED, doubly-robust; before any feature rollout | `backend/causal/`, [PUBLICATION_ROADMAP.md](../../docs/PUBLICATION_ROADMAP.md) |
| **fairness-audit** | Before deploy of any ML/clustering; per release CI gate | `backend/fairness/`, `scripts/fairness_release_check.py` |

### Sensing + Risk (P1)

| Skill | Trigger | Reads |
|-------|---------|-------|
| **signals-pipeline** | Modifying `frontend/src/lib/sensing/`, `backend/signals/`, signal taxonomy | [SIGNAL_TAXONOMY.md](../../docs/SIGNAL_TAXONOMY.md), `PALP_SIGNALS` |
| **risk-scoring** | Modifying weights, components in `backend/risk/`; integration với `dashboard.compute_early_warnings` | `backend/risk/`, `PALP_RISK_WEIGHTS` |

### Peer Engine (P3)

| Skill | Trigger | Reads |
|-------|---------|-------|
| **peer-engine** | Modifying `backend/peer/` (cohort, reciprocal match, herd cluster, frontier) | [PEER_ENGINE_DESIGN.md](../../docs/PEER_ENGINE_DESIGN.md), `PALP_PEER` |

### Hybrid Coach + Emergency (P4)

| Skill | Trigger | Reads |
|-------|---------|-------|
| **coach-safety** | Modifying `backend/coach/llm/`, system prompts, tool registry, safety guardrails | [COACH_SAFETY_PLAYBOOK.md](../../docs/COACH_SAFETY_PLAYBOOK.md), [RED_TEAM_PLAYBOOK.md](../../docs/RED_TEAM_PLAYBOOK.md) |
| **llm-routing** | Modifying intent detection, cloud/local routing rules, adding intent | `backend/coach/llm/router.py`, `SENSITIVE_INTENTS` |
| **emergency-response** | Modifying `backend/emergency/`, counselor flow, escalation chain | [EMERGENCY_RESPONSE_TRAINING.md](../../docs/EMERGENCY_RESPONSE_TRAINING.md), `PALP_EMERGENCY` |

### Intelligence Upgrade (P5)

| Skill | Trigger | Reads |
|-------|---------|-------|
| **dkt-engine** | Modifying `backend/dkt/`, SAKT/AKT training, shadow deployment vs BKT v2 | [DIFFERENTIAL_PRIVACY_SPEC.md](../../docs/DIFFERENTIAL_PRIVACY_SPEC.md), [model_cards/](../../docs/model_cards/) |

### Advanced Intelligence & Governance (P6)

| Skill | Trigger | Reads |
|-------|---------|-------|
| **xai-interpretation** | Adding/modifying explanation for any ML model (SHAP, attention, counterfactual) | `backend/explainability/`, GDPR Art.22 |
| **spaced-repetition** | Modifying `backend/spacedrep/`, FSRS scheduler, CLT tuning, ZPD scaffolding | [LEARNING_SCIENCE_FOUNDATIONS.md](../../docs/LEARNING_SCIENCE_FOUNDATIONS.md) sections 2.6–2.9 |
| **affect-analysis** | Modifying `backend/affect/`, frontend keystroke/facial trackers; 3-tier consent workflow | [PRIVACY_V2_DPIA.md](../../docs/PRIVACY_V2_DPIA.md) sections 3.11–3.13 |
| **instructor-copilot** | Modifying `backend/instructor_copilot/`, auto-generate/grade/feedback drafts (draft-must-approve) | [MULTISTAKEHOLDER_GUIDE.md](../../docs/MULTISTAKEHOLDER_GUIDE.md) section 3 |

## How agents discover & use skills

1. Agent reads the **trigger** column to decide if a skill is relevant.
2. Reads the matching `SKILL.md` (progressive disclosure — only when needed, saves context window).
3. Follows the playbook step-by-step.

## Adding a new skill

```bash
mkdir -p .ruler/skills/my-skill
cat > .ruler/skills/my-skill/SKILL.md <<'EOF'
---
name: my-skill
description: One-sentence trigger.
---

# My Skill

## When to use
- ...

## Workflow
1. ...
EOF
# Update this INDEX.md with a new row
npm run ruler:apply
```

The frontmatter `description` field is what most agents read first — keep it action-oriented and specific to the trigger condition.
