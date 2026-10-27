"""Django admin pages for users and one-time account links."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import AccountToken, User


class UserCreationForm(AdminUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "full_name", "role", "level")


class UserEditForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserEditForm

    list_display = ("email", "full_name", "role", "level", "is_active", "date_joined")
    list_filter = ("role", "level", "is_active", "is_staff")
    search_fields = ("email", "full_name")
    ordering = ("email",)
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "phone", "role", "level")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "level", "usable_password", "password1", "password2"),
            },
        ),
    )


@admin.register(AccountToken)
class AccountTokenAdmin(admin.ModelAdmin):
    list_display = ("email", "purpose", "created_by", "created_at", "expires_at", "used_at")
    list_filter = ("purpose",)
    search_fields = ("email", "name")
    readonly_fields = ("purpose", "email", "name", "user", "created_by", "created_at", "expires_at", "used_at")
    exclude = ("token_hash",)

    def has_add_permission(self, request):
        return False  # links are created from the app (invite / forgot password)
