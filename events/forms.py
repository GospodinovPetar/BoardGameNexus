from django import forms
from django.utils.timezone import now
from events.models import Event
from games.models import BoardGame  # Import BoardGame model


class SearchForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=False,
        label="Име на събитие",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Търсене по име на събитие...",
                "class": "form-control",
            }
        ),
    )
    organizer_name = forms.CharField(
        max_length=100,
        required=False,
        label="Организатор",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Име на организатор...",
                "class": "form-control",
            }
        ),
    )
    location = forms.MultipleChoiceField(
        required=False,
        label="Локация",
        widget=forms.CheckboxSelectMultiple,
    )
    min_players = forms.IntegerField(
        required=False,
        label="Мин. играчи",
        widget=forms.NumberInput(attrs={"placeholder": "1", "class": "form-control"}),
    )
    max_players = forms.IntegerField(
        required=False,
        label="Макс. играчи",
        widget=forms.NumberInput(attrs={"placeholder": "100", "class": "form-control"}),
    )
    date_time_before = forms.DateTimeField(
        required=False,
        label="Преди дата и час",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-control"}
        ),
    )
    date_time_after = forms.DateTimeField(
        required=False,
        label="След дата и час",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-control"}
        ),
    )
    games = forms.ModelMultipleChoiceField(
        queryset=BoardGame.objects.all(),
        required=False,
        label="Игри",
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically populate location choices
        self.fields["location"].choices = [
            (loc, loc)
            for loc in Event.objects.values_list("location", flat=True).distinct()
        ]

    SORT_CHOICES = [
        ("name", "Име (А-Я)"),
        ("-name", "Име (Я-А)"),
        ("date_time", "Дата (стари първо)"),
        ("-date_time", "Дата (нови първо)"),
        ("organizer_name", "Организатор (А-Я)"),
        ("-organizer_name", "Организатор (Я-А)"),
        ("location", "Локация (А-Я)"),
        ("-location", "Локация (Я-А)"),
        ("current_players", "Текущи играчи (възходящ)"),
        ("-current_players", "Текущи играчи (низходящ)"),
        ("max_players", "Макс. играчи (възходящ)"),
        ("-max_players", "Макс. играчи (низходящ)"),
    ]
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        label="Сортирай по",
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name",
            "organizer_name",
            "date_time",
            "location",
            "current_players",
            "max_players",
            "description",
            "games",
        ]
        widgets = {
            "date_time": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "name": forms.TextInput(
                attrs={"placeholder": "Как ще кръстиш събитието? Бъди креативен!"}
            ),
            "organizer_name": forms.TextInput(
                attrs={"placeholder": "Кой организира купона?"}
            ),
            "location": forms.TextInput(
                attrs={"placeholder": "Къде ще се вихри забавлението?"}
            ),
            "current_players": forms.NumberInput(
                attrs={"placeholder": "Колко героя вече са се записали?"}
            ),
            "max_players": forms.NumberInput(
                attrs={"placeholder": "Колко максимум могат да се включат?"}
            ),
            "description": forms.Textarea(
                attrs={"placeholder": "Разкажи повече за епичното събитие!"}
            ),
            "games": forms.SelectMultiple(
                attrs={"placeholder": "Кои игри ще спасят положението?"}
            ),
        }
        labels = {
            "name": "Заглавие",
            "organizer_name": "Организатор",
            "date_time": "Дата на провеждане",
            "location": "Къде?",
            "current_players": "Играчи",
            "max_players": "Максимални играчи",
            "description": "Описание",
            "games": "Игри",
        }

    def clean(self):
        cleaned_data = super().clean()
        current_players = cleaned_data.get("current_players")
        max_players = cleaned_data.get("max_players")
        date_time = cleaned_data.get("date_time")

        if current_players is not None and max_players is not None:
            if current_players > max_players:
                self.add_error(
                    "current_players",
                    "Сегашните играчи надхвърлят максималния брой играчи.",
                )
                self.add_error(
                    "max_players",
                    "Максималния брой играчи не може да е по-малък от сегашния.",
                )

        if date_time is not None:
            if date_time < now():
                self.add_error("date_time", "Датата не може да бъде в миналото.")

        return cleaned_data
