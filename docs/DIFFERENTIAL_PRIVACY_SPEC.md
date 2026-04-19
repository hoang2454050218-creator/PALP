# Differential Privacy Specification

> Spec chính thức cho `backend/privacy_dp/` (Phase 6C). Privacy at scale — bảo vệ individual student trong aggregated analytics, DKT training, federated multi-trường. Đi kèm [PRIVACY_V2_DPIA.md](PRIVACY_V2_DPIA.md).

## 1. Tại sao cần DP

Consent + encryption + RBAC + audit là defense layers tốt cho **direct PII access**. Nhưng có 3 attack class mà các defense này **không bảo vệ**:

1. **Model inversion**: extract training data từ DKT model weights
2. **Membership inference**: biết student X có trong training set
3. **Reconstruction từ aggregates**: re-identify từ cohort statistics khi cohort nhỏ

Differential Privacy provide **mathematical guarantee** chống cả 3.

## 2. Khái niệm cơ bản

### 2.1 ε-Differential Privacy

Một mechanism `M` là ε-differentially private nếu với mọi 2 dataset `D` và `D'` chỉ khác nhau 1 record, và mọi output set `S`:

```
P(M(D) ∈ S) ≤ e^ε * P(M(D') ∈ S)
```

Trực giác: kết quả `M` thay đổi rất ít khi 1 sinh viên thêm/bớt → attacker không thể infer sinh viên đó từ output.

### 2.2 Epsilon (ε) budget

- ε nhỏ → privacy mạnh (nhiều noise) → utility giảm
- ε lớn → privacy yếu → utility cao
- Industry consensus: ε ≤ 1.0 cho strong privacy, ε ≤ 10 cho practical

PALP commit: **ε ≤ 1.0 per training run**, total ε per student per year ≤ 5.0 (composition).

### 2.3 (ε, δ)-DP

Relaxed version cho practical ML:
- δ = probability mechanism fails to be ε-DP
- Standard: δ = 1e-5 hoặc 1/n^2 với n = dataset size

PALP: δ = 1e-5.

## 3. Where DP applies

### 3.1 DKT Training (P5 → P6C)

**Without DP**: Train SAKT on individual student attempt sequences. Risk: model memorize specific students.

**With DP-SGD via Opacus**:

```python
# backend/dkt/trainer_dp.py
from opacus import PrivacyEngine

def train_dkt_dp(model, dataloader, epochs=10):
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.BCELoss()
    
    privacy_engine = PrivacyEngine()
    model, optimizer, dataloader = privacy_engine.make_private(
        module=model,
        optimizer=optimizer,
        data_loader=dataloader,
        noise_multiplier=1.1,
        max_grad_norm=1.0,
    )
    
    for epoch in range(epochs):
        for batch in dataloader:
            optimizer.zero_grad()
            loss = criterion(model(batch.x), batch.y)
            loss.backward()
            optimizer.step()
    
    epsilon = privacy_engine.accountant.get_epsilon(delta=1e-5)
    
    if epsilon > settings.PALP_DP["EPSILON_BUDGET_PER_RUN"]:
        raise EpsilonBudgetExceeded(f"ε={epsilon} > {settings.PALP_DP['EPSILON_BUDGET_PER_RUN']}")
    
    return model, epsilon
```

### 3.2 Aggregated cohort analytics (P6C)

**Without DP**: cohort statistics like "average mastery in cohort X = 72%". Risk: combine with auxiliary info → re-identify.

**With DP noise injection**:

```python
# backend/privacy_dp/noise_injector.py
def laplace_noise(value: float, sensitivity: float, epsilon: float) -> float:
    """Add Laplace noise scaled by sensitivity / epsilon."""
    scale = sensitivity / epsilon
    noise = np.random.laplace(0, scale)
    return value + noise

def gaussian_noise(value: float, sensitivity: float, epsilon: float, delta: float) -> float:
    """Add Gaussian noise for (ε, δ)-DP."""
    sigma = (sensitivity / epsilon) * np.sqrt(2 * np.log(1.25 / delta))
    noise = np.random.normal(0, sigma)
    return value + noise

def dp_aggregate(values: list[float], epsilon: float, sensitivity: float = 1.0) -> float:
    """DP-protected mean aggregate."""
    true_mean = np.mean(values)
    return laplace_noise(true_mean, sensitivity / len(values), epsilon)
```

Apply trong:
- Cohort mean mastery (per-concept)
- Cohort completion rates
- Risk score distribution histograms
- KPI exports

### 3.3 Federated DKT (P6C, multi-trường, optional)

**Setup**: Mỗi trường có DKT instance trained on local data. Periodic federated update — chia weights average với DP noise.

```python
# backend/privacy_dp/flower_federated.py
import flwr as fl

class PALPClient(fl.client.NumPyClient):
    """Each institution runs this client."""
    
    def fit(self, parameters, config):
        # Train locally with DP
        model.set_weights(parameters)
        model, epsilon = train_dkt_dp(model, local_dataloader, epochs=1)
        
        # Add additional noise on weights before sending
        new_weights = [add_dp_noise(w, epsilon=0.5) for w in model.get_weights()]
        return new_weights, len(local_dataloader.dataset), {"epsilon": epsilon}
    
    def evaluate(self, parameters, config):
        model.set_weights(parameters)
        loss, accuracy = evaluate_local(model, local_test_loader)
        return float(loss), len(local_test_loader.dataset), {"accuracy": accuracy}

class PALPServer(fl.server.strategy.FedAvg):
    """Central aggregator."""
    
    def aggregate_fit(self, server_round, results, failures):
        # Weighted average with secure aggregation
        return super().aggregate_fit(server_round, results, failures)
```

Raw student data **never** leaves institution. Only DP-protected model weights.

## 4. Threat model

### 4.1 Adversary model

| Adversary type | Capability | Defense |
|---|---|---|
| Curious researcher | Read aggregated cohort stats | DP noise on aggregates |
| Insider lecturer | Access own class data | RBAC + audit (existing); DP-protected exports for cross-class |
| External attacker (data breach) | Steal model weights | DP-trained model resists inversion |
| Malicious other institution (federated) | Reverse-engineer from weight updates | Secure aggregation + DP per-update |
| Compromised internal DB | Steal raw data | Fernet encryption (existing); DP doesn't replace encryption |

### 4.2 What DP protects

✅ Membership inference: "is student X in training data?"
✅ Attribute inference: "what's student X's exact mastery on concept Y?"
✅ Reconstruction from aggregates: "deduce individuals from cohort stats"

### 4.3 What DP does NOT protect

❌ Direct authorized access (use RBAC + audit + encryption)
❌ Side-channel attacks (timing, network)
❌ Social engineering on counselors/admins
❌ Insider with high access (use principle of least privilege)

DP is **complementary** to existing defenses, not replacement.

## 5. Epsilon Budget Management

### 5.1 Per-student lifetime budget

Each student has cumulative ε budget per year:

```python
# backend/privacy_dp/epsilon_budget.py
class EpsilonBudget(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE)
    year = models.IntegerField()
    epsilon_used = models.FloatField(default=0.0)
    epsilon_limit = models.FloatField(default=5.0)  # configurable
    
    def can_spend(self, epsilon_amount: float) -> bool:
        return self.epsilon_used + epsilon_amount <= self.epsilon_limit
    
    def spend(self, epsilon_amount: float, purpose: str):
        if not self.can_spend(epsilon_amount):
            raise EpsilonBudgetExceeded()
        self.epsilon_used += epsilon_amount
        self.save()
        EpsilonSpendLog.objects.create(
            student=self.student,
            amount=epsilon_amount,
            purpose=purpose,
        )
```

### 5.2 Composition theorems

When student data used in K queries với ε_i each:
- **Sequential**: Total ε = Σ ε_i (worst case)
- **Advanced composition**: tight bound via privacy accountant (Opacus uses RDP accountant)

PALP uses RDP (Rényi DP) accountant in Opacus for tight bounds.

### 5.3 Budget exhaustion

If student exceeds yearly budget:
- New training runs exclude this student
- Aggregated queries cap their contribution
- Notify student (transparency): "Bạn đã đóng góp tối đa data nghiên cứu năm nay"

## 6. Implementation roadmap

### 6.1 Phase 6C tasks

| Task | Owner | ETA |
|---|---|---|
| Setup `backend/privacy_dp/` app | Privacy/Security eng | Week 1 |
| Integrate Opacus with DKT training | ML eng + Privacy eng | Week 2-3 |
| Add `EpsilonBudget` model + migrations | Privacy eng | Week 1-2 |
| Integrate noise_injector into KPI exports | ML eng | Week 3-4 |
| Setup Flower for federated (proof of concept, single-trường first) | ML eng | Week 4 |
| Write tests + validate epsilon accountant | All | Week 4 |
| External crypto/DP review | External consultant | Week 4 |
| Document in [PRIVACY_V2_DPIA.md](PRIVACY_V2_DPIA.md) | Privacy eng | Week 1-4 |

### 6.2 Multi-institution federated (post-GA)

Federated requires:
- MOU between institutions
- IRB approval per institution
- Secure communication channel (mTLS)
- Audit log shared between institutions
- Designated coordinator institution

Out of scope for v3.0 GA. Plan for v3.1.

## 7. Validation

### 7.1 DP guarantee verification

Per training run:
```python
def verify_dp_guarantee(privacy_engine, expected_epsilon, expected_delta):
    actual_epsilon = privacy_engine.accountant.get_epsilon(delta=expected_delta)
    assert actual_epsilon <= expected_epsilon, f"DP violated: {actual_epsilon} > {expected_epsilon}"
```

### 7.2 Empirical testing

- **Membership inference attack**: implement standard MIA, verify accuracy ≤ 51% (random chance) on DP-trained model
- **Model extraction**: attempt to extract training samples, verify failure
- **Reconstruction**: attempt to recover individual records from aggregates, verify failure

These tests in [`backend/privacy_dp/tests/`](../backend/privacy_dp/tests/) marked `@pytest.mark.dp`.

### 7.3 Utility validation

DP introduces noise → check utility:
- DKT AUC with DP vs without: target degradation < 5%
- Cohort analytics: compare DP-protected stats with true (in test env), error within tolerance
- Federated convergence: model converge within 1.5x rounds vs centralized

## 8. Configuration

```python
# backend/palp/settings/base.py
PALP_DP = {
    "EPSILON_BUDGET_PER_RUN": float(os.environ.get("PALP_DP_EPSILON_PER_RUN", 1.0)),
    "EPSILON_BUDGET_PER_STUDENT_YEAR": float(os.environ.get("PALP_DP_EPSILON_PER_YEAR", 5.0)),
    "DELTA": 1e-5,
    "NOISE_MULTIPLIER": 1.1,
    "MAX_GRAD_NORM": 1.0,
    "COHORT_MIN_SIZE_FOR_DP": 10,
}
```

## 9. Disclosure & transparency

In [`/(student)/preferences/privacy/page.tsx`](../frontend/src/app/(student)/preferences/privacy/page.tsx) section "Differential Privacy":

> "PALP dùng Differential Privacy để bảo vệ data của bạn khi train model AI và xuất aggregated stats. Đây là chuẩn được Apple/Google/U.S. Census dùng. Cụ thể: chúng tôi thêm noise toán học vào output, đảm bảo không ai có thể infer data riêng của bạn từ kết quả. Năm nay bạn đã 'đóng góp' [X / 5.0] đơn vị privacy budget."

## 10. References

- [Dwork & Roth 2014 "The Algorithmic Foundations of Differential Privacy"](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- [Abadi et al. 2016 "Deep Learning with Differential Privacy"](https://arxiv.org/abs/1607.00133) (DP-SGD foundation)
- [Opacus library](https://github.com/pytorch/opacus)
- [Flower framework](https://flower.dev/)
- [Apple's DP whitepaper](https://www.apple.com/privacy/docs/Differential_Privacy_Overview.pdf)

## 11. Skills + related docs

- [PRIVACY_V2_DPIA.md](PRIVACY_V2_DPIA.md) — DPIA cho ml_research_participation, dkt_personalization
- [dkt-engine skill](../.ruler/skills/dkt-engine/SKILL.md) — DKT training với DP
- [causal-experiment skill](../.ruler/skills/causal-experiment/SKILL.md) — DP-protected experiment outputs

## 12. Living document

Update khi:
- New DP technique published (e.g., shuffling DP, local DP variants)
- Vendor library update (Opacus, Flower)
- Empirical validation reveals utility gap → tune ε
- Regulator update (NĐ 13/2023 amendments specifying noise requirements)
