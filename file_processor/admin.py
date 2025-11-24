from django.contrib import admin
from .models import FileHeader, FileDetail, ImageAnalysis, AnalysisResult

@admin.register(FileHeader)
class FileHeaderAdmin(admin.ModelAdmin):
    list_display = ('file_header_filename', 'user', 'created_at', 'total_pages', 'status')
    list_filter = ('created_at', 'status', 'user')
    search_fields = ('file_header_filename', 'user__username')

@admin.register(FileDetail)
class FileDetailAdmin(admin.ModelAdmin):
    list_display = ('file_detail_filename', 'file_header', 'page_number', 'created_at')
    list_filter = ('created_at', 'file_header__user')
    search_fields = ('file_detail_filename', 'file_header__file_header_filename')

@admin.register(ImageAnalysis)
class ImageAnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'status')
    list_filter = ('created_at', 'status', 'user')
    search_fields = ('user__username',)
    filter_horizontal = ('images',)

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('analysis', 'image', 'created_at')
    list_filter = ('created_at', 'analysis__user')
    search_fields = ('analysis__user__username', 'image__file_header__file_header_filename')