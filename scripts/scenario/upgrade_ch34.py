from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .upgrade_forest import ROOT, action, move, observe, upsert

BETRAYAL = "heard_xanxus_betrayal"
STOLEN = "「約束の品はもらっていくぞ」ザンザスの声とともに、紅竜の心臓の炎が宙へ吸い上げられていった。"
ANGER = "遠くで、ザンザスの怒りに満ちた咆哮が聞こえた"
WARLOCK = "青い光とともにワーロックが現れた。「先へ進む前に伝えておく。ザンザスは白竜と密約を交わしていた。紅竜の心臓と引き換えに、王国の半分をもらう約束だったそうだ。……気をつけろ」そう言い残し、彼は再び姿を消した。"
REMOVE_SEED = [{"remove_item": {"name": "火種", "quantity": 1, "force": True}},
               {"set_flag": "fire_seed_removed"}, {"set_flag": BETRAYAL}]
CLEANSE = "聖なる光が胸の火種を包み込み、その炎が弱まっていく。ザンザスが怒りに吠える。『小癪な……火種を消される前に、力ずくで奪うまでだ！』"


def fix_ch34(pack: dict[str, Any]) -> None:
    loc = {l["id"]: l for l in pack["locations"]}
    cameo = loc["valley_nest_gate"]["entry_effects"][0]["branch"]["then"][1]["branch"]["else"][0]
    if not pack["meta"].get("npc_combat_v045"):
        cameo["branch"]["requirements"] = {"flag": "warlock_rescue_available"}
    actions = {a["id"]: a for a in loc["xanxus_at_nest"]["actions"]}
    actions["call_warlock"]["requirements"] = {"flag": "warlock_rescue_available"}
    actions["cleanse_fire_seed"]["result_text"] = CLEANSE
    next(m for m in pack["milestones"] if m["level"] == 5)["trigger_flag"] = "nest_event_seen"
    pack["meta"]["content_revision"] = max(pack['meta'].get('content_revision', ''), '2026-10-12-v021-ch34')


def branch(requirements: dict[str, Any], yes: list, no: list | None = None) -> dict[str, Any]:
    return {"branch": {"requirements": requirements, "then": yes, "else": no or []}}


def upgrade(pack: dict[str, Any]) -> None:
    if pack["meta"].get("chapter34_v4"):
        fix_ch34(pack)
        return
    pack["meta"].update(chapter34_v4=True, content_revision="2026-10-12-v019-ch34")
    loc = {l["id"]: l for l in pack["locations"]}

    def location(identifier: str, title: str, description: str, scene: str, background: str, **extra: Any) -> dict[str, Any]:
        record = dict(id=identifier, title=title, description=description, scene_id=scene,
                      background_image=f"/static/images/{background}.png", actions=[], npc_ids=[], enemy_ids=[],
                      connected_location_ids=[], **extra)
        upsert(pack["locations"], record)
        loc[identifier] = record
        owner = next(s for s in pack["scenes"] if s["id"] == scene)
        if identifier not in owner["location_ids"]:
            owner["location_ids"].append(identifier)
        return record

    refuge = loc["village"]
    village_scene = next(s for s in pack["scenes"] if s["id"] == "village")
    if "village" not in village_scene["location_ids"]:
        village_scene["location_ids"].append("village")
    refuge.update(title="麓の村・避難所", description="村外れの石造りの集会所に、焼け出された村人たちが身を寄せ合っている。長老が人々を励まし、行商人の荷車の周りには小さな人だかりができている。")
    refuge["entry_effects"] = [branch({"flag": "riku_abandoned"}, [{"set_flag": "elder_mourning"}])]
    refuge["entry_text"] = "長老は焼け跡を見つめ、黙り込んでいる"
    refuge["narrate_entry"] = True
    elder = next(n for n in pack["npcs"] if n["id"] == "elder")
    elder["description_variants"] = [dict(requirements={"flag": "riku_abandoned"},
        text=elder["description"] + "長老は焼け跡を見つめ、黙り込んでいる")]
    refuge["actions"] += [action("rest_at_refuge", "避難所で休ませてもらう（5G）",
        [{"gold_change": -5}, {"restore_full": True}], requirements={"gold_gte": 5},
        result_text="村人が分けてくれた粥をすすり、毛布にくるまって眠った。"),
        action("return_riku", "リクを長老に会わせる", [{"add_item": {"name": "竜の秘薬", "quantity": 2}},
            {"set_flag": "heard_treaty_lore"}], visible_after="riku_rescued", once="riku_returned",
            result_text="「リク！……よく無事で」長老は孫を抱きしめ、深く頭を下げた。「礼をさせてくれ。これは村に伝わる竜の秘薬じゃ。それと……この話も伝えておこう。昔、白き竜がこの村に霜を降らせたことがある、と」")]
    upsert(pack["npcs"], dict(id="riku", name="長老の孫リク", description="村の長老の孫。火事の夜、家に取り残されていた。", image="/static/images/npc_riku.png"))
    refuge["npc_ids"].append("riku")
    refuge.setdefault("npc_requirements", {})["riku"] = {"flag": "riku_rescued"}
    upsert(pack["items"], dict(id="dragon_elixir", name="竜の秘薬", description="村に代々伝わる秘薬。竜の鱗を煎じたものだという。",
        effect="HP を最大値の 50% 回復", category="consumable", combat=dict(kind="heal", max_hp_ratio=.5, consumable=True)))
    house = location("burning_house", "燃える民家の前", "崩れかけた民家の奥から、子どもの泣き声が聞こえる。入口は燃える梁で塞がれている。", "village", "bg_burning_house",
                     entry_effects=[{"set_flag": "found_burning_house"}])
    house.update(entry_text=house["description"], narrate_entry=True)
    rescued = [{"set_flag": "riku_rescued"}, {"current_location": "village_frozen_clue"}]
    for identifier, text, attr, damage, success, failure in [
        ("break_burning_beam", "燃える梁を叩き壊す", "str", 5, "梁を蹴り砕いて飛び込むと、煙の中で小さな男の子がうずくまっていた。", "梁は思ったより重く、熱に腕を焼かれた。"),
        ("climb_to_window", "裏手の窓からよじ登る", "dex", 3, "壁をよじ登って窓から入り込み、男の子を抱えて外へ飛び降りた。", "足を滑らせ、焼けた壁にしたたかに打ちつけた。")]:
        entry = action(identifier, text, roll=dict(dice_type=f"1d20+{attr}", dc=13),
                       success_effects=deepcopy(rescued), failure_effects=[{"hp_change": -damage}], result_texts=dict(success=success, failure=failure))
        entry["risk"] = "1d20判定（DC13）"
        house["actions"].append(entry)
    ice_names = [next(i["name"] for i in pack["items"] if i["id"] == identifier)
                 for identifier in ("ice_charm", "activated_ice_charm", "ice_iron_greatsword", "ice_katana", "ice_crystal")]
    house["actions"] += [action("douse_with_ice", "冷気で炎を鎮める", deepcopy(rescued),
        requirements={"any": [{"has_item": name} for name in ice_names] + [{"character_id": "mage"}]},
        result_text="冷気を放つと炎が一瞬で退き、その隙に男の子を連れ出した。"),
        action("leave_burning_house", "先を急ぐ", [{"set_flag": "riku_abandoned"}, {"current_location": "village_frozen_clue"}],
               result_text="泣き声を背に、燃える通りを駆け抜けた。")]
    house["objects"] = [observe("house_beam", "燃える梁", "梁の根元が焼け落ちかけている。力を込めれば折れそうだ。", [])]
    for identifier in ("village_fire_slime", "village_fire_elemental"):
        loc[identifier]["combat"]["victory_effects"]["current_location"] = "burning_house"

    def redirect(value: Any) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                if k in {"current_location", "next_location"} and v == "dragon_valley_loc":
                    value[k] = "valley_entrance"
                elif k == "connected_location_ids":
                    value[k] = ["valley_entrance" if x == "dragon_valley_loc" else x for x in v]
                else:
                    redirect(v)
            if "flags_set" in value and "entered_dragon_valley" in value["flags_set"]:
                value["flags_set"].remove("entered_dragon_valley")
        elif isinstance(value, list):
            for v in value:
                redirect(v)
    redirect(pack)
    entrance = location("valley_entrance", "竜の谷・入口", "硫黄の霧が立ち込める谷の入口。霧の中で、煤をまとった人影がゆらゆらと揺れている。", "dragon_valley", "bg_dragon_valley",
                        entry_effects=[{"set_flag": "entered_dragon_valley"}])
    bridge = location("valley_lava_bridge", "溶岩の吊り橋", "煮え立つ溶岩の川に、古い吊り橋が一本だけ架かっている。板は焦げ、縄は今にも切れそうだ。", "dragon_valley", "bg_lava_bridge")
    ledge = location("valley_ledge", "岩棚の迂回路", "溶岩の川を見下ろす狭い岩棚。岩陰から、翼の生えた小型の竜が首をもたげた。", "dragon_valley", "bg_lava_bridge")
    gate = location("valley_nest_gate", "竜の巣の前", "巨大な洞穴の入口から、灼熱の風が吹きつけてくる。奥で、何か巨大なものが重く息をしている。", "dragon_valley", "bg_dragon_nest")
    gate["actions"] = [move("enter_dragon_nest", "竜の巣へ踏み込む", "dragon_valley_loc", start_combat=True)]
    gate["entry_effects"] = [branch({"not_flag": "nest_event_seen"}, [
        {"set_flag": "nest_event_seen"}, branch({"all": [{"flag": "accepted_fire_seed"}, {"not_flag": "fire_seed_removed"}]},
            [{"current_location": "xanxus_at_nest"}], [branch({"flag": "warlock_rescue_available"}, [{"current_location": "warlock_at_nest"}])])])]
    for record, enemy, destination in ((entrance, "ash_wraith", "valley_lava_bridge"), (ledge, "lava_drake", "valley_nest_gate")):
        record["enemy_ids"] = [enemy, enemy]
        record["combat"] = dict(auto_start=record is ledge, enemy_ids=[enemy, enemy], flee_allowed=False, encounter_class="elite",
            victory_effects={"current_location": destination}, defeat_effects=dict(game_over=dict(reason="竜の谷で力尽きた。", ending="dragon_valley_defeat")),
            result_texts=dict(victory=loc[destination]["description"], defeat="竜の谷で力尽きた。"))
    entrance["actions"] = [action("fight_ash_wraiths", "戦う", [{"start_combat": True}]),
        action("sneak_through_ash", "霧に紛れてやり過ごす", roll=dict(dice_type="1d20+dex", dc=14),
               success_effects=[{"current_location": "valley_lava_bridge"}], failure_effects=[{"start_combat": True}, {"enemy_first": True}])]
    entrance["actions"][1]["risk"] = "1d20判定（DC14）"
    bridge["actions"] = [action("cross_lava_bridge", "吊り橋を渡る", roll=dict(dice_type="1d20+dex", dc=12,
        dc_overrides=[dict(requirements={"flag": "bridge_safe_side_known"}, dc=6)]),
        success_effects=[{"current_location": "valley_nest_gate"}], failure_effects=[{"hp_change": -6}, {"current_location": "valley_nest_gate"}],
        result_texts=dict(success="揺れる板を一枚ずつ踏みしめ、向こう岸へたどり着いた。", failure="板が一枚抜け落ち、熱風に焼かれながら必死にしがみついて渡りきった。")),
        move("take_ledge_path", "岩棚の迂回路を進む", "valley_ledge")]
    bridge["actions"][0]["risk"] = "1d20判定（DC12）"
    bridge["objects"] = [observe("bridge_ropes", "焦げた縄", "右側の縄はまだしっかりしている。右端を伝えば安全に渡れそうだ。",
        [{"set_flag": "bridge_safe_side_known"}], dict(dice_type="1d20+wis", dc=10))]
    nest = location("xanxus_at_nest", "竜の巣の前・ザンザス", "炎の中からザンザスが現れた。あなたの胸の火種が、呼応するように熱を帯びる。「よく来た。紅竜を倒したら、その心臓を我に捧げよ。火種を持つ限り、お前は我に逆らえぬ」", "dragon_valley", "bg_dragon_nest")
    nest.update(npc_ids=["xanxus"], portrait_image="/static/images/npc_xanxus.png")
    nest.update(entry_text=nest["description"], narrate_entry=True, entry_effects=[{"set_flag": "xanxus_nest_seen"}])
    nest["actions"] = [action("obey_xanxus_core", "従う", [{"set_flag": "promised_core_to_xanxus"}, {"current_location": "valley_nest_gate"}], result_text="ザンザスは満足げに笑い、炎とともに消えた。"),
        action("cleanse_fire_seed", "聖なる力で火種を浄化する", [branch({"has_item": "聖水"}, [{"remove_item": {"name": "聖水", "quantity": 1}}], [{"mp_change": -6}]),
            {"current_location": "xanxus_phantom_battle"}, {"start_combat": True}],
            requirements={"any": [{"has_item": "聖水"}, {"all": [{"character_id": "cleric"}, {"mp_gte": 6}]}]},
            result_text=CLEANSE),
        action("call_warlock", "ワーロックの名を呼ぶ", deepcopy(REMOVE_SEED) + [{"current_location": "valley_nest_gate"}],
            requirements={"flag": "warlock_rescue_available"},
            result_text="青い光が走り、ワーロックがあなたの前に立った。彼の杖が火種を凍らせて砕く。「ザンザス、もう白竜の手先は終わりだ」ザンザスは舌打ちし、炎の中へ消えた。ワーロックは振り返る。「あの骸骨は、白竜と密約を交わしていた。紅竜の心臓と引き換えに、王国の半分をもらう約束だったそうだ」")]
    phantom = location("xanxus_phantom_battle", "ザンザスの分身", "ザンザスが自らの炎を分けて作り出した分身。本体ほどの力はない。", "dragon_valley", "bg_dragon_nest")
    phantom["enemy_ids"] = ["xanxus_phantom"]
    phantom["combat"] = dict(auto_start=True, enemy_ids=["xanxus_phantom"], flee_allowed=False, encounter_class="boss",
        victory_effects=deepcopy(REMOVE_SEED) + [{"current_location": "valley_nest_gate"}],
        defeat_effects=dict(hp=1, flags_set=["promised_core_to_xanxus"], current_location="valley_nest_gate"),
        result_texts=dict(victory="分身が崩れ落ちる間際、ザンザスの声が響いた。「白竜め……約束が違うではないか……」", defeat="炎に呑まれ、気がつくと巣の前に倒れていた。胸の火種は、まだ脈打っている。"))
    cameo = location("warlock_at_nest", "竜の巣の前", WARLOCK, "dragon_valley", "bg_dragon_nest", entry_effects=[{"set_flag": BETRAYAL}], entry_text=WARLOCK)
    cameo["portrait_image"] = next(n["image"] for n in pack["npcs"] if n["id"] == "blue_robed_mage")
    cameo["narrate_entry"] = True
    cameo["actions"] = [move("continue_after_warlock", "先へ進む", "valley_nest_gate")]
    # Keep the reward in the victory delta so replay and combat share the same source.
    claim = {"all": [{"flag": "promised_core_to_xanxus"}, {"not_flag": "fire_seed_removed"}]}
    core = dict(id="red_dragon_core", name="紅竜の炎核", quantity=1)
    victory = [{"set_flag": "defeated_ignis"}, branch(claim, [{"set_flag": "xanxus_took_core"}], [{"add_item": core}]), {"current_location": "ignis_last_breath"}]
    loc["dragon_valley_loc"]["combat"]["victory_effects"] = deepcopy(victory)
    loc["dragon_valley_loc"]["actions"][0]["success_effects"] = deepcopy(victory)
    loc["ignis_last_breath"]["entry_effects"] = [branch({"flag": "xanxus_took_core"}, [{"set_flag": "xanxus_core_scene_seen"}])]
    loc["ignis_last_breath"]["entry_text"] = STOLEN
    loc["ignis_last_breath"]["narrate_entry"] = True
    loc["ignis_purified"]["entry_effects"] = [branch(claim, [{"set_flag": "xanxus_denied_core"}])]
    loc["ignis_purified"]["entry_text"] = ANGER
    loc["ignis_purified"]["narrate_entry"] = True
    loc["cave_hot_spring"]["background_image"] = "/static/images/bg_hot_spring.png"

    for identifier, name, description, hp, damage, element, resistances, evade, skills in [
        ("ash_wraith", "煤の亡霊", "竜の炎に焼かれた者たちの怨念が、煤となって漂う亡霊。", 18, "1d4", "dark", {"holy": 1.6, "physical": .5, "fire": .5}, 0,
         [dict(id="ash_embrace", name="煤の抱擁", kind="attack", damage="1d4", accuracy=75, element="fire", ai_weight=2,
               on_hit_status=dict(id="suffocation", name="窒息", damage="1", remaining_rounds=2)),
          dict(id="resentment", name="怨嗟", kind="attack", damage="1d5", accuracy=75, element="dark", ai_weight=1)]),
        ("lava_drake", "溶岩ドレイク", "竜の谷に棲む小型の竜。イグニスの眷属とされる。", 20, "1d5", "fire", {"ice": 1.5, "fire": .5}, 8,
         [dict(id="lava_breath", name="溶岩の吐息", kind="attack", damage="1d6", accuracy=80, element="fire", ai_weight=2),
          dict(id="hook_claw", name="鉤爪", kind="attack", damage="1d5", accuracy=85, element="physical", ai_weight=1)]),
        ("xanxus_phantom", "ザンザスの分身", "ザンザスが自らの炎を分けて作り出した分身。", 110, "1d8", "fire", {"ice": 1.5, "holy": 1.5, "fire": .5}, 3,
         [dict(id="flame_vortex", name="火炎旋渦", kind="field", round_damage="2", element="fire", ai_weight=2),
          dict(id="summon_meteor", name="隕石召喚", kind="attack", damage="2d8", accuracy=85, element="fire", ai_weight=3)])]:
        upsert(pack["enemies"], dict(id=identifier, name=name, description=description, hp=hp, max_hp=hp, element=element,
            attributes=dict(str=12, dex=10, int=14, end=10), combat=dict(basic_attack=dict(name=name, damage=damage, accuracy=80, element=element), defense=0, evade=evade),
            resistances=resistances, skills=skills, rewards=dict(gold=0, items=[], flags=[]), image=f"/static/images/enemy_{identifier}.png"))

    pack["quests"][-1:-1] = [dict(id="side_riku", title="燃える家の子ども", description="燃える民家に子どもが取り残されている。", kind="side", start_flag="found_burning_house",
        complete_flags=["riku_returned"], fail_flags=["riku_abandoned"], stages=[dict(text="子どもを助け出す", done_flag="riku_rescued"), dict(text="避難所の長老のもとへ連れて行く", done_flag="riku_returned")]),
        dict(id="fire_seed_curse", title="火種の呪い", description="ザンザスに植え付けられた火種が、胸の中で脈打っている。", kind="side", start_flag="accepted_fire_seed",
             complete_flags=["fire_seed_removed"], fail_flags=["xanxus_took_core"], stages=[dict(text="火種を取り除く方法を探す", done_flag="fire_seed_removed")])]
    def clues(value: Any) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                if k == "clue_flags" or (k in {"flags", "start_flag"} and isinstance(v, list) and "heard_treaty_lore" in v):
                    if BETRAYAL not in v:
                        v.append(BETRAYAL)
                else:
                    clues(v)
        elif isinstance(value, list):
            for v in value:
                clues(v)
    clues(pack)
    for map_id, title, rows, links in [
        ("burning_village", "炎上する村", [
            ("V1", "村の入口", "start", 10, 55, ["village_approach"]),
            ("V2", "燃える大通り", "battle", 28, 55, ["village_fire_slime", "village_fire_elemental", "burning_house"]),
            ("V3", "炎の中の結氷", "event", 46, 55, ["village_frozen_clue"]),
            ("V4", "凍結した路地", "battle", 62, 25, ["ice_elemental_encounter"]),
            ("V5", "氷霜の巨狼", "boss", 77, 25, ["frost_wolf_battle"]),
            ("V6", "砕けた氷の太刀", "event", 92, 25, ["ian_ice_katana_aftermath"]),
            ("V7", "燃える街道", "event", 62, 55, ["xanxus_confrontation", "xanxus_battle", "xanxus_ultimatum", "warlock_rescue_battle"]),
            ("V8", "避難所", "rest", 62, 85, ["village"])],
         [("V1", "V2", "approach_burning_village_carefully"), ("V2", "V3", "leave_burning_house"), ("V3", "V4", "investigate_frozen_village"), ("V4", "V5", "bypass_ice_elemental"),
          ("V5", "V6", ""), ("V3", "V7", "skip_frozen_clue_before_xanxus"), ("V3", "V8", "visit_village"), ("V8", "V3", "return_frozen_clue"), ("V6", "V8", "visit_village"), ("V7", "V3", "accept_xanxus_fire_seed")]),
        ("dragon_valley", "竜の谷", [
            ("D1", "谷の入口", "battle", 10, 50, ["valley_entrance"]), ("D2", "溶岩の吊り橋", "event", 35, 50, ["valley_lava_bridge"]),
            ("D2b", "岩棚の迂回路", "battle", 50, 80, ["valley_ledge"]),
            ("D3", "竜の巣の前", "event", 65, 50, ["valley_nest_gate", "xanxus_at_nest", "xanxus_phantom_battle", "warlock_at_nest"]),
            ("D4", "竜の巣", "boss", 90, 50, ["dragon_valley_loc", "ignis_last_breath", "ignis_purified"])],
         [("D1", "D2", "sneak_through_ash"), ("D2", "D3", "cross_lava_bridge"), ("D2", "D2b", "take_ledge_path"), ("D2b", "D3", ""), ("D3", "D4", "enter_dragon_nest")])]:
        upsert(pack["maps"], dict(id=map_id, title=title,
            nodes=[dict(id=i, label=t, kind=k, x=x, y=y, location_ids=ids, description=loc[ids[0]]["description"]) for i, t, k, x, y, ids in rows],
            edges=[{"from": a, "to": b, **({"action_id": c} if c else {})} for a, b, c in links]))
    fix_ch34(pack)


if __name__ == "__main__":
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        upgrade(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
