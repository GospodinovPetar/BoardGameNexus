import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def send_welcome_email(user_id):
    user = User.objects.get(pk=user_id)
    name = user.first_name or user.username
    subject = "Welcome to BoardGameNexus!"
    message = (
        f"Hi {name},\n\n"
        "Welcome to BoardGameNexus! You can now browse games, join events, "
        "and write reviews.\n\n"
        "Happy gaming!"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    logger.info("Welcome email sent to %s", user.email)
