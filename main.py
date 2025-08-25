"""
Discord Music Bot - Main Entry Point
A comprehensive Discord music bot with interactive buttons, Spotify integration, and high-quality audio streaming.
"""

import asyncio
import logging
import os
from bot import MusicBot

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, continue with environment variables only
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to start the Discord music bot."""
    try:
        # Get Discord bot token from environment
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("DISCORD_TOKEN environment variable is required!")
            return
        
        # Create and start the bot
        bot = MusicBot()
        logger.info("Starting Discord Music Bot...")
        await bot.start(token)
        
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error starting bot: {e}")
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
