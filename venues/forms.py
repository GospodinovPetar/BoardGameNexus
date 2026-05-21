from django import forms

from venues.models import VenueReservation


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
