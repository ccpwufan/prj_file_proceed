/**
 * Camera Detection Module
 * Handles camera access, frame capture, and detection API communication
 */

class CameraDetection {
    constructor() {
        this.cameraActive = false;
        this.cameraStarting = false;
        this.detectionType = 'barcode'; // Default detection type
        this.detectionThreshold = 0.5;
        this.detectionInterval = 1.0;
        this.currentDetections = [];
        this.detectionHistory = [];
        this.stream = null;
        this.detectionTimer = null;
        this.apiBaseUrl = '/video/api/';
        
        // DOM elements
        this.videoElement = null;
        this.canvasElement = null;
        this.statusElement = null;
        
        // Detection configuration
        this.detectionConfig = {
            barcode: { threshold: 0.3, color: '#00ff00', label: 'Barcode' },
            phone: { threshold: 0.7, color: '#ff0000', label: 'Phone' },
            yellowbox: { threshold: 0.6, color: '#ffff00', label: 'Yellow Box' }
        };
    }

    /**
     * Initialize camera detection
     */
    async init() {
        try {
            // Load detection configuration from API
            await this.loadDetectionConfig();
            
            // Get DOM elements
            this.videoElement = document.querySelector('video[x-ref="videoElement"]');
            this.canvasElement = document.querySelector('canvas[x-ref="canvasElement"]');
            this.statusElement = document.querySelector('[data-detection-status]');
            
            console.log('Camera detection initialized');
            return true;
        } catch (error) {
            console.error('Failed to initialize camera detection:', error);
            return false;
        }
    }

    /**
     * Load detection configuration from API
     */
    async loadDetectionConfig() {
        try {
            const response = await fetch(`${this.apiBaseUrl}detection/`);
            const data = await response.json();
            
            if (data.success) {
                // Update configuration with server defaults
                Object.keys(data.default_thresholds).forEach(type => {
                    if (this.detectionConfig[type]) {
                        this.detectionConfig[type].threshold = data.default_thresholds[type];
                    }
                });
                
                console.log('Detection configuration loaded:', this.detectionConfig);
            }
        } catch (error) {
            console.warn('Failed to load detection config, using defaults:', error);
        }
    }

    /**
     * Set detection type
     */
    setDetectionType(type) {
        if (!this.detectionConfig[type]) {
            console.error(`Unknown detection type: ${type}`);
            return;
        }
        
        this.detectionType = type;
        this.detectionThreshold = this.detectionConfig[type].threshold;
        this.currentDetections = []; // Clear current detections
        
        if (this.cameraActive) {
            this.updateStatus(`Switched to ${this.detectionConfig[type].label} detection`);
        }
        
        console.log(`Detection type set to: ${type}`);
    }

    /**
     * Get display label for detection type
     */
    getDetectionTypeLabel(type) {
        return this.detectionConfig[type]?.label.toLowerCase() || 'objects';
    }

    /**
     * Toggle camera on/off
     */
    async toggleCamera() {
        if (this.cameraActive) {
            this.stopCamera();
        } else {
            await this.startCamera();
        }
    }

    /**
     * Start camera and detection
     */
    async startCamera() {
        if (this.cameraStarting) {
            return; // Already starting
        }
        
        this.cameraStarting = true;
        this.updateStatus('Starting camera...');
        
        try {
            // Request camera access
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'environment' // Prefer rear camera on mobile
                } 
            });
            
            if (!this.videoElement) {
                throw new Error('Video element not found');
            }
            
            this.videoElement.srcObject = this.stream;
            
            // Wait for video to be ready
            await new Promise((resolve, reject) => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play()
                        .then(resolve)
                        .catch(reject);
                };
                this.videoElement.onerror = reject;
                
                // Timeout after 5 seconds
                setTimeout(() => reject(new Error('Video loading timeout')), 5000);
            });
            
            // Setup canvas for detection
            if (this.canvasElement) {
                this.canvasElement.width = this.videoElement.videoWidth;
                this.canvasElement.height = this.videoElement.videoHeight;
            }
            
            this.cameraActive = true;
            this.cameraStarting = false;
            this.updateStatus(`Detecting ${this.getDetectionTypeLabel(this.detectionType)}...`);
            
            // Start detection loop
            this.startDetection();
            
            console.log('Camera started successfully');
            
        } catch (error) {
            console.error('Camera access error:', error);
            this.showMessage('Cannot access camera, please check permissions', 'error');
            this.cameraStarting = false;
            this.updateStatus('Camera startup failed');
        }
    }

    /**
     * Stop camera and detection
     */
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.detectionTimer) {
            clearInterval(this.detectionTimer);
            this.detectionTimer = null;
        }
        
        this.cameraActive = false;
        this.currentDetections = [];
        this.updateStatus('Camera stopped');
        
        console.log('Camera stopped');
    }

    /**
     * Start detection loop
     */
    startDetection() {
        this.detectionTimer = setInterval(async () => {
            // Use default options for regular detection
            await this.performDetection();
        }, this.detectionInterval * 1000);
        
        console.log(`Detection started with ${this.detectionInterval}s interval`);
    }

    /**
     * Perform detection on current frame
     * @param {Object} options - Configuration options for detection
     * @param {boolean} options.updateCanvas - Whether to update canvas with detection results (default: true)
     * @param {boolean} options.updateStatus - Whether to update status message (default: true)
     * @param {string} options.imageFormat - Image format for frame data (default: 'image/jpeg')
     * @param {number} options.imageQuality - Image quality for frame data (default: 0.8)
     * @returns {Object} - Object containing frame data and detection results
     */
    async performDetection(options = {}) {
        if (!this.cameraActive || !this.videoElement || !this.canvasElement) {
            return null;
        }
        
        // Set default options
        const {
            updateCanvas = true,
            updateStatus = true,
            imageFormat = 'image/jpeg',
            imageQuality = 0.8
        } = options;
        
        try {
            // Draw current video frame to canvas
            const ctx = this.canvasElement.getContext('2d');
            ctx.drawImage(this.videoElement, 0, 0);
            
            // Get frame as base64 for API
            const frameData = this.canvasElement.toDataURL(imageFormat, imageQuality);
            
            // Call detection API
            const detections = await this.callDetectionAPI(frameData);
            
            // Update current detections
            this.currentDetections = detections;
            
            // Draw detection results if requested
            if (updateCanvas) {
                this.drawDetections(ctx, detections);
            }
            
            // Update status if requested
            if (updateStatus) {
                const detectionLabel = this.getDetectionTypeLabel(this.detectionType);
                this.updateStatus(`Detecting ${detectionLabel}... (${detections.length} found)`);
            }
            
            // Return frame data and detections
            return {
                frameData,
                detections,
                detectionType: this.detectionType,
                threshold: this.detectionThreshold,
                timestamp: new Date().toLocaleString()
            };
            
        } catch (error) {
            console.error('Detection failed:', error);
            if (updateStatus) {
                this.updateStatus('Detection failed');
            }
            return null;
        }
    }

    /**
     * Call detection API
     */
    async callDetectionAPI(frameData) {
        try {
            const response = await fetch(`${this.apiBaseUrl}detection/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: frameData,
                    detection_type: this.detectionType,
                    threshold: this.detectionThreshold
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                return data.detections || [];
            } else {
                console.error('Detection API error:', data.error);
                return [];
            }
            
        } catch (error) {
            console.error('Failed to call detection API:', error);
            return [];
        }
    }

    /**
     * Draw detection results on canvas
     */
    drawDetections(ctx, detections) {
        const config = this.detectionConfig[this.detectionType];
        
        detections.forEach(detection => {
            const [x, y, width, height] = detection.bbox;
            
            // Draw bounding box
            ctx.strokeStyle = config.color;
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, width, height);
            
            // Draw label background
            const label = `${detection.class} (${(detection.confidence * 100).toFixed(1)}%)`;
            ctx.font = '14px Arial';
            const textWidth = ctx.measureText(label).width;
            
            ctx.fillStyle = config.color;
            ctx.fillRect(x, y - 20, textWidth + 8, 20);
            
            // Draw label text
            ctx.fillStyle = '#000000';
            ctx.fillText(label, x + 4, y - 6);
            
            // Draw additional data (e.g., barcode content)
            if (detection.data && Object.keys(detection.data).length > 0) {
                const dataText = Object.entries(detection.data)
                    .map(([key, value]) => `${key}: ${value}`)
                    .join(', ');
                
                ctx.font = '12px Arial';
                ctx.fillStyle = config.color;
                ctx.fillText(dataText, x, y + height + 15);
            }
        });
    }

    /**
     * Capture current frame and send for detection
     */
    async captureSnapshot() {
        try {
            if (!this.videoElement || !this.canvasElement) {
                throw new Error('Video or canvas element not available');
            }
            
            // Ensure video is playing
            if (this.videoElement.readyState < 2) { // HAVE_CURRENT_DATA
                throw new Error('Video not ready');
            }
            
            // Draw current video frame to canvas
            const ctx = this.canvasElement.getContext('2d');
            ctx.drawImage(this.videoElement, 0, 0, this.canvasElement.width, this.canvasElement.height);
            
            // Get image data as base64
            const frameData = this.canvasElement.toDataURL('image/jpeg', 0.8);
            
            // Perform detection on current frame
            const detectionResult = await this.performDetection(); // Call without parameters
            
            // Extract detections from result
            const detections = detectionResult ? detectionResult.detections : [];
            
            // Get current detection settings
            const detectionType = this.detectionType;
            const threshold = this.detectionThreshold;
            const timestamp = new Date().toLocaleString(); // Use local time string
            
            // Create result object
            const result = {
                frameData,
                detections,
                detectionType,
                threshold,
                timestamp
            };
            
            console.log('Captured snapshot with detections:');
            
            // Draw detection results to canvas for the annotated image
            this.drawDetections(ctx, detections);
            
            // Get the annotated frame (with detection boxes)
            const annotatedFrameData = this.canvasElement.toDataURL('image/png');
            
            // Create detection_data object
            const detection_data = {
                image: frameData, // Original image without annotations
                detections: [...detections], // Copy of detections array
                detection_type: detectionType,
                threshold: threshold,
                time: Date.now() / 1000 // Unix timestamp in seconds
            };
            
            // Save snapshot to API with CSRF token
            try {
                const response = await fetch(`/video/capture-snapshot/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken(),
                    },
                    body: JSON.stringify(detection_data)
                });
                
                const data = await response.json();
                
                if (!data.success) {
                    throw new Error(data.message || 'Failed to save snapshot');
                }
                
            } catch (apiError) {
                console.error('Failed to save snapshot to server:', apiError);
                throw apiError;
            }
            
            // Add to local history
            this.detectionHistory.push(detection_data);
            
            // Keep only last 20 snapshots
            if (this.detectionHistory.length > 20) {
                this.detectionHistory.shift();
            }
            
            // Update status
            this.updateStatus(`Snapshot saved (${detections.length} detections)`);
            this.showMessage('Screenshot saved', 'success');
            
        } catch (error) {
            console.error('Failed to capture snapshot:', error);
            this.updateStatus('Failed to save screenshot');
            this.showMessage('Failed to save screenshot', 'error');
        }
    }

    /**
     * Get CSRF token from cookies
     */
    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') return decodeURIComponent(value);
        }
        return '';
    }

    /**
     * Update detection threshold
     */
    setDetectionThreshold(threshold) {
        this.detectionThreshold = parseFloat(threshold);
        
        // Update configuration for current detection type
        if (this.detectionConfig[this.detectionType]) {
            this.detectionConfig[this.detectionType].threshold = this.detectionThreshold;
        }
    }

    /**
     * Update detection interval
     */
    setDetectionInterval(interval) {
        this.detectionInterval = parseFloat(interval);
        
        // Restart detection loop if camera is active
        if (this.cameraActive && this.detectionTimer) {
            clearInterval(this.detectionTimer);
            this.startDetection();
        }
    }

    /**
     * Update status message
     */
    updateStatus(message) {
        if (this.statusElement) {
            this.statusElement.textContent = message;
        }
        
        // Also try to update Alpine.js data if available
        if (window.Alpine && window.Alpine.store) {
            // This will be handled by Alpine.js reactive data
        }
    }

    /**
     * Show message to user
     */
    showMessage(message, type = 'info') {
        // Try to use Alpine.js messages store
        if (window.Alpine && window.Alpine.store('messages')) {
            window.Alpine.store('messages').add(message, type);
        } else {
            // Fallback to console and alert
            console.log(`[${type.toUpperCase()}] ${message}`);
            
            if (type === 'error') {
                alert(message);
            }
        }
    }

    /**
     * Get detection configuration
     */
    getDetectionConfig() {
        return {
            type: this.detectionType,
            threshold: this.detectionThreshold,
            interval: this.detectionInterval,
            available_types: Object.keys(this.detectionConfig)
        };
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopCamera();
        this.stream = null;
        this.videoElement = null;
        this.canvasElement = null;
        this.statusElement = null;
    }
}

// Export for global use
window.CameraDetection = CameraDetection;