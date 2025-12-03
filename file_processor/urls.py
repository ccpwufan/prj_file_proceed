from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [


    
    # Authentication URLs
    path('auth/login/', auth_views.LoginView.as_view(), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(next_page='/auth/login/'), name='logout'),

    

    path('', include('file_processor.file.urls')),
]