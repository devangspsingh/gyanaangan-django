from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect

from core.models import SEODetail
from .models import Notification, SpecialPage, Subject, Course, Resource, Stream
from django.urls import reverse
from django.db.models import Q
from django.templatetags.static import static

# default_og_image_url = static('images/default-og-image.jpg')


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
        Q(name__icontains=query)
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


def home(request):
    courses = Course.published.all()[:5]
    subjects = Subject.published.all().order_by("-last_resource_updated_at")[:5]
    resources = Resource.published.all()[:5]
    latest_notification = (
        Notification.published.filter(show_until__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    
    seo_detail = SEODetail.objects.filter(page_name='home').first()
    if not seo_detail:
        seo_detail = SEODetail(
            title='Gyan Aangan | Explore a variety of courses, resources, and subjects....',
            meta_description='Explore a variety of courses and resources to enhance your knowledge at Gyan Aangan.',
            og_image=None,
            site_name='Gyan Aangan',
        )
    
    context = {
        'courses': courses,
        'subjects': subjects,
        'resources': resources,
        'notification': latest_notification,
        'title': seo_detail.title,
        'meta_description': seo_detail.meta_description,
        'og_image': seo_detail.og_image.url if seo_detail.og_image else static('images/default-og-image.jpg'),
        'site_name': seo_detail.site_name,
    }
    
    return render(request, "courses/home.html", context)



def subject_list(request):
    subjects = Subject.published.all().filter().order_by("-last_resource_updated_at")

    seo_detail = SEODetail.objects.filter(page_name="subject_list").first()
    if not seo_detail:
        seo_detail = SEODetail(
            title="Available Subjects - Gyan Aangan",
            meta_description="Discover a wide range of subjects to boost your knowledge and skills at Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    context = {
        "subjects": subjects,
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static('images/default-og-image.jpg')
        ),
        "site_name": seo_detail.site_name,
    }

    return render(request, "courses/subject_list.html", context)

def course_list(request):
    courses = Course.published.all()

    seo_detail = SEODetail.objects.filter(page_name='course_list').first()
    if not seo_detail:
        seo_detail = SEODetail(
            title='Available Courses - Gyan Aangan',
            meta_description='Explore a variety of courses to enhance your knowledge and skills at Gyan Aangan.',
            og_image=None,
            site_name='Gyan Aangan',
        )
    
    context = {
        'courses': courses,
        'title': seo_detail.title,
        'meta_description': seo_detail.meta_description,
        'og_image': seo_detail.og_image.url if seo_detail.og_image else static('images/default-og-image.jpg'),
        'site_name': seo_detail.site_name,
    }
    
    return render(request, "courses/course_list.html", context)

def resource_list(request):
    resources = Resource.published.all()

    seo_detail = SEODetail.objects.filter(page_name="resource_list").first()
    if not seo_detail:
        seo_detail = SEODetail(
            title="Available Resources - Gyan Aangan",
            meta_description="Explore a variety of resources to enhance your knowledge and skills at Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    context = {
        "resources": resources,
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static('images/default-og-image.jpg')
        ),
        "site_name": seo_detail.site_name,
    }

    return render(request, "courses/resource_list.html", context)


def subject_detail(
    request, subject_slug, course_slug=None, stream_slug=None, year_slug=None
):
    subject = get_object_or_404(Subject, slug=subject_slug)

    seo_detail = SEODetail.objects.filter(page_name=subject_slug).first()
    if not seo_detail:
        seo_detail = SEODetail(
            title=f"{subject.name} - Gyan Aangan",
            meta_description=f"Learn more about the {subject.name} subject at Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )

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

    context = {
        "subject": subject,
        "grouped_resources": grouped_resources,
        "resource_type_filter": resource_type_filter,
        "canonical_url": request.build_absolute_uri(
            reverse("subject_detail", args=[subject_slug])
        ),
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            subject.og_image.url
            if subject.og_image
            else static('images/default-og-image.jpg')
        ),
        "site_name": seo_detail.site_name,
    }

    if course_slug and stream_slug and year_slug:
        special_page = get_object_or_404(
            SpecialPage,
            course__slug=course_slug,
            stream__slug=stream_slug,
            year__slug=year_slug,
        )
        context["slugs"] = {
            "year_slug": special_page.year.slug,
            "course_slug": special_page.course.slug,
            "stream_slug": special_page.stream.slug,
            "subject_slug": subject_slug,
        }

    return render(request, "courses/subject_detail.html", context)


def resource_view(
    request,
    resource_slug,
    subject_slug=None,
    course_slug=None,
    stream_slug=None,
    year_slug=None,
):
    resource = get_object_or_404(Resource, slug=resource_slug)

    seo_detail = SEODetail.objects.filter(page_name=resource_slug).first()
    if not seo_detail:
        seo_detail = SEODetail(
            title=f"{resource.name} - Gyan Aangan",
            meta_description=f"Learn more about the {resource.name} resource at Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    context = {
        "resource": resource,
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            resource.og_image.url
            if resource.og_image
            else static('images/default-og-image.jpg')
        ),
        "site_name": seo_detail.site_name,
    }

    if course_slug and stream_slug and year_slug and subject_slug:
        special_page = get_object_or_404(
            SpecialPage,
            course__slug=course_slug,
            stream__slug=stream_slug,
            year__slug=year_slug,
        )
        context["slugs"] = {
            "year_slug": special_page.year.slug,
            "course_slug": special_page.course.slug,
            "stream_slug": special_page.stream.slug,
            "subject_slug": subject_slug,
        }

    return render(request, "courses/pdf_viewer.html", context)


def course_detail(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    seo_detail = SEODetail.objects.filter(page_name=course_slug).first()
    if not seo_detail:
        seo_detail = SEODetail(
            title=f"{course.name} - Gyan Aangan",
            meta_description=f"Learn more about the {course.name} course at Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    context = {
        "course": course,
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            course.og_image.url
            if course.og_image.url
            else static('images/default-og-image.jpg')
        ),
        "site_name": seo_detail.site_name,
    }

    return render(request, "courses/course_detail.html", context)


def stream_detail(request, course_slug, stream_slug):
    course = get_object_or_404(Course, slug=course_slug)
    stream = get_object_or_404(Stream.published, slug=stream_slug, courses=course)

    seo_detail = SEODetail.objects.filter(page_name=stream_slug).first()
    if not seo_detail:
        seo_detail = SEODetail(
            title=f"{stream.name} - Gyan Aangan",
            meta_description=f"Learn more about the {stream.name} stream at Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    years = stream.years.all()
    years_count = years.count()
    if years_count == 1:
        return redirect(
            reverse("year_detail", args=[course.slug, stream.slug, years.first().slug])
        )

    context = {
        "stream": stream,
        "years": years,
        "course": course,
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static('images/default-og-image.jpg')
        ),
        "site_name": seo_detail.site_name,
    }

    return render(request, "courses/stream_detail.html", context)


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

    seo_detail = SEODetail.objects.filter(page_name=year_slug).first()
    if not seo_detail:
        seo_detail = SEODetail(
            title=f"{stream.name} {year.name} - Gyan Aangan",
            meta_description=f"Learn more about the {course.name} {stream.name} {year.name} year at Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    subjects = Subject.published.filter(years=year, stream=stream).order_by(
        "-last_resource_updated_at"
    )

    context = {
        "stream": stream,
        "year": year,
        "course": course,
        "subjects": subjects,
        "special_page": special_page,
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static('images/default-og-image.jpg')
        ),
        "site_name": seo_detail.site_name,
    }

    return render(request, "courses/year_detail.html", context)
