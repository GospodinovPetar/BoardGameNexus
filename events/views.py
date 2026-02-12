from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from events.forms import CreateEventForm
from events.models import Event


def events_list(request):
    events = Event.objects.all()

    context = {
        'events': events,
    }

    return render(request, 'events.html', context)


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    context = {
        'event': event
    }
    return render(request, 'event_detail.html', context)


def join_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    # Използваме списък в сесията: 'joined_events' = [1, 5, 12]
    joined_events = request.session.get('joined_events', [])

    if pk in joined_events:
        messages.warning(request, "Вече сте се записали за това събитие!")
        return redirect('events:events_list')

    if event.current_players < event.max_players:
        event.current_players += 1
        event.save()

        joined_events.append(pk)
        request.session['joined_events'] = joined_events

        messages.success(request, f"Успешно се присъединихте към {event.name}!")
    else:
        messages.error(request, "Съжаляваме, местата са запълнени.")

    return redirect('events:events_list')


def add_event(request):
    form = CreateEventForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect('events:events_list')

    context = {'form': form}
    return render(request, 'add_event.html', context)