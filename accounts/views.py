from django.shortcuts import redirect, render
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
import requests
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from django.conf import settings
from django.contrib.auth.decorators import login_required

from core.models import SEODetail
from .models import Profile
from django.urls import reverse
from django.templatetags.static import static


@login_required
def profile(request):
    seo_detail = SEODetail.objects.filter(page_name="profile").first()
    if not seo_detail:
        seo_detail = SEODetail(
            title="Your Profile - Gyan Aangan",
            meta_description="Manage your profile and view your activity on Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    context = {
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static("images/default-og-image.jpg")
        ),
        "site_name": seo_detail.site_name,
    }

    return render(request, "accounts/profile.html", context)


def google_login(request):
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        "?response_type=code"
        f"&client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&scope=email%20profile"
    )
    return redirect(google_auth_url)


def google_callback(request):
    code = request.GET.get("code")
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    token_r = requests.post(token_url, data=token_data)
    token_json = token_r.json()
    access_token = token_json.get("access_token")

    user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    user_info_params = {"access_token": access_token}
    user_info_r = requests.get(user_info_url, params=user_info_params)
    user_info = user_info_r.json()

    email = user_info.get("email")
    name = user_info.get("name")
    picture_url = user_info.get("picture")  # Get the profile image URL

    if not email:
        return redirect("login_page")

    # Try to get the user, or create a new one if it doesn't exist
    user, created = User.objects.get_or_create(
        username=email, defaults={"first_name": name, "email": email}
    )

    if not created:
        # Update the user's first name if necessary
        if user.first_name != name:
            user.first_name = name
            user.save()

    # Check if the profile exists; if not, create it
    profile, profile_created = Profile.objects.get_or_create(user=user)

    # Update the img_google_url field
    if profile.img_google_url != picture_url:
        profile.img_google_url = picture_url

    if profile_created:
        profile.bio = (
            f"This is {name}'s bio."  # Set a default bio (can be customized later)
        )
        profile.emoji_tag = "😊"  # Set a default emoji tag

    # Save the profile, which will trigger the save logic to handle the image
    profile.save()

    login(request, user)
    return redirect(reverse("profile"))


def login_page(request):
    if request.user.is_authenticated:
        return redirect(reverse("home"))

    seo_detail = SEODetail.objects.filter(page_name="login_page").first()
    if not seo_detail:
        seo_detail = SEODetail(
            title="Login - Gyan Aangan",
            meta_description="Access your account on Gyan Aangan to explore more subjects and resources.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    context = {
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static("images/default-og-image.jpg")
        ),
        "site_name": seo_detail.site_name,
    }

    return render(request, "accounts/login.html", context)


def google_logout(request):
    logout(request)
    return redirect(reverse("login_page"))
