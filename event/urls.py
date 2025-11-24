from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, MyRegistrationsViewSet

router = DefaultRouter()
router.register(r'my-registrations', MyRegistrationsViewSet, basename='my-registrations')
router.register(r'', EventViewSet, basename='event')

urlpatterns = [
    path('', include(router.urls)),
]
