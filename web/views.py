from django.views.generic import TemplateView

from events.models import Event
from games.models import BoardGame


class IndexView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_count = Event.objects.count()
        game_count = BoardGame.objects.count()
        context["event_count"] = event_count
        context["game_count"] = game_count
        return context


class MissionView(TemplateView):
    template_name = "mission.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_count = Event.objects.count()
        game_count = BoardGame.objects.count()
        context["event_count"] = event_count
        context["game_count"] = game_count
        return context


class ContactView(TemplateView):
    template_name = "contact.html"
