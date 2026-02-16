from django.shortcuts import render, redirect
from django.urls import reverse

from games.models import BoardGame
from .forms import BoardGameSearchForm, GameForm


def get_all_games(request):
    games = BoardGame.objects.all()
    form = BoardGameSearchForm(request.GET)

    if form.is_valid():
        search_query = form.cleaned_data.get("title")

        if search_query:
            games = games.filter(title__icontains=search_query)

    context = {
        "games": games,
        "form": form,
    }

    return render(request, "games.html", context)


def get_game_details(request, pk):
    game = BoardGame.objects.get(pk=pk)

    context = {"game": game}

    return render(request, "game_detail.html", context)


def add_game(request):
    if request.method == "POST":
        form = GameForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("games:games")
    else:  # GET request
        form = GameForm()

    context = {
        "form": form,
        "page_title": "Добави нова игра",
        "button_text": "Добави",
        "form_action_url": redirect("games:add_game"),
    }

    return render(request, "game.html", context)


def edit_game(request, pk):
    game = BoardGame.objects.get(pk=pk)
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

    return render(request, "game.html", context)


def delete_game(request, pk):
    game = BoardGame.objects.get(pk=pk)

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

    return render(request, "game.html", context)
