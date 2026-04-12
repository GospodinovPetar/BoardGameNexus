from django.urls import path

from web import views

app_name = "web"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("mission/", views.MissionView.as_view(), name="mission"),
    path("contact/", views.ContactView.as_view(), name="contact"),
]
