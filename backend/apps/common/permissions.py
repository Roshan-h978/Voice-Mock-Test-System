"""Permissions shared by every app. Role checks (admin/student) live in apps.accounts.permissions."""

import hmac

from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrAdmin(BasePermission):
    """Object-level check: the record's owner or an admin.

    The owner field defaults to "student"; a view can set `owner_field` to change it.
    """

    message = "You can only open your own records."
    owner_field = "student"

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, "is_admin", False):
            return True
        owner_field = getattr(view, "owner_field", self.owner_field)
        return getattr(obj, f"{owner_field}_id", None) == user.id


class ReadOnly(BasePermission):
    """Allows only GET, HEAD and OPTIONS requests."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class HasAutomationKey(BasePermission):
    """Allows trusted automation (n8n) that sends the shared X-Automation-Key header."""

    message = "Missing or invalid automation key."

    def has_permission(self, request, view):
        expected = settings.AUTOMATION_API_KEY
        provided = request.headers.get("X-Automation-Key", "")
        if not expected or not provided:
            return False
        return hmac.compare_digest(provided.encode(), expected.encode())
