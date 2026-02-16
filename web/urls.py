from django.urls import path

from web import views

app_name = "web"
urlpatterns = [
    path("", views.index, name="index"),
    path("mission/", views.mission, name="mission"),
]
