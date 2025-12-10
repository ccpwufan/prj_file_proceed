"""
Detection configuration module for video processing
"""

# Default detection configurations
DEFAULT_DETECTION_CONFIG = {
    'barcode': {
        'enabled': True,
        'threshold': 0.3,  # Optimized for QR codes
        'pyzbar_config': {
            'decode_types': ['QRCODE', 'CODE128', 'CODE39', 'EAN13', 'EAN8', 'UPC_A', 'UPC_E'],
            'scan_regions': None,  # Scan entire image
            'max_detections': 10,
            'min_quality': 0.1
        },
        'visualization': {
            'color': '#00ff00',
            'border_style': 'solid',
            'label_format': '{type}: {data} ({confidence:.1%})'
        }
    },
    
    'phone': {
        'enabled': True,
        'threshold': 0.7,  # Higher threshold for object detection
        'model_config': {
            'model_path': None,  # Will be set when model is available
            'input_size': [640, 640],
            'confidence_threshold': 0.7,
            'nms_threshold': 0.4,
            'max_detections': 5
        },
        'visualization': {
            'color': '#ff0000',
            'border_style': 'solid',
            'label_format': 'Phone ({confidence:.1%})'
        }
    },
    
    'yellowbox': {
        'enabled': True,
        'threshold': 0.6,  # Medium threshold for color detection
        'color_config': {
            'hsv_range': {
                'lower': [20, 100, 100],   # Lower bound for yellow in HSV
                'upper': [30, 255, 255]    # Upper bound for yellow in HSV
            },
            'min_area': 1000,  # Minimum contour area in pixels
            'max_area': 50000, # Maximum contour area in pixels
            'aspect_ratio_range': [0.5, 2.0],  # Expected aspect ratio range
            'rectangularity_threshold': 0.7,  # How rectangular the shape should be
            'morphology_kernel_size': 5,
            'blur_kernel_size': 5
        },
        'visualization': {
            'color': '#ffff00',
            'border_style': 'dashed',
            'label_format': 'Yellow Box ({confidence:.1%})'
        }
    }
}

# Performance settings
PERFORMANCE_CONFIG = {
    'max_processing_time': 2.0,  # Maximum seconds per frame
    'frame_skip': 0,  # Number of frames to skip (0 = process every frame)
    'parallel_processing': True,
    'gpu_acceleration': False,  # Set to True when GPU is available
    'memory_limit_mb': 512  # Memory limit for detection processing
}

# API settings
API_CONFIG = {
    'max_image_size': 1920,  # Maximum dimension for uploaded images
    'compression_quality': 0.8,
    'timeout_seconds': 30,
    'rate_limit': {
        'requests_per_minute': 60,
        'burst_size': 10
    }
}

# Camera settings
CAMERA_CONFIG = {
    'default_resolution': [1280, 720],
    'supported_resolutions': [
        [1920, 1080],
        [1280, 720],
        [640, 480]
    ],
    'default_fps': 30,
    'supported_fps': [15, 30, 60],
    'auto_focus': True,
    'auto_exposure': True,
    'preferred_facing_mode': 'environment'  # 'user' for front camera, 'environment' for rear
}