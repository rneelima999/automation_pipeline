import logging, os
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


class ImageProvider:
    """
    Provides hero images for products:
      - Reuse local asset if present
      - Else try Vertex AI Image Generation (robust to SDK signature changes)
      - Else generate a placeholder so the pipeline never blocks
    """

    def __init__(self, assets_dir: str, project_id: Optional[str], location: str, use_vertex: bool = True):
        self.assets_dir = Path(assets_dir)
        self.project_id = project_id
        self.location = location
        self.use_vertex = bool(use_vertex and project_id)

        self._vertex_model = None
        self._vertex_model_name = None

        if self.use_vertex:
            try:
                import vertexai
                from vertexai.preview.vision_models import ImageGenerationModel

                vertexai.init(project=self.project_id, location=self.location)

                # Try newest first, then older
                for name in ("imagegeneration@002", "imagegeneration@001"):
                    try:
                        self._vertex_model = ImageGenerationModel.from_pretrained(name)
                        self._vertex_model_name = name
                        logging.info(f"Vertex ImageGenerationModel ready ({name})")
                        break
                    except Exception as e:
                        logging.warning(f"Could not load {name}: {e}")

                if not self._vertex_model:
                    logging.warning("No Vertex image model loaded; will use placeholder fallback.")

            except Exception as e:
                logging.exception("Vertex init failed; will use placeholder fallback.")
                self._vertex_model = None
        else:
            logging.info("Vertex disabled or project_id missing; using placeholder generator.")

    # --------------------------- Public API ---------------------------

    def get_or_generate_hero(self, sku: str, product_name: str, region: str) -> tuple[str, bool]:
        """
        Returns (path_to_image, reused_boolean)
        """
        local_path = self.assets_dir / "products" / sku / "hero.png"
        if local_path.exists():
            logging.info(f"Reusing local hero: {local_path}")
            return str(local_path), True

        out_dir = self.assets_dir / "products" / sku
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "hero.png"

        if self._vertex_model:
            ok = self._generate_with_vertex(
                prompt=f"High-quality studio product photo of {product_name} on a clean background, "
                       f"modern fitness aesthetic, no people, region={region}",
                out_path=out_path
            )
            if ok:
                logging.info(f"Vertex generated hero: {out_path}")
                return str(out_path), False

        # Fallback so the pipeline always completes
        self._placeholder(product_name, out_path)
        logging.info(f"Placeholder hero created: {out_path}")
        return str(out_path), False

    # ------------------------ Vertex helpers -------------------------

    def _generate_with_vertex(self, prompt: str, out_path: Path) -> bool:
        """
        Try multiple SDK signatures. Return True if an image is saved.
        """
        model = self._vertex_model
        if not model:
            return False

        # Try several argument shapes (SDK varies across versions).
        attempts = [
            {"desc": "aspect_ratio", "kwargs": dict(prompt=prompt, number_of_images=1, aspect_ratio="1:1")},
            {"desc": "no_size_args", "kwargs": dict(prompt=prompt, number_of_images=1)},
            {"desc": "image_size",  "kwargs": dict(prompt=prompt, number_of_images=1, image_size="1024x1024")},
            {"desc": "size_legacy", "kwargs": dict(prompt=prompt, number_of_images=1, size="1024x1024")},
        ]

        last_err: Optional[Exception] = None
        for att in attempts:
            try:
                r = model.generate_images(**att["kwargs"])
                img = self._first_image_from_response(r)
                if img is None:
                    raise RuntimeError("Vertex returned no image data")

                # Normalize size to 1024x1024 for consistency
                img = img.convert("RGB").resize((1024, 1024), Image.LANCZOS)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(out_path, "PNG")
                logging.info(f"Vertex call ok via '{att['desc']}' using {self._vertex_model_name}")
                return True

            except TypeError as te:
                # Signature mismatch: try next form
                logging.warning(f"Vertex signature mismatch ({att['desc']}): {te}")
                last_err = te
            except Exception as e:
                logging.exception(f"Vertex generation attempt failed ({att['desc']})")
                last_err = e

        if last_err:
            logging.warning(f"All Vertex attempts failed; last error: {last_err}")
        return False

    def _first_image_from_response(self, r) -> Optional[Image.Image]:
        """
        Handle common response shapes across SDK versions.
        """
        try:
            # Newer SDKs: r.images is a list
            imgs = getattr(r, "images", None)
            if imgs:
                img0 = imgs[0]
            else:
                # Some return the image-like object directly
                img0 = r

            # Cases:
            #  - has image_bytes
            #  - has _pil_image
            #  - is bytes
            if hasattr(img0, "image_bytes"):
                return Image.open(BytesIO(img0.image_bytes))
            if hasattr(img0, "_pil_image"):
                return img0._pil_image
            if isinstance(img0, (bytes, bytearray)):
                return Image.open(BytesIO(img0))
        except Exception as e:
            logging.warning(f"Could not parse Vertex image response: {e}")

        return None

    # ------------------------ Placeholder gen ------------------------

    def _placeholder(self, product_name: str, out_path: Path, size=(1024, 1024)):
        img = Image.new("RGB", size)
        # Simple vertical gradient
        for y in range(size[1]):
            c = int(180 + 75 * y / size[1])
            for x in range(size[0]):
                img.putpixel((x, y), (c, max(c - 30, 0), max(c - 60, 0)))

        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("assets/fonts/NotoSans-Regular.ttf", 48)
        except Exception:
            font = ImageFont.load_default()

        text = product_name
        tw = draw.textlength(text, font=font)
        draw.text(((size[0] - tw) // 2, size[1] // 2 - 24), text, fill=(0, 0, 0), font=font)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "PNG")
