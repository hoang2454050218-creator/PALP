"""Research participation + anonymisation tests."""
from __future__ import annotations

import pytest

from research.models import (
    AnonymizedExport,
    ResearchParticipation,
    ResearchProtocol,
)
from research.services import (
    anonymise_rows,
    decline,
    export_anonymised,
    opt_in,
    opted_in_students,
    withdraw,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def protocol(db):
    return ResearchProtocol.objects.create(
        code="test-001",
        title="Replication of Piech et al. 2015 DKT",
        description="Replicate DKT experiments on PALP attempt logs.",
        pi_name="Dr. PI", pi_email="pi@example.com",
        irb_number="IRB-2026-1",
        status=ResearchProtocol.Status.ACTIVE,
    )


class TestParticipationLifecycle:
    def test_opt_in_creates_row_and_consent(self, student, protocol):
        part = opt_in(student, protocol)
        assert part.state == ResearchParticipation.State.OPTED_IN
        assert student.consent_records.filter(
            purpose="research_participation", granted=True,
        ).exists()

    def test_withdraw_marks_state(self, student, protocol):
        opt_in(student, protocol)
        part = withdraw(student, protocol)
        assert part.state == ResearchParticipation.State.WITHDRAWN
        assert part.withdrawn_at is not None
        assert student.consent_records.filter(
            purpose="research_participation", granted=False,
        ).exists()

    def test_decline_creates_row(self, student, protocol):
        part = decline(student, protocol)
        assert part.state == ResearchParticipation.State.DECLINED

    def test_opted_in_students_excludes_withdrawn(self, student, student_b, protocol):
        opt_in(student, protocol)
        opt_in(student_b, protocol)
        withdraw(student_b, protocol)
        ids = {p.student_id for p in opted_in_students(protocol)}
        assert ids == {student.id}


class TestAnonymisation:
    def _rows(self, n: int = 12):
        rows = []
        for i in range(n):
            rows.append({
                "student_id": 1000 + i,
                "first_name": f"Name{i}",
                "concept": "stress_concentration" if i % 2 == 0 else "elastic_buckling",
                "score": 50 + (i % 5) * 10,
            })
        return rows

    def test_hashes_ids_and_suppresses_quasi_identifiers(self):
        cleaned, report = anonymise_rows(self._rows())
        assert all("first_name" not in r for r in cleaned)
        assert all(isinstance(r.get("student_id"), str) for r in cleaned)
        assert report.record_count == 12
        assert report.participant_count == 12

    def test_passes_k_anonymity_when_residual_qi_collapses(self):
        cleaned, report = anonymise_rows(
            self._rows(),
            quasi_identifier_columns=["concept"],
        )
        assert report.passed
        assert report.k_value >= 5

    def test_blocks_export_when_too_unique(self, settings, protocol, lecturer):
        rows = [
            {"student_id": i, "concept": f"unique_{i}"} for i in range(3)
        ]
        try:
            export_anonymised(
                protocol,
                rows=rows,
                dataset_key="too-unique",
                requested_by=lecturer,
            )
        except PermissionError as exc:
            assert "k-anonymity check failed" in str(exc)
        else:
            raise AssertionError("Expected PermissionError")
        assert AnonymizedExport.objects.filter(dataset_key="too-unique").exists()

    def test_export_writes_audit_row(self, protocol, lecturer):
        rows = [
            {"student_id": i, "concept": "shared_topic"} for i in range(10)
        ]
        cleaned, log = export_anonymised(
            protocol,
            rows=rows,
            dataset_key="ok-export",
            requested_by=lecturer,
        )
        assert log.k_anonymity_passed
        assert log.record_count == 10
        assert all(r["concept"] == "shared_topic" for r in cleaned)


class TestResearchAPI:
    def test_student_can_opt_in_and_withdraw(self, student, student_api, protocol):
        r1 = student_api.post(f"/api/research/protocols/{protocol.code}/opt-in/")
        assert r1.status_code == 201, r1.content
        r2 = student_api.post(f"/api/research/protocols/{protocol.code}/withdraw/")
        assert r2.status_code == 200
        assert r2.json()["state"] == "withdrawn"

    def test_my_participations_returns_history(self, student, student_api, protocol):
        opt_in(student, protocol)
        resp = student_api.get("/api/research/me/participations/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_student_sees_only_active_protocols(self, student, student_api, protocol):
        ResearchProtocol.objects.create(
            code="draft-001", title="Draft", description="x",
            status=ResearchProtocol.Status.DRAFT,
        )
        resp = student_api.get("/api/research/protocols/")
        assert resp.status_code == 200
        body = resp.json()
        rows = body["results"] if isinstance(body, dict) else body
        codes = {p["code"] for p in rows}
        assert "test-001" in codes
        assert "draft-001" not in codes
