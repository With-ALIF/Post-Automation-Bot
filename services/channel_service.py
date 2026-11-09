import logging
from typing import Dict, Any, Optional
from telegram import Bot
from config import Config
from utils.helpers import sanitize_text

logger = logging.getLogger(__name__)


class ChannelService:
    @staticmethod
    def is_enabled() -> bool:
        return bool(Config.TELEGRAM_CHANNEL_ID and Config.AUTO_POST_TO_CHANNEL)

    @staticmethod
    async def publish_text_to_channel(bot: Bot, text: str) -> Dict[str, Any]:
        if not Config.TELEGRAM_CHANNEL_ID:
            return {"success": False, "error": "TELEGRAM_CHANNEL_ID কনফিগার করা হয়নি।"}

        try:
            msg = await bot.send_message(
                chat_id=Config.TELEGRAM_CHANNEL_ID,
                text=text
            )
            return {
                "success": True,
                "message_id": msg.message_id,
                "chat_id": msg.chat_id
            }
        except Exception as e:
            logger.error("Channel publish text error: %s", sanitize_text(str(e)))
            return {
                "success": False,
                "error": f"টেলিগ্রাম চ্যানেলে পোস্ট করতে ত্রুটি: {sanitize_text(str(e))}"
            }

    @staticmethod
    async def publish_photo_to_channel(bot: Bot, photo_file_id: str, caption: Optional[str] = None) -> Dict[str, Any]:
        if not Config.TELEGRAM_CHANNEL_ID:
            return {"success": False, "error": "TELEGRAM_CHANNEL_ID কনফিগার করা হয়নি।"}

        try:
            msg = await bot.send_photo(
                chat_id=Config.TELEGRAM_CHANNEL_ID,
                photo=photo_file_id,
                caption=caption
            )
            return {
                "success": True,
                "message_id": msg.message_id,
                "chat_id": msg.chat_id
            }
        except Exception as e:
            logger.error("Channel publish photo error: %s", sanitize_text(str(e)))
            return {
                "success": False,
                "error": f"টেলিগ্রাম চ্যানেলে ছবি পোস্ট করতে ত্রুটি: {sanitize_text(str(e))}"
            }


channel_service = ChannelService()
