from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

handler404 = "web.views.custom_404"
handler500 = "web.views.custom_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("web.urls")),
    path("games/", include("games.urls")),
    path("events/", include("events.urls")),
    path("venues/", include("venues.urls")),
    path("reviews/", include("reviews.urls")),
    path("api/", include(("api.urls", "api"), namespace="api")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api_schema"),
        name="api_docs",
    ),
]

# User uploads (avatars, game images). In production, point MEDIA_URL to object storage
# or serve files with nginx; for local / Docker, enable DEBUG or SERVE_MEDIA_IN_APP.
if settings.DEBUG or getattr(settings, "SERVE_MEDIA_IN_APP", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
