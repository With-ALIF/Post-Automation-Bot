import os
from typing import Set
from dotenv import load_dotenv

load_dotenv()


class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    _raw_allowed_users: str = os.getenv("ALLOWED_USER_IDS", "").strip()
    ALLOWED_USER_IDS: Set[int] = set()
    if _raw_allowed_users:
        for uid in _raw_allowed_users.split(","):
            cleaned = uid.strip()
            if cleaned.isdigit():
                ALLOWED_USER_IDS.add(int(cleaned))
            elif cleaned.startswith("-") and cleaned[1:].isdigit():
                ALLOWED_USER_IDS.add(int(cleaned))

    FACEBOOK_PAGE_ID: str = os.getenv("FACEBOOK_PAGE_ID", "").strip()
    FACEBOOK_PAGE_ACCESS_TOKEN: str = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    GRAPH_API_VERSION: str = os.getenv("GRAPH_API_VERSION", "v21.0").strip()

    TELEGRAM_CHANNEL_ID: str = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
    AUTO_POST_TO_CHANNEL: bool = os.getenv("AUTO_POST_TO_CHANNEL", "false").strip().lower() in ("true", "1", "yes")

    @classmethod
    def validate(cls) -> list[str]:
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.ALLOWED_USER_IDS:
            missing.append("ALLOWED_USER_IDS")
        if not cls.FACEBOOK_PAGE_ID:
            missing.append("FACEBOOK_PAGE_ID")
        if not cls.FACEBOOK_PAGE_ACCESS_TOKEN:
            missing.append("FACEBOOK_PAGE_ACCESS_TOKEN")
        return missing

    @classmethod
    def mask_token(cls, token: str) -> str:
        if not token or len(token) < 8:
            return "***"
        return f"{token[:4]}...{token[-4:]}"

    @classmethod
    def get_summary(cls) -> dict:
        return {
            "Telegram Bot Token": cls.mask_token(cls.TELEGRAM_BOT_TOKEN),
            "Authorized Users Count": len(cls.ALLOWED_USER_IDS),
            "Facebook Page ID": cls.FACEBOOK_PAGE_ID if cls.FACEBOOK_PAGE_ID else "Not Set",
            "Facebook Token": cls.mask_token(cls.FACEBOOK_PAGE_ACCESS_TOKEN),
            "Graph API Version": cls.GRAPH_API_VERSION,
            "Telegram Channel ID": cls.TELEGRAM_CHANNEL_ID or "Disabled",
            "Auto Cross-Post to Channel": "Enabled" if cls.AUTO_POST_TO_CHANNEL else "Disabled"
        }
