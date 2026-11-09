import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import Config

logger = logging.getLogger(__name__)


def is_user_authorized(user_id: int) -> bool:
    if not Config.ALLOWED_USER_IDS:
        return False
    return user_id in Config.ALLOWED_USER_IDS


def authorized_only(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        if not is_user_authorized(user.id):
            username = user.username or user.first_name or "Unknown"
            logger.warning(
                "Unauthorized access attempt! User ID: %s, Username: @%s",
                user.id, username
            )

            message_text = (
                "⛔ *Access Denied / অনুমতি নেই*\n\n"
                f"আপনি এই বটটি ব্যবহার করার জন্য অনুমোদিত নন।\n"
                f"Your Telegram User ID: `{user.id}`\n\n"
                "বটটি ব্যবহার করতে এই User ID-টি বটের `.env` ফাইলের "
                "`ALLOWED_USER_IDS` তালিকায় যুক্ত করুন।"
            )

            if update.callback_query:
                await update.callback_query.answer("⛔ Unauthorized access!", show_alert=True)
                try:
                    await update.callback_query.edit_message_text(
                        text=message_text,
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            elif update.effective_message:
                await update.effective_message.reply_text(
                    text=message_text,
                    parse_mode="Markdown"
                )
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
