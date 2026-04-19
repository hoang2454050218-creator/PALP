---
name: affect-analysis
description: Multi-modal affect detection — keystroke dynamics + linguistic sentiment + facial (on-device only). 3-tier consent. Use when modifying backend/affect/ or frontend affect SDK.
---

# Affect Analysis — Keystroke + Linguistic + Facial (3-Tier)

## When to use

- Editing `backend/affect/` (keystroke_analyzer, sentiment, facial_meta, fusion)
- Editing `frontend/src/lib/sensing/keystroke-tracker.ts`
- Editing `frontend/src/lib/affect/facial-mediapipe.ts` (on-device only)
- Adjusting affect signal weights in RiskScore
- Adding new affect tier
- Reviewing PR touching affect code (extra privacy review required)

## Hard invariants

1. **3-tier consent independent**: `affect_keystroke`, `affect_linguistic`, `affect_facial`. Each opt-in separately. None default ON.
2. **Facial on-device only**: MediaPipe Face Landmarker runs IN BROWSER. Server receives ONLY 2 scalars (valence, arousal) + `on_device_processed: true` flag. Server REJECTS event if flag missing.
3. **No raw biometric transmission**: no video, no landmarks, no key timestamps individually. Aggregated stats only.
4. **Linguistic local model**: PhoBERT/VinAI for VN sentiment. NEVER cloud LLM for affect (PII sensitive).
5. **Affect signal in RiskScore behavioral dimension**: weighted modestly (don't dominate RiskScore from affect).
6. **Fairness audit per release**: affect detector subject to per [fairness-audit skill](../fairness-audit/SKILL.md). Risk: cultural bias in affect models.
7. **Sampling for high-volume**: keystroke 0.1, facial 0.05.
8. **Easy-off**: settings page with prominent toggle per tier.

## App structure

```
backend/affect/
├── models.py             # KeystrokeRhythm, LinguisticAffect, FacialAffectMeta, AffectSignal
├── keystroke_analyzer.py # Aggregate stats from frontend windows
├── sentiment.py          # PhoBERT inference on CoachTurn
├── facial_meta.py        # Receive scalar from frontend (with validation)
├── fusion.py             # Multi-modal late fusion → AffectSignal
├── consent_tiers.py      # 3-tier consent enforcement
├── views.py              # /api/affect/ingest/ (keystroke, facial), /sentiment/
└── tests/
```

```
frontend/src/lib/sensing/
└── keystroke-tracker.ts  # Aggregated stats only
frontend/src/lib/affect/
└── facial-mediapipe.ts   # On-device, scalar transmission only
```

## Tier 1: Keystroke dynamics

```typescript
// frontend/src/lib/sensing/keystroke-tracker.ts
import { hasConsent } from "@/lib/privacy/consent";

class KeystrokeTracker {
  private windowSeconds = 60;
  private windowStart: number = 0;
  private dwellTimes: number[] = [];
  private flightTimes: number[] = [];
  private keyDownTime: Record<string, number> = {};
  private lastKeyUp: number = 0;
  
  start() {
    if (!hasConsent("affect_keystroke")) return;
    
    this.windowStart = Date.now();
    document.addEventListener("keydown", this.onKeyDown);
    document.addEventListener("keyup", this.onKeyUp);
    setInterval(() => this.flush(), this.windowSeconds * 1000);
  }
  
  private onKeyDown = (e: KeyboardEvent) => {
    this.keyDownTime[e.code] = Date.now();
    if (this.lastKeyUp > 0) {
      this.flightTimes.push(Date.now() - this.lastKeyUp);
    }
  };
  
  private onKeyUp = (e: KeyboardEvent) => {
    const downTime = this.keyDownTime[e.code];
    if (downTime) {
      this.dwellTimes.push(Date.now() - downTime);
      delete this.keyDownTime[e.code];
    }
    this.lastKeyUp = Date.now();
  };
  
  private flush() {
    if (this.dwellTimes.length === 0) return;
    
    // SEND ONLY AGGREGATES — no individual key events
    const aggregates = {
      window_seconds: this.windowSeconds,
      dwell_time_avg_ms: avg(this.dwellTimes),
      flight_time_avg_ms: avg(this.flightTimes),
      speed_wpm: this.dwellTimes.length / 5 / (this.windowSeconds / 60),
      rhythm_variance: variance(this.dwellTimes),
    };
    
    ingestBuffer.push("affect_keystroke_window", aggregates);
    
    this.dwellTimes = [];
    this.flightTimes = [];
  }
}
```

Backend:

```python
# backend/affect/keystroke_analyzer.py
def process_keystroke_window(user, window_data):
    """Process aggregated keystroke window into KeystrokeRhythm record."""
    KeystrokeRhythm.objects.create(
        student=user,
        window_seconds=window_data["window_seconds"],
        dwell_time_avg_ms=window_data["dwell_time_avg_ms"],
        flight_time_avg_ms=window_data["flight_time_avg_ms"],
        speed_wpm=window_data["speed_wpm"],
        rhythm_variance=window_data["rhythm_variance"],
    )
    
    # Cognitive load proxy: high variance + slow speed → confusion/load
    cognitive_load_proxy = compute_cognitive_load_from_keystroke(window_data)
    push_to_feature_store(user, {"keystroke_cognitive_load": cognitive_load_proxy})
```

## Tier 2: Linguistic sentiment

```python
# backend/affect/sentiment.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class VietnameseSentimentAnalyzer:
    def __init__(self):
        # PhoBERT-base-VinAI fine-tuned for sentiment
        self.tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base")
        self.model = AutoModelForSequenceClassification.from_pretrained("models/sentiment_vn_v1")
    
    def analyze(self, text: str) -> dict:
        """Local model, never cloud LLM for sentiment.
        
        Returns valence (-1 to 1) and arousal (0 to 1).
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        logits = outputs.logits.softmax(dim=-1).flatten()
        # Map to valence/arousal
        valence = (logits[1] - logits[0]).item()  # positive - negative
        arousal = logits[2].item() if len(logits) > 2 else 0.5  # if model has arousal head
        
        return {"valence": valence, "arousal": arousal, "model_version": "v1"}

@shared_task
def process_coach_turn_sentiment(coach_turn_id):
    """Analyze sentiment after CoachTurn created."""
    turn = CoachTurn.objects.get(pk=coach_turn_id)
    user = turn.conversation.student
    
    if not has_consent(user, "affect_linguistic"):
        return
    
    analyzer = VietnameseSentimentAnalyzer()
    result = analyzer.analyze(turn.content)
    
    LinguisticAffect.objects.create(
        student=user,
        coach_turn=turn,
        valence=result["valence"],
        arousal=result["arousal"],
        model_version=result["model_version"],
    )
```

## Tier 3: Facial (on-device only)

```typescript
// frontend/src/lib/affect/facial-mediapipe.ts
import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import { hasConsent } from "@/lib/privacy/consent";

class FacialAffectTracker {
  private landmarker: FaceLandmarker | null = null;
  private windowSeconds = 30;
  private valences: number[] = [];
  private arousals: number[] = [];
  
  async start() {
    if (!hasConsent("affect_facial")) return;
    
    // Request camera permission
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    
    // Initialize MediaPipe LOCALLY in browser
    const vision = await FilesetResolver.forVisionTasks(...);
    this.landmarker = await FaceLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "/models/face_landmarker.task",
      },
      outputFaceBlendshapes: true,
    });
    
    // Process frame loop — NEVER send video out
    this.processFrames(stream);
    
    setInterval(() => this.flush(), this.windowSeconds * 1000);
  }
  
  private async processFrames(stream: MediaStream) {
    const video = document.createElement("video");
    video.srcObject = stream;
    
    while (true) {
      const result = this.landmarker.detectForVideo(video, performance.now());
      
      // Compute valence/arousal LOCALLY from blendshapes
      const { valence, arousal } = this.computeFromBlendshapes(result.faceBlendshapes);
      this.valences.push(valence);
      this.arousals.push(arousal);
      
      await new Promise((r) => setTimeout(r, 1000)); // 1 fps sample
    }
  }
  
  private flush() {
    if (this.valences.length === 0) return;
    
    // SEND ONLY 2 SCALARS — never frames, never landmarks
    ingestBuffer.push("affect_facial_window", {
      window_seconds: this.windowSeconds,
      valence: avg(this.valences),
      arousal: avg(this.arousals),
      on_device_processed: true,  // MUST set, server validates
    });
    
    this.valences = [];
    this.arousals = [];
  }
}
```

Backend STRICT validation:

```python
# backend/affect/facial_meta.py
def ingest_facial_window(user, data):
    """Validate that processing happened on-device. Reject otherwise."""
    
    if data.get("on_device_processed") is not True:
        raise ValidationError("Facial affect must be processed on-device. Server rejects raw transmission.")
    
    if "valence" not in data or "arousal" not in data:
        raise ValidationError("Missing scalar values.")
    
    if not (-1 <= data["valence"] <= 1):
        raise ValidationError("Valence out of range.")
    
    FacialAffectMeta.objects.create(
        student=user,
        window_seconds=data["window_seconds"],
        valence=data["valence"],
        arousal=data["arousal"],
    )
```

## Multi-modal fusion

```python
# backend/affect/fusion.py
def compute_affect_signal(student, window_minutes=5):
    """Late fusion of available modalities (per consent)."""
    signals = []
    
    if has_consent(student, "affect_keystroke"):
        ks = recent_keystroke(student, window_minutes)
        if ks:
            signals.append(("keystroke", ks_to_valence_arousal(ks)))
    
    if has_consent(student, "affect_linguistic"):
        ling = recent_linguistic(student, window_minutes)
        if ling:
            signals.append(("linguistic", (ling.valence, ling.arousal)))
    
    if has_consent(student, "affect_facial"):
        fac = recent_facial(student, window_minutes)
        if fac:
            signals.append(("facial", (fac.valence, fac.arousal)))
    
    if not signals:
        return None
    
    # Late fusion — weighted average, weights tunable
    weights = settings.PALP_AFFECT.get("FUSION_WEIGHTS", {"keystroke": 0.3, "linguistic": 0.4, "facial": 0.3})
    
    total_w = sum(weights[mod] for mod, _ in signals)
    valence_fused = sum(weights[mod] * v for mod, (v, a) in signals) / total_w
    arousal_fused = sum(weights[mod] * a for mod, (v, a) in signals) / total_w
    
    return AffectSignal.objects.create(
        student=student,
        valence=valence_fused,
        arousal=arousal_fused,
        modalities=[mod for mod, _ in signals],
    )
```

## Integration with RiskScore

```python
# backend/risk/scoring.py
def _stress_signals(student):
    """Used in psychological dimension."""
    affect = recent_affect_signal(student)
    if affect is None:
        return 0.0  # missing data → not increasing risk
    
    # Negative valence + high arousal = stress
    if affect.valence < -0.3 and affect.arousal > 0.6:
        return min(1.0, abs(affect.valence) * affect.arousal * 1.5)
    
    return 0.0
```

## Common pitfalls

- **Sending raw biometric**: catastrophic privacy breach. Server validation must reject.
- **Skipping consent check on each tier**: independent opt-in required.
- **Using cloud LLM for sentiment**: PII leak.
- **Missing model version field**: hard to debug + retrain
- **Affect dominates RiskScore**: should be 1 of 5 dimensions, not main signal
- **Cultural bias in models**: affect detection trained on Western data may miss VN expressions. Fairness audit critical.
- **Dropped frames not handled**: facial tracker should gracefully degrade
- **No easy-off**: hard to disable → bad UX, privacy concern

## Performance budget

- Keystroke window: <50ms server-side processing
- Sentiment per CoachTurn: <500ms (PhoBERT-base local)
- Facial scalar processing on-device: <30ms per frame at 1fps
- Fusion: <100ms

## Test coverage

- Tier consent independence: opt-in 1 doesn't enable others
- Server reject if `on_device_processed: false` for facial
- No raw video/landmarks in any HTTP request (assert never serializes)
- Sentiment uses local model (mock cloud → assert not called)
- Fairness: subgroup affect accuracy (per [fairness-audit skill](../fairness-audit/SKILL.md))
- Edge case: no consent → no signal in RiskScore

## Related

- [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) sections 3.11-3.13 — 3-tier affect consent
- [SIGNAL_TAXONOMY.md](../../../docs/SIGNAL_TAXONOMY.md) section 7 — affect events
- [LEARNING_SCIENCE_FOUNDATIONS.md](../../../docs/LEARNING_SCIENCE_FOUNDATIONS.md) section 2.10 — affective computing theory
- [risk-scoring skill](../risk-scoring/SKILL.md) — RiskScore consumer
- [fairness-audit skill](../fairness-audit/SKILL.md)
- [signals-pipeline skill](../signals-pipeline/SKILL.md) — keystroke shares ingest infra
- [MediaPipe Face Landmarker](https://developers.google.com/mediapipe/solutions/vision/face_landmarker)
- [VinAI PhoBERT](https://github.com/VinAIResearch/PhoBERT)
