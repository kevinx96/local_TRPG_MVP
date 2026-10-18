"""Register spec 034 assets; numbered background previews remain unapproved."""
from __future__ import annotations

import json
import shutil
import struct

from .risk_labels import ROOT


def main() -> None:
    source = ROOT / "assets/candidates/034/generation.json"
    entries = json.loads(source.read_text(encoding="utf-8"))
    if len(entries) != 13:
        raise ValueError("Expected six backgrounds and seven icons")
    qa = []
    for entry in entries:
        path = ROOT / entry["file"]
        header = path.read_bytes()[:29]
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(path)
        width, height = struct.unpack(">II", header[16:24])
        icon = entry["id"].startswith("icon_")
        if icon and (width != height or header[25] != 6):
            raise ValueError(f"Expected square RGBA icon: {path}")
        qa.append(dict(file=entry["file"], width=width, height=height, rgba=header[25] == 6))
    manifest_path = ROOT / "assets/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    previews = [entry for entry in entries if entry["id"].startswith("icon_") or entry["file"].endswith("candidate_01.png")]
    targets = {f"client/images/{entry['id']}.png" for entry in previews}
    manifest["images"] = [e for e in manifest["images"] if e.get("task") != "034" and e["file"] not in targets] + entries
    manifest["selections"] = [e for e in manifest["selections"] if e.get("task") != "034" and e["file"] not in targets]
    for entry in previews:
        target = f"client/images/{entry['id']}.png"
        shutil.copyfile(ROOT / entry["file"], ROOT / target)
        manifest["images"].append({**entry, "file": target, "source_candidate": entry["file"], "preview_only": True})
        manifest["selections"].append(dict(task="034", id=entry["id"], file=target,
            candidates=[e["file"] for e in entries if e["id"] == entry["id"]], selected_candidate=entry["file"],
            approved=False, preview_only=True,
            selection_reason="背景按编号01接入，图标按spec每项一张；TODO(design): 最终美术验收由设计负责人决定。"))
    manifest["tasks"] = list(dict.fromkeys([*manifest.get("tasks", []), "034"]))
    manifest["batches"]["034"] = dict(task="034", generator="image_gen", generation_date="2026-10-17", approved=False,
        candidate_count=13, preview_count=10, qa=qa, prompts="assets/candidates/034/generation.json",
        browser_checks="eval/reports/screens/034/checks.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
