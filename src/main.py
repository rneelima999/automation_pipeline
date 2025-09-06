import json, os, sys, time
from pathlib import Path
import typer
from rich import print
from .pipeline import run_pipeline

app = typer.Typer(help="Creative Automation POC")

@app.command()
def run(
    brief: str = typer.Option(..., help="Path to campaign brief JSON/YAML"),
    brand: str = typer.Option(..., help="Path to brand_config.json"),
    assets_dir: str = typer.Option("assets", help="Local assets root"),
    out_dir: str = typer.Option("outputs", help="Output root"),
    project_id: str = typer.Option(None, help="GCP project (Vertex AI)"),
    location: str = typer.Option("us-central1", help="Vertex location"),
    use_vertex: bool = typer.Option(True, help="Try Vertex AI; fallback if unavailable"),
):
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    try:
        run_pipeline(
            brief_path=brief,
            brand_path=brand,
            assets_dir=assets_dir,
            out_dir=out_dir,
            project_id=project_id or os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=location or os.getenv("VERTEX_LOCATION", "us-central1"),
            use_vertex=use_vertex,
        )
        print(f"[bold green]Done in {time.time()-t0:.1f}s[/bold green]")
    except Exception as e:
        print(f"[bold red]Pipeline failed:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    app()
