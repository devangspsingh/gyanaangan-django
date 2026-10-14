import logging
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from blog.models import BlogPost
from courses.models import Course, Subject, Resource

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 1800  # 30 minutes


class SitemapBlogsView(APIView):
    """
    Ultra-lightweight endpoint returning only slug, updated_at, and publish_date
    for all published blog posts. Direct database value projection.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cache_key = "sitemap:blogs"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        try:
            posts = list(
                BlogPost.published.all()
                .values("slug", "updated_at", "publish_date")
                .order_by("-updated_at")
            )
            cache.set(cache_key, posts, CACHE_TIMEOUT)
            return Response(posts)
        except Exception as e:
            logger.error("Error fetching sitemap blogs: %s", e)
            return Response([], status=500)


class SitemapResourcesView(APIView):
    """
    Ultra-lightweight endpoint returning only slug and updated_at
    for all published resources. Direct database value projection.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cache_key = "sitemap:resources"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        try:
            resources = list(
                Resource.published.all()
                .values("slug", "updated_at")
                .order_by("-updated_at")
            )
            cache.set(cache_key, resources, CACHE_TIMEOUT)
            return Response(resources)
        except Exception as e:
            logger.error("Error fetching sitemap resources: %s", e)
            return Response([], status=500)


class SitemapSubjectsView(APIView):
    """
    Ultra-lightweight endpoint returning only slug and updated_at
    for all published subjects.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cache_key = "sitemap:subjects"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        try:
            subjects = list(
                Subject.published.all()
                .values("slug", "updated_at")
                .order_by("name")
            )
            cache.set(cache_key, subjects, CACHE_TIMEOUT)
            return Response(subjects)
        except Exception as e:
            logger.error("Error fetching sitemap subjects: %s", e)
            return Response([], status=500)


class SitemapCoursesView(APIView):
    """
    Ultra-lightweight endpoint returning course hierarchy (courses, streams, years)
    for sitemap generation.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cache_key = "sitemap:courses"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        try:
            courses_qs = Course.published.prefetch_related("streams__years").all().order_by("name")
            results = []
            for course in courses_qs:
                streams_data = []
                for stream in course.streams.all():
                    years_data = [{"slug": year.slug} for year in stream.years.all() if year.slug]
                    streams_data.append({
                        "slug": stream.slug,
                        "years": years_data,
                    })
                results.append({
                    "slug": course.slug,
                    "updated_at": course.updated_at,
                    "streams": streams_data,
                })

            cache.set(cache_key, results, CACHE_TIMEOUT)
            return Response(results)
        except Exception as e:
            logger.error("Error fetching sitemap courses: %s", e)
            return Response([], status=500)


class SitemapAllView(APIView):
    """
    Consolidated endpoint returning all sitemap feeds in a single payload.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cache_key = "sitemap:all"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        try:
            blogs = list(
                BlogPost.published.all()
                .values("slug", "updated_at", "publish_date")
                .order_by("-updated_at")
            )
            resources = list(
                Resource.published.all()
                .values("slug", "updated_at")
                .order_by("-updated_at")
            )
            subjects = list(
                Subject.published.all()
                .values("slug", "updated_at")
                .order_by("name")
            )
            courses_qs = Course.published.prefetch_related("streams__years").all().order_by("name")
            courses = []
            for course in courses_qs:
                streams_data = []
                for stream in course.streams.all():
                    years_data = [{"slug": year.slug} for year in stream.years.all() if year.slug]
                    streams_data.append({
                        "slug": stream.slug,
                        "years": years_data,
                    })
                courses.append({
                    "slug": course.slug,
                    "updated_at": course.updated_at,
                    "streams": streams_data,
                })

            payload = {
                "blogs": blogs,
                "resources": resources,
                "subjects": subjects,
                "courses": courses,
                "counts": {
                    "blogs": len(blogs),
                    "resources": len(resources),
                    "subjects": len(subjects),
                    "courses": len(courses),
                }
            }
            cache.set(cache_key, payload, CACHE_TIMEOUT)
            return Response(payload)
        except Exception as e:
            logger.error("Error generating sitemap feed: %s", e)
            return Response({"error": str(e)}, status=500)
