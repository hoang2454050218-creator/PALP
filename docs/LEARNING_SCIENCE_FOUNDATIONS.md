# Learning Science Foundations — PALP

> Bộ tài liệu tham chiếu lý thuyết học tập làm cơ sở cho mọi feature trong roadmap v3. Mỗi feature trong code phải có comment citation tới theory tương ứng. Đây là khác biệt giữa "internal tool" và "evidence-based system".

## 1. Nguyên tắc

**Không thiết kế cảm tính.** Mỗi feature có behavior change phải:
1. Trace về 1 hoặc nhiều theory peer-reviewed
2. Citation chính xác (tác giả + năm + paper title)
3. Comment trong code: `# Grounded in: <citation>` ở function definition
4. Validate empirically qua causal A/B (xem [causal-experiment skill](../.ruler/skills/causal-experiment/SKILL.md))

## 2. Theory map

### 2.1 Knowledge Tracing — đo mastery

| Feature | Theory | Citations |
|---|---|---|
| BKT v1 (hiện tại) | Bayesian Knowledge Tracing | Corbett & Anderson 1995, "Knowledge tracing: Modeling the acquisition of procedural knowledge" |
| BKT v2 (P1) | BKT + response-time + hint penalty | Pardos & Heffernan 2011, "KT-IDEM: Introducing Item Difficulty to the Knowledge Tracing Model" |
| DKT/SAKT (P5) | Deep Knowledge Tracing với attention | Piech et al. 2015 "Deep Knowledge Tracing"; Pandey & Karypis 2019 "A Self-Attentive model for Knowledge Tracing" (SAKT); Choi et al. 2020 "Towards an Appropriate Query, Key, and Value Computation for Knowledge Tracing" (AKT) |
| Knowledge Graph + root-cause (P5) | Concept prerequisite graphs | Käser et al. 2017 "Dynamic Bayesian Networks for Student Modeling" |

### 2.2 Self-Regulated Learning — Direction Engine (P2)

| Feature | Theory | Citations |
|---|---|---|
| 3-phase Forethought/Performance/Reflection | Zimmerman SRL cycle | Zimmerman 2002 "Becoming a self-regulated learner: An overview" Theory Into Practice 41(2); Zimmerman & Schunk 2011 "Handbook of Self-Regulation of Learning and Performance" |
| Strategy planning | SRL strategy use | Pintrich 2004 "A Conceptual Framework for Assessing Motivation and Self-Regulated Learning in College Students" |
| Time estimation pre-task | Calibration of comprehension | Thiede et al. 2003 "Summarizing can improve metacomprehension accuracy" |
| Effort rating + strategy effectiveness post-task | Performance phase reflection | Zimmerman 2008 "Investigating Self-Regulation and Motivation: Historical Background, Methodological Developments, and Future Prospects" |

### 2.3 Self-Determination Theory — Motivation design (P2)

| Feature | Theory | Citations |
|---|---|---|
| Autonomy: choice in pathway, opt-out everything | SDT Autonomy need | Deci & Ryan 2000 "The 'What' and 'Why' of Goal Pursuits: Human Needs and the Self-Determination of Behavior"; Ryan & Deci 2017 "Self-Determination Theory: Basic Psychological Needs in Motivation, Development, and Wellness" |
| Competence: mastery framing, no points | SDT Competence need + intrinsic motivation | Deci 1971 "Effects of externally mediated rewards on intrinsic motivation" |
| Relatedness: optional peer connection | SDT Relatedness need | Baumeister & Leary 1995 "The need to belong" |
| **Anti-gamification (no points/badges/streak)** | Crowding-out of intrinsic motivation by extrinsic rewards | Deci, Koestner & Ryan 1999 meta-analysis "A meta-analytic review of experiments examining the effects of extrinsic rewards on intrinsic motivation" Psychological Bulletin 125(6) |

Xem [MOTIVATION_DESIGN.md](MOTIVATION_DESIGN.md) cho code review checklist.

### 2.4 Metacognition — Calibration (P1)

| Feature | Theory | Citations |
|---|---|---|
| Confidence Likert pre-submission | Judgment of Learning (JOL) | Dunlosky & Metcalfe 2009 "Metacognition" Sage Publications; Nelson & Narens 1990 "Metamemory: A theoretical framework and new findings" |
| Calibration error feedback | Calibration of comprehension | Maki 1998 "Test predictions over text material"; Hacker et al. 2008 "Test prediction and performance in a classroom context" |
| Over/under-confidence detection | Hard-easy effect | Lichtenstein, Fischhoff & Phillips 1982 "Calibration of probabilities" |

### 2.5 Peer Tutoring — Reciprocal Teaching (P3)

| Feature | Theory | Citations |
|---|---|---|
| Reciprocal teaching (turn-based) | Reciprocal Teaching method | Palincsar & Brown 1984 "Reciprocal teaching of comprehension-fostering and comprehension-monitoring activities" Cognition and Instruction 1(2) |
| A teaches X, B teaches Y matching | Peer tutoring effectiveness | Topping 2005 "Trends in peer learning" Educational Psychology 25(6) |
| Teaching = strongest learning effect | Protégé effect | Fiorella & Mayer 2013 "The relative benefits of learning by teaching and learning by preparing to teach" Contemporary Educational Psychology 38(4) |

### 2.6 Spaced Repetition + Retrieval — FSRS (P6B)

| Feature | Theory | Citations |
|---|---|---|
| FSRS scheduler | Spacing effect + free spaced repetition | Wozniak SuperMemo (SM-2 → FSRS); Open Spaced Repetition project (FSRS v4/v5) |
| Active retrieval > rereading | Testing/retrieval effect | Karpicke & Roediger 2008 "The critical importance of retrieval for learning" Science 319(5865); Roediger & Butler 2011 "The critical role of retrieval practice in long-term retention" |
| Interleaving practice | Distributed practice | Cepeda et al. 2006 "Distributed practice in verbal recall tasks: A review and quantitative synthesis" Psychological Bulletin 132(3) |

### 2.7 Cognitive Load Theory — UI/Task design (P6B)

| Feature | Theory | Citations |
|---|---|---|
| Intrinsic / extraneous / germane load tracking | Cognitive Load Theory | Sweller 1988 "Cognitive load during problem solving"; Sweller, Ayres & Kalyuga 2011 "Cognitive Load Theory" Springer |
| Difficulty tuning per learner | Element interactivity + expertise reversal | Kalyuga et al. 2003 "The expertise reversal effect" Educational Psychologist 38(1) |
| Worked examples for novices | Worked example effect | Sweller & Cooper 1985 "The use of worked examples as a substitute for problem solving in learning algebra" |

### 2.8 Zone of Proximal Development — Scaffolding (P6B)

| Feature | Theory | Citations |
|---|---|---|
| Buddy match +0.5σ → +1σ mastery | ZPD: nearest peer slightly ahead | Vygotsky 1978 "Mind in Society"; Wood, Bruner & Ross 1976 "The role of tutoring in problem solving" Journal of Child Psychology and Psychiatry 17(2) |
| Dynamic scaffolding fade | Fading scaffolds | Pea 2004 "The social and technological dimensions of scaffolding and related theoretical concepts for learning, education, and human activity" Journal of the Learning Sciences 13(3) |

### 2.9 Deliberate Practice — Targeted weakness (P6B)

| Feature | Theory | Citations |
|---|---|---|
| Targeted weakness drilling từ KG root-cause | Deliberate practice principles | Ericsson, Krampe & Tesch-Römer 1993 "The role of deliberate practice in the acquisition of expert performance" Psychological Review 100(3); Ericsson & Pool 2016 "Peak: Secrets from the New Science of Expertise" |
| Immediate feedback on attempt | Feedback principle | Hattie & Timperley 2007 "The power of feedback" Review of Educational Research 77(1) |

### 2.10 Affective Computing — Affect detection (P6D)

| Feature | Theory | Citations |
|---|---|---|
| Frustration / give-up signals | Affect detection in learning | D'Mello & Graesser 2010 "Multimodal semi-automated affect detection from conversational cues, gross body language, and facial features" User Modeling and User-Adapted Interaction 20(2) |
| Engagement vs disengagement | Engagement framework | Fredricks et al. 2004 "School engagement: Potential of the concept, state of the evidence" Review of Educational Research 74(1) |
| Cognitive-affective loop in learning | Confusion as learning opportunity | D'Mello et al. 2014 "Confusion can be beneficial for learning" Learning and Instruction 29 |

### 2.11 Early Warning + Risk modeling

| Feature | Theory | Citations |
|---|---|---|
| Survival analysis dropout (P5D) | Time-to-event analysis | Cox 1972 "Regression models and life-tables"; Lee & Zame 2018 "DeepHit: A Deep Learning Approach to Survival Analysis with Competing Risks" AAAI |
| Multi-signal risk score (P1F) | Educational data mining early warning | Macfadyen & Dawson 2010 "Mining LMS data to develop an 'early warning system' for educators"; Romero & Ventura 2010 "Educational data mining: A review of the state of the art" |

## 3. Code citation convention

```python
def update_mastery_v2(student_id, concept_id, ctx):
    """Update mastery using BKT extended with response-time and hint penalty.

    Grounded in:
    - Corbett & Anderson (1995) classic BKT formulation
    - Pardos & Heffernan (2011) KT-IDEM for difficulty awareness
    """
```

```typescript
// Grounded in: Deci, Koestner & Ryan (1999) — extrinsic rewards
// crowd out intrinsic motivation. NEVER add points/badges/streak.
function ProgressVisualization({ mastery, history }: Props) {
  return <MasteryFraming current={mastery} trajectory={history} />;
}
```

## 4. PR review checkpoint

Trong PR review, reviewer phải verify:

- [ ] Mọi function/component có behavior-change cho student có citation comment
- [ ] Citation match với theory map ở section 2 (hoặc thêm theory mới nếu missing)
- [ ] Causal experiment đã register với [causal-experiment skill](../.ruler/skills/causal-experiment/SKILL.md) trước rollout
- [ ] Không feature nào violate SDT (xem [MOTIVATION_DESIGN.md](MOTIVATION_DESIGN.md))

## 5. IRB partnership

Khi P6E [PUBLICATION_ROADMAP.md](PUBLICATION_ROADMAP.md) kick off, học thuyết này là backbone của paper. Partner faculty sẽ refine citations theo Vietnamese context. IRB application require theory grounding cho mọi causal experiment với human subjects.

## 6. Living document

Khi thêm theory mới, update section 2 + thêm row vào theory map + update PR template checklist. Đề nghị quarterly review với learning scientist trong team.
