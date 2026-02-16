from django.urls import path

from games import views

app_name = "games"

urlpatterns = [
    path("", views.get_all_games, name="games"),
    path("details/<int:pk>", views.get_game_details, name="game_details"),
    path("add/", views.add_game, name="add_game"),
    path("edit/<int:pk>", views.edit_game, name="edit_game"),
    path("delete/<int:pk>", views.delete_game, name="delete_game"),
]
