from django.urls import path
from .views import terms_and_conditions, privacy_policy

urlpatterns = [
    path('terms-and-conditions/', terms_and_conditions, name='terms_and_conditions'),
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
]
