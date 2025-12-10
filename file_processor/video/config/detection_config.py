"""
Detection configuration management for video processing
"""

import json
import os
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.cache import cache

from . import DEFAULT_DETECTION_CONFIG, PERFORMANCE_CONFIG, API_CONFIG, CAMERA_CONFIG


class DetectionConfigManager:
    """Manages detection configurations with caching and persistence"""
    
    CACHE_KEY_PREFIX = 'detection_config_'
    CACHE_TIMEOUT = 3600  # 1 hour
    
    def __init__(self):
        self.config_dir = getattr(settings, 'DETECTION_CONFIG_DIR', 
                                 os.path.join(settings.BASE_DIR, 'file_processor/video/config'))
        self.custom_config_file = os.path.join(self.config_dir, 'custom_config.json')
        
    def get_detector_config(self, detection_type: str) -> Dict[str, Any]:
        """Get configuration for a specific detector type"""
        cache_key = f'{self.CACHE_KEY_PREFIX}{detection_type}'
        
        # Try to get from cache first
        config = cache.get(cache_key)
        if config is not None:
            return config
        
        # Load configuration
        config = self._load_detector_config(detection_type)
        
        # Cache the configuration
        cache.set(cache_key, config, self.CACHE_TIMEOUT)
        
        return config
    
    def _load_detector_config(self, detection_type: str) -> Dict[str, Any]:
        """Load detector configuration from defaults and custom settings"""
        # Start with default configuration
        config = DEFAULT_DETECTION_CONFIG.get(detection_type, {}).copy()
        
        # Load custom configuration if exists
        custom_config = self._load_custom_config()
        if custom_config and detection_type in custom_config:
            config.update(custom_config[detection_type])
        
        # Ensure required fields
        config.setdefault('enabled', True)
        config.setdefault('threshold', 0.5)
        config.setdefault('visualization', {})
        
        return config
    
    def _load_custom_config(self) -> Optional[Dict[str, Any]]:
        """Load custom configuration from file"""
        if not os.path.exists(self.custom_config_file):
            return None
        
        try:
            with open(self.custom_config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # Log error but continue with defaults
            print(f"Error loading custom config: {e}")
            return None
    
    def update_detector_config(self, detection_type: str, updates: Dict[str, Any]) -> bool:
        """Update configuration for a specific detector type"""
        try:
            # Load current custom configuration
            custom_config = self._load_custom_config() or {}
            
            # Update the specific detector configuration
            if detection_type not in custom_config:
                custom_config[detection_type] = {}
            
            custom_config[detection_type].update(updates)
            
            # Save custom configuration
            self._save_custom_config(custom_config)
            
            # Clear cache for this detector
            cache_key = f'{self.CACHE_KEY_PREFIX}{detection_type}'
            cache.delete(cache_key)
            
            return True
            
        except Exception as e:
            print(f"Error updating detector config: {e}")
            return False
    
    def _save_custom_config(self, config: Dict[str, Any]) -> None:
        """Save custom configuration to file"""
        os.makedirs(self.config_dir, exist_ok=True)
        
        with open(self.custom_config_file, 'w') as f:
            json.dump(config, f, indent=2, sort_keys=True)
    
    def reset_detector_config(self, detection_type: str) -> bool:
        """Reset detector configuration to defaults"""
        try:
            custom_config = self._load_custom_config() or {}
            
            if detection_type in custom_config:
                del custom_config[detection_type]
                self._save_custom_config(custom_config)
            
            # Clear cache
            cache_key = f'{self.CACHE_KEY_PREFIX}{detection_type}'
            cache.delete(cache_key)
            
            return True
            
        except Exception as e:
            print(f"Error resetting detector config: {e}")
            return False
    
    def get_available_detectors(self) -> list:
        """Get list of available detector types"""
        return list(DEFAULT_DETECTION_CONFIG.keys())
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return PERFORMANCE_CONFIG.copy()
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return API_CONFIG.copy()
    
    def get_camera_config(self) -> Dict[str, Any]:
        """Get camera configuration"""
        return CAMERA_CONFIG.copy()
    
    def validate_detector_config(self, detection_type: str, config: Dict[str, Any]) -> tuple[bool, list]:
        """Validate detector configuration"""
        errors = []
        
        # Check if detector type is valid
        if detection_type not in DEFAULT_DETECTION_CONFIG:
            errors.append(f"Unknown detector type: {detection_type}")
            return False, errors
        
        # Validate threshold
        if 'threshold' in config:
            threshold = config['threshold']
            if not isinstance(threshold, (int, float)) or not (0 <= threshold <= 1):
                errors.append("Threshold must be a number between 0 and 1")
        
        # Validate enabled flag
        if 'enabled' in config:
            enabled = config['enabled']
            if not isinstance(enabled, bool):
                errors.append("Enabled flag must be a boolean")
        
        # Detector-specific validation
        if detection_type == 'barcode' and 'pyzbar_config' in config:
            pyzbar_config = config['pyzbar_config']
            if 'decode_types' in pyzbar_config:
                valid_types = ['QRCODE', 'CODE128', 'CODE39', 'EAN13', 'EAN8', 'UPC_A', 'UPC_E']
                for dtype in pyzbar_config['decode_types']:
                    if dtype not in valid_types:
                        errors.append(f"Invalid barcode type: {dtype}")
        
        elif detection_type == 'phone' and 'model_config' in config:
            model_config = config['model_config']
            if 'confidence_threshold' in model_config:
                conf_threshold = model_config['confidence_threshold']
                if not isinstance(conf_threshold, (int, float)) or not (0 <= conf_threshold <= 1):
                    errors.append("Model confidence threshold must be between 0 and 1")
        
        elif detection_type == 'yellowbox' and 'color_config' in config:
            color_config = config['color_config']
            if 'hsv_range' in color_config:
                hsv_range = color_config['hsv_range']
                if 'lower' not in hsv_range or 'upper' not in hsv_range:
                    errors.append("HSV range must include 'lower' and 'upper' bounds")
        
        return len(errors) == 0, errors
    
    def get_detector_status(self) -> Dict[str, Any]:
        """Get status of all detectors"""
        status = {}
        
        for detector_type in self.get_available_detectors():
            config = self.get_detector_config(detector_type)
            
            status[detector_type] = {
                'enabled': config.get('enabled', False),
                'threshold': config.get('threshold', 0.5),
                'last_updated': self._get_last_updated(detector_type)
            }
        
        return status
    
    def _get_last_updated(self, detection_type: str) -> str:
        """Get last updated timestamp for detector configuration"""
        try:
            if os.path.exists(self.custom_config_file):
                import datetime
                mtime = os.path.getmtime(self.custom_config_file)
                return datetime.datetime.fromtimestamp(mtime).isoformat()
        except:
            pass
        
        return "Never"


# Global instance
detection_config_manager = DetectionConfigManager()


def get_detector_config(detection_type: str) -> Dict[str, Any]:
    """Convenience function to get detector configuration"""
    return detection_config_manager.get_detector_config(detection_type)


def update_detector_config(detection_type: str, updates: Dict[str, Any]) -> bool:
    """Convenience function to update detector configuration"""
    return detection_config_manager.update_detector_config(detection_type, updates)


def get_available_detectors() -> list:
    """Convenience function to get available detectors"""
    return detection_config_manager.get_available_detectors()