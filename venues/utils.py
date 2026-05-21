from urllib.parse import quote_plus


def build_google_maps_url(address: str) -> str:
    """Return a Google Maps search URL for an address (no API key required)."""
    if not address or not address.strip():
        return ""
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(address.strip())}"
