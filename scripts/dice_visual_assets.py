"""Offline spec 042 sprite sizing, WebP packaging and candidate registration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "assets/candidates/042/generation.json"


def describe(path: Path) -> dict[str, Any]:
    from PIL import Image

    with Image.open(path) as image:
        alpha = image.convert("RGBA").getchannel("A")
        return {
            "file": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
            "width": image.width, "height": image.height, "alpha_extrema": list(alpha.getextrema()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }


def main() -> None:
    # Pillow is optional tooling; neither the game nor default tests import it.
    from PIL import Image

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    registrations = []
    runtime = []
    for entry in catalog["images"]:
        source = ROOT / entry["original"]
        candidate = ROOT / entry["file"]
        size = (800, 400) if entry["id"] == "dice_tray" else (512, 512)
        with Image.open(source) as original:
            image = original.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        image.save(candidate, optimize=True)
        entry["artifacts"] = [describe(source), describe(candidate)]
        if entry.get("runtime"):
            target = ROOT / entry["runtime"]
            image.save(target, "WEBP", quality=88, method=6)
            info = describe(target)
            runtime.append(info)
            entry["artifacts"].append(info)
        for artifact in entry["artifacts"]:
            if artifact["alpha_extrema"] != [0, 255]:
                raise ValueError(f"Expected transparent background and opaque body: {artifact['file']}")
            registrations.append({
                "id": entry["id"], "task": "042", "purpose": entry["purpose"],
                "prompt": entry["prompt"], "reference_images": entry["reference_images"],
                "generation_date": catalog["generation_date"], "generator": "image_gen",
                "approved": False, **artifact,
            })
    total = sum(item["bytes"] for item in runtime)
    if total >= 1_500_000:
        raise ValueError(f"Runtime sprite budget exceeded: {total}")
    catalog["runtime_bytes"] = total
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path = ROOT / "assets/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["images"] = [e for e in manifest["images"] if e.get("task") != "042"] + registrations
    if "042" not in manifest["tasks"]:
        manifest["tasks"].append("042")
    manifest.setdefault("batches", {})["042"] = {
        "approved": False, "runtime_bytes": total, "runtime_budget": 1_500_000,
        "default": "client/images/dice_bone.webp", "runtime": runtime,
        "prompts": CATALOG.relative_to(ROOT).as_posix(),
        "sheet": "eval/reports/screens/042/dice-sheet.png",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"10 candidates; 7 runtime sprites; {total} bytes; PNG originals preserved")


if __name__ == "__main__":
    main()
