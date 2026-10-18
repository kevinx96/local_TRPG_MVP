"""Register spec 041 candidates, install candidate 01, and assemble the review sheet."""
from __future__ import annotations

import json
import shutil

from PIL import Image, ImageDraw, ImageFont

from .risk_labels import ROOT


def main() -> None:
    entries = json.loads((ROOT / "assets/candidates/041/generation.json").read_text(encoding="utf-8"))
    if len(entries) != 7 or any(not (ROOT / entry["file"]).is_file() for entry in entries):
        raise ValueError("Expected six character candidates and one icon source")
    path = ROOT / "assets/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["images"] = [entry for entry in manifest["images"] if entry.get("task") != "041"] + entries
    manifest["selections"] = [entry for entry in manifest["selections"] if entry.get("task") != "041"]
    for entry in entries:
        icon = entry["id"].startswith("icon_")
        if not icon and not entry["file"].endswith("candidate_01.png"):
            continue
        target = f"client/images/{entry['id']}.png"
        if icon:
            with Image.open(ROOT / entry["file"]) as source:
                source.convert("RGBA").resize((128, 128), Image.Resampling.LANCZOS).save(ROOT / target, optimize=True)
        else:
            shutil.copyfile(ROOT / entry["file"], ROOT / target)
        manifest["images"].append({**entry, "file": target, "source_candidate": entry["file"], "preview_only": True})
        manifest["selections"].append(dict(task="041", id=entry["id"], file=target,
            candidates=[value["file"] for value in entries if value["id"] == entry["id"]],
            selected_candidate=entry["file"], approved=False,
            note="按 spec 安装候选 01；TODO(design): 最终选图由设计负责人决定。"))
    manifest["tasks"] = list(dict.fromkeys([*manifest.get("tasks", []), "041"]))
    manifest["batches"]["041"] = dict(task="041", generator="image_gen", generation_date="2026-10-19", approved=False,
        candidate_count=6, icon_count=1, preview_count=4,
        qa={"prompts": "assets/candidates/041/generation.json", "sheet": "eval/reports/screens/041/dragon-knight-sheet.png",
            "notes": "逐张检查；保留原生立绘与战斗图，图标按036缩为128×128。持枪、人脸、鳞甲细节及灰竜装饰待设计审定。"})
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sheet = Image.new("RGB", (1500, 1960), "#ddd8ce")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 26)
    small = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 20)
    draw.text((25, 16), "041 竜騎士ガレス — 全候補・未承認", fill="#222222", font=font)

    def tile(file: str, x: int, y: int, width: int, height: int, label: str) -> None:
        draw.rectangle((x, y, x + width, y + height), fill="#f7f5f0")
        with Image.open(ROOT / file) as source:
            preview = source.convert("RGBA")
            preview.thumbnail((width - 18, height - 48), Image.Resampling.LANCZOS)
            sheet.paste(preview, (x + (width - preview.width) // 2, y + 35 + (height - 45 - preview.height) // 2), preview)
        draw.text((x + 12, y + 6), label, fill="#222222", font=small)

    for row, identifier in enumerate(("npc_dragon_knight", "enemy_dragon_knight_mounted", "enemy_dragon_knight")):
        for col, number in enumerate(("01", "02")):
            tile(f"assets/candidates/041/{identifier}/candidate_{number}.png", 20 + col * 520, 70 + row * 620,
                 500, 600, f"{identifier} / {number}")
    tile("client/images/npc_walter.png", 1070, 70, 410, 500, "参考 npc_walter")
    tile("client/images/npc_robin.png", 1070, 600, 410, 500, "参考 npc_robin")
    tile("client/images/icon_grey_dragon_scale.png", 1070, 1150, 410, 260, "灰竜の鱗 / 128×128")
    draw.text((1080, 1450), "ゲーム表示: 候補01\napproved: false\n生成: image_gen\n2026-10-19", fill="#222222", font=small, spacing=12)
    output = ROOT / "eval/reports/screens/041/dragon-knight-sheet.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)


if __name__ == "__main__":
    main()
