from django.shortcuts import render
from django.views.generic import TemplateView

from events.models import Event
from events.visibility import filter_public_events
from games.models import BoardGame
from venues.models import Venue


class IndexView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event_count"] = filter_public_events(Event.objects.all()).count()
        context["game_count"] = BoardGame.objects.count()
        return context


class MissionView(TemplateView):
    template_name = "mission.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_count = filter_public_events(Event.objects.all()).count()
        game_count = BoardGame.objects.count()
        venue_count = Venue.objects.filter(is_active=True).count()
        context["event_count"] = event_count
        context["game_count"] = game_count
        context["venue_count"] = venue_count
        return context


class ContactView(TemplateView):
    template_name = "contact.html"


def custom_404(request, exception):
    return render(request, "404.html", status=404)


def custom_500(request):
    return render(request, "500.html", status=500)
