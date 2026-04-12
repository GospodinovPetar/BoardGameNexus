from django.urls import path

from events import views

app_name = "events"

urlpatterns = [
    path("", views.EventListView.as_view(), name="events_list"),
    path("<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("join/<int:pk>/", views.JoinEventView.as_view(), name="join"),
    path("add/", views.EventCreateView.as_view(), name="add_event"),
    path("edit/<int:pk>", views.EventUpdateView.as_view(), name="edit_event"),
    path("delete/<int:pk>", views.EventDeleteView.as_view(), name="delete_event"),
]
