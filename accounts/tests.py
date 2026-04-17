from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from accounts.forms import RegisterForm

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
