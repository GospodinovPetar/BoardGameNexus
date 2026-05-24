from rest_framework import serializers

from accounts.models import CustomUser, UserProfile
from events.models import Event
from games.models import BoardGame
from reviews.models import GameReview, UserCollection


class BoardGameSerializer(serializers.ModelSerializer):
    review_avg = serializers.SerializerMethodField()

    class Meta:
        model = BoardGame
        fields = [
            "id",
            "bgg_id",
            "title",
            "year_published",
            "min_players",
            "max_players",
            "description",
            "image_url",
            "bgg_url",
            "review_avg",
        ]
        read_only_fields = fields

    def get_review_avg(self, obj):
        avg = getattr(obj, "review_avg", None)
        if avg is None:
            return 0.0
        return round(float(avg), 2)


class BoardGameSearchResultSerializer(serializers.Serializer):
    bgg_id = serializers.IntegerField()
    title = serializers.CharField()
    year_published = serializers.IntegerField(allow_null=True, required=False)


class BoardGameRecommendedSerializer(serializers.Serializer):
    bgg_id = serializers.IntegerField()
    title = serializers.CharField()
    year_published = serializers.IntegerField(allow_null=True, required=False)
    image_url = serializers.CharField(required=False, allow_blank=True)
    bgg_url = serializers.URLField(required=False, allow_blank=True)
    bgg_rank = serializers.IntegerField(allow_null=True, required=False)
    bgg_rating = serializers.FloatField(allow_null=True, required=False)
    local_id = serializers.IntegerField(allow_null=True, required=False)


class BoardGameEnsureSerializer(serializers.Serializer):
    bgg_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class EventSerializer(serializers.ModelSerializer):
    games = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=BoardGame.objects.all(),
    )
    has_free_spots = serializers.SerializerMethodField()
    google_maps_url = serializers.SerializerMethodField()
    venue_total_price = serializers.SerializerMethodField()
    venue_price_per_person = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "description",
            "date_time",
            "end_time",
            "location",
            "venue",
            "organizer_name",
            "current_players",
            "max_players",
            "games",
            "has_free_spots",
            "google_maps_url",
            "venue_total_price",
            "venue_price_per_person",
        ]
        read_only_fields = [
            "has_free_spots",
            "google_maps_url",
            "venue_total_price",
            "venue_price_per_person",
        ]

    def get_has_free_spots(self, obj):
        return obj.has_free_spots()

    def get_google_maps_url(self, obj):
        return obj.google_maps_url()

    def get_venue_total_price(self, obj):
        return obj.venue_total_price()

    def get_venue_price_per_person(self, obj):
        return obj.venue_price_per_person()


class GameReviewSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    game_title = serializers.CharField(source="game.title", read_only=True)

    class Meta:
        model = GameReview
        fields = [
            "id",
            "game",
            "author",
            "author_username",
            "game_title",
            "title",
            "content",
            "rating",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author", "author_username", "game_title", "created_at", "updated_at"]


class UserCollectionSerializer(serializers.ModelSerializer):
    game_title = serializers.CharField(source="game.title", read_only=True)

    class Meta:
        model = UserCollection
        fields = [
            "id",
            "game",
            "game_title",
            "status",
            "notes",
            "added_at",
        ]
        read_only_fields = ["game_title", "added_at"]


class CustomUserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "profile",
        ]
        read_only_fields = ["username"]

    def get_profile(self, obj):
        try:
            profile = obj.profile
        except UserProfile.DoesNotExist:
            return None
        return {
            "bio": profile.bio,
            "favourite_genre": profile.favourite_genre,
            "games_played": profile.games_played,
        }
