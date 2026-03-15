from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_future_date(value):
    now = timezone.now()
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    if value < now:
        raise ValidationError("Event date and time cannot be in the past.")