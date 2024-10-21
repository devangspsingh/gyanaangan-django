from django.urls import path
from . import views

urlpatterns = [
    path('', views.blog_list, name='blog_list'),  # URL for listing all blogs
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),  # URL for single blog post
]
