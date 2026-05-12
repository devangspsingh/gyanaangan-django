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
    EmailPasswordLoginView,
    SpecialPageListViewSet,
    SpecialPageDetailView,  # Import SpecialPageDetailView
    GlobalSearchAPIView,
    BlogPostViewSet,
    CategoryViewSet,
    BannerViewSet,  # Import BannerViewSet
    AdminBlogPostViewSet,
    CategoryManagementViewSet,  # Import CategoryManagementViewSet
    StudentProfileViewSet,  # Import StudentProfileViewSet
    SubscriptionViewSet,  # Import SubscriptionViewSet
)
from .admin_views import (
    AdminResourceViewSet,
    AdminSubjectViewSet,
    AdminCourseViewSet,
    AdminYearViewSet,
    AdminStreamViewSet,
    AdminAIPromptTemplateViewSet,
    AdminUserViewSet,
    AdminEducationalYearViewSet,
    AIGenerateContentView,
)
from planner.views import GenerateQuestionPaperView, QuickAnswerView

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
router.register(r"admin/blog/posts", AdminBlogPostViewSet, basename="admin-blog-posts")
router.register(r"admin/blog/categories", CategoryManagementViewSet, basename="admin-blog-categories")
router.register(r"student-profiles", StudentProfileViewSet, basename="student-profile")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")

# Admin Content Endpoints
router.register(r"admin/content/resources", AdminResourceViewSet, basename="admin-resource")
router.register(r"admin/content/subjects", AdminSubjectViewSet, basename="admin-subject")
router.register(r"admin/content/courses", AdminCourseViewSet, basename="admin-course")
router.register(r"admin/content/years", AdminYearViewSet, basename="admin-year")
router.register(r"admin/content/streams", AdminStreamViewSet, basename="admin-stream")
router.register(r"admin/content/templates", AdminAIPromptTemplateViewSet, basename="admin-template")
router.register(r"admin/content/users", AdminUserViewSet, basename="admin-user")
router.register(r"admin/content/educational-years", AdminEducationalYearViewSet, basename="admin-educational-year")

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
    path("auth/login/", EmailPasswordLoginView.as_view(), name="email_password_login"),
    # Organization and Event Management
    path("organizations/", include("organization.urls")),
    path("events/", include("event.urls")),
    path("tracking/", include("tracking.urls")), # Analytics API
    path("planner/", include("planner.urls")),
    path("ai/generate-paper/", GenerateQuestionPaperView.as_view(), name="ai-generate-paper"),
    path("ai/quick-answer/", QuickAnswerView.as_view(), name="ai-quick-answer"),
    path("ai/generate-content/", AIGenerateContentView.as_view(), name="ai-generate-content"),
]
