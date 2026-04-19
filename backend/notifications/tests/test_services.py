"""Notifications service + view tests."""
from __future__ import annotations

import pytest

from notifications.models import Notification, NotificationPreference
from notifications.services import dispatch, mark_read, unread_count


pytestmark = pytest.mark.django_db


class TestDispatch:
    def test_creates_notification(self, student):
        notif = dispatch(
            user=student, category="coach", title="Hi", body="x",
        )
        assert isinstance(notif, Notification)
        assert notif.user_id == student.id

    def test_respects_preference_when_disabled(self, student):
        pref, _ = NotificationPreference.objects.get_or_create(user=student)
        pref.in_app_enabled = False
        pref.save()
        notif = dispatch(user=student, category="coach", title="Hi")
        assert notif is None

    def test_bypass_preference_for_urgent(self, student):
        pref, _ = NotificationPreference.objects.get_or_create(user=student)
        pref.in_app_enabled = False
        pref.save()
        notif = dispatch(
            user=student, category="emergency", title="Urgent",
            bypass_preference=True,
        )
        assert notif is not None


class TestMarkRead:
    def test_marks_only_owner_unread_rows(self, student, student_b):
        own = dispatch(user=student, category="coach", title="A")
        other = dispatch(user=student_b, category="coach", title="B")
        marked = mark_read(user=student, ids=[own.id, other.id])
        assert marked == 1
        own.refresh_from_db()
        assert own.read_at is not None


class TestUnreadCount:
    def test_counts_only_unread_for_user(self, student):
        dispatch(user=student, category="coach", title="A")
        dispatch(user=student, category="coach", title="B")
        assert unread_count(user=student) == 2


class TestViews:
    def test_list_returns_owner_only(self, student_api, student, student_b):
        dispatch(user=student, category="coach", title="A")
        dispatch(user=student_b, category="coach", title="B")
        resp = student_api.get("/api/notifications/")
        assert resp.status_code == 200
        assert len(resp.data["notifications"]) == 1

    def test_unread_filter(self, student_api, student):
        n1 = dispatch(user=student, category="coach", title="A")
        n2 = dispatch(user=student, category="coach", title="B")
        mark_read(user=student, ids=[n1.id])
        resp = student_api.get("/api/notifications/?unread=true")
        assert len(resp.data["notifications"]) == 1
        assert resp.data["notifications"][0]["id"] == n2.id

    def test_mark_one_read(self, student_api, student):
        n = dispatch(user=student, category="coach", title="A")
        resp = student_api.post(f"/api/notifications/{n.id}/read/")
        assert resp.status_code == 200
        assert resp.data["marked"] == 1
