from django.shortcuts import render
from events.models import Event
from games.models import BoardGame

# Create your views here.


def index(request):
    event_count = Event.objects.count()
    game_count = BoardGame.objects.count()
    context = {
        "event_count": event_count,
        "game_count": game_count,
    }
    return render(request, "home.html", context)


def mission(request):
    event_count = Event.objects.count()
    game_count = BoardGame.objects.count()
    context = {
        "event_count": event_count,
        "game_count": game_count,
    }
    return render(request, "mission.html", context)


def contact_view(request):
    return render(request, "contact.html")
