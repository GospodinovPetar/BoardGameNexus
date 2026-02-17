from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from games.models import BoardGame
from .forms import SearchForm, GameForm


def get_all_games(request):
    games = BoardGame.objects.all()
    form = SearchForm(request.GET)

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
            games = games.filter(title__icontains=title)
        if genres:
            games = games.filter(genre__in=genres)
        if min_rating is not None:
            games = games.filter(rating__gte=min_rating)
        if max_rating is not None:
            games = games.filter(rating__lte=max_rating)
        if min_players is not None:
            games = games.filter(min_players__gte=min_players)
        if max_players is not None:
            games = games.filter(max_players__lte=max_players)
        if release_date_before:
            games = games.filter(release_date__lte=release_date_before)
        if release_date_after:
            games = games.filter(release_date__gte=release_date_after)

        if sort_by:
            games = games.order_by(sort_by)

    context = {
        "games": games,
        "form": form,
    }

    return render(request, "games.html", context)


def get_game_details(request, pk):
    game = get_object_or_404(BoardGame, pk=pk)

    context = {"game": game}

    return render(request, "game_detail.html", context)


def add_game(request):
    if request.method == "POST":
        form = GameForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("games:games")
    else:
        form = GameForm()

    context = {
        "form": form,
        "page_title": "Добави нова игра",
        "button_text": "Добави",
        "form_action_url": reverse("games:add_game"),
    }

    return render(request, "game_cud.html", context)


def edit_game(request, pk):
    game = get_object_or_404(BoardGame, pk=pk)
    if request.method == "POST":
        form = GameForm(request.POST, instance=game)
        if form.is_valid():
            form.save()
            return redirect("games:game_details", pk=pk)
    else:
        form = GameForm(instance=game)

    context = {
        "form": form,
        "game": game,
        "edit": True,
        "page_title": f"Редактиране на {game.title}",
        "button_text": "Редактирай",
        "form_action_url": reverse("games:edit_game", kwargs={"pk": pk}),
    }

    return render(request, "game_cud.html", context)


def delete_game(request, pk):
    game = get_object_or_404(BoardGame, pk=pk)

    if request.method == "POST":
        game.delete()
        return redirect("games:games")
    else:
        form = GameForm(instance=game)
        for field in form.fields.values():
            field.widget.attrs["readonly"] = "readonly"

    context = {
        "form": form,
        "game": game,
        "delete": True,
        "form_action_url": reverse("games:delete_game", kwargs={"pk": pk}),
        "button_text": "Изтрий",
        "page_title": f"Изтрий {game.title}",
        "confirm_message": f'Сигурни ли сте, че искате да изтриете "{game.title}"? Това действие не може да бъде отменено!',
    }

    return render(request, "game_cud.html", context)
