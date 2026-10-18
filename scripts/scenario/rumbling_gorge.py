"""Apply spec 035's authored gorge and hydromancer to both scenario packs."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .oaksdawn import action
from .risk_labels import PACKS, ROOT, annotate_risks, movement_destinations
from .upgrade_forest import upsert

CLUES = ("read_miner_diary", "saw_white_claw")
DESCRIPTIONS = {
    "gorge_entrance": ("峡谷の入口", "守護団員がどけた岩の向こうに、深い峡谷が口を開けていた。足元が低く唸るように揺れ、岩壁から小石がぱらぱらと落ちてくる。"),
    "gorge_rockfall_path": ("落石の道", "崩れた岩が転がる細い道。岩陰から、砂利を固めたような甲虫が二匹、顎を鳴らして這い出してきた。"),
    "gorge_miner_camp": ("鉱夫の野営跡", "崩れかけた天幕と、冷えた竈が残る野営跡。逃げ出した鉱夫たちの道具が、そのまま散らばっている。"),
    "gorge_claw_cliff": ("白い爪痕の崖", "峠をふさいでいた崩落の跡。巨大な岩の断面に、何かが引き裂いたような爪痕が三本、深く刻まれている。"),
    "gorge_giant_path": ("岩の巨人の通り道", "峡谷が狭まる先で、苔むした岩山がゆっくりと立ち上がった。岩の巨人だ。足元では、石肌のトカゲが舌を鳴らしている。"),
    "gorge_worm_lair": ("峡谷の底", "峡谷の底は、無数の穴で蜂の巣のようになっていた。地鳴りがひときわ大きくなり、地面を突き破って巨大なワームが姿を現す。"),
}
ENEMIES = (
    ("gravel_beetle", "砂礫の甲虫", "砂利を固めたような殻を持つ甲虫。", 14, "1d6+2"),
    ("stone_lizard", "石肌のトカゲ", "石のような鱗に覆われたトカゲ。", 10, "1d4+1"),
    ("rock_giant", "岩の巨人", "苔むした岩山が意思を持った、峡谷の巨人。", 23, "1d6+2"),
    ("earth_worm", "土喰らいの大ワーム", "峡谷の地下を食い荒らす、巨大なワーム。", 45, "1d10+2"),
)
BATTLES = ("gorge_rockfall_path", "gorge_giant_path", "gorge_worm_lair")
ELIO_DESCRIPTION = "流れの水術士。毎ラウンド開始時に「水刃」で敵へ2d3の水属性ダメージを与える（水に弱い敵を優先して狙う）。4ラウンドごとに「水の帳」を張り、そのラウンドにプレイヤーが受けるダメージを半分にする。"
INN_WITH_ELIO = "樫の梁がむき出しの酒場兼宿屋。非番の守護団員たちが峠の噂話をする隅で、青い外套の青年が水差しの水面をじっと見つめている。"
OPEN_WALL = "城壁の上からは、南に霧の古戦場、東に岩肌のむき出しになった峠が見渡せる。峠の大岩はどけられ、細い道が東へ続いている。"


def apply(pack: dict[str, Any]) -> None:
    locations = {loc["id"]: loc for loc in pack["locations"]}
    for identifier, (title, description) in DESCRIPTIONS.items():
        loc = dict(id=identifier, title=title, description=description, scene_id="rumbling_gorge",
                   background_image=f"/static/images/bg_{identifier}.png", actions=[], choices=[],
                   npc_ids=[], enemy_ids=[], connected_location_ids=[], combat={"enemy_ids": [], "auto_start": False})
        upsert(pack["locations"], loc)
        locations[identifier] = loc

    def travel(identifier: str, text: str, destination: str, **extra: Any) -> dict[str, Any]:
        extra.setdefault("result_text", locations[destination]["description"])
        return action(identifier, text, [{"current_location": destination}], **extra)

    upsert(locations["oaksdawn_hq"]["actions"], action("open_gorge_path", "東の峠を通りたいと頼む",
        [{"set_flag": "gorge_path_open"}], visible_after="greeted_walter", once="gorge_path_open", hidden_after="gorge_path_open",
        result_text="「峠を越えるだと？ ……いいだろう、守護団員に岩をどけさせよう。だが峡谷には近ごろ、岩でできた獣が出るそうだ。気をつけて行け」"))
    upsert(locations["oaksdawn_wall"]["actions"], action("oaksdawn_east_pass", "東の峠へ向かう",
        enabled=False, requirements={}, hidden_after="gorge_path_open",
        disabled_reason="峠は崩れた大岩で塞がれていて、今は通れない。"))
    upsert(locations["oaksdawn_wall"]["actions"], travel("oaksdawn_east_pass_open", "東の峠へ向かう", "gorge_entrance",
        visible_after="gorge_path_open",
        result_text="守護団員たちがどけた岩の間を抜け、東の峠へ踏み込んだ。"))
    locations["oaksdawn_wall"]["description_variants"] = [{"requirements": {"flag": "gorge_path_open"}, "text": OPEN_WALL}]
    locations["gorge_entrance"]["actions"] = [travel("gorge_to_rockfall", "落石の道を進む", "gorge_rockfall_path"),
        travel("gorge_to_wall", "城塞へ戻る", "oaksdawn_wall", result_variants=[dict(requirements={"flag": "gorge_path_open"}, text=OPEN_WALL)])]

    rows = [
        ("gorge_rockfall_path", ["gravel_beetle", "gravel_beetle"], "trash", 13,
         "甲虫と戦う", "剣を構えると、甲虫たちは殻を擦り合わせて威嚇しながら、じりじりと間合いを詰めてきた。",
         "岩陰を縫って抜ける", "甲虫が砂利を噛んでいる隙に、岩陰を縫って道を抜けた。", "足元の小石が崩れ、甲虫が一斉にこちらを向いた。",
         "甲虫は殻ごと崩れて、ただの砂利の山に戻った。"),
        ("gorge_giant_path", ["rock_giant", "stone_lizard"], "elite", 33,
         "岩の巨人と戦う", "岩の巨人が腕を振り上げると、峡谷全体が低く鳴った。トカゲが岩陰から跳び出してくる。",
         "巨人の足元をくぐり抜ける", "巨人が腕を振り上げた隙に、足の間を転がるようにくぐり抜けた。", "巨人の踵が地面を打ち、揺れに足を取られた。",
         "岩の巨人は崩れて、ただの岩山に戻った。崩れた胸の奥に、赤い果実が一つ埋まっている。"),
        ("gorge_worm_lair", ["earth_worm"], "boss", 17,
         "大ワームと戦う", "大ワームが鎌首をもたげ、土砂を噴き上げながら襲いかかってきた。",
         "地鳴りの合間を縫って駆け抜ける", "揺れが途切れた一瞬に、巣穴の間を一気に駆け抜けた。", "足元の地面が崩れ、ワームの巣穴へ滑り落ちた。",
         "大ワームは身をよじり、地響きとともに崩れ落ちた。あれほど続いていた地鳴りが、ふっと止んだ。"),
    ]
    for identifier, enemies, category, dc, fight, intro, sneak, success, failure, victory in rows:
        loc = locations[identifier]
        passed = f"passed_{identifier}"
        # Reuse the existing combat-defeat sentence template; no new narrative is authored.
        defeat = f"{loc['title']}で力尽きた。冒険はここで終わりを迎える。"
        loc["enemy_ids"] = enemies
        loc["combat"] = dict(enemy_ids=deepcopy(enemies), auto_start=False, encounter_class=category,
            boss=category == "boss", flee_allowed=False, intro_text=intro, victory_effects={"flags_set": [passed]},
            defeat_effects={"game_over": {"ending": "combat_defeat", "reason": defeat}},
            result_texts={"victory": victory, "defeat": defeat})
        loc["actions"] = [
            action(f"fight_{identifier}", fight, [{"start_combat": True}], hidden_after=passed, result_text=intro),
            action(f"sneak_{identifier}", sneak, hidden_after=passed, roll={"dice_type": "1d20+dex", "dc": dc},
                   success_effects=[{"set_flag": passed}], failure_effects=[{"start_combat": True},
                       *([{"enemy_first": True}] if category != "trash" else [])],
                   result_texts={"success": success, "failure": failure}),
        ]
    giant = locations["gorge_giant_path"]
    giant["combat"]["one_time_reward"] = dict(flag="reward_claimed:gorge_giant_path",
        shared_flags=["elite_fruit_claimed:rumbling_gorge"], blocking_flags=["elite_fruit_claimed:rumbling_gorge"],
        items=[dict(id="fruit_life", name="生命の果実", quantity=1)], steal_text="すれ違いざまに生命の果実をくすねた。")
    giant["actions"][1]["steal_encounter"] = "gorge_giant_path"
    locations["gorge_worm_lair"]["combat"]["one_time_reward"] = dict(flag="reward_claimed:gorge_worm_lair",
        items=[dict(id="elixir_end", name="鉄壁の霊薬", quantity=1)])
    # Optional combat gold is measured and fitted by scripts.balance.gorge using spec 031's cost rule.
    economics = ROOT / "eval/balance/gorge_economy.json"
    bonuses = json.loads(economics.read_text(encoding="utf-8"))["gold_bonus"] if economics.exists() else {}
    for identifier in BATTLES:
        locations[identifier]["combat"]["victory_gold_bonus"] = bonuses.get(identifier, 0)

    locations["gorge_rockfall_path"]["actions"] += [
        travel("rockfall_to_camp", "鉱夫の野営跡へ向かう", "gorge_miner_camp", visible_after="passed_gorge_rockfall_path"),
        travel("rockfall_to_cliff", "白い爪痕の崖へ向かう", "gorge_claw_cliff", visible_after="passed_gorge_rockfall_path"),
        travel("rockfall_to_entrance", "峡谷の入口へ戻る", "gorge_entrance", visible_after="passed_gorge_rockfall_path")]
    locations["gorge_miner_camp"]["actions"] = [
        action("rest_miner_camp", "竈に火を入れて休む", [{"restore_full": True}], once="rested_miner_camp", hidden_after="rested_miner_camp",
            result_text="竈に火を入れて、天幕の陰で短く眠った。地鳴りが、遠くで低く続いている。"),
        action("search_miner_camp", "鉱夫の荷物を調べる", [{"add_item": {"id": "trail_ration", "name": "携帯食", "quantity": 2}}],
            once="read_miner_diary", hidden_after="read_miner_diary",
            result_text="散らばった荷物の中から、携帯食と一冊の日記が出てきた。最後の頁には、震える字でこう書かれている。「……昨夜、峠の上を白いものが飛んでいった。その直後に山が崩れた。あれは竜だ。白い竜だ」"),
        travel("camp_to_rockfall", "落石の道へ戻る", "gorge_rockfall_path")]
    locations["gorge_claw_cliff"]["actions"] = [
        action("inspect_white_claw", "爪痕を調べる", once="saw_white_claw", hidden_after="saw_white_claw",
            result_text="爪痕の奥には、真夏でも溶けない白い霜がこびりついていた。この岩は、山崩れで落ちたのではない。何か巨大なものが、爪で引き裂いたのだ。"),
        travel("cliff_to_giant", "岩の巨人の通り道へ進む", "gorge_giant_path"),
        travel("cliff_to_rockfall", "落石の道へ戻る", "gorge_rockfall_path")]
    giant["actions"] += [travel("giant_to_worm", "峡谷の底へ下りる", "gorge_worm_lair", visible_after="passed_gorge_giant_path"),
        travel("giant_to_cliff", "白い爪痕の崖へ戻る", "gorge_claw_cliff", visible_after="passed_gorge_giant_path")]
    locations["gorge_worm_lair"]["actions"] += [
        action("elio_flood_worm", "エリオの水で巣穴を満たす", [{"set_flag": "passed_gorge_worm_lair"}],
            requirements={"companion_id": "hydromancer_elio"}, secret=True, hidden_after="passed_gorge_worm_lair",
            result_text="エリオが杖を掲げると、峡谷の湧き水が渦を巻いて巣穴へ流れ込んだ。地中で何かが苦しげにのたうち、地鳴りが遠ざかっていく。「今のうちだ、行こう！」"),
        action("gorge_to_village", "峡谷を抜けて村へ下る", [{"current_location": "village", "flags_set": ["reached_village"]}],
            visible_after="passed_gorge_worm_lair",
            result_text="峡谷を抜けると、眼下に麓の村が見えた。焼け跡の残る家々の外れ、避難所の裏手へと細い坂道が続いている。"),
        # K5–K6 is explicitly bidirectional; reuse the authored destination label.
        travel("worm_to_giant", "岩の巨人の通り道へ進む", "gorge_giant_path", visible_after="passed_gorge_worm_lair")]
    for identifier, name, description, hp, damage in ENEMIES:
        upsert(pack["enemies"], dict(id=identifier, name=name, description=description, hp=hp, max_hp=hp,
            attributes={}, element="earth", tags=["earth"], resistances={"physical": .6, "water": 1.5}, skills=[],
            combat={"defense": 0, "evade": 0, "basic_attack": {"name": "攻撃", "damage": damage, "accuracy": 70, "element": "physical"}},
            rewards={"gold": 0, "items": [], "flags": []}, image=f"/static/images/enemy_{identifier}.png"))
    add_elio(pack, locations)

    def add_clues(value: Any) -> None:
        if isinstance(value, dict):
            if "flags_count_gte" in value and "heard_old_soldier_ghost" in value["flags_count_gte"]["flags"]:
                value["flags_count_gte"]["flags"] = list(dict.fromkeys([*value["flags_count_gte"]["flags"], *CLUES]))
            for child in value.values():
                add_clues(child)
        elif isinstance(value, list):
            for child in value:
                add_clues(child)
    add_clues(locations["castle_report"])
    scene = next(s for s in pack["scenes"] if s["id"] == "oaksdawn")
    scene["next_scene_ids"] = list(dict.fromkeys([*scene["next_scene_ids"], "rumbling_gorge"]))
    scene["npc_ids"] = list(dict.fromkeys([*scene["npc_ids"], "elio"]))
    upsert(pack["scenes"], dict(id="rumbling_gorge", title="地鳴りの峡谷", description=DESCRIPTIONS["gorge_entrance"][1],
        location_ids=list(DESCRIPTIONS), npc_ids=[], enemy_ids=[], next_scene_ids=["oaksdawn", "village"]))
    annotate_risks(pack)
    changed_actions = {
        "oaksdawn_hq": {"open_gorge_path"},
        "oaksdawn_inn": {"talk_elio", "recruit_elio_gold", "recruit_elio_water", "recruit_elio_persuade"},
        "elf_spring": {"draw_spirit_spring_water"},
    }
    for identifier in [*DESCRIPTIONS, "oaksdawn_wall", *changed_actions]:
        loc = locations[identifier]
        if identifier in DESCRIPTIONS or identifier == "oaksdawn_wall":
            loc["connected_location_ids"] = list(dict.fromkeys([*loc.get("connected_location_ids", []),
                *[destination for entry in loc["actions"] for destination in movement_destinations(entry)]]))
        # Keep legacy choices synchronized without replacing unrelated authored choices.
        by_text = {entry["text"]: entry for entry in loc["actions"]
                   if identifier not in changed_actions or entry["id"] in changed_actions[identifier]}
        choices = loc.setdefault("choices", [])
        for entry in by_text.values():
            choice = {key: deepcopy(value) for key, value in entry.items() if key in {
                "text", "preview", "risk", "requirements", "visible_requirements", "visible_after", "hidden_after", "once", "secret", "disabled_reason"}}
            existing = next((i for i, c in enumerate(choices) if c["text"] == entry["text"]), None)
            if existing is None:
                choices.append(choice)
            else:
                choices[existing] = choice
        if identifier == "oaksdawn_wall":
            loc["choices"] = [{key: deepcopy(value) for key, value in entry.items() if key in {
                "text", "preview", "risk", "requirements", "visible_after", "hidden_after", "enabled", "disabled_reason"}}
                for entry in loc["actions"]]
    add_maps(pack, locations)
    pack["meta"]["rumbling_gorge_v035"] = True
    pack["meta"]["content_revision"] = max(pack["meta"].get("content_revision", ""), "2026-10-18-v035")


def add_elio(pack: dict[str, Any], locations: dict[str, Any]) -> None:
    portrait = "/static/images/npc_elio.png"
    upsert(pack["npcs"], dict(id="elio", name="水術士エリオ", description="流れの水術士。", image=portrait))
    inn = locations["oaksdawn_inn"]
    inn["npc_ids"] = list(dict.fromkeys([*inn.get("npc_ids", []), "elio"]))
    inn.setdefault("npc_requirements", {})["elio"] = {"not_flag": "recruited_elio"}
    inn["description_variants"] = [dict(requirements={"not_flag": "recruited_elio"}, text=INN_WITH_ELIO)]
    recruit = [{"set_companion": "hydromancer_elio"}, {"set_flag": "recruited_elio"}]
    common = dict(visible_after="met_elio", hidden_after="recruited_elio", portrait_image=portrait)
    entries = [
        action("talk_elio", "青い外套の青年に話しかける", once="met_elio", hidden_after="met_elio", portrait_image=portrait,
            result_text="「やあ。僕はエリオ、流れの水術士さ。東の峡谷の地鳴りを調べに来たんだけど、道が塞がれていてね。……君も峠を越えるつもりかい？」"),
        action("recruit_elio_gold", "傭兵として雇う（50G）", [{"gold_change": -50}, *deepcopy(recruit)], **common,
            requirements={"all": [{"gold_gte": 50}, {"not_flag": "recruited_elio"}]},
            result_text="「契約成立だね。水の届くところなら、どこでも役に立ってみせるよ」"),
        action("recruit_elio_water", "精霊の泉の水を渡す", [{"remove_item": {"name": "精霊の泉の水", "quantity": 1}}, *deepcopy(recruit)], **common,
            requirements={"all": [{"has_item": "精霊の泉の水"}, {"not_flag": "recruited_elio"}]},
            result_text="エリオは水差しの水を光にかざし、目を輝かせた。「精霊の泉の水だ……！ こんなものをもらったら、断れないよ。一緒に行こう」"),
        action("recruit_elio_persuade", "地鳴りの謎を一緒に調べようと誘う", **common, once="persuaded_elio",
            requirements={"not_flag": "recruited_elio"}, roll={"dice_type": "1d20+int", "dc": 13},
            success_effects=deepcopy(recruit), failure_effects=[], result_texts={
                "success": "「……面白い。君となら、あの地鳴りの正体に辿り着けそうだ」",
                "failure": "「悪いけど、僕はひとりで調べる方が性に合っていてね」"})]
    for entry in entries:
        if entry["id"].startswith("recruit_elio_"):
            entry["preview"] = "同行者にする（毎ラウンド水の刃、4ラウンドごとに被ダメージ半減）"
        upsert(inn["actions"], entry)
    upsert(pack["items"], dict(id="spirit_spring_water", name="精霊の泉の水", category="key", key_item=True,
        description="精霊の泉で汲んだ澄んだ水。ほのかに光を帯びている。"))
    upsert(locations["elf_spring"]["actions"], action("draw_spirit_spring_water", "泉の水を汲む",
        [{"add_item": {"id": "spirit_spring_water", "name": "精霊の泉の水", "quantity": 1}}],
        once="drew_spirit_spring_water", hidden_after="drew_spirit_spring_water",
        result_text="澄んだ泉の水を、空の水筒に汲んだ。水面が、ほのかに光っている。"))
    upsert(pack["companions"], dict(id="hydromancer_elio", name="水術士エリオ", image=portrait, description=ELIO_DESCRIPTION,
        round_start_effects=[dict(kind="damage_enemy", name="水刃", damage="2d3", element="water", target="weak_to:water"),
            dict(kind="received_damage_multiplier", name="水の帳", multiplier=.5, every_n_rounds=4)]))


def add_maps(pack: dict[str, Any], locations: dict[str, Any]) -> None:
    rows = [("K1", "峡谷の入口", "start", 8, 50, "gorge_entrance"),
            ("K2", "落石の道", "battle", 28, 50, "gorge_rockfall_path"),
            ("K3", "鉱夫の野営跡", "rest", 40, 18, "gorge_miner_camp"),
            ("K4", "白い爪痕の崖", "event", 55, 50, "gorge_claw_cliff"),
            ("K5", "岩の巨人の通り道", "battle", 72, 72, "gorge_giant_path"),
            ("K6", "峡谷の底", "boss", 88, 45, "gorge_worm_lair"), ("K7", "村への坂道", "exit", 96, 80, "")]
    nodes = [dict(id=i, label=label, kind=kind, x=x, y=y, location_ids=[loc] if loc else [],
                  description=locations[loc]["description"] if loc else label) for i, label, kind, x, y, loc in rows]
    edges = [{"from": a, "to": b, "action_id": identifier} for a, b, identifier in [
        ("K1", "K2", "gorge_to_rockfall"), ("K2", "K1", "rockfall_to_entrance"),
        ("K2", "K3", "rockfall_to_camp"), ("K3", "K2", "camp_to_rockfall"),
        ("K2", "K4", "rockfall_to_cliff"), ("K4", "K2", "cliff_to_rockfall"),
        ("K4", "K5", "cliff_to_giant"), ("K5", "K4", "giant_to_cliff"),
        ("K5", "K6", "giant_to_worm"), ("K6", "K5", "worm_to_giant"), ("K6", "K7", "gorge_to_village")]]
    upsert(pack["maps"], dict(id="rumbling_gorge", title="地鳴りの峡谷", nodes=nodes, edges=edges))
    city = next(m for m in pack["maps"] if m["id"] == "oaksdawn")
    upsert(city["nodes"], dict(id="gorge", label="地鳴りの峡谷", kind="exit", x=97, y=98,
        location_ids=[], description="地鳴りの峡谷", submap="rumbling_gorge", known_after="gorge_path_open"))
    city["edges"] = [e for e in city["edges"] if not (e["from"] == "G6" and e["to"] == "gorge")]
    edge = {"from": "G6", "to": "gorge", "action_ids": ["oaksdawn_east_pass", "oaksdawn_east_pass_open"]}
    if edge not in city["edges"]:
        city["edges"].append(edge)


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
