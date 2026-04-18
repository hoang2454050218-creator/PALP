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
