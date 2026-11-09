import sys
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from config import Config
from handlers.command_handlers import (
    start_command,
    help_command,
    status_command,
    cancel_command,
    settings_command
)
from handlers.menu_handlers import handle_menu_click
from handlers.post_handlers import (
    handle_text_message,
    handle_photo_message,
    handle_callback_query
)
from utils.helpers import sanitize_text

logging.basicConfig(
    format="%(asctime)s - [%(name)s] - [%(levelname)s] - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger("PageBot")


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err_str = sanitize_text(str(context.error))
    logger.error("Exception handled by global error handler: %s", err_str, exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ *একটি অপ্রত্যাশিত সিস্টেম ত্রুটি ঘটেছে।*\n"
                "দয়া করে কিছুক্ষণ পর পুনরায় চেষ্টা করুন।",
                parse_mode="Markdown"
            )
        except Exception:
            pass


def main() -> None:
    missing_vars = Config.validate()
    if missing_vars:
        logger.error("CRITICAL: Missing required configuration variables in .env file:")
        for var in missing_vars:
            logger.error("  - %s", var)
        sys.exit(1)

    application = (
        Application.builder()
        .token(Config.TELEGRAM_BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    menu_regex = r"^(📝 Create Text Post|🖼 Create Image Post|📊 Publishing Status|⚙️ Settings)$"
    application.add_handler(MessageHandler(filters.Regex(menu_regex), handle_menu_click))

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_error_handler(global_error_handler)

    print("✅ Bot initialized successfully! Listening for Telegram updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
