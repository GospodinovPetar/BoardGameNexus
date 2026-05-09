from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, TemplateView

from events.models import Event
from events.visibility import PARTICIPANT_HISTORY_STATUSES
from reviews.models import GameReview, UserCollection


def _past_participated_events_with_player_count(user):
    """Events that have ended where `user` was a participant (not removed)."""
    now = timezone.now()
    return (
        Event.objects.filter(
            date_time__lte=now,
            registrations__user=user,
            registrations__status__in=PARTICIPANT_HISTORY_STATUSES,
        )
        .distinct()
        .annotate(
            player_count=Count(
                "registrations",
                filter=Q(
                    registrations__status__in=PARTICIPANT_HISTORY_STATUSES,
                ),
            )
        )
        .order_by("-date_time")
        .prefetch_related("games")
    )

from .forms import EditProfileForm, EditUserProfileForm, LoginForm, RegisterForm
from .models import CustomUser


class RegisterView(CreateView):
    model = CustomUser
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("web:index")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        members_group = Group.objects.get(name="Members")
        self.object.groups.add(members_group)
        messages.success(self.request, "Account created! Please log in.")
        return response


class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("web:index")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        reviews = (
            GameReview.objects.filter(author=user)
            .select_related("game")
            .order_by("-created_at")
        )
        collections = (
            UserCollection.objects.filter(user=user)
            .select_related("game")
            .order_by("-added_at")
        )
        now = timezone.now()
        past_events = (
            Event.objects.filter(
                Q(date_time__lte=now)
                & (
                    Q(organizer=user)
                    | Q(
                        registrations__user=user,
                        registrations__status__in=PARTICIPANT_HISTORY_STATUSES,
                    )
                )
            )
            .distinct()
            .order_by("-date_time")
            .prefetch_related("games")
        )
        context["profile_user"] = user
        context["user_profile"] = user.profile
        context["reviews"] = reviews
        context["collections"] = collections
        context["past_events"] = past_events
        context["is_foreign_profile"] = False
        context["played_sessions"] = []
        return context


class PublicProfileView(LoginRequiredMixin, TemplateView):
    """Read-only profile page for any user, accessible to authenticated users."""

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = get_object_or_404(CustomUser, pk=self.kwargs["pk"])
        viewer = self.request.user
        is_foreign = viewer.pk != profile_user.pk

        if is_foreign:
            reviews = GameReview.objects.none()
            collections = UserCollection.objects.none()
            past_events = Event.objects.none()
            played_sessions = list(_past_participated_events_with_player_count(profile_user))
        else:
            reviews = (
                GameReview.objects.filter(author=profile_user)
                .select_related("game")
                .order_by("-created_at")
            )
            collections = (
                UserCollection.objects.filter(user=profile_user)
                .select_related("game")
                .order_by("-added_at")
            )
            now = timezone.now()
            past_events = (
                Event.objects.filter(
                    Q(date_time__lte=now)
                    & (
                        Q(organizer=profile_user)
                        | Q(
                            registrations__user=profile_user,
                            registrations__status__in=PARTICIPANT_HISTORY_STATUSES,
                        )
                    )
                )
                .distinct()
                .order_by("-date_time")
                .prefetch_related("games")
            )
            played_sessions = []

        context["profile_user"] = profile_user
        context["user_profile"] = getattr(profile_user, "profile", None)
        context["reviews"] = reviews
        context["collections"] = collections
        context["past_events"] = past_events
        context["is_foreign_profile"] = is_foreign
        context["played_sessions"] = played_sessions
        return context


class EditProfileView(LoginRequiredMixin, View):
    template_name = "accounts/edit_profile.html"

    def get(self, request):
        user = request.user
        user_form = EditProfileForm(instance=user)
        profile_form = EditUserProfileForm(instance=user.profile)
        context = {
            "user_form": user_form,
            "profile_form": profile_form,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        user = request.user
        user_form = EditProfileForm(
            request.POST,
            request.FILES,
            instance=user,
        )
        profile_form = EditUserProfileForm(request.POST, instance=user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
        context = {
            "user_form": user_form,
            "profile_form": profile_form,
        }
        return render(request, self.template_name, context)
