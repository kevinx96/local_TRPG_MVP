"""Apply the approved 029 text and state corrections to both scenario packs."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .castle_town import ROOT
from .risk_labels import expected_risk, _walk


DEAD_GOBLIN = "combat_defeated:lost_goblin_crossroads:goblin"
BOX_TEXT = "主を失った箱は、金貨の山の陰に転がっていた。蓋の留め金を外し、中身ごと持ち帰ることにした。"
RESULT_TEXTS = {
    "help_lost_goblin": "「分かった、取り返してやる」と告げると、ゴブリンの顔がぱっと明るくなった。「砦の鉄門で合言葉を聞かれたら、こう答えるんだ」背伸びして耳打ちすると、木々の向こうにそびえる砦を指さした。",
    "use_fort_healing_circle": "法陣の中央に立つと、淡い光が足元から立ちのぼり、傷口がみるみる塞がっていった。息が整ったところで、奥の階段を上る。",
    "fight_heat": "熱気の中へ踏み出すと、岩陰から二匹の熱岩トカゲが、溶岩の滴る口を開けて這い出してきた。",
    "fight_crystal": "剣を構えた瞬間、水晶が甲高く鳴り、紅晶のゴーレムと蒼晶の蝶、翠晶の蜘蛛が壁から剥がれるように姿を現した。",
    "fight_ash_wraiths": "霧を割って進むと、煤をまとった二つの人影がこちらへ向き直り、焦げた腕を伸ばしてきた。",
    "fight_ice_sentinels": "一歩近づくと、氷の番兵が軋む音を立てて槍を構え、扉の前を塞いだ。",
    "fight_forest_wolves": "荷車の前へ飛び出すと、森狼たちは低く唸り、狙いをこちらへ変えた。",
    "escort_mina": "「一緒に帰ろう」と手を差し出すと、ミーナは涙を拭って頷き、ローブの裾を握りしめて立ち上がった。",
    "leave_mina_wait": "「すぐ戻る。ここで待っていてくれ」と告げると、ミーナは小さく頷き、湯気の向こうで膝を抱え直した。",
    "take_ledge_path": "吊り橋を避け、崖に張り出した岩棚へ足をかけた。足元から熱風が吹き上げてくる。",
    "enter_dragon_nest": "灼熱の風に逆らって洞穴へ踏み込む。闇の奥で、巨大な何かがゆっくりと目を開けた。",
    "forge_ice_charm": "ローベルトは氷の結晶を炉の脇で慎重に削り、銀の枠にはめ込んだ。「ほらよ。冷気が逃げねえように仕上げておいた」手渡された護符は、ひやりと冷たい。",
    "accept_robin_goblin_quest": "「決まりね」ロビンは弓を背負い直して立ち上がった。「近道を知ってるの。ついてきて」彼女の案内で森の獣道を抜けると、木々の間にゴブリンの砦が黒くそびえていた。",
    "go_dragon_valley": "長老たちに見送られて村を出る。山道を登るにつれて空気は熱を帯び、やがて硫黄の霧が谷の入口を覆っていた。",
    "return_castle_from_village": "村を発ち、来た道を引き返す。森を抜けて城門をくぐると、見慣れた城下町の大通りが広がっていた。",
    "return_village": "城門を出て街道を下り、闇の森を抜けると、焼け跡の残る麓の村が見えてきた。",
}
CHECK_TEXTS = {
    "sneak_heat": ("赤く光る岩肌の影だけを選んで進み、トカゲたちの舌の音を背に回廊を抜けた。", "足元の小石が転がり、熱岩トカゲが一斉にこちらを向いた。"),
    "sneak_crystal": ("壁際で息を殺していると、水晶の震えは少しずつ静まり、形を取りかけた魔物たちも元の結晶へ戻っていった。その隙に回廊を抜ける。", "漏れた吐息に水晶が共鳴し、甲高い音とともに魔物たちが一斉に襲いかかってきた。"),
    "sneak_through_ash": ("硫黄の霧が濃くなる瞬間を待ち、亡霊たちの間を音もなく抜けた。", "霧が晴れた一瞬、煤の亡霊と目が合った。先に動いたのは向こうだった。"),
    "evade_ice_sentinels": ("二体の番兵が向きを変える一瞬を見計らい、凍った床を滑るように扉の内側へ抜けた。", "凍った床がきしみ、番兵の兜がこちらを向いた。冷たい槍が先に突き出される。"),
}
TURN_TEXTS = {
    "fort_second_guards_fight": "一階奥の角を曲がると、ゴブリンが槍を構え、弓ゴブリンが木箱の上へ飛び乗った。矢じりがこちらを向き、逃げ道を封じてくる。",
    "fort_second_bypass_failure": "身を隠した木箱が軋み、弓ゴブリンが振り向いた。退路へ矢が突き刺さり、ゴブリンが武器を抜いて迫る。",
    "fort_second_bypass_success": "巡回の隙を読み、積み上げられた樽の陰を抜けて二匹の背後を通過した。二階へ続く階段まで誰にも気づかれていない。",
    "fort_left_hound_ambush": "左の扉を押し開けた瞬間、鉄鎖が床を激しく擦った。暗がりで一対の目が光り、繋がれていた猛犬が鎖を引きちぎって襲いかかる。",
    "password_correct_king_ambush": "覚えた暗号を告げると鉄門が開く。だが財宝庫へ足を踏み入れた途端、玉座代わりの金貨の山からゴブリン王が立ち上がり、傍らの弓兵が退路へ照準を合わせた。",
    "ask_ian_legend_success": "イアンは遠い目をして、かつて麓の村で語られていた伝説の「氷の太刀」の話をしてくれた。「詳しいことは村の長老に聞くといい」",
    "ask_ian_legend_fail": "イアンは辛い記憶に触れたのか、顔をしかめて口を閉ざした。これ以上は聞き出せそうにない。",
    "ask_ian_advice": "イアンはため息をついた。「邪竜は過去に何度も倒されているが、そのたびに蘇る。国王にとっちゃ、討伐は定期的な仕事みたいなもんさ。言われた通りにしておくのが一番だ」",
    "invite_robin_success": "ロビンは笑って頷いた。「同行してもいいわよ。でもその前に、私の手伝いをしてくれない？王国商人の荷物が、闇の森のゴブリンに奪われたの」",
    "invite_robin_fail": "ロビンは肩をすくめた。「悪いけど、今は忙しいの。また今度ね」",
    "village_opening": "邪竜イグニスが潜む谷の麓、小さな村にたどり着いた。冷たい風が吹き抜ける中、村人たちは怯えた様子で暮らしている。邪竜に立ち向かう術を得るには、まず情報を集め、旅の支度を整える必要がありそうだ。",
    "visit_elder": "白髭を蓄えた長老は、あなたの決意を聞くと静かに頷いた。「イグニスは炎を操るが、その身は冷気に弱い。谷の冷気を宿した『氷の護符』があれば、奴の守りを崩せるはずじゃ。道具屋の店主が持っておるよ」",
}
ENTRIES = {
    "item_shop": "扉の鈴が鳴ると、棚の陰から金髪の少女サラが顔を出した。肩の上では小さな火コウモリ竜が、ぱちぱちと火の粉を散らしている。「いらっしゃいませ！今日は何をお探しですか？」",
    "magic_shop": "薬草と古い紙の匂いが漂う店内で、青いローブの銀髪の魔法使いが顔を上げた。棚の小瓶が、窓からの光を受けて淡く瞬いている。「何かお探しかな」",
    "alley": "昼の路地裏はひっそりとして、干された洗濯物が風に揺れているだけだ。奥へ進む理由も見当たらない。",
}


def choice(action: dict[str, Any]) -> dict[str, Any]:
    value = {key: deepcopy(child) for key, child in action.items()
             if key in {"text", "preview", "risk", "requirements", "secret", "visible_after", "hidden_after"}}
    if action.get("children"):
        value["children"] = [choice(child) for child in action["children"]]
    return value


def upgrade(pack: dict[str, Any]) -> None:
    locations = {loc["id"]: loc for loc in pack["locations"]}
    actions = {a["id"]: a for loc in locations.values() for a in _walk(loc.get("actions", []))}
    for action_id, text in RESULT_TEXTS.items():
        actions[action_id]["result_text"] = text
        actions[action_id].pop("silent", None)
    for action_id, (success, failure) in CHECK_TEXTS.items():
        actions[action_id]["result_texts"] = dict(success=success, failure=failure)
    renames = {"fight_heat": "熱岩トカゲと戦う", "fight_crystal": "水晶の魔物と戦う",
               "fight_ash_wraiths": "煤の亡霊と戦う", "fight_ice_sentinels": "氷の番兵と戦う",
               "fight_fort_second_guards": "ゴブリンたちと戦う", "fort_second_bypass": "見張りの二匹を迂回する",
               "return_inn_after_forest": "城下町へ戻る", "return_castle_from_village": "城下町に戻る",
               "return_forest_exit": "闇の森の出口へ向かう"}
    for identifier, text in renames.items():
        if actions[identifier].get("preview") == actions[identifier]["text"]:
            actions[identifier]["preview"] = ""
        actions[identifier]["text"] = text
        actions[identifier]["intent_keywords"] = [text]

    for identifier in ("accept_robin_goblin_quest", "enter_goblin_fort"):
        actions[identifier]["hidden_after"] = "defeated_goblin_king"
    present = {"all": [{"not_flag": DEAD_GOBLIN}, {"not_flag": "resolved_lost_goblin_box"}]}
    for identifier in ("help_lost_goblin", "ignore_lost_goblin"):
        actions[identifier].update(secret=True, requirements=deepcopy(present))
    for identifier in ("return_lost_goblin_box", "steal_lost_goblin_box"):
        actions[identifier]["hidden_after"] = DEAD_GOBLIN
    for identifier in ("lost_goblin_crossroads", "goblin_fort_chest_choice"):
        loc = locations[identifier]
        loc.setdefault("npc_requirements", {})["lost_goblin"] = deepcopy(present)
        loc.pop("portrait_image", None)
        loc["description_variants"] = [{"requirements": {"any": [{"flag": DEAD_GOBLIN}, {"flag": "resolved_lost_goblin_box"}]},
                                        "text": BOX_TEXT.split("。", 1)[0] + "。" if identifier.endswith("chest_choice") else ""}]
    loot = dict(id="take_abandoned_goblin_box", text="箱を持ち帰る", preview="", risk="判定不要",
                visible_after=DEAD_GOBLIN, once="resolved_lost_goblin_box", result_text=BOX_TEXT,
                effects=[{"add_item": {"name": "縮小の銃", "quantity": 1}}, {"set_flag": "stole_shrinking_gun"},
                         {"current_location": "lost_goblin_crossroads"}])
    chest = locations["goblin_fort_chest_choice"]["actions"]
    if not any(a["id"] == loot["id"] for a in chest):
        chest.append(loot)

    for identifier, text in ENTRIES.items():
        loc = locations[identifier]
        turns = loc.setdefault("hybrid", {}).setdefault("prepared_turns", [])
        if not any(t["id"] == identifier + "_opening" for t in turns):
            turns.insert(0, dict(id=identifier + "_opening", purpose="opening", action_id="go_" + identifier,
                                 outcome="neutral", trigger_keywords=[loc["title"].replace("王城の", ""), "到着"],
                                 draft=dict(gm_text=text, system_log="", state_delta={}, choices=[])))

    for source, identifier in (("castle", "return_village"), ("inn", "return_forest_exit")):
        locations[source]["actions"] = [a for a in locations[source]["actions"] if a["id"] != identifier]
        if not any(a["id"] == identifier for a in locations["castle_town"]["actions"]):
            locations["castle_town"]["actions"].append(actions[identifier])
    # Entering the exit is sufficient, even if the player has not returned to town yet.
    locations["forest_exit"].setdefault("entry_effects", [])
    if {"set_flag": "returned_from_forest"} not in locations["forest_exit"]["entry_effects"]:
        locations["forest_exit"]["entry_effects"].append({"set_flag": "returned_from_forest"})
    for identifier in ("return_castle_from_village", "return_inn_after_forest"):
        for effect in actions[identifier]["effects"]:
            if effect.get("current_location") in ("castle", "inn"):
                effect["current_location"] = "castle_town"
    actions["return_inn_after_forest"]["effects"] = [
        effect for effect in actions["return_inn_after_forest"]["effects"] if effect.get("set_flag") != "returned_from_forest"]
    departure = actions["go_dark_forest"]
    departure["effects"] = departure.pop("success_effects", departure.get("effects", []))
    departure.pop("failure_effects", None)
    departure.pop("roll", None)
    departure["risk"] = "判定不要"
    actions["ask_ian_legend"]["roll"] = {"dice_type": "1d20", "dc": 3}
    actions["continue_from_elf_spring"]["preview"] = "森の奥へ進む"
    forest_base = "森を抜けて村へ近づくにつれ、空が赤く染まり、焦げた匂いが濃くなる。村はすでに一面の火海となっていた。"
    actions["leave_forest_for_village"]["result_text"] = forest_base
    actions["leave_forest_for_village"]["result_variants"] = [
        {"requirements": {"companion_id": "blue_robed_mage"},
         "text": forest_base + "森を抜けたところで振り返ると、青いローブの魔法使いの姿が消えていた。"}]

    bindings = {"ask_ian_legend_success": ("inn", "ask_ian_legend", "success"),
                "ask_ian_legend_fail": ("inn", "ask_ian_legend", "failure"),
                "ask_ian_advice": ("inn", "ask_ian_advice", "neutral"),
                "invite_robin_success": ("inn", "invite_robin", "success"),
                "invite_robin_fail": ("inn", "invite_robin", "failure"),
                "village_opening": ("village", "", ""),
                "visit_elder": ("village", "ask_elder_weakness", "neutral")}
    for identifier, (location_id, action_id, outcome) in bindings.items():
        turns = locations[location_id].setdefault("hybrid", {}).setdefault("prepared_turns", [])
        if not any(turn["id"] == identifier for turn in turns):
            turns.append(dict(id=identifier, action_id=action_id, outcome=outcome,
                              purpose="choice_response" if action_id else "opening",
                              draft=dict(gm_text=TURN_TEXTS[identifier], system_log="", state_delta={}, choices=[])))
    locations["dragon_valley_loc"]["actions"] = []
    locations["dragon_valley_loc"]["choices"] = []

    removed = {"castle_departure_failure", "dragon_valley_ice_amulet", "dragon_valley_sword_attack", "dragon_valley_defend"}
    def update_text(value: Any) -> None:
        if isinstance(value, list):
            value[:] = [v for v in value if not isinstance(v, dict) or v.get("id") not in removed]
            for child in value:
                update_text(child)
        elif isinstance(value, dict):
            if value.get("id") in TURN_TEXTS and "draft" in value:
                value["draft"]["gm_text"] = TURN_TEXTS[value["id"]]
            if value.get("id") == "castle_departure_success":
                value["outcome"] = "neutral"
            if value.get("id") == "forest_exit_to_village":
                value["draft"]["gm_text"] = forest_base
            if value.get("action_id") == "ask_ian_legend" and "draft" in value:
                value["draft"].update(dice_type="1d20", dice_dc=3)
                value["rewrite_notes"] = [note.replace("1d30", "1d20") for note in value.get("rewrite_notes", [])]
            for key, child in value.items():
                if isinstance(child, str):
                    child = child.replace("城内の小さな鍛冶屋", "城下町の小さな鍛冶屋")
                    child = child.replace("1d30判定（DC4）", "1d20判定（DC3）")
                    if key == "title" and ("王城の" in child) and any(w in child for w in ("鍛冶屋", "宿屋", "魔法店", "道具屋", "路地裏")):
                        child = child.replace("王城の", "城下町の")
                    value[key] = child
                else:
                    update_text(child)
            if "preview" in value and value.get("preview") == value.get("text"):
                value["preview"] = ""
    update_text(pack)
    for loc in locations.values():
        for action in _walk(loc.get("actions", [])):
            label = expected_risk(action, loc, {})
            if label and (action["id"] == "ask_ian_legend" or action.get("roll", {}).get("dc", 0) >= 100):
                action["risk"] = label
        affected = set(RESULT_TEXTS) | set(CHECK_TEXTS) | set(renames) | {
            "enter_goblin_fort", "ignore_lost_goblin", "return_lost_goblin_box", "steal_lost_goblin_box",
            "go_dark_forest", "ask_ian_legend", "continue_from_elf_spring"}
        if loc["id"] == "castle" or any(a["id"] in affected for a in _walk(loc.get("actions", []))):
            loc["choices"] = [choice(a) for a in loc.get("actions", [])]
        for turn in loc.get("hybrid", {}).get("prepared_turns", []):
            if turn.get("draft", {}).get("choices") and loc["id"] in ("castle", "castle_town", "inn"):
                turn["draft"]["choices"] = deepcopy(loc["choices"])
    for source, old, new in (("castle", "village", None), ("inn", "forest_exit", None),
                             ("village", "castle", "castle_town"), ("forest_exit", "inn", "castle_town")):
        links = locations[source].get("connected_location_ids", [])
        locations[source]["connected_location_ids"] = list(dict.fromkeys(new if i == old else i for i in links if i != old or new))
    for identifier in ("village", "forest_exit"):
        if identifier not in locations["castle_town"]["connected_location_ids"]:
            locations["castle_town"]["connected_location_ids"].append(identifier)
    capital = next(m for m in pack["maps"] if m["id"] == "capital")
    for identifier, action_id, label in (("forest_exit", "return_forest_exit", "森の出口"), ("village", "return_village", "麓の村")):
        if not any(n["id"] == identifier for n in capital["nodes"]):
            capital["nodes"].append(dict(id=identifier, label=label, kind="exit", x=90 if identifier == "forest_exit" else 10,
                                         y=94, location_ids=[], description=locations[identifier]["description"]))
        if not any(e.get("action_id") == action_id for e in capital["edges"]):
            capital["edges"].append({"from": "C2", "to": identifier, "action_id": action_id,
                                     "visible_after": actions[action_id]["visible_after"]})
        next(n for n in capital["nodes"] if n["id"] == identifier)["known_after"] = actions[action_id]["visible_after"]
    pack["meta"]["content_revision"] = "2026-10-13-v029-playtest-fixes"


def main() -> None:
    for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / filename
        pack = json.loads(path.read_text(encoding="utf-8"))
        upgrade(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
