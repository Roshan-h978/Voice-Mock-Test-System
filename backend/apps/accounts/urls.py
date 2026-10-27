"""Account URLs, mounted at /api/."""

from django.urls import path

from . import views

urlpatterns = [
    # Authentication
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/google/", views.GoogleLoginView.as_view(), name="auth-google"),
    path("auth/google/config/", views.GoogleConfigView.as_view(), name="auth-google-config"),
    path("auth/refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/me/password/", views.ChangePasswordView.as_view(), name="auth-change-password"),
    path("auth/password-reset/", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("auth/password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("auth/invitations/<str:token>/", views.InvitationDetailView.as_view(), name="auth-invitation"),
    # Admin: user management
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-users"),
    path("admin/users/invite/", views.AdminInviteView.as_view(), name="admin-users-invite"),
    path("admin/users/<int:pk>/", views.AdminUserDetailView.as_view(), name="admin-user-detail"),
]
