from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("", views.ReviewListView.as_view(), name="reviews_list"),
    path("<int:pk>/", views.ReviewDetailView.as_view(), name="review_detail"),
    path(
        "game/<int:game_pk>/create/",
        views.ReviewCreateView.as_view(),
        name="create_review",
    ),
    path("<int:pk>/edit/", views.ReviewUpdateView.as_view(), name="edit_review"),
    path("<int:pk>/delete/", views.ReviewDeleteView.as_view(), name="delete_review"),
]
