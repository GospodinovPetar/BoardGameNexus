import datetime
from django import forms
from games.models import BoardGame


class BoardGameSearchForm(forms.Form):
    title = forms.CharField(
        max_length=30,
        min_length=1,
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Search by game title...",
                "class": "form-control me-2",
            }
        ),
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
                attrs={"placeholder": "Как ще кръстиш новата игра? Нещо незабравимо!"}
            ),
            "rating": forms.NumberInput(
                attrs={"placeholder": "Колко звезди от 0 до 5?"}
            ),
            "min_players": forms.NumberInput(
                attrs={"placeholder": "Минимум колко героя са нужни?"}
            ),
            "max_players": forms.NumberInput(
                attrs={"placeholder": "Максимум колко могат да се включат?"}
            ),
            "description": forms.Textarea(
                attrs={"placeholder": "Опиши тази игра като епичен разказ!"}
            ),
            "image_url": forms.URLInput(
                attrs={
                    "placeholder": "Линк към обложката на играта (или остави празно за стандартна)"
                }
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
                    "Минималният брой играчи не може да бъде по-голям от максималния.",
                )
                self.add_error(
                    "max_players",
                    "Максималният брой играчи не може да бъде по-малък от минималния.",
                )

        if rating is not None:
            if rating < 0 or rating > 5:
                self.add_error("rating", "Скалата на рейтинга е от 0 до 5")

        if release_date is not None:
            if release_date > datetime.date.today():
                self.add_error(
                    "release_date", "Датата на издаване не може да е в бъдещето."
                )

        return cleaned_data
