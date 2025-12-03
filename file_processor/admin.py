from django.contrib import admin
from .file.models import FileHeader, FileDetail, FileAnalysis, AnalysisResult
from .video.models import VideoFile, VideoAnalysis, VideoDetectionFrame

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

@admin.register(FileAnalysis)
class FileAnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'analysis_type', 'created_at', 'status')
    list_filter = ('created_at', 'status', 'user', 'analysis_type')
    search_fields = ('user__username',)

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('analysis', 'image', 'created_at')
    list_filter = ('created_at', 'analysis__user')
    search_fields = ('analysis__user__username', 'image__file_header__file_header_filename')

# Video models admin registration
@admin.register(VideoFile)
class VideoFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'user', 'created_at', 'duration', 'status', 'file_size')
    list_filter = ('created_at', 'status', 'user')
    search_fields = ('original_filename', 'user__username')
    readonly_fields = ('created_at', 'file_size')

@admin.register(VideoAnalysis)
class VideoAnalysisAdmin(admin.ModelAdmin):
    list_display = ('video_file', 'user', 'analysis_type', 'created_at', 'status', 'total_frames_processed', 'total_detections')
    list_filter = ('created_at', 'status', 'user', 'analysis_type')
    search_fields = ('user__username', 'video_file__original_filename')
    readonly_fields = ('created_at', 'completed_at', 'total_frames_processed', 'total_detections')

@admin.register(VideoDetectionFrame)
class VideoDetectionFrameAdmin(admin.ModelAdmin):
    list_display = ('video_analysis', 'frame_number', 'timestamp', 'created_at')
    list_filter = ('created_at', 'video_analysis__user')
    search_fields = ('video_analysis__user__username', 'video_analysis__video_file__original_filename')
    readonly_fields = ('created_at',)