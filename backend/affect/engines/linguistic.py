"""Light-weight linguistic affect estimator.

Two stages:

1. **Lexicon lookup** — small editable Vietnamese (and English)
   sentiment lexicon. We keep a hard-coded baseline so the engine
   has signal even when the DB is freshly migrated; admins can add
   rows in ``AffectLexiconEntry`` and the engine merges them.
2. **Heuristics** — exclamation/question marks, ALL CAPS ratio,
   negation handling within a small window.

Output is the same ``LinguisticSnapshot`` dataclass as keystroke,
so the upstream service can fuse them.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Mapping

_BASELINE_VI: tuple[tuple[str, str, float, float], ...] = (
    # term,                 polarity,   valence_w, arousal_w
    ("vui", "positive", 0.6, 0.2),
    ("vui vẻ", "positive", 0.7, 0.2),
    ("hạnh phúc", "positive", 0.8, 0.3),
    ("hứng thú", "positive", 0.6, 0.4),
    ("thích", "positive", 0.5, 0.2),
    ("yêu thích", "positive", 0.7, 0.3),
    ("tự tin", "positive", 0.6, 0.3),
    ("hiểu rồi", "positive", 0.4, 0.1),
    ("ổn", "positive", 0.3, 0.1),
    ("tốt", "positive", 0.4, 0.1),
    ("buồn", "negative", -0.6, 0.2),
    ("chán", "negative", -0.5, 0.1),
    ("nản", "negative", -0.7, 0.3),
    ("nản chí", "negative", -0.8, 0.3),
    ("bỏ cuộc", "negative", -0.9, 0.3),
    ("bực", "negative", -0.7, 0.6),
    ("bực mình", "negative", -0.8, 0.7),
    ("tức", "negative", -0.7, 0.7),
    ("ghét", "negative", -0.7, 0.4),
    ("khó hiểu", "negative", -0.5, 0.3),
    ("không hiểu", "negative", -0.5, 0.2),
    ("mệt", "negative", -0.6, 0.2),
    ("kiệt sức", "negative", -0.8, 0.4),
    ("căng thẳng", "negative", -0.6, 0.6),
    ("lo lắng", "negative", -0.6, 0.6),
    ("sợ", "negative", -0.6, 0.7),
)

_BASELINE_EN: tuple[tuple[str, str, float, float], ...] = (
    ("happy", "positive", 0.6, 0.2),
    ("excited", "positive", 0.7, 0.6),
    ("confident", "positive", 0.6, 0.3),
    ("good", "positive", 0.4, 0.1),
    ("great", "positive", 0.6, 0.3),
    ("ok", "positive", 0.2, 0.0),
    ("sad", "negative", -0.6, 0.2),
    ("angry", "negative", -0.7, 0.7),
    ("frustrated", "negative", -0.7, 0.6),
    ("tired", "negative", -0.5, 0.2),
    ("anxious", "negative", -0.6, 0.6),
    ("stressed", "negative", -0.7, 0.6),
    ("hate", "negative", -0.7, 0.5),
    ("confused", "negative", -0.4, 0.3),
    ("give up", "negative", -0.8, 0.3),
)

_NEGATIONS_VI = {"không", "chưa", "chẳng", "đâu có"}
_NEGATIONS_EN = {"not", "no", "never"}

_TOKEN_RE = re.compile(r"[\w']+|[!?]")


@dataclass
class LinguisticSnapshot:
    valence: float
    arousal: float
    confidence: float
    label: str
    features: dict = field(default_factory=dict)


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return text.lower().strip()


def _tokenise(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _baseline_lexicon(language: str) -> dict[str, tuple[str, float, float]]:
    src = _BASELINE_VI if language.startswith("vi") else _BASELINE_EN
    return {term: (pol, vw, aw) for term, pol, vw, aw in src}


def _merge_db_lexicon(language: str) -> dict[str, tuple[str, float, float]]:
    """Merge baseline + admin-edited rows. Lazy import keeps tests happy."""
    out = _baseline_lexicon(language)
    try:
        from affect.models import AffectLexiconEntry
        for row in AffectLexiconEntry.objects.filter(language__startswith=language[:2]):
            out[row.term.lower()] = (row.polarity, row.valence_weight, row.arousal_weight)
    except Exception:
        pass
    return out


def estimate(text: str, *, language: str = "vi", min_text_len: int = 8) -> LinguisticSnapshot:
    raw = text or ""
    norm = _normalise(raw)
    if len(norm) < min_text_len:
        return LinguisticSnapshot(
            valence=0.0,
            arousal=0.0,
            confidence=max(0.0, len(norm) / max(min_text_len, 1)),
            label="insufficient_sample",
            features={"text_length": len(norm)},
        )

    lexicon = _merge_db_lexicon(language)
    negations = _NEGATIONS_VI if language.startswith("vi") else _NEGATIONS_EN
    tokens = _tokenise(norm)

    valence_sum = 0.0
    arousal_sum = 0.0
    matched = 0
    negate_window = 0
    for tok in tokens:
        if tok in negations:
            negate_window = 3
            continue
        # bigram window for 2-word terms (e.g. "vui vẻ").
        bigram = None
        idx = tokens.index(tok)
        if idx + 1 < len(tokens):
            bigram = f"{tok} {tokens[idx + 1]}"
        for term in (bigram, tok):
            if term and term in lexicon:
                pol, vw, aw = lexicon[term]
                sign = -1.0 if negate_window > 0 else 1.0
                valence_sum += sign * vw
                arousal_sum += aw
                matched += 1
                break
        if negate_window > 0:
            negate_window -= 1

    exclam = norm.count("!")
    question = norm.count("?")
    upper_ratio = sum(1 for c in raw if c.isupper()) / max(len(raw), 1)

    valence = valence_sum / max(matched, 1) if matched else 0.0
    arousal = max(
        0.0,
        min(
            1.0,
            (arousal_sum / max(matched, 1) if matched else 0.0)
            + 0.10 * min(exclam, 5)
            + 0.05 * min(question, 5)
            + 0.20 * upper_ratio,
        ),
    )
    valence = max(-1.0, min(1.0, valence))

    if matched == 0:
        label = "neutral"
    elif valence > 0.3:
        label = "positive"
    elif valence < -0.5 and arousal > 0.5:
        label = "frustrated"
    elif valence < -0.3:
        label = "negative"
    elif arousal < 0.2:
        label = "calm"
    else:
        label = "neutral"

    confidence = max(0.05, min(1.0, matched / 5.0 + len(norm) / 200.0))
    return LinguisticSnapshot(
        valence=valence,
        arousal=arousal,
        confidence=confidence,
        label=label,
        features={
            "matched_terms": matched,
            "exclam": exclam,
            "question": question,
            "upper_ratio": round(upper_ratio, 4),
            "text_length": len(norm),
        },
    )
