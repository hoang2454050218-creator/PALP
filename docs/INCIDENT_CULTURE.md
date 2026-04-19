# Incident Culture — Blameless Postmortem & Responsible Disclosure

> Văn hoá xử lý incident, postmortem, và disclosure cho PALP. Áp dụng cho cả technical incident (bug, outage, model decay) và safety incident (LLM mishandling, fairness violation, emergency mishap). Đi kèm [PRIVACY_INCIDENT.md](PRIVACY_INCIDENT.md) (existing) và [RED_TEAM_PLAYBOOK.md](RED_TEAM_PLAYBOOK.md).

## 1. Triết lý

### 1.1 Blameless

Khi incident xảy ra, **không tìm người để đổ lỗi** — tìm system gap để cải thiện.

Lý do: blame culture → người che giấu lỗi → lỗi tích lũy → catastrophic failure. Blameless culture → người báo cáo nhanh → fix sớm → resilient system.

### 1.2 5 Whys, không 5 Whos

Khi root cause analysis, hỏi "Why" 5 lần (technical/process/organizational), không "Who" — không cần biết người gây.

### 1.3 Just culture

Phân biệt:
- **Human error**: console, retrain (no punishment)
- **At-risk behavior**: coach, change incentive (no punishment)
- **Reckless behavior**: punishment OK (e.g., bypass security knowingly)

Đa số incident là human error hoặc at-risk — không punish.

### 1.4 Learning over judgment

Postmortem mục tiêu là learning. Không phải compliance theatre.

## 2. Incident classification

### 2.1 Severity

| Severity | Definition | Response time |
|---|---|---|
| **P0 (Critical)** | User safety risk, data breach, full outage, emergency pipeline fail | Immediate, all-hands |
| **P1 (High)** | Major feature down, significant user impact, fairness violation, LLM mishandling | < 1 hour to acknowledge, <24h fix |
| **P2 (Medium)** | Minor feature degradation, model decay > threshold, audit log gap | < 4 hours, < 1 week fix |
| **P3 (Low)** | Cosmetic, edge case, doc inconsistency | Next sprint |

### 2.2 Category

- **Technical**: outage, bug, performance, integration failure
- **ML**: model decay, fairness violation, hallucination spike, classifier drift
- **Safety**: emergency mishandling, LLM safety bypass, prompt injection success
- **Privacy**: PII leak, consent violation, retention breach, audit log tampering
- **Process**: deployment mistake, communication failure, on-call miss

### 2.3 Existing incident handlers

| Type | Doc / handler |
|---|---|
| Privacy | [PRIVACY_INCIDENT.md](PRIVACY_INCIDENT.md) (existing) — 48h SLA per `PALP_PRIVACY.SLA_HOURS` |
| Mental health emergency | [EMERGENCY_RESPONSE_TRAINING.md](EMERGENCY_RESPONSE_TRAINING.md) |
| LLM security finding | [RED_TEAM_PLAYBOOK.md](RED_TEAM_PLAYBOOK.md) |
| Release rollback | [RELEASE_RUNBOOK.md](RELEASE_RUNBOOK.md) (existing) |
| ML model issue | This doc + [dkt-engine skill](../.ruler/skills/dkt-engine/SKILL.md) |

## 3. Incident response process

### 3.1 Detect

Sources:
- Monitoring alerts (Grafana + Prometheus)
- User reports (in-app, email)
- Lecturer dashboard alerts
- Red team findings
- Audit log anomalies
- Self-reported by team member

### 3.2 Acknowledge (within SLA)

On-call engineer acknowledges in incident channel (Slack/Teams). Status: "Acknowledged, investigating".

### 3.3 Triage

Assign severity. Form incident response team:
- **Incident Commander (IC)**: coordinates response, communicates
- **Tech Lead**: investigates technical root cause
- **Communicator**: updates stakeholders (lecturer, admin, users)
- (For P0): Add Privacy Officer, Legal, External Comms if needed

### 3.4 Mitigate

Goal: stop bleeding ASAP. Don't worry about root cause yet.

Examples:
- Outage → rollback to last good deploy
- LLM hallucination spike → disable feature, fallback rule-based
- Fairness violation → halt affected model, fallback v1
- Privacy leak → revoke access, isolate

### 3.5 Communicate

Stakeholder communication template:

```
[INCIDENT P{X}] {Brief title}

Status: Investigating / Mitigated / Resolved
Started: {timestamp}
Affected: {users / features}
Workaround: {if any}
ETA: {best guess}
Updates: every {N} min in {channel}
```

For P0 affecting users: in-app banner, email to affected users.

### 3.6 Resolve

Fix verified, monitor for recurrence. Status: "Resolved".

### 3.7 Postmortem

Within 5 business days for P0/P1, 10 days for P2.

## 4. Blameless postmortem template

```markdown
# Postmortem: {Incident title}

## Metadata

- **Date**: YYYY-MM-DD
- **Severity**: P0 / P1 / P2 / P3
- **Category**: technical / ml / safety / privacy / process
- **Duration**: HH:MM (acknowledged → resolved)
- **Affected users**: ~N students / lecturers
- **Affected features**: list
- **IC**: {name}

## Summary

[2-3 sentence executive summary. What happened, what was the impact.]

## Timeline

(All times in Asia/Ho_Chi_Minh)

| Time | Event |
|---|---|
| HH:MM | First signal (alert / report) |
| HH:MM | Acknowledged by on-call |
| HH:MM | IC assigned, triage started |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Resolved, monitoring |
| HH:MM | All clear |

## Root cause

[Technical explanation. NO names. Use 5 Whys.]

Why 1: [proximate cause]
Why 2: [why proximate cause happened]
Why 3: [why that condition existed]
Why 4: [system gap that allowed]
Why 5: [organizational/cultural root]

## What went well

- [List 3-5 things that helped]
- (Examples: alert fired correctly, rollback was fast, runbook accurate)

## What went poorly

- [List 3-5 things that didn't help]
- (Examples: alert was noisy, runbook was outdated, communication was unclear)

## Where we got lucky

- [List things that could have been worse]
- (Examples: it was night so few users affected, easy rollback by chance)

## Action items

| AI | Owner | ETA | Severity |
|---|---|---|---|
| {action 1} | @person | YYYY-MM-DD | high |
| {action 2} | @person | YYYY-MM-DD | medium |
| ... | | | |

(Action items must be: specific, owned, dated, prioritized.)

## Lessons learned

[Free-form reflection. Cultural / process / technical lessons. Share with team.]

## Sharing

- [ ] Shared in #engineering channel
- [ ] Shared in monthly all-hands review
- [ ] Updated relevant runbook/playbook
- [ ] Added test/monitoring to prevent recurrence
- [ ] (For P0/P1) Shared with leadership
```

## 5. Postmortem meeting

For P0/P1, hold meeting within 1 week of resolution.

### 5.1 Attendees

- Incident response team
- Affected feature owners
- Skip-level manager (observer, not driver)
- Anyone who wants to learn

### 5.2 Agenda (60 min)

| Time | Topic |
|---|---|
| 5 min | Context — what happened (summary) |
| 15 min | Walkthrough timeline |
| 10 min | Root cause analysis (5 whys) |
| 15 min | What went well/poorly/lucky |
| 15 min | Action items — prioritize, assign, ETA |

### 5.3 Ground rules

- Past tense, no "you should have"
- Hypothetical reframing: "in the moment, the natural thing to do was X" not "you did X wrong"
- Curiosity, not judgment
- IC facilitates, encourages contribution from quiet members

### 5.4 Output

- Postmortem doc finalized + shared
- Action items in tracker
- Updated runbook (if applicable)
- Lessons summarized for monthly review

## 6. Action item follow-through

Action items often die. Prevent:

- Owner explicit + ETA realistic
- Track in same project tracker as features (not separate)
- Weekly check-in on overdue
- Quarterly review: % action items completed within ETA (target ≥ 80%)
- Re-postmortem if same incident repeats (signal action items insufficient)

## 7. Responsible Disclosure Policy

### 7.1 Scope

Vulnerabilities in PALP affecting:
- Security (auth, RBAC, injection)
- Privacy (PII leak, consent bypass)
- LLM safety (jailbreak, prompt injection in production)
- Fairness (discriminatory output reproducible)

### 7.2 Reporting channel

Email: `security@palp.{institution_domain}` (institution must set up)

PGP key published at `/security.txt`:

```
Contact: mailto:security@palp.example.edu
Encryption: https://palp.example.edu/pgp-key.txt
Acknowledgments: https://palp.example.edu/security/hall-of-fame
Policy: https://palp.example.edu/security/policy
Hiring: https://palp.example.edu/jobs
```

### 7.3 Reporter expectations

Asked of reporter:
- Detailed reproduction steps
- Severity assessment (your view)
- 90-day disclosure timeline (industry standard)
- No exploit beyond proof-of-concept
- No data exfiltration beyond minimum to demonstrate

In return:
- Acknowledge within 5 business days
- Investigate within 30 days
- Fix within 90 days (severity-dependent)
- Credit (if desired) in hall of fame
- Bug bounty (if applicable, post-GA v3.0)

### 7.4 Bug bounty (post-GA v3.0)

Plan:
- Platform: HackerOne or Bugcrowd
- Scope: production PALP instance only
- Out of scope: physical, social engineering, DoS, automated scanning
- Rewards: $100-$5000 based on severity (institution budget dependent)
- Initial private invitation, expand to public after stabilizing

## 8. External comms during incident

### 8.1 Affected users

For P0/P1 affecting students:
- In-app banner at top of every page
- Email if account-affecting
- Status page link

Template:

```
"Chúng tôi đang điều tra một vấn đề ảnh hưởng [feature]. 
Đội ngũ đang xử lý. Cập nhật tiếp theo trong {N} phút.
Status: {URL}"
```

For privacy incident affecting PII:
- Personal email (not in-app banner)
- Detail what data, what risk, what we're doing
- Within legal SLA (NĐ 13/2023: notify in 72h for material incidents)

### 8.2 Lecturer/admin

Direct notification if their class affected. Short briefing.

### 8.3 Public

Status page (if multiple institutions). Twitter/X if major outage. Press release for catastrophic incidents.

**Don't:**
- Speculate cause before known
- Promise things you can't deliver
- Hide impact (even if embarrassing)

## 9. Incident metrics

Track quarterly:

| Metric | Target |
|---|---|
| MTTR P0 | < 4 hours |
| MTTR P1 | < 24 hours |
| Postmortem completion within SLA | 100% |
| Action items completed within ETA | ≥ 80% |
| Recurring incident rate | < 5% (same root cause within 6 months) |
| External vulnerability reports response time | < 5 business days |

## 10. Cultural reinforcement

### 10.1 Quarterly review

In monthly all-hands:
- Highlight 1 well-handled incident (positive reinforcement)
- Share 1 systemic lesson learned
- Update on action items

### 10.2 Onboarding

New hire reads:
- This doc
- Sample postmortem (sanitized)
- Existing runbooks
- Shadows on-call rotation

### 10.3 Anti-pattern alarms

Watch for:
- Same incident repeating → action items insufficient
- Postmortem skipped → process gap
- Blame language in retro → culture coaching needed
- Heroics rewarded > prevention → rebalance

## 11. Skills + related docs

- [PRIVACY_INCIDENT.md](PRIVACY_INCIDENT.md) — privacy-specific incident workflow (existing)
- [EMERGENCY_RESPONSE_TRAINING.md](EMERGENCY_RESPONSE_TRAINING.md) — mental health crisis response
- [RED_TEAM_PLAYBOOK.md](RED_TEAM_PLAYBOOK.md) — proactive vulnerability finding
- [incident-response skill](../.ruler/skills/incident-response/SKILL.md) — operational checklist
- [pr-review skill](../.ruler/skills/pr-review/SKILL.md) — prevention via review

## 12. Living document

Update khi:
- New incident category (e.g., adversarial student attack on peer system)
- Process gap revealed by recurring incident
- Industry best practice update (e.g., new SRE book published)
