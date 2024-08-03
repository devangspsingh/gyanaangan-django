from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from .models import Notification, SpecialPage, Subject, Course, Resource, Stream, Year
from django.db.models import Count, F, Func
from django.urls import reverse
from django.db.models import Q


def search(request):
    query = request.GET.get("q", "")
    courses = Course.published.filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(meta_description__icontains=query)
    )
    subjects = Subject.published.filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(meta_description__icontains=query)
    )
    resources = Resource.published.filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(resource_type__icontains=query)
    )
    return render(
        request,
        "courses/search_results.html",
        {
            "query": query,
            "courses": courses,
            "subjects": subjects,
            "resources": resources,
        },
    )


# Define a custom function to cast NCLOB to a VARCHAR type
class CastToVarchar(Func):
    function = "CAST"
    template = "%(function)s(%(expressions)s AS VARCHAR(4000))"


def home(request):
    courses = Course.published.all()
    subjects = Subject.published.all().order_by("-last_resource_updated_at")[:5]
    resources = Resource.published.all()
    latest_notification = (
        Notification.published.filter(show_until__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    return render(
        request,
        "courses/home.html",
        {
            "courses": courses,
            "subjects": subjects,
            "resources": resources,
            "notification": latest_notification,
        },
    )


def subject_list(request):
    # subjects = Subject.published.all()
    subjects = Subject.published.all().filter().order_by("-last_resource_updated_at")
    return render(request, "courses/subject_list.html", {"subjects": subjects})


def course_list(request):
    courses = Course.published.all()
    return render(request, "courses/course_list.html", {"courses": courses})


def resource_list(request):
    resources = Resource.published.all()
    return render(request, "courses/resource_list.html", {"resources": resources})


def subject_detail(
    request,
    subject_slug,
    course_slug=None,
    stream_slug=None,
    year_slug=None,
):
    subject = get_object_or_404(Subject, slug=subject_slug)

    # Get filter parameters
    resource_type_filter = request.GET.get("resource_type", "all")

    # Validate the filter
    if (
        resource_type_filter != "all"
        and resource_type_filter not in subject.get_all_available_resource_types()
    ):
        return redirect(reverse("subject_detail", args=[subject_slug]))

    resources = subject.resources.all()

    # Apply resource type filter if provided and valid
    if resource_type_filter != "all":
        resources = resources.filter(resource_type=resource_type_filter)

    # Group resources by resource_type
    grouped_resources = {}
    for resource in resources:
        grouped_resources.setdefault(resource.resource_type, []).append(resource)

    if course_slug and stream_slug and year_slug and subject_slug:
        special_page = get_object_or_404(
            SpecialPage,
            course__slug=course_slug,
            stream__slug=stream_slug,
            year__slug=year_slug,
        )

        slugs = {
            "year_slug": special_page.year.slug,
            "course_slug": special_page.course.slug,
            "stream_slug": special_page.stream.slug,
            "subject_slug":subject_slug
        }
        return render(
            request,
            "courses/subject_detail.html",
            {
                "subject": subject,
                "grouped_resources": grouped_resources,
                "resource_type_filter": resource_type_filter,
                "canonical_url": request.build_absolute_uri(
                    reverse("subject_detail", args=[subject_slug])
                ),
                "slugs": slugs,
            },
        )
    return render(
        request,
        "courses/subject_detail.html",
        {
            "subject": subject,
            "grouped_resources": grouped_resources,
            "resource_type_filter": resource_type_filter,
            "canonical_url": request.build_absolute_uri(
                reverse("subject_detail", args=[subject_slug])
            ),
        },
    )


def resource_view(
    request,
    resource_slug,
    subject_slug=None,
    course_slug=None,
    stream_slug=None,
    year_slug=None,
):
    resource = get_object_or_404(Resource, slug=resource_slug)

    if course_slug and stream_slug and year_slug and subject_slug:
        special_page = get_object_or_404(
            SpecialPage,
            course__slug=course_slug,
            stream__slug=stream_slug,
            year__slug=year_slug,
        )

        slugs = {
            "year_slug": special_page.year.slug,
            "course_slug": special_page.course.slug,
            "stream_slug": special_page.stream.slug,
            "subject_slug":subject_slug
        }
        return render(
            request, "courses/pdf_viewer.html", {"resource": resource, "slugs": slugs}
        )
    return render(request, "courses/pdf_viewer.html", {"resource": resource})


def course_detail(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    return render(request, "courses/course_detail.html", {"course": course})


def resource_filter_view(request):
    course_slug = request.GET.get("course")
    subject_slug = request.GET.get("subject")

    if course_slug and not subject_slug:
        try:
            course = Course.published.get(slug=course_slug)
            return redirect("course_detail", course_slug=course.slug)
        except Course.DoesNotExist:
            return render(
                request,
                "courses/resource_filter.html",
            )

    if subject_slug:
        try:
            subject = Subject.published.get(slug=subject_slug)
            resources = Resource.published.filter(subjects=subject)
            if course_slug:
                resources = resources.filter(
                    subjects__stream__courses__slug=course_slug
                )
        except Subject.DoesNotExist:
            return render(
                request,
                "courses/resource_filter.html",
            )

        if not resources.exists():
            return render(
                request,
                "courses/resource_filter.html",
            )

        return render(request, "courses/resource_filter.html", {"resources": resources})

    return render(
        request,
        "courses/resource_filter.html",
    )


def stream_detail(request, course_slug, stream_slug):
    course = get_object_or_404(Course, slug=course_slug)
    stream = get_object_or_404(Stream.published, slug=stream_slug, courses=course)

    years = stream.years.all()
    years_count = years.count()
    if years_count == 1:
        return redirect(
            reverse("year_detail", args=[course.slug, stream.slug, years.first().slug])
        )
    return render(
        request,
        "courses/stream_detail.html",
        {"stream": stream, "years": years, "course": course},
    )


def year_detail(request, course_slug, stream_slug, year_slug):
    special_page = get_object_or_404(
        SpecialPage,
        course__slug=course_slug,
        stream__slug=stream_slug,
        year__slug=year_slug,
    )
    year = special_page.year
    course = special_page.course
    stream = special_page.stream

    subjects = Subject.published.filter(years=year, stream=stream).order_by(
        "-last_resource_updated_at"
    )
    return render(
        request,
        "courses/year_detail.html",
        {
            "stream": stream,
            "year": year,
            "course": course,
            "subjects": subjects,
            "special_page": special_page,
        },
    )
