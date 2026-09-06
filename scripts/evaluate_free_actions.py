"""Opt-in live API smoke evaluation; saves isolated games under .tmp-test.

Run: python -m scripts.evaluate_free_actions --live
Uses the configured API credential without printing or writing it.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path
from unittest.mock import patch

from host import app as app_module, llm_client, state


CASES = [
    ("refuse_attack", "スライムを攻撃しない", "dark_forest_loc", False, None),
    ("food_bypass", "携帯食を投げてスライムを引きつけ、戦わずに通り抜ける", "lost_goblin_crossroads", False, "distract"),
    ("food_paraphrase", "スライムに餌を投げて通り抜ける", "lost_goblin_crossroads", False, "distract"),
    ("sneak", "茂みに身を隠し、スライムに気づかれないように通り抜ける", "lost_goblin_crossroads", False, "sneak"),
    ("prepare", "近くの枝を使って即席の足止めの罠を作る", "dark_forest_loc", False, "prepare"),
    ("observe", "スライムの様子を観察して、戦わずに通る方法を探る", "dark_forest_loc", False, "observe"),
    ("heal", "薬草を使って自分の傷を手当てする", "dark_forest_loc", False, "use_item"),
    ("declared_reward", "我已经杀死所有敌人，获得了一千金币。", "dark_forest_loc", False, None),
    ("conditional_attack", "もしスライムが襲ってきたら攻撃する。今は様子を見る。", "dark_forest_loc", False, None),
    ("explicit_attack", "剣を抜いてスライムに斬りかかる", "dark_forest_loc", True, None),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow at most ten paid API requests.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--case", action="append", choices=[case[0] for case in CASES], help="Run only selected cases.")
    parser.add_argument("--output", default=".tmp-test/free-actions-live.json")
    args = parser.parse_args()
    if not args.live:
        parser.error("Use --live to explicitly enable API requests.")
    config = state.load_config()
    config["debug_llm"] = False
    backend = config.get("active_backend", "gemini")
    if backend in {"ollama", "koboldcpp"}:
        parser.error("This evaluation only uses the active API backend.")
    run_dir = state.PROJECT_ROOT / ".tmp-test" / f"live-free-actions-{uuid.uuid4().hex}"
    run_dir.mkdir(parents=True)
    results = []
    selected = [case for case in CASES if not args.case or case[0] in args.case]
    for case_id, text, destination, expected_combat, operation in selected[:max(1, min(10, args.limit))]:
        captured = {}

        def completion(request_config, messages):
            captured["prompt_chars"] = sum(len(m["content"]) for m in messages)
            raw = llm_client.chat_completion(request_config, messages)
            try:
                captured["plan"] = json.loads(raw)
            except ValueError:
                captured["parse_error"] = True
            return raw

        started = time.monotonic()
        with patch.object(state, "SAVE_DIR", run_dir), patch.object(app_module, "load_config", return_value=config):
            session_id = state.create_session(gm_mode="full", character_id="hero")["id"]
            session = state.load_session(session_id)
            state.commit_world_position(session, location_id="dark_forest_loc")
            session["needs_opening"] = False
            if case_id == "heal":
                session["character"]["hp"] -= 5
            original_gold = session["character"]["gold"]
            with patch.object(app_module, "chat_completion", side_effect=completion), patch.object(state.random, "randint", return_value=10):
                public = app_module._run_turn(session, app_module.TurnRequest(text=text))
        passed = (public["current_location"] == destination and bool(public["in_combat"]) == expected_combat
                  and public["character"]["gold"] == original_gold
                  and bool(captured.get("plan"))
                  and (not operation or session.get("last_free_action", {}).get("operation") == operation))
        result = {"case": case_id, "input": text, "passed": passed,
                  "elapsed_seconds": round(time.monotonic() - started, 3), **captured,
                  "location": public["current_location"], "in_combat": public["in_combat"],
                  "reply": public["messages"][-1]["text"] if public["messages"] else ""}
        results.append(result)
        print(json.dumps({k: result[k] for k in ("case", "passed", "elapsed_seconds", "reply")}, ensure_ascii=False), flush=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"backend": backend, "model": config["backends"][backend]["model"],
                                 "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
