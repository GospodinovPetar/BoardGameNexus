from django.urls import path

from games import views

app_name = "games"

urlpatterns = [
    path("", views.GameListView.as_view(), name="games"),
    path("details/<int:pk>", views.GameDetailView.as_view(), name="game_details"),
    path("add/", views.GameCreateView.as_view(), name="add_game"),
    path("edit/<int:pk>", views.GameUpdateView.as_view(), name="edit_game"),
    path("delete/<int:pk>", views.GameDeleteView.as_view(), name="delete_game"),
]
