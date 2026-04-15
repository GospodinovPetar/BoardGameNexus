from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from . import views

app_name = "api"

urlpatterns = [
    path("genres/", views.GenreListView.as_view(), name="genre_list"),
    path("games/", views.BoardGameListCreateView.as_view(), name="game_list"),
    path("games/<int:pk>/", views.BoardGameDetailView.as_view(), name="game_detail"),
    path("events/", views.EventListCreateView.as_view(), name="event_list"),
    path("events/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("reviews/", views.GameReviewListCreateView.as_view(), name="review_list"),
    path(
        "reviews/<int:pk>/", views.GameReviewDetailView.as_view(), name="review_detail"
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
