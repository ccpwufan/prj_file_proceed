from django import forms
from .models import VideoFile, VideoAnalysis


class VideoUploadForm(forms.ModelForm):
    """Form for uploading video files"""
    
    class Meta:
        model = VideoFile
        fields = ['video_file']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['video_file'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'video/*',
            'required': True
        })
        self.fields['video_file'].label = '选择视频文件'


class VideoAnalysisForm(forms.ModelForm):
    """Form for creating video analysis"""
    
    class Meta:
        model = VideoAnalysis
        fields = ['analysis_type', 'detection_threshold', 'frame_interval']
        widgets = {
            'analysis_type': forms.Select(attrs={'class': 'form-control'}),
            'detection_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.1',
                'max': '1.0',
                'step': '0.1'
            }),
            'frame_interval': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.1',
                'max': '10.0',
                'step': '0.1'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['analysis_type'].label = '分析类型'
        self.fields['detection_threshold'].label = '检测阈值'
        self.fields['frame_interval'].label = '帧间隔（秒）'


class VideoSearchForm(forms.Form):
    """Form for searching video files"""
    search_query = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜索视频文件名...'
        })
    )
    
    analysis_type = forms.ChoiceField(
        choices=[
            ('', 'All Types'),
            ('phone_detection', 'Phone Detection'),
            ('object_detection', 'Object Detection'),
            ('custom', 'Custom Analysis'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'All Status'),
            ('uploaded', 'Uploaded'),
            ('processing', 'Processing'),
            ('processed', 'Processed'),
            ('failed', 'Failed'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )