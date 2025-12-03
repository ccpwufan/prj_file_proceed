from django.urls import path
from . import views

app_name = 'video'

urlpatterns = [
    path('', views.video_home, name='home'),
    path('video_list/', views.video_list, name='video_list'),
    path('upload/', views.video_upload, name='upload'),
    path('camera/', views.camera_detection, name='camera'),
    path('video_analysis/<int:video_file_id>/', views.analyze_video, name='video_analysis'),
    path('analyze_camera/<int:analysis_id>/', views.analyze_camera, name='analyze_camera'),
    path('video_analysis_history/', views.video_analysis_history, name='video_analysis_history'),
    path('delete-video/<int:video_file_id>/', views.delete_video_file, name='delete_video'),
    path('delete-analysis/<int:analysis_id>/', views.delete_analysis, name='delete_analysis'),
    path('generate-thumbnail/<int:video_file_id>/', views.generate_video_thumbnail, name='generate_thumbnail'),
    path('generate-all-thumbnails/', views.generate_all_thumbnails, name='generate_all_thumbnails'),
]