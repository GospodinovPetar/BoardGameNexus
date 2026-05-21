def is_venue_staff(user, venue):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return venue.staff.filter(pk=user.pk).exists()


def can_manage_reservation(user, reservation):
    return is_venue_staff(user, reservation.venue)


def user_has_venue_dashboard_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.managed_venues.exists()


def staff_venues_queryset(user):
    from venues.models import Venue

    if not user.is_authenticated:
        return Venue.objects.none()
    if user.is_superuser:
        return Venue.objects.all()
    return user.managed_venues.all()
