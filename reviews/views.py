from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from games.models import BoardGame

from .forms import ReviewForm
from .models import GameReview


class ReviewListView(ListView):
    model = GameReview
    template_name = "reviews/reviews_list.html"
    context_object_name = "reviews"
    paginate_by = 8

    def get_queryset(self):
        queryset = GameReview.objects.select_related("game", "author").all()
        game_param = self.request.GET.get("game")
        if game_param and str(game_param).isdigit():
            queryset = queryset.filter(game_id=int(game_param))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "All Reviews"
        game_param = self.request.GET.get("game")
        if game_param and str(game_param).isdigit():
            context["filtered_game"] = get_object_or_404(
                BoardGame.objects.only("pk", "title"),
                pk=int(game_param),
            )
        return context


class ReviewDetailView(DetailView):
    model = GameReview
    template_name = "reviews/review_detail.html"
    context_object_name = "review"

    def get_queryset(self):
        return GameReview.objects.select_related("game", "author")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        review = self.object
        context["can_edit_review"] = user.is_authenticated and (
            user == review.author
            or user.groups.filter(name="Moderators").exists()
        )
        return context


class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = GameReview
    form_class = ReviewForm
    template_name = "reviews/review_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.game = get_object_or_404(BoardGame, pk=self.kwargs["game_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        context["page_title"] = "Write a Review"
        return context

    def form_valid(self, form):
        if GameReview.objects.filter(
            game_id=self.kwargs["game_pk"],
            author=self.request.user,
        ).exists():
            messages.error(self.request, "You have already reviewed this game.")
            return self.form_invalid(form)
        form.instance.author = self.request.user
        form.instance.game = self.game
        messages.success(self.request, "Your review was posted.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("games:game_details", kwargs={"pk": self.object.game.pk})


class ReviewUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = GameReview
    form_class = ReviewForm
    template_name = "reviews/review_form.html"

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.author or self.request.user.groups.filter(
            name="Moderators"
        ).exists()

    def get_success_url(self):
        return reverse("games:game_details", kwargs={"pk": self.object.game.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Edit Review"
        context["edit"] = True
        context["game"] = self.object.game
        return context


class ReviewDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = GameReview
    template_name = "reviews/review_confirm_delete.html"
    context_object_name = "review"

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.author or self.request.user.groups.filter(
            name="Moderators"
        ).exists()

    def get_success_url(self):
        return reverse("games:game_details", kwargs={"pk": self.object.game.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Review deleted.")
        return super().delete(request, *args, **kwargs)
