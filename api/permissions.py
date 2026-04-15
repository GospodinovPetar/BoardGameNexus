from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrModeratorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        if request.user.groups.filter(name="Moderators").exists():
            return True
        if hasattr(obj, "author"):
            return obj.author == request.user
        return obj.user == request.user


class IsModeratorOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser
            or request.user.groups.filter(name="Moderators").exists()
        )
