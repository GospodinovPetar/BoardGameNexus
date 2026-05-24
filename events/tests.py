from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event, EventRegistration
from events.visibility import can_view_event, event_is_cancelled, filter_public_events
from events.views import _apply_no_show_penalties, get_suggested_events
from games.models import BoardGame
from games.test_utils import create_test_boardgame
from venues.models import Venue, VenueReservation

User = get_user_model()


def make_event(organizer=None, days_ahead=1, max_players=4, current_players=0, **kwargs):
    date_time = kwargs.pop(
        "date_time",
        timezone.now() + timezone.timedelta(days=days_ahead),
    )
    end_time = kwargs.pop("end_time", date_time + timezone.timedelta(hours=2))
    event = Event.objects.create(
        name=kwargs.get("name", "Test Event"),
        description="A fun test event.",
        date_time=date_time,
        end_time=end_time,
        location=kwargs.get("location", "Test Hall"),
        organizer_name=organizer.username if organizer else "Organizer",
        organizer=organizer,
        venue=kwargs.get("venue"),
        current_players=current_players,
        max_players=max_players,
    )
    return event


def make_user(username="testuser", **kwargs):
    return User.objects.create_user(username=username, password="password", **kwargs)


class EventModelTest(TestCase):
    def test_has_free_spots_when_not_full(self):
        organizer = make_user("org")
        event = make_event(organizer=organizer, current_players=2, max_players=4)
        self.assertTrue(event.has_free_spots())

    def test_has_free_spots_when_full(self):
        organizer = make_user("org")
        event = make_event(organizer=organizer, current_players=4, max_players=4)
        self.assertFalse(event.has_free_spots())

    def test_attendance_window_open(self):
        organizer = make_user("org")
        event = make_event(organizer=organizer)
        event.date_time = timezone.now() - timezone.timedelta(minutes=30)
        event.save()
        self.assertTrue(event.attendance_window_open())

    def test_attendance_window_closed(self):
        organizer = make_user("org")
        event = make_event(organizer=organizer)
        event.date_time = timezone.now() - timezone.timedelta(hours=2)
        event.save()
        self.assertTrue(event.attendance_window_closed())

    def test_attendance_window_not_open_before_event(self):
        organizer = make_user("org")
        event = make_event(organizer=organizer)
        self.assertFalse(event.attendance_window_open())

    def test_active_registration_count(self):
        organizer = make_user("org")
        event = make_event(organizer=organizer, max_players=4)
        u1 = make_user("u1")
        u2 = make_user("u2")
        u3 = make_user("u3")
        EventRegistration.objects.create(event=event, user=u1, status=EventRegistration.STATUS_REGISTERED)
        EventRegistration.objects.create(event=event, user=u2, status=EventRegistration.STATUS_PRESENT)
        EventRegistration.objects.create(event=event, user=u3, status=EventRegistration.STATUS_REMOVED)
        self.assertEqual(event.active_registration_count(), 2)


class JoinEventViewTest(TestCase):
    def setUp(self):
        self.organizer = make_user("org")
        self.user = make_user("player")
        self.event = make_event(organizer=self.organizer, max_players=3, current_players=0)

    def test_join_creates_registration(self):
        self.client.login(username="player", password="password")
        response = self.client.post(reverse("events:join", args=[self.event.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            EventRegistration.objects.filter(
                event=self.event, user=self.user
            ).exists()
        )

    def test_join_increments_current_players(self):
        self.client.login(username="player", password="password")
        self.client.post(reverse("events:join", args=[self.event.pk]))
        self.event.refresh_from_db()
        self.assertEqual(self.event.current_players, 1)

    def test_join_duplicate_prevented(self):
        self.client.login(username="player", password="password")
        self.client.post(reverse("events:join", args=[self.event.pk]))
        self.client.post(reverse("events:join", args=[self.event.pk]))
        count = EventRegistration.objects.filter(event=self.event, user=self.user).count()
        self.assertEqual(count, 1)

    def test_join_respects_capacity(self):
        u1 = make_user("u1")
        u2 = make_user("u2")
        u3 = make_user("u3")
        EventRegistration.objects.create(event=self.event, user=u1)
        EventRegistration.objects.create(event=self.event, user=u2)
        EventRegistration.objects.create(event=self.event, user=u3)
        self.event.current_players = 3
        self.event.save()

        self.client.login(username="player", password="password")
        self.client.post(reverse("events:join", args=[self.event.pk]))
        self.assertFalse(
            EventRegistration.objects.filter(event=self.event, user=self.user).exists()
        )

    def test_removed_user_cannot_rejoin(self):
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            status=EventRegistration.STATUS_REMOVED,
        )
        self.client.login(username="player", password="password")
        self.client.post(reverse("events:join", args=[self.event.pk]))
        count = EventRegistration.objects.filter(event=self.event, user=self.user).count()
        self.assertEqual(count, 1)

    def test_unauthenticated_join_redirects(self):
        response = self.client.post(reverse("events:join", args=[self.event.pk]))
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/events/join/{self.event.pk}/",
        )


class LeaveEventViewTest(TestCase):
    def setUp(self):
        self.organizer = make_user("leave_org")
        self.player = make_user("leave_player")
        self.event = make_event(organizer=self.organizer, max_players=5, current_players=0)

    def test_leave_removes_registration_and_updates_count(self):
        self.client.login(username="leave_player", password="password")
        self.client.post(reverse("events:join", args=[self.event.pk]))
        self.event.refresh_from_db()
        self.assertEqual(self.event.current_players, 1)

        response = self.client.post(reverse("events:leave", args=[self.event.pk]))
        self.assertRedirects(response, reverse("events:event_detail", args=[self.event.pk]))

        reg = EventRegistration.objects.get(event=self.event, user=self.player)
        self.assertEqual(reg.status, EventRegistration.STATUS_REMOVED)

        self.event.refresh_from_db()
        self.assertEqual(self.event.current_players, 0)

    def test_leave_when_not_registered_warns(self):
        self.client.login(username="leave_player", password="password")
        response = self.client.post(reverse("events:leave", args=[self.event.pk]))
        self.assertRedirects(response, reverse("events:event_detail", args=[self.event.pk]))

    def test_leave_after_event_started_blocked(self):
        self.event.date_time = timezone.now() - timezone.timedelta(minutes=5)
        self.event.save(update_fields=["date_time"])

        EventRegistration.objects.create(
            event=self.event,
            user=self.player,
            status=EventRegistration.STATUS_REGISTERED,
        )

        self.client.login(username="leave_player", password="password")
        response = self.client.post(reverse("events:leave", args=[self.event.pk]))
        self.assertRedirects(response, reverse("events:event_detail", args=[self.event.pk]))

        reg = EventRegistration.objects.get(event=self.event, user=self.player)
        self.assertEqual(reg.status, EventRegistration.STATUS_REGISTERED)

    def test_unauthenticated_leave_redirects(self):
        response = self.client.post(reverse("events:leave", args=[self.event.pk]))
        self.assertRedirects(
            response,
            f"/accounts/login/?next=/events/leave/{self.event.pk}/",
        )


class GetSuggestedEventsTest(TestCase):
    def setUp(self):
        self.organizer = make_user("sug_org")
        self.user = make_user("sug_player")
        self.game = create_test_boardgame(bgg_id=13, title="Catan")

    def _make_past_event_with_registration(self):
        past = make_event(organizer=self.organizer, days_ahead=-20, name="Past Meetup")
        past.games.add(self.game)
        EventRegistration.objects.create(
            event=past,
            user=self.user,
            status=EventRegistration.STATUS_REGISTERED,
        )
        return past

    def test_anonymous_returns_empty(self):
        self.assertEqual(list(get_suggested_events(AnonymousUser())), [])

    def test_no_past_registrations_returns_empty(self):
        make_event(organizer=self.organizer, days_ahead=7, name="Future Only")
        self.assertEqual(list(get_suggested_events(self.user)), [])

    def test_suggests_upcoming_with_matching_game_and_match_count(self):
        self._make_past_event_with_registration()
        upcoming = make_event(
            organizer=self.organizer, days_ahead=14, name="Suggested Meetup"
        )
        upcoming.games.add(self.game)

        suggestions = list(get_suggested_events(self.user))
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].pk, upcoming.pk)
        self.assertEqual(suggestions[0].match_count, 1)

    def test_excludes_events_user_already_joined(self):
        self._make_past_event_with_registration()
        upcoming = make_event(
            organizer=self.organizer, days_ahead=14, name="Already In"
        )
        upcoming.games.add(self.game)
        EventRegistration.objects.create(
            event=upcoming,
            user=self.user,
            status=EventRegistration.STATUS_REGISTERED,
        )

        self.assertEqual(list(get_suggested_events(self.user)), [])

    def test_event_list_context_has_suggested_for_authenticated(self):
        self._make_past_event_with_registration()
        upcoming = make_event(
            organizer=self.organizer, days_ahead=14, name="On List"
        )
        upcoming.games.add(self.game)

        self.client.login(username="sug_player", password="password")
        response = self.client.get(reverse("events:events_list"))
        self.assertEqual(response.status_code, 200)
        suggested = list(response.context["suggested_events"])
        self.assertEqual(len(suggested), 1)
        self.assertEqual(suggested[0].pk, upcoming.pk)

    def test_event_list_context_empty_suggested_when_anonymous(self):
        response = self.client.get(reverse("events:events_list"))
        self.assertFalse(response.context["suggested_events"].exists())


class EventDetailViewContextTest(TestCase):
    def setUp(self):
        self.organizer = make_user("org")
        self.player = make_user("player")
        self.event = make_event(organizer=self.organizer, max_players=4, current_players=0)

    def test_organizer_sees_management_panel(self):
        self.client.login(username="org", password="password")
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertTrue(response.context["is_organizer"])

    def test_non_organizer_does_not_see_management_panel(self):
        self.client.login(username="player", password="password")
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertFalse(response.context["is_organizer"])

    def test_anonymous_does_not_see_management_panel(self):
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertFalse(response.context["is_organizer"])

    def test_user_registration_context_populated(self):
        EventRegistration.objects.create(event=self.event, user=self.player)
        self.client.login(username="player", password="password")
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertIsNotNone(response.context["user_registration"])

    def test_user_registration_none_when_not_joined(self):
        self.client.login(username="player", password="password")
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertIsNone(response.context["user_registration"])


class RemoveParticipantViewTest(TestCase):
    def setUp(self):
        self.organizer = make_user("org")
        self.player = make_user("player")
        self.other = make_user("other")
        self.event = make_event(organizer=self.organizer, max_players=4, current_players=1)
        self.reg = EventRegistration.objects.create(
            event=self.event,
            user=self.player,
            status=EventRegistration.STATUS_REGISTERED,
        )

    def _remove_url(self):
        return reverse("events:remove_participant", args=[self.event.pk, self.reg.pk])

    def test_organizer_can_remove_participant(self):
        self.client.login(username="org", password="password")
        response = self.client.post(self._remove_url())
        self.assertRedirects(response, reverse("events:event_detail", args=[self.event.pk]))
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, EventRegistration.STATUS_REMOVED)

    def test_non_organizer_cannot_remove(self):
        self.client.login(username="other", password="password")
        self.client.post(self._remove_url())
        self.reg.refresh_from_db()
        self.assertNotEqual(self.reg.status, EventRegistration.STATUS_REMOVED)

    def test_moderator_cannot_remove_without_being_organizer(self):
        from django.contrib.auth.models import Group

        Group.objects.get_or_create(name="Moderators")
        mod = make_user("mod")
        mod.groups.add(Group.objects.get(name="Moderators"))
        self.client.login(username="mod", password="password")
        self.client.post(self._remove_url())
        self.reg.refresh_from_db()
        self.assertNotEqual(self.reg.status, EventRegistration.STATUS_REMOVED)

    def test_remove_decrements_current_players(self):
        self.client.login(username="org", password="password")
        self.client.post(self._remove_url())
        self.event.refresh_from_db()
        self.assertEqual(self.event.current_players, 0)

    def test_organizer_cannot_remove_participant_from_other_event(self):
        """Hard safety check: organizer of Event A must not remove registrations from Event B."""
        other_organizer = make_user("org2")
        other_event = make_event(organizer=other_organizer, max_players=4, current_players=1, name="Other Event")
        other_reg = EventRegistration.objects.create(
            event=other_event,
            user=self.player,
            status=EventRegistration.STATUS_REGISTERED,
        )

        # Try to remove a registration that belongs to a different event_pk.
        self.client.login(username="org", password="password")
        resp = self.client.post(
            reverse("events:remove_participant", args=[self.event.pk, other_reg.pk])
        )
        self.assertEqual(resp.status_code, 404)
        other_reg.refresh_from_db()
        self.assertEqual(other_reg.status, EventRegistration.STATUS_REGISTERED)


class MarkPresentViewTest(TestCase):
    def setUp(self):
        self.organizer = make_user("org")
        self.player = make_user("player")
        self.event = make_event(organizer=self.organizer, max_players=4, current_players=1)
        self.reg = EventRegistration.objects.create(
            event=self.event,
            user=self.player,
            status=EventRegistration.STATUS_REGISTERED,
        )

    def _mark_url(self):
        return reverse("events:mark_present", args=[self.event.pk, self.reg.pk])

    def _set_event_time(self, minutes_ago):
        self.event.date_time = timezone.now() - timezone.timedelta(minutes=minutes_ago)
        self.event.save()

    def test_mark_present_during_window(self):
        self._set_event_time(30)
        self.client.login(username="org", password="password")
        self.client.post(self._mark_url())
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, EventRegistration.STATUS_PRESENT)

    def test_mark_present_before_window(self):
        """Event hasn't started yet — window is not open."""
        self.client.login(username="org", password="password")
        self.client.post(self._mark_url())
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, EventRegistration.STATUS_REGISTERED)

    def test_mark_present_after_window_closed(self):
        self._set_event_time(120)
        self.client.login(username="org", password="password")
        self.client.post(self._mark_url())
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, EventRegistration.STATUS_REGISTERED)

    def test_non_organizer_cannot_mark_present(self):
        self._set_event_time(30)
        other = make_user("other")
        self.client.login(username="other", password="password")
        self.client.post(self._mark_url())
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.status, EventRegistration.STATUS_REGISTERED)


class NoShowPenaltyTest(TestCase):
    def setUp(self):
        self.organizer = make_user("org")
        self.player = make_user("player")
        self.event = make_event(organizer=self.organizer, max_players=4, current_players=1)
        self.event.date_time = timezone.now() - timezone.timedelta(hours=2)
        self.event.save()
        self.reg = EventRegistration.objects.create(
            event=self.event,
            user=self.player,
            status=EventRegistration.STATUS_REGISTERED,
        )

    def test_no_show_strike_assigned_after_window(self):
        _apply_no_show_penalties(self.event)
        self.reg.refresh_from_db()
        self.player.refresh_from_db()
        self.assertEqual(self.reg.status, EventRegistration.STATUS_NO_SHOW)
        self.assertEqual(self.player.no_show_strikes, 1)

    def test_no_show_strike_not_applied_before_window(self):
        self.event.date_time = timezone.now() + timezone.timedelta(days=1)
        self.event.save()
        _apply_no_show_penalties(self.event)
        self.reg.refresh_from_db()
        self.player.refresh_from_db()
        self.assertEqual(self.reg.status, EventRegistration.STATUS_REGISTERED)
        self.assertEqual(self.player.no_show_strikes, 0)

    def test_no_show_applied_only_once(self):
        _apply_no_show_penalties(self.event)
        _apply_no_show_penalties(self.event)
        self.player.refresh_from_db()
        self.assertEqual(self.player.no_show_strikes, 1)

    def test_present_player_not_penalised(self):
        self.reg.status = EventRegistration.STATUS_PRESENT
        self.reg.save()
        _apply_no_show_penalties(self.event)
        self.player.refresh_from_db()
        self.assertEqual(self.player.no_show_strikes, 0)

    def test_no_show_triggered_on_event_detail_visit(self):
        self.client.login(username="org", password="password")
        self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.reg.refresh_from_db()
        self.player.refresh_from_db()
        self.assertEqual(self.reg.status, EventRegistration.STATUS_NO_SHOW)
        self.assertEqual(self.player.no_show_strikes, 1)


class EventCRUDPermissionsTest(TestCase):
    def setUp(self):
        self.organizer = make_user("org")
        self.other = make_user("other")
        self.event = make_event(organizer=self.organizer, days_ahead=3, max_players=4)

    def test_organizer_can_reach_edit_page(self):
        self.client.login(username="org", password="password")
        response = self.client.get(reverse("events:edit_event", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)

    def test_non_organizer_blocked_from_edit(self):
        self.client.login(username="other", password="password")
        response = self.client.get(reverse("events:edit_event", args=[self.event.pk]))
        self.assertEqual(response.status_code, 403)

    def test_organizer_can_reach_delete_page(self):
        self.client.login(username="org", password="password")
        response = self.client.get(reverse("events:delete_event", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)

    def test_non_organizer_blocked_from_delete(self):
        self.client.login(username="other", password="password")
        response = self.client.get(reverse("events:delete_event", args=[self.event.pk]))
        self.assertEqual(response.status_code, 403)

    def test_create_event_sets_organizer(self):
        self.client.login(username="other", password="password")
        game = create_test_boardgame(bgg_id=171, title="Chess", min_players=2, max_players=2)
        response = self.client.post(
            reverse("events:add_event"),
            {
                "name": "New Event",
                "description": "Desc",
                "date_time": (timezone.now() + timezone.timedelta(days=5)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "end_time": (timezone.now() + timezone.timedelta(days=5, hours=2)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "location": "Library",
                "organizer_name": "Fake Name",
                "current_players": 1,
                "max_players": 4,
                "games": [game.pk],
            },
        )
        event = Event.objects.filter(name="New Event").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.organizer, self.other)
        self.assertEqual(event.organizer_name, self.other.username)


class PublicProfileViewTest(TestCase):
    def setUp(self):
        self.viewer = make_user("viewer")
        self.target = make_user("target")

    def test_authenticated_user_can_view_profile(self):
        self.client.login(username="viewer", password="password")
        response = self.client.get(
            reverse("accounts:public_profile", args=[self.target.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["profile_user"], self.target)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(
            reverse("accounts:public_profile", args=[self.target.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_nonexistent_user_returns_404(self):
        self.client.login(username="viewer", password="password")
        response = self.client.get(
            reverse("accounts:public_profile", args=[99999])
        )
        self.assertEqual(response.status_code, 404)


class PastEventVisibilityTest(TestCase):
    def setUp(self):
        self.organizer = make_user("past_org")
        self.player = make_user("past_player")
        self.stranger = make_user("stranger")
        self.event = make_event(
            organizer=self.organizer, days_ahead=-1, name="Already Gone"
        )

    def test_past_event_not_on_public_list(self):
        future = make_event(organizer=self.organizer, days_ahead=7, name="Still Coming")
        response = self.client.get(reverse("events:events_list"))
        self.assertEqual(response.status_code, 200)
        listed_ids = [e.pk for e in response.context["events"]]
        self.assertNotIn(self.event.pk, listed_ids)
        self.assertIn(future.pk, listed_ids)

    def test_anonymous_cannot_view_past_event_detail(self):
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertEqual(response.status_code, 404)

    def test_stranger_cannot_view_past_event_detail(self):
        self.client.login(username="stranger", password="password")
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertEqual(response.status_code, 404)

    def test_participant_can_view_past_event_detail(self):
        EventRegistration.objects.create(event=self.event, user=self.player)
        self.client.login(username="past_player", password="password")
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_past_event"])
        self.assertGreaterEqual(len(response.context["fellow_participants"]), 1)

    def test_no_show_can_view_past_event_detail(self):
        EventRegistration.objects.create(
            event=self.event,
            user=self.player,
            status=EventRegistration.STATUS_NO_SHOW,
        )
        self.client.login(username="past_player", password="password")
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)

    def test_removed_participant_cannot_view_past_event_detail(self):
        EventRegistration.objects.create(
            event=self.event,
            user=self.player,
            status=EventRegistration.STATUS_REMOVED,
        )
        self.client.login(username="past_player", password="password")
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertEqual(response.status_code, 404)

    def test_organizer_can_view_past_event_detail(self):
        self.client.login(username="past_org", password="password")
        response = self.client.get(reverse("events:event_detail", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)

    def test_join_past_event_redirects_to_list(self):
        self.client.login(username="stranger", password="password")
        response = self.client.post(reverse("events:join", args=[self.event.pk]))
        self.assertRedirects(response, reverse("events:events_list"))

    def test_participant_sees_event_in_profile_history(self):
        EventRegistration.objects.create(event=self.event, user=self.player)
        self.client.login(username="past_player", password="password")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        past = list(response.context["past_events"])
        self.assertEqual(len(past), 1)
        self.assertEqual(past[0].pk, self.event.pk)

    def test_organizer_sees_past_event_in_profile_history(self):
        self.client.login(username="past_org", password="password")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        past = list(response.context["past_events"])
        self.assertEqual(len(past), 1)
        self.assertEqual(past[0].pk, self.event.pk)


class ProfileMyEventsTest(TestCase):
    def setUp(self):
        self.user = make_user("myevents")
        self.client.login(username="myevents", password="password")
        start = timezone.now() + timezone.timedelta(days=2)
        self.organized = make_event(
            organizer=self.user,
            name="My Organized",
            date_time=start,
            end_time=start + timezone.timedelta(hours=2),
        )
        other = make_user("otherorg")
        joined_event = make_event(organizer=other, name="Joined Event")
        EventRegistration.objects.create(event=joined_event, user=self.user)

    def test_profile_has_my_events_context(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        organized = list(response.context["upcoming_organized_events"])
        joined = list(response.context["upcoming_joined_events"])
        self.assertEqual(len(organized), 1)
        self.assertEqual(organized[0].name, "My Organized")
        self.assertEqual(len(joined), 1)
        self.assertEqual(joined[0].name, "Joined Event")


class CancelledEventVisibilityTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group

        Group.objects.get_or_create(name="Members")
        self.organizer = make_user("organizer")
        self.participant = make_user("participant")
        self.other = make_user("other")
        self.venue = Venue.objects.create(
            name="Cafe",
            slug="cafe",
            address="1 St",
            city="Sofia",
            capacity=20,
            table_count=4,
        )
        self.event = make_event(
            organizer=self.organizer,
            venue=self.venue,
            name="Game Night",
            location=self.venue.display_location(),
        )
        self.reservation = VenueReservation.objects.create(
            venue=self.venue,
            event=self.event,
            requested_by=self.organizer,
            status=VenueReservation.STATUS_CONFIRMED,
        )
        EventRegistration.objects.create(
            event=self.event,
            user=self.participant,
            status=EventRegistration.STATUS_REGISTERED,
        )

    def _cancel_booking(self):
        self.reservation.status = VenueReservation.STATUS_CANCELLED
        self.reservation.save(update_fields=["status"])
        self.event.refresh_from_db()

    def test_cancelled_event_flag(self):
        self._cancel_booking()
        self.assertTrue(event_is_cancelled(self.event))

    def test_public_list_excludes_cancelled(self):
        self._cancel_booking()
        self.assertFalse(
            filter_public_events(Event.objects.all()).filter(pk=self.event.pk).exists()
        )

    def test_participant_can_view_cancelled_detail(self):
        self._cancel_booking()
        self.assertTrue(can_view_event(self.participant, self.event))

    def test_other_user_cannot_view_cancelled_detail(self):
        self._cancel_booking()
        self.assertFalse(can_view_event(self.other, self.event))

    def test_cancelled_event_in_profile_my_events_joined(self):
        self._cancel_booking()
        self.client.login(username="participant", password="password")
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "Game Night")
        self.assertContains(response, "Cancelled")

    def test_cancelled_event_not_on_public_events_page(self):
        self._cancel_booking()
        self.client.login(username="participant", password="password")
        response = self.client.get(reverse("events:events_list"))
        self.assertNotContains(response, "Game Night")
