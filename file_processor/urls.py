from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Authentication URLs
    path('auth/login/', auth_views.LoginView.as_view(), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(next_page='/auth/login/'), name='logout'),
    path('auth/register/', views.register, name='register'),

    path('', include('file_processor.file.urls')),
    
    # Video processing URLs
    path('video/', include('file_processor.video.urls')),
    
    # Queue management URLs
    path('queue/', include('file_processor.queue.urls')),
]