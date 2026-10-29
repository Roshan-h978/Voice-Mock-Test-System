"""Root URL configuration for the Voice Mock Test System API."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.urls import include, path

admin.site.site_header = "Voice Mock Test administration"
admin.site.site_title = "Voice Mock Test admin"
admin.site.index_title = "Data management"


def health_check(_request):
    """Check for hosting platforms and uptime monitors: the API answers and the database is reachable.

    A monitor that opens this page every few minutes also keeps a free Render server and Supabase project awake.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "error", "service": "voice-mock-test-api", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "service": "voice-mock-test-api", "database": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.tests_manager.urls")),
    path("api/", include("apps.attempts.urls")),
    path("api/", include("apps.learning.urls")),
    path("api/evaluation/", include("apps.evaluation.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
]

# Serve uploaded recordings from backend/media during local development only.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
