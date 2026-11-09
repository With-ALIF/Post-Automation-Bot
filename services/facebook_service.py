import logging
import random
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config
from utils.helpers import sanitize_text

logger = logging.getLogger(__name__)

# Curated Facebook background presets:
# Black, Solid Red, Sunset Orange, Light Yellow, Indigo/Purple, Deep Blue, Warm Gradient
PRESET_COLOR_PALETTES = [
    "1881421442117417",  # Solid Black
    "1903718606535395",  # Solid Red
    "901751159967576",   # Sunset Orange
    "862667370603267",   # Light Yellow
    "106018623298955",   # Indigo / Purple
    "319468561816672",   # Deep Indigo / Blue
    "303063890126415",   # Yellow-Orange Gradient
]


class FacebookService:
    def __init__(self):
        self.session = self._create_resilient_session()
        self._cached_page_token = None

    def get_effective_page_token(self) -> str:
        """
        If the configured token is a User Access Token, automatically resolve
        it to the specific Page Access Token for Config.FACEBOOK_PAGE_ID.
        If it's already a Page Access Token, use it directly.
        """
        if self._cached_page_token:
            return self._cached_page_token

        base_token = Config.FACEBOOK_PAGE_ACCESS_TOKEN
        if not base_token or not Config.FACEBOOK_PAGE_ID:
            return base_token

        try:
            # 1. Direct query to /{page_id}?fields=access_token
            url = f"{self.base_url}/{Config.FACEBOOK_PAGE_ID}"
            res = self.session.get(
                url,
                params={"fields": "access_token,name", "access_token": base_token},
                timeout=12
            )
            data = res.json()
            if res.status_code == 200 and "access_token" in data:
                self._cached_page_token = data["access_token"]
                logger.info("Successfully auto-resolved Page Access Token for %s", data.get("name", Config.FACEBOOK_PAGE_ID))
                return self._cached_page_token

            # 2. Query /me/accounts
            accounts_url = f"{self.base_url}/me/accounts"
            res2 = self.session.get(
                accounts_url,
                params={"access_token": base_token},
                timeout=12
            )
            data2 = res2.json()
            if res2.status_code == 200 and "data" in data2:
                for item in data2.get("data", []):
                    if str(item.get("id")) == str(Config.FACEBOOK_PAGE_ID):
                        token = item.get("access_token")
                        if token:
                            self._cached_page_token = token
                            logger.info("Successfully resolved Page Access Token from /me/accounts for %s", item.get("name"))
                            return self._cached_page_token
        except Exception as e:
            logger.warning("Could not auto-resolve Page Access Token: %s", sanitize_text(str(e)))

        return base_token

    @staticmethod
    def _create_resilient_session() -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    @property
    def base_url(self) -> str:
        version = Config.GRAPH_API_VERSION if Config.GRAPH_API_VERSION.startswith("v") else f"v{Config.GRAPH_API_VERSION}"
        return f"https://graph.facebook.com/{version}"

    def check_connection(self) -> Dict[str, Any]:
        if not Config.FACEBOOK_PAGE_ID or not Config.FACEBOOK_PAGE_ACCESS_TOKEN:
            return {
                "success": False,
                "error": "Facebook Page ID অথবা Access Token কনফিগার করা হয়নি (.env চেক করুন)।"
            }

        token = self.get_effective_page_token()
        url = f"{self.base_url}/{Config.FACEBOOK_PAGE_ID}"
        params = {
            "fields": "id,name,link,is_published",
            "access_token": token
        }

        try:
            response = self.session.get(url, params=params, timeout=15)
            data = response.json()

            if response.status_code == 200 and "id" in data:
                return {
                    "success": True,
                    "page_id": data.get("id"),
                    "page_name": data.get("name", "Unknown Page"),
                    "link": data.get("link", f"https://facebook.com/{data.get('id')}"),
                    "is_published": data.get("is_published", True)
                }

            error_msg = self._parse_error(data, response.status_code)
            return {"success": False, "error": error_msg}

        except requests.exceptions.RequestException as e:
            logger.error("Facebook API connection test error: %s", sanitize_text(str(e)))
            return {
                "success": False,
                "error": f"নেটওয়ার্ক সংযোগ ত্রুটি (Network Error): {sanitize_text(str(e))}"
            }

    def publish_text_post(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"success": False, "error": "পোস্টের জন্য কোনো টেক্সট দেওয়া হয়নি।"}

        clean_text = text.strip()
        token = self.get_effective_page_token()
        url = f"{self.base_url}/{Config.FACEBOOK_PAGE_ID}/feed"
        payload = {
            "message": clean_text,
            "access_token": token
        }

        # Apply colored background if enabled and text is within 130 characters limit
        if Config.ENABLE_TEXT_BACKGROUND and len(clean_text) <= 130:
            if Config.FB_TEXT_BACKGROUND_PRESET_ID.lower() in ("random", "", "true"):
                chosen_preset = random.choice(PRESET_COLOR_PALETTES)
            else:
                chosen_preset = Config.FB_TEXT_BACKGROUND_PRESET_ID
            payload["text_format_preset_id"] = chosen_preset

        try:
            response = self.session.post(url, data=payload, timeout=20)
            data = response.json()

            # Automatic fallback: if Facebook rejects the preset, retry without preset as plain text
            if response.status_code != 200 and "text_format_preset_id" in payload:
                logger.info("Background preset rejected, retrying as standard text post...")
                payload.pop("text_format_preset_id", None)
                response = self.session.post(url, data=payload, timeout=20)
                data = response.json()

            if response.status_code == 200 and "id" in data:
                post_id = data.get("id")
                return {
                    "success": True,
                    "post_id": post_id,
                    "post_url": self._generate_post_url(post_id)
                }

            self._cached_page_token = None
            error_msg = self._parse_error(data, response.status_code)
            return {"success": False, "error": error_msg}

        except requests.exceptions.RequestException as e:
            logger.error("Facebook publish text post error: %s", sanitize_text(str(e)))
            return {
                "success": False,
                "error": f"পোস্ট প্রকাশের সময় নেটওয়ার্ক ত্রুটি ঘটেছে: {sanitize_text(str(e))}"
            }

    def publish_photo_post(self, photo_bytes: bytes, caption: Optional[str] = None) -> Dict[str, Any]:
        if not photo_bytes:
            return {"success": False, "error": "কোনো ছবি পাওয়া যায়নি।"}

        token = self.get_effective_page_token()
        url = f"{self.base_url}/{Config.FACEBOOK_PAGE_ID}/photos"
        files = {
            "source": ("photo.jpg", photo_bytes, "image/jpeg")
        }
        data = {
            "access_token": token
        }
        if caption and caption.strip():
            data["message"] = caption.strip()
            data["caption"] = caption.strip()

        try:
            response = self.session.post(url, data=data, files=files, timeout=40)
            result = response.json()

            if response.status_code == 200 and ("id" in result or "post_id" in result):
                post_id = result.get("post_id") or result.get("id")
                return {
                    "success": True,
                    "post_id": post_id,
                    "photo_id": result.get("id"),
                    "post_url": self._generate_post_url(post_id)
                }

            self._cached_page_token = None
            error_msg = self._parse_error(result, response.status_code)
            return {"success": False, "error": error_msg}

        except requests.exceptions.RequestException as e:
            logger.error("Facebook publish photo post error: %s", sanitize_text(str(e)))
            return {
                "success": False,
                "error": f"ছবি আপলোড করার সময় নেটওয়ার্ক ত্রুটি ঘটেছে: {sanitize_text(str(e))}"
            }

    def _generate_post_url(self, post_id: str) -> str:
        if not post_id:
            return f"https://facebook.com/{Config.FACEBOOK_PAGE_ID}"
        if "_" in post_id:
            page_id, story_id = post_id.split("_", 1)
            return f"https://www.facebook.com/{page_id}/posts/{story_id}"
        return f"https://www.facebook.com/{post_id}"

    def _parse_error(self, response_data: dict, status_code: int) -> str:
        error_info = response_data.get("error", {})
        fb_message = error_info.get("message", "অজানা ফেসবুক ত্রুটি (Unknown API error)")
        fb_code = error_info.get("code")

        safe_message = sanitize_text(fb_message)

        if fb_code == 190:
            return (
                f"⚠️ ফেসবুক Access Token মেয়াদোত্তীর্ণ বা অকার্যকর (Invalid/Expired Token).\n"
                f"কোড: 190 | বার্তা: {safe_message}\n"
                f"পরামর্শ: নতুন Page Access Token তৈরি করে .env ফাইলে আপডেট করুন।"
            )
        elif fb_code == 200:
            return (
                f"⚠️ অনুমতির ঘাটতি (Permissions Missing).\n"
                f"বার্তা: {safe_message}\n"
                f"পরামর্শ: টোকেনে 'pages_manage_posts' এবং 'pages_read_engagement' পারমিশন নিশ্চিত করুন।"
            )
        elif fb_code == 100:
            return (
                f"⚠️ ভুল প্যারামিটার (Invalid Parameter).\n"
                f"বার্তা: {safe_message}"
            )
        elif fb_code == 368:
            return (
                f"⚠️ ফেসবুক অ্যাকাউন্ট সাময়িক ব্লক বা সীমাবদ্ধ করা হয়েছে (Temporarily Restricted).\n"
                f"বার্তা: {safe_message}"
            )

        return f"ফেসবুক API ত্রুটি (HTTP {status_code}, কোড {fb_code}): {safe_message}"


facebook_service = FacebookService()
