from telegram import Update
from telegram.ext import ContextTypes

from utils.auth import authorized_only
from handlers.command_handlers import status_command, settings_command


@authorized_only
async def handle_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.effective_message.text.strip()

    if text == "📝 Create Text Post":
        context.user_data["awaiting_text_post"] = True
        await update.effective_message.reply_text(
            "📝 *টেক্সট পোস্ট তৈরি করুন:*\n\n"
            "ফেসবুক পেজে যে বার্তাটি পোস্ট করতে চান, তা এখন সরাসরি লিখে পাঠান।\n"
            "_(বাতিল করতে চাইলে /cancel লিখুন)_",
            parse_mode="Markdown"
        )
    elif text == "🖼 Create Image Post":
        context.user_data["awaiting_image_post"] = True
        await update.effective_message.reply_text(
            "🖼 *ছবি পোস্ট তৈরি করুন:*\n\n"
            "ফেসবুক পেজে পোস্ট করার জন্য একটি ছবি পাঠান।\n"
            "ছবির সাথে ক্যাপশন লিখে দিতে পারেন, অথবা ছবি পাঠানোর পরও ক্যাপশন যোগ করা যাবে।\n"
            "_(বাতিল করতে চাইলে /cancel লিখুন)_",
            parse_mode="Markdown"
        )
    elif text == "📊 Publishing Status":
        await status_command(update, context)
    elif text == "⚙️ Settings":
        await settings_command(update, context)
