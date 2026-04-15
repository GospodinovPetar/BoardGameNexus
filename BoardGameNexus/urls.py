from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("web.urls")),
    path("games/", include("games.urls")),
    path("events/", include("events.urls")),
    path("reviews/", include("reviews.urls")),
    path("api/", include(("api.urls", "api"), namespace="api")),
    path(
        "api/docs/",
        TemplateView.as_view(template_name="api/api_docs.html"),
        name="api_docs",
    ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
