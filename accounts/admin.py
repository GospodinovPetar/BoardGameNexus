from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, UserProfile


class _PermissionLabelMixin:
    @staticmethod
    def _short_perm_label(perm):
        # Example: "reviews.add_gamereview"
        return f"{perm.content_type.app_label}.{perm.codename}"

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        formfield = super().formfield_for_manytomany(
            db_field, request=request, **kwargs
        )
        if db_field.name == "permissions" or db_field.name == "user_permissions":
            if formfield is not None:
                formfield.label_from_instance = self._short_perm_label
        return formfield


@admin.register(CustomUser)
class CustomUserAdmin(_PermissionLabelMixin, UserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
        (_("Profile"), {"fields": ("bio", "avatar", "date_of_birth")}),
    )


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Group)
class GroupAdmin(_PermissionLabelMixin, admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("permissions",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "favourite_genre", "games_played", "location")
    search_fields = ("user__username", "location", "favourite_genre")
