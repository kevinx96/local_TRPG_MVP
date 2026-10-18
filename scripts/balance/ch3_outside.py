"""Spec 037 companion checks outside their routes, using the 033/035 battle checkpoints."""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import state
from scripts.scenario.rumbling_gorge import BATTLES
from . import ch3_routes, checkpoints, economy, gorge, liese, sim

OUTPUT = checkpoints.ROOT / "eval/reports/037-companion-outside"


def comparisons(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for location, character in dict.fromkeys((r["location"], r["character"]) for r in rows):
        rates = {r["companion"]: r["win_rate"] for r in rows if (r["location"], r["character"]) == (location, character)}
        for companion, excluded in (("paladin_liese", liese.BATTLEFIELD), (gorge.ELIO, BATTLES)):
            if location in excluded:
                continue
            # Keep the original 033 comparison cohort; 035 includes Liese.
            controls = [cid for cid in liese.COMPANIONS if cid not in {"none", companion}]
            best = max(controls, key=rates.__getitem__)
            excess = 100 * (rates[companion] - rates[best])
            result.append(dict(location=location, character=character, companion=companion,
                baseline=rates["none"], win_rate=rates[companion], best=best, best_rate=rates[best],
                excess_pp=excess, passed=excess <= 3 + 1e-9))
    return result


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 037 第三轮：路线外同行者复核", "",
        f"逐战N={result['n']}，seed={result['seed']}，四职业，完全离线。", "",
        "复用033／035的可达逐战检查点、heuristic与有限背包；每场独立满资源，不等于连续路线通关率。自动枚举35场非剧情必败、允许同行者的遭遇，全部八种同行条件；リーゼ排除古戦場三场，エリオ排除峡谷三场。",
        "リーゼ的旧同行者对照沿用033（不把后来加入的エリオ算作抬高上限的依据）；エリオ沿用035（包含本轮リーゼ）。所有对照同N、同起始种子重新计算，耗骰不保证逐骰一致。",
        "", "|同行者|职业|遭遇|无同行|本轮|旧同行者最强|最强胜率|超出pp|≤3pp|", "|---|---|---|---:|---:|---|---:|---:|---|"]
    for r in result["comparisons"]:
        lines.append(f"|{r['companion']}|{r['character']}|{r['location']}|{r['baseline']:.2%}|{r['win_rate']:.2%}|{r['best']}|{r['best_rate']:.2%}|{r['excess_pp']:+.2f}|{r['passed']}|")
    failures = [r for r in result["comparisons"] if not r["passed"]]
    lines += ["", f"越界：{len(failures)}/{len(result['comparisons'])}项。",
        "", "本轮固定采用リーゼ20%／2d6、エリオ2d6／4回合。本路线严格最强仅以未准备、无诅咒的核心8项为门槛；上述路线外上限若未达标，逐项如实列出，不继续调参。第二轮结果保留在[报告](037-companion-outside-round2.md)和[JSON](037-companion-outside-round2.json)。", "",
        "```powershell", f"python -X utf8 -m scripts.balance.ch3_outside --n {result['n']} --seed {result['seed']} --workers {result['workers']}", "```", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if min(args.n, args.workers) < 1:
        parser.error("n and workers must be positive")
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    starts = gorge.starts(pack, cp)
    jobs = []
    for location in [*BATTLES, *gorge.outside_locations(pack)]:
        for character in liese.CHARACTERS:
            if location in (*BATTLES, *liese.BATTLEFIELD):
                template = deepcopy(starts[character], {id(pack): pack})
                state.apply_state_delta(template, {"current_location": location}, allow_world_transition=True)
            else:
                point = cp if location in cp["encounters"] else economy.encounter_checkpoint(pack, cp, location, character)
                template = sim.prepare_session(pack, location, character, point, companion=False)
            jobs.append((location, character, template, ch3_routes.COMPANIONS, args.n, args.seed))
    files = (Path(__file__), Path(gorge.__file__), Path(liese.__file__), Path(sim.__file__), Path(checkpoints.__file__),
             checkpoints.DEFAULT_SCENARIO, *sorted((checkpoints.ROOT / "host").glob("*.py")))
    result = dict(n=args.n, seed=args.seed, workers=args.workers, rows=[],
        companions=[c for c in pack["companions"] if c["id"] in ch3_routes.COUNTERS.values()],
        fingerprints={p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for group in gorge._map_jobs(gorge._battle_job, jobs, args.workers):
        result["rows"].extend(group)
        print(group[0]["location"], group[0]["character"], flush=True)
        args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    result["comparisons"] = comparisons(result["rows"])
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
