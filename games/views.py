from django.shortcuts import render, redirect
from games.models import BoardGame
from .forms import BoardGameSearchForm, AddGameForm


def get_all_games(request):
    games = BoardGame.objects.all()
    form = BoardGameSearchForm(request.GET)

    if form.is_valid():
        search_query = form.cleaned_data.get('search_query')

        if search_query:
            games = games.filter(title__icontains=search_query)

    context = {
        'games': games,
        'form': form,
    }

    return render(request, 'games.html', context)

def get_game_details(request, pk):
    game = BoardGame.objects.get(pk=pk)

    context = {'game': game}

    return render(request, 'game_detail.html', context)

def add_game(request):
    form = AddGameForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect('games:games')

    context = {'form': form}

    return render(request, 'add_game.html', context)


