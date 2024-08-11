from django.urls import path
from .views import login_page, google_login, google_callback, google_logout, profile

urlpatterns = [
    path('login/', login_page, name='login_page'),  # Default login page
    path('oauth/login/', google_login, name='login'),  # Google login URL
    path('oauth/callback/', google_callback, name='callback'),  # Google callback URL
    path('logout/', google_logout, name='logout'),  # Logout URL
    path('profile/', profile, name='profile'),  # Profile page URL
]
