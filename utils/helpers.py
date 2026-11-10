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


_hb_cache: Dict[str, Any] = {}


def _get_harfbuzz_renderer():
    """
    Returns cached FreeType and HarfBuzz objects for native Indic/Bengali complex text shaping.
    """
    if "ft_face" in _hb_cache and "hb_font" in _hb_cache:
        return _hb_cache["ft_face"], _hb_cache["hb_font"]

    import os
    import freetype
    import uharfbuzz as hb

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    font_path = os.path.join(project_root, "assets", "fonts", "HindSiliguri-Bold.ttf")
    if not os.path.exists(font_path):
        font_path = os.path.join("assets", "fonts", "HindSiliguri-Bold.ttf")

    with open(font_path, "rb") as f:
        font_bytes = f.read()

    hb_face = hb.Face(font_bytes)
    hb_font = hb.Font(hb_face)
    ft_face = freetype.Face(font_path)

    _hb_cache["ft_face"] = ft_face
    _hb_cache["hb_font"] = hb_font
    return ft_face, hb_font


def _shape_and_draw_text(
    target_img,
    text: str,
    font_size: int,
    color: tuple,
    center_x: int,
    center_y: int,
    max_w: int = 880,
    line_spacing_ratio: float = 1.45
):
    import re
    import numpy as np
    from PIL import Image
    import freetype
    import uharfbuzz as hb

    ft_face, hb_font = _get_harfbuzz_renderer()

    # Strip emoji characters that lack glyphs in the Bengali TTF
    emoji_pattern = re.compile(
        r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]",
        flags=re.UNICODE
    )
    clean_text = emoji_pattern.sub("", text).strip()

    def shape_single_line(line_str: str):
        ft_face.set_char_size(font_size * 64)
        hb_font.scale = (font_size * 64, font_size * 64)
        buf = hb.Buffer()
        buf.add_str(line_str)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf)
        line_width = sum(pos.x_advance / 64.0 for pos in buf.glyph_positions)
        return line_width, buf.glyph_infos, buf.glyph_positions

    # Split paragraphs and word-wrap using exact HarfBuzz pixel measurements
    paragraphs = clean_text.split("\n")
    wrapped_lines = []
    for para in paragraphs:
        words = para.strip().split()
        if not words:
            wrapped_lines.append("")
            continue
        cur_line = []
        for word in words:
            candidate = " ".join(cur_line + [word])
            w, _, _ = shape_single_line(candidate)
            if w <= max_w:
                cur_line.append(word)
            else:
                if cur_line:
                    wrapped_lines.append(" ".join(cur_line))
                    cur_line = [word]
                else:
                    wrapped_lines.append(word)
                    cur_line = []
        if cur_line:
            wrapped_lines.append(" ".join(cur_line))

    wrapped_lines = wrapped_lines[:16]
    line_h = int(font_size * line_spacing_ratio)
    total_text_h = len(wrapped_lines) * line_h
    start_y = int(center_y - (total_text_h / 2.0))

    img_w, img_h = target_img.size
    alpha_layer = np.zeros((img_h, img_w), dtype=np.uint8)

    ft_face.set_char_size(font_size * 64)
    hb_font.scale = (font_size * 64, font_size * 64)

    for idx, line in enumerate(wrapped_lines):
        if not line:
            continue
        line_w, infos, positions = shape_single_line(line)
        pen_x = (img_w - line_w) / 2.0
        pen_y = start_y + (idx * line_h) + int(font_size * 0.9)

        for info, pos in zip(infos, positions):
            ft_face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
            slot = ft_face.glyph
            bitmap = slot.bitmap

            if bitmap.width > 0 and bitmap.rows > 0:
                x = int(pen_x + (pos.x_offset / 64.0) + slot.bitmap_left)
                y = int(pen_y - (pos.y_offset / 64.0) - slot.bitmap_top)

                bm_arr = np.array(bitmap.buffer, dtype=np.uint8).reshape((bitmap.rows, bitmap.width))
                h_b, w_b = bm_arr.shape
                y1, y2 = max(0, y), min(img_h, y + h_b)
                x1, x2 = max(0, x), min(img_w, x + w_b)
                bw_y1, bw_y2 = max(0, -y), h_b - max(0, (y + h_b) - img_h)
                bw_x1, bw_x2 = max(0, -x), w_b - max(0, (x + w_b) - img_w)

                if y2 > y1 and x2 > x1 and bw_y2 > bw_y1 and bw_x2 > bw_x1:
                    alpha_layer[y1:y2, x1:x2] = np.maximum(
                        alpha_layer[y1:y2, x1:x2],
                        bm_arr[bw_y1:bw_y2, bw_x1:bw_x2]
                    )

            pen_x += pos.x_advance / 64.0
            pen_y += pos.y_advance / 64.0

    color_layer = Image.new("RGB", (img_w, img_h), color)
    mask = Image.fromarray(alpha_layer, mode="L")
    target_img.paste(color_layer, (0, 0), mask)


def create_story_image_from_text(text: str) -> Optional[bytes]:
    """
    Renders text into a 1080x1920 (9:16 vertical ratio) JPEG image
    suitable for publishing as a Facebook Page Story.
    Uses HarfBuzz + FreeType for 100% correct Bengali conjuncts (যুক্তবর্ণ) and vowels (কার).
    """
    if not text:
        return None

    try:
        import io
        import random
        from PIL import Image, ImageDraw

        width, height = 1080, 1920

        # Elegant color themes for stories
        themes = [
            {
                "top": (15, 23, 42),
                "bottom": (30, 41, 59),
                "accent": (56, 189, 248),
                "badge_bg": (30, 41, 59),
                "subtext": (148, 163, 184)
            },
            {
                "top": (24, 15, 45),
                "bottom": (45, 25, 75),
                "accent": (167, 139, 250),
                "badge_bg": (45, 25, 75),
                "subtext": (196, 181, 253)
            },
            {
                "top": (6, 35, 28),
                "bottom": (15, 55, 45),
                "accent": (52, 211, 153),
                "badge_bg": (15, 55, 45),
                "subtext": (167, 243, 208)
            },
            {
                "top": (45, 10, 20),
                "bottom": (70, 20, 35),
                "accent": (251, 113, 133),
                "badge_bg": (70, 20, 35),
                "subtext": (253, 164, 175)
            },
            {
                "top": (28, 25, 23),
                "bottom": (45, 40, 35),
                "accent": (251, 191, 36),
                "badge_bg": (45, 40, 35),
                "subtext": (252, 211, 77)
            }
        ]
        theme = random.choice(themes)

        # Smooth vertical gradient background
        base = Image.new("RGB", (1, 2))
        base.putpixel((0, 0), theme["top"])
        base.putpixel((0, 1), theme["bottom"])
        img = base.resize((width, height), Image.Resampling.BILINEAR)
        draw = ImageDraw.Draw(img)

        # Decorative outer border
        draw.rounded_rectangle([45, 70, width - 45, height - 70], radius=40, outline=theme["accent"], width=5)

        # Header Badge
        bw, bh = 620, 90
        bx, by = (width - bw) // 2, 140
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=26, fill=theme["badge_bg"], outline=theme["accent"], width=2)
        _shape_and_draw_text(
            img,
            text="SOT ADMISSION NEWS",
            font_size=46,
            color=theme["accent"],
            center_x=width // 2,
            center_y=by + bh // 2,
            max_w=bw - 20
        )

        # Dynamic typography based on text length (larger, punchier fonts)
        clean_text = text.strip()
        length = len(clean_text)
        if length <= 100:
            body_size = 72
            max_text_w = 930
            spacing_ratio = 1.50
        elif length <= 220:
            body_size = 62
            max_text_w = 920
            spacing_ratio = 1.45
        elif length <= 350:
            body_size = 52
            max_text_w = 900
            spacing_ratio = 1.40
        else:
            body_size = 44
            max_text_w = 880
            spacing_ratio = 1.35

        # Draw HarfBuzz-shaped Bengali body text
        _shape_and_draw_text(
            img,
            text=clean_text,
            font_size=body_size,
            color=(255, 255, 255),
            center_x=width // 2,
            center_y=height // 2,
            max_w=max_text_w,
            line_spacing_ratio=spacing_ratio
        )

        # Footer
        draw.line([width // 2 - 160, height - 210, width // 2 + 160, height - 210], fill=theme["accent"], width=2)
        page_ref = Config.FACEBOOK_PAGE_ID or "page"
        _shape_and_draw_text(
            img,
            text=f"facebook.com/{page_ref}",
            font_size=38,
            color=theme["subtext"],
            center_x=width // 2,
            center_y=height - 160,
            max_w=750
        )

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue()

    except Exception as e:
        return None
