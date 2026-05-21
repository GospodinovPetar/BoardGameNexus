"""Rules for which users can see events on the public list and detail pages."""

from django.utils import timezone

from events.models import EventRegistration
from venues.models import VenueReservation

PARTICIPANT_HISTORY_STATUSES = (
    EventRegistration.STATUS_REGISTERED,
    EventRegistration.STATUS_PRESENT,
    EventRegistration.STATUS_NO_SHOW,
)

ACTIVE_REGISTRATION_STATUSES = (
    EventRegistration.STATUS_REGISTERED,
    EventRegistration.STATUS_PRESENT,
)


def event_is_cancelled(event):
    """Venue-backed event whose booking was cancelled (inactive for public listings)."""
    try:
        reservation = event.venue_reservation
    except VenueReservation.DoesNotExist:
        return False
    return reservation.status == VenueReservation.STATUS_CANCELLED


def filter_active_events(queryset):
    """Exclude events with a cancelled venue reservation."""
    return queryset.exclude(
        venue_reservation__status=VenueReservation.STATUS_CANCELLED,
    )


def filter_public_events(queryset):
    """Upcoming, publicly listable events."""
    return filter_active_events(queryset).filter(date_time__gt=timezone.now())


def is_event_organizer(user, event):
    if not user.is_authenticated:
        return False
    return event.organizer is not None and event.organizer_id == user.pk


def is_organizer_or_moderator(user, event):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.groups.filter(name="Moderators").exists():
        return True
    return is_event_organizer(user, event)


def user_is_registered_participant(user, event):
    if not user.is_authenticated:
        return False
    return event.registrations.filter(
        user=user,
        status__in=ACTIVE_REGISTRATION_STATUSES,
    ).exists()


def can_view_event(user, event):
    """
    Public upcoming active events: everyone.
    Cancelled events: only registered participants (and staff/moderator/organizer).
    Past events: organizer, moderators, or participants with history status.
    """
    if event_is_cancelled(event):
        if not user.is_authenticated:
            return False
        if is_organizer_or_moderator(user, event):
            return True
        return user_is_registered_participant(user, event)

    now = timezone.now()
    if event.date_time > now:
        return True
    if not user.is_authenticated:
        return False
    if is_organizer_or_moderator(user, event):
        return True
    return event.registrations.filter(
        user=user,
        status__in=PARTICIPANT_HISTORY_STATUSES,
    ).exists()


def event_has_started(event):
    return event.date_time <= timezone.now()
