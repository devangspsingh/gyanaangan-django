from django.urls import path
from .views import (
    login_page,
    google_login,
    google_callback,
    google_logout,
    profile,
    subscriptions,
    toggle_save_resource,
    saved_resources,
    toggle_subscription,
)

urlpatterns = [
    path("", login_page, name="login_page"),  # Default login page
    path("login/", login_page, name="login_page"),  # Default login page
    path("oauth/login/", google_login, name="login"),  # Google login URL
    path("oauth/callback/", google_callback, name="callback"),  # Google callback URL
    path("logout/", google_logout, name="logout"),  # Logout URL
    path("profile/", profile, name="profile"),  # Profile page URL
    path(
        "toggle_save_resource/<int:resource_id>/",
        toggle_save_resource,
        name="toggle_save_resource",
    ),
    path("saved-resources/", saved_resources, name="saved_resources"),
    path(
        "toggle-subscription/<str:entity_type>/<int:entity_id>/",
        toggle_subscription,
        name="toggle_subscription",
    ),
    path("subscriptions/", subscriptions, name="subscriptions"),
]
