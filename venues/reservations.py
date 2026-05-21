from django.db import transaction
from django.utils import timezone

from venues.availability import has_table_availability
from venues.models import VenueReservation


@transaction.atomic
def ensure_confirmed_venue_reservation(event, requested_by):
    """
    Create or refresh a confirmed reservation for a venue-backed event.
    Raises ValueError if tables are not available.
    """
    if not event.venue_id:
        return None

    venue = event.venue
    if not has_table_availability(
        venue,
        event.date_time,
        event.end_time,
        guests_needed=event.max_players,
        exclude_event_id=event.pk,
    ):
        raise ValueError(
            "No table or guest capacity available for the selected time."
        )

    reservation, created = VenueReservation.objects.get_or_create(
        event=event,
        defaults={
            "venue": venue,
            "requested_by": requested_by,
            "status": VenueReservation.STATUS_CONFIRMED,
            "tables_reserved": 1,
        },
    )
    if not created:
        reservation.venue = venue
        reservation.status = VenueReservation.STATUS_CONFIRMED
        reservation.tables_reserved = 1
        reservation.cancelled_at = None
        reservation.staff_note = ""
        reservation.save(
            update_fields=[
                "venue",
                "status",
                "tables_reserved",
                "cancelled_at",
                "staff_note",
                "updated_at",
            ]
        )
    return reservation


def cancel_venue_reservation(event, *, staff_note=""):
    try:
        reservation = event.venue_reservation
    except VenueReservation.DoesNotExist:
        return None
    if reservation.status == VenueReservation.STATUS_CANCELLED:
        return reservation
    reservation.status = VenueReservation.STATUS_CANCELLED
    reservation.cancelled_at = timezone.now()
    if staff_note:
        reservation.staff_note = staff_note
    reservation.save(update_fields=["status", "cancelled_at", "staff_note", "updated_at"])
    return reservation
