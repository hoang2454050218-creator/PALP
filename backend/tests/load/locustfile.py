"""
PALP Load / Stress / Soak / Spike Test Suite

Usage (standalone, normal load):
    locust -f backend/tests/load/locustfile.py --host=http://localhost:8000

Usage (with custom shape):
    locust -f backend/tests/load/locustfile.py,backend/tests/load/shapes.py \
           --host=http://localhost:8000 --class-picker

SLO Targets (from PALP_SLO in settings/base.py):
    p95 response time:
        /auth/          < 500ms
        /adaptive/submit/ < 2s
        /dashboard/     < 2s
        /assessment/    < 2s
        /events/track/  < 500ms
        /health/        < 200ms
    Error rate          < 0.5%
    Queue depth         < WARN threshold (50)
"""
import random
import logging

from locust import HttpUser, task, between, SequentialTaskSet, events

logger = logging.getLogger("palp.loadtest")

SLO_P95 = {
    "/api/auth/login/": 500,
    "/api/adaptive/submit/": 2000,
    "/api/adaptive/pathway/": 2000,
    "/api/adaptive/mastery/": 1000,
    "/api/dashboard/class/": 2000,
    "/api/dashboard/alerts/": 1000,
    "/api/assessment/": 2000,
    "/api/events/track/": 500,
    "/api/analytics/kpi/": 2000,
    "/api/health/": 200,
}


def _jwt_login(client, username, password):
    resp = client.post(
        "/api/auth/login/",
        json={"username": username, "password": password},
        name="/api/auth/login/",
    )
    if resp.status_code == 200:
        token = resp.json().get("access", "")
        client.headers["Authorization"] = f"Bearer {token}"
        return True
    logger.warning("Login failed for %s: %s", username, resp.status_code)
    return False


# ---------------------------------------------------------------------------
# Student profile (70% traffic)
#   login -> load dashboard -> complete task -> trigger adaptive
# ---------------------------------------------------------------------------
class StudentBehavior(SequentialTaskSet):

    def on_start(self):
        idx = random.randint(1, 200)
        self.username = f"sv_load_{idx}"
        self.course_id = 1
        self.task_ids = list(range(1, 11))
        if not _jwt_login(self.client, self.username, "loadtest123!"):
            _jwt_login(self.client, "sv_test", "testpass123")

    # -- Step 1: login (done in on_start) --

    @task
    def load_student_dashboard(self):
        """Load student-facing data: pathway + mastery + assessment sessions."""
        self.client.get(
            f"/api/adaptive/pathway/{self.course_id}/",
            name="/api/adaptive/pathway/[id]/",
        )
        self.client.get(
            "/api/adaptive/mastery/",
            name="/api/adaptive/mastery/",
        )
        self.client.get(
            "/api/assessment/my-sessions/",
            name="/api/assessment/my-sessions/",
        )

    @task
    def complete_task(self):
        """Submit a task answer (complete task flow)."""
        tid = random.choice(self.task_ids)
        self.client.post(
            "/api/adaptive/submit/",
            json={
                "task_id": tid,
                "answer": random.choice(["A", "B", "C", "D"]),
                "duration_seconds": random.randint(30, 180),
                "hints_used": random.randint(0, 2),
            },
            name="/api/adaptive/submit/",
        )

    @task
    def trigger_adaptive(self):
        """Fetch pathway decision after submission (trigger adaptive engine)."""
        self.client.get(
            f"/api/adaptive/pathway/{self.course_id}/",
            name="/api/adaptive/pathway/[id]/",
        )
        self.client.get(
            f"/api/adaptive/next-task/{self.course_id}/",
            name="/api/adaptive/next-task/[id]/",
        )

    @task
    def track_learning_event(self):
        self.client.post(
            "/api/events/track/",
            json={
                "event_name": "micro_task_completed",
                "properties": {
                    "page": "/pathway",
                    "concept_id": random.randint(1, 10),
                },
            },
            name="/api/events/track/",
        )

    @task
    def check_wellbeing(self):
        self.client.post(
            "/api/wellbeing/check/",
            json={"continuous_minutes": random.randint(20, 70)},
            name="/api/wellbeing/check/",
        )


# ---------------------------------------------------------------------------
# Lecturer profile (20% traffic)
#   login -> load dashboard -> view alerts -> take action
# ---------------------------------------------------------------------------
class LecturerBehavior(SequentialTaskSet):

    def on_start(self):
        idx = random.randint(1, 20)
        self.class_id = 1
        if not _jwt_login(self.client, f"gv_load_{idx}", "loadtest123!"):
            _jwt_login(self.client, "gv_test", "testpass123")

    @task
    def load_dashboard(self):
        self.client.get(
            f"/api/dashboard/class/{self.class_id}/overview/",
            name="/api/dashboard/class/[id]/overview/",
        )

    @task
    def view_alerts(self):
        self.client.get(
            f"/api/dashboard/alerts/?class_id={self.class_id}",
            name="/api/dashboard/alerts/",
        )
        self.client.get(
            f"/api/dashboard/alerts/?class_id={self.class_id}&severity=red",
            name="/api/dashboard/alerts/?severity=red",
        )

    @task
    def view_kpi(self):
        self.client.get(
            f"/api/analytics/kpi/{self.class_id}/",
            name="/api/analytics/kpi/[id]/",
        )

    @task
    def view_intervention_history(self):
        self.client.get(
            "/api/dashboard/interventions/history/",
            name="/api/dashboard/interventions/history/",
        )


# ---------------------------------------------------------------------------
# Admin profile (10% traffic)
#   login -> analytics -> deep health
# ---------------------------------------------------------------------------
class AdminBehavior(SequentialTaskSet):

    def on_start(self):
        if not _jwt_login(self.client, "admin_load", "loadtest123!"):
            _jwt_login(self.client, "test_admin", "testpass123")

    @task
    def view_analytics(self):
        self.client.get(
            "/api/analytics/reports/",
            name="/api/analytics/reports/",
        )
        self.client.get(
            "/api/analytics/data-quality/",
            name="/api/analytics/data-quality/",
        )

    @task
    def deep_health_check(self):
        self.client.get(
            "/api/health/deep/",
            name="/api/health/deep/",
        )

    @task
    def health_check(self):
        self.client.get(
            "/api/health/",
            name="/api/health/",
        )
        self.client.get(
            "/api/health/ready/",
            name="/api/health/ready/",
        )


# ---------------------------------------------------------------------------
# User classes with traffic weights matching QA_STANDARD Section 8.3
# ---------------------------------------------------------------------------
class StudentUser(HttpUser):
    tasks = [StudentBehavior]
    wait_time = between(1, 3)
    weight = 7


class LecturerUser(HttpUser):
    tasks = [LecturerBehavior]
    wait_time = between(2, 5)
    weight = 2


class AdminUser(HttpUser):
    tasks = [AdminBehavior]
    wait_time = between(3, 8)
    weight = 1


# ---------------------------------------------------------------------------
# SLO assertion on test quit
# ---------------------------------------------------------------------------
@events.quitting.add_listener
def _assert_slo(environment, **_kwargs):
    from .slo_assertions import check_slo_on_quit
    check_slo_on_quit(environment)
