from django.db import models
from django.contrib.auth.models import User
import os
import json

class FileHeader(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='file_headers', default=1)
    file_header_filename = models.FileField(upload_to='pdfs/', help_text='Upload PDF file')
    file_type = models.CharField(max_length=10, blank=True, null=True, help_text='File extension')
    created_at = models.DateTimeField(auto_now_add=True)
    total_pages = models.IntegerField(default=0)
    processor = models.CharField(max_length=50, blank=True, null=True, help_text='Selected processor for the conversion')
    comments = models.CharField(max_length=100, blank=True, null=True, help_text='User comments about the conversion')
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('converted', 'Converted'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    
    def __str__(self):
        return f"PDF: {os.path.basename(self.file_header_filename.name)}"
    
    class Meta:
        ordering = ['-created_at']

class FileDetail(models.Model):
    file_header = models.ForeignKey(FileHeader, on_delete=models.CASCADE, related_name='images')
    file_detail_filename = models.ImageField(upload_to='images/')
    page_number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    result_data = models.JSONField(default=dict, blank=True, null=True, help_text='AI analysis result data')
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('converted', 'Converted'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    
    def __str__(self):
        return f"Page {self.page_number} of {self.file_header}"
    
    class Meta:
        ordering = ['page_number']

class ImageAnalysis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='image_analyses', default=1)
    images = models.ManyToManyField(FileDetail, related_name='analyses')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('converted', 'Converted'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    
    def __str__(self):
        return f"Analysis by {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-created_at']

class AnalysisResult(models.Model):
    analysis = models.ForeignKey(ImageAnalysis, on_delete=models.CASCADE, related_name='results')
    image = models.ForeignKey(FileDetail, on_delete=models.CASCADE)
    result_data = models.JSONField(default=dict, help_text='Dify API response data')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Result for {self.image}"
    
    def get_formatted_result(self):
        return json.dumps(self.result_data, indent=2, ensure_ascii=False)
    
    class Meta:
        ordering = ['image__page_number']
