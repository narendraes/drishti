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
from blink_handler import BlinkLocalHandler
from telegram_handler import TelegramHandler
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlinkMonitor:
    """
    Main monitoring system that coordinates between Blink cameras and Telegram notifications.
    
    Attributes:
        blink_handler (BlinkLocalHandler): Handles Blink camera operations
        telegram_handler (TelegramHandler): Handles Telegram notifications
        temp_dir (str): Directory for temporary video storage
    """
    def __init__(self, local_storage_path):
        self.blink_handler = BlinkLocalHandler(local_storage_path)
        self.telegram_handler = TelegramHandler()
        self.temp_dir = tempfile.gettempdir()
        
        # Set up cross-references
        self.telegram_handler.set_blink_handler(self.blink_handler)
        
        # Add motion callback
        self.blink_handler.add_event_callback(self.handle_motion_event)
        
    async def handle_motion_event(self, event):
        """Handle motion event from local storage"""
        if not await self.telegram_handler.is_running():
            return
            
        try:
            camera_name = event['camera_name']
            video_path = event['video_path']
            
            # Send alert with video
            await self.telegram_handler.send_motion_alert(camera_name, video_path)
            
        except Exception as e:
            logger.error(f"Error handling motion event: {str(e)}")
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        if not await self.blink_handler.initialize():
            return
            
        # Setup and start Telegram bot
        await self.telegram_handler.setup_handlers()
        
        logger.info("Starting monitoring loop...")
        
        # Start bot polling in the background
        asyncio.create_task(self.telegram_handler.start_polling())
        
        # Keep the application running
        while True:
            try:
                if not await self.telegram_handler.is_running():
                    logger.info("Bot disconnected. Stopping monitor loop.")
                    break
                    
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in monitor loop: {str(e)}")
                await asyncio.sleep(60)

async def main():
    local_storage_path = os.getenv('BLINK_LOCAL_STORAGE')
    if not local_storage_path:
        logger.error("BLINK_LOCAL_STORAGE environment variable not set")
        return
        
    monitor = BlinkMonitor(local_storage_path)
    await monitor.monitor_loop()

if __name__ == "__main__":
    asyncio.run(main()) 