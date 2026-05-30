from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from .health import health, health_live, health_ready

urlpatterns = [
    path("health", health),
    path("health/live", health_live),
    path("health/ready", health_ready),
    path("debug/", include("polls.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("quests.urls")),
    path("social-auth/", include("social_django.urls", namespace="social")),
    path("api/", include("users.urls")),
    path("api/", include("storage.urls")),
]

if settings.DOCS_ENABLED:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
