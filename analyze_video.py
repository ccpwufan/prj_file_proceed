#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from pathlib import Path

def get_video_info(video_path):
    """Get video information using ffprobe if available, otherwise basic file info"""
    try:
        # Try to use ffprobe first
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_format', '-show_streams', video_path
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        pass
    
    # Fallback to basic file info
    info = {
        'format': {
            'filename': os.path.basename(video_path),
            'size': os.path.getsize(video_path),
            'format_name': 'unknown'
        },
        'streams': []
    }
    
    # Try to get basic info using OpenCV
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            info['streams'].append({
                'codec_type': 'video',
                'width': width,
                'height': height,
                'fps': fps,
                'frame_count': frame_count,
                'duration': frame_count / fps if fps > 0 else 0
            })
        cap.release()
    except ImportError:
        pass
    
    return info

def analyze_video_compatibility(video_info):
    """Analyze video compatibility with web browsers"""
    issues = []
    recommendations = []
    
    # Check format
    format_name = video_info.get('format', {}).get('format_name', '').lower()
    if 'mp4' not in format_name:
        issues.append(f"Container format: {format_name} (MP4 recommended)")
    
    # Check streams
    video_streams = [s for s in video_info.get('streams', []) if s.get('codec_type') == 'video']
    audio_streams = [s for s in video_info.get('streams', []) if s.get('codec_type') == 'audio']
    
    for stream in video_streams:
        codec = stream.get('codec_name', '').lower()
        if codec not in ['h264', 'avc', 'mpeg4']:
            issues.append(f"Video codec: {codec} (H.264/AVC recommended for web)")
            recommendations.append("Convert video to H.264 encoding for better browser compatibility")
        
        profile = stream.get('profile', '').lower()
        if profile and 'high' in profile:
            recommendations.append("Consider using H.264 Main or Baseline profile for older devices")
    
    for stream in audio_streams:
        codec = stream.get('codec_name', '').lower()
        if codec not in ['aac', 'mp3']:
            issues.append(f"Audio codec: {codec} (AAC recommended for web)")
            recommendations.append("Convert audio to AAC encoding for better browser compatibility")
    
    return issues, recommendations

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_video.py <video_file>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"Error: File {video_path} not found")
        sys.exit(1)
    
    print(f"Analyzing: {video_path}")
    print("=" * 50)
    
    # Get video info
    info = get_video_info(video_path)
    
    # Print basic info
    format_info = info.get('format', {})
    print(f"File: {format_info.get('filename', 'Unknown')}")
    print(f"Size: {format_info.get('size', 0) / (1024*1024):.2f} MB")
    print(f"Format: {format_info.get('format_name', 'Unknown')}")
    print(f"Duration: {format_info.get('duration', 'Unknown')} seconds")
    
    # Print stream info
    print("\nStreams:")
    for i, stream in enumerate(info.get('streams', [])):
        codec_type = stream.get('codec_type', 'unknown')
        print(f"  Stream {i}: {codec_type}")
        
        if codec_type == 'video':
            print(f"    Codec: {stream.get('codec_name', 'Unknown')}")
            print(f"    Resolution: {stream.get('width', '?')}x{stream.get('height', '?')}")
            print(f"    FPS: {stream.get('fps', 'Unknown')}")
            print(f"    Profile: {stream.get('profile', 'Unknown')}")
        elif codec_type == 'audio':
            print(f"    Codec: {stream.get('codec_name', 'Unknown')}")
            print(f"    Sample Rate: {stream.get('sample_rate', 'Unknown')} Hz")
            print(f"    Channels: {stream.get('channels', 'Unknown')}")
    
    # Analyze compatibility
    print("\nCompatibility Analysis:")
    issues, recommendations = analyze_video_compatibility(info)
    
    if issues:
        print("  Issues:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  No compatibility issues detected")
    
    if recommendations:
        print("\n  Recommendations:")
        for rec in recommendations:
            print(f"    - {rec}")

if __name__ == "__main__":
    main()