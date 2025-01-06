"""
Blink Camera Handler Module

This module handles all interactions with the Blink camera system, including:
- Initializing connection to Blink servers
- Authentication using credentials from config/secrets.json
- Monitoring cameras for motion events
- Tracking motion state changes

Dependencies:
- blinkpy: For Blink camera integration
- aiohttp: For async HTTP requests
- logging: For event logging
"""

import asyncio
from aiohttp import ClientSession
from blinkpy.blinkpy import Blink
from blinkpy.auth import Auth
from blinkpy.helpers.util import json_load
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlinkHandler:
    """
    Manages Blink camera system interactions and motion detection.
    
    Attributes:
        blink (Blink): Main Blink system instance
        previous_motion_states (dict): Tracks motion states for all cameras
    """
    
    def __init__(self):
        self.blink = None
        self.previous_motion_states = {}
        
    async def initialize(self):
        """Initialize Blink connection"""
        try:
            self.blink = Blink(session=ClientSession())
            auth = Auth(await json_load("config/secrets.json"), no_prompt=True)
            self.blink.auth = auth
            await self.blink.start()
            
            # Initialize previous motion states
            for name, camera in self.blink.cameras.items():
                self.previous_motion_states[name] = False
                
            logger.info("Blink system initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing Blink system: {str(e)}")
            return False
            
    async def check_motion(self):
        """Check for motion on all cameras"""
        try:
            await self.blink.refresh(force=True)
            motion_events = []
            
            for name, camera in self.blink.cameras.items():
                current_motion = camera.motion_detected
                if current_motion and not self.previous_motion_states[name]:
                    # Motion was just detected
                    motion_events.append({
                        'camera': camera,
                        'name': name
                    })
                self.previous_motion_states[name] = current_motion
                
            return motion_events
        except Exception as e:
            logger.error(f"Error checking motion: {str(e)}")
            return [] 