import logging
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests
from django.conf import settings

from games.models import BoardGame, bgg_thing_url
from games.services.cache import (
    THING_BATCH_SIZE,
    acquire_search_lock,
    get_search_cache,
    get_stale_search_cache,
    get_stale_thing_cache,
    get_thing_cache,
    release_search_lock,
    set_search_cache,
    set_thing_cache,
    wait_for_search_cache,
)

logger = logging.getLogger(__name__)

BGG_BASE = "https://boardgamegeek.com/xmlapi2"
SEARCH_LIMIT = 20
MAX_RETRIES = 5
RETRY_DELAY = 1.5
GATEWAY_STATUSES = (502, 503, 504)
BGG_UNAVAILABLE_MSG = (
    "BoardGameGeek is temporarily unavailable. Try again shortly."
)


class BGGError(Exception):
    pass


class BGGNotFoundError(BGGError):
    pass


def _bgg_token() -> str:
    return (
        getattr(settings, "BGG_API_KEY", None)
        or getattr(settings, "BGG_APPLICATION_TOKEN", None)
        or ""
    ).strip()


def _bgg_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/xml",
        "User-Agent": "BoardGameNexus/1.0",
    }
    token = _bgg_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _require_bgg_token() -> None:
    if not _bgg_token():
        raise BGGError(
            "BGG API key is not configured. Add BGG_API_KEY to your .env file "
            "(create a token at https://boardgamegeek.com/applications)."
        )


def _get_xml(path: str, params: dict | None = None) -> ET.Element:
    _require_bgg_token()
    url = f"{BGG_BASE}/{path}"
    params = params or {}
    last_error = None
    last_status = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                params=params,
                headers=_bgg_headers(),
                timeout=15,
            )
            last_status = response.status_code
            if response.status_code in (401, 403):
                raise BGGError(
                    "BGG rejected the API key. Check BGG_API_KEY in .env "
                    "(Bearer token from boardgamegeek.com/applications)."
                )
            if response.status_code in (202, *GATEWAY_STATUSES):
                time.sleep(RETRY_DELAY * (2**attempt))
                continue
            response.raise_for_status()
            if not response.text.strip():
                raise BGGError("Empty response from BGG")
            return ET.fromstring(response.text)
        except requests.HTTPError as exc:
            last_error = exc
            if last_status in GATEWAY_STATUSES:
                time.sleep(RETRY_DELAY * (2**attempt))
                continue
            raise BGGError(BGG_UNAVAILABLE_MSG) from exc
        except (requests.RequestException, ET.ParseError) as exc:
            last_error = exc
            time.sleep(RETRY_DELAY * (2**attempt))
    if last_status == 202:
        raise BGGError("BGG is still processing the request. Try again in a moment.")
    if last_status in GATEWAY_STATUSES:
        raise BGGError(BGG_UNAVAILABLE_MSG)
    raise BGGError(BGG_UNAVAILABLE_MSG) from last_error


def _fetch_search_results(query: str, limit: int) -> list[dict[str, Any]]:
    root = _get_xml(
        "search",
        {"query": query, "type": "boardgame", "exact": 0},
    )
    results = []
    for item in root.findall("item"):
        bgg_id = int(item.get("id", 0))
        if not bgg_id:
            continue
        title_el = item.find("name")
        title = title_el.get("value", "") if title_el is not None else ""
        year_el = item.find("yearpublished")
        year = None
        if year_el is not None and year_el.get("value"):
            try:
                year = int(year_el.get("value"))
            except ValueError:
                year = None
        results.append(
            {
                "bgg_id": bgg_id,
                "title": title,
                "year_published": year,
            }
        )
        if len(results) >= limit:
            break
    return results


def search_boardgames(
    query: str, limit: int = SEARCH_LIMIT
) -> tuple[list[dict[str, Any]], bool]:
    query = (query or "").strip()
    if len(query) < 2:
        return [], False

    cached = get_search_cache(query)
    if cached is not None:
        return cached[:limit], False

    lock_acquired = acquire_search_lock(query)
    if not lock_acquired:
        waited = wait_for_search_cache(query)
        if waited is not None:
            return waited[:limit], False

    try:
        cached = get_search_cache(query)
        if cached is not None:
            return cached[:limit], False

        results = _fetch_search_results(query, limit)
        set_search_cache(query, results)
        return results[:limit], False
    except BGGError:
        stale = get_stale_search_cache(query)
        if stale is not None:
            logger.warning("Returning stale BGG search cache for query=%r", query)
            return stale[:limit], True
        raise
    finally:
        if lock_acquired:
            release_search_lock(query)


def _parse_int(text: str | None, default: int) -> int:
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def _parse_rank_and_rating(item: ET.Element) -> tuple[int | None, float | None]:
    rank = None
    bayes = None
    ratings = item.find("statistics/ratings")
    if ratings is None:
        return None, None
    bayes_el = ratings.find("bayesaverage")
    if bayes_el is not None and bayes_el.get("value"):
        try:
            bayes = float(bayes_el.get("value"))
        except ValueError:
            bayes = None
    for rank_el in ratings.findall("ranks/rank"):
        if rank_el.get("name") == "boardgame":
            value = rank_el.get("value")
            if value and value != "Not Ranked":
                try:
                    rank = int(value)
                except ValueError:
                    rank = None
            if bayes is None and rank_el.get("bayesaverage"):
                try:
                    bayes = float(rank_el.get("bayesaverage"))
                except ValueError:
                    pass
            break
    return rank, bayes


def _parse_thing_item(item: ET.Element) -> dict[str, Any] | None:
    """Full boardgame payload from a BGG thing item (stats + players + description)."""
    if item.get("type") != "boardgame":
        return None
    bgg_id = int(item.get("id", 0))
    if not bgg_id:
        return None

    title = ""
    for name in item.findall("name"):
        if name.get("type") == "primary":
            title = name.get("value", "")
            break
    if not title and item.findall("name"):
        title = item.findall("name")[0].get("value", "")

    year_el = item.find("yearpublished")
    year = _parse_int(year_el.get("value") if year_el is not None else None, 0) or None

    min_players = 1
    max_players = 4
    min_el = item.find("minplayers")
    max_el = item.find("maxplayers")
    if min_el is not None:
        min_players = _parse_int(min_el.get("value"), min_players)
    if max_el is not None:
        max_players = _parse_int(max_el.get("value"), max_players)
    if min_players > max_players:
        max_players = min_players

    description = ""
    desc_el = item.find("description")
    if desc_el is not None and desc_el.text:
        description = desc_el.text

    image_url = ""
    thumb_el = item.find("thumbnail")
    image_el = item.find("image")
    if thumb_el is not None and thumb_el.text:
        image_url = thumb_el.text
    elif image_el is not None and image_el.text:
        image_url = image_el.text

    bgg_rank, bgg_rating = _parse_rank_and_rating(item)

    return {
        "bgg_id": bgg_id,
        "title": title,
        "year_published": year,
        "min_players": min_players,
        "max_players": max_players,
        "description": description,
        "image_url": image_url,
        "bgg_url": bgg_thing_url(bgg_id),
        "bgg_rank": bgg_rank,
        "bgg_rating": round(bgg_rating, 2) if bgg_rating is not None else None,
    }


def fetch_things_cached(bgg_ids: list[int]) -> dict[int, dict[str, Any]]:
    """
    Return full thing data per bgg_id, using Redis cache and batched BGG /thing calls.
    Missing ids after a failed fetch are omitted from the result.
    """
    ordered = list(dict.fromkeys(int(i) for i in bgg_ids if int(i) > 0))
    if not ordered:
        return {}

    result: dict[int, dict[str, Any]] = {}
    to_fetch: list[int] = []
    for bgg_id in ordered:
        cached = get_thing_cache(bgg_id)
        if cached is not None:
            result[bgg_id] = cached
            continue
        to_fetch.append(bgg_id)

    for chunk_start in range(0, len(to_fetch), THING_BATCH_SIZE):
        chunk = to_fetch[chunk_start : chunk_start + THING_BATCH_SIZE]
        try:
            root = _get_xml(
                "thing",
                {"id": ",".join(str(i) for i in chunk), "stats": 1},
            )
            for item in root.findall("item"):
                parsed = _parse_thing_item(item)
                if parsed:
                    set_thing_cache(parsed["bgg_id"], parsed)
                    result[parsed["bgg_id"]] = parsed
        except BGGError:
            for bgg_id in chunk:
                stale = get_stale_thing_cache(bgg_id)
                if stale is not None:
                    logger.warning("Using stale BGG thing cache for bgg_id=%s", bgg_id)
                    result[bgg_id] = stale
            if not any(bgg_id in result for bgg_id in chunk):
                raise

    return result


def fetch_boardgames_stats_batch(bgg_ids: list[int]) -> list[dict[str, Any]]:
    if not bgg_ids:
        return []
    things = fetch_things_cached(bgg_ids)
    return [things[bgg_id] for bgg_id in bgg_ids if bgg_id in things]


def fetch_boardgame(bgg_id: int) -> dict[str, Any]:
    things = fetch_things_cached([bgg_id])
    if bgg_id not in things:
        raise BGGNotFoundError(f"Board game {bgg_id} not found on BGG")
    return things[bgg_id]


def _boardgame_defaults_from_thing(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": data["title"],
        "year_published": data.get("year_published"),
        "min_players": data.get("min_players", 1),
        "max_players": data.get("max_players", 4),
        "description": data.get("description") or "",
        "image_url": data.get("image_url") or "",
        "bgg_url": data.get("bgg_url") or bgg_thing_url(data["bgg_id"]),
    }


def _boardgame_defaults_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    bgg_id = summary["bgg_id"]
    return {
        "title": summary["title"],
        "year_published": summary.get("year_published"),
        "min_players": summary.get("min_players", 1),
        "max_players": summary.get("max_players", 4),
        "description": summary.get("description") or "",
        "image_url": summary.get("image_url") or "",
        "bgg_url": summary.get("bgg_url") or bgg_thing_url(bgg_id),
    }


def ensure_boardgame(bgg_id: int) -> BoardGame:
    games = ensure_boardgames([bgg_id])
    if not games:
        raise BGGNotFoundError(f"Board game {bgg_id} not found on BGG")
    return games[0]


def ensure_boardgames_from_summaries(summaries: list[dict[str, Any]]) -> list[BoardGame]:
    """
    Create or update local BoardGame rows using summary payloads (e.g. from a
    stats batch fetch) without additional BGG /thing calls.
    """
    if not summaries:
        return []

    ordered_ids = list(dict.fromkeys(int(s["bgg_id"]) for s in summaries if s.get("bgg_id")))
    by_bgg_id = {int(s["bgg_id"]): s for s in summaries if s.get("bgg_id")}
    existing = {
        g.bgg_id: g
        for g in BoardGame.objects.filter(bgg_id__in=ordered_ids)
    }
    need_fetch: list[int] = []

    for bgg_id in ordered_ids:
        if bgg_id in existing:
            continue
        summary = by_bgg_id.get(bgg_id, {})
        if summary.get("title"):
            game, _created = BoardGame.objects.update_or_create(
                bgg_id=bgg_id,
                defaults=_boardgame_defaults_from_summary(summary),
            )
            existing[bgg_id] = game
        else:
            need_fetch.append(bgg_id)

    if need_fetch:
        for game in ensure_boardgames(need_fetch):
            existing[game.bgg_id] = game

    return [existing[bgg_id] for bgg_id in ordered_ids if bgg_id in existing]


def ensure_boardgames(bgg_ids: list[int]) -> list[BoardGame]:
    ordered = list(dict.fromkeys(int(i) for i in bgg_ids if int(i) > 0))
    if not ordered:
        return []

    existing = {
        g.bgg_id: g
        for g in BoardGame.objects.filter(bgg_id__in=ordered)
    }
    missing = [bgg_id for bgg_id in ordered if bgg_id not in existing]
    if missing:
        things = fetch_things_cached(missing)
        for bgg_id in missing:
            data = things.get(bgg_id)
            if not data:
                continue
            game, _created = BoardGame.objects.update_or_create(
                bgg_id=bgg_id,
                defaults=_boardgame_defaults_from_thing(data),
            )
            existing[bgg_id] = game

    return [existing[bgg_id] for bgg_id in ordered if bgg_id in existing]
