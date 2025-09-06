from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

class Renderer:
    def __init__(self, brand: dict):
        self.brand = brand
        self.banner_bg = brand.get("banner_bg", "#FFFFFF")
        self.primary = brand.get("primary_color", "#000000")
        self.text_color = brand.get("text_color", "#000000")
        self.logo_path = brand["logo_path"]
        self.safe = int(brand.get("safe_margins_px", 24))

    def _pick_font(self, candidate_paths, size):
        for p in candidate_paths:
            if p and os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size=size)
                except Exception:
                    pass
        # system fallbacks
        for p in [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size=size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def compose_banner_plus_image(self, canvas_w: int, canvas_h: int, message: str,
                                  hero_path: str, font_path: str | None, out_path: Path):
        # Smaller, ratio-aware banner
        if canvas_h > canvas_w:   # tall (9x16)
            banner_ratio = 0.12
        elif canvas_h == canvas_w:  # square (1x1)
            banner_ratio = 0.14
        else:                      # wide (16x9)
            banner_ratio = 0.10
        banner_h = max(80, int(canvas_h * banner_ratio))  # never too tiny
        img_area_h = canvas_h - banner_h

        canvas = Image.new("RGB", (canvas_w, canvas_h), self.banner_bg)
        draw = ImageDraw.Draw(canvas)

        # --- logo (scale to banner height - padding) ---
        logo_w = 0
        logo_img = None
        if os.path.exists(self.logo_path):
            logo_img = Image.open(self.logo_path).convert("RGBA")
            scale = (banner_h - self.safe) / logo_img.height
            nw, nh = int(logo_img.width * scale), int(logo_img.height * scale)
            logo_img = logo_img.resize((nw, nh), Image.LANCZOS)
            logo_w = nw

        # --- font autosize to fit available width ---
        avail_w = canvas_w - (self.safe*3 + logo_w)  # left margin + gap + logo block + right margin
        desired = int(banner_h * 0.45)               # start size a bit smaller than banner height
        min_size = max(14, int(banner_h * 0.22))
        current_size = desired
        font = self._pick_font([font_path, "assets/fonts/NotoSans-Regular.ttf"], current_size)
        # shrink until it fits width
        while draw.textlength(message, font=font) > avail_w and current_size > min_size:
            current_size -= 2
            font = self._pick_font([font_path, "assets/fonts/NotoSans-Regular.ttf"], current_size)

        # --- draw message ---
        msg_x = self.safe
        # center vertically within banner
        ascent, descent = font.getmetrics() if hasattr(font, "getmetrics") else (current_size, 0)
        msg_h = ascent + descent + int(current_size*0.15)
        msg_y = max(0, (banner_h - msg_h)//2)
        draw.text((msg_x, msg_y), message, fill=self.text_color, font=font)

        # --- paste logo on top-right ---
        if logo_img:
            canvas.paste(logo_img, (canvas_w - logo_w - self.safe, (banner_h - logo_img.height)//2), logo_img)

        # --- main image (keep whole product visible for tall; cover for others) ---
        hero = Image.open(hero_path).convert("RGB")
        if canvas_h > canvas_w:
            hero_fitted = self._fit_contain(hero, (canvas_w, img_area_h), bg="#FFFFFF")
        else:
            hero_fitted = self._fit_cover(hero, (canvas_w, img_area_h))
        canvas.paste(hero_fitted, (0, banner_h))

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, format="PNG")

    def _fit_cover(self, img: Image.Image, target_size: tuple[int, int]) -> Image.Image:
        tw, th = target_size
        iw, ih = img.size
        scale = max(tw/iw, th/ih)
        nw, nh = int(iw*scale), int(ih*scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - tw)//2
        top  = (nh - th)//2
        return img.crop((left, top, left+tw, top+th))

    def _fit_contain(self, img: Image.Image, target_size: tuple[int, int], bg="#FFFFFF") -> Image.Image:
        tw, th = target_size
        iw, ih = img.size
        scale = min(tw/iw, th/ih)
        nw, nh = int(iw*scale), int(ih*scale)
        img_resized = img.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGB", (tw, th), bg)
        canvas.paste(img_resized, ((tw - nw)//2, (th - nh)//2))
        return canvas
