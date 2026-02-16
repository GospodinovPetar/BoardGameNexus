from django import forms
from django.utils.timezone import now

from events.models import Event


class EventSearchForm(forms.Form):
    search_query = forms.CharField(
        max_length=30,
        min_length=1,
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Search by event name...",
                "class": "form-control me-2",
            }
        ),
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
