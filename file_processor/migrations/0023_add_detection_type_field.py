# Generated migration file for adding detection_type field to VideoDetectionFrame
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('file_processor', '0022_videofile_conversion_error_videofile_conversion_log_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='videodetectionframe',
            name='detection_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('object', 'Object Detection'),
                    ('barcode', 'Barcode Recognition'),
                    ('phone', 'Phone Detection'),
                    ('box', 'Yellow Box Detection'),
                    ('multi', 'Multi-Type Detection'),
                ],
                default='object',
                help_text='Type of detection performed on this frame'
            ),
        ),
        migrations.AddField(
            model_name='videodetectionframe',
            name='processing_time',
            field=models.FloatField(
                null=True,
                blank=True,
                help_text='Processing time in milliseconds for detection on this frame'
            ),
        ),
        migrations.AlterField(
            model_name='videodetectionframe',
            name='detection_data',
            field=models.JSONField(
                default=dict,
                help_text='Structured detection results including bounding boxes, confidence scores, and type-specific data'
            ),
        ),
    ]