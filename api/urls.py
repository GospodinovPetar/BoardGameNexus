from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import views

app_name = "api"

urlpatterns = [
    path("games/search/", views.BoardGameSearchView.as_view(), name="game_search"),
    path(
        "games/recommended/",
        views.BoardGameRecommendedView.as_view(),
        name="game_recommended",
    ),
    path("games/ensure/", views.BoardGameEnsureView.as_view(), name="game_ensure"),
    path(
        "venues/<int:venue_id>/games/",
        views.VenueGamesListView.as_view(),
        name="venue_games",
    ),
    path(
        "venues/<int:venue_id>/recommended-games/",
        views.VenueRecommendedGamesView.as_view(),
        name="venue_recommended_games",
    ),
    path("events/", views.EventListCreateView.as_view(), name="event_list"),
    path("events/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("reviews/", views.GameReviewListCreateView.as_view(), name="review_list"),
    path(
        "reviews/<int:pk>/",
        views.GameReviewDetailView.as_view(),
        name="review_detail",
    ),
    path(
        "collections/",
        views.UserCollectionListCreateView.as_view(),
        name="collection_list",
    ),
    path(
        "collections/<int:pk>/",
        views.UserCollectionDetailView.as_view(),
        name="collection_detail",
    ),
    path("users/me/", views.CurrentUserView.as_view(), name="current_user"),
    path("auth/token/", obtain_auth_token, name="obtain_token"),
]
