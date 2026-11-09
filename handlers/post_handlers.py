import uuid
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from services.facebook_service import facebook_service
from services.channel_service import channel_service
from utils.auth import authorized_only
from utils.helpers import (
    duplicate_manager,
    get_preview_keyboard,
    get_main_keyboard,
    sanitize_text
)

logger = logging.getLogger(__name__)


async def _safely_edit_message(query, text: str, reply_markup=None):
    try:
        if query.message and query.message.photo:
            await query.edit_message_caption(
                caption=text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.warning("Message edit notice: %s", sanitize_text(str(e)))


@authorized_only
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.effective_message.text.strip()

    awaiting_caption_for = context.user_data.get("awaiting_caption_for")
    if awaiting_caption_for:
        drafts = context.user_data.get("drafts", {})
        draft = drafts.get(awaiting_caption_for)

        if draft and draft.get("type") == "photo":
            draft["caption"] = text
            del context.user_data["awaiting_caption_for"]

            preview_text = (
                "🖼 *ছবি পোস্ট প্রিভিউ (Photo Post Preview):*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 *ক্যাপশন:*\n{text}\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📍 *টার্গেট পেজ:* `{Config.FACEBOOK_PAGE_ID}`\n\n"
                "ক্যাপশন আপডেট হয়েছে! আপনি কি এই ছবিটি ফেসবুকে পোস্ট করতে চান?"
            )

            await update.effective_message.reply_text(
                "✅ *ক্যাপশন যুক্ত করা হয়েছে!*",
                parse_mode="Markdown"
            )

            await update.effective_message.reply_photo(
                photo=draft["file_id"],
                caption=preview_text,
                parse_mode="Markdown",
                reply_markup=get_preview_keyboard(awaiting_caption_for, is_image=True, has_caption=True)
            )
            return
        else:
            if "awaiting_caption_for" in context.user_data:
                del context.user_data["awaiting_caption_for"]

    if "awaiting_text_post" in context.user_data:
        del context.user_data["awaiting_text_post"]

    draft_id = uuid.uuid4().hex[:8]
    if "drafts" not in context.user_data:
        context.user_data["drafts"] = {}

    context.user_data["drafts"][draft_id] = {
        "type": "text",
        "text": text,
        "created_at": datetime.now().isoformat()
    }

    preview_text = (
        "📄 *পোস্ট প্রিভিউ (Facebook Post Preview):*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 *টার্গেট পেজ:* `{Config.FACEBOOK_PAGE_ID}`\n\n"
        "আপনি কি এই পোস্টটি আপনার ফেসবুক পেজে প্রকাশ করতে চান?"
    )

    await update.effective_message.reply_text(
        text=preview_text,
        parse_mode="Markdown",
        reply_markup=get_preview_keyboard(draft_id, is_image=False)
    )


@authorized_only
async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = update.effective_message.photo
    if not photos:
        return

    if "awaiting_image_post" in context.user_data:
        del context.user_data["awaiting_image_post"]

    highest_res_photo = photos[-1]
    file_id = highest_res_photo.file_id
    caption = update.effective_message.caption

    draft_id = uuid.uuid4().hex[:8]
    if "drafts" not in context.user_data:
        context.user_data["drafts"] = {}

    context.user_data["drafts"][draft_id] = {
        "type": "photo",
        "file_id": file_id,
        "caption": caption.strip() if caption else None,
        "created_at": datetime.now().isoformat()
    }

    has_caption = bool(caption and caption.strip())

    if has_caption:
        preview_text = (
            "🖼 *ছবি পোস্ট প্রিভিউ (Photo Post Preview):*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 *ক্যাপশন:*\n{caption.strip()}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *টার্গেট পেজ:* `{Config.FACEBOOK_PAGE_ID}`\n\n"
            "আপনি কি এই ছবিটি ক্যাপশনসহ ফেসবুক পেজে প্রকাশ করতে চান?"
        )
    else:
        preview_text = (
            "🖼 *ছবি পোস্ট প্রিভিউ (Photo Post Preview):*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📝 *ক্যাপশন:* _(কোনো ক্যাপশন নেই)_\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *টার্গেট পেজ:* `{Config.FACEBOOK_PAGE_ID}`\n\n"
            "ক্যাপশন ছাড়া সরাসরি পোস্ট করতে *Publish Now* চাপুন, "
            "অথবা ক্যাপশন লিখতে *Add Caption* চাপুন।"
        )

    await update.effective_message.reply_text(
        text=preview_text,
        parse_mode="Markdown",
        reply_markup=get_preview_keyboard(draft_id, is_image=True, has_caption=has_caption)
    )


@authorized_only
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    parts = data.split(":", 1)
    if len(parts) != 2:
        return

    action, draft_id = parts[0], parts[1]
    drafts = context.user_data.get("drafts", {})
    draft = drafts.get(draft_id)

    if action == "cancel":
        duplicate_manager.release(draft_id)
        if draft_id in drafts:
            del drafts[draft_id]

        await _safely_edit_message(
            query,
            "🚫 *পোস্টটি বাতিল করা হয়েছে।* (Post Cancelled)\n\n"
            "নতুন পোস্ট করতে চাইলে যেকোনো টেক্সট বা ছবি পাঠান।"
        )
        return

    if not draft:
        await _safely_edit_message(
            query,
            "⚠️ *এই ড্রাফটটির মেয়াদ শেষ হয়ে গেছে বা এটি খুঁজে পাওয়া যায়নি।*\n"
            "অনুগ্রহ করে নতুন করে টেক্সট বা ছবি পাঠান।"
        )
        return

    if action == "caption":
        context.user_data["awaiting_caption_for"] = draft_id
        await query.message.reply_text(
            "✏️ *ছবির জন্য ক্যাপশন লিখুন:*\n\n"
            "দয়া করে ছবিতে যে ক্যাপশনটি দিতে চান তা এখন লিখে পাঠান।\n"
            "_(বাতিল করতে চাইলে /cancel লিখুন)_",
            parse_mode="Markdown"
        )
        return

    if action == "rmcaption":
        draft["caption"] = None
        preview_text = (
            "🖼 *ছবি পোস্ট প্রিভিউ (Photo Post Preview):*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📝 *ক্যাপশন:* _(ক্যাপশন মুছে ফেলা হয়েছে)_\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *টার্গেট পেজ:* `{Config.FACEBOOK_PAGE_ID}`\n\n"
            "ক্যাপশন ছাড়া সরাসরি পোস্ট করতে *Publish Now* চাপুন।"
        )
        await _safely_edit_message(
            query,
            preview_text,
            reply_markup=get_preview_keyboard(draft_id, is_image=True, has_caption=False)
        )
        return

    if action == "pub":
        if not duplicate_manager.set_in_flight(draft_id):
            await query.answer(
                "⏳ এই পোস্টটি ইতিমধ্যে প্রসেস হচ্ছে অথবা প্রকাশিত হয়েছে।",
                show_alert=True
            )
            return

        await _safely_edit_message(
            query,
            "⏳ *ফেসবুক পেজে পোস্ট করা হচ্ছে...*\nঅনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন।"
        )

        post_type = draft.get("type")
        fb_result = None

        try:
            if post_type == "text":
                content = draft.get("text", "")
                fb_result = facebook_service.publish_text_post(content)

                if fb_result.get("success") and channel_service.is_enabled():
                    await channel_service.publish_text_to_channel(context.bot, content)

            elif post_type == "photo":
                file_id = draft.get("file_id")
                caption = draft.get("caption")

                tg_file = await context.bot.get_file(file_id)
                photo_bytes = await tg_file.download_as_bytearray()

                fb_result = facebook_service.publish_photo_post(
                    photo_bytes=bytes(photo_bytes),
                    caption=caption
                )

                if fb_result.get("success") and channel_service.is_enabled():
                    await channel_service.publish_photo_to_channel(
                        context.bot,
                        photo_file_id=file_id,
                        caption=caption
                    )

        except Exception as e:
            logger.error("Exception during publish execution: %s", sanitize_text(str(e)))
            fb_result = {
                "success": False,
                "error": f"সিস্টেম ত্রুটি: {sanitize_text(str(e))}"
            }

        if fb_result and fb_result.get("success"):
            duplicate_manager.mark_completed(draft_id)
            if draft_id in drafts:
                del drafts[draft_id]

            post_id = fb_result.get("post_id", "N/A")
            post_url = fb_result.get("post_url", f"https://facebook.com/{Config.FACEBOOK_PAGE_ID}")
            timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

            success_text = (
                "🎉 *ফেসবুক পেজে সফলভাবে পোস্ট প্রকাশিত হয়েছে!* (Published)\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *Post ID:* `{post_id}`\n"
                f"🔗 *পোস্ট লিংক:* [Facebook-এ দেখুন]({post_url})\n"
                f"🕒 *সময়:* `{timestamp}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "নতুন পোস্ট তৈরি করতে টেক্সট বা ছবি পাঠান।"
            )

            await _safely_edit_message(query, success_text)
            logger.info("Successfully published post ID %s to Facebook Page", post_id)

        else:
            duplicate_manager.release(draft_id)
            error_msg = fb_result.get("error", "অজানা ত্রুটি") if fb_result else "পোস্ট প্রক্রিয়া সম্পন্ন হতে পারেনি।"

            failure_text = (
                "❌ *ফেসবুকে পোস্ট প্রকাশ ব্যর্থ হয়েছে!* (Publish Failed)\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{error_msg}\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "আপনি কি পুনরায় চেষ্টা করতে চান?"
            )

            await _safely_edit_message(
                query,
                failure_text,
                reply_markup=get_preview_keyboard(
                    draft_id,
                    is_image=(post_type == "photo"),
                    has_caption=bool(draft.get("caption"))
                )
            )
            logger.warning("Facebook post failed for draft %s: %s", draft_id, error_msg)
