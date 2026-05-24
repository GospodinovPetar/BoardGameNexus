from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APITestCase

from games.services.cache import set_stale_search_cache
from games.test_utils import create_test_boardgame

User = get_user_model()


class ApiTests(APITestCase):
    def setUp(self):
        result = Group.objects.get_or_create(name="Members")
        self.members_group = result[0]
        cache.clear()
        self.game = create_test_boardgame()

    def test_game_search_returns_stale_header_when_cached(self):
        stale = [{"bgg_id": 13, "title": "Catan", "year_published": 1995}]
        set_stale_search_cache("catan", stale)
        with patch(
            "games.services.bgg._fetch_search_results",
            side_effect=__import__("games.services.bgg", fromlist=["BGGError"]).BGGError(
                "unavailable"
            ),
        ):
            response = self.client.get("/api/games/search/", {"q": "catan"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-BGG-Cache"], "stale")
        self.assertEqual(response.data[0]["title"], "Catan")

    def test_reviews_list_returns_200_for_anonymous_user(self):
        response = self.client.get("/api/reviews/")

        self.assertEqual(response.status_code, 200)

    def test_collections_requires_login(self):
        response = self.client.get("/api/collections/")

        self.assertEqual(response.status_code, 403)

    def test_current_user_requires_login(self):
        response = self.client.get("/api/users/me/")

        self.assertEqual(response.status_code, 403)

    @patch("games.services.bgg.ensure_boardgames")
    def test_game_ensure_creates_local_cache(self, mock_ensure):
        user = User.objects.create_user(
            username="apiuser",
            email="api@test.com",
            password="StrongPass12345!",
        )
        self.client.force_authenticate(user=user)
        mock_ensure.return_value = [
            create_test_boardgame(bgg_id=9209, title="Ticket to Ride"),
        ]
        response = self.client.post(
            "/api/games/ensure/",
            {"bgg_ids": [9209]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["title"], "Ticket to Ride")

    @patch("games.services.bgg.fetch_boardgames_stats_batch")
    def test_venue_recommended_games_endpoint(self, mock_batch):
        from venues.tests import make_venue

        mock_batch.return_value = [
            {
                "bgg_id": self.game.bgg_id,
                "title": self.game.title,
                "year_published": self.game.year_published,
                "image_url": self.game.image_url,
                "bgg_url": self.game.bgg_url,
                "bgg_rank": 10,
                "bgg_rating": 8.0,
            }
        ]
        venue = make_venue(slug="api-venue-rec")
        venue.games.add(self.game)
        response = self.client.get(f"/api/venues/{venue.pk}/recommended-games/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["bgg_id"], self.game.bgg_id)
