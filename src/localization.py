import json, os
from typing import Dict

class Localizer:
    def __init__(self, locales_path: str):
        with open(locales_path, "r", encoding="utf-8") as f:
            self.locales = json.load(f)

    def for_region(self, region: str, default_message: str) -> Dict:
        cfg = self.locales.get(region, {})
        if not cfg:
            return {"language": "en", "message": default_message, "font": None}
        msg = cfg.get("message") or default_message
        font = cfg.get("font")
        if font and not os.path.exists(font):
            # font missing; fallback to English text
            return {"language": "en", "message": default_message, "font": None}
        return {"language": cfg.get("language", "en"), "message": msg, "font": font}
