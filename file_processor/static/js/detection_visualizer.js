/**
 * Detection Visualizer Module
 * Handles visualization of detection results with different styles for each detection type
 */

class DetectionVisualizer {
    constructor() {
        // Color schemes for different detection types
        this.colorSchemes = {
            barcode: {
                primary: '#00ff00',    // Green
                secondary: '#00cc00',  // Dark green
                text: '#000000',       // Black
                background: 'rgba(0, 255, 0, 0.2)',
                borderStyle: 'solid'
            },
            phone: {
                primary: '#ff0000',     // Red
                secondary: '#cc0000',   // Dark red
                text: '#ffffff',        // White
                background: 'rgba(255, 0, 0, 0.2)',
                borderStyle: 'solid'
            },
            yellowbox: {
                primary: '#ffff00',     // Yellow
                secondary: '#cccc00',   // Dark yellow
                text: '#000000',        // Black
                background: 'rgba(255, 255, 0, 0.3)',
                borderStyle: 'dashed'
            }
        };
        
        // Visualization options
        this.options = {
            showLabels: true,
            showConfidence: true,
            showData: true,
            labelFontSize: 14,
            confidenceDecimals: 1,
            minConfidenceToShow: 0.1,
            animationDuration: 200
        };
    }

    /**
     * Draw detection results on canvas
     */
    drawDetections(ctx, detections, detectionType, timestamp = null) {
        if (!detections || detections.length === 0) {
            return;
        }
        
        const scheme = this.colorSchemes[detectionType] || this.colorSchemes.barcode;
        
        // Sort detections by confidence (highest first)
        const sortedDetections = detections
            .filter(d => d.confidence >= this.options.minConfidenceToShow)
            .sort((a, b) => b.confidence - a.confidence);
        
        // Draw each detection
        sortedDetections.forEach((detection, index) => {
            this.drawSingleDetection(ctx, detection, detectionType, scheme, index, timestamp);
        });
        
        // Draw detection summary
        this.drawDetectionSummary(ctx, sortedDetections.length, detectionType, scheme);
    }

    /**
     * Draw a single detection box with label
     */
    drawSingleDetection(ctx, detection, detectionType, scheme, index, timestamp) {
        const [x, y, width, height] = detection.bbox;
        const confidence = detection.confidence;
        const label = detection.class || 'unknown';
        const data = detection.data || {};
        
        // Save context state
        ctx.save();
        
        // Draw bounding box
        this.drawBoundingBox(ctx, x, y, width, height, scheme, confidence);
        
        // Draw label
        if (this.options.showLabels) {
            this.drawLabel(ctx, x, y, label, confidence, scheme, data, detectionType);
        }
        
        // Draw additional data
        if (this.options.showData && Object.keys(data).length > 0) {
            this.drawAdditionalData(ctx, x, y, width, height, data, scheme);
        }
        
        // Draw timestamp if provided
        if (timestamp) {
            this.drawTimestamp(ctx, x, y, height, timestamp, scheme);
        }
        
        // Restore context state
        ctx.restore();
    }

    /**
     * Draw bounding box
     */
    drawBoundingBox(ctx, x, y, width, height, scheme, confidence) {
        // Set line style based on confidence
        ctx.lineWidth = Math.max(1, Math.floor(confidence * 3));
        ctx.strokeStyle = scheme.primary;
        
        // Apply border style
        if (scheme.borderStyle === 'dashed') {
            ctx.setLineDash([5, 5]);
        } else {
            ctx.setLineDash([]);
        }
        
        // Draw rectangle
        ctx.strokeRect(x, y, width, height);
        
        // Draw background fill with low opacity
        ctx.fillStyle = scheme.background;
        ctx.fillRect(x, y, width, height);
        
        // Reset line dash
        ctx.setLineDash([]);
    }

    /**
     * Draw detection label
     */
    drawLabel(ctx, x, y, label, confidence, scheme, data, detectionType) {
        const labelText = this.options.showConfidence 
            ? `${label} (${(confidence * 100).toFixed(this.options.confidenceDecimals)}%)`
            : label;
        
        // Set font
        ctx.font = `bold ${this.options.labelFontSize}px Arial`;
        ctx.textBaseline = 'top';
        
        // Measure text
        const textMetrics = ctx.measureText(labelText);
        const textWidth = textMetrics.width;
        const textHeight = this.options.labelFontSize + 4;
        
        // Adjust label position based on detection type
        let labelY = y - textHeight;
        
        // Special handling for barcode labels
        if (detectionType === 'barcode' && data.content) {
            labelY = y; // Put label below barcode
        }
        
        // Draw label background
        ctx.fillStyle = scheme.primary;
        ctx.fillRect(x, labelY, textWidth + 8, textHeight);
        
        // Draw label text
        ctx.fillStyle = scheme.text;
        ctx.fillText(labelText, x + 4, labelY + 2);
        
        // Draw type indicator for barcodes
        if (detectionType === 'barcode' && data.type) {
            ctx.font = `${this.options.labelFontSize - 2}px Arial`;
            const typeText = `[${data.type}]`;
            const typeWidth = ctx.measureText(typeText).width;
            
            ctx.fillStyle = scheme.secondary;
            ctx.fillRect(x + textWidth + 8, labelY, typeWidth + 6, textHeight);
            
            ctx.fillStyle = scheme.text;
            ctx.fillText(typeText, x + textWidth + 10, labelY + 2);
        }
    }

    /**
     * Draw additional detection data
     */
    drawAdditionalData(ctx, x, y, width, height, data, scheme) {
        ctx.font = `${this.options.labelFontSize - 2}px Arial`;
        ctx.fillStyle = scheme.secondary;
        
        let dataY = y + height + 15;
        const lineHeight = 16;
        
        Object.entries(data).forEach(([key, value]) => {
            // Skip content for barcode as it's handled in label
            if (key === 'content' || key === 'type') {
                return;
            }
            
            const dataText = `${key}: ${value}`;
            ctx.fillText(dataText, x, dataY);
            dataY += lineHeight;
        });
    }

    /**
     * Draw timestamp
     */
    drawTimestamp(ctx, x, y, height, timestamp, scheme) {
        ctx.font = `${this.options.labelFontSize - 3}px Arial`;
        ctx.fillStyle = scheme.secondary;
        
        const timestampText = new Date(timestamp).toLocaleTimeString();
        ctx.fillText(timestampText, x, y + height + 30);
    }

    /**
     * Draw detection summary
     */
    drawDetectionSummary(ctx, count, detectionType, scheme) {
        const summaryText = `${count} ${this.getPluralLabel(detectionType, count)}`;
        
        ctx.font = `bold ${this.options.labelFontSize + 2}px Arial`;
        ctx.fillStyle = scheme.primary;
        ctx.strokeStyle = scheme.secondary;
        ctx.lineWidth = 2;
        
        // Position summary in top-right corner
        const textMetrics = ctx.measureText(summaryText);
        const padding = 10;
        const boxX = ctx.canvas.width - textMetrics.width - padding * 2 - 20;
        const boxY = 20;
        const boxWidth = textMetrics.width + padding * 2;
        const boxHeight = this.options.labelFontSize + 8;
        
        // Draw background
        ctx.fillStyle = scheme.background;
        ctx.fillRect(boxX, boxY, boxWidth, boxHeight);
        
        // Draw border
        ctx.strokeStyle = scheme.primary;
        ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);
        
        // Draw text
        ctx.fillStyle = scheme.text;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(summaryText, boxX + boxWidth / 2, boxY + boxHeight / 2);
        
        // Reset text alignment
        ctx.textAlign = 'start';
        ctx.textBaseline = 'alphabetic';
    }

    /**
     * Get plural form of detection type label
     */
    getPluralLabel(detectionType, count) {
        const labels = {
            barcode: count === 1 ? 'barcode' : 'barcodes',
            phone: count === 1 ? 'phone' : 'phones',
            yellowbox: count === 1 ? 'yellow box' : 'yellow boxes'
        };
        
        return labels[detectionType] || 'objects';
    }

    /**
     * Create animated detection effect
     */
    animateDetection(ctx, detection, detectionType, progress) {
        if (progress < 0 || progress > 1) {
            return;
        }
        
        const [x, y, width, height] = detection.bbox;
        const scheme = this.colorSchemes[detectionType];
        
        ctx.save();
        
        // Animated scaling effect
        const scale = 0.8 + (progress * 0.2);
        const centerX = x + width / 2;
        const centerY = y + height / 2;
        const scaledWidth = width * scale;
        const scaledHeight = height * scale;
        const scaledX = centerX - scaledWidth / 2;
        const scaledY = centerY - scaledHeight / 2;
        
        // Animated opacity
        ctx.globalAlpha = progress;
        
        // Draw animated box
        ctx.strokeStyle = scheme.primary;
        ctx.lineWidth = 2;
        ctx.setLineDash([10, 5]);
        ctx.strokeRect(scaledX, scaledY, scaledWidth, scaledHeight);
        
        ctx.restore();
    }

    /**
     * Draw detection heatmap overlay
     */
    drawHeatmap(ctx, detections, detectionType) {
        if (!detections || detections.length === 0) {
            return;
        }
        
        const scheme = this.colorSchemes[detectionType];
        
        ctx.save();
        
        // Create gradient for heatmap
        detections.forEach(detection => {
            const [x, y, width, height] = detection.bbox;
            const centerX = x + width / 2;
            const centerY = y + height / 2;
            const radius = Math.max(width, height) * detection.confidence;
            
            const gradient = ctx.createRadialGradient(
                centerX, centerY, 0,
                centerX, centerY, radius
            );
            
            gradient.addColorStop(0, scheme.primary + '40'); // 40% opacity
            gradient.addColorStop(0.5, scheme.primary + '20'); // 20% opacity
            gradient.addColorStop(1, scheme.primary + '00'); // 0% opacity
            
            ctx.fillStyle = gradient;
            ctx.fillRect(centerX - radius, centerY - radius, radius * 2, radius * 2);
        });
        
        ctx.restore();
    }

    /**
     * Configure visualization options
     */
    configure(options) {
        this.options = { ...this.options, ...options };
    }

    /**
     * Get current configuration
     */
    getConfiguration() {
        return { ...this.options };
    }

    /**
     * Add custom color scheme
     */
    addColorScheme(name, scheme) {
        this.colorSchemes[name] = {
            primary: '#00ff00',
            secondary: '#00cc00',
            text: '#000000',
            background: 'rgba(0, 255, 0, 0.2)',
            borderStyle: 'solid',
            ...scheme
        };
    }

    /**
     * Clear canvas
     */
    clearCanvas(ctx) {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    }

    /**
     * Export detection visualization as image
     */
    exportAsImage(ctx, format = 'image/png', quality = 0.9) {
        return ctx.canvas.toDataURL(format, quality);
    }
}

// Export for global use
window.DetectionVisualizer = DetectionVisualizer;