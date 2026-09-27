from django.urls import path
from django.shortcuts import redirect
from .views import (
    home,
    subject_list,
    stream_detail,
    course_list,
    resource_list,
    subject_detail,
    course_detail,
    resource_view,
    search,
    year_detail,
)


def frontend_redirect(request, *args, **kwargs):
    path = request.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    qs = request.META.get("QUERY_STRING", "")
    target = f"https://gyanaangan.in{path}" + (f"?{qs}" if qs else "")
    return redirect(target, permanent=True)


urlpatterns = [
    path("", frontend_redirect, name="home"),
    path("search/", frontend_redirect, name="search"),
    path("subjects/", frontend_redirect, name="subject_list"),
    path("courses/", frontend_redirect, name="course_list"),
    path("resources/", frontend_redirect, name="resource_list"),
    path("subjects/<slug:subject_slug>/", frontend_redirect, name="subject_detail"),
    path(
        "resources/<slug:resource_slug>",
        frontend_redirect,
        name="resource_view",
    ),
    path("<slug:course_slug>/", frontend_redirect, name="course_detail"),
    path("<slug:course_slug>/<slug:stream_slug>", frontend_redirect, name="stream_detail"),
    path(
        "<slug:course_slug>/<slug:stream_slug>/<slug:year_slug>",
        frontend_redirect,
        name="year_detail",
    ),
    path(
        "<slug:course_slug>/<slug:stream_slug>/<slug:year_slug>/<slug:subject_slug>",
        frontend_redirect,
        name="subject_all_detail",
    ),
    path(
        "<slug:course_slug>/<slug:stream_slug>/<slug:year_slug>/<slug:subject_slug>/<slug:resource_slug>",
        frontend_redirect,
        name="resource_view_all_detail",
    ),
]

