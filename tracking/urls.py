from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrackEventView, VisitorViewSet, SessionViewSet, EventViewSet, VisitorStatusView

router = DefaultRouter()
router.register(r'visitors', VisitorViewSet)
router.register(r'sessions', SessionViewSet)
router.register(r'events', EventViewSet)

from .dashboard_views import DashboardStatsView

# ...

urlpatterns = [
    path('track/', TrackEventView.as_view(), name='track_event'),
    path('visitor-status/<str:visitor_id>/', VisitorStatusView.as_view(), name='visitor_status'),
    path('dashboard/', include(router.urls)),
    path('dashboard-stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
]
