from django import forms
from django.utils.timezone import now
from events.models import Event
from games.models import BoardGame  # Import BoardGame model


class EventSearchForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=False,
        label="Event Name",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Search by event name...",
                "class": "form-control",
            }
        ),
    )
    organizer_name = forms.CharField(
        max_length=100,
        required=False,
        label="Organizer",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Organizer name...",
                "class": "form-control",
            }
        ),
    )
    location = forms.MultipleChoiceField(
        required=False,
        label="Location",
        widget=forms.CheckboxSelectMultiple,
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
    date_time_before = forms.DateTimeField(
        required=False,
        label="Before Date and Time",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-control"}
        ),
    )
    date_time_after = forms.DateTimeField(
        required=False,
        label="After Date and Time",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-control"}
        ),
    )
    games = forms.ModelMultipleChoiceField(
        queryset=BoardGame.objects.all(),
        required=False,
        label="Games",
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].choices = [
            (loc, loc)
            for loc in Event.objects.values_list("location", flat=True).distinct()
        ]

    SORT_CHOICES = [
        ("name", "Name (A-Z)"),
        ("-name", "Name (Z-A)"),
        ("date_time", "Date (Oldest First)"),
        ("-date_time", "Date (Newest First)"),
        ("organizer_name", "Organizer (A-Z)"),
        ("-organizer_name", "Organizer (Z-A)"),
        ("location", "Location (A-Z)"),
        ("-location", "Location (Z-A)"),
        ("current_players", "Current Players (Asc)"),
        ("-current_players", "Current Players (Desc)"),
        ("max_players", "Max Players (Asc)"),
        ("-max_players", "Max Players (Desc)"),
    ]
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        label="Sort By",
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
            "date_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "name": forms.TextInput(
                attrs={"placeholder": "What will you call the event? Be creative!"}
            ),
            "organizer_name": forms.TextInput(
                attrs={"placeholder": "Who's organizing the party?"}
            ),
            "location": forms.TextInput(
                attrs={"placeholder": "Where will the fun be happening?"}
            ),
            "current_players": forms.NumberInput(
                attrs={"placeholder": "How many heroes have already signed up?"}
            ),
            "max_players": forms.NumberInput(
                attrs={"placeholder": "How many can join at most?"}
            ),
            "description": forms.Textarea(
                attrs={"placeholder": "Tell us more about the epic event!"}
            ),
            "games": forms.CheckboxSelectMultiple(),
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
                    "Current players cannot exceed maximum players.",
                )
                self.add_error(
                    "max_players",
                    "Maximum players cannot be less than current players.",
                )

        if date_time is not None:
            if date_time < now():
                self.add_error("date_time", "Date cannot be in the past.")

        return cleaned_data
