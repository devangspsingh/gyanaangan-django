from django.urls import path
from . import views

app_name = 'results'

urlpatterns = [
    path('', views.result_home, name='home'),
    path('search/', views.search_result, name='search_result'),
    path('manual-calculator/', views.manual_calculator, name='manual_calculator'),
    # path('manual-entry/', views.manual_entry, name='manual_entry'),
    # path('manual-result/<int:pk>/', views.view_manual_result, name='view_manual_result'),
    # path('full-result/<str:roll_number>/', views.view_full_result, name='view_full_result'),
    # path('bulk-upload/', views.BulkUploadView.as_view(), name='bulk_upload'),
    # path('statistics/', views.result_statistics, name='statistics'),
]
