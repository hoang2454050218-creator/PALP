---
name: llm-routing
description: Cloud vs Local LLM routing — sensitive intents force local LLM, PII Guard before cloud. Use when modifying intent detection, router rules, or adding new intent.
---

# LLM Routing — Cloud vs Local Decision

## When to use

- Editing `backend/coach/llm/router.py`
- Adding new intent to `INTENT_LABELS`
- Adjusting `SENSITIVE_INTENTS` set
- Tuning intent classifier
- Reviewing PR touching routing logic
- Investigating "why did coach use cloud for this?" question

## Hard invariants

1. **Sensitive intents force local LLM** — no exception, no override even with explicit user consent for cloud.
2. **No-consent forces local** — if user lacks `ai_coach_cloud` consent, route to local.
3. **Budget exceeded forces local** — silent fallback when cloud token budget hit.
4. **Emergency detection short-circuits** — overrides routing decision, takes emergency path.
5. **Multi-intent message routes to most sensitive** intent.
6. **Routing decision logged** in `CoachAuditLog.llm_provider` field.

## Sensitive intents (forced local)

```python
# backend/coach/llm/router.py
SENSITIVE_INTENTS = {
    # Mental health / emotional
    "frustration",
    "give_up",
    "stress",
    "wellbeing",
    "mental_health",
    "personal_struggle",
    "family",
    "relationships",
    
    # Crisis (also triggers emergency pipeline)
    "self_harm",
    "suicidal_ideation",
    "severe_distress",
    
    # Identity / sensitive personal topics
    "gender_identity",
    "sexual_orientation",
    "religious",
    "political_personal",
    "trauma",
}
```

When in doubt about new intent, default to sensitive (err on caution).

## Routing logic

```python
# backend/coach/llm/router.py
from typing import Union
from .cloud_client import CloudLLMClient
from .local_client import LocalLLMClient

def route_llm(intent: str, payload: dict) -> Union[CloudLLMClient, LocalLLMClient]:
    """Decide cloud vs local based on intent sensitivity, consent, budget.
    
    Order of checks (return immediately on first applicable):
    1. Emergency intent → local + emergency pipeline (caller handles)
    2. Sensitive intent → local
    3. No cloud consent → local
    4. Budget exceeded → local (silent fallback)
    5. Default → cloud
    """
    user_id = payload["user_id"]
    
    # 1. Sensitive intent
    if intent in SENSITIVE_INTENTS:
        return LocalLLMClient(model=settings.PALP_COACH["LOCAL_MODEL"])
    
    # 2. Consent check
    if not has_consent(user_id, "ai_coach_cloud"):
        return LocalLLMClient(model=settings.PALP_COACH["LOCAL_MODEL"])
    
    # 3. Token budget
    if budget_exceeded(user_id, period="day"):
        return LocalLLMClient(model=settings.PALP_COACH["LOCAL_MODEL"])
    
    # 4. Default cloud
    return CloudLLMClient(
        provider=settings.PALP_COACH["CLOUD_PROVIDER"],
        model=settings.PALP_COACH["CLOUD_MODEL"],
    )
```

## Intent detection

```python
# backend/coach/intent_classifier.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class IntentClassifier:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("models/intent_v1")
        self.model = AutoModelForSequenceClassification.from_pretrained("models/intent_v1")
    
    def classify(self, text: str) -> str:
        """Return single most-likely intent label."""
        intents = self.classify_multi(text)
        if not intents:
            return "general"
        # Most-sensitive-wins
        for intent_label, score in intents:
            if intent_label in SENSITIVE_INTENTS and score > 0.3:
                return intent_label  # short-circuit on sensitive
        return intents[0][0]
    
    def classify_multi(self, text: str) -> list[tuple[str, float]]:
        """Return ranked intents above threshold 0.2."""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        outputs = self.model(**inputs)
        probs = outputs.logits.softmax(dim=-1).flatten()
        labels = self.model.config.id2label
        result = [(labels[i], probs[i].item()) for i in range(len(labels))]
        return sorted([r for r in result if r[1] > 0.2], key=lambda x: -x[1])
```

Train intent classifier (DistilBERT or PhoBERT-base for VN) on hand-labeled examples. Re-train quarterly with audit log review.

## Adding new intent

1. Define intent name (snake_case)
2. Decide if sensitive — if any chance about feelings/identity/personal, default sensitive
3. Add to `INTENT_LABELS` in [`backend/coach/intent_classifier.py`](backend/coach/intent_classifier.py)
4. If sensitive, add to `SENSITIVE_INTENTS` in [`backend/coach/llm/router.py`](backend/coach/llm/router.py)
5. Create `CoachPrompt` system prompt template for this intent
6. Train intent classifier with new label (need ≥ 50 hand-labeled examples)
7. Add refusal template if applicable
8. Test routing decision matrix
9. Update [COACH_SAFETY_PLAYBOOK.md](../../../docs/COACH_SAFETY_PLAYBOOK.md) if new defense layer needed

## Cloud LLM client

```python
# backend/coach/llm/cloud_client.py
import anthropic
import openai

class CloudLLMClient:
    def __init__(self, provider="anthropic", model="claude-opus-4"):
        self.provider = provider
        self.model_name = model
        if provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        elif provider == "openai":
            self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    async def chat(self, messages, tools=None, user=None, max_tokens=2048):
        # Token budget check
        check_budget(user.id, max_tokens)
        
        # Vendor-specific call
        if self.provider == "anthropic":
            response = await self.client.messages.create(
                model=self.model_name,
                messages=messages,
                tools=tools or [],
                max_tokens=max_tokens,
                metadata={"user_id_hash": hash_user_id(user.id)},  # vendor abuse detection
            )
        # ...
        
        # Increment budget
        increment_budget(user.id, response.usage.input_tokens + response.usage.output_tokens)
        
        return response
```

Rule: providers must be configured to opt-out of training (Zero Data Retention with Anthropic Workspace, "no train" with OpenAI API).

## Local LLM client

```python
# backend/coach/llm/local_client.py
import httpx

class LocalLLMClient:
    def __init__(self, model="llama3:8b-instruct-q4_K_M"):
        self.provider = "ollama_local"
        self.model_name = model
        self.endpoint = settings.PALP_COACH["LOCAL_ENDPOINT"]
    
    async def chat(self, messages, tools=None, user=None, max_tokens=2048):
        # Local LLM doesn't count toward cloud budget but tracks GPU usage
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "tools": tools or [],
                    "options": {"num_predict": max_tokens},
                },
                timeout=60,
            )
        return parse_ollama_response(response.json())
```

For prod scale, switch to vLLM with continuous batching.

## Routing decision matrix

| Intent | User has cloud consent | Budget left | Routing decision |
|---|---|---|---|
| `explain_concept` | Yes | Yes | **Cloud** |
| `explain_concept` | Yes | No | Local (silent fallback) |
| `explain_concept` | No | (any) | Local |
| `homework_help` | Yes | Yes | **Cloud** |
| `summary_request` | Yes | Yes | **Cloud** |
| `frustration` | (any) | (any) | **Local** (forced) |
| `mental_health` | (any) | (any) | **Local** (forced) |
| `self_harm` | (any) | (any) | **Local + Emergency Pipeline** |
| `general` (unknown) | Yes | Yes | **Cloud** with fallback safety prompt |

## Common pitfalls

- **Routing sensitive to cloud "for quality"**: NEVER. Privacy is hard rule.
- **Forgetting budget check**: cost spike from adversarial usage
- **Hard-coding model names**: use `PALP_COACH` settings
- **Single intent assumption**: messages can multi-intent; route to most sensitive
- **Logging routing decision insufficiently**: hard to debug "why local?" without audit
- **Vendor opt-out forgotten**: training data leakage to vendor

## Test cases

```python
# backend/coach/tests/test_router.py
def test_sensitive_intent_forces_local(student_with_full_consent):
    client = route_llm("frustration", {"user_id": student_with_full_consent.id})
    assert isinstance(client, LocalLLMClient)

def test_no_cloud_consent_forces_local(student_with_local_only_consent):
    client = route_llm("explain_concept", {"user_id": student_with_local_only_consent.id})
    assert isinstance(client, LocalLLMClient)

def test_budget_exceeded_falls_back_local(student_with_full_consent):
    exhaust_budget(student_with_full_consent.id)
    client = route_llm("explain_concept", {"user_id": student_with_full_consent.id})
    assert isinstance(client, LocalLLMClient)

def test_default_cloud(student_with_full_consent):
    client = route_llm("explain_concept", {"user_id": student_with_full_consent.id})
    assert isinstance(client, CloudLLMClient)
```

## Related

- [coach-safety skill](../coach-safety/SKILL.md) — overall coach defenses
- [emergency-response skill](../emergency-response/SKILL.md) — emergency override
- [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) sections 3.7, 3.8 — cloud vs local consent
- [COACH_SAFETY_PLAYBOOK.md](../../../docs/COACH_SAFETY_PLAYBOOK.md) section 6 — Layer 4 routing
