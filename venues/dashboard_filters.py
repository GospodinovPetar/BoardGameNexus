from datetime import datetime, timedelta

from django.utils import timezone


def month_bounds(selected_date):
    """Return aware [start, end) for the calendar month containing selected_date."""
    month_start = selected_date.replace(day=1)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(month_start, datetime.min.time()), tz)
    end = timezone.make_aware(datetime.combine(next_month, datetime.min.time()), tz)
    return start, end


def period_bounds(view_mode, selected_date, *, day_view, week_view, month_view):
    """
    Return (start, end) aware datetimes for [start, end), or (None, None) when
    the view does not use a calendar period (all / past).
    """
    tz = timezone.get_current_timezone()
    if view_mode == day_view:
        start = timezone.make_aware(
            datetime.combine(selected_date, datetime.min.time()), tz
        )
        return start, start + timedelta(days=1)
    if view_mode == week_view:
        week_start = selected_date - timedelta(days=selected_date.weekday())
        start = timezone.make_aware(
            datetime.combine(week_start, datetime.min.time()), tz
        )
        return start, start + timedelta(days=7)
    if view_mode == month_view:
        return month_bounds(selected_date)
    return None, None


def dashboard_period_label(view_mode, selected_date, range_start, range_end, *, forms):
    """Human-readable subtitle for the dashboard header."""
    if view_mode == forms.VIEW_DAY:
        today = timezone.localdate()
        if selected_date == today:
            return "Today's table occupancy and bookings"
        return (
            f"Table occupancy and bookings for {selected_date.strftime('%d %b %Y')}"
        )
    if view_mode == forms.VIEW_WEEK and range_start and range_end:
        return (
            f"Week of {timezone.localtime(range_start).strftime('%d %b %Y')}"
            f" – {timezone.localtime(range_end).strftime('%d %b %Y')}"
        )
    if view_mode == forms.VIEW_MONTH:
        return f"Bookings for {selected_date.strftime('%B %Y')}"
    if view_mode == forms.VIEW_ALL:
        return "All reservations at your venues"
    if view_mode == forms.VIEW_PAST:
        return "Past bookings (events already ended)"
    return ""
