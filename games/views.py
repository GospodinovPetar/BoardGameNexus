from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Avg, FloatField, Prefetch, Value
from django.db.models.functions import Coalesce
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from games.models import BoardGame
from reviews.models import GameReview
from .forms import GameForm, GameSearchForm


def _games_with_review_avg(queryset):
    return queryset.annotate(
        review_avg=Coalesce(
            Avg("reviews__rating"),
            Value(0.0),
            output_field=FloatField(),
        ),
    )


class GameListView(ListView):
    model = BoardGame
    template_name = "games.html"
    context_object_name = "games"
    paginate_by = 6

    def get_queryset(self):
        games_list = _games_with_review_avg(BoardGame.objects.all())
        form = GameSearchForm(self.request.GET)

        if form.is_valid():
            title = form.cleaned_data.get("title")
            genres = form.cleaned_data.get("genre")
            min_rating = form.cleaned_data.get("min_rating")
            max_rating = form.cleaned_data.get("max_rating")
            min_players = form.cleaned_data.get("min_players")
            max_players = form.cleaned_data.get("max_players")
            release_date_before = form.cleaned_data.get("release_date_before")
            release_date_after = form.cleaned_data.get("release_date_after")
            sort_by = form.cleaned_data.get("sort_by")

            if title:
                games_list = games_list.filter(title__icontains=title)
            if genres:
                games_list = games_list.filter(genre__in=genres)
            if min_rating is not None:
                games_list = games_list.filter(review_avg__gte=min_rating)
            if max_rating is not None:
                games_list = games_list.filter(review_avg__lte=max_rating)
            if min_players is not None:
                games_list = games_list.filter(min_players__gte=min_players)
            if max_players is not None:
                games_list = games_list.filter(max_players__lte=max_players)
            if release_date_before:
                games_list = games_list.filter(
                    release_date__lte=release_date_before
                )
            if release_date_after:
                games_list = games_list.filter(
                    release_date__gte=release_date_after
                )

            if sort_by:
                sort_map = {
                    "rating": "review_avg",
                    "-rating": "-review_avg",
                }
                games_list = games_list.order_by(sort_map.get(sort_by, sort_by))

        return games_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context["page_obj"]
        context["games"] = page_obj
        form = GameSearchForm(self.request.GET)
        context["form"] = form
        return context


class GameDetailView(DetailView):
    model = BoardGame
    template_name = "game_detail.html"
    context_object_name = "game"

    def get_queryset(self):
        queryset = _games_with_review_avg(BoardGame.objects.all())
        queryset = queryset.prefetch_related(
            Prefetch(
                "reviews",
                queryset=GameReview.objects.select_related("author").order_by(
                    "-created_at"
                ),
            )
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        game = context["game"]
        reviews = game.reviews.all()
        context["reviews"] = reviews
        return context


class GameCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = BoardGame
    form_class = GameForm
    template_name = "game_cud.html"
    success_url = reverse_lazy("games:games")

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(
            name="Moderators"
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add a new game"
        context["button_text"] = "Add"
        context["cancel_url"] = reverse("games:games")
        context["form_action_url"] = reverse("games:add_game")
        return context


class GameUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = BoardGame
    form_class = GameForm
    template_name = "game_cud.html"
    context_object_name = "game"

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(
            name="Moderators"
        ).exists()

    def get_success_url(self):
        url = reverse("games:game_details", kwargs={"pk": self.object.pk})
        return url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit"] = True
        context["page_title"] = f"Editing {self.object.title}"
        context["button_text"] = "Edit"
        context["cancel_url"] = reverse(
            "games:game_details",
            kwargs={"pk": self.object.pk},
        )
        context["form_action_url"] = reverse(
            "games:edit_game",
            kwargs={"pk": self.object.pk},
        )
        return context


class GameDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = BoardGame
    template_name = "game_cud.html"
    success_url = reverse_lazy("games:games")
    context_object_name = "game"

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(
            name="Moderators"
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = GameForm(instance=self.object)
        for field in form.fields.values():
            field.widget.attrs["disabled"] = "disabled"
        context["form"] = form
        context["delete"] = True
        context["form_action_url"] = reverse(
            "games:delete_game",
            kwargs={"pk": self.object.pk},
        )
        context["button_text"] = "Delete"
        context["page_title"] = f"Delete {self.object.title}"
        context["cancel_url"] = reverse(
            "games:game_details",
            kwargs={"pk": self.object.pk},
        )
        context["confirm_message"] = (
            f'Are you sure you want to delete "{self.object.title}"? This action cannot be undone!'
        )
        return context
