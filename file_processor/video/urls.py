from django.urls import path
from . import views
from .api.detection_api import DetectionAPIView

app_name = 'video'

urlpatterns = [
    path('', views.video_home, name='home'),
    path('video_list/', views.video_list, name='video_list'),
    path('upload/', views.video_upload, name='upload'),
    path('camera/', views.camera_detection, name='camera'),
    path('test_camera/', views.test_camera_system, name='test_camera'),
    path('video_analysis/<int:video_file_id>/', views.analyze_video, name='video_analysis'),
    path('analyze_camera/<int:analysis_id>/', views.analyze_camera, name='analyze_camera'),
    path('video_analysis_history/', views.video_analysis_history, name='video_analysis_history'),
    path('analysis-details/<int:analysis_id>/', views.get_analysis_details, name='get_analysis_details'),
    path('delete-video/<int:video_file_id>/', views.delete_video_file, name='delete_video'),
    path('delete-analysis/<int:analysis_id>/', views.delete_analysis, name='delete_analysis'),
    path('generate-thumbnail/<int:video_file_id>/', views.generate_video_thumbnail, name='generate_thumbnail'),
    path('conversion-status/<int:video_file_id>/', views.video_conversion_status, name='conversion_status'),
    
    # Detection API endpoints
    path('api/detection/', DetectionAPIView.as_view(), name='api_detection'),
    path('capture-snapshot/', views.capture_snapshot, name='capture_snapshot'),
    path('detection-history/', views.get_detection_history, name='detection_history'),
    path('re-detect/', views.re_detect, name='re_detect'),
]