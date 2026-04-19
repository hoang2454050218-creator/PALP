---
name: coach-safety
description: Coach AI safety — 9-layer defense, prompt injection, jailbreak, PII guard, hallucination check, refusal patterns, canary tokens, watermark. Use when modifying backend/coach/llm/, system prompts, tool registry, or safety guardrails.
---

# Coach Safety — 9-Layer Defense Workflow

## When to use

- Editing `backend/coach/llm/` (router, security, pii_guard, tool_registry, safety, prompts)
- Modifying `CoachPrompt` records (system prompts)
- Adding new function-calling tool
- Tuning thresholds (jailbreak classifier, hallucination, token budget)
- Reviewing finding from [RED_TEAM_PLAYBOOK.md](../../../docs/RED_TEAM_PLAYBOOK.md)
- Implementing new refusal pattern

## Hard invariants

1. **All 9 defense layers active** in every coach call (per [COACH_SAFETY_PLAYBOOK.md](../../../docs/COACH_SAFETY_PLAYBOOK.md) section 2)
2. **Tool whitelist enforced** — no write tools, ever. RBAC on read tools.
3. **PII Guard mandatory** before any cloud LLM call. Restore after.
4. **Canary tokens in every system prompt**. Check leak before sending response.
5. **Token budget per user/day**. Fallback to local LLM when exceeded.
6. **Audit log every LLM call** with token count, provider, model, intent, safety flags.
7. **Emergency detection runs PARALLEL** with normal flow. Override response if triggered.
8. **Refusal patterns over LLM-generated** for: dishonesty, PII other students, medical/legal/financial advice, self-harm.
9. **Templates over LLM** for emergency/critical responses — don't trust LLM in crisis.

## Layer-by-layer reference

| Layer | Purpose | File |
|---|---|---|
| 1 | Prompt injection scanner | `backend/coach/llm/security.py::scan_prompt_injection` |
| 2 | Jailbreak classifier (DistilBERT) | `backend/coach/llm/jailbreak_classifier.py` |
| 3 | PII Guard (mask before send) | `backend/coach/llm/pii_guard.py::mask` |
| 4 | Intent router (sensitive → local) | `backend/coach/llm/router.py::route_llm` |
| 5 | Output validator + canary check | `backend/coach/llm/security.py::validate_output` |
| 6 | Hallucination check vs tool results | `backend/coach/llm/security.py::check_hallucination` |
| 7 | Safety filter (refusal patterns) | `backend/coach/safety.py::apply_refusal` |
| 8 | Watermark inject | `backend/coach/llm/security.py::inject_watermark` |
| 9 | PII restore (token → real) | `backend/coach/llm/pii_guard.py::restore` |

## Workflow when adding feature

### 1. Define intent

Add intent label to `INTENT_LABELS` in `backend/coach/intent_classifier.py`. Decide if sensitive (route to local) or not.

### 2. Add system prompt template

In `CoachPrompt` model, version-controlled:

```python
CoachPrompt.objects.create(
    intent="explain_concept",
    system_prompt_template="""Bạn là PALP Coach, trợ lý học tập...
    
    Trong response của bạn, bạn được phép:
    - Giải thích concept dùng ví dụ và analogy
    - Dùng tool get_mastery, get_pathway để xem context student
    
    Bạn KHÔNG được:
    - Viết bài thay student
    - Tiết lộ thông tin của student khác
    - Đưa ra lời khuyên y tế/pháp lý/tài chính
    
    [INTERNAL_TOKEN={canary}]""",
    version="1.0.0",
    active=True,
)
```

Canary placeholder injected at runtime per request.

### 3. Implement orchestration

```python
# backend/coach/services.py
async def generate_response(message, user, conversation):
    request_id = generate_request_id()
    
    # Parallel emergency detection
    emergency_task = asyncio.create_task(emergency_detector.detect(message, user))
    
    # Layer 1: prompt injection scan
    inj_result = scan_prompt_injection(message)
    if inj_result.severity == "blocked":
        return refusal_response("blocked_injection")
    if inj_result.severity == "suspicious":
        message = strip_suspicious_tokens(message, inj_result)
    
    # Layer 2: jailbreak classifier
    jb_result = jailbreak_classifier.classify(message)
    if jb_result["is_jailbreak"]:
        await record_jailbreak_attempt(user)
        return refusal_response("jailbreak_attempt")
    
    # Detect intent
    intent = intent_classifier.classify(message)
    
    # Check emergency (don't await yet, but check ready)
    emergency = await emergency_task  # at this point, parallel detection done
    if emergency.should_escalate:
        return await emergency_response(message, user, emergency)
    
    # Layer 4: route LLM
    llm_client = route_llm(intent, {"user_id": user.id})
    
    # Layer 3: PII Guard mask (only if cloud)
    mapping = {}
    if isinstance(llm_client, CloudLLMClient):
        message_for_llm, mapping = pii_guard.mask(message)
    else:
        message_for_llm = message
    
    # Build system prompt with canary
    canary = secrets.token_hex(8)
    canary_store[request_id] = canary
    system_prompt = build_system_prompt(intent, canary)
    
    # Tool calling with read-only registry
    response = await llm_client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message_for_llm},
        ],
        tools=TOOL_REGISTRY.openai_format(),
        user=user,
    )
    
    # Process tool calls (validate args, RBAC)
    tool_results = await execute_tools(response.tool_calls, user)
    
    # Final response with tool results
    final_response = await llm_client.chat(
        messages=[..., {"role": "tool", "content": tool_results}],
    )
    
    response_text = final_response.content
    
    # Layer 5: output validator + canary check
    if not check_canary_leak(response_text, request_id):
        logger.critical("Canary leak", extra={"request_id": request_id})
        return refusal_response("canary_leak")
    
    # Layer 6: hallucination check
    halluc = check_hallucination(response_text, tool_results)
    if not halluc["clean"]:
        return regenerate_with_stricter_prompt(message, halluc)
    
    # Layer 7: safety filter
    response_text = apply_refusal(response_text, intent)
    
    # Layer 8: watermark
    response_text = inject_watermark(response_text, llm_client.model_name, time.time())
    
    # Layer 9: PII restore
    if mapping:
        response_text = pii_guard.restore(response_text, mapping)
    
    # Audit log
    CoachAuditLog.objects.create(
        request_id=request_id,
        conversation_id=conversation.id,
        intent=intent,
        llm_provider=llm_client.provider,
        llm_model=llm_client.model_name,
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
        latency_ms=response.latency_ms,
        tools_called=[t.name for t in response.tool_calls],
        safety_flags={
            "injection": inj_result.severity,
            "jailbreak": jb_result,
            "hallucination": halluc,
            "pii_tokens_count": len(mapping),
            "canary_passed": True,
        },
    )
    
    return response_text
```

### 4. Test new feature

Per [RED_TEAM_PLAYBOOK.md](../../../docs/RED_TEAM_PLAYBOOK.md):
- Run prompt injection probes against new intent
- Run jailbreak corpus
- Test hallucination on factual claims
- Verify tool whitelist holds
- Verify canary detection
- Verify token budget honored

## Adding new tool

```python
# backend/coach/llm/tool_registry.py
TOOLS = {
    "get_mastery": {
        "description": "Get student's current mastery for given course",
        "arg_schema": {
            "type": "object",
            "properties": {
                "course_id": {"type": "integer"},
            },
            "required": ["course_id"],
        },
        "handler": "backend.coach.tools.get_mastery_handler",
        "requires_consent": [],  # public to user
        "rbac": "own_only",  # student can only query own data
    },
    # ...
}
```

Rule: **NEVER** add write tools. Coach is read-only adviser. Lecturer/Admin handle write actions.

## Refusal templates (NOT LLM-generated)

Per [COACH_SAFETY_PLAYBOOK.md](../../../docs/COACH_SAFETY_PLAYBOOK.md) section 7.4:

```python
REFUSAL_TEMPLATES = {
    "academic_dishonesty": "Mình không thể viết bài thay bạn — đó không tôn trọng việc học của bạn. Nhưng mình có thể giúp brainstorm outline, review draft, hoặc giải thích concept. Bạn muốn cách nào?",
    "other_student_pii": "Mình không chia sẻ thông tin của bạn khác. Mỗi sinh viên có privacy riêng. Mình có thể giúp gì khác?",
    "medical_advice": "Đây không phải lĩnh vực mình có thể tư vấn an toàn. Hãy tham vấn bác sĩ. Trong khi đó, mình giúp việc học nhé?",
    "legal_advice": "Đây cần luật sư tư vấn, không phải mình. Việc học mình giúp được nhé?",
    "self_harm": None,  # NEVER use template; trigger emergency pipeline
    "blocked_injection": "Câu hỏi của bạn có vài điểm mình không xử lý được. Bạn có thể hỏi lại theo cách khác không?",
    "jailbreak_attempt": "Mình không trả lời theo cách bạn yêu cầu được. Mình ở đây để hỗ trợ học. Bạn cần giúp gì?",
    "canary_leak": "Mình không thể trả lời câu này. Hãy thử câu khác.",
}
```

## Emergency override

If `emergency_detector.detect()` returns severity high/critical, **don't** generate via LLM. Use template + trigger pipeline:

```python
def emergency_response(message, user, detection):
    # Create incident
    incident = EmergencyEvent.objects.create(
        student=user,
        severity=detection.severity,
        trigger_type=detection.trigger_type,
        encrypted_evidence=encrypt(message),
    )
    
    # Enqueue counselor
    enqueue_counselor(incident)
    
    # Return template (NOT LLM-generated)
    return EMERGENCY_RESPONSE_TEMPLATE.format(
        emergency_contact_name=user.emergency_contact.name if user.emergency_contact else "[chưa đăng ký]",
    )
```

Per [EMERGENCY_RESPONSE_TRAINING.md](../../../docs/EMERGENCY_RESPONSE_TRAINING.md).

## Common pitfalls

- **Skipping a layer**: defense-in-depth requires all 9. Don't optimize away "for performance".
- **Logging unmasked text**: PII leak in logs. Audit log only metadata.
- **Tool with state**: tools must be read-only. State changes via dashboard, not coach.
- **Prompt drift**: tweaking system prompt without versioning. Use `CoachPrompt` model.
- **Trust LLM in crisis**: emergency response must be template. LLM for non-critical only.
- **Missing canary**: leak undetectable. Inject canary in every system prompt.
- **No token budget**: cost spike from adversarial usage.
- **Forgetting to update Model Card**: when adding intent, refusal, or tool

## Quarterly review

Per [RED_TEAM_PLAYBOOK.md](../../../docs/RED_TEAM_PLAYBOOK.md):
- Run full attack suite
- Update jailbreak classifier training data with new attacks
- Review refusal templates for new edge cases
- Audit `CoachAuditLog` for anomalies (high tool call rate, refusal rate spike)

## Related

- [COACH_SAFETY_PLAYBOOK.md](../../../docs/COACH_SAFETY_PLAYBOOK.md) — full reference
- [RED_TEAM_PLAYBOOK.md](../../../docs/RED_TEAM_PLAYBOOK.md) — testing
- [EMERGENCY_RESPONSE_TRAINING.md](../../../docs/EMERGENCY_RESPONSE_TRAINING.md) — emergency override
- [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) sections 3.7, 3.8 — coach consent
- [llm-routing skill](../llm-routing/SKILL.md)
- [emergency-response skill](../emergency-response/SKILL.md)
