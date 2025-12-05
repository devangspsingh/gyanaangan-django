from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrackEventView, VisitorViewSet, SessionViewSet, EventViewSet

router = DefaultRouter()
router.register(r'visitors', VisitorViewSet)
router.register(r'sessions', SessionViewSet)
router.register(r'events', EventViewSet)

urlpatterns = [
    path('track/', TrackEventView.as_view(), name='track_event'),
    path('dashboard/', include(router.urls)),
]
