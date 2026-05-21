from rest_framework import serializers

from accounts.models import CustomUser, UserProfile
from events.models import Event
from games.models import BoardGame, Genre
from reviews.models import GameReview, UserCollection


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class BoardGameSerializer(serializers.ModelSerializer):
    genre = serializers.PrimaryKeyRelatedField(queryset=Genre.objects.all())
    genre_name = serializers.SerializerMethodField()
    review_avg = serializers.SerializerMethodField()

    class Meta:
        model = BoardGame
        fields = [
            "id",
            "title",
            "genre",
            "genre_name",
            "release_date",
            "min_players",
            "max_players",
            "description",
            "image_url",
            "review_avg",
        ]
        read_only_fields = ["genre_name", "review_avg"]

    def get_genre_name(self, obj):
        return obj.genre.name

    def get_review_avg(self, obj):
        return round(float(obj.review_avg), 2)


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
        return obj.google_maps_url

    def get_venue_total_price(self, obj):
        total = obj.venue_total_price
        return float(total) if total is not None else None

    def get_venue_price_per_person(self, obj):
        per_person = obj.venue_price_per_person
        return float(per_person) if per_person is not None else None


class GameReviewSerializer(serializers.ModelSerializer):
    game = serializers.PrimaryKeyRelatedField(queryset=BoardGame.objects.all())
    game_title = serializers.SerializerMethodField()
    author_username = serializers.SerializerMethodField()

    class Meta:
        model = GameReview
        fields = [
            "id",
            "game",
            "game_title",
            "author_username",
            "title",
            "content",
            "rating",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["game_title", "author_username", "created_at", "updated_at"]

    def get_game_title(self, obj):
        return obj.game.title

    def get_author_username(self, obj):
        return obj.author.username


class UserCollectionSerializer(serializers.ModelSerializer):
    game = serializers.PrimaryKeyRelatedField(queryset=BoardGame.objects.all())
    game_title = serializers.SerializerMethodField()

    class Meta:
        model = UserCollection
        fields = ["id", "game", "game_title", "status", "notes", "added_at"]
        read_only_fields = ["game_title", "added_at"]

    def get_game_title(self, obj):
        return obj.game.title


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["favourite_genre", "games_played", "location"]
        read_only_fields = ["games_played"]


class CustomUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "bio",
            "date_of_birth",
            "profile",
        ]
        read_only_fields = ["id", "username"]
