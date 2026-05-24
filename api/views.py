from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CustomUser
from events.models import Event
from events.visibility import can_view_event
from games.models import BoardGame
from games.services import bgg as bgg_service
from reviews.models import GameReview, UserCollection
from venues.models import Venue

from .permissions import IsModeratorOrReadOnly, IsOwnerOrModeratorOrReadOnly
from games.services.recommended import (
    get_top_rated_boardgames,
    get_top_rated_for_venue,
    summaries_to_api_payload,
)

from .serializers import (
    BoardGameEnsureSerializer,
    BoardGameRecommendedSerializer,
    BoardGameSearchResultSerializer,
    BoardGameSerializer,
    CustomUserSerializer,
    EventSerializer,
    GameReviewSerializer,
    UserCollectionSerializer,
)


class BoardGameSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "")
        try:
            results, from_stale = bgg_service.search_boardgames(query)
        except bgg_service.BGGError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = BoardGameSearchResultSerializer(results, many=True)
        response = Response(serializer.data)
        if from_stale:
            response["X-BGG-Cache"] = "stale"
        return response


class BoardGameRecommendedView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        limit = request.query_params.get("limit", "5")
        try:
            limit = max(1, min(int(limit), 10))
        except (TypeError, ValueError):
            limit = 5
        try:
            summaries = get_top_rated_boardgames(limit)
            payload = summaries_to_api_payload(summaries)
        except bgg_service.BGGError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = BoardGameRecommendedSerializer(payload, many=True)
        return Response(serializer.data)


class BoardGameEnsureView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BoardGameEnsureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bgg_ids = serializer.validated_data["bgg_ids"]
        try:
            games = bgg_service.ensure_boardgames(bgg_ids)
        except bgg_service.BGGNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except bgg_service.BGGError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        out = BoardGameSerializer(games, many=True)
        return Response(out.data, status=status.HTTP_200_OK)


class VenueGamesListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, venue_id):
        venue = get_object_or_404(Venue, pk=venue_id, is_active=True)
        games = venue.games.order_by("title")
        data = [
            {
                "id": g.pk,
                "bgg_id": g.bgg_id,
                "title": g.title,
                "image_url": g.image_url,
                "year_published": g.year_published,
            }
            for g in games
        ]
        return Response(data)


class VenueRecommendedGamesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, venue_id):
        venue = get_object_or_404(Venue, pk=venue_id, is_active=True)
        limit = request.query_params.get("limit", "5")
        try:
            limit = max(1, min(int(limit), 10))
        except (TypeError, ValueError):
            limit = 5
        try:
            summaries = get_top_rated_for_venue(venue, limit)
            payload = summaries_to_api_payload(summaries)
        except bgg_service.BGGError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = BoardGameRecommendedSerializer(payload, many=True)
        return Response(serializer.data)


class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsModeratorOrReadOnly]

    def get_queryset(self):
        from events.visibility import filter_public_events

        queryset = filter_public_events(
            Event.objects.prefetch_related("games").all()
        )
        location = self.request.query_params.get("location")
        if location:
            queryset = queryset.filter(location__icontains=location)
        return queryset


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Event.objects.prefetch_related("games").all()
    serializer_class = EventSerializer
    permission_classes = [IsModeratorOrReadOnly]

    def get_object(self):
        obj = super().get_object()
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            if not can_view_event(self.request.user, obj):
                raise NotFound()
        return obj


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
