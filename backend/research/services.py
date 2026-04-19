"""IRB-grade research participation services.

Three responsibilities:

1. **Opt-in / withdraw lifecycle** — wrappers that always create a
   ``ResearchParticipation`` row and a matching ``ConsentRecord`` so
   the audit trail tells the same story from both sides.
2. **Eligible cohort resolution** — for a given protocol, return the
   currently opted-in students; never include withdrawn ones.
3. **Anonymisation** — produce a row stream where (a) student IDs
   are SHA-256(salt + id) hashed, (b) configured quasi-identifiers
   are suppressed, (c) k-anonymity ≥ K_PALP_RESEARCH_K is verified
   on the residual quasi-identifiers, blocking the export when
   not met.
"""
from __future__ import annotations

import hashlib
import logging
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from privacy.constants import CONSENT_VERSION
from privacy.models import ConsentRecord

from .models import AnonymizedExport, ResearchParticipation, ResearchProtocol

logger = logging.getLogger("palp.research")


@dataclass(frozen=True)
class AnonymisationReport:
    record_count: int
    participant_count: int
    k_value: int
    passed: bool
    suppressed_columns: Sequence[str]


def _settings():
    return getattr(settings, "PALP_RESEARCH", {}) or {}


def _hash_id(value: int | str) -> str:
    salt = _settings().get("ID_HASH_SALT", "palp-dev-salt")
    digest = hashlib.sha256(f"{salt}::{value}".encode("utf-8")).hexdigest()
    return digest[:16]


def opt_in(student, protocol: ResearchProtocol) -> ResearchParticipation:
    """Create or refresh an opt-in row + matching ConsentRecord row."""
    with transaction.atomic():
        part, _ = ResearchParticipation.objects.update_or_create(
            student=student,
            protocol=protocol,
            defaults={
                "state": ResearchParticipation.State.OPTED_IN,
                "consent_text_version": CONSENT_VERSION,
                "withdrawn_at": None,
            },
        )
        ConsentRecord.objects.create(
            user=student,
            purpose=ConsentRecord.Purpose.RESEARCH_PARTICIPATION,
            granted=True,
            version=CONSENT_VERSION,
        )
    return part


def withdraw(student, protocol: ResearchProtocol) -> ResearchParticipation | None:
    """Mark withdrawal — never delete row so audit log stays intact."""
    try:
        part = ResearchParticipation.objects.get(
            student=student, protocol=protocol,
        )
    except ResearchParticipation.DoesNotExist:
        return None
    with transaction.atomic():
        part.state = ResearchParticipation.State.WITHDRAWN
        part.withdrawn_at = timezone.now()
        part.save(update_fields=["state", "withdrawn_at"])
        ConsentRecord.objects.create(
            user=student,
            purpose=ConsentRecord.Purpose.RESEARCH_PARTICIPATION,
            granted=False,
            version=CONSENT_VERSION,
        )
    return part


def decline(student, protocol: ResearchProtocol) -> ResearchParticipation:
    """Create a 'declined' row when a student dismisses the prompt."""
    part, _ = ResearchParticipation.objects.update_or_create(
        student=student,
        protocol=protocol,
        defaults={
            "state": ResearchParticipation.State.DECLINED,
            "consent_text_version": CONSENT_VERSION,
        },
    )
    return part


def opted_in_students(protocol: ResearchProtocol):
    return (
        ResearchParticipation.objects
        .filter(protocol=protocol, state=ResearchParticipation.State.OPTED_IN)
        .select_related("student")
    )


def _k_anonymity(rows: Sequence[Mapping], qi_columns: Sequence[str]) -> int:
    """Min equivalence-class size on the residual quasi-identifier set.

    A row whose QI tuple appears n times across the dataset is in an
    n-anonymous equivalence class. The dataset's k-anonymity is the
    minimum n across all rows. Returns ``len(rows)`` (i.e. fully
    indistinguishable) when no QI columns survive — that is the
    safest possible outcome.
    """
    if not rows:
        return 0
    if not qi_columns:
        return len(rows)
    counter: Counter = Counter()
    for row in rows:
        key = tuple((c, row.get(c)) for c in qi_columns)
        counter[key] += 1
    return min(counter.values())


def anonymise_rows(
    rows: Iterable[Mapping],
    *,
    suppress_columns: Sequence[str] | None = None,
    quasi_identifier_columns: Sequence[str] | None = None,
    id_columns: Sequence[str] = ("student_id",),
) -> tuple[List[Dict], AnonymisationReport]:
    """Run the anonymisation pipeline on a row stream.

    * Hash any column listed in ``id_columns``.
    * Drop any column listed in ``suppress_columns`` (defaults to the
      configured ``SUPPRESS_QUASI_IDENTIFIERS``).
    * Compute k-anonymity over ``quasi_identifier_columns`` (default:
      everything that survives suppression except the hashed IDs).
    """
    cfg = _settings()
    suppress = list(suppress_columns or cfg.get("SUPPRESS_QUASI_IDENTIFIERS", []))
    target_k = int(cfg.get("K_ANONYMITY_K", 5))

    cleaned: List[Dict] = []
    seen_participants = set()
    id_set = set(id_columns)
    for row in rows:
        normalised: Dict = {}
        for k, v in row.items():
            if k in id_set:
                if v is not None:
                    normalised[k] = _hash_id(v)
                    seen_participants.add(normalised[k])
                continue
            if k in suppress:
                continue
            normalised[k] = v
        cleaned.append(normalised)

    qi_cols = list(quasi_identifier_columns or [
        k for k in (cleaned[0].keys() if cleaned else [])
        if k not in id_columns
    ])

    k_value = _k_anonymity(cleaned, qi_cols)
    report = AnonymisationReport(
        record_count=len(cleaned),
        participant_count=len(seen_participants),
        k_value=k_value,
        passed=k_value >= target_k,
        suppressed_columns=tuple(suppress),
    )
    return cleaned, report


def export_anonymised(
    protocol: ResearchProtocol,
    *,
    rows: Iterable[Mapping],
    dataset_key: str,
    requested_by=None,
    suppress_columns: Sequence[str] | None = None,
    quasi_identifier_columns: Sequence[str] | None = None,
    id_columns: Sequence[str] = ("student_id",),
) -> tuple[List[Dict], AnonymizedExport]:
    """Anonymise rows + persist the audit log.

    The audit row is committed in its OWN transaction *before* we
    raise, so a failed export still leaves a permanent paper trail
    (the auditor needs to see who tried, what k-value triggered the
    block, and when). Only after the audit row is durably stored do
    we raise on a k-anonymity failure.
    """
    cleaned, report = anonymise_rows(
        rows,
        suppress_columns=suppress_columns,
        quasi_identifier_columns=quasi_identifier_columns,
        id_columns=id_columns,
    )

    with transaction.atomic():
        log = AnonymizedExport.objects.create(
            protocol=protocol,
            requested_by=requested_by,
            dataset_key=dataset_key,
            record_count=report.record_count,
            participant_count=report.participant_count,
            k_anonymity_value=report.k_value,
            k_anonymity_passed=report.passed,
            suppressed_columns=list(report.suppressed_columns),
            salt_id="env:PALP_RESEARCH_HASH_SALT",
        )

    if not report.passed:
        raise PermissionError(
            f"k-anonymity check failed: k={report.k_value} < target. "
            f"Export {log.id} blocked from delivery."
        )
    return cleaned, log
