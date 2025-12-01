from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
    # Authentication URLs
    path('auth/login/', auth_views.LoginView.as_view(), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(next_page='/auth/login/'), name='logout'),
    path('auth/register/', views.register, name='register'),
    
    # File Processing URLs
    path('file/upload/', views.upload_file, name='upload_file'),
    path('file/list/', views.file_list, name='file_list'),
    path('file/detail/<int:pk>/', views.file_detail, name='file_detail'),
    path('file/detail-partial/<int:pk>/', views.file_detail_partial, name='file_detail_partial'),
    path('file/analyze-single-file/', views.analyze_single_file, name='analyze_single_file'),
    path('file/analyze-all/<int:pk>/', views.analyze_all_files, name='analyze_all_files'),
    path('file/delete/<int:pk>/', views.delete_file, name='delete_file'),
    path('file/get-log/<int:pk>/', views.get_log, name='get_log'),
    
    # Image Analysis URLs
    path('analysis/list/', views.analysis_list, name='analysis_list'),
    
    # Result Detail URLs
    path('result/detail/<int:pk>/', views.result_detail, name='result_detail'),
]