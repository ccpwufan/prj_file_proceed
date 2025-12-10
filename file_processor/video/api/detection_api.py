"""
Detection API endpoints for camera-based multi-type detection
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import base64
import io
from PIL import Image
import numpy as np
import cv2
import logging

from file_processor.video.services.detection_service import DetectionService
from file_processor.video.services.camera_service import CameraService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class DetectionAPIView(View):
    """API endpoint for real-time detection from camera frames"""
    
    def __init__(self):
        super().__init__()
        self.detection_service = DetectionService()
        self.camera_service = CameraService()
    
    def post(self, request):
        """Process detection request from camera frame"""
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            if 'image' not in data or 'detection_type' not in data:
                return JsonResponse({
                    'success': False,
                    'error': 'Missing required fields: image, detection_type'
                }, status=400)
            
            # Decode base64 image
            image_data = base64.b64decode(data['image'].split(',')[1])
            image = Image.open(io.BytesIO(image_data))
            
            # Convert PIL Image to numpy array for OpenCV processing
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Perform detection based on type
            detection_type = data['detection_type']
            threshold = data.get('threshold', 0.5)
            
            logger.info(f"Processing {detection_type} detection with threshold {threshold}")
            
            # Use detection service to process frame
            detection_results = self.detection_service.detect_objects(
                frame=frame,
                detection_types=[detection_type],
                threshold=threshold
            )
            
            # Format results for frontend
            formatted_results = []
            for result in detection_results.get(detection_type, []):
                formatted_results.append({
                    'class': result.get('class', 'unknown'),
                    'confidence': float(result.get('confidence', 0.0)),
                    'bbox': [int(x) for x in result.get('bbox', [0, 0, 0, 0])],
                    'data': result.get('data', {})  # Additional data like barcode content
                })
            
            return JsonResponse({
                'success': True,
                'detections': formatted_results,
                'detection_type': detection_type,
                'processing_time': detection_results.get('processing_time', 0.0),
                'timestamp': detection_results.get('timestamp', '')
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON format'
            }, status=400)
        except Exception as e:
            logger.error(f"Detection processing failed: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Detection processing failed: {str(e)}'
            }, status=500)
    
    def get(self, request):
        """Get detection configuration and status"""
        try:
            # Get available detection types
            available_types = self.detection_service.get_available_detectors()
            
            # Get default thresholds for each type
            default_thresholds = {
                'barcode': 0.3,  # Optimized for QR codes
                'phone': 0.7,     # Higher threshold for object detection
                'yellowbox': 0.6  # Medium threshold for color detection
            }
            
            return JsonResponse({
                'success': True,
                'available_detection_types': available_types,
                'default_thresholds': default_thresholds,
                'service_status': 'ready'
            })
            
        except Exception as e:
            logger.error(f"Failed to get detection config: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to get detection config: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def capture_snapshot(request):
    """Save camera snapshot with detection results"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if 'image' not in data or 'detections' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: image, detections'
            }, status=400)
        
        # Create camera analysis session
        camera_service = CameraService()
        
        # Get user from request (use default user for camera snapshots)
        from django.contrib.auth.models import User
        user = User.objects.first()  # Get first user as default
        if not user:
            # Create default user if none exists
            user = User.objects.create_user(
                username='camera_user',
                email='camera@example.com',
                password='camera_pass123'
            )
        
        analysis = camera_service.create_camera_analysis(
            user=user,
            title=f"Camera Snapshot - {data.get('detection_type', 'unknown')} detection",
            detection_types=[data.get('detection_type', 'barcode')]
        )
        
        analysis_id = analysis.id  # Extract the ID from the VideoAnalysis object
        
        # Save snapshot and detections
        image_data = base64.b64decode(data['image'].split(',')[1])
        
        snapshot_result = camera_service.save_detection_snapshot(
            analysis_id=analysis_id,
            image_data=image_data,
            detections=data['detections'],
            metadata={
                'timestamp': data.get('timestamp', ''),
                'threshold': data.get('threshold', 0.5),
                'camera_settings': data.get('camera_settings', {})
            }
        )
        
        logger.info(f"Snapshot saved for analysis {analysis_id}")
        logger.info(f"Snapshot result: {snapshot_result}")
        
        # Ensure all values are JSON serializable
        response_data = {
            'success': True,
            'analysis_id': int(analysis_id),
            'snapshot_id': int(snapshot_result.get('snapshot_id', 0)),
            'message': 'Snapshot saved successfully'
        }
        
        logger.info(f"Response data: {response_data}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        logger.error(f"Failed to save snapshot: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to save snapshot: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_detection_history(request):
    """Get recent detection history"""
    try:
        limit = int(request.GET.get('limit', 20))
        detection_type = request.GET.get('detection_type', '')
        
        camera_service = CameraService()
        history = camera_service.get_recent_detections(
            limit=limit,
            detection_type=detection_type if detection_type else None
        )
        
        return JsonResponse({
            'success': True,
            'history': history,
            'total_count': len(history)
        })
        
    except Exception as e:
        logger.error(f"Failed to get detection history: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to get detection history: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_detection_config(request):
    """Update detection configuration"""
    try:
        data = json.loads(request.body)
        
        # Validate configuration
        if 'detection_type' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Missing detection_type field'
            }, status=400)
        
        detection_service = DetectionService()
        
        # Update detector configuration
        config_result = detection_service.update_detector_config(
            detection_type=data['detection_type'],
            config=data.get('config', {})
        )
        
        logger.info(f"Configuration updated for {data['detection_type']}")
        
        return JsonResponse({
            'success': True,
            'message': f'Configuration updated for {data["detection_type"]}',
            'config_applied': config_result
        })
        
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to update configuration: {str(e)}'
        }, status=500)