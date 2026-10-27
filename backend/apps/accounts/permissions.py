"""Role-based permissions: admins and students."""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Signed-in admins (role "admin") and Django superusers."""

    message = "Only admins can do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin)


class IsStudent(BasePermission):
    """Signed-in students."""

    message = "This area is for students."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_student)
