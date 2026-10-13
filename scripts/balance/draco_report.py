from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from host import state
from scripts.scenario import redundancy
from . import checkpoints, route, sim


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 白竜ドラコ数值与可达性报告（2026-10-12）", "",
             "离线确定性引擎；heuristic；seed=20261012；每职业每准备条件 N=" + str(result["n"]) + "。",
             "单场使用可达路线生成的 Lv5 checkpoint，HP/MP/SP 回满；标准准备只保留一枚紅竜の炎核，移除其他火属性技能、物品及火属性同伴。无火条件再移除炎核。两条件其他资源相同。",
             "阶段回合按到达该阶段的全部样本（含败北）计算，变身回合同时计入两个阶段；胜利必须击败最终阶段。日志截断不影响阶段计数。", "",
             "|职业|准备|胜利/N|胜率|人形平均回合|竜形平均回合|竜形到达数|",
             "|---|---|---:|---:|---:|---:|---:|"]
    for row in result["rows"]:
        phases = row["phase_rounds_mean"]
        lines.append(f"|{row['character']}|{row['preparation']}|{round(row['win_rate'] * row['n'])}/{row['n']}|{row['win_rate']:.3f}|{phases.get('draco_human', 0):.3f}|{phases.get('draco_dragon', 0):.3f}|{row['phase_reached'].get('draco_dragon', 0)}|")
    lines += ["", "标准准备目标 [0.50, 0.70]、无火目标 <0.30；0/1000 只是本批样本的观测结果。", "",
              "|连续真结局路线职业|完成率|到达ドラコ次数|失败地点（次数）|",
              "|---|---:|---:|---|"]
    for row in result["routes"]:
        lines.append(f"|{row['character']}|{row['completion_rate']:.3f}|{row['boss_arrivals']}|{json.dumps(row['failure_counts'], ensure_ascii=False)}|")
    lines += ["", "连续路线从初始角色出发，按 checkpoint 动作推进；每场实际战斗，保留消耗，只应用原有剧情/升级回复，不额外补满。路线仍保留职业自带火技能；连续路线只报告、不设阈值。", "",
              "|来源类别|精灵泉主线（含往返/支线）|砦主线（含往返/支线）|",
              "|---|---:|---:|"]
    counts = result["redundancy"]["counts"]
    for key, value in counts["spring"].items():
        lines.append(f"|{key}|{value}|{counts['fort'][key]}|")
    lines += ["", "每个来源有独立动作见证路径，检查金币、物品、flag、once、地点迁移及实际发放效果。战斗在可达性见证中假定获胜；职业来源只在对应职业计入，不代表单角色能拥有所有来源。允许回城、重访十字路和可选砦支线；精灵泉主线的砦来源来自支线重访。", "",
              "## 数值与实现选择", "",
              "- ドラコ人形 HP25；竜形 HP220。火弱点1.5、冰抗性0.25按设计；额外物理/圣抗性0.25用于把既有盗贼高爆发及圣水纳入同一准备门槛。",
              "- 炎核伤害1d100+100、命中100%、一次消耗；高方差使准备提升胜率而非保证胜利。没有改动已有职业技能数值。",
              "- 護衛の構え使用两回合0.6减伤状态；雪嵐の咆哮使当前及下回合防御倍率失效，不抹除玩家其他状态。",
              "- heuristic 根据已声明的下一阶段抗性保留属性消耗品，不读取随机数；仅在下一阶段更弱于该属性时延后使用。",
              "- 标准准备中的魔法使移除火球・改，是人为控制变量的对照条件；自然连续路线保留职业技能。", "",
              "## 文档矛盾、推断和 TODO(design)", "",
              "- 第4.3节先写两个动作互斥，末尾又要求有证据仍可正常汇报；按任务第5节和后一条实现，同时保留正常汇报。",
              "- 设计第0节要求至少3来源，任务要求每路线至少2（白鳞片3）；实际五类关键资源均达3以上。支度金指定仅一次，三个可替代线索flag指定单来源；这些单独校验与报告，不擅自增写来源。",
              "- 原图缺少村庄入口、攻略后回宿屋及冰结晶返回锻冶屋的路径。新增森林出口↔宿屋、村庄↔王城及村庄↔结冰点连接；用既有地点/动作措辞，并按原里程碑标记抵达村庄。",
              "- 新动作缺省 preview/intent_keywords 复用动作标题；未提供的观察成功/失败短句采用现有术语，once 消耗一次尝试（成功和失败均不可刷取）。将军18阈值采用现有1d20总值，等于裸骰出目。",
              "- 报告统计按四职业分别验证，不把职业来源叠加给单一角色；原商店药草保留三份库存，单价按第4.7节改为10G。",
              "- 多阶段在同一玩家动作结算后转换，剩余行动及敌人回合照常；敌人满血、清状态，玩家不回复。已完成阶段奖励仅在最终胜利时结算。",
              "- 旧版已结束的イグニス存档保持原结局，不强制复活或补发剧情；刷新场景数据后仍能加载。",
              "- TODO(design): ドラコ人形和白竜图像最终选图；当前分别复用 npc_general / enemy_ignis，地图复用王城背景。",
              "- TODO(design): 请审定上述最小往返连接及额外物理/圣抗性、炎核高方差；当前按工程可达性与给定胜率目标实现。", "",
              "没有新增依赖，没有修改默认提示词、benchmark 标准答案或设计文档。", "",
              "## 复现", "", "```powershell",
              f"python -m scripts.balance.draco_report --n {result['n']} --route-n {result['route_n']}",
              "python scripts/scenario/redundancy.py",
              "python -m unittest discover -s tests -q", "node --check client/app.js", "```", "",
              "数值目标违规数：" + str(len(result["violations"])) + "；冗余错误数：" + str(len(result["redundancy"]["errors"])) + "。", "",
              "原始 JSON 含每条件的消耗品、资源消耗、阶段到达数、败北原因、连续路线到达资源和源文件 SHA256。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Draco balance and true-ending route report")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--route-n", type=int, default=500)
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/balance-2026-10-12-draco")
    args = parser.parse_args()
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    result: dict[str, Any] = dict(n=args.n, route_n=args.route_n, rows=[], routes=[], violations=[])
    for preparation in ("standard", "no_fire"):
        rows = []
        for character in ("hero", "cleric", "mage", "thief"):
            row = sim.simulate(pack, "draco_battle", character, n=args.n, seed=20261012, checkpoints=cp, preparation=preparation)
            rows.append(row)
            print(f"{preparation}/{character}: {row['win_rate']:.3f}", flush=True)
        result["rows"].extend(rows)
        result["violations"].extend(sim.check_results(rows, targets))
    for character in ("hero", "cleric", "mage", "thief"):
        row = route.simulate_route(pack, cp, character, encounter="draco_battle", n=args.route_n, seed=20261012)
        result["routes"].append(row)
        print(f"route/{character}: {row['completion_rate']:.3f}", flush=True)
    result["redundancy"] = redundancy.check(pack, json.loads(redundancy.MANIFEST.read_text(encoding="utf-8")))
    result["fingerprints"] = {p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_CHECKPOINTS, sim.TARGETS,
                                        checkpoints.ROOT / "host/combat.py", Path(sim.__file__), Path(route.__file__))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    return int(bool(result["violations"] or result["redundancy"]["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
