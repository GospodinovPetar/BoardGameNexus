from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("web.urls")),
    path("games/", include("games.urls")),
    path("events/", include("events.urls")),
]
