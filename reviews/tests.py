from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from games.models import BoardGame, Genre
from reviews.forms import ReviewForm
from reviews.models import GameReview

User = get_user_model()


class ReviewsTests(TestCase):
    def setUp(self):
        group = Group.objects.get_or_create(name="Members")
        self.members_group = group[0]
        group = Group.objects.get_or_create(name="Moderators")
        self.moderators_group = group[0]

        self.genre = Genre.objects.create(name="Eurogame")
        self.game = BoardGame.objects.create(
            title="Brass: Birmingham",
            genre=self.genre,
            min_players=2,
            max_players=4,
        )

    def test_review_str_contains_author_and_game_title(self):
        user = User.objects.create_user(
            username="dana",
            email="dana@test.com",
            password="StrongPass12345!",
        )
        review = GameReview.objects.create(
            game=self.game,
            author=user,
            title="Fantastic",
            content="Loved it.",
            rating=5,
        )

        self.assertIn(user.username, str(review))
        self.assertIn(self.game.title, str(review))

    def test_unique_together_prevents_second_review_for_same_game(self):
        user = User.objects.create_user(
            username="erin",
            email="erin@test.com",
            password="StrongPass12345!",
        )
        GameReview.objects.create(
            game=self.game,
            author=user,
            title="First",
            content="First review.",
            rating=4,
        )

        with self.assertRaises(IntegrityError):
            GameReview.objects.create(
                game=self.game,
                author=user,
                title="Second",
                content="Second review.",
                rating=3,
            )

    def test_review_form_rejects_rating_of_zero(self):
        form = ReviewForm(
            data={
                "title": "Bad rating",
                "content": "Nope",
                "rating": 0,
            }
        )

        self.assertFalse(form.is_valid())

    def test_create_review_view_redirects_anonymous_user(self):
        response = self.client.get(
            reverse("reviews:create_review", kwargs={"game_pk": self.game.pk})
        )

        self.assertEqual(response.status_code, 302)

    def test_create_review_view_returns_200_for_logged_in_user(self):
        user = User.objects.create_user(
            username="frank",
            email="frank@test.com",
            password="StrongPass12345!",
        )
        logged_in = self.client.login(username="frank", password="StrongPass12345!")
        self.assertTrue(logged_in)

        response = self.client.get(
            reverse("reviews:create_review", kwargs={"game_pk": self.game.pk})
        )

        self.assertEqual(response.status_code, 200)
