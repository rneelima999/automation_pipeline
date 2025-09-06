# import json, yaml, os, time, logging
# from pathlib import Path
# from typing import Dict, Any, List
# from pydantic import BaseModel, Field
# from .image_provider import ImageProvider
# from .localization import Localizer
# from .compliance import Compliance
# from .renderer import Renderer
# from .utils import ensure_dir, timestamp, write_json

# ASPECT_RATIOS = {
#     "1x1":   (1080, 1080),
#     "9x16":  (1080, 1920),
#     "16x9":  (1920, 1080),
# }

# class Product(BaseModel):
#     sku: str
#     name: str

# class Brief(BaseModel):
#     campaign_id: str
#     target_region: str
#     audience: str
#     message_en: str
#     products: List[Product]
#     regions: List[str] = Field(default_factory=lambda: ["US"])

# def load_structured(path: str) -> Dict[str, Any]:
#     with open(path, "r", encoding="utf-8") as f:
#         if path.endswith((".yml", ".yaml")):
#             return yaml.safe_load(f)
#         return json.load(f)

# def run_pipeline(
#     brief_path: str,
#     brand_path: str,
#     assets_dir: str,
#     out_dir: str,
#     project_id: str | None,
#     location: str,
#     use_vertex: bool,
# ):
#     # logging
#     os.makedirs("logs", exist_ok=True)
#     logging.basicConfig(
#         filename=f"logs/{Path(brief_path).stem}_{timestamp()}.log",
#         level=logging.INFO,
#         format="%(asctime)s [%(levelname)s] %(message)s",
#     )
#     logging.info("Starting pipeline")

#     brief = Brief(**load_structured(brief_path))
#     brand = load_structured(brand_path)

#     # services
#     localizer = Localizer("config/locales.json")
#     compliance = Compliance("config/banned_words.json", brand)
#     renderer = Renderer(brand)
#     provider = ImageProvider(
#         assets_dir=assets_dir, project_id=project_id, location=location, use_vertex=use_vertex
#     )

#     run_meta = {
#         "campaign_id": brief.campaign_id,
#         "regions": brief.regions,
#         "products": [p.model_dump() for p in brief.products],
#         "started_at": timestamp(),
#         "generated_assets": [],
#         "reused_assets": [],
#         "outputs": [],
#         "compliance": [],
#         "legal_flags": [],
#         "errors": []
#     }

#     for region in brief.regions:
#         loc = localizer.for_region(region, default_message=brief.message_en)
#         region_msg = loc["message"]
#         font_path = loc.get("font")
#         logging.info(f"Region {region} => message: {region_msg}")

#         for prod in brief.products:
#             # 1) get or generate hero
#             hero_path, from_cache = provider.get_or_generate_hero(prod.sku, prod.name, region)
#             (run_meta["reused_assets"] if from_cache else run_meta["generated_assets"]).append({
#                 "region": region, "sku": prod.sku, "path": hero_path
#             })

#             # 2) render creatives for each aspect ratio
#             for key, (W, H) in ASPECT_RATIOS.items():
#                 out_dir_final = Path(out_dir) / brief.campaign_id / prod.sku / region / key
#                 ensure_dir(out_dir_final)

#                 final_path = out_dir_final / "final.png"
#                 meta_path  = out_dir_final / "meta.json"

#                 try:
#                     renderer.compose_banner_plus_image(
#                         canvas_w=W, canvas_h=H,
#                         message=region_msg,
#                         hero_path=hero_path,
#                         font_path=font_path,
#                         out_path=final_path,
#                     )
#                     # 3) compliance & legal checks
#                     comp = compliance.run_checks(
#                         final_path=str(final_path),
#                         message=region_msg,
#                         logo_expected=True
#                     )

#                     write_json(meta_path, {
#                         "campaign_id": brief.campaign_id,
#                         "region": region,
#                         "product": prod.model_dump(),
#                         "ratio": key,
#                         "message": region_msg,
#                         "final_path": str(final_path),
#                         "compliance": comp
#                     })

#                     run_meta["outputs"].append(str(final_path))
#                     if comp.get("legal_flags"):
#                         run_meta["legal_flags"].append({
#                             "region": region, "ratio": key, "flags": comp["legal_flags"]
#                         })
#                     run_meta["compliance"].append({ "region": region, "ratio": key, **comp })

#                 except Exception as e:
#                     logging.exception("Render/compliance failed")
#                     run_meta["errors"].append({"region": region, "product": prod.sku, "ratio": key, "error": str(e)})

#     # 4) write run report
#     report_path = Path(out_dir) / brief.campaign_id / "run_report.json"
#     run_meta["finished_at"] = timestamp()
#     write_json(report_path, run_meta)
#     logging.info(f"Wrote report: {report_path}")





import json, yaml, os, time, logging
from pathlib import Path
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from .image_provider import ImageProvider
from .localization import Localizer
from .compliance import Compliance
from .renderer import Renderer
from .storage import PublicSiteStorage
from .utils import ensure_dir, timestamp, write_json

ASPECT_RATIOS = {
    "1x1":   (1080, 1080),
    "9x16":  (1080, 1920),
    "16x9":  (1920, 1080),
}

class Product(BaseModel):
    sku: str
    name: str

class Brief(BaseModel):
    campaign_id: str
    target_region: str
    audience: str
    message_en: str
    products: List[Product]
    regions: List[str] = Field(default_factory=lambda: ["US"])

def load_structured(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith((".yml", ".yaml")):
            return yaml.safe_load(f)
        return json.load(f)

def run_pipeline(
    brief_path: str,
    brand_path: str,
    assets_dir: str,
    out_dir: str,
    project_id: str | None,
    location: str,
    use_vertex: bool,
):
    # logging
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        filename=f"logs/{Path(brief_path).stem}_{timestamp()}.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Starting pipeline")

    brief = Brief(**load_structured(brief_path))
    brand = load_structured(brand_path)

    # services
    localizer = Localizer("config/locales.json")
    compliance = Compliance("config/banned_words.json", brand)
    renderer = Renderer(brand)
    provider = ImageProvider(
        assets_dir=assets_dir, project_id=project_id, location=location, use_vertex=use_vertex
    )
    public_storage = PublicSiteStorage(site_root="site")

    run_meta = {
        "campaign_id": brief.campaign_id,
        "regions": brief.regions,
        "products": [p.model_dump() for p in brief.products],
        "started_at": timestamp(),
        "generated_assets": [],
        "reused_assets": [],
        "outputs": [],
        "compliance": [],
        "legal_flags": [],
        "errors": []
    }

    for region in brief.regions:
        loc = localizer.for_region(region, default_message=brief.message_en)
        region_msg = loc["message"]
        font_path = loc.get("font")
        logging.info(f"Region {region} => message: {region_msg}")

        for prod in brief.products:
            # 1) get or generate hero
            hero_path, from_cache = provider.get_or_generate_hero(prod.sku, prod.name, region)
            (run_meta["reused_assets"] if from_cache else run_meta["generated_assets"]).append({
                "region": region, "sku": prod.sku, "path": hero_path
            })

            # 2) render creatives for each aspect ratio
            for key, (W, H) in ASPECT_RATIOS.items():
                out_dir_final = Path(out_dir) / brief.campaign_id / prod.sku / region / key
                ensure_dir(out_dir_final)

                final_path = out_dir_final / "final.png"
                meta_path  = out_dir_final / "meta.json"

                try:
                    renderer.compose_banner_plus_image(
                        canvas_w=W, canvas_h=H,
                        message=region_msg,
                        hero_path=hero_path,
                        font_path=font_path,
                        out_path=final_path,
                    )
                    # 3) compliance & legal checks
                    comp = compliance.run_checks(
                        final_path=str(final_path),
                        message=region_msg,
                        logo_expected=True
                    )

                    meta_obj = {
                        "campaign_id": brief.campaign_id,
                        "region": region,
                        "product": prod.model_dump(),
                        "ratio": key,
                        "message": region_msg,
                        "final_path": str(final_path),
                        "compliance": comp
                    }
                    write_json(meta_path, meta_obj)

                    run_meta["outputs"].append(str(final_path))
                    if comp.get("legal_flags"):
                        run_meta["legal_flags"].append({
                            "region": region, "ratio": key, "flags": comp["legal_flags"]
                        })
                    run_meta["compliance"].append({ "region": region, "ratio": key, **comp })

                    # 4) mirror into static site for keyless sharing
                    public_storage.add_asset(
                        campaign_id=brief.campaign_id,
                        sku=prod.sku,
                        region=region,
                        ratio=key,
                        final_path=str(final_path),
                        meta=meta_obj
                    )

                except Exception as e:
                    logging.exception("Render/compliance failed")
                    run_meta["errors"].append({"region": region, "product": prod.sku, "ratio": key, "error": str(e)})

    # write run report
    report_path = Path(out_dir) / brief.campaign_id / "run_report.json"
    run_meta["finished_at"] = timestamp()
    write_json(report_path, run_meta)
    logging.info(f"Wrote report: {report_path}")

    # write static site indexes
    public_storage.finalize(brief.campaign_id)
