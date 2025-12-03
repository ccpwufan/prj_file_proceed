from django.urls import path, include

urlpatterns = [
    path('', include('file_processor.file.urls')),
]