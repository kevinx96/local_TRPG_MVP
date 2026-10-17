"""Apply the authored spec 034 quests, materials and dawn weapons to both packs."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .oaksdawn import action
from .risk_labels import PACKS, ROOT
from .upgrade_forest import upsert


BELL_REQUEST = "古戦場の外れの礼拝堂に、昔の鐘が残っているのです。誰かがあの鐘を正しく鳴らせば、死者は眠りにつけるはず……"
BELL_TEXT = "錆びた鐘の綱を引くと、澄んだ音が古戦場に響き渡った。霧の向こうで、無数の影が静かに頭を垂れ、消えていった。"
LIESE_THANKS = "リーゼは鐘の音が消えるまで目を閉じていた。「……ありがとう。これで、皆が眠れます」"
FORGE_REQUEST = "炉の火床が割れちまってね。熱に強い石が要るんだ。森の洞窟の奥に、溶岩で焼けた石があるって聞いたけど……"
FORGE_TEXT = "ブリギッテは石を叩いて音を確かめ、にやりと笑った。「上等だ。礼に、あんたの鎧を打ち直してやるよ」"
DAWN_TEXT = "ブリギッテは聖銀を炉にくべ、打ち延ばした刃に細い光の紋を一本ずつ刻んでいった。「ほらよ。死者相手なら、こいつがいちばん効く」"
FOG_TEXT = "鐘が鳴って以来、霧は少しだけ薄くなった。"
WEAPONS = {
    "hero": ("dawn_sword", "暁光の剣", "2d6+str/3+2", 92, "刃に昇る太陽の紋を刻んだ聖銀の剣。"),
    "cleric": ("dawn_khakkhara", "暁光の錫杖", "1d8+wis/3+2", 92, "光の紋が祈りを増幅する聖銀の錫杖。"),
    "mage": ("dawn_staff", "暁光の杖", "1d8+int/3+4", 92, "先端の聖銀が、魔力を光に変える杖。"),
    "thief": ("dawn_dagger", "暁光の短剣", "2d4+dex/4+3", 96, "闇に紛れても淡く光る、聖銀の短剣。"),
}
MATERIALS = {
    "holy_silver": ("聖銀", "光を通すと淡く輝く銀。ブリギッテの工房で、光の紋を刻む武器の材料になる。"),
    # TODO(design): spec未提供独立道具说明文；先复用拾取叙述，不补写设定。
    "baked_lava_stone": ("焼けた溶岩石", "溶岩の熱を吸って黒く焼けた石。今もほんのりと温かい。"),
}

# Quest logs summarise in the narrator's voice, as the older quests do; the NPC lines stay in the dialogue.
BELL_QUEST_LOG = "聖騎士リーゼは、古戦場の礼拝堂に残る鐘を正しく鳴らせば、眠れぬ死者を送れると信じている。"
HEARTH_QUEST_LOG = "城塞工房の炉の火床が割れた。鍛冶師ブリギッテは、熱に強い溶岩で焼けた石を探している。"
PICK_STONE_TEXT = "熱の残る黒い石を布でくるみ、背嚢に押し込んだ。"

def apply(pack: dict[str, Any]) -> None:
    locations = {loc["id"]: loc for loc in pack["locations"]}
    for identifier, (name, description) in MATERIALS.items():
        upsert(pack["items"], dict(id=identifier, name=name, description=description, category="material",
                                  icon=f"/static/images/icon_{identifier}.png"))
    for character, (identifier, name, damage, accuracy, description) in WEAPONS.items():
        spec = dict(kind="weapon", name=name, damage=damage, accuracy=accuracy, element="holy")
        if character == "cleric":
            spec["skill_healing_bonus"] = 2
        upsert(pack["items"], dict(id=identifier, name=name, description=description, category="equipment",
                                  slot="weapon", combat=spec, icon=f"/static/images/icon_{identifier}.png"))
    # Spec's aid uses the existing 補助 slot, stored as accessory since 032.
    upsert(pack["items"], dict(id="guardian_small_shield", name="守護団の小盾", category="equipment",
        slot="accessory", description="樫と太陽の紋章を描いた小さな盾。", combat=dict(kind="armor", defense=1),
        icon="/static/images/icon_guardian_small_shield.png"))
    items = {item["id"]: item for item in pack["items"]}

    def give(identifier: str) -> dict[str, Any]:
        item = items[identifier]
        return {"add_item": {"id": identifier, "name": item["name"], "quantity": 1,
                             **({"slot": item["slot"]} if item.get("slot") else {})}}

    def add_action(location: str, entry: dict[str, Any]) -> None:
        entry["risk_source"] = "action"
        upsert(locations[location]["actions"], entry)

    # Combat-only rewards remain separate from the stealable fruit and its shared elite flags.
    for location, identifier in (("grave_chapel", "holy_silver"), ("valley_ledge", "baked_lava_stone")):
        locations[location]["combat"]["victory_reward"] = {
            "flag": f"reward_claimed:{identifier}", "items": [give(identifier)["add_item"]]}
    shop = next(s for s in pack["shops"] if s["id"] == "oaksdawn_workshop_shop")
    shop["items"] = [offer for offer in shop["items"] if offer["item_id"] != "holy_silver"]
    shop["items"].append(dict(item_id="holy_silver", price=120, stock=None))

    forge_effects = [{"remove_item": {"name": "聖銀", "quantity": 1}}, {"gold_change": -30}]
    for character, (identifier, name, *_) in WEAPONS.items():
        forge_effects.append({"branch": {"requirements": {"character_id": character},
                                        "then": [give(identifier), {"equip_item": name}]}})
    add_action("oaksdawn_workshop", action("forge_dawn_weapon", "光の紋を刻んでもらう", forge_effects,
        once="forged_dawn_weapon", hidden_after="forged_dawn_weapon", visible_requirements={"has_item": "聖銀"},
        requirements={"all": [{"has_item": "聖銀"}, {"gold_gte": 30}]}, result_text=DAWN_TEXT))
    next(a for a in locations["oaksdawn_workshop"]["actions"] if a["id"] == "forge_dawn_weapon")["preview"] = "聖銀 ×1 / 30G"

    add_action("oaksdawn_chapel", action("ask_battlefield_bell", "鐘のことを詳しく聞く",
        once="accepted_battlefield_bell", hidden_after="accepted_battlefield_bell", visible_after="met_liese",
        result_text=f"「{BELL_REQUEST}」"))
    events = locations["grave_chapel"].setdefault("entry_events", [])
    events[:] = [event for event in events if event["once"] != "accepted_battlefield_bell"]
    events.append(dict(once="accepted_battlefield_bell", requirements={"companion_id": "paladin_liese"},
                       narrate=True, text=f"「{BELL_REQUEST}」", portrait_image="/static/images/npc_liese.png"))
    add_action("grave_chapel", action("ring_battlefield_bell", "弔いの鐘を鳴らす",
        [{"set_flag": "laid_battlefield_to_rest"}], visible_after="passed_grave_chapel",
        once="laid_battlefield_to_rest", hidden_after="laid_battlefield_to_rest", result_text=BELL_TEXT,
        result_variants=[dict(requirements={"companion_id": "paladin_liese"}, text=f"{BELL_TEXT}\n{LIESE_THANKS}")]))
    reward = [give("holy_silver"), {"gold_change": 100}, give("guardian_small_shield")]
    for location, text in (
        ("oaksdawn_chapel", "リーゼは胸に手を当てて、深く頭を下げた。「団長にも伝えておきます。……これは、守護団からのお礼です」"),
        ("oaksdawn_hq", "ヴァルターは長いこと黙っていた。「十年、あの鐘の音を待っておった。礼を言う」")):
        add_action(location, action(f"report_battlefield_bell_{location.rsplit('_', 1)[1]}", "鐘を鳴らしたことを伝える", deepcopy(reward),
            once="rewarded_battlefield_bell", hidden_after="rewarded_battlefield_bell", visible_after="laid_battlefield_to_rest",
            visible_requirements={"not_companion_id": "paladin_liese"} if location == "oaksdawn_chapel" else {},
            requirements={"not_companion_id": "paladin_liese"} if location == "oaksdawn_chapel" else {}, result_text=text))
    battlefield = locations["old_battlefield"]
    variants = battlefield.setdefault("description_variants", [])
    variants[:] = [v for v in variants if v.get("requirements") != {"flag": "laid_battlefield_to_rest"}]
    variants.insert(0, dict(requirements={"flag": "laid_battlefield_to_rest"}, text=battlefield["description"] + FOG_TEXT))
    for loc in pack["locations"]:
        for entry in loc.get("actions", []):
            if any(e.get("current_location") == "old_battlefield" for e in entry.get("effects", [])):
                variants = entry.setdefault("result_variants", [])
                variants[:] = [v for v in variants if v.get("requirements") != {"flag": "laid_battlefield_to_rest"}]
                variants.insert(0, dict(requirements={"flag": "laid_battlefield_to_rest"},
                                       text=str(entry.get("result_text") or battlefield["description"]) + FOG_TEXT))

    add_action("oaksdawn_workshop", action("ask_workshop_hearth", "何か困っていることは？",
        once="accepted_workshop_hearth", hidden_after="accepted_workshop_hearth", visible_after="met_brigitte",
        result_text=f"「{FORGE_REQUEST}」"))
    add_action("cave_lava_room", action("pick_baked_lava_stone", "溶岩で焼けた石を拾う", [give("baked_lava_stone")],
        once="picked_baked_lava_stone", hidden_after="picked_baked_lava_stone", result_text=PICK_STONE_TEXT))
    add_action("oaksdawn_workshop", action("deliver_baked_lava_stone", "焼けた石を渡す",
        [{"remove_item": {"name": "焼けた溶岩石", "quantity": 1}},
         {"reforge_armor": {"defense_bonus": 1, "suffix": "＋", "fallback_item": "守護団の鎖帷子"}}],
        once="rewarded_workshop_hearth", hidden_after="rewarded_workshop_hearth", visible_after="accepted_workshop_hearth",
        requirements={"has_item": "焼けた溶岩石"}, result_text=FORGE_TEXT))
    # TODO(design): 日志的独立说明和阶段文案未提供，复用定稿对白与选项。
    upsert(pack["quests"], dict(id="side_battlefield_bell", title="古戦場の鐘", description=BELL_QUEST_LOG, kind="side",
        start_flag=["accepted_battlefield_bell", "laid_battlefield_to_rest"], complete_flags=["rewarded_battlefield_bell"],
        fail_flags=[], stages=[dict(text="古戦場の礼拝堂で、弔いの鐘を鳴らす", done_flag="laid_battlefield_to_rest"),
                               dict(text="リーゼか団長ヴァルターに報告する", done_flag="rewarded_battlefield_bell")]))
    upsert(pack["quests"], dict(id="side_workshop_hearth", title="工房の火床", description=HEARTH_QUEST_LOG, kind="side",
        start_flag="accepted_workshop_hearth", complete_flags=["rewarded_workshop_hearth"], fail_flags=[],
        stages=[dict(text="焼けた溶岩石をブリギッテに渡す（洞窟の溶岩の小部屋か、溶岩ドレイクから手に入る）",
                     done_flag="rewarded_workshop_hearth")]))
    locations["oaksdawn_water_gate"]["background_image"] = "/static/images/bg_oaksdawn_water_gate.png"
    pack["meta"]["oaksdawn_v034"] = True
    pack["meta"]["content_revision"] = max(pack["meta"].get("content_revision", ""), "2026-10-17-v034")


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
