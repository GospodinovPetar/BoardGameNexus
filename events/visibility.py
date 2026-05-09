"""Rules for which users can see events on the public list and detail pages."""

from django.utils import timezone

from events.models import EventRegistration

PARTICIPANT_HISTORY_STATUSES = (
    EventRegistration.STATUS_REGISTERED,
    EventRegistration.STATUS_PRESENT,
    EventRegistration.STATUS_NO_SHOW,
)


def is_organizer_or_moderator(user, event):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.groups.filter(name="Moderators").exists():
        return True
    return event.organizer is not None and event.organizer_id == user.pk


def can_view_event(user, event):
    """
    Upcoming events are visible to everyone.
    Past events are visible only to moderators, the organizer, or participants
    (registered / present / no-show — not removed).
    """
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
