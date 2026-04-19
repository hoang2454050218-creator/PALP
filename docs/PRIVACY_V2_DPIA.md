# Privacy v2 — Data Protection Impact Assessment (DPIA)

> Bản DPIA chính thức cho 14 consent types mới được thêm trong roadmap v3. Tuân thủ GDPR (EU), Vietnam Nghị định 13/2023/NĐ-CP, và FERPA (US) cho data học sinh. Phải refresh trước mỗi phase rollout.

## 1. Phương pháp

DPIA tuân theo template ICO (UK Information Commissioner's Office) Article 35 GDPR + bổ sung Vietnamese requirements:

1. Mô tả processing
2. Đánh giá necessity và proportionality
3. Threat model + risk assessment
4. Mitigation matrix
5. Consent flow
6. DPO sign-off (Data Protection Officer)

## 2. 14 consent types — overview

| # | Consent type | Phase | Default | Data category | Purpose limitation | Retention |
|---|---|---|---|---|---|---|
| 1 | `behavioral_signals` | P1 | off | Indirect PII (focus/idle/tab patterns) | Adaptive scaffolding + risk score | 90 days raw, indefinite aggregated |
| 2 | `cognitive_calibration` | P1 | off | Behavioral (confidence judgments) | Metacognitive feedback | 90 days raw, indefinite aggregated |
| 3 | `device_fingerprinting` | P0 | off | Indirect PII (canvas+audio+UA hash) | Multi-device session linking | 30 days, then anonymized |
| 4 | `ml_research_participation` | P0 | off | Anonymized aggregates | Causal experiments + research | Per-experiment retention (max 12 months) |
| 5 | `peer_comparison` | P3 | off | Indirect (cohort percentile views) | Show benchmark in same-ability cohort | Real-time, no storage |
| 6 | `peer_teaching` | P3 | off | Direct (peer pairing + chat) | Reciprocal teaching session | Session content 30 days, ratings indefinite |
| 7 | `ai_coach_cloud` | P4 | off | Direct (chat content sent to vendor) | LLM dialog with Anthropic/OpenAI | Conversation 30 days, anonymized longer |
| 8 | `ai_coach_local` | P4 | on | Direct (chat content stays local) | LLM dialog with Ollama in-infra | Conversation 30 days |
| 9 | `emergency_contact` | P4 | off | Direct PII (trusted person info) | Crisis escalation | Indefinite (until revoked) |
| 10 | `dkt_personalization` | P5 | off | Behavioral aggregates (training data) | DKT model individual prediction | Aggregated indefinite, raw 1 year |
| 11 | `affect_keystroke` | P6 | off | Behavioral biometric | Cognitive load proxy | 30 days raw, aggregated indefinite |
| 12 | `affect_linguistic` | P6 | off | Linguistic content | Sentiment from coach turns | Sentiment scalar 1 year, source 30 days |
| 13 | `affect_facial` | P6 | off | Behavioral biometric (on-device) | Valence/arousal scalar only | Scalar 30 days, NO raw video/landmarks ever |
| 14 | `parent_sponsor_view` | P6 | off | Direct PII (parent contact) | Read-only progress for trusted family | Indefinite (until revoked, 2-way) |

## 3. Per-consent DPIA

Mỗi consent có 6 sections: Processing, Necessity, Threats, Mitigations, Consent UX, Retention.

---

### 3.1 `behavioral_signals`

**Processing.** Frontend SDK (`frontend/src/lib/sensing/`) capture page visibility, idle, tab switch, frustration patterns. Batch ingest qua `POST /api/signals/ingest/`. Server rollup vào `SignalSession` 5-min windows. Raw events trong `EventLog`, aggregates trong `BehaviorScore`.

**Necessity.** Without this signal, "phân tâm" hoàn toàn invisible — không thể giải quyết 1 trong 4 vấn đề target. Less-invasive alternative: chỉ dùng task completion patterns (BKT v1 hiện tại) → không đủ độ phân giải.

**Threats.**
- Re-identification từ pattern (T1)
- Surveillance creep — feature mở rộng phạm vi quá purpose ban đầu (T2)
- Data breach (T3)
- Discriminatory profiling (T4)

**Mitigations.**
- T1: Aggregate vào 5-min windows (giảm fingerprinting); cohort minimum 5 trước khi report
- T2: Code review checkpoint mỗi PR — feature dùng `behavioral_signals` data phải declare purpose, audit log
- T3: Encrypted at rest (Fernet), TLS in transit, retention 90 days raw
- T4: P0 fairness audit cho mọi model dùng signal này

**Consent UX.** Plain Vietnamese: "Bạn cho phép PALP đo độ tập trung và phát hiện sự phân tâm để cải thiện việc học? (Chúng tôi không ghi lại nội dung bạn xem trên tab khác.) [Cho phép] [Không]". Granular subtoggle for each subtype (focus/idle/tab/frustration).

**Retention.** Raw `EventLog` rows 90 days. Aggregated `SignalSession` indefinite (anonymized after 1 year). Right to erasure: trigger Celery task xoá raw + flag aggregated as "erased_subject".

---

### 3.2 `cognitive_calibration`

**Processing.** Trước nộp bài, UI hỏi confidence Likert 1-5. Server pair với actual_correct, lưu `MetacognitiveJudgment`. Weekly feedback Coach.

**Necessity.** Calibration error là indicator đặc biệt mạnh cho metacognitive deficit (Dunlosky 2009). Without nó, không thể detect over/under-confidence pattern.

**Threats.**
- Self-judgment privacy (T1) — student có thể không muốn lecturer biết "tôi tưởng đúng nhưng sai"
- Performance pressure (T2) — calibration test thêm cognitive load

**Mitigations.**
- T1: `MetacognitiveJudgment` chỉ visible cho student và lecturer-with-explicit-need. Aggregate "calibration_score" trong RiskScore không show raw judgments.
- T2: UI optional skip ("Bỏ qua" button); không penalty nếu skip. Document trong [MOTIVATION_DESIGN.md](MOTIVATION_DESIGN.md).

**Consent UX.** "Trước nộp bài, bạn muốn tự đánh giá độ tự tin? Việc này giúp coach hiểu metacognition của bạn (Bạn nghĩ đúng vs Thực tế đúng). [Cho phép] [Không]"

**Retention.** 90 days raw, aggregated indefinite.

---

### 3.3 `device_fingerprinting`

**Processing.** Frontend `frontend/src/lib/device-id/` generate fingerprint từ canvas+audio+UA hash. Stable client ID lưu IndexedDB. Server linker (`backend/sessions/linker.py`) link sessions cùng user_id + temporal proximity 5min + fingerprint partial match.

**Necessity.** Sinh viên dùng laptop + mobile → signals fragmented nếu không stitch. Without fingerprinting, BKT/risk score thiếu data hoặc sai (cùng sv tính 2 lần).

**Threats.**
- Cross-site tracking (T1) — fingerprint có thể identify sv trên web khác
- Permanent tracking (T2) — khác cookie, khó clear
- Stalking risk (T3)

**Mitigations.**
- T1: Fingerprint chỉ dùng INSIDE PALP domain. Server không ship fingerprint hash ra ngoài. Audit code review.
- T2: Default off, opt-in với clear explanation. Right to clear → IndexedDB.clear() + server delete `DeviceFingerprint` rows.
- T3: Per [SECURITY threat model](RED_TEAM_PLAYBOOK.md), fingerprint data không truy cập được bởi other students; lecturer chỉ thấy "session_count_per_device" stats.

**Consent UX.** Detailed disclosure: "PALP có thể nhận dạng thiết bị của bạn (canvas + audio fingerprint) để gộp sessions từ laptop và mobile. [Tìm hiểu thêm] [Cho phép] [Không]". Link tới chi tiết kỹ thuật.

**Retention.** 30 days, sau đó hash anonymized với salt rotation hằng tháng → impossible to re-link.

---

### 3.4 `ml_research_participation`

**Processing.** Aggregated learning analytics export cho causal experiments + academic research (P6E [PUBLICATION_ROADMAP.md](PUBLICATION_ROADMAP.md)). DP noise injection (P6C [DIFFERENTIAL_PRIVACY_SPEC.md](DIFFERENTIAL_PRIVACY_SPEC.md)) trước khi rời institution.

**Necessity.** Causal-not-correlational principle (nguyên tắc 4 [AI_COACH_ARCHITECTURE.md](AI_COACH_ARCHITECTURE.md)) require A/B với uplift. External benchmarks require shareable aggregates.

**Threats.**
- Re-identification từ aggregates (T1)
- Research scope creep (T2)
- Cross-institution data leak (T3)

**Mitigations.**
- T1: ε-DP với epsilon ≤ 1.0 per training run; cohort minimum 5; suppression rule cells < 5
- T2: Per-experiment IRB approval (P6E); audit log mỗi data export
- T3: Federated option (Flower) — model weights only, raw data never leave institution

**Consent UX.** "Bạn có muốn data học của bạn (đã ẩn danh) được dùng để cải thiện hệ thống và đóng góp vào nghiên cứu giáo dục? Bạn có thể rút lại bất cứ lúc nào." [Cho phép] [Không] [Tìm hiểu nghiên cứu]

**Retention.** Per-experiment, max 12 months. Right to withdraw triggers exclude from future analyses; existing aggregates retained per IRB protocol.

---

### 3.5 `peer_comparison`

**Processing.** `backend/peer/services/benchmark.py` compute percentile trong cohort cùng năng lực ban đầu (k-means trên assessment score). UI hiển thị "Top 30% trong nhóm 25 bạn cùng xuất phát".

**Necessity.** Optional feature cho student muốn so peer. Không essential — `frontier-mode` (chỉ vs past-self) là default + main mode.

**Threats.**
- Tự ti / discouragement (T1)
- Re-identification trong cohort nhỏ (T2)
- Competitive culture creep (T3)

**Mitigations.**
- T1: Default OFF, chỉ opt-in sau 4 tuần học (UI prompt clearly explain pros/cons). Frontier-mode is default.
- T2: Cohort minimum size 10 trước khi show benchmark; cell suppression < 5; no names/ranks.
- T3: Per [MOTIVATION_DESIGN.md](MOTIVATION_DESIGN.md) anti-gamification — copywriting guideline forbid comparison framing.

**Consent UX.** Sau 4 tuần on-board: "Bạn đã học 4 tuần. Có muốn xem mình đang ở khoảng nào trong nhóm 25 bạn cùng xuất phát điểm (ẩn danh)? Nhiều bạn thấy có ích, nhưng cũng có bạn không thoải mái. Bạn có thể bật/tắt bất cứ lúc nào." [Bật] [Không, giữ frontier-mode]

**Retention.** Real-time computation, no storage of individual percentile history.

---

### 3.6 `peer_teaching`

**Processing.** `backend/peer/services/reciprocal_matcher.py` match sv A (mạnh X yếu Y) với sv B. `TeachingSession` model store turn-based session metadata + chat content (encrypted).

**Necessity.** Reciprocal teaching evidence-based (Topping 2005, Fiorella & Mayer 2013). Single most effective peer learning intervention.

**Threats.**
- Direct PII exchange (T1)
- Bullying / inappropriate content (T2)
- Mismatched expectations (T3)

**Mitigations.**
- T1: Peer pairing không reveal full name unless mutual consent. Default display: nickname.
- T2: Content moderation (linguistic affect P6D + report button). Lecturer can audit on report.
- T3: Pre-session brief explain expectations. Mutual rating after session.

**Consent UX.** "Bạn có muốn ghép với 1 bạn để dạy nhau? Bạn sẽ giải thích concept X cho bạn ấy, và họ sẽ giải thích Y cho bạn. Đây là cách học mạnh nhất theo nghiên cứu giáo dục." [Cho phép] [Không]

**Retention.** Session chat 30 days encrypted, ratings indefinite anonymized.

---

### 3.7 `ai_coach_cloud`

**Processing.** Chat content sent to Anthropic Claude / OpenAI GPT cho non-sensitive intents. PII Guard mask trước, restore sau. Vendor sees tokenized content only.

**Necessity.** Cloud LLM chất lượng cao nhất cho dialog/explain/summarize. Local LLM 7B chưa đủ cho task non-sensitive nhưng đòi hỏi reasoning depth.

**Threats.**
- Vendor data leak / breach (T1)
- Content used for vendor model training (T2)
- Cross-border data transfer (T3 — vendor servers ngoài VN)
- Hallucination → misinformation (T4)

**Mitigations.**
- T1: PII Guard layer (`coach/llm/pii_guard.py`); CoachAuditLog every call; quarterly red team [RED_TEAM_PLAYBOOK.md](RED_TEAM_PLAYBOOK.md)
- T2: Vendor contract opt-out training (Anthropic Workspace, OpenAI API "no train"); Zero Data Retention with Anthropic when available
- T3: Disclose location in consent; allow user to choose `ai_coach_local` only mode
- T4: Output validator + canary tokens + watermark; coach disclaim "Đây là gợi ý từ AI, không thay thế tư vấn chuyên môn"

**Consent UX.** "Coach AI có thể dùng dịch vụ Anthropic/OpenAI (server ngoài VN) cho các tin nhắn không nhạy cảm. Tin nhắn về cảm xúc, sức khoẻ tâm thần CHỈ dùng AI nội bộ. PII (tên/email/MSSV) được mask trước khi gửi. [Cho phép cả 2] [Chỉ AI nội bộ] [Không dùng coach]"

**Retention.** Conversation 30 days encrypted. Anonymized aggregates indefinite (per Anthropic/OpenAI API logs ≤ 30 days at vendor side, contract-enforced).

---

### 3.8 `ai_coach_local`

**Processing.** Chat content via Ollama in-infra (Docker service). Model llama3:8b-instruct hoặc qwen2.5:7b-instruct. Never leaves infrastructure.

**Necessity.** Sensitive intents (frustration, give_up, mental health) MUST stay in-infra. Default-on để có safety net minimum.

**Threats.**
- In-infra breach (T1)
- Hallucination on critical topics (T2)
- Performance degradation (T3 — 7B model)

**Mitigations.**
- T1: Same security as other PALP services (TLS in-cluster, network policies, Docker security)
- T2: Stricter output validator cho sensitive intents; auto-route to emergency pipeline if certain triggers
- T3: vLLM for prod scale; cache common responses; fallback to template if model timeout

**Consent UX.** "Coach AI nội bộ (chạy trong server PALP, không gửi data ra ngoài) sẽ giúp bạn với các vấn đề nhạy cảm như cảm xúc, lo lắng. Chúng tôi mặc định bật. Bạn có thể tắt bất cứ lúc nào." [Bật mặc định] [Tắt]

**Retention.** 30 days encrypted, hard-delete on revoke.

---

### 3.9 `emergency_contact`

**Processing.** Sv pre-register trusted person (lecturer/parent/friend) với contact info encrypted. Used ONLY khi emergency pipeline trigger và counselor không respond trong SLA.

**Necessity.** Self-harm crisis SLA — counselor có thể miss; emergency contact là last-resort safety net.

**Threats.**
- Misuse (false alarm contact parent) (T1)
- Privacy violation (sv không muốn parent biết) (T2)
- Contact info breach (T3)

**Mitigations.**
- T1: 2-step verification before activate emergency_contact (counselor must confirm SLA missed); audit log; post-incident review
- T2: Sv chooses any trusted person (not necessarily parent). Can revoke any time. Sv informed when activated.
- T3: Encrypted at rest (Fernet); access requires emergency-flag + audit; access expire 24h after incident close

**Consent UX.** Detailed multi-step: "Trong trường hợp hệ thống phát hiện bạn đang gặp khó khăn nghiêm trọng, và counselor không trả lời trong 15 phút, bạn muốn ai được liên hệ? (Họ sẽ chỉ được gọi/email khi thực sự cần — không phải vấn đề học tập thông thường.) [Add contact: tên, quan hệ, SĐT/email] [Có thể bỏ qua, không bắt buộc]"

**Retention.** Indefinite (until revoked). Hard-delete on revoke.

---

### 3.10 `dkt_personalization`

**Processing.** `backend/dkt/` train SAKT/AKT transformer trên individual student attempt sequences. Without consent, sv chỉ dùng cohort-aggregated DKT prediction.

**Necessity.** Personalized DKT chính xác hơn cohort-aggregated 15-30% AUC. Là core value proposition của Phase 5.

**Threats.**
- Model inversion attack — extract training data từ model (T1)
- Membership inference — biết sv X có trong training set (T2)
- Profile creation cho discrimination (T3)

**Mitigations.**
- T1, T2: P6C Differential Privacy (Opacus DP-SGD with ε ≤ 1.0)
- T3: Model use limited to PALP internal; no export to third party; fairness audit P0 ngăn discrimination

**Consent UX.** "DKT cá nhân hoá: model AI sẽ học pattern học của riêng bạn để dự đoán mastery chính xác hơn. Data train được bảo vệ bằng Differential Privacy. [Cho phép] [Không, dùng model chung]"

**Retention.** Aggregated weights indefinite (anonymized via DP). Individual training data 1 year, then deleted.

---

### 3.11-13 `affect_keystroke` / `affect_linguistic` / `affect_facial`

3-tier consent — sv opt-in từng tier riêng (tăng dần độ nhạy cảm).

**Tier 1 (`affect_keystroke`):** keystroke dynamics → cognitive load proxy. Aggregated stats only (window 60s), no individual key logging.

**Tier 2 (`affect_linguistic`):** sentiment trên CoachTurn content. Local model PhoBERT. Output là 2 scalar (valence, arousal).

**Tier 3 (`affect_facial`):** **on-device only**. MediaPipe Face Landmarker chạy in-browser. Server CHỈ nhận 2 scalar. Raw video/landmarks NEVER transmitted. Server reject nếu metadata missing `on_device_processed: true`.

**Necessity.** Affect detection literature 2020+ (D'Mello & Graesser 2010+) cho thấy multi-modal nâng accuracy 20-30%. Frustration rule-based hiện tại miss nhiều cases.

**Threats per tier:**
- Tier 1: behavioral biometric profiling (T1)
- Tier 2: emotional content analysis privacy (T2)
- Tier 3: **biometric facial data** — highest risk per GDPR Special Category (T3)

**Mitigations.**
- T1: Aggregated only, sample rate 0.1, encrypted at rest, retention 30 days
- T2: Local PhoBERT only, no cloud LLM for sentiment; output scalar only
- T3: On-device hard requirement. Server validation reject non-compliant. Device permission camera each session (browser native). Easy on/off toggle persistent in UI. Audit log every session start/stop.

**Consent UX.** Multi-step staircase. "Affect detection — bạn muốn coach 'cảm' được trạng thái cảm xúc của bạn để hỗ trợ tốt hơn? Có 3 cấp độ, bạn chọn từng cấp:
1. Keystroke rhythm (đo nhịp gõ phím) [Cho phép]
2. Sentiment trên tin nhắn coach (model nội bộ) [Cho phép]
3. Facial expression (CHỈ chạy trong browser của bạn, không gửi video ra ngoài) [Cho phép]
Bạn có thể bật từng cái độc lập."

**Retention.** Tier 1: 30 days raw. Tier 2: scalar 1 year, source 30 days. Tier 3: scalar 30 days, NEVER raw video/landmarks.

---

### 3.14 `parent_sponsor_view`

**Processing.** Parent/sponsor account (new role) read-only view tiến độ sv. 2-way opt-in (cả sv và parent confirm). No PII detail (no chat content, no calibration error).

**Necessity.** Multi-stakeholder coverage (nguyên tắc 8). Parent là stakeholder quan trọng đặc biệt với sinh viên năm nhất.

**Threats.**
- Surveillance / autonomy violation (T1)
- Coercion (parent force sv to consent) (T2)
- Detail leak (parent thấy quá nhiều) (T3)

**Mitigations.**
- T1: 2-way opt-in mandatory; sv có thể revoke any time without parent notification; parent chỉ thấy aggregated progress
- T2: Lecturer can flag suspected coercion; counselor outreach
- T3: Aggregated mastery + completion only; NO chat content, NO behavioral signal detail, NO emergency events visible to parent

**Consent UX.** "Phụ huynh / người bảo trợ của bạn có thể xem tiến độ học (chỉ tổng quan, không chi tiết). Đây là 2-chiều — phụ huynh cũng phải confirm. Bạn có thể tắt bất cứ lúc nào, phụ huynh sẽ không được thông báo. [Cho phép] [Không]"

**Retention.** Indefinite (until revoked). Hard-delete on either party revoke.

## 4. Threat model — overall

| Threat | Likelihood | Impact | Mitigation chính |
|---|---|---|---|
| Data breach via vendor (cloud LLM) | Medium | High | PII Guard, contract opt-out training, audit |
| Insider threat (lecturer abuse) | Low | High | RBAC + audit log + quarterly access review |
| Re-identification từ aggregates | Medium | Medium | DP noise + cell suppression + cohort min 5 |
| Model inversion attack | Low | Medium | DP-SGD ε ≤ 1.0 |
| Cross-border data transfer non-compliance | Medium | High | User choice cloud vs local; consent disclosure |
| Surveillance creep | High | Medium | Per-PR purpose declaration; quarterly DPIA refresh |
| Discriminatory profiling | Medium | High | Fairness audit CI gate (P0) |
| Self-harm crisis missed | Low | **Critical** | Emergency pipeline P4D; 15-min SLA |

## 5. Consent UX principles

1. **Granular** — không bundle nhiều consent vào 1 toggle.
2. **Plain Vietnamese** — no legalese; technical detail in optional "Tìm hiểu thêm" link.
3. **Reversible** — every consent revokable any time, settings page có "Privacy Hub".
4. **Default safe** — defaults towards minimal data collection. Only `ai_coach_local` defaults ON.
5. **Cooling-off** — sensitive consents (affect_facial, peer_comparison) prompt sau onboarding period (4 weeks), not on first login.
6. **Re-consent on version bump** — `CONSENT_VERSION` change triggers fresh flow (per existing `ConsentGateMiddleware`).

## 6. Right of subject (GDPR + NĐ 13/2023)

| Right | Implementation | Endpoint |
|---|---|---|
| Right to access (GDPR Art.15) | Export full data dump | `/api/privacy/export/` (existing) |
| Right to rectification (Art.16) | Profile edit | `/api/auth/profile/` PATCH |
| Right to erasure (Art.17) | Delete account + cascade hard-delete | `/api/privacy/delete/` (existing) |
| Right to portability (Art.20) | JSON export with schema | `/api/privacy/export/?format=json` |
| Right to object (Art.21) | Per-consent revoke | `/api/privacy/consents/` PATCH |
| Right to explanation (Art.22) | XAI panel cho automated decisions | `/api/explain/*` (P6A) |
| Vietnam Art.21-23 NĐ 13/2023 | Process info disclosure | `/api/privacy/processing-info/` |

## 7. DPO sign-off process

Trước mỗi phase rollout:
1. Refresh DPIA (this doc) cho consent mới
2. Internal DPO review
3. External legal review (annual)
4. Update [PRIVACY_INCIDENT.md](PRIVACY_INCIDENT.md) playbook nếu threat model thay đổi
5. Consent flow QA test (Playwright E2E `consent-version-bump.spec.ts`)
6. Audit log verification (sample 100 sensitive accesses, verify all logged)

## 8. Phase-level DPIA refresh schedule

| Phase | DPIA refresh trigger | New consents | Risk classification |
|---|---|---|---|
| P0 | Pre-rollout | `device_fingerprinting`, `ml_research_participation` | Medium |
| P1 | Pre-rollout | `behavioral_signals`, `cognitive_calibration` | Medium |
| P3 | Pre-rollout | `peer_comparison`, `peer_teaching` | Medium |
| P4 | Pre-rollout (mandatory legal review) | `ai_coach_cloud`, `ai_coach_local`, `emergency_contact` | **High** |
| P5 | Pre-rollout | `dkt_personalization` | Medium |
| P6 | Pre-rollout (mandatory legal review for facial) | `affect_keystroke`, `affect_linguistic`, `affect_facial`, `parent_sponsor_view` | **High** |

## 9. Living document

DPIA refresh quarterly hoặc khi:
- New threat scenario detected (red team output)
- Vendor terms change
- Legal regulation update (GDPR, NĐ 13/2023 amendments)
- Incident postmortem reveals gap
