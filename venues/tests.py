from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event, EventRegistration
from venues.availability import (
    event_planned_headcount,
    get_venue_availability,
    guests_booked_for_interval,
    has_table_availability,
    has_venue_booking_availability,
    merge_contiguous_hour_slots,
)
from venues.forms import ReservationDashboardForm
from venues.models import Venue, VenueReservation
from venues.permissions import can_manage_reservation, is_venue_staff

User = get_user_model()


def make_user(username="user", **kwargs):
    return User.objects.create_user(username=username, password="password", **kwargs)


def make_venue(name="Game Cafe", **kwargs):
    defaults = {
        "name": name,
        "slug": kwargs.pop("slug", name.lower().replace(" ", "-")),
        "address": "1 Main St",
        "city": "Sofia",
        "capacity": 30,
        "is_active": True,
    }
    defaults.update(kwargs)
    return Venue.objects.create(**defaults)


def future_venue_slot(days_ahead=5, start_hour=14, duration_hours=2):
    base = timezone.localdate() + timedelta(days=days_ahead)
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(base, time(start_hour, 0)), tz)
    end_dt = start_dt + timedelta(hours=duration_hours)
    return start_dt, end_dt


def format_local_datetime(dt):
    local = timezone.localtime(dt)
    return local.strftime("%Y-%m-%dT%H:%M")


def venue_schedule_post_times(start, end):
    """POST fields for partner-venue schedule (date + time only)."""
    local_start = timezone.localtime(start)
    local_end = timezone.localtime(end)
    return {
        "event_date": local_start.date().isoformat(),
        "start_time": local_start.strftime("%H:%M"),
        "end_time_field": local_end.strftime("%H:%M"),
    }


def venue_schedule_post_slots(start, end):
    """POST fields with multi-hour slot selection."""
    from venues.availability import hour_slot_starts_in_range

    payload = venue_schedule_post_times(start, end)
    slots = list(hour_slot_starts_in_range(start, end))
    payload["venue_time_slots"] = ",".join(s.isoformat() for s in slots)
    return payload


def make_event(organizer=None, venue=None, **kwargs):
    if "date_time" in kwargs:
        date_time = kwargs["date_time"]
        end_time = kwargs.get("end_time", date_time + timedelta(hours=2))
    else:
        date_time, end_time = future_venue_slot(
            days_ahead=kwargs.pop("days_ahead", 5),
            start_hour=kwargs.pop("start_hour", 14),
            duration_hours=kwargs.pop("duration_hours", 2),
        )
    event = Event.objects.create(
        name=kwargs.get("name", "Board Night"),
        description="Fun evening",
        date_time=date_time,
        end_time=end_time,
        location=kwargs.get("location", "Independent Hall"),
        organizer_name=organizer.username if organizer else "Organizer",
        organizer=organizer,
        venue=venue,
        current_players=1,
        max_players=kwargs.get("max_players", 6),
    )
    return event


class VenueModelTest(TestCase):
    def test_full_address(self):
        venue = make_venue()
        self.assertEqual(venue.full_address, "1 Main St, Sofia")

    def test_auto_slug_on_save(self):
        venue = Venue(name="New Place", address="A", city="B", capacity=10)
        venue.save()
        self.assertEqual(venue.slug, "new-place")


class VenuePermissionsTest(TestCase):
    def setUp(self):
        self.staff_user = make_user("staff")
        self.other_user = make_user("other")
        self.venue = make_venue()
        self.venue.staff.add(self.staff_user)

    def test_staff_can_manage_reservation(self):
        organizer = make_user("org")
        event = make_event(organizer=organizer, venue=self.venue)
        reservation = VenueReservation.objects.create(
            venue=self.venue,
            event=event,
            requested_by=organizer,
        )
        self.assertTrue(is_venue_staff(self.staff_user, self.venue))
        self.assertFalse(is_venue_staff(self.other_user, self.venue))
        self.assertTrue(can_manage_reservation(self.staff_user, reservation))


class VenueListViewTest(TestCase):
    def test_lists_active_venues_only(self):
        make_venue(name="Active Cafe")
        make_venue(name="Closed Cafe", is_active=False, slug="closed-cafe")
        response = self.client.get(reverse("venues:venue_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Cafe")
        self.assertNotContains(response, "Closed Cafe")


class VenueDetailViewTest(TestCase):
    def test_venue_detail_page(self):
        venue = make_venue()
        response = self.client.get(reverse("venues:venue_detail", args=[venue.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, venue.name)


class EventCreateWithVenueTest(TestCase):
    def setUp(self):
        self.user = make_user("organizer")
        self.venue = make_venue(table_count=6)
        Group.objects.get_or_create(name="Members")
        self.client.login(username="organizer", password="password")

    def test_creating_event_with_venue_creates_confirmed_reservation(self):
        start, end = future_venue_slot()
        response = self.client.post(
            reverse("events:add_event"),
            {
                "name": "Venue Event",
                "organizer_name": "Organizer",
                "venue": self.venue.pk,
                "location": "",
                "current_players": 1,
                "max_players": 6,
                "description": "At a partner venue",
                **venue_schedule_post_times(start, end),
            },
        )
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(name="Venue Event")
        self.assertEqual(event.venue_id, self.venue.pk)
        self.assertEqual(event.location, self.venue.display_location())
        reservation = VenueReservation.objects.get(event=event)
        self.assertEqual(reservation.status, VenueReservation.STATUS_CONFIRMED)
        self.assertEqual(reservation.requested_by, self.user)

    def test_max_players_above_venue_cap_rejected(self):
        start, end = future_venue_slot(days_ahead=6)
        response = self.client.post(
            reverse("events:add_event"),
            {
                "name": "Too Many",
                "venue": self.venue.pk,
                "location": "",
                "current_players": 1,
                "max_players": 11,
                "description": "Test",
                **venue_schedule_post_times(start, end),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Event.objects.filter(name="Too Many").exists())

    def test_multi_hour_slots_merge_into_one_booking(self):
        start, _ = future_venue_slot(days_ahead=7, start_hour=14, duration_hours=1)
        end = start + timedelta(hours=2)
        response = self.client.post(
            reverse("events:add_event"),
            {
                "name": "Long Venue Night",
                "venue": self.venue.pk,
                "location": "",
                "current_players": 1,
                "max_players": 6,
                "description": "Two hours",
                **venue_schedule_post_slots(start, end),
            },
        )
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(name="Long Venue Night")
        self.assertEqual(timezone.localtime(event.date_time).hour, 14)
        self.assertEqual(timezone.localtime(event.end_time).hour, 16)
        self.assertEqual(VenueReservation.objects.get(event=event).tables_reserved, 1)

    def test_independent_location_still_works(self):
        start, end = future_venue_slot()
        response = self.client.post(
            reverse("events:add_event"),
            {
                "name": "Home Event",
                "organizer_name": "Should Be Ignored",
                "date_time": format_local_datetime(start),
                "end_time": format_local_datetime(end),
                "venue": "",
                "location": "My living room",
                "current_players": 1,
                "max_players": 8,
                "description": "Casual night",
            },
        )
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(name="Home Event")
        self.assertIsNone(event.venue_id)
        self.assertFalse(VenueReservation.objects.filter(event=event).exists())


class ReservationWorkflowTest(TestCase):
    def setUp(self):
        self.organizer = make_user("organizer")
        self.staff_user = make_user("staff")
        self.venue = make_venue()
        self.venue.staff.add(self.staff_user)
        self.event = make_event(organizer=self.organizer, venue=self.venue)
        self.reservation = VenueReservation.objects.create(
            venue=self.venue,
            event=self.event,
            requested_by=self.organizer,
            status=VenueReservation.STATUS_CONFIRMED,
        )

    def test_approve_url_removed(self):
        self.client.login(username="staff", password="password")
        response = self.client.post("/venues/reservations/99999/approve/")
        self.assertEqual(response.status_code, 404)

    def test_staff_can_cancel_reservation(self):
        self.client.login(username="staff", password="password")
        response = self.client.post(
            reverse("venues:cancel_reservation", args=[self.reservation.pk]),
            {"staff_note": "Venue maintenance"},
        )
        self.assertRedirects(response, reverse("venues:dashboard"))
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, VenueReservation.STATUS_CANCELLED)
        self.assertEqual(self.reservation.staff_note, "Venue maintenance")

    def test_non_staff_cannot_cancel(self):
        outsider = make_user("outsider")
        self.client.login(username="outsider", password="password")
        response = self.client.post(
            reverse("venues:cancel_reservation", args=[self.reservation.pk])
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, VenueReservation.STATUS_CONFIRMED)

    def test_organizer_can_cancel_reservation(self):
        self.client.login(username="organizer", password="password")
        response = self.client.post(
            reverse("venues:cancel_reservation", args=[self.reservation.pk])
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, VenueReservation.STATUS_CANCELLED)


class VenueDashboardTest(TestCase):
    def setUp(self):
        self.staff_user = make_user("staff")
        self.venue = make_venue()
        self.venue.staff.add(self.staff_user)
        organizer = make_user("org")
        event = make_event(organizer=organizer, venue=self.venue)
        VenueReservation.objects.create(
            venue=self.venue,
            event=event,
            requested_by=organizer,
        )

    def test_dashboard_requires_staff_access(self):
        outsider = make_user("outsider")
        self.client.login(username="outsider", password="password")
        response = self.client.get(reverse("venues:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_shows_reservations_for_staff(self):
        event = Event.objects.get(name="Board Night")
        on_date = timezone.localtime(event.date_time).date()
        self.client.login(username="staff", password="password")
        response = self.client.get(
            reverse("venues:dashboard"),
            {"view": "day", "date": on_date.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Board Night")
        self.assertContains(response, "confirmed immediately")

    def test_dashboard_defaults_to_confirmed_only(self):
        organizer = Event.objects.get(name="Board Night").organizer
        cancelled_event = make_event(
            organizer=organizer,
            venue=self.venue,
            name="Cancelled Night",
        )
        VenueReservation.objects.create(
            venue=self.venue,
            event=cancelled_event,
            requested_by=organizer,
            status=VenueReservation.STATUS_CANCELLED,
        )
        self.client.login(username="staff", password="password")
        response = self.client.get(reverse("venues:dashboard"))
        self.assertNotContains(response, "Cancelled Night")

    def test_dashboard_shows_cancelled_when_filtered(self):
        organizer = Event.objects.get(name="Board Night").organizer
        cancelled_event = make_event(
            organizer=organizer,
            venue=self.venue,
            name="Cancelled Night",
        )
        VenueReservation.objects.create(
            venue=self.venue,
            event=cancelled_event,
            requested_by=organizer,
            status=VenueReservation.STATUS_CANCELLED,
        )
        on_date = timezone.localtime(cancelled_event.date_time).date()
        self.client.login(username="staff", password="password")
        response = self.client.get(
            reverse("venues:dashboard"),
            {
                "view": "day",
                "date": on_date.isoformat(),
                "status": VenueReservation.STATUS_CANCELLED,
            },
        )
        self.assertContains(response, "Cancelled Night")

    def test_dashboard_month_view(self):
        event = Event.objects.get(name="Board Night")
        on_date = timezone.localtime(event.date_time).date()
        self.client.login(username="staff", password="password")
        response = self.client.get(
            reverse("venues:dashboard"),
            {
                "view": ReservationDashboardForm.VIEW_MONTH,
                "date": on_date.isoformat(),
                "status": VenueReservation.STATUS_CONFIRMED,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Board Night")
        self.assertContains(response, on_date.strftime("%B %Y"))

    def test_dashboard_all_view_lists_every_reservation(self):
        organizer = Event.objects.get(name="Board Night").organizer
        other_start, other_end = future_venue_slot(days_ahead=40)
        other_event = make_event(
            organizer=organizer,
            venue=self.venue,
            name="Far Future Night",
            date_time=other_start,
            end_time=other_end,
        )
        VenueReservation.objects.create(
            venue=self.venue,
            event=other_event,
            requested_by=organizer,
        )
        self.client.login(username="staff", password="password")
        response = self.client.get(
            reverse("venues:dashboard"),
            {"view": ReservationDashboardForm.VIEW_ALL, "status": ""},
        )
        self.assertContains(response, "Board Night")
        self.assertContains(response, "Far Future Night")
        self.assertContains(response, "All reservations")

    def test_dashboard_past_view_shows_only_ended_events(self):
        organizer = Event.objects.get(name="Board Night").organizer
        past_start, past_end = future_venue_slot(days_ahead=-14)
        past_event = make_event(
            organizer=organizer,
            venue=self.venue,
            name="Old Night",
            date_time=past_start,
            end_time=past_end,
        )
        VenueReservation.objects.create(
            venue=self.venue,
            event=past_event,
            requested_by=organizer,
        )
        self.client.login(username="staff", password="password")
        response = self.client.get(
            reverse("venues:dashboard"),
            {"view": ReservationDashboardForm.VIEW_PAST, "status": ""},
        )
        self.assertContains(response, "Old Night")
        self.assertContains(response, "Past bookings")
        self.assertNotContains(response, "Board Night")

    def test_dashboard_search_by_event_name(self):
        event = Event.objects.get(name="Board Night")
        self.client.login(username="staff", password="password")
        response = self.client.get(
            reverse("venues:dashboard"),
            {"view": ReservationDashboardForm.VIEW_ALL, "q": "Board"},
        )
        self.assertContains(response, "Board Night")

    def test_dashboard_search_by_organizer_username(self):
        organizer = Event.objects.get(name="Board Night").organizer
        self.client.login(username="staff", password="password")
        response = self.client.get(
            reverse("venues:dashboard"),
            {"view": ReservationDashboardForm.VIEW_PAST, "q": organizer.username},
        )
        self.assertNotContains(response, "Board Night")
        past_start, past_end = future_venue_slot(days_ahead=-10)
        past_event = make_event(
            organizer=organizer,
            venue=self.venue,
            name="Past Search Event",
            date_time=past_start,
            end_time=past_end,
        )
        VenueReservation.objects.create(
            venue=self.venue,
            event=past_event,
            requested_by=organizer,
        )
        response = self.client.get(
            reverse("venues:dashboard"),
            {"view": ReservationDashboardForm.VIEW_PAST, "q": organizer.username},
        )
        self.assertContains(response, "Past Search Event")

    def test_dashboard_search_no_match(self):
        self.client.login(username="staff", password="password")
        response = self.client.get(
            reverse("venues:dashboard"),
            {"view": ReservationDashboardForm.VIEW_ALL, "q": "zzznomatch"},
        )
        self.assertContains(response, "No results for")


class VenueStaffIsolationTest(TestCase):
    def setUp(self):
        self.staff_a = make_user("staff_a")
        self.staff_b = make_user("staff_b")
        self.venue_a = make_venue(name="Venue A", slug="venue-a")
        self.venue_b = make_venue(name="Venue B", slug="venue-b")
        self.venue_a.staff.add(self.staff_a)
        self.venue_b.staff.add(self.staff_b)
        organizer = make_user("org")
        self.event_a = make_event(organizer=organizer, venue=self.venue_a)
        self.event_b = make_event(organizer=organizer, venue=self.venue_b, name="Other Night")
        self.res_a = VenueReservation.objects.create(
            venue=self.venue_a,
            event=self.event_a,
            requested_by=organizer,
        )
        self.res_b = VenueReservation.objects.create(
            venue=self.venue_b,
            event=self.event_b,
            requested_by=organizer,
        )

    def test_staff_a_dashboard_only_shows_own_venue(self):
        on_date = timezone.localtime(self.event_a.date_time).date()
        self.client.login(username="staff_a", password="password")
        response = self.client.get(
            reverse("venues:dashboard"),
            {"view": "day", "date": on_date.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Board Night")
        self.assertNotContains(response, "Other Night")

    def test_staff_a_cannot_cancel_other_venue_reservation(self):
        self.client.login(username="staff_a", password="password")
        response = self.client.post(
            reverse("venues:cancel_reservation", args=[self.res_b.pk])
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.res_b.refresh_from_db()
        self.assertEqual(self.res_b.status, VenueReservation.STATUS_CONFIRMED)


class VenueAvailabilityTest(TestCase):
    def setUp(self):
        self.venue = make_venue(table_count=2)
        self.organizer = make_user("org")

    def test_one_booking_leaves_partial_slot(self):
        start, end = future_venue_slot(days_ahead=7, start_hour=15, duration_hours=1)
        event = make_event(
            organizer=self.organizer,
            venue=self.venue,
            date_time=start,
            end_time=end,
        )
        VenueReservation.objects.create(
            venue=self.venue,
            event=event,
            requested_by=self.organizer,
            status=VenueReservation.STATUS_CONFIRMED,
        )
        on_date = timezone.localtime(start).date()
        payload = get_venue_availability(self.venue, on_date)
        partial_slots = [s for s in payload["slots"] if s["status"] == "partial"]
        self.assertEqual(len(partial_slots), 1)
        self.assertEqual(partial_slots[0]["free_tables"], 1)

    def test_full_venue_blocks_new_booking(self):
        start, end = future_venue_slot(days_ahead=8, start_hour=16, duration_hours=1)
        for i in range(2):
            event = make_event(
                organizer=self.organizer,
                venue=self.venue,
                name=f"Event {i}",
                date_time=start,
                end_time=end,
            )
            VenueReservation.objects.create(
                venue=self.venue,
                event=event,
                requested_by=self.organizer,
                status=VenueReservation.STATUS_CONFIRMED,
            )
        self.assertFalse(
            has_table_availability(self.venue, start, end),
        )

    def test_availability_api_requires_login(self):
        start, _ = future_venue_slot()
        on_date = timezone.localtime(start).date()
        url = reverse("venues:venue_availability", args=[self.venue.pk])
        response = self.client.get(url, {"date": on_date.isoformat()})
        self.assertEqual(response.status_code, 302)

    def test_availability_api_returns_slots(self):
        self.client.login(username="org", password="password")
        start, _ = future_venue_slot()
        on_date = timezone.localtime(start).date()
        url = reverse("venues:venue_availability", args=[self.venue.pk])
        response = self.client.get(url, {"date": on_date.isoformat(), "guests": "4"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["slots"]), 0)
        self.assertEqual(data["total_tables"], 2)
        self.assertIn("guests_remaining", data["slots"][0])

    def test_merge_contiguous_hour_slots(self):
        start, _ = future_venue_slot(days_ahead=12, start_hour=13, duration_hours=1)
        slots = [start, start + timedelta(hours=1), start + timedelta(hours=2)]
        merged_start, merged_end = merge_contiguous_hour_slots(slots)
        self.assertEqual(merged_start, start)
        self.assertEqual(merged_end, start + timedelta(hours=3))

    def test_planned_headcount_uses_max_players(self):
        start, end = future_venue_slot(days_ahead=10, start_hour=12, duration_hours=1)
        event = make_event(
            organizer=self.organizer,
            venue=self.venue,
            date_time=start,
            end_time=end,
            max_players=8,
        )
        VenueReservation.objects.create(
            venue=self.venue,
            event=event,
            requested_by=self.organizer,
            status=VenueReservation.STATUS_CONFIRMED,
        )
        self.assertEqual(event_planned_headcount(event), 8)
        hour_start = start
        hour_end = start + timedelta(hours=1)
        self.assertEqual(
            guests_booked_for_interval(self.venue, hour_start, hour_end),
            8,
        )

    def test_guest_capacity_blocks_overlapping_booking(self):
        self.venue.capacity = 15
        self.venue.save(update_fields=["capacity"])
        start, end = future_venue_slot(days_ahead=11, start_hour=15, duration_hours=1)
        first = make_event(
            organizer=self.organizer,
            venue=self.venue,
            name="Eight People",
            date_time=start,
            end_time=end,
            max_players=8,
        )
        VenueReservation.objects.create(
            venue=self.venue,
            event=first,
            requested_by=self.organizer,
            status=VenueReservation.STATUS_CONFIRMED,
        )
        self.assertFalse(
            has_venue_booking_availability(
                self.venue,
                start,
                end,
                guests_needed=8,
            )
        )
        self.assertTrue(
            has_venue_booking_availability(
                self.venue,
                start,
                end,
                guests_needed=7,
            )
        )

    def test_cancelled_reservation_does_not_block(self):
        start, end = future_venue_slot(days_ahead=9, start_hour=17, duration_hours=1)
        event = make_event(
            organizer=self.organizer,
            venue=self.venue,
            date_time=start,
            end_time=end,
        )
        VenueReservation.objects.create(
            venue=self.venue,
            event=event,
            requested_by=self.organizer,
            status=VenueReservation.STATUS_CANCELLED,
        )
        self.assertTrue(has_table_availability(self.venue, start, end))


class EventPricingTest(TestCase):
    def setUp(self):
        self.organizer = make_user("org")
        self.venue = make_venue(hourly_rate=Decimal("20.00"))
        start = timezone.now() + timezone.timedelta(days=2)
        self.event = make_event(
            organizer=self.organizer,
            venue=self.venue,
            date_time=start,
            end_time=start + timezone.timedelta(hours=3),
        )
        EventRegistration.objects.create(
            event=self.event,
            user=make_user("p1"),
            status=EventRegistration.STATUS_REGISTERED,
        )
        EventRegistration.objects.create(
            event=self.event,
            user=make_user("p2"),
            status=EventRegistration.STATUS_REGISTERED,
        )

    def test_venue_total_and_per_person_price(self):
        self.assertEqual(self.event.venue_total_price, Decimal("60.00"))
        self.assertEqual(self.event.venue_price_per_person, Decimal("30.00"))

    def test_google_maps_url_for_venue_event(self):
        self.assertIn("google.com/maps", self.event.google_maps_url)
        self.assertIn("Sofia", self.event.google_maps_url)


class VenueGamesConstraintTest(TestCase):
    def setUp(self):
        from games.test_utils import create_test_boardgame

        self.user = make_user("organizer")
        self.client.login(username="organizer", password="password")
        self.venue = make_venue()
        self.allowed = create_test_boardgame(bgg_id=100, title="Allowed")
        self.other = create_test_boardgame(bgg_id=101, title="Other")
        self.venue.games.add(self.allowed)

    def test_cannot_select_games_outside_venue(self):
        start = timezone.now() + timezone.timedelta(days=4)
        end = start + timezone.timedelta(hours=2)
        response = self.client.post(
            reverse("events:add_event"),
            {
                "name": "Bad Games Event",
                "venue": self.venue.pk,
                "location": "",
                "current_players": 1,
                "max_players": 4,
                "description": "Test",
                "games": [self.other.pk],
                **venue_schedule_post_times(start, end),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Event.objects.filter(name="Bad Games Event").exists())


class VenueDashboardEditLinksTest(TestCase):
    def setUp(self):
        self.staff_user = make_user("staff")
        self.venue = make_venue()
        self.venue.staff.add(self.staff_user)

    def test_dashboard_shows_edit_venue_links(self):
        self.client.login(username="staff", password="password")
        response = self.client.get(reverse("venues:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit venue")
        self.assertContains(response, reverse("venues:edit_venue", args=[self.venue.slug]))


class VenueReviewTests(TestCase):
    def setUp(self):
        self.user = make_user("reviewer")
        self.venue = make_venue()

    def test_venue_review_list_and_create(self):
        from reviews.models import VenueReview

        self.client.login(username="reviewer", password="password")
        create_url = reverse("venues:venue_review_create", args=[self.venue.slug])
        response = self.client.post(
            create_url,
            {
                "title": "Great space",
                "content": "Lots of games and friendly staff.",
                "rating": 5,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VenueReview.objects.filter(venue=self.venue).count(), 1)

        list_url = reverse("venues:venue_review_list", args=[self.venue.slug])
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Great space")


class NavbarTemplateTest(TestCase):
    def test_navbar_excludes_reviews_link(self):
        response = self.client.get(reverse("web:index"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("reviews:reviews_list"))
        self.assertNotContains(response, "dropdown-toggle")
        self.assertContains(response, reverse("venues:venue_list"))
