from django.db.models import Avg, FloatField, Value
from django.db.models.functions import Coalesce
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CustomUser, UserProfile
from events.models import Event
from games.models import BoardGame, Genre
from reviews.models import GameReview, UserCollection

from .permissions import IsModeratorOrReadOnly, IsOwnerOrModeratorOrReadOnly
from .serializers import (
    BoardGameSerializer,
    CustomUserSerializer,
    EventSerializer,
    GameReviewSerializer,
    GenreSerializer,
    UserCollectionSerializer,
    UserProfileSerializer,
)


def _boardgames_with_review_avg(queryset):
    return queryset.annotate(
        review_avg=Coalesce(
            Avg("reviews__rating"),
            Value(0.0),
            output_field=FloatField(),
        )
    )


class GenreListView(generics.ListAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class BoardGameListCreateView(generics.ListCreateAPIView):
    serializer_class = BoardGameSerializer
    permission_classes = [IsModeratorOrReadOnly]

    def get_queryset(self):
        queryset = BoardGame.objects.select_related("genre").all()
        queryset = _boardgames_with_review_avg(queryset)
        queryset = queryset.order_by("title")

        title = self.request.query_params.get("title")
        genre_id = self.request.query_params.get("genre")
        if title:
            queryset = queryset.filter(title__icontains=title)
        if genre_id:
            queryset = queryset.filter(genre_id=genre_id)
        return queryset


class BoardGameDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BoardGameSerializer
    permission_classes = [IsModeratorOrReadOnly]

    def get_queryset(self):
        queryset = BoardGame.objects.select_related("genre").all()
        queryset = _boardgames_with_review_avg(queryset)
        return queryset.order_by("title")


class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsModeratorOrReadOnly]

    def get_queryset(self):
        queryset = Event.objects.prefetch_related("games").all()
        location = self.request.query_params.get("location")
        if location:
            queryset = queryset.filter(location__icontains=location)
        return queryset


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Event.objects.prefetch_related("games").all()
    serializer_class = EventSerializer
    permission_classes = [IsModeratorOrReadOnly]


class GameReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = GameReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = GameReview.objects.select_related("game", "author").all()
        game_id = self.request.query_params.get("game")
        if game_id:
            queryset = queryset.filter(game_id=game_id)
        return queryset

    def perform_create(self, serializer):
        game = serializer.validated_data.get("game")
        already_reviewed = GameReview.objects.filter(
            game=game,
            author=self.request.user,
        ).exists()
        if already_reviewed:
            raise serializers.ValidationError("You have already reviewed this game.")
        serializer.save(author=self.request.user)


class GameReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GameReview.objects.select_related("game", "author").all()
    serializer_class = GameReviewSerializer
    permission_classes = [IsOwnerOrModeratorOrReadOnly]


class UserCollectionListCreateView(generics.ListCreateAPIView):
    serializer_class = UserCollectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserCollection.objects.filter(user=self.request.user).select_related(
            "game"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserCollectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserCollectionSerializer
    permission_classes = [IsOwnerOrModeratorOrReadOnly]

    def get_queryset(self):
        return UserCollection.objects.filter(user=self.request.user).select_related(
            "game"
        )


class CurrentUserView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
