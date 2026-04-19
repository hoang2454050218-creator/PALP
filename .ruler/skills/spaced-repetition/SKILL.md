---
name: spaced-repetition
description: FSRS scheduler + Cognitive Load tuning + ZPD scaffolding + Deliberate Practice. Long-term retention engineering. Use when modifying backend/spacedrep/ or designing review flows.
---

# Spaced Repetition — FSRS + CLT + ZPD + Deliberate Practice

## When to use

- Editing `backend/spacedrep/` (fsrs, scheduler, cognitive_load, zpd, deliberate_practice)
- Tuning FSRS parameters (default-stability, retention-target)
- Designing review queue UI
- Adjusting difficulty curve per learner
- Adding new scaffold type
- Reviewing PR touching review/practice flow

## Hard invariants

1. **FSRS algorithm v4/v5** — implement per [open-spaced-repetition spec](https://github.com/open-spaced-repetition/fsrs4anki). Don't roll own scheduler.
2. **Retention target ≥ 0.9** by default — `PALP_FSRS["RETENTION_TARGET"]`. Tunable per concept difficulty.
3. **Cognitive load tuning** — task difficulty within learner's CLT capacity (intrinsic + extraneous + germane budget).
4. **ZPD-aware scaffolding** — scaffold visible in Zone of Proximal Development, fade as mastery grows.
5. **Targeted weakness drilling** — Deliberate Practice (Ericsson) on KG root-cause weak prerequisites.
6. **No streak gamification** — display "X concepts due today" not "3-day streak!" per [MOTIVATION_DESIGN.md](../../../docs/MOTIVATION_DESIGN.md).
7. **Per-concept review tracking** — `SpacedReview` linked to concept, not just card.

## App structure

```
backend/spacedrep/
├── models.py              # SpacedReview, ReviewCard, ReviewLog
├── fsrs.py                # FSRS algorithm v4/v5
├── scheduler.py           # daily generate_review_queue
├── cognitive_load.py      # intrinsic/extraneous/germane budget
├── zpd.py                 # scaffolding dynamic
├── deliberate_practice.py # targeted weakness drilling
├── views.py               # /api/spacedrep/queue/, /review/
└── tests/
```

## Theory grounding

| Feature | Theory | Reference |
|---|---|---|
| FSRS scheduler | Spacing effect, free spaced repetition | Open Spaced Repetition project; Wozniak SuperMemo SM-2 → FSRS |
| Active retrieval over reread | Testing/retrieval effect | Karpicke & Roediger 2008 Science 319 |
| Interleaving | Distributed practice | Cepeda et al. 2006 Psychological Bulletin |
| Cognitive load tuning | Cognitive Load Theory | Sweller 1988, 2011 |
| Worked examples for novices | Worked example effect | Sweller & Cooper 1985 |
| Difficulty per learner | Element interactivity, expertise reversal | Kalyuga 2003 |
| Scaffolding fade | Sociocultural Theory, ZPD | Vygotsky 1978; Wood, Bruner & Ross 1976 |
| Targeted weakness | Deliberate Practice | Ericsson, Krampe & Tesch-Römer 1993 |

Cite in code per [LEARNING_SCIENCE_FOUNDATIONS.md](../../../docs/LEARNING_SCIENCE_FOUNDATIONS.md) section 3.

## FSRS implementation

```python
# backend/spacedrep/fsrs.py
from dataclasses import dataclass
from datetime import datetime, timedelta

# FSRS-4 default parameters (per open-spaced-repetition)
W_DEFAULT = (0.4, 0.6, 2.4, 5.8, 4.93, 0.94, 0.86, 0.01, 1.49, 0.14, 0.94, 2.18, 0.05, 0.34, 1.26, 0.29, 2.61)

@dataclass
class FSRSState:
    stability: float
    difficulty: float
    last_review: datetime
    reps: int
    lapses: int
    state: str  # 'new', 'learning', 'review', 'relearning'

class FSRSScheduler:
    """Free Spaced Repetition Scheduler.
    
    Grounded in: Wozniak SuperMemo evolution; open-spaced-repetition FSRS v4/v5.
    """
    def __init__(self, retention_target=0.9, w=W_DEFAULT):
        self.retention_target = retention_target
        self.w = w
    
    def initial_state(self, rating: int) -> FSRSState:
        """rating: 1=Again, 2=Hard, 3=Good, 4=Easy."""
        return FSRSState(
            stability=self._init_stability(rating),
            difficulty=self._init_difficulty(rating),
            last_review=datetime.now(),
            reps=1,
            lapses=0,
            state="learning",
        )
    
    def next_state(self, state: FSRSState, rating: int) -> tuple[FSRSState, timedelta]:
        """Compute next state + interval after a review."""
        elapsed_days = (datetime.now() - state.last_review).days
        retrievability = self._retrievability(state.stability, elapsed_days)
        
        if rating == 1:  # Again
            new_stability = self._stability_after_lapse(state, retrievability)
            new_difficulty = self._next_difficulty(state.difficulty, rating)
            new_state = FSRSState(
                stability=new_stability,
                difficulty=new_difficulty,
                last_review=datetime.now(),
                reps=state.reps + 1,
                lapses=state.lapses + 1,
                state="relearning",
            )
        else:  # Hard / Good / Easy
            new_stability = self._next_stability(state, rating, retrievability)
            new_difficulty = self._next_difficulty(state.difficulty, rating)
            new_state = FSRSState(
                stability=new_stability,
                difficulty=new_difficulty,
                last_review=datetime.now(),
                reps=state.reps + 1,
                lapses=state.lapses,
                state="review",
            )
        
        next_interval_days = self._next_interval(new_stability)
        return new_state, timedelta(days=next_interval_days)
    
    def _retrievability(self, stability, elapsed_days):
        return (1 + elapsed_days / (9 * stability)) ** -1
    
    def _next_interval(self, stability):
        """Interval to achieve retention_target."""
        return stability * (self.retention_target ** (1/-0.5) - 1) * 9
    
    # ... other helpers per FSRS spec
```

Use [`open-spaced-repetition/py-fsrs`](https://github.com/open-spaced-repetition/py-fsrs) as reference implementation.

## Daily review queue generation

```python
# backend/spacedrep/scheduler.py
@shared_task
def generate_review_queue_for_student(student_id):
    """Generate today's review queue for a student.
    
    Combines:
    - FSRS-due cards
    - Deliberate practice items (KG root-cause weak prereqs)
    - Cognitive load budget cap
    """
    student = User.objects.get(pk=student_id)
    
    # FSRS-due cards
    due_cards = SpacedReview.objects.filter(
        student=student,
        next_review_at__lte=timezone.now(),
    ).order_by("next_review_at")
    
    # Deliberate practice — KG root-cause
    weak_prereqs = diagnose_struggle(student, recent_struggle_concepts(student))
    practice_items = build_practice_items(weak_prereqs)
    
    # Cognitive load budget
    budget = compute_cognitive_budget(student)  # intrinsic + germane budget for today
    
    # Mix + cap
    queue = mix_and_cap(due_cards, practice_items, budget)
    
    ReviewQueue.objects.create(
        student=student,
        date=timezone.now().date(),
        items=queue,
    )
```

## Cognitive Load Theory tuning

```python
# backend/spacedrep/cognitive_load.py
def compute_cognitive_budget(student):
    """Estimate today's cognitive budget for student.
    
    Grounded in: Sweller 1988 CLT — intrinsic + extraneous + germane load.
    """
    # Recent fatigue (from signals)
    recent_focus_avg = avg_focus_score_last_7d(student)
    
    # Mastery level (expertise reversal — experts handle more)
    mastery_avg = avg_mastery(student)
    
    # Time of day (circadian — typically peak morning/early afternoon)
    hour = timezone.now().hour
    circadian_factor = 1.0 if 8 <= hour <= 14 else 0.7
    
    # Composite budget (in "task-equivalents")
    base_budget = 10
    return int(base_budget * recent_focus_avg * (0.5 + mastery_avg * 0.5) * circadian_factor)
```

## ZPD scaffolding

```python
# backend/spacedrep/zpd.py
def select_scaffold_level(student, concept):
    """Pick scaffold within learner's Zone of Proximal Development.
    
    Grounded in: Vygotsky 1978 ZPD; Wood, Bruner & Ross 1976 scaffolding.
    """
    mastery = get_mastery(student, concept).p_mastery
    
    if mastery < 0.3:
        return "worked_example"  # full guided
    elif mastery < 0.6:
        return "hint_chain"       # partial scaffold
    elif mastery < 0.85:
        return "self_explanation_prompt"  # minimal scaffold
    else:
        return "no_scaffold"      # independent
```

Fade automatic — as mastery grows, scaffold reduces.

## Deliberate Practice — targeted weakness

```python
# backend/spacedrep/deliberate_practice.py
def build_practice_items(weak_prereqs):
    """Build targeted practice items for weak prerequisite concepts.
    
    Grounded in: Ericsson et al. 1993 deliberate practice.
    """
    items = []
    for concept in weak_prereqs:
        # Generate 3-5 high-quality items focusing on that concept
        items.extend(
            MicroTask.objects.filter(
                concept=concept,
                difficulty=adjust_for_zpd(concept, current_mastery=...),
            )[:5]
        )
    return items
```

## Common pitfalls

- **Ignoring FSRS state for non-due card**: review without FSRS update → schedule degrades
- **Hardcoded retention target**: should be settings, configurable per concept
- **Streak/streak/streak**: violates anti-gamification rule
- **No cognitive budget cap**: overload → diminishing returns + frustration
- **Scaffold not fading**: leads to dependency, not independence
- **Practice items random**: should target KG weakness, not random
- **No A/B for FSRS impact**: validate retention uplift via [causal-experiment skill](../causal-experiment/SKILL.md) — target ≥20% long-term

## Test coverage

- FSRS algorithm: unit tests against [open-spaced-repetition reference](https://github.com/open-spaced-repetition/py-fsrs) test cases
- Scheduler: queue generation respects budget cap
- ZPD: scaffold level matches mastery band
- Deliberate practice: items match weak prereqs
- Long-term retention: causal A/B per [causal-experiment skill](../causal-experiment/SKILL.md)

## Related

- [LEARNING_SCIENCE_FOUNDATIONS.md](../../../docs/LEARNING_SCIENCE_FOUNDATIONS.md) sections 2.6, 2.7, 2.8, 2.9
- [MOTIVATION_DESIGN.md](../../../docs/MOTIVATION_DESIGN.md) — anti-gamification (no streak)
- [open-spaced-repetition](https://github.com/open-spaced-repetition) — FSRS reference
- [bkt-engine skill](../bkt-engine/SKILL.md) / [dkt-engine skill](../dkt-engine/SKILL.md) — mastery state input
- [causal-experiment skill](../causal-experiment/SKILL.md) — retention uplift validation
