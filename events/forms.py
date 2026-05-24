from datetime import datetime, timedelta

from django import forms
from django.utils import timezone
from django.utils.timezone import now
from events.models import Event
from games.models import BoardGame
from venues.availability import (
    event_within_working_hours,
    has_venue_booking_availability,
    merge_contiguous_hour_slots,
    parse_venue_time_slot_values,
)
from venues.models import Venue

VENUE_MAX_PLAYERS = 10
VENUE_MIN_DURATION = timedelta(hours=1)


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
        widget=forms.SelectMultiple(attrs={"class": "d-none"}),
    )
    game_title = forms.CharField(
        required=False,
        label="Game title",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Filter by game title…",
                "class": "form-control",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        venue_locations = Venue.objects.filter(is_active=True).values_list(
            "name", flat=True
        )
        event_locations = Event.objects.values_list("location", flat=True).distinct()
        all_locations = sorted(set(list(venue_locations) + list(event_locations)))
        self.fields["location"].choices = [(loc, loc) for loc in all_locations if loc]

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
    venue = forms.ModelChoiceField(
        queryset=Venue.objects.filter(is_active=True).order_by("name"),
        required=False,
        label="Registered venue",
        empty_label="— Independent location —",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_venue"}),
    )
    event_date = forms.DateField(
        required=False,
        label="Date",
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "id": "id_event_date"}
        ),
    )
    start_time = forms.TimeField(
        required=False,
        label="Start time",
        widget=forms.TimeInput(
            attrs={"class": "form-control", "type": "time", "id": "id_start_time"}
        ),
    )
    end_time_field = forms.TimeField(
        required=False,
        label="End time",
        widget=forms.TimeInput(
            attrs={
                "class": "form-control",
                "type": "time",
                "id": "id_venue_end_time",
            }
        ),
    )
    venue_time_slots = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_venue_time_slots"}),
    )

    class Meta:
        model = Event
        fields = [
            "name",
            "date_time",
            "end_time",
            "venue",
            "location",
            "current_players",
            "max_players",
            "description",
            "games",
        ]
        widgets = {
            "date_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local", "id": "id_date_time"}
            ),
            "end_time": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                    "id": "id_event_end_datetime",
                }
            ),
            "name": forms.TextInput(
                attrs={"placeholder": "What will you call the event? Be creative!"}
            ),
            "location": forms.TextInput(
                attrs={
                    "placeholder": "Where will the fun be happening?",
                    "id": "id_location",
                }
            ),
            "current_players": forms.NumberInput(
                attrs={"placeholder": "How many heroes have already signed up?"}
            ),
            "max_players": forms.NumberInput(
                attrs={"placeholder": "How many players do you expect?"}
            ),
            "description": forms.Textarea(
                attrs={"placeholder": "Tell us more about the epic event!"}
            ),
            "games": forms.MultipleHiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["location"].required = False
        self.fields["games"].required = False
        self.fields["max_players"].label = "Expected players"
        self.using_venue_schedule = False

        venue = self._selected_venue()
        if venue:
            self.using_venue_schedule = True
            self.fields["venue"].initial = venue.pk
            self.fields["games"].queryset = venue.games.all().order_by("title")
            self.fields["date_time"].required = False
            self.fields["end_time"].required = False
            self.fields["date_time"].widget = forms.HiddenInput()
            self.fields["end_time"].widget = forms.HiddenInput()
            self.fields["event_date"].required = True
            self.fields["start_time"].required = True
            self.fields["end_time_field"].required = True
            self.fields["venue_time_slots"].required = False
            self._init_venue_schedule_from_instance()
            self._init_venue_time_slots_from_instance()
        else:
            self.fields["games"].queryset = BoardGame.objects.all().order_by("title")
        if self.data:
            posted_ids = self.data.getlist("games")
            if posted_ids:
                self.fields["games"].queryset = BoardGame.objects.filter(
                    pk__in=posted_ids
                ).order_by("title")
        if not venue:
            self.fields["event_date"].required = False
            self.fields["start_time"].required = False
            self.fields["end_time_field"].required = False
            self.fields["venue_time_slots"].widget = forms.HiddenInput()

    def _init_venue_schedule_from_instance(self):
        if self.instance and self.instance.pk and self.instance.date_time:
            local_start = timezone.localtime(self.instance.date_time)
            local_end = timezone.localtime(self.instance.end_time)
            self.fields["event_date"].initial = local_start.date()
            self.fields["start_time"].initial = local_start.time().replace(
                second=0, microsecond=0
            )
            self.fields["end_time_field"].initial = local_end.time().replace(
                second=0, microsecond=0
            )

    def _init_venue_time_slots_from_instance(self):
        if not self.instance or not self.instance.pk:
            return
        if not self.instance.venue_id or not self.instance.date_time:
            return
        from venues.availability import hour_slot_starts_in_range

        starts = list(
            hour_slot_starts_in_range(
                self.instance.date_time,
                self.instance.end_time,
            )
        )
        if starts:
            self.fields["venue_time_slots"].initial = ",".join(
                timezone.localtime(dt).isoformat() for dt in starts
            )

    def _selected_venue(self):
        venue_pk = None
        if self.data.get("venue"):
            venue_pk = self.data.get("venue")
        elif self.initial.get("venue"):
            initial = self.initial.get("venue")
            venue_pk = initial.pk if hasattr(initial, "pk") else initial
        elif self.instance and self.instance.pk and self.instance.venue_id:
            venue_pk = self.instance.venue_id
        if venue_pk:
            return Venue.objects.filter(pk=venue_pk, is_active=True).first()
        return None

    def _exclude_event_id(self):
        if self.instance and self.instance.pk:
            return self.instance.pk
        return None

    def _combine_date_and_time(self, on_date, at_time):
        tz = timezone.get_current_timezone()
        naive = datetime.combine(on_date, at_time)
        return timezone.make_aware(naive, tz)

    def _apply_venue_schedule_to_datetimes(self, cleaned_data):
        event_date = cleaned_data.get("event_date")
        start_time = cleaned_data.get("start_time")
        end_time_only = cleaned_data.get("end_time_field")

        if not event_date:
            self.add_error("event_date", "Choose a date for the event.")
            return
        if not start_time:
            self.add_error("start_time", "Choose a start time.")
            return
        if not end_time_only:
            self.add_error("end_time_field", "Choose an end time.")
            return

        date_time = self._combine_date_and_time(event_date, start_time)
        end_time = self._combine_date_and_time(event_date, end_time_only)
        cleaned_data["date_time"] = date_time
        cleaned_data["end_time"] = end_time

    def _apply_venue_slots_to_datetimes(self, cleaned_data, venue):
        raw_slots = cleaned_data.get("venue_time_slots", "")
        slot_starts = parse_venue_time_slot_values(raw_slots)
        if not slot_starts:
            self._apply_venue_schedule_to_datetimes(cleaned_data)
            return

        try:
            date_time, end_time = merge_contiguous_hour_slots(slot_starts)
        except ValueError as exc:
            self.add_error("venue_time_slots", str(exc))
            return

        local_starts = {timezone.localtime(dt).date() for dt in slot_starts}
        if len(local_starts) != 1:
            self.add_error("venue_time_slots", "All selected hours must be on the same day.")
            return

        cleaned_data["date_time"] = date_time
        cleaned_data["end_time"] = end_time
        cleaned_data["event_date"] = timezone.localtime(date_time).date()
        cleaned_data["start_time"] = timezone.localtime(date_time).time().replace(
            second=0, microsecond=0
        )
        cleaned_data["end_time_field"] = timezone.localtime(end_time).time().replace(
            second=0, microsecond=0
        )

    def _venue_player_cap(self, venue):
        return min(VENUE_MAX_PLAYERS, venue.capacity)

    def clean(self):
        cleaned_data = super().clean()
        current_players = cleaned_data.get("current_players")
        max_players = cleaned_data.get("max_players")
        venue = cleaned_data.get("venue")
        location = (cleaned_data.get("location") or "").strip()
        games = cleaned_data.get("games")

        if venue:
            self._apply_venue_slots_to_datetimes(cleaned_data, venue)

        date_time = cleaned_data.get("date_time")
        end_time = cleaned_data.get("end_time")

        if current_players is not None and max_players is not None:
            if current_players > max_players:
                self.add_error(
                    "current_players",
                    "Current players cannot exceed maximum players.",
                )

        if venue:
            if not venue.is_active:
                self.add_error("venue", "This venue is not accepting bookings.")
            cleaned_data["location"] = venue.display_location()
            venue_game_ids = set(venue.games.values_list("pk", flat=True))
            if games:
                invalid = [g for g in games if g.pk not in venue_game_ids]
                if invalid:
                    self.add_error(
                        "games",
                        "Selected games must be available at the chosen venue.",
                    )
            player_cap = self._venue_player_cap(venue)
            if max_players is not None and max_players > player_cap:
                self.add_error(
                    "max_players",
                    f"This venue allows at most {player_cap} players per event "
                    f"(venue capacity {venue.capacity}, limit {VENUE_MAX_PLAYERS}).",
                )
            if current_players is not None and current_players > player_cap:
                self.add_error(
                    "current_players",
                    f"This venue allows at most {player_cap} players per event.",
                )
        elif not location:
            self.add_error(
                "location",
                "Enter a location or select a registered venue.",
            )

        schedule_error_field = "start_time" if venue else "date_time"

        if date_time is not None and date_time < now():
            self.add_error(schedule_error_field, "The event cannot be scheduled in the past.")

        if date_time and end_time:
            if end_time <= date_time:
                end_field = "end_time_field" if venue else "end_time"
                self.add_error(end_field, "End time must be after the start time.")
            elif venue and (end_time - date_time) < VENUE_MIN_DURATION:
                self.add_error(
                    "end_time_field",
                    "Partner venue bookings must be at least 1 hour long.",
                )

        if venue and date_time and end_time and not self.errors:
            if not event_within_working_hours(venue, date_time, end_time):
                self.add_error(
                    "start_time",
                    f"Event must fit within venue working hours "
                    f"({venue.working_hours_display}).",
                )
            elif max_players and not has_venue_booking_availability(
                venue,
                date_time,
                end_time,
                guests_needed=max_players,
                exclude_event_id=self._exclude_event_id(),
            ):
                self.add_error(
                    "venue_time_slots",
                    "Not enough tables or guest capacity for the selected hours "
                    f"with {max_players} players. Adjust times, player count, or hours.",
                )

        return cleaned_data
