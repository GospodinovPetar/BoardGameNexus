import json
import time

from django.core.cache import cache

SEARCH_TTL = 86400
STALE_SEARCH_TTL = 604800
RECOMMENDED_TTL = 86400
RECOMMENDED_CACHE_KEY = "bgg:recommended:top5"
THING_TTL = 604800
THING_STALE_TTL = 2592000
THING_BATCH_SIZE = 20
LOCK_POLL_INTERVAL = 0.25
LOCK_MAX_WAIT = 5.0


def get_search_cache(query: str) -> list[dict] | None:
    key = _search_key(query)
    raw = cache.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def set_search_cache(query: str, results: list[dict]) -> None:
    cache.set(_search_key(query), json.dumps(results), SEARCH_TTL)
    set_stale_search_cache(query, results)


def get_stale_search_cache(query: str) -> list[dict] | None:
    raw = cache.get(_stale_search_key(query))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def set_stale_search_cache(query: str, results: list[dict]) -> None:
    cache.set(_stale_search_key(query), json.dumps(results), STALE_SEARCH_TTL)


def acquire_search_lock(query: str) -> bool:
    return cache.add(_lock_key(query), 1, timeout=30)


def release_search_lock(query: str) -> None:
    cache.delete(_lock_key(query))


def wait_for_search_cache(query: str, max_wait: float = LOCK_MAX_WAIT) -> list[dict] | None:
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        cached = get_search_cache(query)
        if cached is not None:
            return cached
        time.sleep(LOCK_POLL_INTERVAL)
    return None


def _search_key(query: str) -> str:
    normalized = query.strip().lower()[:200]
    return f"bgg:search:{normalized}"


def _stale_search_key(query: str) -> str:
    normalized = query.strip().lower()[:200]
    return f"bgg:search:stale:{normalized}"


def _lock_key(query: str) -> str:
    normalized = query.strip().lower()[:200]
    return f"bgg:lock:search:{normalized}"


def get_recommended_cache() -> list[dict] | None:
    raw = cache.get(RECOMMENDED_CACHE_KEY)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def set_recommended_cache(results: list[dict]) -> None:
    cache.set(RECOMMENDED_CACHE_KEY, json.dumps(results), RECOMMENDED_TTL)


def _venue_recommended_key(venue_id: int) -> str:
    return f"bgg:recommended:venue:{venue_id}"


def get_venue_recommended_cache(venue_id: int) -> list[dict] | None:
    raw = cache.get(_venue_recommended_key(venue_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def set_venue_recommended_cache(venue_id: int, results: list[dict]) -> None:
    cache.set(_venue_recommended_key(venue_id), json.dumps(results), RECOMMENDED_TTL)


def invalidate_venue_recommended_cache(venue_id: int) -> None:
    cache.delete(_venue_recommended_key(venue_id))


def get_thing_cache(bgg_id: int) -> dict | None:
    raw = cache.get(_thing_key(bgg_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def set_thing_cache(bgg_id: int, data: dict) -> None:
    payload = json.dumps(data)
    cache.set(_thing_key(bgg_id), payload, THING_TTL)
    cache.set(_thing_stale_key(bgg_id), payload, THING_STALE_TTL)


def get_stale_thing_cache(bgg_id: int) -> dict | None:
    raw = cache.get(_thing_stale_key(bgg_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def _thing_key(bgg_id: int) -> str:
    return f"bgg:thing:{int(bgg_id)}"


def _thing_stale_key(bgg_id: int) -> str:
    return f"bgg:thing:stale:{int(bgg_id)}"
