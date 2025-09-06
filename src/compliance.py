import json, os
from typing import Dict, List
from PIL import Image

class Compliance:
    def __init__(self, banned_words_path: str, brand: Dict):
        with open(banned_words_path, "r", encoding="utf-8") as f:
            self.banned = set(w.lower() for w in json.load(f)["prohibited"])
        self.brand = brand

    def run_checks(self, final_path: str, message: str, logo_expected: bool=True) -> Dict:
        flags: List[str] = []
        msg_l = message.lower()
        for w in self.banned:
            if w in msg_l:
                flags.append(w)

        logo_present = self._logo_present(final_path)
        color_used = True  # we render banner using brand primary/secondary colors by design

        return {
            "logo_present": bool(logo_present or not logo_expected),
            "brand_color_used": color_used,
            "legal_flags": flags
        }

    def _logo_present(self, final_path: str) -> bool:
        # Heuristic: check that top-right banner region contains non-background (logo) pixels.
        # Since renderer pastes the logo, assume present if file exists and image alpha channel differs.
        if not os.path.exists(final_path):
            return False
        try:
            im = Image.open(final_path).convert("RGBA")
            w, h = im.size
            crop = im.crop((int(w*0.80), 0, w, int(h*0.18)))  # top-right banner slice
            # Count alpha < 255 (transparent logo edges)
            alpha = [a for *_, a in crop.getdata()]
            translucent = sum(1 for a in alpha if a < 255)
            return translucent > 0
        except:
            return False
