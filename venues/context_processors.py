from venues.permissions import user_has_venue_dashboard_access


def venue_nav_context(request):
    match = getattr(request, "resolver_match", None)
    namespace = match.namespace if match else ""
    url_name = match.url_name if match else ""

    return {
        "user_has_venue_dashboard": user_has_venue_dashboard_access(request.user),
        "nav_events_active": namespace == "events",
        "nav_venues_active": namespace == "venues",
        "nav_mission_active": namespace == "web" and url_name == "mission",
        "nav_contact_active": namespace == "web" and url_name == "contact",
        "nav_home_active": namespace == "web" and url_name == "index",
    }
