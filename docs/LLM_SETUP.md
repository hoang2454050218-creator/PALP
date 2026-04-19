# PALP — AI Coach LLM Setup

This guide walks through wiring real cloud + local LLMs into the AI
Coach (Phase 4 of the v3 MAXIMAL roadmap). The system ships with
safe defaults (`EchoClient`) so it works out of the box with no key;
this guide explains how to upgrade.

## Architecture in 60 seconds

```
                 ┌──────────────────────────────┐
 Sinh viên gõ ──▶│   coach/services.py           │
                 │   9-layer defense pipeline    │
                 └──────────────┬───────────────┘
                                │
                ┌───────────────▼───────────────┐
                │ coach/llm/router.py            │
                │  intent + consent + budget     │
                └────┬───────────────────────┬───┘
                     │ sensitive intent      │ default
                     ▼                       ▼
       ┌────────────────────┐   ┌────────────────────────────┐
       │ OllamaClient       │   │ OpenAICompatClient         │
       │ (local, no key)    │   │ (OpenAI / key4u / OpenRouter)│
       └────────────────────┘   └────────────────────────────┘
```

Two key safety properties:

1. **Sensitive intents stay local.** Frustration / wellbeing /
   self-harm signals are routed to Ollama so PII never leaves your
   infra — even if the cloud LLM is configured.
2. **Cloud is opt-in.** The student must consent to `ai_coach_cloud`
   in the privacy panel before any non-sensitive message is sent
   to the cloud provider. Without consent, everything goes local.

## Step 1 — Pick your cloud provider

The `OpenAICompatClient` works with **any OpenAI Chat Completions
compatible endpoint**. Pick whichever fits your situation:

| Provider | When to choose | `BASE_URL` | Model examples |
|---|---|---|---|
| **OpenAI direct** | English-first, big budget, want latest GPT | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini`, `gpt-5` |
| **key4u.shop** (VN) | Vietnamese aggregator, đa model qua 1 key, thanh toán VND | `https://api.key4u.shop/v1` | `claude-sonnet-4-6`, `claude-opus-4-20250514`, `gpt-5.4-xhigh`, `gemini-2.5-pro` |
| **OpenRouter** | One key for 100+ models, transparent routing | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4.5`, `openai/gpt-4o` |
| **Anthropic direct** *(via OpenRouter — Anthropic's own SDK is not installed by default)* | Best Claude support outside aggregators | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4.5` |

Recommended for PALP (Vietnamese students, education domain):
**Claude Sonnet 4.5 / 4.6** via either OpenRouter or key4u.shop.

## Step 2 — Generate the API key safely

> ⚠️ **NEVER paste your API key into chat, screenshots, git commits,
> Slack messages, or screen shares.** Bots scrape these channels for
> keys 24/7. If you accidentally expose a key, **rotate it
> immediately** — most providers let you revoke + regenerate in <1
> minute.

1. Go to your provider's dashboard:
   - OpenAI: <https://platform.openai.com/api-keys>
   - key4u.shop: <https://key4u.shop/token>
   - OpenRouter: <https://openrouter.ai/keys>
2. Create a new key. Name it `palp-prod-coach` so you can rotate it
   independently from other projects.
3. Copy the key into your **OS clipboard** — do not paste it
   anywhere else.

## Step 3 — Drop the key into `.env`

Create `backend/.env` (this file is `.gitignore`-d) with at minimum:

```bash
# --- Cloud LLM ---
PALP_COACH_CLOUD_PROVIDER=openai_compat
OPENAI_COMPAT_API_KEY=sk-your-real-key-here
OPENAI_COMPAT_BASE_URL=https://api.key4u.shop/v1   # or openai/openrouter
OPENAI_COMPAT_MODEL=claude-sonnet-4-6              # or gpt-4o-mini, etc.

# --- Local LLM (PII-sensitive intents) ---
PALP_COACH_LOCAL_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

Full list of supported env vars lives in `.env.example` at the
repository root.

## Step 4 — Install Ollama (local LLM, free)

Ollama runs the local model that handles sensitive intents. It is
free and stays entirely on your machine.

### macOS / Windows

1. Download installer from <https://ollama.com/download>
2. Run it; the daemon starts automatically on `http://localhost:11434`

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable --now ollama
```

### Docker (server deployment)

```yaml
# docker-compose.yml additive snippet
services:
  ollama:
    image: ollama/ollama:latest
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

### Pull a model

```bash
# Best Vietnamese support in the 7B class (~4.7 GB)
ollama pull qwen2.5:7b

# Smaller / faster, weaker Vietnamese (~2 GB)
ollama pull llama3.2:3b
```

Confirm it works:

```bash
ollama run qwen2.5:7b "Chào bạn, hôm nay tôi cảm thấy mệt"
```

## Step 5 — Restart Django + verify

```bash
# Restart so the new env vars are picked up
cd backend
python manage.py runserver 0.0.0.0:8001
```

Health check the LLM via the management shell:

```bash
python manage.py shell
```

```python
from coach.llm.client import get_default_client
from coach.llm.client import LLMRequest

client = get_default_client()
print("provider:", client.provider, "model:", client.model)

resp = client.generate(LLMRequest(
    system_prompt="Bạn là PALP Coach.",
    user_message="Giải thích định luật Hooke ngắn gọn",
    intent="explain_concept", user_id=1,
))
print(resp.text)
```

Expected output: a real Vietnamese explanation from your chosen
cloud model.

## Step 6 — End-to-end smoke test in the browser

1. Log in as a student
2. Navigate to **Quyền riêng tư**, scroll to the consent list, and
   grant **"Trợ lý AI bên ngoài (Cloud LLM)"**
3. Navigate to **AI Coach**, send a message like
   "Giải thích cho mình ứng suất chính"
4. The reply now comes from your real cloud LLM, not the Echo
   template
5. Try a sensitive message ("mình bực quá, bỏ cuộc") — the router
   forces the local Ollama path even with cloud consent on

## Operations

### Cost monitoring

```bash
python manage.py shell -c "
from coach.models import CoachAuditLog
from django.db.models import Sum
totals = CoachAuditLog.objects.values('llm_provider').annotate(
    tokens_in=Sum('tokens_in'), tokens_out=Sum('tokens_out'),
)
for row in totals: print(row)
"
```

### Rotating the key (zero-downtime)

1. Generate a new key in the provider dashboard
2. Edit `.env` → replace `OPENAI_COMPAT_API_KEY`
3. Restart the Django process (`systemctl restart palp` or container
   restart). The factory reads the env on each instantiation, so the
   first request after restart picks up the new key.
4. **After verifying the new key works, revoke the old one** in the
   provider dashboard.

### Disabling LLM in an emergency

Set in `.env` and restart:

```bash
PALP_COACH_CLOUD_PROVIDER=echo
PALP_COACH_LOCAL_PROVIDER=echo
```

The coach now answers with safe deterministic templates only — no
network calls — until you restore the real provider.

## Failure modes that are handled automatically

| Symptom | What the system does |
|---|---|
| Empty `OPENAI_COMPAT_API_KEY` | Factory raises → router downgrades to `EchoClient` silently |
| Provider 401 / 5xx mid-request | `coach/services.py` catches `LLMTransportError`, retries once with `EchoClient`, marks `safety_flags: [{"kind": "llm_upstream_failed"}]` |
| Ollama daemon not running | Same fallback as above; logs a warning |
| Daily token budget exceeded | Router routes to local Ollama silently for the rest of the day |
| Sensitive intent (frustration / self-harm) | Router routes to local Ollama regardless of cloud consent |

## See also

- `backend/coach/llm/openai_compat.py` — cloud client implementation
- `backend/coach/llm/ollama_client.py` — local client implementation
- `backend/coach/llm/router.py` — routing decision tree
- `backend/coach/services.py` — full 9-layer defense pipeline
- `.env.example` — full env var reference
