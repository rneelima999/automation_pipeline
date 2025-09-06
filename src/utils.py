import json, os, datetime
from pathlib import Path

def ensure_dir(p: str | Path):
    Path(p).mkdir(parents=True, exist_ok=True)

def write_json(path: str | Path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def timestamp():
    return datetime.datetime.utcnow().isoformat() + "Z"
