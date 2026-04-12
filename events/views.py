from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from events.forms import EventForm, EventSearchForm
from events.models import Event
from games.models import BoardGame


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
                events_list = events_list.filter(
                    current_players__gte=min_players
                )
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
        return context


class EventDetailView(DetailView):
    model = Event
    template_name = "event_detail.html"
    context_object_name = "event"


class JoinEventView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = self.post(request, *args, **kwargs)
        return response

    def post(self, request, *args, **kwargs):
        pk = kwargs["pk"]
        event = get_object_or_404(Event, pk=pk)

        joined_events = request.session.get("joined_events", [])

        if pk in joined_events:
            messages.warning(request, "You have already joined this event!")
            return redirect("events:event_detail", pk=pk)

        if event.current_players < event.max_players:
            event.current_players += 1
            event.save()

            joined_events.append(pk)
            request.session["joined_events"] = joined_events
            messages.success(request, f"Successfully joined {event.name}!")

        else:
            messages.info(request, "Sorry, all spots are filled.")

        return redirect("events:event_detail", pk=pk)


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "event_cud.html"
    success_url = reverse_lazy("events:events_list")

    def get_initial(self):
        game_id = self.request.GET.get("game_id")
        if game_id:
            game = get_object_or_404(BoardGame, pk=game_id)
            return {"games": [game]}
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["button_text"] = "Create"
        context["form_action_url"] = reverse("events:add_event")
        context["cancel_url"] = reverse("events:events_list")
        context["page_title"] = "Create Event"
        return context


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "event_cud.html"
    context_object_name = "event"

    def get_success_url(self):
        url = reverse("events:event_detail", kwargs={"pk": self.object.pk})
        return url

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


class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    template_name = "event_cud.html"
    success_url = reverse_lazy("events:events_list")
    context_object_name = "event"

    def delete(self, request, *args, **kwargs):
        event = self.get_object()
        event_name = event.name
        response = super().delete(request, *args, **kwargs)
        messages.success(
            request,
            f"Successfully deleted {event_name}!",
        )
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
            f"Are you sure you want to delete {self.object.name}? This action cannot be undone!"
        )
        return context
