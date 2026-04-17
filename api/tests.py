from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from games.models import BoardGame, Genre

User = get_user_model()


class ApiTests(APITestCase):
    def setUp(self):
        result = Group.objects.get_or_create(name="Members")
        self.members_group = result[0]

        self.genre = Genre.objects.create(name="Strategy")
        self.game = BoardGame.objects.create(
            title="Catan",
            genre=self.genre,
            min_players=3,
            max_players=4,
        )

    def test_games_list_returns_200_for_anonymous_user(self):
        response = self.client.get("/api/games/")

        self.assertEqual(response.status_code, 200)

    def test_games_list_contains_game_title(self):
        response = self.client.get("/api/games/")

        self.assertContains(response, "Catan")

    def test_reviews_list_returns_200_for_anonymous_user(self):
        response = self.client.get("/api/reviews/")

        self.assertEqual(response.status_code, 200)

    def test_collections_requires_login(self):
        response = self.client.get("/api/collections/")

        self.assertEqual(response.status_code, 403)

    def test_current_user_requires_login(self):
        response = self.client.get("/api/users/me/")

        self.assertEqual(response.status_code, 403)
