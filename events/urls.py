from django.urls import path

from events import views

app_name = "events"

urlpatterns = [
    path("", views.EventListView.as_view(), name="events_list"),
    path("<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("join/<int:pk>/", views.JoinEventView.as_view(), name="join"),
    path("leave/<int:pk>/", views.LeaveEventView.as_view(), name="leave"),
    path("add/", views.EventCreateView.as_view(), name="add_event"),
    path("edit/<int:pk>", views.EventUpdateView.as_view(), name="edit_event"),
    path("delete/<int:pk>", views.EventDeleteView.as_view(), name="delete_event"),
    path(
        "<int:event_pk>/remove/<int:reg_pk>/",
        views.RemoveParticipantView.as_view(),
        name="remove_participant",
    ),
    path(
        "<int:event_pk>/mark-present/<int:reg_pk>/",
        views.MarkPresentView.as_view(),
        name="mark_present",
    ),
]
