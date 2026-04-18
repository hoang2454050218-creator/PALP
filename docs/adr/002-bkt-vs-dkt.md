# ADR-002: Bayesian Knowledge Tracing thay vì Deep Knowledge Tracing

* Status: Accepted
* Date: 2026-04
* Deciders: Pedagogical Lead, ML Lead
* Tags: pedagogy, machine-learning, adaptive

## Context

PALP cần thuật toán theo dõi mức nắm vững (mastery) của sinh viên cho từng
concept. Ba lớp lựa chọn:

1. **BKT (Bayesian Knowledge Tracing)** — mô hình HMM 4 tham số (`P(L0)`,
   `P(T)`, `P(G)`, `P(S)`), giải thích được, ít data yêu cầu.
2. **DKT (Deep Knowledge Tracing)** — RNN/LSTM, độ chính xác cao hơn 5-10%
   nhưng cần ≥50K interaction để train, không giải thích được decisions.
3. **SAKT (Self-Attentive Knowledge Tracing)** — Transformer-based,
   state-of-the-art accuracy, yêu cầu data + GPU.

Yêu cầu pilot 60-90 sinh viên × 10 tuần ≈ 30K-60K TaskAttempt → thiếu data
cho DKT/SAKT. Yêu cầu giải thích được mọi quyết định cho giảng viên (per
PALP design philosophy).

## Decision

Sử dụng **BKT** cho pilot và phase 1. Cấu hình mặc định:
* `P(L0) = 0.3`, `P(T) = 0.09`, `P(G) = 0.25`, `P(S) = 0.10`.
* Per-concept tuning trong Wave 4 MLOps (replay TaskAttempt 90 ngày, optimize
  Brier score).

Transition đến DKT/SAKT trong phase 2 nếu data >100K interaction sau pilot.

## Consequences

### Positive

* Mỗi quyết định advance/continue/supplement giải thích được bằng `p_mastery`
  cụ thể, giảng viên hiểu được.
* Không cần GPU, train được trên CPU container nhỏ.
* Calibration plot dễ vẽ, ECE đo được.

### Negative

* Accuracy thấp hơn DKT ~5-8% theo benchmark public dataset (ASSISTments).
* Không capture được dependency giữa concepts qua thời gian.
* Mitigation: ConceptPrerequisite graph + per-concept BKT params + override
  cho lecturer.

## Alternatives considered

* **DKT-Forgetting**: cải tiến DKT thêm forgetting decay — hứa hẹn nhưng
  vẫn không giải thích được.
* **PFA (Performance Factor Analysis)**: logistic regression đơn giản — thiếu
  modeling của learning over time.

## References

* Corbett & Anderson (1995) "Knowledge tracing"
* `backend/adaptive/engine.py` `update_mastery`, `decide_pathway_action`
* `backend/adaptive/tests/test_bkt_property.py` Hypothesis property tests
