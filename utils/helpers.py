import time
import hashlib
from typing import Dict, Any, Optional
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from config import Config


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    sanitized = str(text)

    if Config.FACEBOOK_PAGE_ACCESS_TOKEN and len(Config.FACEBOOK_PAGE_ACCESS_TOKEN) > 6:
        sanitized = sanitized.replace(Config.FACEBOOK_PAGE_ACCESS_TOKEN, "[REDACTED_FB_TOKEN]")

    if Config.TELEGRAM_BOT_TOKEN and len(Config.TELEGRAM_BOT_TOKEN) > 6:
        sanitized = sanitized.replace(Config.TELEGRAM_BOT_TOKEN, "[REDACTED_TG_TOKEN]")

    return sanitized


class DuplicateManager:
    def __init__(self, ttl_seconds: int = 60):
        self.ttl = ttl_seconds
        self._published_history: Dict[str, float] = {}
        self._in_flight: set[str] = set()

    def is_in_flight(self, draft_id: str) -> bool:
        return draft_id in self._in_flight

    def set_in_flight(self, draft_id: str) -> bool:
        self._cleanup()
        if draft_id in self._in_flight or draft_id in self._published_history:
            return False
        self._in_flight.add(draft_id)
        return True

    def mark_completed(self, draft_id: str):
        self._in_flight.discard(draft_id)
        self._published_history[draft_id] = time.time()

    def release(self, draft_id: str):
        self._in_flight.discard(draft_id)

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self._published_history.items() if now - v > self.ttl]
        for k in expired:
            del self._published_history[k]


duplicate_manager = DuplicateManager(ttl_seconds=120)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton("📝 Create Text Post"),
            KeyboardButton("🖼 Create Image Post")
        ],
        [
            KeyboardButton("📊 Publishing Status"),
            KeyboardButton("⚙️ Settings")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_preview_keyboard(draft_id: str, is_image: bool = False, has_caption: bool = True) -> InlineKeyboardMarkup:
    buttons = []

    buttons.append([
        InlineKeyboardButton("🚀 Publish Now", callback_data=f"pub:{draft_id}")
    ])

    if is_image:
        if has_caption:
            buttons.append([
                InlineKeyboardButton("✏️ Edit Caption", callback_data=f"caption:{draft_id}"),
                InlineKeyboardButton("🗑 Remove Caption", callback_data=f"rmcaption:{draft_id}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("➕ Add Caption", callback_data=f"caption:{draft_id}")
            ])

    buttons.append([
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{draft_id}")
    ])

    return InlineKeyboardMarkup(buttons)


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def create_story_image_from_text(text: str) -> Optional[bytes]:
    """
    Renders text into a 1080x1920 (9:16 vertical ratio) JPEG image
    suitable for publishing as a Facebook Page Story.
    """
    if not text:
        return None

    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        import textwrap

        width, height = 1080, 1920
        bg_color = (15, 23, 42)
        img = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Draw decorative card border
        draw.rectangle([40, 40, width - 40, height - 40], outline=(56, 189, 248), width=5)

        try:
            font_title = ImageFont.truetype("arial.ttf", 52)
            font_body = ImageFont.truetype("arial.ttf", 60)
            font_footer = ImageFont.truetype("arial.ttf", 38)
        except Exception:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
            font_footer = ImageFont.load_default()

        # Wrap text lines
        lines = []
        for line in text.split("\n"):
            wrapped = textwrap.wrap(line, width=28)
            if wrapped:
                lines.extend(wrapped)
            else:
                lines.append("")

        display_text = "\n".join(lines[:16])

        # Draw header, body text, and footer
        draw.text((width // 2, 220), "📢 SOT Admission News", font=font_title, fill=(56, 189, 248), anchor="mm")
        draw.multiline_text((width // 2, height // 2), display_text, font=font_body, fill=(255, 255, 255), anchor="mm", align="center", spacing=24)
        draw.text((width // 2, height - 180), "facebook.com/" + (Config.FACEBOOK_PAGE_ID or "page"), font=font_footer, fill=(148, 163, 184), anchor="mm")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception:
        return None
