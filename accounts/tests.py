from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.forms import RegisterForm
from events.models import Event, EventRegistration
from games.models import BoardGame, Genre
from reviews.models import GameReview

User = get_user_model()


class AccountsTests(TestCase):
    def setUp(self):
        group = Group.objects.get_or_create(name="Members")
        self.members_group = group[0]
        group = Group.objects.get_or_create(name="Moderators")
        self.moderators_group = group[0]

    def test_user_str_returns_username(self):
        user = User.objects.create_user(
            username="alice",
            email="alice@test.com",
            password="StrongPass12345!",
        )

        self.assertEqual(str(user), user.username)

    def test_signal_creates_profile_on_user_creation(self):
        user = User.objects.create_user(
            username="bob",
            email="bob@test.com",
            password="StrongPass12345!",
        )

        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.games_played, 0)

    def test_register_form_valid_with_correct_data(self):
        form = RegisterForm(
            data={
                "username": "charlie",
                "email": "charlie@test.com",
                "password1": "StrongPass12345!",
                "password2": "StrongPass12345!",
            }
        )

        self.assertTrue(form.is_valid())

    def test_register_form_rejects_duplicate_email(self):
        User.objects.create_user(
            username="taken",
            email="taken@test.com",
            password="StrongPass12345!",
        )

        form = RegisterForm(
            data={
                "username": "newuser",
                "email": "taken@test.com",
                "password1": "StrongPass12345!",
                "password2": "StrongPass12345!",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_register_view_get_returns_200(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_profile_view_redirects_anonymous_user(self):
        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 302)


class PasswordResetAndChangeTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name="Members")
        self.user = User.objects.create_user(
            username="pwflow",
            email="pwflow@test.com",
            password="StrongPass12345!",
        )

    def test_password_reset_posts_email_when_user_exists(self):
        mail.outbox.clear()
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": self.user.email},
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], self.user.email)

    def test_password_change_redirects_anonymous_to_login(self):
        response = self.client.get(reverse("accounts:password_change"))
        self.assertRedirects(
            response,
            "/accounts/login/?next=/accounts/password-change/",
        )


class PublicProfilePlayedGamesOnlyTest(TestCase):
    def test_foreign_profile_shows_only_played_games_summary(self):
        group = Group.objects.get_or_create(name="Members")[0]
        target = User.objects.create_user(
            username="gamer",
            email="gamer@test.com",
            password="StrongPass12345!",
        )
        target.groups.add(group)
        viewer = User.objects.create_user(
            username="viewerx",
            email="viewerx@test.com",
            password="StrongPass12345!",
        )
        viewer.groups.add(group)
        genre = Genre.objects.create(name="Strategy")
        game = BoardGame.objects.create(
            title="Azul",
            genre=genre,
            min_players=2,
            max_players=4,
            release_date=timezone.now().date(),
        )
        organizer = User.objects.create_user(
            username="orgx",
            email="orgx@test.com",
            password="StrongPass12345!",
        )
        organizer.groups.add(group)
        past = Event.objects.create(
            name="Night session",
            description="Test",
            date_time=timezone.now() - timezone.timedelta(days=1),
            end_time=timezone.now() - timezone.timedelta(days=1, hours=-2),
            location="Cafe",
            organizer_name="Org",
            organizer=organizer,
            current_players=2,
            max_players=4,
        )
        past.games.add(game)
        EventRegistration.objects.create(event=past, user=target)
        EventRegistration.objects.create(
            event=past,
            user=viewer,
            status=EventRegistration.STATUS_PRESENT,
        )
        GameReview.objects.create(
            author=target,
            game=game,
            title="Great",
            rating=5,
            content="Nice game.",
        )

        self.client.login(username="viewerx", password="StrongPass12345!")
        response = self.client.get(
            reverse("accounts:public_profile", args=[target.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_foreign_profile"])
        sessions = list(response.context["played_sessions"])
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].player_count, 2)
        self.assertEqual(list(response.context["reviews"]), [])
        self.assertEqual(list(response.context["collections"]), [])
