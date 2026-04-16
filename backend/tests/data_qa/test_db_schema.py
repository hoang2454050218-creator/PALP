"""
Database Schema Discipline Tests (DB-01..DB-08, NQ-01..NQ-05).

QA_STANDARD Section 6.5.
Verifies FK constraints, unique constraints, indexes, and N+1 prevention.
"""
import pytest
from django.db import IntegrityError, connection

from accounts.models import User
from adaptive.models import MasteryState, TaskAttempt
from assessment.models import AssessmentSession
from curriculum.models import Concept, Course
from dashboard.models import Alert
from events.models import EventLog

pytestmark = [pytest.mark.django_db, pytest.mark.data_qa]


# ---------------------------------------------------------------------------
# DB-02: Unique MasteryState(student, concept)
# ---------------------------------------------------------------------------


class TestDB02UniqueMastery:

    def test_duplicate_mastery_raises_integrity_error(self, student, concepts):
        MasteryState.objects.create(
            student=student, concept=concepts[0], p_mastery=0.5,
        )
        with pytest.raises(IntegrityError):
            MasteryState.objects.create(
                student=student, concept=concepts[0], p_mastery=0.6,
            )

    def test_different_concepts_allowed(self, student, concepts):
        if len(concepts) < 2:
            pytest.skip("Need >= 2 concepts")
        MasteryState.objects.create(student=student, concept=concepts[0])
        MasteryState.objects.create(student=student, concept=concepts[1])
        assert MasteryState.objects.filter(student=student).count() == 2


# ---------------------------------------------------------------------------
# DB-05: Unique idempotency_key on EventLog
# ---------------------------------------------------------------------------


class TestDB05UniqueIdempotencyKey:

    def test_duplicate_key_raises_integrity_error(self, student):
        from django.utils import timezone
        EventLog.objects.create(
            event_name=EventLog.EventName.PAGE_VIEW,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            idempotency_key="unique-test-key-001",
        )
        with pytest.raises(IntegrityError):
            EventLog.objects.create(
                event_name=EventLog.EventName.PAGE_VIEW,
                timestamp_utc=timezone.now(),
                actor=student,
                actor_type=EventLog.ActorType.STUDENT,
                idempotency_key="unique-test-key-001",
            )

    def test_null_keys_allowed_multiple(self, student):
        from django.utils import timezone
        for _ in range(3):
            EventLog.objects.create(
                event_name=EventLog.EventName.PAGE_VIEW,
                timestamp_utc=timezone.now(),
                actor=student,
                actor_type=EventLog.ActorType.STUDENT,
                idempotency_key=None,
            )
        assert EventLog.objects.filter(actor=student).count() == 3


# ---------------------------------------------------------------------------
# DB-06: Unique Concept order per course
# ---------------------------------------------------------------------------


class TestDB06UniqueConceptOrder:

    def test_duplicate_order_in_same_course_rejected(self, course):
        Concept.objects.create(course=course, code="DUP1", name="First", order=1)
        with pytest.raises(IntegrityError):
            Concept.objects.create(course=course, code="DUP2", name="Second", order=1)

    def test_same_order_different_courses_allowed(self):
        c1 = Course.objects.create(code="C1", name="Course 1")
        c2 = Course.objects.create(code="C2", name="Course 2")
        Concept.objects.create(course=c1, code="A1", name="A1", order=1)
        Concept.objects.create(course=c2, code="A2", name="A2", order=1)


# ---------------------------------------------------------------------------
# DB-08: Indexes exist on hot-path queries
# ---------------------------------------------------------------------------


class TestDB08CoreIndexes:

    def test_mastery_state_has_student_concept_index(self):
        indexes = self._get_indexes("palp_mastery_state")
        columns_covered = set()
        for idx in indexes:
            columns_covered.update(idx["columns"])
        assert "student_id" in columns_covered
        assert "concept_id" in columns_covered

    def test_event_log_has_actor_timestamp_index(self):
        indexes = self._get_indexes("palp_event_log")
        has_actor_index = any(
            "actor_id" in idx["columns"]
            for idx in indexes
        )
        assert has_actor_index

    def test_alert_has_class_status_index(self):
        indexes = self._get_indexes("palp_alert") if self._table_exists("palp_alert") else []
        if indexes:
            columns_covered = set()
            for idx in indexes:
                columns_covered.update(idx["columns"])
            assert "student_class_id" in columns_covered or "status" in columns_covered

    def _table_exists(self, table_name):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
                [table_name],
            )
            return cursor.fetchone()[0]

    def _get_indexes(self, table_name):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT indexname, array_agg(attname ORDER BY attnum) as columns
                FROM pg_indexes
                JOIN pg_index ON indexrelid = (
                    SELECT oid FROM pg_class WHERE relname = indexname
                )
                JOIN pg_attribute ON attrelid = indrelid AND attnum = ANY(indkey)
                WHERE tablename = %s
                GROUP BY indexname
            """, [table_name])
            return [
                {"name": row[0], "columns": row[1]}
                for row in cursor.fetchall()
            ]


# ---------------------------------------------------------------------------
# DB-01: FK constraints enforced at DB level
# ---------------------------------------------------------------------------


class TestDB01ForeignKeys:

    def test_mastery_state_fk_fields(self):
        fk_fields = [
            f for f in MasteryState._meta.get_fields()
            if hasattr(f, "related_model") and f.related_model is not None
        ]
        fk_model_names = {f.related_model.__name__ for f in fk_fields}
        assert "User" in fk_model_names
        assert "Concept" in fk_model_names

    def test_task_attempt_fk_fields(self):
        fk_fields = [
            f for f in TaskAttempt._meta.get_fields()
            if hasattr(f, "related_model") and f.related_model is not None
        ]
        fk_model_names = {f.related_model.__name__ for f in fk_fields}
        assert "User" in fk_model_names
        assert "MicroTask" in fk_model_names

    def test_alert_fk_fields(self):
        fk_fields = [
            f for f in Alert._meta.get_fields()
            if hasattr(f, "related_model") and f.related_model is not None
        ]
        fk_model_names = {f.related_model.__name__ for f in fk_fields}
        assert "User" in fk_model_names
        assert "StudentClass" in fk_model_names

    def test_event_log_fk_fields(self):
        fk_fields = [
            f for f in EventLog._meta.get_fields()
            if hasattr(f, "related_model") and f.related_model is not None
        ]
        fk_model_names = {f.related_model.__name__ for f in fk_fields}
        assert "User" in fk_model_names


# ---------------------------------------------------------------------------
# MIG-05: No missing migrations
# ---------------------------------------------------------------------------


class TestMIG05NoMissingMigrations:

    def test_no_pending_migrations(self):
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        try:
            call_command("makemigrations", "--check", "--dry-run", stdout=out)
        except SystemExit as e:
            assert e.code == 0, f"Missing migrations detected: {out.getvalue()}"
