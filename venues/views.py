from collections import OrderedDict
from datetime import datetime, timedelta

from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from events.models import Event
from venues.forms import (
    ReservationDashboardForm,
    StaffCancelReservationForm,
    VenueSearchForm,
)
from venues.availability import get_venue_availability
from venues.models import Venue, VenueReservation
from venues.permissions import (
    can_manage_reservation,
    is_venue_staff,
    staff_venues_queryset,
    user_has_venue_dashboard_access,
)
from venues.dashboard_filters import dashboard_period_label, period_bounds
from venues.reservations import cancel_venue_reservation


class VenueListView(ListView):
    model = Venue
    template_name = "venues.html"
    context_object_name = "venues"
    paginate_by = 9

    def get_queryset(self):
        queryset = Venue.objects.filter(is_active=True)
        form = VenueSearchForm(self.request.GET)
        if form.is_valid():
            name = form.cleaned_data.get("name")
            city = form.cleaned_data.get("city")
            if name:
                queryset = queryset.filter(name__icontains=name)
            if city:
                queryset = queryset.filter(city__icontains=city)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = VenueSearchForm(self.request.GET)
        return context


class VenueDetailView(DetailView):
    model = Venue
    template_name = "venue_detail.html"
    context_object_name = "venue"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Venue.objects.filter(is_active=True).prefetch_related("games")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venue = self.object
        now = timezone.now()
        user = self.request.user

        upcoming_confirmed = (
            Event.objects.filter(
                venue=venue,
                date_time__gt=now,
                venue_reservation__status=VenueReservation.STATUS_CONFIRMED,
            )
            .select_related("venue_reservation", "organizer")
            .prefetch_related("games")
            .order_by("date_time")
        )

        context["upcoming_events"] = upcoming_confirmed
        context["is_venue_staff"] = is_venue_staff(user, venue)
        if context["is_venue_staff"]:
            context["staff_manage_reservations"] = (
                VenueReservation.objects.filter(
                    venue=venue,
                    status=VenueReservation.STATUS_CONFIRMED,
                    event__date_time__gt=now,
                )
                .select_related("event", "requested_by", "event__organizer")
                .order_by("event__date_time")
            )
            context["staff_today_availability"] = get_venue_availability(
                venue,
                timezone.localdate(),
            )
            context["dashboard_day_url"] = (
                f"{reverse('venues:dashboard')}?view=day"
                f"&date={timezone.localdate().isoformat()}"
                f"&status={VenueReservation.STATUS_CONFIRMED}"
            )
        else:
            context["staff_manage_reservations"] = VenueReservation.objects.none()
            context["staff_today_availability"] = None
            context["dashboard_day_url"] = None
        context["STATUS_CONFIRMED"] = VenueReservation.STATUS_CONFIRMED
        context["STATUS_CANCELLED"] = VenueReservation.STATUS_CANCELLED
        return context


class VenueAvailabilityView(LoginRequiredMixin, View):
    def get(self, request, venue_id):
        venue = get_object_or_404(Venue, pk=venue_id, is_active=True)
        date_str = request.GET.get("date")
        on_date = parse_date(date_str) if date_str else timezone.localdate()
        if not on_date:
            return JsonResponse({"error": "Invalid date."}, status=400)

        exclude_event = request.GET.get("exclude_event")
        exclude_event_id = int(exclude_event) if exclude_event else None
        guests_param = request.GET.get("guests")
        try:
            guests_needed = max(int(guests_param), 0) if guests_param else 0
        except (TypeError, ValueError):
            guests_needed = 0

        payload = get_venue_availability(
            venue,
            on_date,
            exclude_event_id=exclude_event_id,
            guests_needed=guests_needed,
        )
        return JsonResponse(payload)


class VenueDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "venue_dashboard.html"

    def test_func(self):
        return user_has_venue_dashboard_access(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        managed_venues = staff_venues_queryset(user)
        form = ReservationDashboardForm(self.request.GET or None)
        context["form"] = form
        now = timezone.now()
        managed_venue_list = list(managed_venues.order_by("name"))

        reservations = VenueReservation.objects.filter(
            venue__in=managed_venues,
        ).select_related(
            "venue",
            "event",
            "requested_by",
            "event__organizer",
        )

        search_query = ""
        selected_date = timezone.localdate()
        view_mode = ReservationDashboardForm.VIEW_WEEK
        if form.is_valid():
            view_mode = form.cleaned_data.get("view") or ReservationDashboardForm.VIEW_WEEK
            selected_date = form.cleaned_data.get("date") or timezone.localdate()
            if view_mode == ReservationDashboardForm.VIEW_DAY and "date" not in self.request.GET:
                selected_date = timezone.localdate()
            status_filter = form.cleaned_data.get("status")
            search_query = (form.cleaned_data.get("q") or "").strip()
            if view_mode not in (
                ReservationDashboardForm.VIEW_PAST,
                ReservationDashboardForm.VIEW_ALL,
            ) and status_filter:
                reservations = reservations.filter(status=status_filter)
            if search_query:
                reservations = reservations.filter(
                    Q(event__name__icontains=search_query)
                    | Q(requested_by__username__icontains=search_query)
                    | Q(requested_by__first_name__icontains=search_query)
                    | Q(requested_by__last_name__icontains=search_query)
                    | Q(event__organizer__username__icontains=search_query)
                    | Q(event__organizer__first_name__icontains=search_query)
                    | Q(event__organizer__last_name__icontains=search_query)
                )

            if view_mode == ReservationDashboardForm.VIEW_PAST:
                reservations = reservations.filter(event__end_time__lt=now)
            elif view_mode == ReservationDashboardForm.VIEW_ALL:
                pass
            else:
                start, end = period_bounds(
                    view_mode,
                    selected_date,
                    day_view=ReservationDashboardForm.VIEW_DAY,
                    week_view=ReservationDashboardForm.VIEW_WEEK,
                    month_view=ReservationDashboardForm.VIEW_MONTH,
                )
                reservations = reservations.filter(
                    event__date_time__gte=start,
                    event__date_time__lt=end,
                )
                context["range_start"] = start
                context["range_end"] = end - timedelta(seconds=1)
        else:
            start, end = period_bounds(
                view_mode,
                selected_date,
                day_view=ReservationDashboardForm.VIEW_DAY,
                week_view=ReservationDashboardForm.VIEW_WEEK,
                month_view=ReservationDashboardForm.VIEW_MONTH,
            )
            reservations = reservations.filter(
                event__date_time__gte=start,
                event__date_time__lt=end,
                status=VenueReservation.STATUS_CONFIRMED,
            )
            context["range_start"] = start
            context["range_end"] = end - timedelta(seconds=1)

        context["view_mode"] = view_mode
        context["selected_date"] = selected_date
        context["search_query"] = search_query
        context["show_date_filter"] = view_mode in ReservationDashboardForm.PERIOD_VIEWS
        context["period_label"] = dashboard_period_label(
            view_mode,
            selected_date,
            context.get("range_start"),
            context.get("range_end"),
            forms=ReservationDashboardForm,
        )
        context["now"] = now

        reverse_chronological = view_mode in (
            ReservationDashboardForm.VIEW_PAST,
            ReservationDashboardForm.VIEW_ALL,
        )
        reservations = reservations.order_by(
            "-event__date_time" if reverse_chronological else "event__date_time"
        )

        grouped = OrderedDict()
        for reservation in reservations:
            day_key = timezone.localtime(reservation.event.date_time).date()
            grouped.setdefault(day_key, []).append(reservation)

        context["managed_venues"] = managed_venues
        context["managed_venue_list"] = managed_venue_list
        context["show_venue_column"] = len(managed_venue_list) > 1
        context["grouped_reservations"] = grouped
        context["reservation_count"] = reservations.count()
        context["confirmed_count"] = reservations.filter(
            status=VenueReservation.STATUS_CONFIRMED
        ).count()
        context["cancelled_count"] = reservations.filter(
            status=VenueReservation.STATUS_CANCELLED
        ).count()
        context["STATUS_CONFIRMED"] = VenueReservation.STATUS_CONFIRMED
        context["STATUS_CANCELLED"] = VenueReservation.STATUS_CANCELLED

        if view_mode == ReservationDashboardForm.VIEW_DAY:
            venues_for_availability = managed_venue_list
            context["venue_day_availability"] = [
                {
                    "venue": venue,
                    "availability": get_venue_availability(venue, selected_date),
                }
                for venue in venues_for_availability
            ]
        else:
            context["venue_day_availability"] = []

        return context


class CancelReservationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        reservation = get_object_or_404(
            VenueReservation.objects.select_related("venue", "event", "requested_by"),
            pk=pk,
        )
        user = request.user
        is_staff = can_manage_reservation(user, reservation)
        is_organizer = reservation.requested_by_id == user.pk

        if not (is_staff or is_organizer):
            messages.error(request, "You are not authorised to cancel this reservation.")
            return redirect("accounts:profile")

        if reservation.status == VenueReservation.STATUS_CANCELLED:
            messages.warning(request, "This reservation is already cancelled.")
            if is_staff:
                return redirect("venues:dashboard")
            return redirect("accounts:profile")

        staff_note = ""
        if is_staff:
            form = StaffCancelReservationForm(request.POST)
            if form.is_valid():
                staff_note = form.cleaned_data.get("staff_note", "")

        event = reservation.event
        cancel_venue_reservation(event, staff_note=staff_note)

        from events.models import EventRegistration
        from events.tasks import send_event_cancelled_email

        dt_str = timezone.localtime(event.date_time).strftime("%d %b %Y %H:%M")
        for reg in event.registrations.filter(
            status__in=[
                EventRegistration.STATUS_REGISTERED,
                EventRegistration.STATUS_PRESENT,
            ]
        ).select_related("user"):
            if reg.user.email:
                send_event_cancelled_email.delay(
                    event.name,
                    dt_str,
                    event.display_location,
                    reg.user.email,
                )

        messages.success(
            request,
            f'Reservation for "{event.name}" has been cancelled.',
        )

        if is_staff:
            return redirect("venues:dashboard")
        return redirect("accounts:profile")
