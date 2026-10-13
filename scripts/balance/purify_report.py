from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from host import state
from scripts.scenario import redundancy
from . import checkpoints, route, sim


CHARACTERS = ("hero", "cleric", "mage", "thief")


def markdown(result: dict[str, Any]) -> str:
    lines = ["# イグニス净化数值报告（2026-10-12）", "",
             f"离线确定性引擎；heuristic；seed=20261012；单场每职业每条件 N={result['n']}；连续路线每职业 N={result['route_n']}。",
             "单场沿用可达 Lv5 checkpoint，HP/MP/SP 回满。ドラコ两阶段合计；击杀准备仅保留一枚紅竜の炎核，净化准备移除炎核并设置 ignis_ally，两组均移除其他火属性手段，其他资源相同。",
             "击杀对照不启用特殊行动。净化策略保留最后一份聖水；只有祈祷可用时预留 MP6；HP≤40% 后优先执行净化。不会读取未来随机数。", "",
             "|职业|击杀路线ドラコ胜率|净化路线ドラコ胜率|", "|---|---:|---:|"]
    for character in CHARACTERS:
        rows = {r["preparation"]: r for r in result["draco"] if r["character"] == character}
        lines.append(f"|{character}|{rows['standard']['win_rate']:.3f}|{rows['purification']['win_rate']:.3f}|")
    lines += ["", "目标逐职业核对：击杀 [0.50, 0.70]，净化 [0.65, 0.80]。本报告是调参使用的固定种子验收批次，不是独立留出评估；这些是样本胜率，接近边界的职业仍有抽样不确定性。", "",
              "|职业|到达40%平均回合|执行净化平均回合|直接打倒平均回合|净化/直接击杀成功数|",
              "|---|---:|---:|---:|---:|"]
    for character in CHARACTERS:
        rows = {r["purify"]: r for r in result["ignis"] if r["character"] == character}
        p, k = rows[True], rows[False]
        lines.append(f"|{character}|{p['threshold_rounds_mean']:.3f}|{p['success_rounds_mean']:.3f}|{k['success_rounds_mean']:.3f}|{p['outcomes'].get('purified', 0)}/{k['outcomes'].get('victory', 0)}|")
    lines += ["", "到达40%统计首次造成伤害后仍存活且HP≤40%的回合，按实际到达样本计；净化/击杀回合按各自成功样本计（含执行净化的行动），不把失败的短战斗当作成功提速。JSON同时报告全部样本平均回合和失败原因；两组用相同种子、相同初始资源，因保留聖水，后续随机流可能不同。", "",
              "|净化→真结局连续路线|完成率|到达ドラコ次数|失败地点及次数|", "|---|---:|---:|---|"]
    for row in result["routes"]:
        lines.append(f"|{row['character']}|{row['completion_rate']:.3f}|{row['boss_arrivals']}|{json.dumps(row['failure_counts'], ensure_ascii=False)}|")
    lines += ["", "连续路线从初始角色开始，保留跨战斗消耗，仅应用原有升级/剧情回复；途中保留最后一份聖水。イグニス若被打死而未净化，计入此路线未完成。净化后依次听证词、取鳞、请求援军、回城揭发；最终目标为 draco_defeated_with_ignis。连续路线只报告，不设阈值。", "",
              "|新关键资源|精灵泉路线来源数|砦路线来源数|", "|---|---:|---:|"]
    for key in ("purification_knowledge", "purification_means"):
        lines.append(f"|{key}|{result['redundancy']['counts']['spring'][key]}|{result['redundancy']['counts']['fort'][key]}|")
    lines += ["", "冗余检查逐个重放来源，确认在イグニス前获取、存在可用净化行动、并能继续到第五章；见证路径的战斗假定获胜。知识只计三类指定flag及白鳞片的战前来源，结冰调查成功/失败合并为同一来源；手段计支度金聖水、商店聖水、将军聖水、僧侣祈祷。职业来源不表示一个角色能兼任多个职业。", "",
              "## 实现与推断", "",
              f"- 援军火伤公式：`{result['ally_damage']}`，每回合一次，命中100%；沿用引擎公式的非负截断、火抗性、护甲与防御结算。援军只在白竜阶段激活，入场不另赠攻击；第一次伤害在下一个回合开始。",
              "- 援军作为战斗内的独立记录，复用同伴回合效果，不占同伴位，不进入可攻击敌人列表，也没有生命结算。",
              "- 条件行动声明 requirements、enemy_id、enemy_hp_ratio_lte、cost_item 或 cost_type/cost、outcome、effects、log_text；提交时再次校验，失败不扣费。",
              "- 特殊行动费用即时扣除，剧情效果通过现有 pending_state_delta 在收尾应用；不发击杀奖励、击败flag和炎核。",
              "- 新动作未指定 preview 时复用动作标题；once取鳞使用 received_ignis_scale 标记；新结局标题复用冒険完了。净化地点复用现有竜の谷背景和 enemy_ignis。",
              "- done_flag数组取任一为真；heard_ignis_testimony同步计入揭发条件和谜团线索计数。",
              "- 版本号沿用services前缀递增，适配现有存档的字符串版本比较，不修改存档刷新机制。", "",
              "## 文档矛盾、偏离与 TODO(design)", "",
              "- 第3.5节原列表没有证词，按第6.3节及任务说明追加 heard_ignis_testimony。",
              "- 第4.3节先称揭发和正常报告互斥，随后允许有证据仍正常报告；沿用现有后者规则，净化后也可正常报告。",
              "- 净化后可无判定取得白鳞片并保证揭发，但设计仍允许不取鳞就返回王城；实现保留指定的独立取鳞动作，不擅自强制领取。",
              "- 援军公式的高方差用于同时满足现有四职业胜率区间；TODO(design): 请审定这种伤害波动的体验。数值由本任务授权工程设定，未改职业、Boss、击杀奖励或已有技能数值。",
              "- TODO(design): 新图像及最终选图由014处理，本任务使用现有素材。",
              "- 没有无法实现的功能；没有修改默认提示词、benchmark标准答案、日语正文或设计文档；没有新增依赖或联网调用。", "",
              "## 验证和复现", "", "```powershell",
              f"python -m scripts.balance.purify_report --n {result['n']} --route-n {result['route_n']}",
              "python scripts/scenario/redundancy.py", "python -m unittest discover -s tests -q", "node --check client/app.js", "```", "",
              f"数值违规数：{len(result['violations'])}；冗余错误数：{len(result['redundancy']['errors'])}。",
              "原始JSON记录胜负数、资源消耗、阶段回合、连续路线资源与源文件SHA256。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline purification balance and continuous route report")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--route-n", type=int, default=500)
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/balance-2026-10-12-purify")
    args = parser.parse_args()
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    result: dict[str, Any] = dict(n=args.n, route_n=args.route_n, draco=[], ignis=[], routes=[], violations=[])
    result["ally_damage"] = next(e for e in pack["enemies"] if e["id"] == "draco_dragon")["phase_allies"][0]["round_start_effects"][0]["damage"]
    for preparation in ("standard", "purification"):
        rows = []
        for character in CHARACTERS:
            row = sim.simulate(pack, "draco_battle", character, n=args.n, seed=20261012, checkpoints=cp, preparation=preparation)
            rows.append(row)
            print(f"draco/{preparation}/{character}: {row['win_rate']:.3f}", flush=True)
        result["draco"].extend(rows)
        result["violations"].extend(sim.check_results(rows, targets))
    for character in CHARACTERS:
        purify, kill = [sim.simulate(pack, "dragon_valley_loc", character, n=args.n, seed=20261012,
                                    checkpoints=cp, purify=value) for value in (True, False)]
        result["ignis"].extend([purify, kill])
        if purify["outcomes"].get("victory", 0) or not purify["outcomes"].get("purified", 0):
            result["violations"].append(dict(character=character, metric="purification_outcome", outcomes=purify["outcomes"]))
        if purify["success_rounds_mean"] is None or kill["success_rounds_mean"] is None or purify["success_rounds_mean"] > kill["success_rounds_mean"]:
            result["violations"].append(dict(character=character, metric="purification_rounds"))
        print(f"ignis/{character}: purify {purify['success_rounds_mean']}, kill {kill['success_rounds_mean']}", flush=True)
    for character in CHARACTERS:
        row = route.simulate_route(pack, cp, character, encounter="draco_battle", n=args.route_n, seed=20261012, purify=True)
        result["routes"].append(row)
        print(f"route/{character}: {row['completion_rate']:.3f}", flush=True)
    result["redundancy"] = redundancy.check(pack, json.loads(redundancy.MANIFEST.read_text(encoding="utf-8")))
    paths = [checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_SCENARIO.with_name("dragon_rpg_hybrid.json"),
             checkpoints.DEFAULT_CHECKPOINTS, sim.TARGETS, redundancy.MANIFEST, Path(sim.__file__), Path(route.__file__),
             Path(__file__), checkpoints.ROOT / "host/combat.py"]
    result["fingerprints"] = {p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    return int(bool(result["violations"] or result["redundancy"]["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
