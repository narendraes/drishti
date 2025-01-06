"""
Blink Camera Monitor Module

This is the main module that coordinates between Blink cameras and Telegram notifications.
It handles:
- Continuous monitoring of Blink cameras
- Processing of motion events
- Video clip retrieval and temporary storage
- Coordination of notifications via Telegram

Dependencies:
- blink_handler: For Blink camera operations
- telegram_handler: For Telegram notifications
- tempfile: For temporary video storage
"""

import asyncio
import os
import logging
from blink_handler import BlinkHandler
from telegram_handler import TelegramHandler
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlinkMonitor:
    """
    Main monitoring system that coordinates between Blink cameras and Telegram notifications.
    
    Attributes:
        blink_handler (BlinkHandler): Handles Blink camera operations
        telegram_handler (TelegramHandler): Handles Telegram notifications
        temp_dir (str): Directory for temporary video storage
    """
    def __init__(self):
        self.blink_handler = BlinkHandler()
        self.telegram_handler = TelegramHandler()
        self.temp_dir = tempfile.gettempdir()
        
        # Set up cross-references
        self.telegram_handler.set_blink_handler(self.blink_handler)
        
    async def process_motion_events(self, events):
        """Process motion events and send notifications"""
        if not await self.telegram_handler.is_running():
            return
            
        for event in events:
            camera = event['camera']
            name = event['name']
            
            # Create temporary file for video
            temp_video = os.path.join(self.temp_dir, f"motion_{name}.mp4")
            
            try:
                # Download the video
                await camera.video_to_file(temp_video)
                
                # Send alert with video
                await self.telegram_handler.send_motion_alert(name, temp_video)
                
                # Clean up
                os.remove(temp_video)
            except Exception as e:
                logger.error(f"Error processing motion event: {str(e)}")
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        if not await self.blink_handler.initialize():
            return
            
        # Setup and start Telegram bot
        await self.telegram_handler.setup_handlers()
        
        logger.info("Starting monitoring loop...")
        
        # Start bot polling in the background
        asyncio.create_task(self.telegram_handler.start_polling())
        
        while True:
            try:
                if not await self.telegram_handler.is_running():
                    logger.info("Bot disconnected. Stopping monitor loop.")
                    break
                    
                # Check for motion events
                events = await self.blink_handler.check_motion()
                if events:
                    await self.process_motion_events(events)
                
                # Wait before next check (30 seconds to respect API limits)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error

async def main():
    monitor = BlinkMonitor()
    await monitor.monitor_loop()

if __name__ == "__main__":
    asyncio.run(main()) 