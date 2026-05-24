from games.models import BoardGame, bgg_thing_url


def create_test_boardgame(
    *,
    bgg_id: int = 13,
    title: str = "Catan",
    year_published: int | None = 1995,
    min_players: int = 2,
    max_players: int = 4,
    **kwargs,
) -> BoardGame:
    defaults = {
        "title": title,
        "year_published": year_published,
        "min_players": min_players,
        "max_players": max_players,
        "description": kwargs.pop("description", ""),
        "image_url": kwargs.pop("image_url", ""),
        "bgg_url": kwargs.pop("bgg_url", bgg_thing_url(bgg_id)),
    }
    defaults.update(kwargs)
    return BoardGame.objects.create(bgg_id=bgg_id, **defaults)
