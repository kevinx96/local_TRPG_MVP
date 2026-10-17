"""Register spec 033 candidates and copy numbered preview assets without approving a selection."""
from __future__ import annotations

import json
import shutil

from .risk_labels import ROOT


def main() -> None:
    candidates = json.loads((ROOT / "assets/candidates/033/generation.json").read_text(encoding="utf-8"))
    manifest_path = ROOT / "assets/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(candidates) != 20 or any(not (ROOT / entry["file"]).is_file() for entry in candidates):
        raise ValueError("Expected twenty generated candidate PNGs")
    manifest["images"] = [entry for entry in manifest["images"] if entry.get("task") != "033"] + candidates
    manifest["selections"] = [entry for entry in manifest["selections"] if entry.get("task") != "033"]
    for entry in candidates:
        if not entry["file"].endswith("candidate_01.png"):
            continue
        target = f"client/images/{entry['id']}.png"
        shutil.copyfile(ROOT / entry["file"], ROOT / target)
        manifest["images"].append({**entry, "file": target, "source_candidate": entry["file"], "preview_only": True})
        manifest["selections"].append(dict(task="033", id=entry["id"], file=target,
            candidates=[e["file"] for e in candidates if e["id"] == entry["id"]], selected_candidate=entry["file"],
            approved=False, preview_only=True,
            selection_reason="工程按编号01提供运行预览，不作审美取舍；TODO(design): 最终选图由设计负责人决定。"))
    manifest["tasks"] = list(dict.fromkeys([*manifest.get("tasks", []), "033"]))
    manifest["batches"]["033"] = dict(task="033", generator="image_gen", generation_date="2026-10-17", approved=False,
        candidate_count=20, preview_count=10, qa={
            "dimensions": "14张背景1672×941 RGB，6张立绘1024×1536 RGBA；保留生成原生尺寸。",
            "alpha": "立绘alpha范围0..254；透明区域含未清零RGB，浏览器按alpha合成；未做像素后处理。",
            "style": "已逐张查看候选；细节及最终风格归设计审定。水路比细水渠宽、本営与礼拝堂装饰较繁复，候选墙面/旗帜紋章与城外霜覆盖范围有差异。",
            "prompts": "assets/candidates/033/generation.json",
            "browser_checks": "eval/reports/screens/033/checks.json"})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
