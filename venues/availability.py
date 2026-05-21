from datetime import datetime, timedelta

from django.utils import timezone

from venues.models import Venue, VenueReservation


def intervals_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b


def event_planned_headcount(event):
    """Guests counted toward venue capacity (uses max_players even with no sign-ups yet)."""
    return event.max_players


def _confirmed_reservations(venue, *, exclude_event_id=None):
    qs = VenueReservation.objects.filter(
        venue=venue,
        status=VenueReservation.STATUS_CONFIRMED,
    ).select_related("event")
    if exclude_event_id:
        qs = qs.exclude(event_id=exclude_event_id)
    return qs


def booked_tables_for_interval(
    venue,
    interval_start,
    interval_end,
    *,
    exclude_event_id=None,
):
    booked = 0
    for reservation in _confirmed_reservations(venue, exclude_event_id=exclude_event_id):
        event = reservation.event
        if intervals_overlap(
            interval_start,
            interval_end,
            event.date_time,
            event.end_time,
        ):
            booked += reservation.tables_reserved
    return booked


def guests_booked_for_interval(
    venue,
    interval_start,
    interval_end,
    *,
    exclude_event_id=None,
):
    total = 0
    for reservation in _confirmed_reservations(venue, exclude_event_id=exclude_event_id):
        event = reservation.event
        if intervals_overlap(
            interval_start,
            interval_end,
            event.date_time,
            event.end_time,
        ):
            total += event_planned_headcount(event)
    return total


def free_tables_for_interval(
    venue,
    interval_start,
    interval_end,
    *,
    exclude_event_id=None,
):
    booked = booked_tables_for_interval(
        venue,
        interval_start,
        interval_end,
        exclude_event_id=exclude_event_id,
    )
    return max(venue.table_count - booked, 0)


def guests_remaining_for_interval(
    venue,
    interval_start,
    interval_end,
    *,
    exclude_event_id=None,
):
    booked = guests_booked_for_interval(
        venue,
        interval_start,
        interval_end,
        exclude_event_id=exclude_event_id,
    )
    return max(venue.capacity - booked, 0)


def iter_hours_in_event(date_time, end_time):
    slot_start = date_time
    while slot_start < end_time:
        slot_end = min(slot_start + timedelta(hours=1), end_time)
        yield slot_start, slot_end
        slot_start += timedelta(hours=1)


def hour_slot_starts_in_range(date_time, end_time):
    """Yield aware datetimes for each full hour start covered by [date_time, end_time)."""
    for slot_start, _ in iter_hours_in_event(date_time, end_time):
        yield slot_start


def merge_contiguous_hour_slots(slot_starts):
    """
    Sort hour starts and return (range_start, range_end) covering all slots.
    Raises ValueError if empty or not contiguous 1-hour steps.
    """
    if not slot_starts:
        raise ValueError("No time slots selected.")
    ordered = sorted(slot_starts)
    for i in range(1, len(ordered)):
        if ordered[i] - ordered[i - 1] != timedelta(hours=1):
            raise ValueError("Selected hours must be consecutive.")
    return ordered[0], ordered[-1] + timedelta(hours=1)


def parse_venue_time_slot_values(raw_value):
    """Parse comma-separated slot start ISO strings into aware datetimes."""
    if not raw_value or not str(raw_value).strip():
        return []
    slots = []
    for part in str(raw_value).split(","):
        part = part.strip()
        if not part:
            continue
        parsed = datetime.fromisoformat(part)
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        slots.append(parsed)
    return slots


def slot_interval_status(
    venue,
    interval_start,
    interval_end,
    *,
    exclude_event_id=None,
    guests_needed=0,
    tables_needed=1,
):
    free_tables = free_tables_for_interval(
        venue,
        interval_start,
        interval_end,
        exclude_event_id=exclude_event_id,
    )
    guests_remaining = guests_remaining_for_interval(
        venue,
        interval_start,
        interval_end,
        exclude_event_id=exclude_event_id,
    )
    guests_booked = venue.capacity - guests_remaining

    table_blocked = free_tables < tables_needed
    guest_blocked = guests_needed > 0 and guests_remaining < guests_needed

    if table_blocked or guest_blocked:
        status = "full"
    elif free_tables < venue.table_count or guests_booked > 0:
        status = "partial"
    else:
        status = "free"

    return {
        "free_tables": free_tables,
        "total_tables": venue.table_count,
        "guests_booked": guests_booked,
        "guests_remaining": guests_remaining,
        "venue_capacity": venue.capacity,
        "status": status,
        "bookable": not table_blocked and not guest_blocked,
    }


def has_venue_booking_availability(
    venue,
    date_time,
    end_time,
    *,
    guests_needed,
    tables_needed=1,
    exclude_event_id=None,
):
    if not venue.is_active:
        return False
    if end_time <= date_time:
        return False
    if guests_needed < 1:
        return False

    for slot_start, slot_end in iter_hours_in_event(date_time, end_time):
        info = slot_interval_status(
            venue,
            slot_start,
            slot_end,
            exclude_event_id=exclude_event_id,
            guests_needed=guests_needed,
            tables_needed=tables_needed,
        )
        if info["free_tables"] < tables_needed or info["guests_remaining"] < guests_needed:
            return False
    return True


def has_table_availability(
    venue,
    date_time,
    end_time,
    *,
    tables_needed=1,
    exclude_event_id=None,
    guests_needed=1,
):
    """Backward-compatible wrapper including guest capacity."""
    return has_venue_booking_availability(
        venue,
        date_time,
        end_time,
        guests_needed=guests_needed,
        tables_needed=tables_needed,
        exclude_event_id=exclude_event_id,
    )


def event_within_working_hours(venue, date_time, end_time):
    if end_time <= date_time:
        return False
    local_start = timezone.localtime(date_time)
    local_end = timezone.localtime(end_time)
    if local_start.date() != local_end.date():
        return False
    if local_start.time() < venue.opens_at:
        return False
    if local_end.time() > venue.closes_at:
        return False
    return True


def get_venue_availability(
    venue,
    on_date,
    *,
    exclude_event_id=None,
    guests_needed=0,
    tables_needed=1,
):
    slots = []
    for hour_start in venue.iter_hour_slot_starts(on_date):
        hour_end = hour_start + timedelta(hours=1)
        info = slot_interval_status(
            venue,
            hour_start,
            hour_end,
            exclude_event_id=exclude_event_id,
            guests_needed=guests_needed,
            tables_needed=tables_needed,
        )
        slots.append(
            {
                "start": hour_start.isoformat(),
                "end": hour_end.isoformat(),
                "label": (
                    f"{timezone.localtime(hour_start).strftime('%H:%M')} – "
                    f"{timezone.localtime(hour_end).strftime('%H:%M')}"
                ),
                "free_tables": info["free_tables"],
                "total_tables": info["total_tables"],
                "guests_booked": info["guests_booked"],
                "guests_remaining": info["guests_remaining"],
                "venue_capacity": info["venue_capacity"],
                "status": info["status"],
                "bookable": info["bookable"],
            }
        )

    return {
        "venue_id": venue.pk,
        "date": on_date.isoformat(),
        "opens_at": venue.opens_at.strftime("%H:%M"),
        "closes_at": venue.closes_at.strftime("%H:%M"),
        "total_tables": venue.table_count,
        "venue_capacity": venue.capacity,
        "guests_needed": guests_needed,
        "slots": slots,
    }
