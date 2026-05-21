from django.urls import path

from venues import views

app_name = "venues"

urlpatterns = [
    path("", views.VenueListView.as_view(), name="venue_list"),
    path("dashboard/", views.VenueDashboardView.as_view(), name="dashboard"),
    path(
        "<int:venue_id>/availability/",
        views.VenueAvailabilityView.as_view(),
        name="venue_availability",
    ),
    path(
        "reservations/<int:pk>/cancel/",
        views.CancelReservationView.as_view(),
        name="cancel_reservation",
    ),
    path("<slug:slug>/", views.VenueDetailView.as_view(), name="venue_detail"),
]
