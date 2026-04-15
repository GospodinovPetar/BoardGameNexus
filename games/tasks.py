import logging

from celery import shared_task

from events.models import Event
from games.models import BoardGame
from reviews.models import GameReview

logger = logging.getLogger(__name__)


@shared_task
def send_weekly_digest():
    game_count = BoardGame.objects.count()
    event_count = Event.objects.count()
    review_count = GameReview.objects.count()

    digest = (
        f"BoardGameNexus — Weekly Digest\n"
        f"Games on platform: {game_count}\n"
        f"Events scheduled: {event_count}\n"
        f"Reviews published: {review_count}"
    )
    logger.info(digest)
    return digest
