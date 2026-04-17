from django.shortcuts import render
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


def custom_404(request, exception):
    return render(request, "404.html", status=404)


def custom_500(request):
    return render(request, "500.html", status=500)
