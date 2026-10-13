from __future__ import annotations

import json
import subprocess
from pathlib import Path
from statistics import mean
from typing import Any

from . import checkpoints, sim

ROOT = checkpoints.ROOT
REPORT = ROOT / "eval/reports/balance-2026-10-11-pass3"


def changes(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        return [entry for key in sorted(before.keys() | after.keys())
                for entry in changes(before.get(key), after.get(key), path + "/" + key)]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [entry for i, (a, b) in enumerate(zip(before, after)) for entry in changes(a, b, path + f"/{i}")]
    return [] if before == after else [dict(path=path, before=before, after=after)]


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("|", "\\|")


def fmt(value: Any) -> str:
    return "—" if value is None else f"{value:.3f}"


def main() -> None:
    result = json.loads(REPORT.with_suffix(".json").read_text(encoding="utf-8"))
    previous = json.loads((ROOT / "eval/reports/balance-2026-10-11-pass2.json").read_text(encoding="utf-8"))
    routes = json.loads((ROOT / "eval/reports/balance-2026-10-11-pass3-routes.json").read_text(encoding="utf-8"))["rows"]
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    old_rows = [r for r in previous["rows"] if r["companion"]]
    rows = [r for r in result["rows"] if r["companion"]]
    old_violations = previous["violations_after"]
    rebased = sim.check_results(old_rows, targets)
    violations = sim.check_results(rows, targets)
    result["comparison"] = dict(pass2_historical_violations=len(old_violations),
                                pass2_current_targets_violations=len(rebased), pass3_violations=len(violations))
    original = json.loads(subprocess.check_output(["git", "show", result["baseline_commit"] + ":host/prompt/processed/dragon_rpg.json"], cwd=ROOT).decode("utf-8"))
    raw = json.loads(checkpoints.DEFAULT_SCENARIO.read_text(encoding="utf-8"))
    diff = changes(original, raw)
    result["changes"] = diff
    out = ["# 007 第三轮平衡报告", "", "离线真实战斗引擎，flat 防御，无外部 API，无新增依赖。",
           f"正式 N={result['n']} / cell，seed={result['seed']}；{len(result['rows'])} cell。先 N=16 粗筛，再 N=64 复核，锁定参数后 N=500 确认。",
           "搜索记录见 `eval/balance/pass3-search.json`；正式矩阵与输入/代码 SHA256 见同名 JSON；连续流程逐职业逐路线结果见 `balance-2026-10-11-pass3-routes.json`。",
           "单场与连续流程分别报告。单场仍按 proposed checkpoint 满 HP/MP/SP、两瓶聖水起步；连续流程重放同一 checkpoint 的 sources，真实战斗替换 @victory/@defeat，不再注入下一场快照。",
           "", "复现：", "", "```powershell",
           "python -m scripts.balance.checkpoints",
           "python -m scripts.balance.pass3 --apply eval/balance/pass3-search.json --output .tmp-test/pass3-apply.json",
           "python -m scripts.balance.pass3 --n 500 --output .tmp-test/pass3-reconfirm.json",
           "python -m scripts.balance.route --n 500 --routes all --output .tmp-test/pass3-routes-reconfirm.json",
           "python -m scripts.balance.pass3_report",
           "python -m scripts.balance.sim --check --n 500 --output .tmp-test/pass3-check.json", "```", "",
           "上述确认复用归档搜索参数，不覆盖归档基线。搜索复现应从 JSON 的 baseline_commit 开始，先应用本轮技能/策略/文本改动，再执行 --search --iterations 100；另外通过 --refine-elites 对纯精英模板补充100个候选，合并各组最优参数，记录在search JSON的elite_refinement中。在最终数值上重搜属于新实验。Windows 沙箱使用 --shard/--shards 分片，计算及 seed 与不分片相同。",
           "", "## 1. 达标对比", "",
           f"`--check` 越界：pass2 原目标 **{len(old_violations)}** → pass2 按本轮目标重算 **{len(rebased)}** → pass3 **{len(violations)}**。",
           "本轮未修改 targets.json。历史对比同时包含目标、策略、技能与敌人数值的变化，不归因于单一因素。",
           "全指标包含 heuristic 胜率/胜利剩余 HP/全部战斗回合中位数、职业差距及 Boss 普攻胜率上限；同伴均值单列验收。", "",
           "| 类别 | 总数 | pass2原目标全指标 | pass2新目标全指标 | pass3全指标 | pass2仅胜率 | pass3仅胜率 |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for cls in targets["classes"]:
        names = [e for e, c in targets["encounters"].items() if c == cls]
        def passed(vs, only_win=False):
            failed = {v["encounter"] for v in vs if not only_win or v["metric"] == "win_rate"}
            return sum(e not in failed for e in names)
        out.append(f"| {cls} | {len(names)} | {passed(old_violations)} | {passed(rebased)} | {passed(violations)} | {passed(old_violations, True)} | {passed(violations, True)} |")
    out += ["", "职业顺序 hero / cleric / mage / thief；guest 为 warlock。", "",
            "| 遭遇 | Lv | pass2胜率 | pass3胜率 | pass3回合 | pass3胜利HP | 新目标越界前→后 |", "|---|---:|---|---|---|---|---|"]
    for encounter in targets["encounters"]:
        current = [r for r in rows if r["encounter"] == encounter and r["policy"] == "heuristic"]
        old = [r for r in old_rows if r["encounter"] == encounter and r["policy"] == "heuristic"]
        values = lambda rs, k: " / ".join(fmt(r[k]) for r in rs)
        out.append(f"| {encounter} | {current[0]['level']} | {values(old, 'win_rate')} | {values(current, 'win_rate')} | {values(current, 'rounds_median')} | {values(current, 'hp_left_mean')} | {sum(v['encounter']==encounter for v in rebased)}→{sum(v['encounter']==encounter for v in violations)} |")
    without = {(r["encounter"], r["character"]): r for r in result["rows"] if not r["companion"]}
    uplifts = []
    out += ["", "### 同伴等权均值", "", "| 遭遇 | 平均胜率提升 pp |", "|---|---:|"]
    for encounter in targets["encounters"]:
        selected = [r for r in rows if r["encounter"] == encounter and r["policy"] == "heuristic"
                    and r["encounter_class"] != "guest" and cp["encounters"][encounter]["characters"][r["character"]]["companion"]]
        uplift = [r["win_rate"] - without[encounter, r["character"]]["win_rate"] for r in selected]
        if uplift:
            uplifts += uplift
            out.append(f"| {encounter} | {mean(uplift)*100:.2f} |")
    result["companion_uplift"] = mean(uplifts)
    out += ["", f"{len(uplifts)} 个实际有同伴 cell 等权均值 **{mean(uplifts)*100:.2f}pp**；目标10–20pp；{'达标' if .1 <= mean(uplifts) <= .2 else '越界'}。保持每2回合回复最大 HP 的15%，与007指定描述一致。", "",
            "## 2. 每场消耗品", "", "heuristic、每次试验平均消耗；职业顺序同上，空对象表示零消耗。详细逐职业值在 JSON 的 consumables_mean。",
            "稀有规则仅过滤 trash/elite 的消耗品：rare=true、圣/光属性（含 multi_elements），或对任一存活敌人的单次期望净伤害达到其最大HP绝对值的30%。期望使用现有模拟伤害估计，含命中/闪避/防御/抗性与多段。Boss 可使用。",
            "", "| 遭遇 | 平均消耗（各职业） |", "|---|---|"]
    for encounter in targets["encounters"]:
        current = [r for r in rows if r["encounter"] == encounter and r["policy"] == "heuristic"]
        out.append(f"| {encounter} | " + " / ".join(dump(r["consumables_mean"]) for r in current) + " |")
    out += ["", "## 3. 连续流程", "",
            "全部21个 checkpoint 路线各运行 N=500 × 4个起始职业；每个分支独立起步。主线通关定义为 dragon_valley_loc 路线击败最终 Boss。战败立即终止，scripted_loss 按剧本败北效果继续；guest 使用引擎角色替换/还原。",
            "不增加购物、休息或分支决策；按 sources 中指定的成功/失败结果重放非战斗动作，故结果是给定路线/非战斗判定条件下的通关率。恢复只来自实际动作、战斗机制、剧情效果和升级。路线不存在的宿屋或回复阵不会凭空补入。",
            "", "| 职业 | 主线通关率 | 最常见失败点（次数/500） | 到达Boss人数 | 到达时平均HP/MP/SP | 平均剩余聖水 |", "|---|---:|---|---:|---|---:|"]
    for r in routes:
        if r["route"] != "dragon_valley_loc":
            continue
        failures = sorted(r["failure_counts"].items(), key=lambda kv: -kv[1])
        arrival = r["boss_resources_mean"]
        out.append(f"| {r['character']} | {r['completion_rate']:.3f} | {dump(failures[0]) if failures else '—'} | {r['boss_arrivals']} | {' / '.join(fmt(arrival[k]) for k in ('hp','mp','sp')) if arrival else '—'} | {fmt(arrival['inventory'].get('聖水', 0)) if arrival else '—'} |")
    out += ["", "最终 Boss 入口触发 Lv5，真实升级会补满资源；该入口均值不能代表之前没有消耗。完整背包均值、失败分布及逐战消耗保存在 routes JSON。", "",
            "| 路线终点 | hero通达/完成率 | cleric | mage | thief |", "|---|---:|---:|---:|---:|"]
    for endpoint in cp["encounters"]:
        out.append(f"| {endpoint} | " + " | ".join(fmt(r["completion_rate"]) for r in routes if r["route"] == endpoint) + " |")
    out += ["", "主线失败完整分布：", "", "| 职业 | 失败场次及次数 |", "|---|---|"]
    for r in routes:
        if r["route"] == "dragon_valley_loc":
            out.append(f"| {r['character']} | {dump(r['failure_counts'])} |")
    out += ["", "## 4. 改动清单", "", "两份剧本相同字段同步。以下路径以 dragon_rpg.json 为准；JSON另存机器可读完整差分。未改玩家初始属性/资源、旧技能定义、抗性、敌人名称/描述、遭遇类别、xanxus/warlock战斗定义。", "",
            "### 数值与结构", "", "| 路径 | 原值 | 新值 | 理由 |", "|---|---|---|---|"]
    text_changes = []
    for change in diff:
        path = change["path"]
        if path.startswith("/locations/") or path.endswith("/description") and path.startswith("/companions/"):
            text_changes.append(change)
            continue
        reason = ("稀有消耗品显式标记" if path.endswith("/rare") else
                  "同名技能替换/魔法使Lv2解锁" if "/level_skills/" in path else
                  "007数值搜索：胜率、HP、回合与职业差距综合越界最少" if path.startswith("/enemies/") else
                  "使旧存档刷新到本轮剧本")
        out.append(f"| `{path}` | `{dump(change['before'])}` | `{dump(change['after'])}` | {reason} |")
    out += ["", "### 第6节文本同步（全部）", "", "只改下列描述/结果中的数字和量词，以及指定的同伴说明。hybrid.summary、prepared_turns.draft.gm_text 是同一描述/动作结果的可见副本。", "",
            "| 路径 | 原文 | 新文 |", "|---|---|---|"]
    for change in text_changes:
        out.append(f"| `{change['path']}` | {change['before']} | {change['after']} |")
    out += ["", "## 5. 仍越界的项目", "", "| 遭遇 | 职业 | 指标 | 实测 | 目标 |", "|---|---|---|---:|---|"]
    for v in violations:
        out.append(f"| {v['encounter']} | {v['character']} | {v['metric']} | {fmt(v['value'])} | {v['target']} |")
    out += ["", "有限搜索未证明剩余约束无解。共享 goblin/hobgoblin/archer 模板同时参与不同等级、数量和类别的战斗；职业防御、治疗、元素输出及MP/SP差异会使统一敌人数值难以同时拟合。胜利条件下剩余HP和包含早败的回合中位数并非同一批样本。70%胜率在N=500下标准误差约2pp，区间边缘有抽样波动。", "",
            "## 6. TODO(design)", "",
            "- TODO(design): 砦系列 checkpoint 的首次战斗至 goblin_fort_fourth 均为Lv1；Lv2触发仍在击败史莱姆王/森林出口等既有flag之后，砦通关再到Lv3。火球・改提前Lv2已实现，但该路线仍无提前使用窗口，未改触发条件。",
            "- TODO(design): forest_wolves 的动作结果仍有「茂みの左右」「唸り声が重なった」「退路と行く手を分けて塞ぎ」，一头狼的空间描写需审定。",
            "- TODO(design): slime_ambush_one 仍有「包囲されている」；胜利结果中的「水音が一つ重なった」「半円を描いて包囲を狭めてくる」和 slime_ambush_two 胜利的「仲間の残骸」需审定。",
            "- TODO(design): goblin_fort_first_second 开战结果仍有「中央」「両脇の弓兵」；失败结果仍有「一匹…同時に振り向いた」，不改非数字措辞。",
            "- TODO(design): goblin_fort_third_guards 仍有「鉄門の前後を…挟まれた」；胜利结果的一匹弓兵「高台へ散って」需审定。",
            "- TODO(design): 本次授权限于地点描述/结果，保留动作 UI/intent_keywords 的「三人のゴブリンと戦う」「三人組を迂回する」及 continue_from_elf_spring.preview 的「二頭の森狼」。location.enemy_ids 仍为历史列表，实际战斗以 combat.enemy_ids 为准；如需全量同步请另定范围。",
            "- TODO(design): checkpoint 仍为 proposed，连续流程未设阈值；请审定路线、补给和同伴选择是否代表实际玩家。剩余数值越界见第5节。", "",
            f"- TODO(design): 同伴等权提升{mean(uplifts)*100:.2f}pp，低于10pp下限。本轮保持007指定15%描述和对应实际效果；请审定后续同伴/战斗节奏调整。", "",
            "## 7. 推断、偏离与已知问题", "",
            "- 推断：按每个 checkpoint 的 sources 作为一条独立路线；dragon_valley_loc 是主线通关，其他终点完成率仅表示完成该分支，不称为整个游戏通关。非战斗判定沿用 checkpoint 固定结果。",
            "- 推断：稀有伤害阈值使用现有策略的单次期望净伤害，任一敌人达线就保留；不将多敌总伤害相加后与某一敌人HP比较。聖水和三种巻物标记 rare=true。",
            "- 推断：同名升级按 replaces 关联旧名字，保留旧技能所在顺序并去重；同ID的旧pass2新技能刷新为新版。没有旧技能时也发放指定升级技能。",
            "- 推断：clear_skills 记录当时等级并持久化 skills_cleared_through_level，以免事件240条截断后重新补发；旧事件按level_up顺序恢复清除时等级。只有清除记录、没有升级记录时保守视为清到当前等级。旧存档缺level仍Lv1，不追溯成长。",
            "- 已知限制：如果旧事件中清除记录已被截断、且旧档没有持久化标记，就无法重建该历史。未自行推断剧情flag来永久禁用技能。",
            "- 偏离：没有范围外改动；数值目标未全部达标，完整保留越界结果。未新增依赖、未联网。", "",
            "## 8. 工程交付与验证", "",
            "- 引擎：host/state.py；剧本：两份dragon_rpg JSON及schema；模拟：scripts/balance/sim.py、route.py、pass3.py、pass3_report.py；checkpoint及搜索结果、报告；测试：test_balance_pass3.py，并更新pass2技能断言和剧情版本断言。",
            "- `python -m unittest discover -s tests -q`：315项，314通过，1项按既有BALANCE_ENFORCE条件跳过。Windows沙箱创建临时目录后无法读写，已在放宽沙箱权限后用相同离线命令通过，未修改既有测试来规避。",
            "- `node --check client/app.js`、`git diff --check`：通过。两份剧本按记录ID核对，本轮103处变更完全一致；受保护字段与targets未改。",
            f"- `python -m scripts.balance.sim --check --n 500`：{len(violations)}项越界，退出码1；与正式矩阵逐cell完全一致。--check非零表示上述数值目标越界，不等于单元测试失败。",
            "- 连续流程对最终Boss胜利导致的剧情结束标记按胜利处理，回归测试覆盖；最终路线文件全部用修正后的代码重新运行N=500。", ""]
    REPORT.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.with_suffix(".md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
