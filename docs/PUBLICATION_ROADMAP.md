# Publication Roadmap — LAK / AIED / EDM

> Plan academic publication cho Phase 6E (External Benchmarks + Academic Co-design). Mục tiêu: ≥1 paper submission tới LAK/AIED/EDM 2027 deadline. Phase 6 gate criteria.

## 1. Tại sao publish

PALP roadmap v3 contains research-grade contributions:
- Hybrid BKT + DKT với causal validation (P5)
- Reciprocal peer teaching algorithm với fairness audit (P3)
- Multi-modal affect detection on-device (P6D)
- Dual-LLM coach architecture với emergency pipeline (P4)
- Differential privacy cho educational data at scale (P6C)

Publishing converts internal innovation → field contribution. Benefits:
- **Validation**: peer review catches blind spots
- **Reputation**: institution + team
- **Talent**: attract specialists
- **Funding**: grants, partnerships
- **Society**: contribute to global education research

Cost: significant time (30-50% of P6E budget on writing/IRB), risk of scoop nếu chậm.

## 2. Target conferences

### 2.1 Tier 1 venues (top priority)

| Venue | Full name | Deadline (typical) | Rank |
|---|---|---|---|
| **LAK** | Learning Analytics & Knowledge | September | A |
| **AIED** | International Conference on Artificial Intelligence in Education | January | A |
| **EDM** | Educational Data Mining | February | A |
| **CHI EDU** | CHI Education subcommittee | September | A* |

### 2.2 Tier 2 venues (alternative / secondary papers)

- L@S (Learning at Scale)
- ITS (Intelligent Tutoring Systems)
- Journal of Learning Analytics (JLA)
- IEEE Transactions on Learning Technologies (TLT)
- Computers & Education (Elsevier)

### 2.3 Workshops (low-stakes start)

- LAK workshops (e.g., LAK-LAS Learning Analytics Specifications)
- NeurIPS workshops on AI for Education
- ACM SIGCSE for CS education focus

## 3. Paper roadmap

### 3.1 Paper 1: Hybrid BKT-DKT with Causal Validation

**Target**: AIED 2027 (deadline January 2027)

**Hypothesis**: Hybrid BKT (interpretable) + DKT (predictive) outperforms either alone trên Vietnamese higher-ed dataset, validated với causal A/B not just correlational benchmarks.

**Methods**:
- BKT v2 (P1) baseline
- DKT/SAKT (P5) deep model
- Hybrid ensemble với uplift estimator (P0 causal)
- Validate trên: PALP internal data (3000+ students), EdNet, ASSISTments 2017
- Fairness audit (P0) per subgroup (gender, region)

**Contribution**:
- Hybrid architecture novel
- Causal validation (vs correlational standard) is methodological contribution
- Vietnamese context (under-represented in literature)

**Authors**: Tech lead ML + Learning scientist + Faculty co-author (VNU/HUST)

**Timeline**:
- Q1 2026: data collection design
- Q2 2026: baseline experiments
- Q3 2026: hybrid + causal experiments
- Q4 2026: write paper + internal review
- January 2027: submit AIED

### 3.2 Paper 2: Reciprocal Peer Teaching with Fairness Audit

**Target**: LAK 2027 (deadline September 2027)

**Hypothesis**: Reciprocal peer teaching (mạnh-yếu chéo) với weekly fairness audit prevent demographic clustering bias, improve learning outcome cho both peers vs control (1-chiều buddy).

**Methods**:
- 3-arm RCT: control (no peer), 1-chiều buddy, reciprocal teaching
- Sample size 200+ pairs
- Outcome: mastery delta, engagement, IMI motivation scale
- Fairness analysis: subgroup outcomes parity
- Qualitative: post-session interviews (n=20)

**Contribution**:
- Algorithm spec public
- Fairness audit methodology novel for peer matching
- Mixed-method (quant + qual)

**Authors**: Tech lead Backend + Learning scientist + Faculty + ethnographer (potential)

**Timeline**:
- Q2 2026: pilot study
- Q3 2026: full RCT
- Q1 2027: analysis + write
- September 2027: submit LAK

### 3.3 Paper 3: Emergency Pipeline for Mental Health in Adaptive Learning

**Target**: CHI EDU 2027 or JLA 2027

**Hypothesis**: Multi-layer detection (keyword + zero-shot LLM) + 15-min counselor SLA + 3-level escalation reduces missed crises vs baseline (manual reporting only).

**Methods**:
- Pre-post comparison: 6 months baseline (existing wellbeing nudge), 6 months full pipeline
- Outcome: detection rate, time-to-counselor, follow-up completion, student satisfaction
- Qualitative: counselor interviews
- Ethics: IRB heavy review

**Contribution**:
- Pipeline design + open-source detector
- First reported empirical evaluation in VN higher-ed context
- Potentially life-saving intervention design

**Authors**: Privacy/Security eng + Counselor coordinator + Mental health professional + Faculty

**Timeline**:
- Q3 2026: pre-implementation baseline measurement
- Q1 2027: pipeline rollout
- Q2-Q3 2027: data collection
- Q4 2027: analysis + write
- 2028 submission

### 3.4 Paper 4 (stretch): Dual-LLM Coach Architecture for Privacy-Preserving Education

**Target**: NeurIPS Education workshop 2027 hoặc EDM 2028

**Hypothesis**: Dual-LLM (Cloud cho non-sensitive, Local cho sensitive) với PII Guard architecture preserves privacy without sacrificing dialog quality.

**Methods**:
- Architecture description
- Privacy threat model + DP analysis
- Quality benchmarks (vs cloud-only and local-only)
- User study (n=100): perceived privacy, perceived helpfulness

**Contribution**:
- Reference architecture for privacy-conscious LLM education
- Open-source PII Guard implementation

## 4. IRB partnership

### 4.1 Why IRB

Causal experiments với human subjects require IRB review for:
- Ethical compliance
- Subject protection
- Publication eligibility (most venues require)
- Legal liability

### 4.2 Partner institutions

Target faculty learning sciences departments:
- VNU University of Engineering and Technology (Hanoi)
- HUST (Hanoi University of Science and Technology) — Education department
- HCMUT (HCMC University of Technology) — Education program
- (Optional) International: SMU Singapore, NTU Singapore

### 4.3 IRB application timeline

For each major study:
- 3 months prep (protocol, consent forms, risk assessment)
- 1-3 months IRB review
- Approval valid 1 year, renewable

Start IRB process 6 months before planned data collection.

### 4.4 Standing IRB protocol

Establish standing IRB approval for ongoing PALP causal experiments (umbrella protocol). Each new experiment is amendment to standing protocol — faster than new application.

## 5. Data sharing & open science

### 5.1 Public dataset release

After GA v3.0 + IRB approval, release anonymized PALP dataset publicly:
- BKT-style: student attempts với DP noise injected
- Format: compatible với KDD Cup, ASSISTments format
- License: CC BY-NC 4.0
- Hosted: Zenodo / HuggingFace Datasets

Contribution: under-represented Vietnamese context in EDM datasets.

### 5.2 Open-source releases

Open-source components valuable to community:
- PII Guard (multi-language NER + masking) — `palp-pii-guard` package
- Fairness audit clustering — `palp-fairness-cluster` package
- Reciprocal peer matcher — `palp-reciprocal-match` package
- Dual-LLM router architecture — reference implementation

License: Apache 2.0 (permissive, encourage adoption).

### 5.3 Reproducibility

Each paper includes:
- Code on GitHub (with DOI via Zenodo)
- Trained models on HuggingFace Hub (when DP allows)
- Dataset (with IRB approval + DP noise)
- Docker compose for reproducibility
- Notebook walkthroughs

## 6. Co-author management

### 6.1 Authorship criteria

Per ICMJE (International Committee of Medical Journal Editors):

1. Substantial contribution to conception/design OR data collection OR analysis
2. Drafting OR revising critically
3. Final approval of version to be published
4. Accountable for all aspects of work

Authors meet ALL 4 criteria.

### 6.2 Order

- First author: lead researcher (usually tech lead or learning scientist)
- Middle authors: contributors
- Last author: senior PI (faculty partner) — convention in academia
- Equal contribution: noted in footnote

### 6.3 Acknowledgments

Non-author contributors (e.g., students who helped data collection, counselors who reviewed protocol) acknowledged separately.

## 7. Publication ethics

### 7.1 Conflicts of interest

Disclose:
- PALP institutional affiliation
- Faculty partner affiliation
- Vendor relationships (Anthropic, OpenAI, etc.)
- Funding sources

### 7.2 Data integrity

- Pre-registration (e.g., OSF) for confirmatory studies
- All hypotheses pre-stated
- All statistical tests pre-specified
- Negative results published (no file-drawer effect)

### 7.3 Plagiarism + self-plagiarism

- Original wording (use Turnitin pre-submission)
- Cite own prior work (no double-publishing)

### 7.4 Reviewer ethics

If invited to review competing work, recuse if conflict.

## 8. Marketing + dissemination

### 8.1 Conference presentation

- Practice talk internally 2x before
- 12-15 slides for 15-min talk
- Demo video (especially for system papers)
- Q&A prep

### 8.2 Post-publication

- Blog post on PALP institution site
- Twitter/X thread (if account)
- LinkedIn announcement
- Cross-post to ResearchGate, Academia.edu
- Press release (if institution does this)

### 8.3 Citations tracking

- Set up Google Scholar Alerts for paper title
- Track citations in CV
- Engage with citing work (often leads to collaboration)

## 9. Phase 6 Gate criterion

P6 Gate requires:

- [ ] IRB approval obtained for at least 1 study
- [ ] EdNet AUC for DKT within ±2% of published SOTA
- [ ] At least 1 paper draft completed
- [ ] At least 1 paper submitted (not necessarily accepted yet) to LAK/AIED/EDM 2027

## 10. Long-term — beyond v3.0

- Annual paper submission cadence
- Workshop hosting (e.g., "Vietnamese Learning Analytics" workshop at LAK)
- Special issue editor in JLA / TLT
- Keynote invitations
- Funding grants (NAFOSTED, World Bank, Gates Foundation)

## 11. Risks

| Risk | Mitigation |
|---|---|
| Scoop (other team publishes similar first) | Pre-print on arXiv early; prioritize unique angle (Vietnamese context, fairness) |
| IRB delay blocks data collection | Start standing protocol early; have backup studies |
| Negative results | Publish anyway (open science culture); negative results are contributions |
| Team capacity for writing | Dedicate Academic Liaison role (0.5 FTE); use Faculty co-author for academic style |
| External validity questioned | Multi-site studies (multiple Vietnamese institutions) |

## 12. Skills + related docs

- [LEARNING_SCIENCE_FOUNDATIONS.md](LEARNING_SCIENCE_FOUNDATIONS.md) — citation backbone
- [PRIVACY_V2_DPIA.md](PRIVACY_V2_DPIA.md) — `ml_research_participation` consent
- [DIFFERENTIAL_PRIVACY_SPEC.md](DIFFERENTIAL_PRIVACY_SPEC.md) — DP for shareable data
- [causal-experiment skill](../.ruler/skills/causal-experiment/SKILL.md) — methodology
- [model_cards/](model_cards/) — reproducibility artifacts

## 13. Living document

Update khi:
- Paper accepted/rejected (track lessons)
- New venue emerges
- Faculty partnership formalized
- Major dataset/code release
