# For PoC we store locally. This module is a stub where you'd add S3/Azure/Dropbox uploads.
# Keep the interface so you can swap backends without changing pipeline code.
# class Storage:
#     def __init__(self): ...




import json, shutil
from pathlib import Path
from typing import Dict, List


class PublicSiteStorage:
    """
    Writes final assets + meta into a static site folder (site/)
    and builds HTML index pages. Viewable via GitHub Pages (no keys for reviewers).
    """
    def __init__(self, site_root: str = "site"):
        self.root = Path(site_root)
        self.assets: List[Dict] = []
        # fixed subdir
        self.out_root = self.root / "outputs"
        self.out_root.mkdir(parents=True, exist_ok=True)

    def add_asset(
        self,
        campaign_id: str,
        sku: str,
        region: str,
        ratio: str,
        final_path: str,
        meta: Dict
    ):
        dest_dir = self.out_root / campaign_id / sku / region / ratio
        dest_dir.mkdir(parents=True, exist_ok=True)
        # copy final.png
        shutil.copy2(final_path, dest_dir / "final.png")
        # write meta.json (we pass it in to avoid re-reading)
        with open(dest_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        self.assets.append({
            "campaign_id": campaign_id,
            "sku": sku,
            "region": region,
            "ratio": ratio,
            "rel_path": f"outputs/{campaign_id}/{sku}/{region}/{ratio}/final.png",
            "meta_rel": f"outputs/{campaign_id}/{sku}/{region}/{ratio}/meta.json",
            "message": meta.get("message", "")
        })

    def finalize(self, campaign_id: str):
        # campaign index
        camp_dir = self.out_root / campaign_id
        camp_dir.mkdir(parents=True, exist_ok=True)

        # Root index of all campaigns
        self._write_root_index()

        # Campaign page
        camp_assets = [a for a in self.assets if a["campaign_id"] == campaign_id]
        self._write_campaign_index(campaign_id, camp_assets)

    # ----------------- helpers -----------------

    def _write_root_index(self):
        # list campaigns present in site/outputs/*
        campaigns = sorted({p.name for p in self.out_root.glob("*") if p.is_dir()})
        html = [
            "<!doctype html><html><head><meta charset='utf-8'>",
            "<title>Creative Automation — Campaigns</title>",
            "<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:24px;} ul{line-height:1.9}</style>",
            "</head><body>",
            "<h1>Campaigns</h1><ul>"
        ]
        for c in campaigns:
            html.append(f"<li><a href='outputs/{c}/index.html'>{c}</a></li>")
        html += ["</ul></body></html>"]
        (self.root / "index.html").write_text("\n".join(html), encoding="utf-8")

    def _write_campaign_index(self, campaign_id: str, assets: List[Dict]):
        # group by sku/region
        def key(a): return (a["sku"], a["region"], a["ratio"])
        assets_sorted = sorted(assets, key=key)

        css = """
        body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:24px;}
        .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;align-items:start}
        .card{border:1px solid #ddd;border-radius:12px;padding:12px}
        .meta{font-size:12px;color:#555;margin:6px 0 10px}
        img{width:100%;height:auto;border-radius:8px;display:block;background:#fafafa}
        code{background:#f5f5f5;padding:1px 4px;border-radius:4px}
        """

        html = [
            "<!doctype html><html><head><meta charset='utf-8'>",
            f"<title>{campaign_id} — Outputs</title>",
            f"<style>{css}</style>",
            "</head><body>",
            f"<h1>Outputs — {campaign_id}</h1>",
            "<p><a href='../../index.html'>&larr; Back to all campaigns</a></p>",
            "<div class='grid'>"
        ]

        for a in assets_sorted:
            html += [
                "<div class='card'>",
                f"<div class='meta'><b>SKU</b> {a['sku']} &nbsp; <b>Region</b> {a['region']} &nbsp; <b>Ratio</b> {a['ratio']}</div>",
                f"<img loading='lazy' src='../../{a['rel_path'].split('outputs/',1)[1]}' alt='creative'/>",
                f"<div class='meta'><b>Message:</b> {a['message']}</div>",
                f"<div class='meta'><a href='../../{a['meta_rel'].split('outputs/',1)[1]}'>meta.json</a></div>",
                "</div>"
            ]

        html += ["</div></body></html>"]
        (self.out_root / campaign_id / "index.html").write_text("\n".join(html), encoding="utf-8")
