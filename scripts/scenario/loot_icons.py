"""Validate and register the eleven generated spec 038 icons and build the review sheet."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .item_icons import ROOT, write_json


def main() -> None:
    from PIL import Image, ImageDraw, ImageFont

    catalog = ROOT / "assets/candidates/038/generation.json"
    entries = json.loads(catalog.read_text(encoding="utf-8"))
    qa = []
    for entry in entries:
        path = ROOT / entry["file"]
        with Image.open(path) as icon:
            if icon.size != (128, 128) or icon.mode != "RGBA" or icon.getchannel("A").getextrema() != (0, 255):
                raise ValueError(f"Invalid icon: {entry['file']}")
        qa.append(dict(file=entry["file"], bytes=path.stat().st_size, width=128, height=128, rgba=True))
    total = sum(p.stat().st_size for p in (ROOT / "client/images").glob("icon_*.png"))
    if total >= 2_000_000:
        raise ValueError(f"Icon budget exceeded: {total}")
    manifest_path = ROOT / "assets/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["images"] = [e for e in manifest["images"] if e.get("task") != "038"] + entries
    manifest["tasks"] = list(dict.fromkeys([*manifest.get("tasks", []), "038"]))
    manifest["batches"]["038"] = dict(task="038", generator="image_gen", approved=False,
        icon_count=len(entries), output_size=[128, 128], total_icon_bytes=total, qa=qa,
        prompts=catalog.relative_to(ROOT).as_posix(), sheet="eval/reports/screens/038/icons-sheet.png")
    write_json(manifest_path, manifest)
    sheet = Image.new("RGB", (1200, 80 + math.ceil(len(entries) / 6) * 180), "#171b26")
    draw = ImageDraw.Draw(sheet)
    font_path = Path(r"C:\Windows\Fonts\meiryo.ttc")
    font = ImageFont.truetype(str(font_path), 16)
    title = ImageFont.truetype(str(font_path), 25)
    draw.text((24, 20), "戦利品 — 038", font=title, fill="#eee6d5")
    for index, entry in enumerate(entries):
        x, y = index % 6 * 200, 80 + index // 6 * 180
        with Image.open(ROOT / entry["file"]) as icon:
            sheet.paste(icon, (x + 36, y), icon)
        name = entry["name"]
        draw.text((x + (200 - draw.textlength(name, font=font)) / 2, y + 134), name, font=font, fill="#eee6d5")
    output = ROOT / "eval/reports/screens/038/icons-sheet.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)
    print(f"{len(entries)} new icons; RGBA 128x128; all icon files {total} bytes; approved=false")


if __name__ == "__main__":
    main()
