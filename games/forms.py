import datetime
from django import forms
from games.models import BoardGame, Genre


class GameSearchForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        required=False,
        label="",  # Set label to empty string
        widget=forms.TextInput(
            attrs={
                "placeholder": "Търсене по заглавие на игра...",
                "class": "form-control",
            }
        ),
    )
    genre = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all(),
        required=False,
        label="Жанр",
        widget=forms.CheckboxSelectMultiple,
    )
    min_rating = forms.FloatField(
        required=False,
        label="Минимален рейтинг",
        widget=forms.NumberInput(attrs={"placeholder": "0.0", "class": "form-control"}),
    )
    max_rating = forms.FloatField(
        required=False,
        label="Максимален рейтинг",
        widget=forms.NumberInput(attrs={"placeholder": "5.0", "class": "form-control"}),
    )
    min_players = forms.IntegerField(
        required=False,
        label="Минимален брой играчи",
        widget=forms.NumberInput(attrs={"placeholder": "1", "class": "form-control"}),
    )
    max_players = forms.IntegerField(
        required=False,
        label="Максимален брой играчи",
        widget=forms.NumberInput(attrs={"placeholder": "100", "class": "form-control"}),
    )
    release_date_before = forms.DateField(
        required=False,
        label="Издадена преди",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    release_date_after = forms.DateField(
        required=False,
        label="Издадена след",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    SORT_CHOICES = [
        ("title", "Заглавие (А-Я)"),
        ("-title", "Заглавие (Я-А)"),
        ("rating", "Рейтинг (възходящ)"),
        ("-rating", "Рейтинг (низходящ)"),
        ("release_date", "Дата на издаване (най-стари)"),
        ("-release_date", "Дата на издаване (най-нови)"),
        ("min_players", "Мин. играчи (възходящ)"),
        ("-min_players", "Мин. играчи (низходящ)"),
        ("max_players", "Макс. играчи (възходящ)"),
        ("-max_players", "Макс. играчи (низходящ)"),
    ]

    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        label="Сортирай по",
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class GameForm(forms.ModelForm):
    class Meta:
        model = BoardGame
        fields = [
            "title",
            "genre",
            "release_date",
            "rating",
            "min_players",
            "max_players",
            "description",
            "image_url",
        ]
        widgets = {
            "release_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "title": forms.TextInput(
                attrs={"placeholder": "What's the name of the game?"}
            ),
            "rating": forms.NumberInput(
                attrs={"placeholder": "Whats the rating? (0/5)"}
            ),
            "min_players": forms.NumberInput(attrs={"placeholder": "Min. Players"}),
            "max_players": forms.NumberInput(attrs={"placeholder": "Max. Players"}),
            "description": forms.Textarea(attrs={"placeholder": "Description"}),
            "image_url": forms.URLInput(
                attrs={"placeholder": "URL to the game's photo"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        min_players = cleaned_data.get("min_players")
        max_players = cleaned_data.get("max_players")
        rating = cleaned_data.get("rating")
        release_date = cleaned_data.get("release_date")

        if min_players is not None and max_players is not None:
            if min_players > max_players:
                self.add_error(
                    "min_players",
                    "Minimum players can't be more than maximum players.",
                )
                self.add_error(
                    "max_players",
                    "Maximum players can't be less than minimum players.",
                )

        if rating is not None:
            if rating < 0 or rating > 5:
                self.add_error("rating", "Rating is only from 0 to 5")

        if release_date is not None:
            if release_date > datetime.date.today():
                self.add_error(
                    "release_date", "Release date can't be in the future."
                )

        return cleaned_data
