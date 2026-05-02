from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
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
from events.tasks import (
    send_event_cancelled_email,
    send_event_join_email,
    send_event_reminder_email,
    send_removed_from_event_email,
)
from games.models import BoardGame


def _is_organizer_or_mod(user, event):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.groups.filter(name="Moderators").exists():
        return True
    return event.organizer is not None and event.organizer == user


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


class EventListView(ListView):
    model = Event
    template_name = "events.html"
    context_object_name = "events"
    paginate_by = 6

    def get_queryset(self):
        events_list = Event.objects.all()
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
        else:
            context["joined_event_pks"] = set()

        return context


class EventDetailView(DetailView):
    model = Event
    template_name = "event_detail.html"
    context_object_name = "event"

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

        is_organizer = _is_organizer_or_mod(user, event)
        can_edit_event = is_organizer

        user_registration = None
        if user.is_authenticated:
            user_registration = event.registrations.filter(user=user).first()

        all_registrations = (
            event.registrations.select_related("user", "user__profile")
            .exclude(status=EventRegistration.STATUS_REMOVED)
            .order_by("joined_at")
        )

        context.update(
            {
                "is_organizer": is_organizer,
                "can_edit_event": can_edit_event,
                "registrations": all_registrations if is_organizer else [],
                "user_registration": user_registration,
                "attendance_window_open": event.attendance_window_open(),
                "attendance_window_closed": event.attendance_window_closed(),
                "is_before_event": timezone.now() < event.date_time,
                "STATUS_REGISTERED": EventRegistration.STATUS_REGISTERED,
                "STATUS_PRESENT": EventRegistration.STATUS_PRESENT,
                "STATUS_NO_SHOW": EventRegistration.STATUS_NO_SHOW,
            }
        )
        return context


class JoinEventView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pk = kwargs["pk"]
        event = get_object_or_404(Event, pk=pk)

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


class RemoveParticipantView(LoginRequiredMixin, View):
    def post(self, request, event_pk, reg_pk):
        event = get_object_or_404(Event, pk=event_pk)

        if not _is_organizer_or_mod(request.user, event):
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

        if not _is_organizer_or_mod(request.user, event):
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

    def get_initial(self):
        initial = {}
        game_id = self.request.GET.get("game_id")
        if game_id:
            game = get_object_or_404(BoardGame, pk=game_id)
            initial["games"] = [game]
        user = self.request.user
        initial["organizer_name"] = user.get_full_name() or user.username
        return initial

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["button_text"] = "Create"
        context["form_action_url"] = reverse("events:add_event")
        context["cancel_url"] = reverse("events:events_list")
        context["page_title"] = "Create Event"
        return context


class EventUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "event_cud.html"
    context_object_name = "event"

    def test_func(self):
        event = self.get_object()
        return _is_organizer_or_mod(self.request.user, event)

    def get_success_url(self):
        return reverse("events:event_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
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
        return _is_organizer_or_mod(self.request.user, event)

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
