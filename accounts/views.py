from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import FieldError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView

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
        profile = getattr(user, "profile", None)
        context["profile_user"] = user
        context["user_profile"] = profile
        context["reviews"] = self._reviews_for_user(user)
        context["collections"] = self._collections_for_user(user)
        return context

    def _reviews_for_user(self, user):
        if not apps.is_installed("reviews"):
            return []
        Review = apps.get_model("reviews", "Review")
        queryset = None
        for fk in ("author", "user", "reviewer"):
            try:
                queryset = Review.objects.filter(**{fk: user})
                break
            except FieldError:
                continue
        if queryset is None:
            return []
        field_names = {f.name for f in Review._meta.get_fields()}
        prefetch = [
            name for name in ("comments", "replies", "tags") if name in field_names
        ]
        if prefetch:
            queryset = queryset.prefetch_related(*prefetch)
        for name in ("game", "boardgame", "board_game"):
            if name in field_names:
                try:
                    queryset = queryset.select_related(name)
                except (FieldError, ValueError):
                    continue
                break
        return queryset

    def _collections_for_user(self, user):
        if not apps.is_installed("games"):
            return []
        try:
            Collection = apps.get_model("games", "Collection")
        except LookupError:
            return []
        for fk in ("owner", "user"):
            try:
                return Collection.objects.filter(**{fk: user})
            except FieldError:
                continue
        return []


class EditProfileView(LoginRequiredMixin, View):
    template_name = "accounts/edit_profile.html"

    def get(self, request):
        user = request.user
        profile = getattr(user, "profile", None)
        if profile is None:
            from .models import UserProfile

            profile, _ = UserProfile.objects.get_or_create(user=user)
        user_form = EditProfileForm(instance=user)
        profile_form = EditUserProfileForm(instance=profile)
        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )

    def post(self, request):
        user = request.user
        profile = getattr(user, "profile", None)
        if profile is None:
            from .models import UserProfile

            profile, _ = UserProfile.objects.get_or_create(user=user)
        user_form = EditProfileForm(
            request.POST,
            request.FILES,
            instance=user,
        )
        profile_form = EditUserProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )
