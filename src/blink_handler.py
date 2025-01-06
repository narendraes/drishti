"""
Blink Camera Handler Module for Local Network

This module handles all interactions with the Blink camera system on local network:
- Discovering cameras on local network
- Monitoring local storage for new videos
- Tracking motion state changes
"""

import asyncio
import os
import logging
from pathlib import Path
import aiofiles
import aiofiles.os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlinkLocalHandler:
    def __init__(self, local_storage_path):
        """
        Initialize Blink local handler
        
        Args:
            local_storage_path (str): Path to local Blink storage directory
        """
        self.storage_path = Path(local_storage_path)
        self.cameras = {}  # Dictionary to store camera info
        self.event_callbacks = []
        self.observer = Observer()
        
    async def initialize(self):
        """Initialize local camera monitoring"""
        try:
            # Verify storage path exists
            if not await aiofiles.os.path.exists(self.storage_path):
                logger.error(f"Storage path not found: {self.storage_path}")
                return False
                
            # Discover cameras by directory structure
            await self._discover_cameras()
            
            # Setup file system monitoring
            event_handler = BlinkFileHandler(self._handle_new_video)
            self.observer.schedule(event_handler, str(self.storage_path), recursive=True)
            self.observer.start()
            
            logger.info(f"Initialized local monitoring for {len(self.cameras)} cameras")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing local handler: {str(e)}")
            return False
            
    async def _discover_cameras(self):
        """Discover cameras from local storage structure"""
        try:
            async for entry in aiofiles.os.scandir(self.storage_path):
                if await aiofiles.os.path.isdir(entry.path):
                    camera_name = entry.name
                    self.cameras[camera_name] = {
                        'name': camera_name,
                        'path': entry.path
                    }
        except Exception as e:
            logger.error(f"Error discovering cameras: {str(e)}")
            
    def _handle_new_video(self, video_path):
        """Handle new video file detection"""
        camera_name = Path(video_path).parent.name
        if camera_name in self.cameras:
            for callback in self.event_callbacks:
                asyncio.create_task(callback({
                    'camera_name': camera_name,
                    'video_path': video_path
                }))
                
    async def get_latest_video(self, camera_name):
        """Get most recent video for a camera"""
        if camera_name not in self.cameras:
            return None
            
        camera_path = Path(self.cameras[camera_name]['path'])
        try:
            videos = sorted(camera_path.glob('*.mp4'), key=os.path.getmtime, reverse=True)
            return str(videos[0]) if videos else None
        except Exception as e:
            logger.error(f"Error getting latest video: {str(e)}")
            return None
            
    async def get_latest_image(self, camera_name):
        """Get most recent image for a camera"""
        if camera_name not in self.cameras:
            return None
            
        camera_path = Path(self.cameras[camera_name]['path'])
        try:
            images = sorted(camera_path.glob('*.jpg'), key=os.path.getmtime, reverse=True)
            return str(images[0]) if images else None
        except Exception as e:
            logger.error(f"Error getting latest image: {str(e)}")
            return None
            
    def add_event_callback(self, callback):
        """Add callback for motion events"""
        self.event_callbacks.append(callback)
        
class BlinkFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.mp4'):
            self.callback(event.src_path) 