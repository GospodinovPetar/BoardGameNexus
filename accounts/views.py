from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView

from accounts.tasks import send_welcome_email
from reviews.models import GameReview, UserCollection

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
        send_welcome_email.delay(self.object.pk)
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
        context["profile_user"] = user
        context["user_profile"] = user.profile
        context["reviews"] = reviews
        context["collections"] = collections
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
