"""Deterministic, offline exploration through the public app API."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import uuid
from collections import Counter
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional
from unittest.mock import patch

import requests

from host import app, combat, llm_trace, state
from host.area_retry import areas_here
from scripts.balance import sim


ROOT = Path(__file__).resolve().parents[2]
CHARACTERS = ("hero", "cleric", "mage", "thief")
SEEDS = (20261013, 20261014)
FALLBACK_TEXTS = ("接続中のローカルLLMから応答を取得できませんでした", "運命の出目は",
                  "（GMとの通信が途切れたため、描写を省略した。結果は記録に反映されている。）")
AREA_ORDER = {"capital": 0, "forest": 1, "goblin_fort": 1, "sealed_cave": 1, "burning_village": 2,
              "old_battlefield": 2, "dragon_valley": 3, "royal_return": 4, "general_mansion": 4}


class OfflineRequests:
    def post(self, url: str, **kwargs: Any) -> None:
        if not url.startswith("http://127.0.0.1:1/"):
            raise AssertionError("Playtests must never contact an external model")
        raise requests.ConnectionError("offline playtest: model unavailable")


@contextmanager
def offline_runtime(seed: int) -> Iterator[Path]:
    config = {"active_backend": "ollama", "debug_llm": False, "demo_fallback_on_error": True,
              "max_model_attempts": 1, "_request_policy": OfflineRequests(),
              "backends": {"ollama": {"base_url": "http://127.0.0.1:1/v1", "model": "offline", "api_key": ""}}}
    temporary_root = ROOT / ".tmp-test"
    temporary_root.mkdir(exist_ok=True)
    root = temporary_root / ("playtest-" + uuid.uuid4().hex)
    root.mkdir()
    with ExitStack() as stack:
        stack.callback(shutil.rmtree, root, ignore_errors=True)
        stack.enter_context(patch.object(state, "SAVE_DIR", root / "saves"))
        stack.enter_context(patch.object(llm_trace, "TRACE_DIR", root / "traces"))
        stack.enter_context(patch.object(app, "load_config", return_value=config))
        stack.enter_context(patch.object(app, "debug_log"))
        stack.enter_context(patch.object(state, "random", random.Random(seed)))
        stack.enter_context(patch.object(combat, "random", random.Random(seed)))
        stack.enter_context(patch.object(requests.sessions.Session, "request", side_effect=AssertionError("network forbidden")))
        yield root


def flatten(choices: list[dict[str, Any]], depth: int = 0):
    for choice in choices:
        yield choice, depth
        yield from flatten(choice.get("children", []), depth + 1)


def battlefield_action(session: dict[str, Any]) -> Optional[str]:
    location = state.current_location_id(session)
    flags = session["flags"]
    if location == "old_battlefield":
        return "battlefield_to_bones"
    if location == "bone_field":
        if not flags.get("passed_bone_field"):
            return "sneak_bone_field"
        return "bones_to_marsh" if flags.get("rested_watchtower") else "bones_to_tower"
    if location == "ruined_watchtower":
        return ("talk_old_soldier" if not flags.get("heard_old_soldier_ghost") else
                "search_watchtower" if not flags.get("found_gravekeeper_cloak") else
                "rest_watchtower" if not flags.get("rested_watchtower") else "tower_to_bones")
    if location == "ghoul_marsh":
        return "marsh_to_chapel" if flags.get("passed_ghoul_marsh") else "sneak_ghoul_marsh"
    if location == "grave_chapel":
        return "chapel_to_village" if flags.get("passed_grave_chapel") else "fight_grave_knight"
    return None


def explore(character: str, seed: int, max_steps: int = 150, *, output: Optional[Path] = None) -> dict[str, Any]:
    rng = random.Random(seed)
    taken: Counter = Counter()
    lines = [f"# {character} / seed {seed}", ""]
    failures: list[str] = []
    deaths: list[dict[str, Any]] = []
    locations: list[str] = []
    seen_messages = seen_logs = 0
    farthest: tuple[tuple[int, int], str] = ((-1, -1), "")
    after_retry_locations: list[str] = []

    def dump(public: dict[str, Any]) -> None:
        nonlocal seen_messages, seen_logs
        for message in public["messages"][seen_messages:]:
            text = message.get("text", "")
            lines.append(f"> [{message.get('speaker') or message.get('role')}] {text.replace(chr(10), chr(10) + '> ')}")
            if message.get("role") == "assistant" and any(marker in text for marker in FALLBACK_TEXTS):
                failures.append(f"fallback at {public['current_location']}: {text}")
        seen_messages = len(public["messages"])
        for entry in public.get("system_logs", [])[seen_logs:]:
            lines.append(f"- {entry['text']}")
        seen_logs = len(public.get("system_logs", []))

    with offline_runtime(seed):
        public = app.api_create_session(app.CreateSessionRequest(character_id=character, character={"name": "テスト"}))
        session_id = public["id"]
        dump(public)
        step = 0
        for step in range(1, max_steps + 1):
            session = state.load_session(session_id)
            location = public["current_location"]
            if location not in locations:
                locations.append(location)
                area = areas_here(session)
                rank = AREA_ORDER.get(area[0]["id"], -1) if area else -1
                node = next((i for i, n in enumerate(area[0]["nodes"]) if location in n["location_ids"]), -1) if area else -1
                if (rank, node) >= farthest[0]:
                    farthest = ((rank, node), location)
            if public.get("retry_count") and location not in after_retry_locations:
                after_retry_locations.append(location)
            actor = public["character"]
            lines.append(f"\n## step {step} / {location} 「{public['current_location_title']}」 HP {actor['hp']}/{actor['max_hp']} G {actor['gold']}\n")
            options = []
            for choice, depth in flatten(public["choices"]):
                unavailable = "" if choice.get("enabled", True) else f" [不可: {choice.get('disabled_reason', '')}]"
                lines.append(f"{'  ' * depth}- {choice['text']} | {choice.get('preview', '')} | {choice.get('risk', '')}{unavailable}")
                if choice.get("enabled", True) and not choice.get("children") and choice.get("action_id") and not choice.get("open_shop"):
                    options.append(choice)
            try:
                # Resolve the last combat round before evaluating the ending or retrying.
                if combat.combat_needs_resolution(session):
                    public = app.api_combat_resolve(session_id)
                elif public.get("game_over"):
                    snapshot = state.retry_snapshot(session)
                    deaths.append({"step": step, "location": location, "ending": public["game_over"].get("ending"),
                                   "combat_defeat": bool(public["game_over"].get("combat_defeat")),
                                   "area": snapshot["area_id"] if snapshot else None,
                                   "entry_hp": snapshot["state"]["character"]["hp"] if snapshot else None})
                    lines.append(f"\n終了: {json.dumps(public['game_over'], ensure_ascii=False)}")
                    if public.get("can_retry_area") and not public.get("retry_count"):
                        public = app.api_retry_area(session_id)
                    else:
                        break
                elif combat.combat_is_active(session):
                    action, target = sim.choose_action(session, "heuristic")
                    lines.append(f"\n戦闘: {action['type']} / {action['id']} → {target or ''}")
                    previous = len((session.get("combat") or {}).get("log", []))
                    public = app.api_combat_action(session_id, app.CombatActionRequest(
                        action_type=action["type"], action_id=action["id"], target_id=target or ""))
                    saved_combat = state.load_session(session_id).get("combat") or {}
                    for event in saved_combat.get("log", [])[previous:]:
                        lines.append(f"- {event.get('text', '')}")
                else:
                    if not options:
                        failures.append(f"no enabled scenario action at {location} (step {step})")
                        break
                    pick = min(options, key=lambda c: (taken[c["action_id"]],
                                                       "章" in (c.get("preview", "") + c["text"]), rng.random()))
                    if location == "forest_exit" and seed % 2 and "old_battlefield" not in locations:
                        pick = next(c for c in options if c["action_id"] == "enter_old_battlefield")
                    preferred = battlefield_action(session)
                    if preferred:
                        if preferred == "sneak_bone_field":
                            preferred = next((c["action_id"] for c in options if c["action_id"] == "show_curse_to_skeletons"), preferred)
                        if preferred == "fight_grave_knight":
                            preferred = next((c["action_id"] for c in options if c["action_id"] == "curse_pass_grave_knight"), preferred)
                        pick = next(c for c in options if c["action_id"] == preferred)
                    taken[pick["action_id"]] += 1
                    lines.append(f"\n選択: {pick['text']}")
                    public = app.api_turn(session_id, app.TurnRequest(text=pick["text"], action_id=pick["action_id"]))
                dump(public)
            except Exception as exc:
                failures.append(f"{location} step {step}: {type(exc).__name__}: {exc}")
                break
        session = state.load_session(session_id)
        ending = public.get("game_over") or {}
        result = {"character": character, "seed": seed, "steps": step, "retry_count": public.get("retry_count", 0),
                  "ending": ending.get("ending") or "step_limit", "final_location": public["current_location"],
                  "first_death": next((death for death in deaths if death["combat_defeat"]), None),
                  "deaths": deaths, "farthest_location": farthest[1], "visited_locations": locations,
                  "retry_visited_locations": after_retry_locations, "failures": failures}
        result["battlefield_completed"] = bool(session["flags"].get("passed_grave_chapel") and "village_frozen_clue" in locations)
        repeated = [death for death in deaths if death["combat_defeat"]]
        result["repeat_death_candidate"] = len(repeated) > 1 and repeated[0]["location"] == repeated[-1]["location"]
        lines.extend(["\n## 検証結果\n", "```json", json.dumps(result, ensure_ascii=False, indent=2), "```", ""])
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        rendered = "\n".join(lines)
        output.write_text("\n".join(line.rstrip() for line in rendered.split("\n")), encoding="utf-8")
    return result


def write_report(results: list[dict[str, Any]], path: Path, transcript_dir: Path) -> None:
    lines = ["# 离线试玩回归（2026-10-13）", "",
             "4 职业 × 2 固定种子（20261013、20261014），每局最多 150 步；战斗每个指令和结算各占一步。",
             "首次战斗死亡后重来一次，选择次数及随机流继续累计。选项、判定和战斗的随机数均固定。",
             "031：奇数种子首次到森林出口时优先古戦場；进入后依次潜行骨野、访问塔、取外套休息、潜行沼地、通过礼拝堂。诅咒持有者使用专属放行，至少2局通过新地图。",
             "LLM 配置指向 127.0.0.1:1，并在请求适配器直接模拟连接失败；禁止真实网络。", "",
             "| 职业 | 种子 | 首次死亡 | 重来后结果 / 最终结果 | 最远地点 | 步数 |",
             "|---|---:|---|---|---|---:|"]
    for result in results:
        death = result["first_death"]
        lines.append(f"| {result['character']} | {result['seed']} | {death['location'] if death else '无'} | {result['ending']} @ {result['final_location']} | {result['farthest_location']} | {result['steps']} |")
    lines += ["", "最远地点口径：按主线章节、地图节点顺序取最大值；砦/洞窟归森林章、屋敷归王城归还章。同级支线没有唯一剧情顺序，完整到访记录见逐步日志。",
              "", "最终分布：" + json.dumps(dict(Counter(r["ending"] for r in results)), ensure_ascii=False),
              "", "首次死亡地点：" + json.dumps(dict(Counter(r["first_death"]["location"] for r in results if r["first_death"])), ensure_ascii=False),
              "", "重来后分布：" + json.dumps(dict(Counter(r["ending"] for r in results if r["retry_count"])), ensure_ascii=False), "",
              "## 不变量检查", ""]
    failures = [issue for result in results for issue in result["failures"]]
    battlefield_visits = sum("old_battlefield" in result["visited_locations"] for result in results)
    lines += [f"- 异常、非战斗死路及兜底叙述：{len(failures)} 项。", *[f"- {issue}" for issue in failures],
              f"- 古戦場到访：{battlefield_visits}/{len(results)}局。",
              f"- 经礼拝堂到村后门：{sum(r['battlefield_completed'] for r in results)}/{len(results)}局。",
              "- 同一地点重来后再次死亡（仅作为循环候选，不能据此证明必死）：" +
              ", ".join(f"{r['character']}/{r['seed']} @ {r['final_location']}" for r in results if r["repeat_death_candidate"]),
              "", "## 逐步记录", ""]
    for result in results:
        name = f"{result['character']}-{result['seed']}.md"
        lines.append(f"- [{name}]({transcript_dir.name}/{name})")
    lines += ["", "## 复现", "", "```powershell", "python -m scripts.playtest.explore", "```", "",
              "剧本 SHA-256：", ""]
    for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        digest = hashlib.sha256((ROOT / "host/prompt/processed" / filename).read_bytes()).hexdigest()
        lines.append(f"- {filename}: `{digest}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--characters", nargs="+", choices=CHARACTERS, default=CHARACTERS)
    parser.add_argument("--seeds", nargs="+", type=int, default=SEEDS)
    parser.add_argument("--steps", type=int, default=150)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/playtest-2026-10-13.md")
    args = parser.parse_args()
    transcripts = args.output.with_suffix("")
    results = []
    for character in args.characters:
        for seed in args.seeds:
            result = explore(character, seed, args.steps, output=transcripts / f"{character}-{seed}.md")
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    write_report(results, args.output, transcripts)
    args.output.with_suffix(".json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(r["failures"] for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
