from django.urls import path
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

urlpatterns = [
    path("", home, name="home"),
    path("search/", search, name="search"),
    path("subjects/", subject_list, name="subject_list"),
    path("courses/", course_list, name="course_list"),
    path("resources/", resource_list, name="resource_list"),
    path("subjects/<slug:subject_slug>/", subject_detail, name="subject_detail"),
    path(
        "resources/<slug:resource_slug>",
        resource_view,
        name="resource_view",
    ),
    path("<slug:course_slug>/", course_detail, name="course_detail"),
    path("<slug:course_slug>/<slug:stream_slug>", stream_detail, name="stream_detail"),
    path(
        "<slug:course_slug>/<slug:stream_slug>/<slug:year_slug>",
        year_detail,
        name="year_detail",
    ),
    path(
        "<slug:course_slug>/<slug:stream_slug>/<slug:year_slug>/<slug:subject_slug>",
        subject_detail,
        name="subject_all_detail",
    ),
    path(
        "<slug:course_slug>/<slug:stream_slug>/<slug:year_slug>/<slug:subject_slug>/<slug:resource_slug>",
        resource_view,
        name="resource_view_all_detail",
    ),
]
