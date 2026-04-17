import sys

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomUser, UserProfile
from .tasks import send_welcome_email


@receiver(post_save, sender=CustomUser, dispatch_uid="accounts.create_user_profile")
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        if instance.email:
            if "test" in sys.argv:
                send_welcome_email(instance.pk)
            else:
                send_welcome_email.delay(instance.pk)
