# Peer Engine Design — Anti-Herd + Reciprocal Teaching + Fairness

> Tài liệu thiết kế cho `backend/peer/` (Phase 3). Giải quyết "bị nhóm kéo xuống" qua 4 cơ chế bổ trợ + fairness audit bắt buộc. Đọc kèm [LEARNING_SCIENCE_FOUNDATIONS.md](LEARNING_SCIENCE_FOUNDATIONS.md) section 2.5 và 2.8.

## 1. Vấn đề cần giải quyết

Sinh viên trong môi trường mass-class có 2 hiệu ứng tiêu cực:

1. **Đồng hoá nhóm yếu (herd effect)** — khi học chung với nhóm có hành vi học tệ (skip class, give up, low engagement), sinh viên bị "kéo xuống" theo hành vi xã hội. Evidence: Christakis & Fowler 2007 "The Spread of Obesity in a Large Social Network" (cùng cơ chế social contagion áp dụng cho học tập).

2. **Tự ti từ peer comparison ngược** — khi so sánh với peer mạnh hơn rõ rệt, sv yếu hơn càng demoralize. Evidence: Marsh 1987 "Big Fish Little Pond Effect" — sv khá trong lớp giỏi tự đánh giá thấp hơn sv khá trong lớp trung bình.

PALP cần **chặn cả 2** mà vẫn dùng được giá trị positive của peer learning.

## 2. Triết lý thiết kế

### 2.1 4 nguyên tắc

1. **Default frontier (vs past-self)** — sinh viên mới mặc định không thấy peer compare. Đây là default vì 70% sv (theo lit review) sẽ bị tổn thương bởi early peer exposure.
2. **Cohort cùng năng lực ban đầu** — khi opt-in peer feature, chỉ so với cohort có cùng entry assessment band (k-means cluster). Tránh "Big Fish Little Pond" effect.
3. **Reciprocal > 1-chiều** — peer interaction là teaching nhau (mạnh-yếu chéo), không phải competition. Evidence: protégé effect (Fiorella & Mayer 2013).
4. **Fairness audit bắt buộc** — mọi clustering output qua P0 fairness module, fail nếu demographic concentration > 70%.

### 2.2 4 cơ chế

| Cơ chế | Vai trò | Default | Consent |
|---|---|---|---|
| **Personal Frontier** | So với past-self only | ON | (none — không cần) |
| **Peer Benchmark** | Percentile ẩn danh trong cohort | OFF | `peer_comparison` |
| **Reciprocal Teaching** | Match mạnh-yếu chéo, turn-based | OFF | `peer_teaching` |
| **Herd Cluster Detection** | Lecturer-side intervention | (system) | (lecturer-only) |

## 3. App architecture

```
backend/peer/
├── models.py
│   ├── PeerCohort           # cluster theo năng lực ban đầu, weekly re-cluster
│   ├── ReciprocalPeerMatch  # match mạnh-yếu chéo
│   ├── TeachingSession      # turn-based session
│   ├── HerdCluster          # negative behavior cluster
│   └── PeerConsent          # opt-in per feature
├── services/
│   ├── benchmark.py         # percentile ẩn danh cohort cùng năng lực
│   ├── reciprocal_matcher.py  # match A(mạnh X yếu Y) ↔ B(yếu X mạnh Y)
│   ├── cluster_detector.py    # DBSCAN herd detection
│   └── frontier.py            # personal-frontier mode
├── tasks.py                 # weekly_recompute_cohorts, daily_detect_herds
├── views.py                 # /api/peer/benchmark/, /api/peer/buddy/, /api/peer/frontier/, /api/peer/teaching-session/
├── permissions.py           # IsStudent + PeerConsent gates
├── urls.py
└── tests/
```

## 4. Cơ chế chi tiết

### 4.1 PeerCohort — clustering năng lực ban đầu

**Algorithm.** K-means trên entry assessment scores per concept (vector dim = số concept core).

```python
# backend/peer/services/cohort_builder.py
def build_cohorts(student_class) -> list[PeerCohort]:
    """Cluster students by entry assessment scores into ability cohorts.
    
    Grounded in: Marsh 1987 Big Fish Little Pond Effect — comparison should
    happen within similar-ability groups to avoid demoralization.
    """
    students = student_class.members.all()
    vectors = [build_assessment_vector(s) for s in students]
    n_clusters = max(2, len(students) // 25)  # ~25 students per cohort
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(vectors)
    
    cohorts = []
    for label in set(labels):
        members = [students[i] for i, l in enumerate(labels) if l == label]
        cohort = PeerCohort.objects.create(
            student_class=student_class,
            ability_band_label=f"band_{label}",
            members_count=len(members),
        )
        cohort.members.set(members)
        cohorts.append(cohort)
    
    return cohorts
```

**Re-cluster cadence.** Weekly (Sunday 03:00 ICT). Sv chuyển cohort nếu mastery thay đổi đáng kể.

**Cohort minimum size.** 10 — nếu < 10, gộp với cohort gần nhất. Lý do: privacy (cell suppression).

### 4.2 Personal Frontier mode (default)

UI hiển thị "Bạn vs bạn-tuần-trước" thay vì "Bạn vs peer".

```typescript
// frontend/src/app/(student)/peer/page.tsx
function FrontierChart({ history }: Props) {
  return (
    <Chart>
      <Line dataKey="mastery_self_now" label="Hiện tại" />
      <Line dataKey="mastery_self_4_weeks_ago" label="4 tuần trước" />
      <Annotation>Tăng X% so với chính bạn 4 tuần trước</Annotation>
    </Chart>
  );
}
```

Sau 4 tuần on-board, prompt opt-in benchmark mode (không auto-switch).

### 4.3 Peer Benchmark — ẩn danh + có ý đồ

```python
# backend/peer/services/benchmark.py
def compute_benchmark(student) -> dict:
    """Anonymous percentile within same-ability cohort.
    
    Returns relative position only, no names/ranks.
    """
    cohort = student.peer_cohort
    if cohort.members_count < 10:
        return {"available": False, "reason": "cohort_too_small"}
    
    own_score = compute_composite_mastery(student)
    cohort_scores = [compute_composite_mastery(m) for m in cohort.members.all()]
    percentile = stats.percentileofscore(cohort_scores, own_score)
    
    return {
        "available": True,
        "cohort_size": cohort.members_count,
        "percentile_band": _to_band(percentile),  # e.g., "top 30%", not "rank 7"
        "interpretation_safe": _safe_copy(percentile),
    }

def _to_band(percentile: float) -> str:
    """Convert raw percentile to safer band display."""
    if percentile >= 75:
        return "top_25_pct"  # Display: "Trong nhóm cao của cohort"
    elif percentile >= 50:
        return "above_median"
    elif percentile >= 25:
        return "below_median"
    else:
        return "bottom_25_pct"  # Display: "Đang trong giai đoạn xây nền — coach gợi ý..."
```

**Anti-tự-ti rule.** Khi percentile < 25%, UI không hiển thị "bạn dưới 75%" — thay bằng:

> "Bạn đang trong giai đoạn xây nền tảng. Trong cohort cùng xuất phát điểm, có 6 bạn từng ở vị trí của bạn 4 tuần trước, hiện đã thông thạo concept X. Có muốn xem cách họ học không?"

### 4.4 Reciprocal Peer Teaching

#### Matching algorithm

```python
# backend/peer/services/reciprocal_matcher.py
def find_reciprocal_match(student, cohort) -> Optional[ReciprocalPeerMatch]:
    """Find student B such that A is strong where B is weak, and vice versa.
    
    Grounded in: 
    - Topping 2005 peer tutoring meta-analysis
    - Fiorella & Mayer 2013 protégé effect
    - Vygotsky 1978 ZPD (B must be in A's ZPD for A's strong concepts)
    """
    a_concept_vec = get_mastery_vector(student)  # [(concept_id, mastery)]
    
    candidates = []
    for b in cohort.members.exclude(id=student.id):
        b_concept_vec = get_mastery_vector(b)
        
        # Find concept pairs where A>>B and B>>A
        a_strong_b_weak = find_strong_weak_pairs(a_concept_vec, b_concept_vec, threshold=0.3)
        b_strong_a_weak = find_strong_weak_pairs(b_concept_vec, a_concept_vec, threshold=0.3)
        
        if a_strong_b_weak and b_strong_a_weak:
            score = compatibility_score(a_strong_b_weak, b_strong_a_weak)
            candidates.append((b, score, a_strong_b_weak[0], b_strong_a_weak[0]))
    
    # Sort by compatibility
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

#### TeachingSession — turn-based

```python
# backend/peer/models.py
class TeachingSession(models.Model):
    match = models.ForeignKey(ReciprocalPeerMatch, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Round(models.TextChoices):
        A_TEACHES_X = "a_teaches_x", "A dạy X cho B"
        B_TEACHES_Y = "b_teaches_y", "B dạy Y cho A"
        FREE_DISCUSSION = "free_discussion", "Thảo luận tự do"
    
    current_round = models.CharField(choices=Round.choices, max_length=20)
    a_rating_by_b = models.IntegerField(null=True)  # B rates A's teaching
    b_rating_by_a = models.IntegerField(null=True)  # A rates B's teaching
    a_mastery_delta_after = models.FloatField(null=True)
    b_mastery_delta_after = models.FloatField(null=True)
```

#### Session structure

| Round | Duration | Activity |
|---|---|---|
| 1. Brief | 5 min | UI introduce match: "Bạn sẽ dạy concept X cho bạn B; B sẽ dạy Y cho bạn" |
| 2. A teaches X | 15 min | Chat + whiteboard. A explains concept X to B |
| 3. B asks | 5 min | B confirms understanding, asks clarification |
| 4. B teaches Y | 15 min | Switch role — B explains Y to A |
| 5. A asks | 5 min | A confirms, asks clarification |
| 6. Mutual rating | 3 min | Both rate teaching quality 1-5 |
| 7. Optional follow-up task | 10 min | Each does a quick task on the concept they were taught |

Total: ~60 min. Async optional (sv schedule together).

#### Frontend

[`frontend/src/app/(student)/peer/teaching-session/[id]/page.tsx`](../frontend/src/app/(student)/peer/teaching-session/page.tsx) — chat + whiteboard component (use existing `frontend/src/components/whiteboard/` if exists, else integrate Excalidraw).

### 4.5 Herd Cluster Detection — anti-herd

#### DBSCAN trên behavior vector

```python
# backend/peer/services/cluster_detector.py
def detect_herd_clusters(student_class) -> list[HerdCluster]:
    """Detect clusters of students with negative behavior patterns.
    
    Uses DBSCAN on 14-day behavior vectors. Clusters with high mean risk
    score and size >= 3 are flagged as herd clusters needing intervention.
    """
    students = student_class.members.all()
    vectors = []
    for s in students:
        vec = (
            avg_focus_minutes_14d(s),
            missed_milestones_14d(s),
            give_up_count_14d(s),
            dismissed_nudges_14d(s),
            weekly_login_days_14d(s),
        )
        vectors.append(vec)
    
    eps = settings.PALP_PEER["HERD_EPS"]
    min_samples = settings.PALP_PEER.get("HERD_MIN_SAMPLES", 3)
    
    db = DBSCAN(eps=eps, min_samples=min_samples)
    labels = db.fit_predict(vectors)
    
    clusters = []
    for label in set(labels):
        if label == -1:  # noise points, ignore
            continue
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
            audit_result = fairness.audit_clustering(
                cluster_members=members,
                total_class=students,
                check_attributes=["gender", "economic_band", "region"],
            )
            cluster.fairness_audit_result = audit_result
            cluster.save()
            
            if not audit_result["passed"]:
                # Cluster has demographic bias > 70% — alert + don't suggest action yet
                cluster.flagged_for_review = True
                cluster.save()
                logger.warning("HerdCluster fairness audit failed", extra={
                    "cluster_id": cluster.id,
                    "audit": audit_result,
                })
            
            clusters.append(cluster)
    
    return clusters
```

#### Lecturer view

[`frontend/src/app/(lecturer)/herd-clusters/page.tsx`](../frontend/src/app/(lecturer)/herd-clusters/page.tsx):

- List clusters sorted by severity
- Each cluster: members (with PII access per RBAC), mean risk, behavior pattern summary
- Suggested intervention: "Tách-cohort" (re-assign reciprocal matches), 1-on-1 outreach, group counseling
- **Warning banner** nếu fairness audit failed: "Cluster này có concentration cao về [demographic]. Hãy review trước khi can thiệp để tránh bias."

#### Anti-herd intervention strategies

1. **Tách-cohort recovery**: re-match members vào reciprocal pairs với students positive (ngoài cluster)
2. **Group session với counselor**: lecturer hoặc counselor host meeting với cluster members
3. **Coach proactive nudge**: per-member coach trigger "Coach thấy bạn và 1 số bạn đang gặp khó khăn cùng. Có muốn coach giúp riêng không?"
4. **Curriculum review**: nếu cluster cùng struggle 1 concept → curriculum optimization (P6F Instructor Co-pilot)

## 5. Fairness audit integration

### 5.1 Per-clustering audit

`backend/fairness/audit_clustering.py` (P0):

```python
def audit_clustering(cluster_members, total_class, check_attributes):
    """Check if cluster has disproportionate demographic concentration.
    
    Returns {passed: bool, ratios: dict, ...}
    """
    results = {"passed": True, "ratios": {}, "violations": []}
    total_size = len(total_class)
    cluster_size = len(cluster_members)
    
    for attr in check_attributes:
        for value in get_attribute_values(total_class, attr):
            class_ratio = count_attr_value(total_class, attr, value) / total_size
            cluster_ratio = count_attr_value(cluster_members, attr, value) / cluster_size
            
            results["ratios"][f"{attr}={value}"] = {
                "class": class_ratio,
                "cluster": cluster_ratio,
                "concentration_ratio": cluster_ratio / max(class_ratio, 0.01),
            }
            
            # Fail if cluster concentration > 70% AND class baseline < 50%
            if cluster_ratio > 0.7 and class_ratio < 0.5:
                results["passed"] = False
                results["violations"].append({
                    "attr": attr,
                    "value": value,
                    "cluster_ratio": cluster_ratio,
                    "class_ratio": class_ratio,
                })
    
    return results
```

### 5.2 CI gate

[`scripts/fairness_release_check.py`](../scripts/fairness_release_check.py) chạy trên historical clustering data trước mỗi release. Fail-build nếu cluster có demographic concentration > 0.7 AND `disparate_impact_ratio < 0.8`.

## 6. Privacy & consent flow

### 6.1 Default state cho new student

```python
# backend/peer/services/onboarding.py
def initialize_peer_settings(student):
    PeerConsent.objects.create(
        student=student,
        peer_comparison=False,  # opt-in sau 4 tuần
        peer_teaching=False,    # opt-in anytime nhưng không auto
        frontier_mode=True,     # default ON
        cohort_assignment=None, # delayed 4 tuần
    )
```

### 6.2 Opt-in prompt sau 4 tuần

`backend/peer/tasks.py`:

```python
@shared_task
def prompt_peer_optin_after_4_weeks():
    """Weekly task: find students who reached 4-week mark and have not been prompted."""
    candidates = User.objects.filter(
        date_joined__lte=timezone.now() - timedelta(days=28),
        peerconsent__prompt_shown_at__isnull=True,
        peerconsent__peer_comparison=False,
    )
    for student in candidates:
        # Create CoachTrigger for next coach interaction to surface prompt
        CoachTrigger.objects.create(
            student=student,
            trigger_type="peer_optin_prompt",
            payload={"current_phase": "4_week_milestone"},
        )
        student.peerconsent.prompt_shown_at = timezone.now()
        student.peerconsent.save()
```

### 6.3 Revocation

User can toggle in [`/preferences/peer/`](../frontend/src/app/preferences/peer/page.tsx) any time. On revoke:
- `peer_comparison` off → benchmark UI hidden, history cleared from cache
- `peer_teaching` off → existing matches archived, no new matches; sv can still complete current session
- `frontier_mode` luôn available không cần consent

## 7. Metrics & gates

### 7.1 P3 Gate criteria

| Metric | Target | Source |
|---|---|---|
| Reciprocal teaching accept rate | ≥ 40% | `TeachingSession.created` / `match.opt_in_prompt_sent` |
| Average teaching session rating | ≥ 3.5/5 | `TeachingSession.a_rating_by_b` + `b_rating_by_a` |
| Mastery delta post-session | positive (mean) | `TeachingSession.a_mastery_delta_after` + `b_mastery_delta_after` |
| Herd cluster detection precision | ≥ 70% | Lecturer review feedback "valid concern" |
| Fairness clustering pass rate | 100% | All clusters pass `audit_clustering` |
| Peer benchmark complaint rate | < 5% | Survey "Did peer comparison feel discouraging?" |

### 7.2 Long-term metrics (P3 + P5 ongoing)

- Cohort mobility (sv chuyển cohort up over time): healthy = 20-40% per quarter
- Buddy match retention (continue sau session 1): ≥ 60%
- Herd cluster intervention impact: 30 days post-intervention, mean risk reduces ≥ 15%

## 8. Edge cases

| Edge case | Handling |
|---|---|
| Cohort < 10 members | Merge với nearest cohort; suppress benchmark display |
| Sv không có entry assessment | Defer cohort assignment; show frontier-mode only |
| Reciprocal match không tìm được sau 7 ngày | Retry với loosened threshold; if still none, suggest mentor instead |
| Sv refuse all peer features | Respect — frontier-mode + private learning path |
| HerdCluster gồm sv của lecturer khác | Cross-class herd → admin notification, multi-lecturer coordination |
| Sv chuyển class giữa kỳ | Re-cluster + re-evaluate buddy match in new cohort |

## 9. Đọc tiếp

- [LEARNING_SCIENCE_FOUNDATIONS.md](LEARNING_SCIENCE_FOUNDATIONS.md) section 2.5 (peer tutoring) + 2.8 (ZPD)
- [MOTIVATION_DESIGN.md](MOTIVATION_DESIGN.md) section 5.2 (peer benchmark UX example)
- [PRIVACY_V2_DPIA.md](PRIVACY_V2_DPIA.md) sections 3.5, 3.6, 3.14
- [peer-engine skill](../.ruler/skills/peer-engine/SKILL.md)
- [fairness-audit skill](../.ruler/skills/fairness-audit/SKILL.md)
