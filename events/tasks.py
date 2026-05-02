import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from events.models import Event, EventRegistration

logger = logging.getLogger(__name__)


def _send_if_email(to_email: str, subject: str, message: str):
    if not to_email:
        return
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])


@shared_task
def send_event_join_email(event_id: int, user_id: int):
    event = Event.objects.filter(pk=event_id).first()
    if not event:
        return
    reg = EventRegistration.objects.filter(event_id=event_id, user_id=user_id).select_related("user").first()
    if not reg or reg.status != EventRegistration.STATUS_REGISTERED:
        return
    user = reg.user
    subject = f'You joined "{event.name}"'
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f'You successfully joined "{event.name}".\n'
        f"Date & time: {timezone.localtime(event.date_time).strftime('%d %b %Y %H:%M')}\n"
        f"Location: {event.location}\n\n"
        "See you there!"
    )
    _send_if_email(user.email, subject, message)
    logger.info("Join email sent to %s for event %s", user.email, event_id)


@shared_task
def send_event_reminder_email(event_id: int, user_id: int, hours_before: int):
    event = Event.objects.filter(pk=event_id).first()
    if not event:
        return
    reg = EventRegistration.objects.filter(event_id=event_id, user_id=user_id).select_related("user").first()
    if not reg or reg.status != EventRegistration.STATUS_REGISTERED:
        return
    user = reg.user

    subject = f'Reminder: "{event.name}" in {hours_before} hour(s)'
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f'This is a reminder for "{event.name}".\n'
        f"Starts at: {timezone.localtime(event.date_time).strftime('%d %b %Y %H:%M')}\n"
        f"Location: {event.location}\n\n"
        "If you can't make it, please contact the organizer."
    )
    _send_if_email(user.email, subject, message)
    logger.info("Reminder (%sh) email sent to %s for event %s", hours_before, user.email, event_id)


@shared_task
def send_event_cancelled_email(event_name: str, event_date_time_iso: str, location: str, to_email: str):
    subject = f'Event cancelled: "{event_name}"'
    message = (
        "Hi,\n\n"
        f'The event "{event_name}" has been cancelled.\n'
        f"Planned start: {event_date_time_iso}\n"
        f"Location: {location}\n\n"
        "Sorry for the inconvenience."
    )
    _send_if_email(to_email, subject, message)


@shared_task
def send_removed_from_event_email(event_id: int, user_id: int):
    event = Event.objects.filter(pk=event_id).first()
    if not event:
        return
    reg = EventRegistration.objects.filter(event_id=event_id, user_id=user_id).select_related("user").first()
    if not reg or reg.status != EventRegistration.STATUS_REMOVED:
        return
    user = reg.user
    subject = f'You were removed from "{event.name}"'
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f'You were removed from the event "{event.name}".\n'
        f"Date & time: {timezone.localtime(event.date_time).strftime('%d %b %Y %H:%M')}\n"
        f"Location: {event.location}\n\n"
        "If this is a mistake, contact the organizer."
    )
    _send_if_email(user.email, subject, message)
    logger.info("Removed email sent to %s for event %s", user.email, event_id)

