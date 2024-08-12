from collections import defaultdict
from urllib.parse import parse_qs, urlencode
from django.shortcuts import redirect, render
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import SEODetail
from courses.models import Course, Resource, SpecialPage, Stream, Subject
from .models import Profile, SavedResource, Subscription
from django.urls import reverse
from django.templatetags.static import static
from django.shortcuts import get_object_or_404, redirect


@login_required
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
    next_url = request.GET.get(
        "next", reverse("profile")
    )  # Capture the `next` parameter to redirect after login
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        "?response_type=code"
        f"&client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&scope=email%20profile"
        f"&state={urlencode({'next': next_url})}"
    )
    return redirect(google_auth_url)


def google_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    next_url = parse_qs(state).get("next", [reverse("profile")])[0]

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
    picture_url = user_info.get("picture")

    if not email:
        return redirect("login_page")

    user, created = User.objects.get_or_create(
        username=email, defaults={"first_name": name, "email": email}
    )

    if not created and user.first_name != name:
        user.first_name = name
        user.save()

    profile, profile_created = Profile.objects.get_or_create(user=user)

    if profile.img_google_url != picture_url:
        profile.img_google_url = picture_url

    if profile_created:
        profile.bio = f"This is {name}'s bio."
        profile.emoji_tag = "😊"

    profile.save()

    login(request, user)
    messages.success(request, f'You have been logged in!')
    return redirect(next_url)


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


@login_required
def toggle_save_resource(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    saved_resource, created = SavedResource.objects.get_or_create(
        user=request.user, resource=resource
    )

    if created:
        messages.success(request, f'Resource "{resource.name}" saved successfully!')
    else:
        saved_resource.delete()
        messages.info(
            request, f'Resource "{resource.name}" removed from your saved resources.'
        )

    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def saved_resources(request):
    saved_resources = SavedResource.objects.filter(user=request.user).select_related(
        "resource"
    )
    return render(
        request, "accounts/saved_resources.html", {"saved_resources": saved_resources}
    )


@login_required
def toggle_subscription(request, entity_type, entity_id):
    entity_model = None
    entity = None

    # Determine the entity type and get the corresponding model and instance
    if entity_type == "course":
        entity_model = Course
    elif entity_type == "stream":
        entity_model = Stream
    elif entity_type == "subject":
        entity_model = Subject
    elif entity_type == "special_page":
        entity_model = SpecialPage

    if entity_model:
        entity = get_object_or_404(entity_model, id=entity_id)

    if entity:
        # Check if the user is already subscribed to this entity
        subscription = Subscription.objects.filter(
            user=request.user,
            course=entity if entity_type == "course" else None,
            stream=entity if entity_type == "stream" else None,
            subject=entity if entity_type == "subject" else None,
            special_page=entity if entity_type == "special_page" else None,
        ).first()

        if subscription:
            # If already subscribed, unsubscribe
            subscription.delete()
            messages.info(request, f'You have unsubscribed from "{entity}".')
        else:
            # Otherwise, subscribe
            Subscription.subscribe(
                user=request.user,
                course=entity if entity_type == "course" else None,
                stream=entity if entity_type == "stream" else None,
                subject=entity if entity_type == "subject" else None,
                special_page=entity if entity_type == "special_page" else None,
            )
            messages.success(request, f'You have subscribed to "{entity}".')

    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def subscriptions(request):
    subscriptions = Subscription.objects.filter(user=request.user)
    
    grouped_subscriptions = defaultdict(list)
    
    for subscription in subscriptions:
        if subscription.special_page:
            grouped_subscriptions['special_pages'].append(subscription.special_page)
        elif subscription.course:
            grouped_subscriptions['courses'].append(subscription.course)
        elif subscription.subject:
            grouped_subscriptions['subjects'].append(subscription.subject)
        elif subscription.stream:
            grouped_subscriptions['streams'].append(subscription.stream)
    
    context = {
        'grouped_subscriptions': grouped_subscriptions,
    }
    
    return render(request, 'accounts/subscriptions.html', context)