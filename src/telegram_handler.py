"""
Telegram Bot Handler Module

This module manages all Telegram bot interactions, including:
- Sending motion detection alerts
- Sending video clips from motion events
- Managing bot authentication and chat communications
- Handling bot commands (dgetphoto, dgetvideo, ddisconnect)

Dependencies:
- python-telegram-bot: For Telegram bot API integration
- python-dotenv: For loading environment variables
"""

import os
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from dotenv import load_dotenv
import asyncio

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramHandler:
    """
    Handles Telegram bot operations and message sending.
    
    Attributes:
        bot_token (str): Telegram bot API token from environment variables
        chat_id (str): Target chat ID for sending notifications
        bot (Bot): Telegram bot instance
        app (Application): Telegram application instance
        blink_handler (BlinkHandler): Reference to BlinkHandler for camera operations
    """
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.bot = Bot(self.bot_token)
        self.app = Application.builder().token(self.bot_token).build()
        self.blink_handler = None  # Will be set by monitor
        self._running = True
        self.HELP_TEXT = """
🤖 *Available Commands*

📸 */dgetphoto* <camera_name>
   Get a current photo from specified camera
   Example: `/dgetphoto front_door`

🎥 */dgetvideo* <camera_name>
   Get a 5-second video from specified camera
   Example: `/dgetvideo backyard`

⏹ */ddisconnect*
   Stop all monitoring until app restart

ℹ️ */dhelp*
   Show this help message

*Note:* Replace <camera_name> with your actual camera name
"""
        
    def set_blink_handler(self, blink_handler):
        """Set the blink handler reference"""
        self.blink_handler = blink_handler
        
    async def setup_handlers(self):
        """Setup command handlers"""
        self.app.add_handler(CommandHandler("dgetphoto", self.cmd_get_photo))
        self.app.add_handler(CommandHandler("dgetvideo", self.cmd_get_video))
        self.app.add_handler(CommandHandler("ddisconnect", self.cmd_disconnect))
        self.app.add_handler(CommandHandler("dhelp", self.cmd_help))
        self.app.add_handler(CommandHandler("start", self.cmd_help))
        
    async def start_polling(self):
        """Start the bot polling"""
        await self.app.initialize()
        await self.app.start()
        await self.app.run_polling()
        
    async def cmd_get_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle dgetphoto command"""
        if not self._running:
            await update.message.reply_text("Bot is disconnected. Please restart the application.")
            return
            
        try:
            camera_name = context.args[0] if context.args else None
            if not camera_name:
                await update.message.reply_text("Please specify a camera name: /dgetphoto <camera_name>")
                return
                
            camera = self.blink_handler.blink.cameras.get(camera_name)
            if not camera:
                await update.message.reply_text(f"Camera '{camera_name}' not found")
                return
                
            # Take new photo
            await camera.snap_picture()
            await self.blink_handler.blink.refresh()
            
            # Get the latest image
            image_url = camera.image_from_cache
            await update.message.reply_photo(
                photo=image_url,
                caption=f"Current photo from {camera_name}"
            )
            
        except Exception as e:
            logger.error(f"Error in dgetphoto command: {str(e)}")
            await update.message.reply_text(f"Error getting photo: {str(e)}")
            
    async def cmd_get_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle dgetvideo command"""
        if not self._running:
            await update.message.reply_text("Bot is disconnected. Please restart the application.")
            return
            
        try:
            camera_name = context.args[0] if context.args else None
            if not camera_name:
                await update.message.reply_text("Please specify a camera name: /dgetvideo <camera_name>")
                return
                
            camera = self.blink_handler.blink.cameras.get(camera_name)
            if not camera:
                await update.message.reply_text(f"Camera '{camera_name}' not found")
                return
                
            # Request a new video clip (5 seconds)
            await camera.record_video()
            await self.blink_handler.blink.refresh()
            
            # Get the video URL
            video_url = camera.video_from_cache
            await update.message.reply_video(
                video=video_url,
                caption=f"5-second video from {camera_name}"
            )
            
        except Exception as e:
            logger.error(f"Error in dgetvideo command: {str(e)}")
            await update.message.reply_text(f"Error getting video: {str(e)}")
            
    async def cmd_disconnect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle ddisconnect command"""
        try:
            self._running = False
            await update.message.reply_text(
                "Bot disconnected. The application will stop monitoring until restarted."
            )
        except Exception as e:
            logger.error(f"Error in ddisconnect command: {str(e)}")
            
    async def is_running(self):
        """Check if the bot is running"""
        return self._running
        
    async def send_motion_alert(self, camera_name, video_path=None):
        """Send motion alert with optional video to Telegram"""
        if not self._running:
            return
            
        try:
            message = f"🚨 Motion detected on camera: {camera_name}"
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            
            if video_path:
                with open(video_path, 'rb') as video:
                    await self.bot.send_video(
                        chat_id=self.chat_id,
                        video=video,
                        caption=f"Motion video from {camera_name}"
                    )
            
            logger.info(f"Alert sent for camera {camera_name}")
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {str(e)}")
            
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help command"""
        try:
            await update.message.reply_text(
                self.HELP_TEXT,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error sending help message: {str(e)}")
            await update.message.reply_text("Error displaying help message. Please try again.") 