"""Deterministic, offline exploration through the public app API."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import uuid
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional
from unittest.mock import patch

import requests

from host import app, combat, llm_trace, state
from host.area_retry import areas_here
from scripts.balance import sim
from . import metrics


ROOT = Path(__file__).resolve().parents[2]
CHARACTERS = ("hero", "cleric", "mage", "thief")
SEEDS = (20261013, 20261014, 101, 102, 103, 104, 105, 106)
ROUTE_SEEDS = (20261013, 20261014, 102, 101, 103, 104, 105, 106)
FALLBACK_TEXTS = ("接続中のローカルLLMから応答を取得できませんでした", "運命の出目は",
                  "（GMとの通信が途切れたため、描写を省略した。結果は記録に反映されている。）")
AREA_ORDER = {"capital": 0, "forest": 1, "goblin_fort": 1, "sealed_cave": 1, "burning_village": 2,
              "old_battlefield": 2, "oaksdawn": 2, "rumbling_gorge": 2, "dragon_valley": 3, "royal_return": 4, "general_mansion": 4}


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


def oaksdawn_action(session: dict[str, Any], *, prefer_gorge: bool = False) -> Optional[str]:
    location = state.current_location_id(session)
    visited = session.get("visited_locations", [])
    flags = session["flags"]
    if "oaksdawn_square" not in visited:
        return {"old_battlefield": "battlefield_to_oaksdawn", "cave_hot_spring": "follow_hot_spring_water",
                "cave_waterway": "waterway_to_gate", "oaksdawn_water_gate": "open_oaksdawn_gate"}.get(location)
    if location == "oaksdawn_square":
        for suffix in ("hq", "chapel", "workshop", "inn", "wall"):
            if f"oaksdawn_{suffix}" not in visited:
                return f"square_to_{suffix}"
        return "square_to_wall"
    if location == "oaksdawn_hq":
        return ("greet_walter" if not flags.get("greeted_walter") else "ask_guardian_refusal" if not flags.get("heard_guardian_refusal")
                else "request_guardian_letter" if not flags.get("received_guardian_letter")
                else "open_gorge_path" if prefer_gorge and not flags.get("gorge_path_open") else "hq_to_square")
    if location == "oaksdawn_chapel":
        return "talk_liese" if not flags.get("met_liese") else "recruit_liese_letter" if not flags.get("recruited_liese") else "chapel_to_square"
    if location == "oaksdawn_workshop":
        return "talk_brigitte" if not flags.get("met_brigitte") else "workshop_to_square"
    if location == "oaksdawn_inn":
        if prefer_gorge and not flags.get("recruited_elio"):
            if not flags.get("met_elio"):
                return "talk_elio"
            for identifier in ("recruit_elio_water", "recruit_elio_gold", "recruit_elio_persuade"):
                entry = state.resolve_action(session, action_id=identifier)
                if entry and state.action_requirement_status(entry, session)[0]:
                    return identifier
        return "ask_oaksdawn_rumor" if not flags.get("heard_pass_rumor") else "inn_to_square"
    if location == "oaksdawn_wall":
        return "oaksdawn_east_pass_open" if prefer_gorge and flags.get("gorge_path_open") else "oaksdawn_to_battlefield"
    return None


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


def preferred_route(seed: int) -> str:
    return metrics.ROUTES[(ROUTE_SEEDS.index(seed) if seed in ROUTE_SEEDS else seed) % len(metrics.ROUTES)]


def chapter3_action(session: dict[str, Any], path: str) -> Optional[str]:
    location = state.current_location_id(session)
    entered = any(loc in session.get("visited_locations", []) for loc in metrics.ROUTE_LOCATIONS)
    if location == "forest_exit" and not entered:
        return "leave_forest_for_village" if path == "village" else "enter_old_battlefield"
    if location == "old_battlefield" and path == "village" and not entered:
        return "battlefield_to_forest"
    if location.startswith("gorge_"):
        from scripts.balance.gorge import route_action

        return route_action(session)
    return oaksdawn_action(session, prefer_gorge=path == "gorge") or battlefield_action(session)


def ending_record(public: dict[str, Any], session: dict[str, Any], step: int) -> dict[str, Any]:
    ending = public["game_over"]
    snapshot = state.retry_snapshot(session)
    return dict(step=step, location=public["current_location"], ending=ending.get("ending"),
        combat_defeat=bool(ending.get("combat_defeat")), completed=ending.get("title") == "冒険完了",
        attempt=public.get("retry_count", 0), area=snapshot["area_id"] if snapshot else None,
        entry_hp=snapshot["state"]["character"]["hp"] if snapshot else None)


def explore(character: str, seed: int, max_steps: int = 330, *, output: Optional[Path] = None) -> dict[str, Any]:
    rng = random.Random(seed)
    taken: Counter = Counter()
    lines = [f"# {character} / seed {seed}", ""]
    failures: list[str] = []
    deaths: list[dict[str, Any]] = []
    locations: list[str] = []
    seen_messages = seen_logs = 0
    farthest: tuple[tuple[int, int], str] = ((-1, -1), "")
    after_retry_locations: list[str] = []
    scenario_choices: list[dict[str, Any]] = []
    route_entries: list[dict[str, Any]] = []
    companion_history: list[dict[str, Any]] = []
    collected_clues: set[str] = set()
    invariants = dict(exceptions=0, noncombat_dead_ends=0, fallback_narrations=0)
    path = preferred_route(seed)

    def dump(public: dict[str, Any]) -> None:
        nonlocal seen_messages, seen_logs
        for message in public["messages"][seen_messages:]:
            text = message.get("text", "")
            lines.append(f"> [{message.get('speaker') or message.get('role')}] {text.replace(chr(10), chr(10) + '> ')}")
            if message.get("role") == "assistant" and any(marker in text for marker in FALLBACK_TEXTS):
                failures.append(f"fallback at {public['current_location']}: {text}")
                invariants["fallback_narrations"] += 1
        seen_messages = len(public["messages"])
        for entry in public.get("system_logs", [])[seen_logs:]:
            lines.append(f"- {entry['text']}")
        seen_logs = len(public.get("system_logs", []))

    with offline_runtime(seed):
        public = app.api_create_session(app.CreateSessionRequest(character_id=character, character={"name": "テスト"}))
        session_id = public["id"]
        initial = state.load_session(session_id)
        clues = metrics.clue_flags(initial["scenario_pack"])

        def observe(current: dict[str, Any], step_number: int) -> None:
            location_id = state.current_location_id(current)
            attempt = current.get("retry_count", 0)
            companion = (current.get("companion") or {}).get("id")
            if not companion_history or (attempt, companion) != (companion_history[-1]["attempt"], companion_history[-1]["companion"]):
                companion_history.append(dict(step=step_number, attempt=attempt, location=location_id, companion=companion))
            selected = metrics.ROUTE_LOCATIONS.get(location_id)
            if selected and not any(r["route"] == selected and r["attempt"] == attempt for r in route_entries):
                route_entries.append(dict(route=selected, step=step_number, attempt=attempt, companion=companion))
            collected_clues.update(flag for flag in clues if current["flags"].get(flag))

        dump(public)
        step = 0
        for step in range(1, max_steps + 1):
            session = state.load_session(session_id)
            observe(session, step)
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
                    deaths.append(ending_record(public, session, step))
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
                        invariants["noncombat_dead_ends"] += 1
                        break
                    pick = min(options, key=lambda c: (taken[c["action_id"]],
                                                       "章" in (c.get("preview", "") + c["text"]), rng.random()))
                    preferred = chapter3_action(session, path)
                    if preferred:
                        if preferred == "sneak_bone_field":
                            preferred = next((c["action_id"] for c in options if c["action_id"] == "show_curse_to_skeletons"), preferred)
                        if preferred == "fight_grave_knight":
                            preferred = next((c["action_id"] for c in options if c["action_id"] == "curse_pass_grave_knight"), preferred)
                        pick = next(c for c in options if c["action_id"] == preferred)
                    taken[pick["action_id"]] += 1
                    selected_action = state.resolve_action(session, action_id=pick["action_id"])
                    scenario_choices.append(dict(step=step, attempt=public.get("retry_count", 0), location=location,
                        action_id=pick["action_id"], text=pick["text"], pure_movement=metrics.pure_movement(selected_action)))
                    lines.append(f"\n選択: {pick['text']}")
                    public = app.api_turn(session_id, app.TurnRequest(text=pick["text"], action_id=pick["action_id"]))
                dump(public)
            except Exception as exc:
                failures.append(f"{location} step {step}: {type(exc).__name__}: {exc}")
                invariants["exceptions"] += 1
                break
        session = state.load_session(session_id)
        observe(session, step)
        if public["current_location"] not in locations:
            locations.append(public["current_location"])
        ending = public.get("game_over") or {}
        if ending and not any(death["attempt"] == public.get("retry_count", 0) for death in deaths):
            deaths.append(ending_record(public, session, step))
        result = {"character": character, "seed": seed, "steps": step, "retry_count": public.get("retry_count", 0),
                  "ending": ending.get("ending") or "step_limit", "final_location": public["current_location"],
                  "first_death": next((death for death in deaths if not death["completed"]), None),
                  "deaths": deaths, "farthest_location": farthest[1], "visited_locations": locations,
                  "retry_visited_locations": after_retry_locations, "failures": failures,
                  "completed": ending.get("title") == "冒険完了", "preferred_chapter3_route": path,
                  "chapter3_routes": list(dict.fromkeys(r["route"] for r in route_entries)), "route_entries": route_entries,
                  "companion_history": companion_history, "final_companion": (session.get("companion") or {}).get("id"),
                  "clue_flags": sorted(collected_clues), "final_clue_flags": [flag for flag in clues if session["flags"].get(flag)],
                  "scenario_choices": scenario_choices, "invariants": invariants}
        result["battlefield_completed"] = bool(session["flags"].get("passed_grave_chapel") and "village_frozen_clue" in locations)
        result["gorge_completed"] = bool(session["flags"].get("passed_gorge_worm_lair") and "village" in locations)
        repeated = [death for death in deaths if death["combat_defeat"]]
        result["repeat_death_candidate"] = len(repeated) > 1 and repeated[0]["location"] == repeated[-1]["location"]
        lines.extend(["\n## 検証結果\n", "```json", json.dumps(result, ensure_ascii=False, indent=2), "```", ""])
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        rendered = "\n".join(lines)
        output.write_text("\n".join(line.rstrip() for line in rendered.split("\n")), encoding="utf-8")
    return result


def write_report(results: list[dict[str, Any]], path: Path, transcript_dir: Path,
                 summary: dict[str, Any], max_steps: int) -> None:
    lines = [f"# 离线试玩回归（{path.stem}）", "",
             f"{len(results)}局，职业：{', '.join(dict.fromkeys(r['character'] for r in results))}；种子：{', '.join(str(s) for s in dict.fromkeys(r['seed'] for r in results))}；每局最多{max_steps}步。战斗每个指令和结算各占一步。",
             "首次战斗死亡后重来一次，选择次数及随机流继续累计。选项、判定和战斗的随机数均固定。",
             "首次死亡包含剧情导致的死亡结局；剧情必败但仍能继续的战斗不计死亡，冒険完了也不计死亡。",
             "037第二轮：路线轮换使用20261013、20261014、102、101、103、104、105、106的顺序，循环村／古戦場／峡谷；仅交换101与102的优先路线，让第一轮能到达第三章的魔法使い/102走峡谷。运行仍按原种子列表，子集映射固定。村优先种子如从洞窟先到城塞，则从古戦場入口返回森林出口走村。古戦場和峡谷保留现行城塞访问、招募与路线内策略，其余仍按选项使用次数、章节推进偏好及固定随机数选择。",
             "实际路线以village_approach／bone_field／gorge_entrance首次进入为准，old_battlefield仅作为城塞通道时不算走古戦場。重来分别记attempt，同行者记录路线入口和全程变化，不以最终同行者代替。",
             "线索flag从凱旋の間告发条件与既有mystery任务读取；曾取得与最终保留分别统计。选择重合率只取实际剧本选项的（地点ID、选项ID）集合，排除无判定、无一次性标记且效果只有移动/背景的纯移动；不含战斗指令。",
             "通关以剧本的冒険完了结局为准。Jaccard取所有通关局的无序两两组合，包含同一局重来前的经历；没有足够通关局时返回null。空集合对定义为1。",
             "LLM 配置指向 127.0.0.1:1，并在请求适配器直接模拟连接失败；禁止真实网络。", "",
             "|职业|种子|首次死亡|重来次数|结局|步数|第三章路线（入口同行者）|线索flag|",
             "|---|---:|---|---:|---|---:|---|---|"]
    for result in results:
        death = result["first_death"]
        entries = "; ".join(f"{r['route']} ({r['companion'] or 'none'}, attempt {r['attempt']})" for r in result["route_entries"])
        lines.append(f"|{result['character']}|{result['seed']}|{death['location'] if death else '无'}|{result['retry_count']}|{result['ending']} @ {result['final_location']}|{result['steps']}|{entries or '未到达'}|{', '.join(result['clue_flags']) or '无'}|")
    lines += ["", "最远地点口径：按主线章节、地图节点顺序取最大值；砦/洞窟归森林章、屋敷归王城归还章。同级支线没有唯一剧情顺序，完整到访记录见逐步日志。",
              "", "最终分布：" + json.dumps(dict(Counter(r["ending"] for r in results)), ensure_ascii=False),
              "", "首次死亡地点：" + json.dumps(dict(Counter(r["first_death"]["location"] for r in results if r["first_death"])), ensure_ascii=False),
              "", "重来后分布：" + json.dumps(dict(Counter(r["ending"] for r in results if r["retry_count"])), ensure_ascii=False), "",
              "## 不变量检查", ""]
    failures = [issue for result in results for issue in result["failures"]]
    battlefield_visits = sum("old_battlefield" in result["visited_locations"] for result in results)
    lines += [f"- 异常、非战斗死路及兜底叙述：{len(failures)} 项。", *[f"- {issue}" for issue in failures],
              f"- 古戦場到访：{battlefield_visits}/{len(results)}局。",
              f"- 城塞到访：{sum('oaksdawn_square' in r['visited_locations'] for r in results)}/{len(results)}局。",
              f"- 峡谷到访：{sum('gorge_entrance' in r['visited_locations'] for r in results)}/{len(results)}局；完成峡谷：{sum(r.get('gorge_completed', False) for r in results)}局。",
              f"- 经礼拝堂到村后门：{sum(r['battlefield_completed'] for r in results)}/{len(results)}局。",
              "- 同一地点重来后再次死亡（仅作为循环候选，不能据此证明必死）：" +
              ", ".join(f"{r['character']}/{r['seed']} @ {r['final_location']}" for r in results if r["repeat_death_candidate"]),
              "", "不变量分类：" + json.dumps(summary["invariants"], ensure_ascii=False),
              "", "各职业实际路线覆盖：" + json.dumps(summary["route_counts_by_character"], ensure_ascii=False),
              "", "## 通关局重合率", "", f"通关局{summary['completed']}局。", "",
              "|集合|配对数|均值|最小|最大|", "|---|---:|---:|---:|---:|"]
    for label, stats in summary["overlap"].items():
        if label != "pairwise":
            numbers = [f"{stats[k]:.4f}" if stats[k] is not None else "null" for k in ("mean", "min", "max")]
            lines.append(f"|{label}|{stats['pairs']}|{'|'.join(numbers)}|")
    lines += ["", "## 线索覆盖", "", "|flag|曾取得局数|最终保留局数|", "|---|---:|---:|"]
    for flag, count in summary["clue_counts"].items():
        lines.append(f"|{flag}|{count}|{summary['final_clue_counts'][flag]}|")
    lines += ["", "## 从未到达的地点", "", *[f"- `{loc['id']}`：{loc['title']}" for loc in summary["never_visited"]],
              "", "## 逐步记录", ""]
    for result in results:
        name = f"{result['character']}-{result['seed']}.md"
        link = (transcript_dir / name).relative_to(path.parent).as_posix()
        lines.append(f"- [{name}]({link})")
    seeds = " ".join(str(s) for s in dict.fromkeys(r["seed"] for r in results))
    characters = " ".join(dict.fromkeys(r["character"] for r in results))
    lines += ["", "## 复现", "", "```powershell", f'python -m scripts.playtest.explore --characters {characters} --seeds {seeds} --steps {max_steps} --output "{path.as_posix()}"', "```", "",
              "剧本 SHA-256：", ""]
    for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        digest = hashlib.sha256((ROOT / "host/prompt/processed" / filename).read_bytes()).hexdigest()
        lines.append(f"- {filename}: `{digest}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _explore_job(job: tuple[str, int, int, Path]) -> dict[str, Any]:
    character, seed, steps, output = job
    return explore(character, seed, steps, output=output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--characters", nargs="+", choices=CHARACTERS, default=CHARACTERS)
    parser.add_argument("--seeds", nargs="+", type=int, default=SEEDS)
    parser.add_argument("--steps", type=int, default=330)
    parser.add_argument("--workers", type=int, default=1, help="Isolated offline processes; results retain input order")
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/playtest-2026-10-18-ch3/summary.md")
    args = parser.parse_args()
    if min(args.steps, args.workers) < 1:
        parser.error("steps and workers must be positive")
    transcripts = args.output.parent / "logs" if args.output.stem == "summary" else args.output.with_suffix("")
    jobs = [(character, seed, args.steps, transcripts / f"{character}-{seed}.md") for character in args.characters for seed in args.seeds]
    with ExitStack() as stack:
        pool = stack.enter_context(ProcessPoolExecutor(max_workers=args.workers)) if args.workers > 1 else None
        results = []
        for result in (pool.map(_explore_job, jobs) if pool else map(_explore_job, jobs)):
            results.append(result)
            print(json.dumps({k: result[k] for k in ("character", "seed", "steps", "ending", "chapter3_routes", "invariants")}, ensure_ascii=False), flush=True)
    summary = metrics.summarize(results, state.load_scenario_pack(state.DEFAULT_SCENARIO))
    write_report(results, args.output, transcripts, summary, args.steps)
    fingerprints = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (Path(__file__), Path(metrics.__file__), state.DEFAULT_SCENARIO, state.DEFAULT_SCENARIO.with_name("dragon_rpg_hybrid.json"))}
    args.output.with_suffix(".json").write_text(json.dumps(dict(summary=summary, runs=results,
        max_steps=args.steps, workers=args.workers, fingerprints=fingerprints), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(r["failures"] for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
