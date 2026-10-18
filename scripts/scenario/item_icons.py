"""Offline spec 036 icon catalog, installation, registration and review sheet."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from .risk_labels import PACKS, ROOT


CATALOG = ROOT / "assets/candidates/036/generation.json"
SCREENS = ROOT / "eval/reports/screens/036"
INLINE_IDS = {
    "革の鎧": "leather_armor", "聖なる杖": "holy_staff", "ローブ": "robe",
    "魔導書": "grimoire", "魔法のローブ": "magic_robe", "ダガー": "dagger", "盗賊道具": "thieves_tools",
}
PILOTS = {"holy_silver", "baked_lava_stone", "dawn_sword", "dawn_khakkhara",
          "dawn_staff", "dawn_dagger", "guardian_small_shield"}
STYLE = (
    "Use case: stylized-concept. Asset type: one square fantasy inventory item icon, readable at 32px, "
    "for final 128x128 PNG. Match the existing Dawn weapon icons: detailed semi-realistic Japanese fantasy "
    "thick-painted illustration, visible painterly material texture, restrained saturation, upper-left lighting. "
    "One centered item, entirely visible, 8 percent empty margins. Actual transparent background, clean alpha. "
    "No text, letters, labels, frame, watermark, person, hands, ground, scenery or additional props. "
    "Use only the described appearance; do not invent emblems or narrative details. "
)
# These are visual instructions only; authored item text and game categories are never rewritten.
DETAILS = {
    "iron_sword": "One plain iron sword. Keep it simple.",
    "herb": "One sprig of medicinal herb, clearly readable leaves; no invented flowers.",
    "magic_scroll": "One rolled magic scroll. No visible writing or added element emblem.",
    "mp_potion": "One small bottle of blue medicine.",
    "travel_potion": "One small corked bottle of red healing medicine.",
    "ice_charm": "One simple frost-cold charm, no writing. Keep this base form for the activated version.",
    "adamantite_armor": "One suit of armor made from extremely hard metal, no invented crest.",
    "ice_iron_greatsword": "One large high-quality iron greatsword fused with the ice charm, cold blade.",
    "ice_katana": "One powerful ice-element katana, full curved blade and grip visible.",
    "earth_staff": "One staff imbued with earth magic. No invented insignia or additional plants.",
    "healing_scroll": "One healing scroll, partly rolled, no readable writing or invented emblem.",
    "fireball_scroll": "One scroll containing fireball magic, restrained fire glow attached to the scroll, no writing.",
    "smoke_bomb": "One smoke bomb, with only a small trace of smoke attached to the object.",
    "poison_dart": "One poison arrow; full arrowhead, shaft and fletching visible.",
    "cursed_holy_sword": "One holy sword with black-purple curse markings along the blade, as required by spec 036.",
    "cursed_holy_staff": "One cursed holy staff. Convey the curse subtly; no invented religious emblem.",
    "cursed_crystal_ball": "One cursed crystal ball containing dark magic, no stand or extra objects.",
    "dark_crystal_ball": "One dark crystal ball, free of curse markings; dark power inside, no stand.",
    "cursed_dagger": "One cursed dagger associated with poison, no added emblem or creatures.",
    "rusted_crown": "One old rusted crown, all metal corroded as described, no slime creature.",
    "shrinking_gun": "One fantasy shrinking gun. No modern branding or readable markings.",
    "fire_seed": "One unstable glowing ember of magical fire, as described in the story, without a container or body.",
    "activated_ice_charm": "The same charm as icon_ice_charm, with one additional ring of cold light, per spec 036.",
    "trail_ration": "One compact travel ration portion containing dried meat and hardtack, no other food.",
    "holy_water": "One small vessel of clear purified water, no invented religious emblem.",
    "white_dragon_scale": "One snow-white dragon scale, icy surface that freezes fingers, no dragon.",
    "ice_crystal": "One unmelted piece of ice crystal.",
    "red_dragon_core": "One crystal containing the red dragon Ignis's living flame, no dragon or heart anatomy.",
    "prism_shard": "One crystal shard with shifting rainbow colors and contained magical light.",
    "ruby_charm": "One charm set with a warm red gemstone.",
    "glowing_moss": "One small patch of faintly glowing moss, no flowers or mushrooms.",
    "robert_hammer": "One old blacksmith hammer; engraved handle seen at a scale that reveals no readable letters.",
    "prism_weapon_hero": "One sword with a blade of shifting rainbow colors.",
    "prism_weapon_cleric": "One staff splitting prayer light into seven colors.",
    "prism_weapon_mage": "One magical orb with light shifting between elemental colors, no stand.",
    "prism_weapon_thief": "One short dagger whose blade changes color.",
    "dragon_elixir": "One bottle of old medicine brewed from dragon scales; no dragon decoration or invented liquid color.",
    "draco_journal": "One closed journal, no visible title or readable writing.",
    "frost_seal_charm": "One charm woven with white dragon scales, visibly woven construction.",
    "assassin_crest": "One badge in the shape of a white dragon, no text.",
    "fire_dragon_oil": "One small vessel of volcanic oil, no flames or invented dragon ornament.",
    "gravekeeper_cloak": "One old guard's cloak, lining visible, stitched prayer marks too small to be writing; no wearer.",
    "elixir_str": "One bottle of old strength elixir; no invented color or symbol.",
    "elixir_dex": "One bottle of agility elixir; no invented color or symbol.",
    "elixir_int": "One bottle of clear blue wisdom elixir, matching the explicit blue description.",
    "elixir_wis": "One bottle of prayer elixir; no invented color or religious symbol.",
    "elixir_end": "One bottle of endurance elixir; no invented color or rock emblem.",
    "fruit_life": "One ripe red mysterious fruit, no invented species-specific details.",
    "fruit_mana": "One mysterious blue glowing fruit, no invented species-specific details.",
    "guardian_letter": "One recommendation letter; fold it so the signature and text are not visible. No invented seal.",
    "guardian_chainmail": "One shirt of finely linked chain mail, no invented crest.",
    "spirit_spring_water": "One travel water flask containing clear faintly glowing spring water. Story says 空の水筒に汲んだ.",
    "leather_armor": "One simple lightweight tanned-leather armor, shared by hero and thief.",
    "holy_staff": "One staff that amplifies holy magic, no invented religious emblem.",
    "robe": "One simple cleric's robe, no wearer or invented insignia.",
    "grimoire": "One closed book of ancient magic, no visible title or readable writing.",
    "magic_robe": "One fine robe imbued with magic, no wearer or invented insignia.",
    "dagger": "One lightweight, easy-to-handle short dagger.",
    "thieves_tools": "One compact set of lockpicking and trap-disarming tools arranged as a single inventory item.",
}


def records(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return [*pack.get("items", []), *(item for character in pack.get("characters", [])
                                     for item in character.get("inventory", []))]


def icon_ids(pack: dict[str, Any]) -> dict[str, str]:
    return {**INLINE_IDS, **{item["name"]: item["id"] for item in pack.get("items", [])}}


def apply(pack: dict[str, Any]) -> None:
    identifiers = icon_ids(pack)
    for item in records(pack):
        item["icon"] = f"/static/images/icon_{identifiers[item['name']]}.png"
    pack["meta"]["item_icons_v036"] = True


def catalog() -> list[dict[str, Any]]:
    from host.shops import item_category

    manifest = json.loads((ROOT / "assets/manifest.json").read_text(encoding="utf-8"))
    approved = {entry["file"]: entry.get("approved", False) for entry in manifest["images"]}
    unique: dict[str, dict[str, Any]] = {}
    for filename in PACKS:
        pack = json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8"))
        identifiers = icon_ids(pack)
        for item in records(pack):
            identifier = identifiers[item["name"]]
            if identifier in unique:
                continue
            slot = item.get("slot")
            group = {"weapon": "武器", "armor": "防具", "accessory": "補助"}.get(slot)
            group = group or {"consumable": "消耗品", "material": "素材", "loot": "戦利品", "key": "重要",
                              "equipment": "装備", "": "その他"}[item_category(item)]
            orientation = ("Weapon laid diagonally from lower left to upper right." if group == "武器" or identifier in {"holy_staff", "poison_dart"}
                           else "Armor shown straight from the front." if group == "防具"
                           else "Front view with a slight view from above.")
            file = f"client/images/icon_{identifier}.png"
            unique[identifier] = dict(task="041" if identifier == "grey_dragon_scale" else "038" if group == "戦利品" else "036", id=f"icon_{identifier}", name=item["name"], group=group,
                file=file, generator="image_gen", approved=approved.get(file, False) if identifier in PILOTS else False,
                transparent_background=True, retained_from="034" if identifier in PILOTS else None,
                prompt=STYLE + f"Subject: {item['name']}。{item.get('description', '')} "
                       + DETAILS.get(identifier, "" if group == "戦利品" else "Retain the original 034 pilot unchanged.") + " " + orientation)
    return list(unique.values())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def install(identifier: str, source: Path) -> None:
    from PIL import Image

    entry = next(e for e in catalog() if e["id"] == identifier)
    if entry["retained_from"]:
        raise ValueError("034 pilots must remain unchanged")
    with Image.open(source) as image:
        image = image.convert("RGBA")
        if image.width != image.height or image.getchannel("A").getextrema() != (0, 255):
            raise ValueError("Expected a square transparent image with an opaque subject")
        image.resize((128, 128), Image.Resampling.LANCZOS).save(ROOT / entry["file"], optimize=True, compress_level=9)


def finish() -> None:
    from PIL import Image, ImageDraw, ImageFont

    entries = json.loads(CATALOG.read_text(encoding="utf-8"))
    qa = []
    for entry in entries:
        path = ROOT / entry["file"]
        with Image.open(path) as image:
            if image.size != (128, 128) or image.mode != "RGBA" or image.getchannel("A").getextrema() != (0, 255):
                raise ValueError(f"Invalid final icon: {path}")
        qa.append(dict(file=entry["file"], bytes=path.stat().st_size, width=128, height=128, rgba=True))
    total = sum(p.stat().st_size for p in (ROOT / "client/images").glob("icon_*.png"))
    if total >= 2_000_000:
        raise ValueError(f"Icon budget exceeded: {total}")
    manifest_path = ROOT / "assets/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    new_entries = [entry for entry in entries if not entry["retained_from"]]
    manifest["images"] = [e for e in manifest["images"] if e.get("task") != "036"] + new_entries
    manifest["tasks"] = list(dict.fromkeys([*manifest.get("tasks", []), "036"]))
    manifest["batches"]["036"] = dict(task="036", generator="image_gen", approved=False,
        icon_count=len(entries), new_count=len(new_entries), retained_count=len(PILOTS), total_bytes=total,
        output_size=[128, 128], prompts=str(CATALOG.relative_to(ROOT)).replace("\\", "/"), qa=qa,
        sheet="eval/reports/screens/036/icons-sheet.png", browser_checks="eval/reports/screens/036/checks.json")
    write_json(manifest_path, manifest)
    groups = ["武器", "防具", "補助", "装備", "消耗品", "素材", "重要", "その他"]
    groups = [(group, [e for e in entries if e["group"] == group]) for group in groups]
    groups = [(group, rows) for group, rows in groups if rows]
    height = 72 + sum(48 + math.ceil(len(rows) / 7) * 180 for _, rows in groups)
    sheet = Image.new("RGB", (1400, height), "#171b26")
    draw = ImageDraw.Draw(sheet)
    font_path = Path(r"C:\Windows\Fonts\meiryo.ttc")
    font = ImageFont.truetype(str(font_path), 16)
    title = ImageFont.truetype(str(font_path), 25)
    draw.text((24, 16), "道具アイコン一覧 — 036", font=title, fill="#eee6d5")
    y = 72
    for group, rows in groups:
        draw.text((24, y), group, font=title, fill="#d4a94b")
        y += 48
        for index, entry in enumerate(rows):
            x, top = (index % 7) * 200, y + (index // 7) * 180
            with Image.open(ROOT / entry["file"]) as icon:
                sheet.paste(icon, (x + 36, top), icon)
            name = entry["name"]
            lines = [name] if draw.textlength(name, font=font) <= 192 else [name[:10], name[10:]]
            for line_index, line in enumerate(lines):
                draw.text((x + (200 - draw.textlength(line, font=font)) / 2, top + 133 + line_index * 22),
                          line, font=font, fill="#eee6d5")
        y += math.ceil(len(rows) / 7) * 180
    SCREENS.mkdir(parents=True, exist_ok=True)
    sheet.save(SCREENS / "icons-sheet.png", optimize=True)
    print(f"{len(entries)} icons; {len(new_entries)} new; {total} bytes; RGBA 128x128")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    sub.add_parser("apply")
    sub.add_parser("finish")
    importer = sub.add_parser("install")
    importer.add_argument("id")
    importer.add_argument("source", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        write_json(CATALOG, [entry for entry in catalog() if entry["task"] == "036"])
    elif args.command == "install":
        install(args.id, args.source)
    elif args.command == "finish":
        finish()
    else:
        for filename in PACKS:
            path = ROOT / "host/prompt/processed" / filename
            original = path.read_text(encoding="utf-8")
            pack = json.loads(original)
            apply(pack)
            path.write_text(json.dumps(pack, ensure_ascii=False, indent=2 if '\n  "' in original[:200] else None)
                            + ("\n" if original.endswith("\n") else ""), encoding="utf-8")


if __name__ == "__main__":
    main()
