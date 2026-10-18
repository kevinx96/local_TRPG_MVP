"""Apply the authored spec 033 to both packs; no later Oaksdawn chapters."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .risk_labels import PACKS, ROOT, annotate_risks, movement_destinations
from .upgrade_forest import upsert

UNDEAD = ("skeleton_soldier", "ghoul", "wraith", "grave_knight", "ash_wraith", "xanxus_phantom", "zebok")
CLUES = ("heard_guardian_refusal", "heard_pass_rumor")
RECRUIT_PREVIEW = "同行者にする（HPが半分を切ると最大HPの20%を回復、それ以外は敵へ2d6の光属性ダメージ）"
# Shown when arriving from the cave for the first time, and to the model while Liese still prays in the chapel.
GATE_CHALLENGE = "水路の出口は、鉄格子の水門で塞がれていた。格子の向こうから、鎧の擦れる音と誰何の声が響く。「止まれ！ 何者だ！」"
CHAPEL_WITH_LIESE = "高い窓から朝の光が差し込む礼拝堂。祭壇の前で、銀の鎧をまとった若い女騎士が祈りを捧げている。"
LIESE_DESCRIPTION = "暁の守護団の若き聖騎士。毎ラウンド開始時、プレイヤーのHPが半分未満なら「癒しの祈り」で最大HPの20%を回復し、そうでなければ「聖光の一撃」で敵へ2d6の光属性ダメージを与える（不死の敵を優先して狙う）。"
DESCRIPTIONS = {
    "cave_waterway": ("地底の水路", "温泉の湯は細い水路となって、岩の奥へ流れていく。水音を頼りに進むと、壁に古い騎士団の紋章――樫の葉と昇る太陽――が刻まれていた。"),
    "oaksdawn_water_gate": ("オークスドーンの水門", "城塞の水門。鉄格子の向こうでは、洞窟から続く地下水路が暗く口を開けている。"),
    "oaksdawn_square": ("城塞の大通り", "石畳の大通りの両側に、樫の木を組んだ兵舎と工房が並ぶ。城壁の上では、白い外套の守護団員たちが東の峠を見張っていた。大通りの突き当たりには、昇る太陽を掲げた本営の旗がはためいている。"),
    "oaksdawn_hq": ("守護団本営", "地図と剣が並ぶ質素な広間。白髪の老騎士――守護団長ヴァルターが、卓上の地図から顔を上げた。"),
    "oaksdawn_chapel": ("暁の礼拝堂", "高い窓から朝の光が差し込む礼拝堂。祭壇の前には、死者を弔う白い花が供えられている。"),
    "oaksdawn_workshop": ("城塞工房", "炉の熱と槌の音が響く工房。分厚い前掛けの女鍛冶師が、白銀の剣に光の紋を刻んでいる。"),
    "oaksdawn_inn": ("樫の葉亭", "樫の梁がむき出しの酒場兼宿屋。非番の守護団員たちが、干し肉をかじりながら峠の噂話をしている。"),
    "oaksdawn_wall": ("城壁の見張り台", "城壁の上からは、南に霧の古戦場、東に岩肌のむき出しになった峠が見渡せる。峠の道は、崩れ落ちた大岩でふさがれている。"),
}


def action(identifier: str, text: str, effects: list[dict[str, Any]] | None = None, **extra: Any) -> dict[str, Any]:
    return dict(id=identifier, text=text, preview="", risk="判定不要", intent_keywords=[text],
                effects=effects or [], **extra)


def apply(pack: dict[str, Any]) -> None:
    locations = {loc["id"]: loc for loc in pack["locations"]}
    for identifier, (title, description) in DESCRIPTIONS.items():
        # Spec 034 replaces the shared gate preview with its dedicated background below.
        background = "bg_cave_waterway" if identifier == "oaksdawn_water_gate" else f"bg_{identifier}"
        loc = dict(id=identifier, scene_id="dark_forest" if identifier == "cave_waterway" else "oaksdawn",
                   title=title, description=description, background_image=f"/static/images/{background}.png",
                   npc_ids=[], enemy_ids=[], actions=[], choices=[], connected_location_ids=[],
                   combat={"enemy_ids": [], "auto_start": False})
        upsert(pack["locations"], loc)
        locations[identifier] = loc

    def travel(identifier: str, text: str, destination: str, **extra: Any) -> dict[str, Any]:
        extra.setdefault("result_text", locations[destination]["description"])
        return action(identifier, text, [{"current_location": destination}], **extra)

    upsert(locations["cave_hot_spring"]["actions"], travel("follow_hot_spring_water", "湯の流れを辿る", "cave_waterway"))
    locations["cave_waterway"]["actions"] = [travel("waterway_to_gate", "水路の先へ進む", "oaksdawn_water_gate", result_text=GATE_CHALLENGE),
        travel("waterway_to_spring", "温泉へ戻る", "cave_hot_spring")]
    gate = locations["oaksdawn_water_gate"]
    gate["actions"] = [
        action("open_oaksdawn_gate", "名乗って門を開けてもらう", [{"set_flag": "opened_oaksdawn_gate"}, {"current_location": "oaksdawn_square"}],
               once="opened_oaksdawn_gate", hidden_after="opened_oaksdawn_gate",
               result_text="見張りの兵士は松明を掲げてこちらの顔を確かめると、渋々と格子を上げた。「森から水路を抜けてきただと……？ 団長に報告しておく。中へ入れ」"),
        travel("enter_oaksdawn", "城塞へ入る", "oaksdawn_square", visible_after="opened_oaksdawn_gate"),
        travel("gate_back_before", "水路を戻る", "cave_waterway", hidden_after="opened_oaksdawn_gate", requirements={"not_flag": "opened_oaksdawn_gate"}),
        travel("gate_back", "水路へ戻る", "cave_waterway", visible_after="opened_oaksdawn_gate")]
    destinations = [("hq", "守護団本営へ向かう"), ("chapel", "暁の礼拝堂へ向かう"), ("workshop", "城塞工房へ向かう"),
                    ("inn", "樫の葉亭へ向かう"), ("wall", "城壁の見張り台へ上る"), ("water_gate", "水門へ向かう")]
    locations["oaksdawn_square"]["actions"] = [travel(f"square_to_{suffix}", text, f"oaksdawn_{suffix}") for suffix, text in destinations]
    # Reaching the square by any road means the guards know you; the water gate is then just a passage.
    locations["oaksdawn_square"]["entry_effects"] = [{"set_flag": "visited_oaksdawn"}, {"set_flag": "opened_oaksdawn_gate"}]
    locations["oaksdawn_chapel"]["description_variants"] = [{"requirements": {"not_flag": "recruited_liese"}, "text": CHAPEL_WITH_LIESE}]
    for suffix in ("hq", "chapel", "workshop", "inn", "wall"):
        locations[f"oaksdawn_{suffix}"]["actions"] = [travel(f"{suffix}_to_square", "大通りへ戻る", "oaksdawn_square")]

    for identifier, name, description, suffix in [
        ("walter", "守護団長ヴァルター", "白髪の老騎士", "hq"),
        ("liese", "聖騎士リーゼ", "暁の守護団の若き聖騎士。", "chapel"),
        ("brigitte", "鍛冶師ブリギッテ", "分厚い前掛けの女鍛冶師", "workshop")]:
        upsert(pack["npcs"], dict(id=identifier, name=name, description=description, image=f"/static/images/npc_{identifier}.png"))
        locations[f"oaksdawn_{suffix}"].update(npc_ids=[identifier], portrait_image=f"/static/images/npc_{identifier}.png")
    locations["oaksdawn_hq"]["actions"][:0] = [
        action("greet_walter", "団長に挨拶する", once="greeted_walter", hidden_after="greeted_walter",
               result_text="「この砦まで辿り着くとは、物好きな冒険者だ。わしはヴァルター、暁の守護団の団長をしておる。……邪竜を討ちに行くのか。ならば一つ忠告しておこう。竜の谷の炎が本当にあの紅竜だけのものか、よく確かめることだ」"),
        action("ask_guardian_refusal", "十年前の遠征について聞く", once="heard_guardian_refusal", hidden_after="heard_guardian_refusal", visible_after="greeted_walter",
               result_text="「十年前、将軍ドラコは竜の谷への出兵を命じた。我ら守護団は盟約を理由にそれを拒み、それ以来、王都からは見捨てられた砦よ。あの時に谷へ向かった兵は、一人も帰ってこなかった」"),
        action("request_guardian_letter", "推薦状を願い出る", [{"add_item": {"id": "guardian_letter", "name": "守護団の推薦状", "quantity": 1}}],
               once="received_guardian_letter", hidden_after="received_guardian_letter", visible_after="heard_guardian_refusal",
               result_text="ヴァルターは羽根ペンを走らせ、封蝋を押した。「礼拝堂のリーゼに見せるといい。あの子は古戦場の鐘のことで、ずっと胸を痛めておる」")]
    upsert(pack["items"], dict(id="guardian_letter", name="守護団の推薦状", category="key", key_item=True, description="暁の守護団長ヴァルターの署名入りの推薦状。"))
    upsert(pack["items"], dict(id="guardian_chainmail", name="守護団の鎖帷子", category="equipment", slot="armor",
                              description="守護団員が身につける、目の細かい鎖帷子。", combat={"kind": "armor", "defense": 2}))
    recruit = [{"set_companion": "paladin_liese"}, {"set_flag": "recruited_liese"}]
    common = dict(visible_after="met_liese", hidden_after="recruited_liese", portrait_image="/static/images/npc_liese.png")
    chapel = locations["oaksdawn_chapel"]
    chapel.pop("portrait_image", None)
    chapel["npc_requirements"] = {"liese": {"not_flag": "recruited_liese"}}
    chapel["actions"][:0] = [
        action("pray_oaksdawn", "祈りを捧げてもらう", [{"gold_change": -5}, {"restore_full": True}], requirements={"gold_gte": 5},
               result_text="祭壇の前で目を閉じると、温かな光が体を包み、疲れが消えていった。"),
        action("talk_liese", "祈りを捧げる女騎士に話しかける", once="met_liese", hidden_after="met_liese",
               result_text="「私はリーゼ。暁の守護団の聖騎士です。……南の古戦場から、夜ごと弔いの鐘が聞こえるのです。死者がまだ眠れずにいる。いつか、確かめに行かなければ」"),
        action("recruit_liese_letter", "守護団の推薦状を見せる", deepcopy(recruit), **common,
               requirements={"all": [{"has_item": "守護団の推薦状"}, {"not_flag": "recruited_liese"}]},
               result_text="リーゼは推薦状の封蝋を確かめ、静かに頷いた。「団長がお認めになったのなら、私もこの剣を預けましょう」"),
        action("recruit_liese_water", "聖水を祭壇に捧げる", [{"remove_item": {"name": "聖水", "quantity": 1}}, *deepcopy(recruit)], **common,
               requirements={"all": [{"has_item": "聖水"}, {"not_flag": "recruited_liese"}]},
               result_text="祭壇に聖水を注ぐと、リーゼは目を見開いた。「死者を弔う心をお持ちなのですね。……ご一緒させてください」"),
        action("recruit_liese_persuade", "共に死者を弔いたいと説く", **common, once="persuaded_liese", requirements={"not_flag": "recruited_liese"},
               roll={"dice_type": "1d20+wis", "dc": 13}, success_effects=deepcopy(recruit), failure_effects=[],
               result_texts={"success": "「……その言葉、信じます。ご一緒させてください」", "failure": "「お気持ちは嬉しいのですが、私は守護団の務めを離れられません」"}),
        action("open_oaksdawn_chapel_shop", "聖水を分けてもらう", open_shop="oaksdawn_chapel_shop")]
    for entry in chapel["actions"]:
        if entry["id"].startswith("recruit_liese_"):
            entry["preview"] = RECRUIT_PREVIEW
        elif entry["id"] == "pray_oaksdawn":
            entry["preview"] = "5G"
    locations["oaksdawn_workshop"]["actions"][:0] = [
        action("talk_brigitte", "鍛冶師に話しかける", once="met_brigitte", hidden_after="met_brigitte",
               result_text="「守護団の鎧なら、いくらでも打ってやるよ。光の紋を刻んだ武器は……材料が揃ったら、また来な」"),
        action("open_oaksdawn_workshop_shop", "店に入る", open_shop="oaksdawn_workshop_shop")]
    locations["oaksdawn_inn"]["actions"][:0] = [
        action("rest_oaksdawn", "宿で休む", [{"gold_change": -10}, {"restore_full": True}], requirements={"gold_gte": 10},
               result_text="樫の香りのする寝台で、久しぶりにぐっすりと眠った。"),
        action("ask_oaksdawn_rumor", "噂話を聞く", once="heard_pass_rumor", hidden_after="heard_pass_rumor",
               result_text="「東の峠が、ひと晩で崩れた岩に塞がれちまった。その夜、白くてでかい影が谷の方へ飛んでいくのを見たって奴もいる」")]
    locations["oaksdawn_inn"]["actions"][0]["preview"] = "10G"
    locations["oaksdawn_wall"]["actions"][:0] = [
        travel("oaksdawn_to_battlefield", "城塞の街道を南へ下る", "old_battlefield",
               result_text="城門を出て街道を南へ下ると、やがて白い霧が足元から立ちのぼってきた。"),
        action("oaksdawn_east_pass", "東の峠へ向かう", enabled=False, disabled_reason="峠は崩れた大岩で塞がれていて、今は通れない。", requirements={})]
    upsert(locations["old_battlefield"]["actions"], travel("battlefield_to_oaksdawn", "城塞の街道を北へ向かう", "oaksdawn_square"))
    # The chapel shop is kept by an old priest, so it still makes sense after Liese joins the party.
    upsert(pack["npcs"], dict(id="oaksdawn_priest", name="礼拝堂の老司祭", description="暁の礼拝堂を守る老司祭。"))
    shop_lines = {
        "chapel": ("oaksdawn_priest", "holy_water", 12, "死者の弔いに、聖水をお持ちなさい。", "光のご加護がありますように。",
                   "……お代が少し足りないようですな。"),
        "workshop": ("brigitte", "guardian_chainmail", 40, "守護団の鎧なら任せな。体に合わせて仕立ててやるよ", "毎度。きつかったら言いな、すぐ詰め直してやる",
                     "金が足りないね。出直してきな"),
    }
    for suffix, (npc, item, price, greeting, buy_line, poor_line) in shop_lines.items():
        upsert(pack["shops"], dict(id=f"oaksdawn_{suffix}_shop", location_id=f"oaksdawn_{suffix}", keeper_npc=npc,
                                  title=locations[f"oaksdawn_{suffix}"]["title"], buys=False, greeting=greeting,
                                  buy_line=buy_line, poor_line=poor_line, items=[dict(item_id=item, price=price, stock=None)]))
    upsert(pack["companions"], dict(id="paladin_liese", name="聖騎士リーゼ", image="/static/images/npc_liese.png",
        description=LIESE_DESCRIPTION, round_start_effects=[
            dict(kind="heal_player", name="癒しの祈り", max_hp_ratio=.20, requirements={"player_hp_ratio_lt": .5}),
            dict(kind="damage_enemy", name="聖光の一撃", damage="2d6", element="holy", target="undead_first", requirements={"player_hp_ratio_gte": .5})]))
    for enemy in pack["enemies"]:
        if enemy["id"] in UNDEAD:
            enemy["tags"] = list(dict.fromkeys([*enemy.get("tags", []), "undead"]))
            enemy.setdefault("resistances", {})["holy"] = 1.5

    def add_clues(value: Any) -> None:
        if isinstance(value, dict):
            if "flags_count_gte" in value:
                flags = value["flags_count_gte"]["flags"]
                if "heard_old_soldier_ghost" in flags:
                    flags[:] = list(dict.fromkeys([*flags, *CLUES]))
            for child in value.values():
                add_clues(child)
        elif isinstance(value, list):
            for child in value:
                add_clues(child)
    add_clues(locations["castle_report"])
    for scene in pack["scenes"]:
        if scene["id"] == "dark_forest":
            scene["location_ids"] = list(dict.fromkeys([*scene["location_ids"], "cave_waterway"]))
            if scene.get("next_scene_ids"):
                scene["next_scene_ids"] = list(dict.fromkeys([*scene["next_scene_ids"], "oaksdawn"]))
        if scene["id"] == "old_battlefield":
            scene["next_scene_ids"] = list(dict.fromkeys([*scene.get("next_scene_ids", []), "oaksdawn"]))
    upsert(pack["scenes"], dict(id="oaksdawn", title="城塞都市オークスドーン", description=DESCRIPTIONS["oaksdawn_square"][1],
        location_ids=[key for key in DESCRIPTIONS if key.startswith("oaksdawn_")], npc_ids=["walter", "liese", "brigitte"],
        enemy_ids=[], next_scene_ids=["dark_forest", "old_battlefield"]))
    annotate_risks(pack)
    for identifier in [*DESCRIPTIONS, "cave_hot_spring", "old_battlefield"]:
        loc = locations[identifier]
        loc["connected_location_ids"] = list(dict.fromkeys([*loc.get("connected_location_ids", []), *[
            destination for entry in loc["actions"] for destination in movement_destinations(entry)]]))
        entries = loc["actions"] if identifier in DESCRIPTIONS else [entry for entry in loc["actions"]
            if entry["id"] in {"follow_hot_spring_water", "battlefield_to_oaksdawn"}]
        choices = [{key: deepcopy(value) for key, value in entry.items() if key in {
            "text", "preview", "risk", "requirements", "visible_after", "hidden_after", "once", "enabled", "disabled_reason", "open_shop"}}
            for entry in entries]
        if identifier in DESCRIPTIONS:
            loc["choices"] = choices
        else:
            loc["choices"] = [choice for choice in loc.get("choices", []) if choice["text"] not in {c["text"] for c in choices}] + choices
    add_maps(pack, locations)
    pack["meta"]["oaksdawn_v033"] = True
    pack["meta"]["content_revision"] = max(pack["meta"].get("content_revision", ""), "2026-10-17-v033")
    if pack["meta"].get("oaksdawn_v034"):
        from .oaksdawn_quests import apply as apply_quests

        apply_quests(pack)


def add_maps(pack: dict[str, Any], locations: dict[str, Any]) -> None:
    def node(identifier: str, label: str, x: int, y: int, location: str, **extra: Any) -> dict[str, Any]:
        return dict(id=identifier, label=label, kind="event", x=x, y=y,
                    location_ids=[location] if location else [], description=locations[location]["description"] if location else label, **extra)

    def edge(a: str, b: str, action_id: str = "") -> dict[str, Any]:
        return {"from": a, "to": b, **({"action_id": action_id} if action_id else {})}

    maps = {m["id"]: m for m in pack["maps"]}
    cave = maps["sealed_cave"]
    upsert(cave["nodes"], node("C6", "地底の水路", 75, 90, "cave_waterway"))
    upsert(cave["nodes"], node("oaksdawn", "オークスドーン", 95, 90, "", submap="oaksdawn", known_after="visited_oaksdawn"))
    for entry in [edge("C3b", "C6", "follow_hot_spring_water"), edge("C6", "C3b", "waterway_to_spring"), edge("C6", "oaksdawn", "waterway_to_gate")]:
        if entry not in cave["edges"]:
            cave["edges"].append(entry)
    forest_cave = next(n for n in maps["forest"]["nodes"] if n["id"] == "cave")
    forest_cave["location_ids"] = list(dict.fromkeys([*forest_cave["location_ids"], "cave_waterway"]))
    battlefield = maps["old_battlefield"]
    upsert(battlefield["nodes"], node("oaksdawn", "オークスドーン", 10, 15, "", submap="oaksdawn", known_after="visited_oaksdawn"))
    link = edge("B1", "oaksdawn", "battlefield_to_oaksdawn")
    if link not in battlefield["edges"]:
        battlefield["edges"].append(link)
    rows = [("G0", "水門", 8, 55, "water_gate"), ("G1", "大通り", 45, 55, "square"),
            ("G2", "本営", 45, 15, "hq"), ("G3", "礼拝堂", 20, 25, "chapel"), ("G4", "工房", 72, 22, "workshop"),
            ("G5", "樫の葉亭", 25, 85, "inn"), ("G6", "見張り台", 80, 75, "wall")]
    edges = []
    for identifier, _, _, _, suffix in rows:
        if identifier != "G1":
            edges += [edge("G1", identifier, f"square_to_{suffix}"),
                      edge(identifier, "G1", "" if suffix == "water_gate" else f"{suffix}_to_square")]
    next(e for e in edges if e["from"] == "G0")["action_ids"] = ["open_oaksdawn_gate", "enter_oaksdawn"]
    upsert(pack["maps"], dict(id="oaksdawn", title="城塞都市オークスドーン",
        nodes=[node(identifier, label, x, y, f"oaksdawn_{suffix}") for identifier, label, x, y, suffix in rows], edges=edges))


def main() -> None:
    for filename in PACKS:
        path = ROOT / "host/prompt/processed" / filename
        original = path.read_text(encoding="utf-8")
        pack = json.loads(original)
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2 if '\n  "' in original[:200] else None)
                        + ("\n" if original.endswith("\n") else ""), encoding="utf-8")


if __name__ == "__main__":
    main()
