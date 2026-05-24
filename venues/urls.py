from django.urls import path

from reviews import views as review_views

from venues import views

app_name = "venues"

urlpatterns = [
    path("", views.VenueListView.as_view(), name="venue_list"),
    path("add/", views.VenueCreateView.as_view(), name="add_venue"),
    path("edit/<slug:slug>/", views.VenueUpdateView.as_view(), name="edit_venue"),
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
    path(
        "<slug:slug>/reviews/",
        review_views.VenueReviewListView.as_view(),
        name="venue_review_list",
    ),
    path(
        "<slug:slug>/reviews/create/",
        review_views.VenueReviewCreateView.as_view(),
        name="venue_review_create",
    ),
    path("<slug:slug>/", views.VenueDetailView.as_view(), name="venue_detail"),
]
