---
name: peer-engine
description: Anti-herd peer engine — cohort clustering, reciprocal teaching matching, herd cluster detection with fairness audit, frontier mode default. Use when modifying backend/peer/.
---

# Peer Engine — Anti-Herd Workflow

## When to use

- Editing `backend/peer/` (models, services, tasks, views)
- Tuning `PALP_PEER` settings (HERD_EPS, BUDDY_REMATCH_DAYS, BENCHMARK_DEFAULT)
- Adding new peer feature (e.g., study group recommendation)
- Reviewing PR touching peer matching algorithm
- Investigating "đè bẹp" complaint từ student survey

## Hard invariants

1. **Default frontier-mode** for all new students. Opt-in benchmark only after 4 weeks.
2. **Cohort minimum 10 members** — if smaller, merge or suppress.
3. **Same-ability cohort comparison only** — k-means on entry assessment, no cross-cohort benchmark.
4. **Reciprocal matching, not 1-chiều** — A teaches B, B teaches A. Both directions required.
5. **Fairness audit MANDATORY** for all clustering output (PeerCohort, HerdCluster) — fail-build if concentration > 70%.
6. **No leaderboards, no rank, no points** — per [MOTIVATION_DESIGN.md](../../../docs/MOTIVATION_DESIGN.md).
7. **Consent gated**: `peer_comparison` for benchmarks, `peer_teaching` for sessions.
8. **Herd intervention** by lecturer only, not auto-action — system flags, human decides.

## App structure (review before editing)

```
backend/peer/
├── models.py
│   ├── PeerCohort
│   ├── ReciprocalPeerMatch
│   ├── TeachingSession
│   ├── HerdCluster
│   └── PeerConsent
├── services/
│   ├── benchmark.py
│   ├── reciprocal_matcher.py
│   ├── cluster_detector.py
│   └── frontier.py
├── tasks.py
├── views.py
├── permissions.py
└── tests/
```

## Workflow when modifying

### 1. Cohort building

```python
# backend/peer/services/cohort_builder.py
def build_cohorts(student_class):
    """Cluster students by entry assessment ability.
    
    Grounded in: Marsh 1987 Big Fish Little Pond — comparison should be within
    same-ability groups to avoid demoralization.
    """
    students = student_class.members.all()
    if len(students) < 10:
        # Single cohort, no clustering
        cohort = PeerCohort.objects.create(student_class=student_class, ability_band_label="all")
        cohort.members.set(students)
        return [cohort]
    
    vectors = [build_assessment_vector(s) for s in students]
    n_clusters = max(2, len(students) // 25)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(vectors)
    
    cohorts = []
    for label in set(labels):
        members = [students[i] for i, l in enumerate(labels) if l == label]
        if len(members) < 10:
            # Merge with nearest cohort, don't create
            continue
        cohort = PeerCohort.objects.create(
            student_class=student_class,
            ability_band_label=f"band_{label}",
            members_count=len(members),
        )
        cohort.members.set(members)
        cohorts.append(cohort)
    
    # MANDATORY: fairness audit on cohort assignment
    for cohort in cohorts:
        audit_result = audit_clustering(
            cluster_members=cohort.members.all(),
            total_class=students,
            check_attributes=["gender", "economic_band", "region"],
        )
        if not audit_result["passed"]:
            logger.warning("Cohort fairness audit failed", extra={"cohort_id": cohort.id})
            # Document but don't auto-rebalance — escalate to lecturer
    
    return cohorts
```

Run weekly via Celery `weekly_recompute_cohorts`.

### 2. Reciprocal matching

```python
# backend/peer/services/reciprocal_matcher.py
def find_reciprocal_match(student, cohort):
    """Match A(strong X, weak Y) with B(weak X, strong Y).
    
    Grounded in:
    - Topping 2005 peer tutoring meta-analysis
    - Fiorella & Mayer 2013 protégé effect
    - Vygotsky 1978 ZPD
    """
    a_vec = get_mastery_vector(student)
    candidates = []
    
    for b in cohort.members.exclude(id=student.id):
        if not has_consent(b, "peer_teaching"):
            continue
        
        b_vec = get_mastery_vector(b)
        
        a_strong_b_weak = find_strong_weak_pairs(a_vec, b_vec, threshold=0.3)
        b_strong_a_weak = find_strong_weak_pairs(b_vec, a_vec, threshold=0.3)
        
        if a_strong_b_weak and b_strong_a_weak:
            score = compatibility_score(a_strong_b_weak, b_strong_a_weak)
            candidates.append((b, score, a_strong_b_weak[0], b_strong_a_weak[0]))
    
    candidates.sort(key=lambda x: -x[1])
    
    if not candidates:
        return None
    
    best_b, score, concept_a_to_b, concept_b_to_a = candidates[0]
    return ReciprocalPeerMatch.objects.create(
        student_a=student,
        student_b=best_b,
        concept_a_to_b=concept_a_to_b,
        concept_b_to_a=concept_b_to_a,
        compatibility_score=score,
    )
```

### 3. Herd cluster detection (with fairness audit)

```python
# backend/peer/services/cluster_detector.py
def detect_herd_clusters(student_class):
    students = student_class.members.all()
    vectors = [build_behavior_vector_14d(s) for s in students]
    
    db = DBSCAN(
        eps=settings.PALP_PEER["HERD_EPS"],
        min_samples=settings.PALP_PEER.get("HERD_MIN_SAMPLES", 3),
    )
    labels = db.fit_predict(vectors)
    
    clusters = []
    for label in set(labels):
        if label == -1:
            continue  # noise
        members = [students[i] for i, l in enumerate(labels) if l == label]
        mean_risk = mean([compute_risk_score(m).composite for m in members])
        
        if mean_risk > 70 and len(members) >= 3:
            cluster = HerdCluster.objects.create(
                student_class=student_class,
                detected_at=timezone.now(),
                severity="high",
                mean_risk_score=mean_risk,
            )
            cluster.members.set(members)
            
            # MANDATORY: fairness audit
            audit_result = audit_clustering(
                cluster_members=members,
                total_class=students,
                check_attributes=["gender", "economic_band", "region"],
            )
            cluster.fairness_audit_result = audit_result
            
            if not audit_result["passed"]:
                cluster.flagged_for_review = True
                # DON'T suggest action — lecturer reviews first
            
            cluster.save()
            clusters.append(cluster)
    
    return clusters
```

### 4. Frontier mode (default for new students)

```python
# backend/peer/services/frontier.py
def get_frontier_data(student):
    """Return Bạn-vs-Bạn-tuần-trước data, no peer comparison."""
    history = MasteryState.objects.filter(student=student).order_by("-last_updated")
    
    return {
        "current_mastery_avg": compute_avg_mastery(history[:1]),  # this week
        "prior_mastery_avg": compute_avg_mastery(history.filter(last_updated__lt=4_weeks_ago)),
        "delta": current - prior,
        "concepts_progressed": list_progressed_concepts(student, days=28),
    }
```

## Adding new peer feature

1. Discuss in design review (UX + ethics)
2. Check [MOTIVATION_DESIGN.md](../../../docs/MOTIVATION_DESIGN.md) — does it violate SDT? Does it gamify?
3. Define consent type if new (e.g., `study_group_matching`) — update [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md)
4. Implement service + view + permission gate
5. Default off (opt-in)
6. Fairness audit any clustering/matching output
7. Causal A/B before broad rollout (per [causal-experiment skill](../causal-experiment/SKILL.md))
8. Update [PEER_ENGINE_DESIGN.md](../../../docs/PEER_ENGINE_DESIGN.md) — add section
9. Test matrix: opt-in/out, RBAC, fairness, edge cases

## Common pitfalls

- **Forgetting fairness audit**: clustering can encode bias unintentionally
- **Using benchmark as default**: per literature this discourages 70% of students
- **1-chiều buddy matching**: less effective than reciprocal (Topping 2005)
- **Cross-cohort comparison**: violates same-ability principle
- **Auto-action on herd cluster**: should be lecturer-decided, not auto-intervention
- **Hardcoded threshold**: use settings (HERD_EPS, BUDDY_THRESHOLD)
- **Skipping consent gate**: ingest endpoint accepts events from non-consenting users
- **Showing rank**: forbidden per anti-gamification rule

## Test matrix

For every endpoint:
- Owner can access (with consent)
- Other student cannot access
- Consent required (403 without)
- Fairness audit on output passes

For every cluster/match service:
- Cohort < 10 members handled (no display)
- Empty result handled
- Edge case: only 1 student in class
- Fairness audit invocation
- Idempotency (same input → same output, deterministic random seed)

## Related

- [PEER_ENGINE_DESIGN.md](../../../docs/PEER_ENGINE_DESIGN.md) — full design
- [MOTIVATION_DESIGN.md](../../../docs/MOTIVATION_DESIGN.md) — SDT, anti-gamification
- [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) sections 3.5, 3.6 — peer consent
- [LEARNING_SCIENCE_FOUNDATIONS.md](../../../docs/LEARNING_SCIENCE_FOUNDATIONS.md) sections 2.5, 2.8
- [fairness-audit skill](../fairness-audit/SKILL.md)
- [causal-experiment skill](../causal-experiment/SKILL.md)
