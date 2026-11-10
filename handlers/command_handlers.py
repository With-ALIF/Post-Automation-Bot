import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from services.facebook_service import facebook_service
from services.channel_service import channel_service
from utils.auth import authorized_only
from utils.helpers import get_main_keyboard

logger = logging.getLogger(__name__)


@authorized_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user else "User"

    welcome_text = (
        f"👋 *স্বাগতম, {name}!* (Welcome)\n\n"
        "এটি আপনার *Telegram to Facebook Auto Publisher* বট।\n"
        "এই বটের মাধ্যমে আপনি টেলিগ্রাম থেকেই সরাসরি আপনার ফেসবুক পেজে "
        "টেক্সট ও ছবিসহ পোস্ট করতে পারবেন।\n\n"
        "📌 *কীভাবে ব্যবহার করবেন:*\n"
        "• সরাসরি যেকোনো টেক্সট মেসেজ পাঠালে পোস্টের প্রিভিউ তৈরি হবে।\n"
        "• যেকোনো ছবি (ক্যাপশনসহ বা ছাড়া) পাঠালে প্রিভিউ তৈরি হবে।\n"
        "• প্রিভিউতে *Publish* চাপলে সাথে সাথে পেজে পোস্ট হয়ে যাবে।\n\n"
        "নিচের মেনু বা কমান্ডগুলো ব্যবহার করতে পারেন:"
    )

    await update.effective_message.reply_text(
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *বট ব্যবহারের নির্দেশিকা (Help & Instructions)*\n\n"
        "🔹 *১. Text Post:*\n"
        "বটে সাধারণ টেক্সট মেসেজ পাঠান অথবা মেনু থেকে *📝 Create Text Post* চাপুন। "
        "এরপর প্রিভিউ দেখে *🚀 Publish Now* চাপলে তা ফেসবুক পেজে পোস্ট হবে।\n\n"
        "🔹 *২. Image + Caption Post:*\n"
        "বটে একটি ছবি পাঠান। ছবির সাথে ক্যাপশন থাকলে তা ফেসবুক পোস্টের ক্যাপশন হবে। "
        "ক্যাপশন ছাড়া পাঠালেও প্রিভিউ থেকে *➕ Add Caption* চেপে ক্যাপশন যোগ করতে পারবেন।\n\n"
        "🔹 *৩. প্রয়োজনীয় কমান্ডসমূহ:*\n"
        "• `/start` — ওয়েলকাম মেসেজ ও মেইন মেনু\n"
        "• `/help` — ব্যবহারের নির্দেশিকা\n"
        "• `/status` — ফেসবুক পেজ ও এপিআই কানেকশন স্ট্যাটাস\n"
        "• `/settings` — বটের বর্তমান কনফিগারেশন বিবরণ\n"
        "• `/comment <post_id> <মন্তব্য>` — ফেসবুক পোস্টে কমেন্ট করুন\n"
        "• `/cancel` — চলমান যেকোনো ড্রাফট বা ক্যাপশন বাতিল করুন\n\n"
        "⚠️ *নিরাপত্তা:* কেবল অনুমোদিত টেলিগ্রাম ইউজাররাই এই বট ব্যবহার করতে পারবেন।"
    )

    await update.effective_message.reply_text(
        text=help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


@authorized_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.effective_message.reply_text(
        "🔍 *ফেসবুক পেজ সংযোগ পরীক্ষা করা হচ্ছে...*\nঅনুগ্রহ করে অপেক্ষা করুন।",
        parse_mode="Markdown"
    )

    fb_result = facebook_service.check_connection()

    if fb_result.get("success"):
        page_name = fb_result.get("page_name", "N/A")
        page_id = fb_result.get("page_id", "N/A")
        page_link = fb_result.get("link", f"https://facebook.com/{page_id}")
        is_published = "হ্যাঁ (Published)" if fb_result.get("is_published") else "না (Unpublished)"
        channel_status = "সক্রিয় (Active)" if channel_service.is_enabled() else "নিষ্ক্রিয় (Disabled)"

        text = (
            "✅ *Facebook Connection Status: সফল (Connected)*\n\n"
            f"📄 *পেজের নাম:* {page_name}\n"
            f"🆔 *পেজ আইডি:* `{page_id}`\n"
            f"🌐 *পেজ লিংক:* [ভিজিট করুন]({page_link})\n"
            f"📢 *পেজ স্ট্যাটাস:* {is_published}\n"
            f"📡 *API ভার্সন:* `{Config.GRAPH_API_VERSION}`\n"
            f"📲 *Telegram Channel Auto Post:* {channel_status}\n\n"
            "বটটি এখন পোস্ট করার জন্য সম্পূর্ণ প্রস্তুত!"
        )
    else:
        err = fb_result.get("error", "অজানা ত্রুটি")
        text = (
            "❌ *Facebook Connection Status: ব্যর্থ (Failed)*\n\n"
            f"{err}\n\n"
            "দয়া করে আপনার `.env` ফাইলের `FACEBOOK_PAGE_ID` এবং "
            "`FACEBOOK_PAGE_ACCESS_TOKEN` পরীক্ষা করুন।"
        )

    await status_msg.edit_text(
        text=text,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


@authorized_only
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    summary = Config.get_summary()

    lines = ["⚙️ *Bot Configuration & Settings:*\n"]
    for key, value in summary.items():
        lines.append(f"• *{key}:* `{value}`")

    lines.append("\n_দ্রষ্টব্য: নিরাপত্তার স্বার্থে কোনো সিক্রেট টোকেন সম্পূর্ণ প্রকাশ করা হয় না।_")

    await update.effective_message.reply_text(
        text="\n".join(lines),
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


@authorized_only
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "awaiting_caption_for" in context.user_data:
        del context.user_data["awaiting_caption_for"]

    if "awaiting_text_post" in context.user_data:
        del context.user_data["awaiting_text_post"]

    if "awaiting_image_post" in context.user_data:
        del context.user_data["awaiting_image_post"]

    await update.effective_message.reply_text(
        "🚫 *চলমান প্রক্রিয়া বাতিল করা হয়েছে।* (Cancelled)\n\n"
        "নতুন পোস্ট তৈরি করতে টেক্সট বা ছবি পাঠান অথবা নিচের মেনু ব্যবহার করুন।",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


@authorized_only
async def comment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Format: /comment <post_id> <comment text>
    Also supports: /coment <post_id> <comment text>
    """
    args = context.args
    if not args or len(args) < 2:
        usage_text = (
            "💬 *ফেসবুক পোস্টে মন্তব্য করার নিয়ম (How to Comment):*\n\n"
            "ফরম্যাট:\n"
            "`/comment <post_id> <আপনার মন্তব্য>`\n\n"
            "📌 *উদাহরণ:*\n"
            "`/comment 646949765165078_123456 দারুণ একটি আপডেট!`\n\n"
            "_(টিপস: যেকোনো পোস্ট সফল হওয়ার পর যে Post ID টি পান, সেটি এখানে দিন)_"
        )
        await update.effective_message.reply_text(
            text=usage_text,
            parse_mode="Markdown"
        )
        return

    post_id = args[0].strip()
    comment_text = " ".join(args[1:]).strip()

    status_msg = await update.effective_message.reply_text(
        f"⏳ *Post ID:* `{post_id}`-এ মন্তব্য পোস্ট করা হচ্ছে...\nঅনুগ্রহ করে অপেক্ষা করুন।",
        parse_mode="Markdown"
    )

    result = facebook_service.post_comment(post_id=post_id, message=comment_text)

    if result.get("success"):
        comment_id = result.get("comment_id", "N/A")
        post_url = result.get("post_url", f"https://facebook.com/{post_id}")
        reply_success = (
            "💬 *ফেসবুক পোস্টে মন্তব্য সফলভাবে প্রকাশিত হয়েছে!* (Comment Added)\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Comment ID:* `{comment_id}`\n"
            f"📌 *Post ID:* `{post_id}`\n"
            f"🔗 *পোস্ট লিংক:* [Facebook-এ দেখুন]({post_url})\n"
            f"📝 *মন্তব্য:* {comment_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        try:
            await status_msg.edit_text(text=reply_success, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            await status_msg.edit_text(text=reply_success, disable_web_page_preview=True)
    else:
        err = result.get("error", "অজানা ত্রুটি")
        reply_fail = (
            "❌ *ফেসবুক পোস্টে মন্তব্য প্রকাশ ব্যর্থ হয়েছে!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *কারণ:* {err}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "দয়া করে Post ID এবং পেজের পারমিশন সঠিক আছে কি না নিশ্চিত করুন।"
        )
        try:
            await status_msg.edit_text(text=reply_fail, parse_mode="Markdown")
        except Exception:
            await status_msg.edit_text(text=reply_fail)
