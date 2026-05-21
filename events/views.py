from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from events.forms import EventForm, EventSearchForm
from events.models import Event, EventRegistration
from events.visibility import (
    ACTIVE_REGISTRATION_STATUSES,
    PARTICIPANT_HISTORY_STATUSES,
    can_view_event,
    event_has_started,
    event_is_cancelled,
    filter_public_events,
    is_event_organizer,
    is_organizer_or_moderator,
)
from events.tasks import (
    send_event_cancelled_email,
    send_event_join_email,
    send_event_reminder_email,
    send_removed_from_event_email,
)
from games.models import BoardGame
from venues.models import VenueReservation


def _apply_no_show_penalties(event):
    """
    Lazily mark overdue registered participants as no-show and assign strikes.
    Returns a list of users who were just penalised in this call.
    """
    if not event.attendance_window_closed():
        return []

    overdue = event.registrations.filter(
        status=EventRegistration.STATUS_REGISTERED
    ).select_related("user")

    penalised = []
    for reg in overdue:
        reg.status = EventRegistration.STATUS_NO_SHOW
        reg.no_show_marked_at = timezone.now()
        reg.save(update_fields=["status", "no_show_marked_at"])
        reg.user.no_show_strikes += 1
        reg.user.save(update_fields=["no_show_strikes"])
        penalised.append(reg.user)

    return penalised


def get_suggested_events(user, limit=4):
    """
    Връща до `limit` предстоящи събития на база игрите от минали регистрации
    (активен статус). Всяко събитие има анотация `match_count`.
    """
    if not user.is_authenticated:
        return Event.objects.none()

    now = timezone.now()

    historical_game_ids = (
        BoardGame.objects.filter(
            events__date_time__lt=now,
            events__registrations__user=user,
            events__registrations__status__in=[
                EventRegistration.STATUS_REGISTERED,
                EventRegistration.STATUS_PRESENT,
            ],
        )
        .values_list("pk", flat=True)
        .distinct()
    )
    historical_ids_list = list(historical_game_ids)
    if not historical_ids_list:
        return Event.objects.none()

    joined_event_ids = user.event_registrations.filter(
        status__in=[
            EventRegistration.STATUS_REGISTERED,
            EventRegistration.STATUS_PRESENT,
        ]
    ).values_list("event_id", flat=True)

    return (
        filter_public_events(Event.objects.all())
        .exclude(pk__in=joined_event_ids)
        .filter(games__pk__in=historical_ids_list)
        .annotate(
            match_count=Count(
                "games",
                filter=Q(games__pk__in=historical_ids_list),
                distinct=True,
            )
        )
        .distinct()
        .order_by("-match_count", "date_time", "name")
        .prefetch_related("games")[:limit]
    )


class EventListView(ListView):
    model = Event
    template_name = "events.html"
    context_object_name = "events"
    paginate_by = 6

    def get_queryset(self):
        events_list = filter_public_events(Event.objects.all())
        form = EventSearchForm(self.request.GET)

        if form.is_valid():
            name = form.cleaned_data.get("name")
            organizer_name = form.cleaned_data.get("organizer_name")
            locations = form.cleaned_data.get("location")
            min_players = form.cleaned_data.get("min_players")
            max_players = form.cleaned_data.get("max_players")
            date_time_before = form.cleaned_data.get("date_time_before")
            date_time_after = form.cleaned_data.get("date_time_after")
            games = form.cleaned_data.get("games")
            sort_by = form.cleaned_data.get("sort_by")

            if name:
                events_list = events_list.filter(name__icontains=name)
            if organizer_name:
                events_list = events_list.filter(
                    organizer_name__icontains=organizer_name
                )
            if locations:
                events_list = events_list.filter(location__in=locations)
            if min_players is not None:
                events_list = events_list.filter(current_players__gte=min_players)
            if max_players is not None:
                events_list = events_list.filter(max_players__lte=max_players)
            if date_time_before:
                events_list = events_list.filter(date_time__lte=date_time_before)
            if date_time_after:
                events_list = events_list.filter(date_time__gte=date_time_after)
            if games:
                events_list = events_list.filter(games__in=games).distinct()

            if sort_by:
                events_list = events_list.order_by(sort_by)

        return events_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context["page_obj"]
        context["events"] = page_obj
        form = EventSearchForm(self.request.GET)
        context["form"] = form

        if self.request.user.is_authenticated:
            joined_pks = set(
                self.request.user.event_registrations.filter(
                    status__in=[
                        EventRegistration.STATUS_REGISTERED,
                        EventRegistration.STATUS_PRESENT,
                    ]
                ).values_list("event_id", flat=True)
            )
            context["joined_event_pks"] = joined_pks
            context["suggested_events"] = get_suggested_events(self.request.user)
        else:
            context["joined_event_pks"] = set()
            context["suggested_events"] = Event.objects.none()

        return context


class EventDetailView(DetailView):
    model = Event
    template_name = "event_detail.html"
    context_object_name = "event"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not can_view_event(self.request.user, obj):
            raise Http404()
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        penalised = _apply_no_show_penalties(self.object)

        context = self.get_context_data(object=self.object)

        if request.user.is_authenticated and request.user in penalised:
            messages.warning(
                request,
                f'You received a no-show strike for missing "{self.object.name}".',
            )

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        user = self.request.user

        is_organizer = is_event_organizer(user, event)
        can_edit_event = is_organizer_or_moderator(user, event)
        can_manage_participants = is_organizer

        user_registration = None
        if user.is_authenticated:
            user_registration = event.registrations.filter(user=user).first()

        all_registrations = (
            event.registrations.select_related("user", "user__profile")
            .exclude(status=EventRegistration.STATUS_REMOVED)
            .order_by("joined_at")
        )

        started = event_has_started(event)
        fellow_participants = []
        if started:
            fellow_participants = list(
                event.registrations.filter(status__in=PARTICIPANT_HISTORY_STATUSES)
                .select_related("user", "user__profile")
                .order_by("joined_at")
            )

        context.update(
            {
                "is_organizer": is_organizer,
                "can_manage_participants": can_manage_participants,
                "can_edit_event": can_edit_event,
                "registrations": all_registrations if can_manage_participants else [],
                "user_registration": user_registration,
                "attendance_window_open": event.attendance_window_open(),
                "attendance_window_closed": event.attendance_window_closed(),
                "is_before_event": timezone.now() < event.date_time,
                "is_past_event": started,
                "fellow_participants": fellow_participants,
                "STATUS_REGISTERED": EventRegistration.STATUS_REGISTERED,
                "STATUS_PRESENT": EventRegistration.STATUS_PRESENT,
                "STATUS_NO_SHOW": EventRegistration.STATUS_NO_SHOW,
                "venue_reservation": getattr(event, "venue_reservation", None),
                "event_is_cancelled": event_is_cancelled(event),
                "can_cancel_venue_reservation": (
                    is_organizer
                    and event.venue_id
                    and timezone.now() < event.date_time
                    and getattr(
                        getattr(event, "venue_reservation", None),
                        "status",
                        None,
                    )
                    == VenueReservation.STATUS_CONFIRMED
                ),
            }
        )
        return context


class JoinEventView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pk = kwargs["pk"]
        event = get_object_or_404(Event, pk=pk)

        if event_is_cancelled(event):
            messages.error(
                request,
                "This event has been cancelled and is no longer open for registration.",
            )
            return redirect("events:events_list")

        if event_has_started(event):
            messages.error(
                request,
                "This event has already started; registration is closed.",
            )
            return redirect("events:events_list")

        existing = EventRegistration.objects.filter(
            event=event, user=request.user
        ).first()

        if existing:
            if existing.status == EventRegistration.STATUS_REMOVED:
                messages.warning(
                    request, "You have been removed from this event by the organizer."
                )
            else:
                messages.warning(request, "You have already joined this event!")
            return redirect("events:event_detail", pk=pk)

        active_count = event.registrations.filter(
            status__in=[
                EventRegistration.STATUS_REGISTERED,
                EventRegistration.STATUS_PRESENT,
            ]
        ).count()

        if active_count >= event.max_players:
            messages.info(request, "Sorry, all spots are filled.")
            return redirect("events:event_detail", pk=pk)

        EventRegistration.objects.create(event=event, user=request.user)
        event.current_players = active_count + 1
        event.save(update_fields=["current_players"])
        messages.success(request, f"Successfully joined {event.name}!")

        # Emails: join confirmation + reminders (1 day and 2 hours before).
        if request.user.email:
            send_event_join_email.delay(event.pk, request.user.pk)

            now = timezone.now()
            reminder_24h = event.date_time - timezone.timedelta(hours=24)
            reminder_2h = event.date_time - timezone.timedelta(hours=2)
            if reminder_24h > now:
                send_event_reminder_email.apply_async(
                    args=(event.pk, request.user.pk, 24),
                    eta=reminder_24h,
                )
            if reminder_2h > now:
                send_event_reminder_email.apply_async(
                    args=(event.pk, request.user.pk, 2),
                    eta=reminder_2h,
                )

        return redirect("events:event_detail", pk=pk)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class LeaveEventView(LoginRequiredMixin, View):
    """Allow a participant to cancel their registration before the event starts."""

    def post(self, request, *args, **kwargs):
        pk = kwargs["pk"]
        event = get_object_or_404(Event, pk=pk)

        if event_has_started(event):
            messages.error(
                request,
                "You cannot leave an event that has already started.",
            )
            return redirect("events:event_detail", pk=pk)

        reg = EventRegistration.objects.filter(event=event, user=request.user).first()

        if not reg or reg.status != EventRegistration.STATUS_REGISTERED:
            messages.warning(
                request,
                "You are not actively registered for this event.",
            )
            return redirect("events:event_detail", pk=pk)

        reg.status = EventRegistration.STATUS_REMOVED
        reg.removed_at = timezone.now()
        reg.save(update_fields=["status", "removed_at"])

        active_count = event.registrations.filter(
            status__in=[
                EventRegistration.STATUS_REGISTERED,
                EventRegistration.STATUS_PRESENT,
            ]
        ).count()
        event.current_players = active_count
        event.save(update_fields=["current_players"])

        messages.success(request, f'You have left "{event.name}".')
        return redirect("events:event_detail", pk=pk)


class RemoveParticipantView(LoginRequiredMixin, View):
    def post(self, request, event_pk, reg_pk):
        event = get_object_or_404(Event, pk=event_pk)

        if not is_event_organizer(request.user, event):
            messages.error(request, "You are not authorised to remove participants.")
            return redirect("events:event_detail", pk=event_pk)

        reg = get_object_or_404(
            EventRegistration,
            pk=reg_pk,
            event=event,
        )

        if reg.status in [
            EventRegistration.STATUS_REGISTERED,
            EventRegistration.STATUS_PRESENT,
        ]:
            removed_user_id = reg.user_id
            reg.status = EventRegistration.STATUS_REMOVED
            reg.removed_at = timezone.now()
            reg.save(update_fields=["status", "removed_at"])

            active_count = event.registrations.filter(
                status__in=[
                    EventRegistration.STATUS_REGISTERED,
                    EventRegistration.STATUS_PRESENT,
                ]
            ).count()
            event.current_players = max(active_count, 0)
            event.save(update_fields=["current_players"])

            messages.success(
                request,
                f"{reg.user.username} has been removed from the event.",
            )

            if reg.user.email:
                send_removed_from_event_email.delay(event.pk, removed_user_id)
        else:
            messages.warning(
                request,
                f"{reg.user.username} cannot be removed (status: {reg.get_status_display()}).",
            )

        return redirect("events:event_detail", pk=event_pk)


class MarkPresentView(LoginRequiredMixin, View):
    def post(self, request, event_pk, reg_pk):
        event = get_object_or_404(Event, pk=event_pk)

        if not is_event_organizer(request.user, event):
            messages.error(request, "You are not authorised to mark attendance.")
            return redirect("events:event_detail", pk=event_pk)

        if not event.attendance_window_open():
            messages.error(
                request,
                "The attendance window is not open. "
                "Attendance can only be marked during the event (within 1 hour of start).",
            )
            return redirect("events:event_detail", pk=event_pk)

        reg = get_object_or_404(
            EventRegistration,
            pk=reg_pk,
            event=event,
            status=EventRegistration.STATUS_REGISTERED,
        )
        reg.status = EventRegistration.STATUS_PRESENT
        reg.marked_present_at = timezone.now()
        reg.save(update_fields=["status", "marked_present_at"])

        messages.success(
            request, f"{reg.user.username} has been marked as present."
        )
        return redirect("events:event_detail", pk=event_pk)


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "event_cud.html"
    success_url = reverse_lazy("events:events_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = {}
        game_id = self.request.GET.get("game_id")
        if game_id:
            game = get_object_or_404(BoardGame, pk=game_id)
            initial["games"] = [game]
        venue_id = self.request.GET.get("venue_id")
        if venue_id:
            from venues.models import Venue

            venue = Venue.objects.filter(pk=venue_id, is_active=True).first()
            if venue:
                initial["venue"] = venue
        start = timezone.now() + timezone.timedelta(days=5)
        local_start = timezone.localtime(start)
        local_end = timezone.localtime(start + timezone.timedelta(hours=2))
        initial["date_time"] = start
        initial["end_time"] = start + timezone.timedelta(hours=2)
        initial["event_date"] = local_start.date()
        initial["start_time"] = local_start.time().replace(second=0, microsecond=0)
        initial["end_time_field"] = local_end.time().replace(second=0, microsecond=0)
        return initial

    def form_valid(self, form):
        from django.db import transaction

        from venues.reservations import ensure_confirmed_venue_reservation

        user = self.request.user
        form.instance.organizer = user
        form.instance.organizer_name = user.get_full_name() or user.username
        with transaction.atomic():
            response = super().form_valid(form)
            if form.instance.venue_id:
                ensure_confirmed_venue_reservation(form.instance, user)
                messages.success(
                    self.request,
                    "Your partner venue booking is confirmed.",
                )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["button_text"] = "Create"
        context["form_action_url"] = reverse("events:add_event")
        context["cancel_url"] = reverse("events:events_list")
        context["page_title"] = "Create Event"
        context["editing_event_pk"] = None
        return context


class EventUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "event_cud.html"
    context_object_name = "event"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def test_func(self):
        event = self.get_object()
        return is_organizer_or_moderator(self.request.user, event)

    def get_success_url(self):
        return reverse("events:event_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        from django.db import transaction

        from venues.reservations import (
            cancel_venue_reservation,
            ensure_confirmed_venue_reservation,
        )

        user = self.request.user
        form.instance.organizer_name = user.get_full_name() or user.username
        with transaction.atomic():
            response = super().form_valid(form)
            if form.instance.venue_id:
                ensure_confirmed_venue_reservation(form.instance, user)
            else:
                cancel_venue_reservation(form.instance)
        messages.success(
            self.request,
            f"Successfully edited {self.object.name}!",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit"] = True
        context["page_title"] = f"Edit {self.object.name}"
        context["button_text"] = "Edit"
        context["editing_event_pk"] = self.object.pk
        context["cancel_url"] = reverse(
            "events:event_detail",
            kwargs={"pk": self.object.pk},
        )
        context["form_action_url"] = reverse(
            "events:edit_event",
            kwargs={"pk": self.object.pk},
        )
        return context


class EventDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Event
    template_name = "event_cud.html"
    success_url = reverse_lazy("events:events_list")
    context_object_name = "event"

    def test_func(self):
        event = self.get_object()
        return is_organizer_or_moderator(self.request.user, event)

    def delete(self, request, *args, **kwargs):
        event = self.get_object()
        event_name = event.name

        # Snapshot recipients before the event is deleted.
        recipients = list(
            event.registrations.filter(
                status__in=[
                    EventRegistration.STATUS_REGISTERED,
                    EventRegistration.STATUS_PRESENT,
                ]
            )
            .select_related("user")
            .values_list("user__email", flat=True)
        )
        recipients = [e for e in recipients if e]
        dt_str = timezone.localtime(event.date_time).strftime("%d %b %Y %H:%M")
        location = event.location

        response = super().delete(request, *args, **kwargs)
        messages.success(
            request,
            f"Successfully deleted {event_name}!",
        )

        # Notify participants (async).
        for to_email in recipients:
            send_event_cancelled_email.delay(event_name, dt_str, location, to_email)

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = EventForm(instance=self.object)
        for field in form.fields.values():
            field.widget.attrs["disabled"] = "disabled"
        context["form"] = form
        context["delete"] = True
        context["form_action_url"] = reverse(
            "events:delete_event",
            kwargs={"pk": self.object.pk},
        )
        context["button_text"] = "Delete"
        context["page_title"] = f"Delete {self.object.name}"
        context["cancel_url"] = reverse(
            "events:event_detail",
            kwargs={"pk": self.object.pk},
        )
        context["confirm_message"] = (
            f"Are you sure you want to delete {self.object.name}? "
            "This action cannot be undone!"
        )
        return context
