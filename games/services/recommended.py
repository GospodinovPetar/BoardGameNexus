import logging
from typing import Any

from django.conf import settings

from games.models import BoardGame
from games.services import bgg as bgg_service
from games.services.cache import (
    get_recommended_cache,
    get_venue_recommended_cache,
    set_recommended_cache,
    set_venue_recommended_cache,
)

logger = logging.getLogger(__name__)

RECOMMENDED_LIMIT = 5
BATCH_CHUNK = 20
VENUE_RECOMMENDED_MAX_CANDIDATES = 40


def _candidate_bgg_ids() -> list[int]:
    raw = getattr(settings, "BGG_RECOMMENDED_CANDIDATE_IDS", None)
    if raw:
        return [int(x) for x in raw]
    return [
        224517,
        342942,
        161936,
        266192,
        167791,
        174430,
        12333,
        233078,
        266507,
        187645,
        297562,
        318983,
        220308,
        192291,
        182028,
        295770,
        251247,
        285775,
        124361,
        169786,
        31260,
        164928,
        183394,
        84876,
        173346,
    ]


def _rank_and_pick_top(all_stats: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    with_rank = [g for g in all_stats if g.get("bgg_rank") is not None]
    with_rank.sort(key=lambda g: (g["bgg_rank"], -(g.get("bgg_rating") or 0)))
    top = with_rank[:limit]
    if len(top) < limit:
        seen = {g["bgg_id"] for g in top}
        by_rating = sorted(
            [g for g in all_stats if g["bgg_id"] not in seen],
            key=lambda g: -(g.get("bgg_rating") or 0),
        )
        for g in by_rating:
            top.append(g)
            if len(top) >= limit:
                break
    return top[:limit]


def get_top_rated_boardgames(limit: int = RECOMMENDED_LIMIT) -> list[dict[str, Any]]:
    cached = get_recommended_cache()
    if cached is not None:
        return cached[:limit]

    candidates = _candidate_bgg_ids()
    all_stats: list[dict[str, Any]] = []
    for chunk_start in range(0, len(candidates), BATCH_CHUNK):
        chunk = candidates[chunk_start : chunk_start + BATCH_CHUNK]
        try:
            all_stats.extend(bgg_service.fetch_boardgames_stats_batch(chunk))
        except bgg_service.BGGError:
            logger.exception("Failed to fetch BGG stats for recommended games")

    top = _rank_and_pick_top(all_stats, limit)
    set_recommended_cache(top)
    return top


def get_top_rated_for_venue(venue, limit: int = RECOMMENDED_LIMIT) -> list[dict[str, Any]]:
    venue_id = venue.pk if hasattr(venue, "pk") else int(venue)
    cached = get_venue_recommended_cache(venue_id)
    if cached is not None:
        return cached[:limit]

    bgg_ids = list(
        venue.games.order_by("title").values_list("bgg_id", flat=True)[
            :VENUE_RECOMMENDED_MAX_CANDIDATES
        ]
    )
    if not bgg_ids:
        set_venue_recommended_cache(venue_id, [])
        return []

    all_stats: list[dict[str, Any]] = []
    for chunk_start in range(0, len(bgg_ids), BATCH_CHUNK):
        chunk = bgg_ids[chunk_start : chunk_start + BATCH_CHUNK]
        try:
            all_stats.extend(bgg_service.fetch_boardgames_stats_batch(chunk))
        except bgg_service.BGGError:
            logger.exception(
                "Failed to fetch BGG stats for venue %s recommended games", venue_id
            )

    top = _rank_and_pick_top(all_stats, limit)
    set_venue_recommended_cache(venue_id, top)
    return top


def load_venue_recommended_games(venue, limit: int = RECOMMENDED_LIMIT) -> list[dict[str, Any]]:
    if venue is None:
        return []
    try:
        summaries = get_top_rated_for_venue(venue, limit)
    except bgg_service.BGGError:
        logger.warning("Could not load venue recommended games for venue %s", venue.pk)
        return []

    if not summaries:
        return []

    try:
        games = bgg_service.ensure_boardgames_from_summaries(summaries)
    except bgg_service.BGGError:
        logger.warning("Could not ensure venue recommended games in local cache")
        return []

    by_bgg_id = {g.bgg_id: g for g in games}
    items = []
    for summary in summaries:
        game = by_bgg_id.get(summary["bgg_id"])
        if not game:
            continue
        items.append(
            {
                "game": game,
                "bgg_rank": summary.get("bgg_rank"),
                "bgg_rating": summary.get("bgg_rating"),
            }
        )
    return items


def summaries_to_api_payload(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enrich BGG summaries with local BoardGame ids for API responses."""
    if not summaries:
        return []

    bgg_ids = [s["bgg_id"] for s in summaries]
    local = dict(BoardGame.objects.filter(bgg_id__in=bgg_ids).values_list("bgg_id", "pk"))
    missing_summaries = [s for s in summaries if s["bgg_id"] not in local]

    if missing_summaries:
        try:
            ensured = bgg_service.ensure_boardgames_from_summaries(missing_summaries)
            local.update({g.bgg_id: g.pk for g in ensured})
        except bgg_service.BGGError:
            pass

    out = []
    for s in summaries:
        row = dict(s)
        row["local_id"] = local.get(s["bgg_id"])
        out.append(row)
    return out


def load_recommended_games(limit: int = RECOMMENDED_LIMIT) -> list[dict[str, Any]]:
    """List of {game, bgg_rank, bgg_rating} for templates."""
    try:
        summaries = get_top_rated_boardgames(limit)
    except bgg_service.BGGError:
        logger.warning("Could not load BGG recommended games")
        return []

    if not summaries:
        return []

    try:
        games = bgg_service.ensure_boardgames_from_summaries(summaries)
    except bgg_service.BGGError:
        logger.warning("Could not ensure recommended games in local cache")
        return []

    by_bgg_id = {g.bgg_id: g for g in games}
    items = []
    for summary in summaries:
        game = by_bgg_id.get(summary["bgg_id"])
        if not game:
            continue
        items.append(
            {
                "game": game,
                "bgg_rank": summary.get("bgg_rank"),
                "bgg_rating": summary.get("bgg_rating"),
            }
        )
    return items
