import datetime
from django import forms
from games.models import BoardGame, Genre


class GameSearchForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Search by title",
                "class": "form-control",
            }
        ),
    )
    genre = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all(),
        required=False,
        label="Genre",
        widget=forms.CheckboxSelectMultiple,
    )
    min_rating = forms.FloatField(
        required=False,
        label="Min. Rating",
        widget=forms.NumberInput(attrs={"placeholder": "0.0", "class": "form-control"}),
    )
    max_rating = forms.FloatField(
        required=False,
        label="Max. Rating",
        widget=forms.NumberInput(attrs={"placeholder": "5.0", "class": "form-control"}),
    )
    min_players = forms.IntegerField(
        required=False,
        label="Min. Players",
        widget=forms.NumberInput(attrs={"placeholder": "1", "class": "form-control"}),
    )
    max_players = forms.IntegerField(
        required=False,
        label="Max. Players",
        widget=forms.NumberInput(attrs={"placeholder": "100", "class": "form-control"}),
    )
    release_date_before = forms.DateField(
        required=False,
        label="Released before",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    release_date_after = forms.DateField(
        required=False,
        label="Released after",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    SORT_CHOICES = [
        ("title", "Title (A-Z)"),
        ("-title", "Title (Z-A)"),
        ("rating", "Rating (Asc.)"),
        ("-rating", "Rating (Desc.)"),
        ("release_date", "Release Date (Oldest First)"),
        ("-release_date", "Release Date (Newest First)"),
        ("min_players", "Min. Players (Asc.)"),
        ("-min_players", "Min. Players (Desc.)"),
        ("max_players", "Max. Players (Asc.)"),
        ("-max_players", "Max. Players (Desc.)"),
    ]

    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        label="Sort by:",
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
                self.add_error("release_date", "Release date can't be in the future.")

        return cleaned_data
