from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q  # Import Q for complex lookups

from events.forms import EventSearchForm, EventForm
from events.models import Event


def events_list(request):
    events = Event.objects.all()
    form = EventSearchForm(request.GET)

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
            events = events.filter(name__icontains=name)
        if organizer_name:
            events = events.filter(organizer_name__icontains=organizer_name)
        if locations:
            events = events.filter(location__in=locations)
        if min_players is not None:
            events = events.filter(current_players__gte=min_players)
        if max_players is not None:
            events = events.filter(max_players__lte=max_players)
        if date_time_before:
            events = events.filter(date_time__lte=date_time_before)
        if date_time_after:
            events = events.filter(date_time__gte=date_time_after)
        if games:
            events = events.filter(games__in=games).distinct()

        if sort_by:
            events = events.order_by(sort_by)

    context = {
        "events": events,
        "form": form,
    }

    return render(request, "events.html", context)


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    context = {"event": event}
    return render(request, "event_detail.html", context)


def join_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    # Използваме списък в сесията 'joined_events' = [1, 5, 12]
    joined_events = request.session.get("joined_events", [])

    if pk in joined_events:
        messages.warning(request, "Вече сте се записали за това събитие!")
        return redirect("events:events_list")

    if event.current_players < event.max_players:
        event.current_players += 1
        event.save()

        joined_events.append(pk)
        request.session["joined_events"] = joined_events
        messages.success(request, f"Успешно се присъединихте към {event.name}!")

    else:
        messages.error(request, "Съжаляваме, местата са запълнени.")

    return redirect("events:events_list")


def add_event(request):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("events:events_list")
    else:
        form = EventForm()

    context = {
        "form": form,
        "button_text": "Създай",
        "page_title": f"Създаване на събитие",
    }
    return render(request, "event_cud.html", context)


def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f"Успешно редактирахте {event.name}!")
            return redirect("events:event_detail", pk=pk)
    else:
        form = EventForm(instance=event)

    context = {
        "form": form,
        "event": event,
        "edit": True,
        "page_title": f"Редактиране на {event.name}",
        "button_text": "Редактирай",
        "form_action_url": reverse("events:edit_event", kwargs={"pk": pk}),
    }

    return render(request, "event_cud.html", context)


def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        event.delete()
        messages.success(request, f"Успешно изтрихте {event.name}!")
        return redirect("events:events_list")
    else:
        form = EventForm(instance=event)
        for field in form.fields.values():
            field.widget.attrs["readonly"] = "readonly"

    context = {
        "form": form,
        "event": event,
        "delete": True,
        "form_action_url": reverse("events:delete_event", kwargs={"pk": pk}),
        "button_text": "Изтрий",
        "page_title": f"Изтрий {event.name}",
        "confirm_message": f"Сигурни ли сте, че искате да изтриете {event.name}? Това действие не може да бъде отменено!",
    }

    return render(request, "event_cud.html", context)
