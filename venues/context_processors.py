from venues.permissions import user_has_venue_dashboard_access


def venue_nav_context(request):
    return {
        "user_has_venue_dashboard": user_has_venue_dashboard_access(request.user),
    }
