from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_future_date(value):
    if value < timezone.now():
        raise ValidationError("Event date and time cannot be in the past.")
