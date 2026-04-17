from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from games.forms import GameForm
from games.models import BoardGame, Genre

User = get_user_model()


class GamesTests(TestCase):
    def setUp(self):
        group = Group.objects.get_or_create(name="Members")
        self.members_group = group[0]
        group = Group.objects.get_or_create(name="Moderators")
        self.moderators_group = group[0]

    def test_boardgame_str_returns_title(self):
        genre = Genre.objects.create(name="Strategy")
        game = BoardGame.objects.create(
            title="Terraforming Mars",
            genre=genre,
            min_players=1,
            max_players=5,
        )

        self.assertEqual(str(game), game.title)

    def test_game_list_returns_200_for_anonymous_user(self):
        response = self.client.get(reverse("games:games"))

        self.assertEqual(response.status_code, 200)

    def test_game_detail_returns_404_for_nonexistent_pk(self):
        response = self.client.get(reverse("games:game_details", kwargs={"pk": 99999}))

        self.assertEqual(response.status_code, 404)

    def test_game_create_view_requires_moderator_group(self):
        user = User.objects.create_user(
            username="regular",
            email="regular@test.com",
            password="StrongPass12345!",
        )
        logged_in = self.client.login(username="regular", password="StrongPass12345!")
        self.assertTrue(logged_in)

        response = self.client.get(reverse("games:add_game"))

        self.assertEqual(response.status_code, 403)

    def test_game_form_rejects_min_players_greater_than_max_players(self):
        genre = Genre.objects.create(name="Co-op")
        form = GameForm(
            data={
                "title": "Pandemic",
                "genre": genre.pk,
                "min_players": 6,
                "max_players": 2,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("min_players", form.errors)
