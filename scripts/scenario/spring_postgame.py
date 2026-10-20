"""048: one spring rest and data-driven post-Ignis guidance (offline, idempotent)."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
POSTGAME = {"any": [{"flag": "defeated_ignis"}, {"flag": "ignis_purified"}]}
BEFORE = {"all": [{"not_flag": "defeated_ignis"}, {"not_flag": "ignis_purified"}]}
GUIDANCE = {
    "ignis_last_breath": ("return_to_castle_report",),
    "ignis_purified": ("return_to_castle_report",),
    "royal_gate": ("enter_festival_town",),
    "festival_town": ("go_report_hall", "go_general_mansion", "request_king_audience"),
    "castle_report": ("report_normally", "report_with_evidence"),
    "mansion_garden": ("sneak_into_mansion", "robin_picks_lock"),
    "mansion_corridor": ("fight_ice_sentinels", "evade_ice_sentinels", "pass_cleared_sentinels"),
    "mansion_study": ("take_draco_journal", "leave_mansion_study"),
    "king_private_room": ("confide_in_king", "leave_king_room"),
    "forge": ("return_castle_from_forge",),
    "magic_shop": ("return_castle_from_magic_shop",),
    "inn": ("return_castle_from_inn",),
    "item_shop": ("return_castle_from_item_shop",),
    "alley": ("return_castle_from_alley",),
    "alley_night": ("leave_night_alley",),
    "alley_after": ("return_castle_after_curse",),
    "castle": ("go_castle_town",),
    "castle_town": ("return_castle_from_town",),
}
HIDE = {
    "castle": ("ask_king_info", "ask_general_advice", "check_supplies"),
    "forge": ("ask_blacksmith_weakness",),
    "magic_shop": ("ask_blue_mage_rumor",),
    "village": ("ask_elder_weakness",),
}
# Shops and unrelated quests remain available.
CHATS = (
    ("castle", "king", "国王"), ("castle", "general", "将軍ドラコ"),
    ("castle_town", "gald", "行商人ガルド"), ("festival_town", "gald", "行商人ガルド"),
    ("forge", "blacksmith", "鍛冶師ローベルト"), ("magic_shop", "warlock", "青いローブの魔法使い"),
    ("magic_shop", "mina", "ミーナ"), ("inn", "ian", "イアン"), ("inn", "robin", "ロビン"),
    ("item_shop", "sarah", "サラ"), ("alley_night", "suspicious_merchant", "怪しい商人"),
    ("village", "elder", "長老"), ("village", "shopkeeper", "道具屋の店主"),
)
CHAT_TEXTS: dict[tuple[str, str], tuple[str, str, str]] = {
    ("castle", "king"): (
        "玉座の国王に戦いの首尾を伝える",
        "老王は深く息を吐き、疲れた目で頷いた。「……そうか、イグニスは斃れたか。十年の災厄を断ち切ったそなたの武勲、後に凱旋の間で正式に労おう」",
        "老王は目を見開き、震える手で胸を押さえた。「……なんと、イグニスが正気を取り戻したと申すか。古の盟約がまだ消えておらなんだとは……！」",
    ),
    ("castle", "general"): (
        "佇むドラコ将軍に勝利を告げる",
        "ドラコは静かに拍手を送り、穏やかに微笑んだ。「見事だ。赤き竜の焔が消え、谷の均衡もこれで変わるだろう。……まずは凱旋の間で胸を張るといい」",
        "ドラコは一瞬だけ目を細め、すぐに称賛の笑みを浮かべた。「ほう、殺さずに呪いを解いたか。想定外の結末だが……見事な手並みだ。陛下も喜ばれよう」",
    ),
    ("castle_town", "gald"): (
        "荷を広げるガルドに声をかける",
        "ガルドは相好を崩して肩を叩いてきた。「よう、命の恩人！あんたが赤竜を討ったって噂で持ちきりだぜ。王城への報告が済んだら一杯おごらせてくれよな！」",
        "ガルドは目を丸くして口笛を吹いた。「へえっ、あの恐ろしい赤竜を生かしたまま鎮めちまったのかい！あんたらしいが、商売人としては腰が抜ける話だぜ」",
    ),
    ("festival_town", "gald"): (
        "屋台脇のガルドと祝祭を語らう",
        "ガルドは賑わう大通りを見渡して笑った。「見ろよこの騒ぎ！赤竜が倒れて街道の封鎖も解けるってんで、商人連中も大喜びさ。あんたは国の救い主だぜ！」",
        "ガルドは祝祭の旗を見上げて苦笑した。「街じゃ討伐祝いのつもりで騒いでるが、まさか竜と和解して帰ってくるとはな。王様への報告、どんな顔されるか楽しみだぜ」",
    ),
    ("forge", "blacksmith"): (
        "炉の前に立つローベルトを見る",
        "ローベルトは黙って得物の刃筋を検め、短く鼻を鳴らした。「……竜の鱗を断ってなお折れなかったか。よく振ったな。手直しが要るならいつでも置いていけ」",
        "ローベルトは刃に血脂が焼き付いていないのを見て眉を上げた。「……竜を斬らずに鎮めたのか。妙な戦い方をする奴だが、得物を大事にする腕前は気に入った」",
    ),
    ("magic_shop", "warlock"): (
        "魔道書を閉じるワーロックを見る",
        "ワーロックは静かに茶を啜り、値踏みするようにこちらを見た。「……赤竜の魔力反応が完全に消えたな。だが、これで全てが片付いたと気を抜くなよ」",
        "ワーロックは珍しく感嘆の息を漏らした。「……ほう、暴走の呪詛だけを剥がしてイグニスを生かしたか。あの竜の証言があれば、十年前の闇も暴けるかもしれんな」",
    ),
    ("magic_shop", "mina"): (
        "目を輝かせるミーナに手を振る",
        "ミーナは杖を抱えてぴょんぴょん跳ねた。「すごいです！あのイグニスを倒しちゃうなんて、まるでおとぎ話の英雄ですね！お城での報告、頑張ってください！」",
        "ミーナは両手を合わせて顔をほころばせた。「赤竜さんを倒さずに正気に戻してあげたんですね！きっと優しい竜さんに戻れたはずです、本当にすごいです！」",
    ),
    ("inn", "ian"): (
        "杯を磨くイアンに近況を話す",
        "イアンは杯を磨く手を止め、懐かしそうに目を細めた。「イグニスを討ったか。麓で槌を振るってた頃には、こんな日が来るとは思わなかったよ。今夜はゆっくりしていけ」",
        "イアンは目を丸くし、やがて笑った。「竜を正気に戻した、か。鍛冶屋だった頃に聞いた古い盟約の話、まんざら作り話でもなかったんだな」",
    ),
    ("inn", "robin"): (
        "窓辺のロビンに首尾を明かす",
        "ロビンは肩をすくめ、不敵に口の端を上げた。「本当に赤竜を仕留めてくるとはね。街はお祭り騒ぎだけど、あんたを狙う妙な視線には気をつけなよ」",
        "ロビンは驚いたように瞬きし、くすっと笑った。「へえ、殺さずに手懐けてきたってわけ？あんた、見た目よりずっとお人好しだね。嫌いじゃないさ」",
    ),
    ("item_shop", "sarah"): (
        "子竜を抱くサラに微笑みかける",
        "サラは小竜の頭を撫でながら少し複雑な顔をした。「無事でよかった！……大きな赤い竜さん、もう苦しまずに眠れたならいいんだけどな」",
        "サラはぱっと笑顔になり、小竜も嬉しそうに鳴いた。「本当！？赤い竜さん、元気になったんだね！いつかこの子と一緒に会いに行けたらいいなあ！」",
    ),
    ("alley_night", "suspicious_merchant"): (
        "暗がりの商人の様子を窺う",
        "フードの奥で男が低く喉を鳴らした。「ヒヒ……赤竜の首級とは恐れ入りましたねえ。王城でどんな褒美が待っているか、せいぜい楽しみになさることです」",
        "男はフードの陰でピクリと肩を揺らした。「……ほう、あの狂竜を生かして鎮めましたか。余計な真似を……いやいや、お見事な慈悲でございますねえ、ヒヒ」",
    ),
    ("village", "elder"): (
        "杖をつく長老に谷の結末を語る",
        "長老は深い皺を刻んだ顔で静かに合掌した。「……そうか、ついに赤竜の焔が消えたか。これで谷の脅威も去ったが、心なしか風が冷たくなった気がするのう」",
        "長老は感極まったように何度も頷いた。「なんと、盟約の竜が正気に戻られたか！古き約束は、まだ生きておったのじゃな。王様にも早く知らせておくれ」",
    ),
    ("village", "shopkeeper"): (
        "棚を整理する店主に声をかける",
        "店主は荷縄を締める手を止めて大きく頷いた。「あんたが赤竜を討ってくれたのか！これで王都からの荷馬車も安心して通れるようになるよ、本当にありがとうな！」",
        "店主は驚いて目を丸くしたあと、ほっと胸を撫で下ろした。「赤竜が正気に戻ったのかい？また暴れ出さないなら何よりだ。あんたのおかげで村も落ち着くよ」",
    ),
}
SPRING_DESCRIPTION = "神秘的な光が揺れるエルフの泉。澄んだ霊水は一度だけ傷と魔力を癒やしてくれる。"
REST_PREVIEW = "泉の恵みで休めるのは一度きりだ。無防備な休息中は魔物に襲われる危険もある。"
TRANSITION_PLACEHOLDER = "【仮】泉でのひと休みを終え、先へ進む。"
TRANSITION = "スライム王は弾けて消え、泉に静寂が戻った。短い休息を終え、森の奥へと歩を進める。"
VILLAGE_BUTTON = "長老のいる麓の村へ向かう"


def walk_actions(actions: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for action in actions:
        yield action
        yield from walk_actions(action.get("children", []))


def both(first: Any, second: Any) -> dict[str, Any]:
    if not first or first == second:
        return deepcopy(second)
    if isinstance(first, dict) and second in first.get("all", []):
        return deepcopy(first)
    return {"all": [deepcopy(first), deepcopy(second)]}


def apply(pack: dict[str, Any]) -> None:
    pack["meta"]["content_revision"] = "2026-10-21-guidance-048"
    locations = {loc["id"]: loc for loc in pack["locations"]}
    spring = locations["elf_spring"]
    rest = next(a for a in spring["actions"] if a["id"] == "rest_at_elf_spring")
    rest.update(once="rested_at_elf_spring", hidden_after="rested_at_elf_spring",
                visible_requirements={"not_flag": "defeated_slime_king"},
                risk="危険（戦闘）",
                effects=[{"restore_full": True}, {"current_location": "slime_ambush_one"}, {"start_combat": True}])
    # Keep the one-use rest limit explicit in the finalized description.
    rest["preview"] = REST_PREVIEW
    spring["description"] = SPRING_DESCRIPTION
    if isinstance(spring.get("hybrid"), dict):
        spring["hybrid"]["summary"] = spring["description"]
    for game_map in pack.get("maps", []):
        for node in game_map.get("nodes", []):
            if node.get("location_id") == "elf_spring" or "elf_spring" in node.get("location_ids", []):
                node["description"] = spring["description"]
    boss = locations["slime_king_battle"]["combat"]
    boss["victory_effects"]["current_location"] = "forest_wolves"
    texts = boss.setdefault("result_texts", {})
    original = texts.get("victory", "").replace(TRANSITION_PLACEHOLDER, "").rstrip()
    if TRANSITION not in original:
        texts["victory"] = original + ("\n" if original else "") + TRANSITION
    else:
        texts["victory"] = original

    for location_id, ids in HIDE.items():
        for action in walk_actions(locations[location_id]["actions"]):
            if action["id"] in ids:
                action["visible_requirements"] = both(action.get("visible_requirements"), BEFORE)
    for location_id in ("village_frozen_clue", "ian_ice_katana_aftermath"):
        action = next(a for a in locations[location_id]["actions"] if a["id"] == "visit_village")
        action["visible_requirements"] = both(action.get("visible_requirements"), BEFORE)
        replacement_id = "visit_village_postgame"
        replacement = next((a for a in locations[location_id]["actions"] if a["id"] == replacement_id), None)
        if replacement is None:
            replacement = deepcopy(action)
            replacement.update(id=replacement_id, text=VILLAGE_BUTTON, intent_keywords=[],
                               visible_requirements=deepcopy(POSTGAME))
            locations[location_id]["actions"].append(replacement)
        else:
            replacement.update(text=VILLAGE_BUTTON, visible_requirements=deepcopy(POSTGAME))

    for location_id, npc_id, _ in CHATS:
        actions = locations[location_id]["actions"]
        identifier = "postgame_chat_" + npc_id
        button, defeated_text, purified_text = CHAT_TEXTS[(location_id, npc_id)]
        result_variants = [{"requirements": {"flag": "ignis_purified"}, "text": purified_text}]
        if any(a["id"] == identifier for a in actions):
            existing = next(a for a in actions if a["id"] == identifier)
            existing.update(text=button, result_text=defeated_text,
                            result_variants=result_variants, risk_source="action")
            continue
        action = dict(id=identifier, text=button,
                      npc_id=npc_id, once=f"{location_id}:{identifier}", effects=[],
                      visible_requirements=deepcopy(POSTGAME),
                      result_text=defeated_text, result_variants=result_variants,
                      risk_source="action")
        if npc_id == "gald":
            action["visible_after"] = "saved_gald"
        if npc_id == "mina":
            action["visible_after"] = "mina_quest_done"
        actions.append(action)

    # Legacy saves can revisit the original capital without returned_to_capital.
    # Keep the existing pre-Ignis destinations and use the same two postgame flags.
    for location_id, action_id, destination in (
        ("castle_town", "return_castle_from_town", "castle"),
        ("village", "return_castle_from_village", "castle_town"),
    ):
        action = next(a for a in locations[location_id]["actions"] if a["id"] == action_id)
        for effect in action["effects"]:
            branch = effect.get("branch", {})
            if branch.get("requirements") == POSTGAME:
                branch["then"] = [{"set_flag": "returned_to_capital"}, {"current_location": "festival_town"}]
        if not any("branch" in e and e["branch"].get("requirements") == POSTGAME for e in action["effects"]):
            for effect in action["effects"]:
                if effect.get("current_location") == destination:
                    effect.pop("current_location")
                    effect["branch"] = dict(requirements=deepcopy(POSTGAME),
                                            then=[{"set_flag": "returned_to_capital"}, {"current_location": "festival_town"}],
                                            **{"else": [{"current_location": destination}]})

    for location_id, ids in GUIDANCE.items():
        found = {a["id"]: a for a in walk_actions(locations[location_id]["actions"])}
        for identifier in ids:
            found[identifier]["guidance"] = True

    # Older migrations reappend their own actions; keep new dialogue after them.
    for loc in locations.values():
        actions = loc.get("actions", [])
        is_new = lambda action: action["id"].startswith("postgame_chat_") or action["id"] == "visit_village_postgame"
        loc["actions"] = [a for a in actions if not is_new(a)] + [a for a in actions if is_new(a)]

    # Synchronize display-only legacy menus, including prepared-turn fallbacks.
    # Avoid copying effects/numbers: 047's baby snapshot must stay identical.
    by_text = {a["text"]: a for loc in locations.values() for a in walk_actions(loc.get("actions", []))}
    changed_ids = {identifier for identifiers in HIDE.values() for identifier in identifiers}
    changed_ids.update(("rest_at_elf_spring", "visit_village"))
    def sync(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ("choices", "fallback_choices") and isinstance(child, list):
                    for choice in walk_actions([c for c in child if isinstance(c, dict)]):
                        source = by_text.get(choice.get("text", ""))
                        if source and source["id"] in changed_ids:
                            for field in ("visible_requirements",):
                                if field in source:
                                    choice[field] = deepcopy(source[field])
                            if source["id"] == "rest_at_elf_spring":
                                choice["preview"] = rest["preview"]
                                choice["once"] = rest["once"]
                                choice["hidden_after"] = rest["hidden_after"]
                sync(child)
        elif isinstance(value, list):
            for child in value:
                sync(child)
    sync(pack)
    from .npc_combat import _absence_inventory

    _absence_inventory(pack)


def placeholder_rows(pack: dict[str, Any], path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(pack, dict):
        for key, value in pack.items():
            yield from placeholder_rows(value, path + "/" + key)
    elif isinstance(pack, list):
        for index, value in enumerate(pack):
            label = value.get("id", index) if isinstance(value, dict) else index
            yield from placeholder_rows(value, path + "/" + str(label))
    elif isinstance(pack, str) and "【仮】" in pack:
        yield path, pack


def recovery_audit(pack: dict[str, Any]) -> list[dict[str, Any]]:
    """Conservative movement cycles, then the engine's permanent defeat guard.

    Branches are over-approximated; paid and item-consuming branches are listed
    separately. A location cycle alone does not make defeated enemies respawn.
    """
    from scripts.playtest.audit import branches

    locations = {loc["id"]: loc for loc in pack["locations"]}
    edges: dict[str, set[str]] = {identifier: set() for identifier in locations}
    resets: dict[str, set[str]] = {identifier: set() for identifier in locations}
    for identifier, loc in locations.items():
        effects = [a.get(key, []) for a in walk_actions(loc.get("actions", []))
                   for key in ("effects", "success_effects", "failure_effects")]
        victory = loc.get("combat", {}).get("victory_effects", {})
        effects.append(victory if isinstance(victory, list) else [victory])
        for effect_list in effects:
            for path in branches(effect_list):
                for effect in path:
                    dest = effect.get("current_location") or effect.get("next_location")
                    if dest in locations:
                        edges[identifier].add(dest)
                    if effect.get("unset_flag"):
                        resets[identifier].add(effect["unset_flag"])
                    resets[identifier].update(effect.get("flags_unset", []))

    def reachable(start: str) -> set[str]:
        visited, pending = set(), [start]
        while pending:
            current = pending.pop()
            if current not in visited:
                visited.add(current)
                pending.extend(edges[current] - visited)
        return visited

    reach = {identifier: reachable(identifier) for identifier in locations}
    results = []
    def visit(actions: list[dict[str, Any]], limited: bool = False) -> Iterator[dict[str, Any]]:
        for action in actions:
            gated = limited or bool(action.get("once") or action.get("disabled_after"))
            if not gated:
                yield action
            yield from visit(action.get("children", []), gated)

    for identifier, loc in locations.items():
        cycle = {other for other in reach[identifier] if identifier in reach[other]}
        cycle_battles = sorted(other for other in cycle
                               if locations[other].get("combat", {}).get("enemy_ids")
                               or locations[other].get("enemy_ids"))
        reset_flags = set().union(*(resets[other] for other in cycle))
        repeatable = []
        for other in cycle_battles:
            enemies = locations[other].get("combat", {}).get("enemy_ids") or locations[other].get("enemy_ids", [])
            if any(f"combat_defeated:{other}:{enemy}" in reset_flags for enemy in enemies):
                repeatable.append(other)
        for action in visit(loc.get("actions", [])):
            for key in ("effects", "success_effects", "failure_effects"):
                for index, path in enumerate(branches(action.get(key, []))):
                    healing = [effect for effect in path if effect.get("restore_full") is True
                               or effect.get("restore_ratio", 0) > 0
                               or any(effect.get(resource + "_change", 0) > 0 for resource in ("hp", "mp", "sp"))]
                    if not healing:
                        continue
                    cost = sum(-min(0, effect.get("gold_change", 0)) for effect in path)
                    consumes = any(effect.get("remove_item") or effect.get("inventory_remove") for effect in path)
                    results.append(dict(location=identifier, action=action["id"], branch=f"{key}/{index}",
                                        recovery=healing, gold_cost=cost, consumes_item=consumes,
                                        cycle_battles=cycle_battles, repeatable_battles=repeatable,
                                        free_repeatable_battle_loop=not cost and not consumes and bool(repeatable)))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true", help="Read-only recovery cycle audit")
    args = parser.parse_args()
    if args.audit:
        for name in PACKS:
            pack = json.loads((ROOT / "host/prompt/processed" / name).read_text(encoding="utf-8"))
            print(json.dumps(dict(pack=name, actions=recovery_audit(pack)), ensure_ascii=False))
        return
    for name in PACKS:
        path = ROOT / "host/prompt/processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"048: {name}: {len(list(placeholder_rows(pack)))} placeholders")
    guard_path = ROOT / "host/prompt/processed/difficulty/overlay_revision.json"
    guard = json.loads(guard_path.read_text(encoding="utf-8"))
    for entry in guard.values():
        entry["content_revision"] = "2026-10-21-guidance-048"
    guard_path.write_text(json.dumps(guard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
