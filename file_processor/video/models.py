from django.db import models
from django.contrib.auth.models import User


class VideoFile(models.Model):
    """Video file model for storing uploaded video information"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_files')
    video_file = models.FileField(upload_to='videos/')
    original_filename = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    duration = models.FloatField(null=True, blank=True)  # Video duration in seconds
    status = models.CharField(max_length=20, default='uploaded', choices=[
        ('uploaded', 'Uploaded'),
        ('converting', 'Converting'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ])
    thumbnail = models.ImageField(upload_to='video_thumbnails/', null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)  # File size in bytes
    resolution = models.CharField(max_length=20, null=True, blank=True)  # Resolution
    
    # Conversion related fields
    original_file = models.FileField(upload_to='videos/original/', null=True, blank=True)  # Original uploaded file
    converted_file = models.FileField(upload_to='videos/converted/', null=True, blank=True)  # Converted web-compatible file
    conversion_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('converting', 'Converting'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),  # Already compatible
    ])
    conversion_progress = models.IntegerField(default=0)  # Progress percentage 0-100
    conversion_error = models.TextField(blank=True, null=True)  # Error message if conversion failed
    conversion_log = models.TextField(blank=True, null=True)  # Conversion log
    is_web_compatible = models.BooleanField(default=False)  # Whether the video is web compatible
    original_format = models.CharField(max_length=50, blank=True, null=True)  # Original format info
    converted_format = models.CharField(max_length=50, blank=True, null=True)  # Converted format info

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_filename} - {self.user.username}"


class VideoAnalysis(models.Model):
    """Video analysis model for storing analysis results"""
    video_file = models.ForeignKey(VideoFile, on_delete=models.CASCADE, related_name='analyses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_analyses')
    analysis_type = models.CharField(max_length=20, default='phone_detection', choices=[
        ('phone_detection', 'Phone Detection'),
        ('object_detection', 'Object Detection'),
        ('custom', 'Custom Analysis'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    result_summary = models.TextField(blank=True, null=True)
    detection_threshold = models.FloatField(default=0.5)
    frame_interval = models.FloatField(default=1.0)  # Detection interval in seconds
    total_frames_processed = models.IntegerField(default=0)
    total_detections = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Analysis of {self.video_file.original_filename} - {self.analysis_type}"


class VideoDetectionFrame(models.Model):
    """Video detection frame model for storing frame-by-frame detection results"""
    video_analysis = models.ForeignKey(VideoAnalysis, on_delete=models.CASCADE, related_name='detection_frames')
    frame_number = models.IntegerField()
    frame_image = models.ImageField(upload_to='detection_frames/')
    detection_data = models.JSONField(default=dict)  # Store detection results
    timestamp = models.FloatField()  # Frame timestamp in seconds
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['frame_number']

    def __str__(self):
        return f"Frame {self.frame_number} of {self.video_analysis}"