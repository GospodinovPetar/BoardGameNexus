from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event
from games.models import BoardGame, Genre

User = get_user_model()


class EventsTests(TestCase):
    def test_event_has_free_spots_returns_true_when_not_full(self):
        event = Event.objects.create(
            name="Friday Night Games",
            description="Open gaming session.",
            date_time=timezone.now() + timezone.timedelta(days=1),
            location="Community Center",
            organizer_name="Organizer",
            current_players=2,
            max_players=4,
        )

        self.assertTrue(event.has_free_spots())

    def test_event_list_returns_200_for_anonymous_user(self):
        response = self.client.get(reverse("events:events_list"))

        self.assertEqual(response.status_code, 200)
