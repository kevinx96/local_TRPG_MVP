"""Register the 22 unapproved 035 candidates and expose numbered previews."""
from __future__ import annotations

import json
import shutil
import struct
from collections import Counter

from .risk_labels import ROOT


def main() -> None:
    entries = json.loads((ROOT / "assets/candidates/035/generation.json").read_text(encoding="utf-8"))
    counts = Counter(e["id"] for e in entries)
    if len(counts) != 11 or set(counts.values()) != {2}:
        raise ValueError("035 requires two candidates for each of eleven assets")
    qa = []
    for entry in entries:
        header = (ROOT / entry["file"]).read_bytes()[:29]
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(entry["file"])
        width, height = struct.unpack(">II", header[16:24])
        transparent = not entry["id"].startswith("bg_")
        if transparent and header[25] != 6:
            raise ValueError(f"Transparent RGBA required: {entry['file']}")
        qa.append(dict(file=entry["file"], width=width, height=height, rgba=header[25] == 6))
    path = ROOT / "assets/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["images"] = [e for e in manifest["images"] if e.get("task") != "035"] + entries
    manifest["selections"] = [e for e in manifest["selections"] if e.get("task") != "035"]
    for entry in entries:
        if not entry["file"].endswith("candidate_01.png"):
            continue
        target = f"client/images/{entry['id']}.png"
        shutil.copyfile(ROOT / entry["file"], ROOT / target)
        manifest["images"].append({**entry, "file": target, "source_candidate": entry["file"], "preview_only": True})
        manifest["selections"].append(dict(task="035", id=entry["id"], file=target,
            candidates=[e["file"] for e in entries if e["id"] == entry["id"]], selected_candidate=entry["file"],
            approved=False, preview_only=True,
            selection_reason="按编号01接入工程预览；TODO(design): 22张候选由设计负责人选定，未作最终选图。"))
    manifest["tasks"] = list(dict.fromkeys([*manifest.get("tasks", []), "035"]))
    manifest["batches"]["035"] = dict(task="035", generator="image_gen", generation_date="2026-10-18",
        approved=False, candidate_count=22, preview_count=11, qa=qa, prompts="assets/candidates/035/generation.json",
        browser_checks="eval/reports/screens/035/checks.json")
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
