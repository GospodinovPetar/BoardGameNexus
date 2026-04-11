from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class GameReview(models.Model):
    game = models.ForeignKey(
        "games.BoardGame",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [["game", "author"]]
        verbose_name = "Review"
        verbose_name_plural = "Reviews"

    def __str__(self):
        return f"{self.author.username}'s review of {self.game.title}"

    def get_absolute_url(self):
        return reverse("reviews:review_detail", kwargs={"pk": self.pk})


class UserCollection(models.Model):
    STATUS_CHOICES = [
        ("want", "Want to Play"),
        ("playing", "Currently Playing"),
        ("played", "Played"),
        ("owned", "Owned"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collections",
    )
    game = models.ForeignKey(
        "games.BoardGame",
        on_delete=models.CASCADE,
        related_name="in_collections",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="want",
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [["user", "game"]]
        verbose_name = "User Collection"
        verbose_name_plural = "User Collections"
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.user.username} — {self.game.title} ({self.status})"
