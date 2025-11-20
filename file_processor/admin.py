from django.contrib import admin
from .models import PDFConversion, ConvertedImage, ImageAnalysis, AnalysisResult

class ConvertedImageInline(admin.TabularInline):
    model = ConvertedImage
    extra = 0
    readonly_fields = ('page_number', 'image_file', 'created_at')

class AnalysisResultInline(admin.TabularInline):
    model = AnalysisResult
    extra = 0
    readonly_fields = ('image', 'result_data', 'created_at')

@admin.register(PDFConversion)
class PDFConversionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'status', 'total_pages', 'created_at')
    list_filter = ('status', 'created_at', 'user')
    readonly_fields = ('total_pages', 'status', 'created_at')
    inlines = [ConvertedImageInline]

@admin.register(ConvertedImage)
class ConvertedImageAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'page_number', 'created_at')
    list_filter = ('created_at', 'pdf_conversion__user')

@admin.register(ImageAnalysis)
class ImageAnalysisAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'user')
    readonly_fields = ('status', 'created_at')
    inlines = [AnalysisResultInline]

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'analysis', 'created_at')
    list_filter = ('created_at', 'analysis__user')
    readonly_fields = ('result_data', 'created_at')
