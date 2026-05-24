from django import forms

from games.models import BoardGame
from venues.models import Venue, VenueReservation


class VenueSearchForm(forms.Form):
    name = forms.CharField(
        required=False,
        label="Venue name",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Search by venue name...",
                "class": "form-control",
            }
        ),
    )
    city = forms.CharField(
        required=False,
        label="City",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Filter by city...",
                "class": "form-control",
            }
        ),
    )


class VenueForm(forms.ModelForm):
    games = forms.ModelMultipleChoiceField(
        queryset=BoardGame.objects.all(),
        required=False,
        widget=forms.MultipleHiddenInput(),
    )

    class Meta:
        model = Venue
        fields = [
            "name",
            "description",
            "address",
            "city",
            "phone",
            "email",
            "website",
            "capacity",
            "table_count",
            "hourly_rate",
            "opens_at",
            "closes_at",
            "is_active",
            "image",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "opens_at": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "closes_at": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["games"].initial = self.instance.games.all()
        if self.data:
            posted_ids = self.data.getlist("games")
            if posted_ids:
                self.fields["games"].queryset = BoardGame.objects.filter(
                    pk__in=posted_ids
                )


class ReservationDashboardForm(forms.Form):
    VIEW_DAY = "day"
    VIEW_WEEK = "week"
    VIEW_MONTH = "month"
    VIEW_ALL = "all"
    VIEW_PAST = "past"
    VIEW_CHOICES = [
        (VIEW_DAY, "Today's occupancy"),
        (VIEW_WEEK, "Week"),
        (VIEW_MONTH, "Month"),
        (VIEW_ALL, "All bookings"),
        (VIEW_PAST, "Past bookings"),
    ]
    PERIOD_VIEWS = {VIEW_DAY, VIEW_WEEK, VIEW_MONTH}

    view = forms.ChoiceField(
        choices=VIEW_CHOICES,
        required=False,
        initial=VIEW_WEEK,
        widget=forms.Select(
            attrs={"class": "form-select", "id": "dashboard-view"},
        ),
    )
    date = forms.DateField(
        required=False,
        label="Reference date",
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control", "id": "dashboard-date"},
        ),
    )
    status = forms.ChoiceField(
        choices=[("", "All statuses")] + list(VenueReservation.STATUS_CHOICES),
        required=False,
        initial=VenueReservation.STATUS_CONFIRMED,
        widget=forms.Select(
            attrs={"class": "form-select", "id": "dashboard-status"},
        ),
    )
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "dashboard-search",
                "placeholder": "Event or organizer — press Enter to search",
                "autocomplete": "off",
            }
        ),
    )


class StaffCancelReservationForm(forms.Form):
    staff_note = forms.CharField(
        required=False,
        label="Note to organizer (optional)",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
