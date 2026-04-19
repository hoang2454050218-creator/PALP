from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.permissions import IsAdminUser
from palp.metrics_view import metrics_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/assessment/", include("assessment.urls")),
    path("api/adaptive/", include("adaptive.urls")),
    path("api/curriculum/", include("curriculum.urls")),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/analytics/", include("analytics.urls")),
    path("api/events/", include("events.urls")),
    path("api/wellbeing/", include("wellbeing.urls")),
    path("api/privacy/", include("privacy.urls")),
    path("api/health/", include("analytics.health_urls")),
    path("api/feature-flags/", include("featureflags.urls")),
    path("api/experiments/", include("experiments.urls")),
    path("api/mlops/", include("mlops.urls")),
    path("api/fairness/", include("fairness.urls")),
    path("api/causal/", include("causal.urls")),
    path("api/sessions/", include("device_sessions.urls")),
    path("api/signals/", include("signals.urls")),
    path("api/risk/", include("risk.urls")),
    path("api/goals/", include("goals.urls")),
    path("api/peer/", include("peer.urls")),
    path("api/coach/", include("coach.urls")),
    path("api/emergency/", include("emergency.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/dkt/", include("dkt.urls")),
    path("api/knowledge-graph/", include("knowledge_graph.urls")),
    path("api/bandit/", include("bandit.urls")),
    path("api/coach/memory/", include("coach_memory.urls")),
    path("api/explain/", include("explainability.urls")),
    path("api/spacedrep/", include("spacedrep.urls")),
    path("api/privacy-dp/", include("privacy_dp.urls")),
    path("api/copilot/", include("instructor_copilot.urls")),
    # Phase 7 — Academic layer
    path("api/benchmarks/", include("benchmarks.urls")),
    path("api/research/", include("research.urls")),
    path("api/publication/", include("publication.urls")),
    path("api/affect/", include("affect.urls")),
    path("metrics", metrics_view, name="prometheus-metrics"),
    path("metrics/", metrics_view, name="prometheus-metrics-slash"),
]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]
else:
    urlpatterns += [
        path(
            "api/schema/",
            SpectacularAPIView.as_view(permission_classes=[IsAdminUser]),
            name="schema",
        ),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(
                url_name="schema",
                permission_classes=[IsAdminUser],
            ),
            name="swagger-ui",
        ),
    ]
