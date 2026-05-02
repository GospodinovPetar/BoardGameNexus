from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .models import CustomUser, UserProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("bio", "avatar", "date_of_birth", "no_show_strikes")}),
    )
    list_display = UserAdmin.list_display + ("no_show_strikes",)


admin.site.unregister(Group)


class GroupAdmin(admin.ModelAdmin):
    filter_horizontal = ("permissions",)


admin.site.register(Group, GroupAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "favourite_genre", "games_played", "location")
    search_fields = ("user__username", "location", "favourite_genre")
