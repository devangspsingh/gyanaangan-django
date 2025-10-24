from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet,
    SubjectViewSet,
    ResourceViewSet,
    StreamViewSet,
    NotificationViewSet,
    UserProfileViewSet,
    SavedResourceViewSet,
    GoogleLoginView,
    SpecialPageListViewSet,
    SpecialPageDetailView,  # Import SpecialPageDetailView
    GlobalSearchAPIView,
    BlogPostViewSet,
    CategoryViewSet,
    BannerViewSet,  # Import BannerViewSet
)

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"subjects", SubjectViewSet, basename="subject")
router.register(r"resources", ResourceViewSet, basename="resource")
router.register(r"streams", StreamViewSet, basename="stream")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"profiles", UserProfileViewSet, basename="profile")
router.register(r"saved-resources", SavedResourceViewSet, basename="savedresource")
router.register(
    r"special-pages", SpecialPageListViewSet, basename="specialpage"
)  # Register SpecialPage
router.register(r"blog/posts", BlogPostViewSet, basename="blogpost")
router.register(r"blog/categories", CategoryViewSet, basename="category")
router.register(r"banners", BannerViewSet, basename="banner")  # Register Banner


urlpatterns = [
    path("", include(router.urls)),
    path("search/", GlobalSearchAPIView.as_view(), name="global_search_api"),
    path(
        "special-pages/details/<slug:course_slug>/<slug:stream_slug>/<slug:year_slug>/",
        SpecialPageDetailView.as_view(),
        name="special_page_detail_by_slugs",
    ),  # New URL
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("auth/google/", GoogleLoginView.as_view(), name="google_login"),
]
