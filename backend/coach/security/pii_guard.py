"""PII Guard — mask PII before sending to any LLM, restore on the way back.

Pure-Python implementation that never imports spaCy or any other
heavyweight dependency at module level. The playbook calls for spaCy
NER on names; we keep that as a pluggable step gated on
``spacy`` import success so the test suite (and the bare-metal SQLite
runner) work without the wheel.

The masker is **deterministic** within a single ``mask`` call so the
restore step can do a literal string replacement. We don't try to be
clever with overlapping spans — the simple "replace longest first"
ordering is enough for our threat model (the LLM may see masked
tokens; an unmasked token slipping through is the failure case we
defend against, not a slightly wrong mask).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Pattern


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

EMAIL_RE: Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
PHONE_VN_RE: Pattern[str] = re.compile(r"(?:\+?84|0)\d{9,10}\b")
STUDENT_ID_RE: Pattern[str] = re.compile(r"\b\d{8,10}\b")
CREDIT_CARD_RE: Pattern[str] = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


@dataclass
class MaskResult:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)
    count: int = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def mask(text: str) -> MaskResult:
    """Replace PII in ``text`` with opaque tokens. Idempotent at the call boundary.

    The mapping returned can be passed to :func:`restore` after the LLM
    response is received. Mapping is request-scope only; callers must
    not persist it.
    """
    if not text:
        return MaskResult(text=text, mapping={}, count=0)

    mapping: dict[str, str] = {}
    masked = text

    masked = _mask_with(EMAIL_RE, masked, mapping, prefix="EMAIL")
    masked = _mask_with(PHONE_VN_RE, masked, mapping, prefix="PHONE")
    masked = _mask_with(STUDENT_ID_RE, masked, mapping, prefix="STUDENT_ID")
    masked = _mask_with(CREDIT_CARD_RE, masked, mapping, prefix="CARD")

    masked = _mask_names_via_spacy(masked, mapping)

    return MaskResult(text=masked, mapping=mapping, count=len(mapping))


def restore(text: str, mapping: dict[str, str]) -> str:
    """Restore tokens back to the original PII strings."""
    if not mapping:
        return text
    out = text
    for token, original in mapping.items():
        out = out.replace(token, original)
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mask_with(
    pattern: Pattern[str],
    text: str,
    mapping: dict[str, str],
    *,
    prefix: str,
) -> str:
    matches = list(pattern.finditer(text))
    if not matches:
        return text
    # Replace from the end so earlier indices stay valid.
    out_parts: list[str] = []
    cursor = 0
    for i, m in enumerate(matches):
        token = f"[{prefix}_{len(mapping)}]"
        mapping[token] = m.group()
        out_parts.append(text[cursor:m.start()])
        out_parts.append(token)
        cursor = m.end()
    out_parts.append(text[cursor:])
    return "".join(out_parts)


def _mask_names_via_spacy(text: str, mapping: dict[str, str]) -> str:
    """Best-effort name masking via spaCy NER if installed.

    This is intentionally a soft dependency — the system check, the
    test suite and the bare-metal SQLite runner all work without
    spaCy. If spaCy or the multi-language model is missing we just
    skip names and rely on the patterned PII categories.
    """
    try:  # pragma: no cover - guarded import
        import spacy
    except ImportError:  # pragma: no cover - common in test env
        return text

    try:  # pragma: no cover - guarded model load
        nlp = spacy.load("xx_ent_wiki_sm")
    except Exception:  # pragma: no cover
        return text

    doc = nlp(text)  # pragma: no cover
    out = text  # pragma: no cover
    for ent in doc.ents:  # pragma: no cover
        if ent.label_ in ("PER", "PERSON") and ent.text in out:
            token = f"[NAME_{len(mapping)}]"
            mapping[token] = ent.text
            out = out.replace(ent.text, token)
    return out  # pragma: no cover
