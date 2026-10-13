from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any

from host import state
from . import checkpoints, ch5, sim

CHARACTERS = ch5.CHARACTERS
LABELS = dict(none='无支援', king='国王', robin='ロビン', mina='ミーナ', robert='ローベルト',
              gald='ガルド/火油', charm='護符', ignis='イグニス（控制实验）',
              all_kill='击杀路线全满', all_purify='净化路线全满')


def cases() -> dict[str, dict[str, Any]]:
    result = ch5.cases()
    result['all_purify'] = result.pop('all')
    return result


def check_results(rows: list[dict[str, Any]], selected: list[str] | None = None) -> list[str]:
    errors = []
    required = ['none', *[case for case in selected if case != 'none']] if selected else list(cases())
    for case in required:
        for character in CHARACTERS:
            matches = [r for r in rows if r['case'] == case and r['character'] == character]
            if len(matches) != 1:
                errors.append(f'{character}/{case}: missing or duplicate')
    if errors:
        return errors
    for case in ('king', 'robin'):
        if case not in required:
            continue
        contribution = mean(r['contribution_pp'] for r in rows if r['case'] == case)
        if not 3 - 1e-9 <= contribution <= 8 + 1e-9:
            errors.append(f'{case}: mean contribution {contribution:.3f}pp outside [3,8]')
    for row in rows:
        if row['case'] == 'all_kill' and row['win_rate'] > .95:  # design 2026-10-12: a near-perfect run may reach 95%
            errors.append(f"{row['character']}/all_kill: win rate above 0.95")
    return errors


def evaluate(n: int, seed: int, *, selected: list[str] | None = None) -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    rows = []
    for character in CHARACTERS:
        baseline = 0.0
        for case, delta in cases().items():
            if selected and case != 'none' and case not in selected:
                continue
            row = sim.simulate(pack, 'draco_battle', character, n=n, seed=seed, checkpoints=cp,
                               preparation='purification' if case == 'all_purify' else 'standard',
                               initial_delta=delta, purify=False)
            if case == 'none':
                baseline = row['win_rate']
            row.update(case=case, contribution_pp=round((row['win_rate'] - baseline) * 100, 6))
            rows.append(row)
            print(f"{character}/{case}: {row['win_rate']:.4f} ({row['contribution_pp']:+.3f}pp)", flush=True)
    paths = [checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_SCENARIO.with_name('dragon_rpg_hybrid.json'),
             checkpoints.DEFAULT_CHECKPOINTS, Path(__file__), Path(ch5.__file__), Path(sim.__file__),
             Path(checkpoints.__file__), checkpoints.ROOT / 'host/combat.py',
             checkpoints.ROOT / 'scripts/scenario/tune_ch5.py']
    encounter = next(loc for loc in pack['locations'] if loc['id'] == 'draco_battle')['combat']
    return dict(n=n, seed=seed, supports=rows, selected=selected,
                violations=check_results(rows, selected), encounter=deepcopy(encounter),
                fingerprints={p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in paths})


def search(n: int, seed: int) -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    encounter = next(loc for loc in pack['locations'] if loc['id'] == 'draco_battle')['combat']
    modifiers = encounter['encounter_modifiers']
    king = next(m for m in modifiers if m['id'] == 'king')
    king.pop('round_start_attack', None)
    robin = next(m for m in modifiers if m['id'] == 'robin')
    robin.update(enemy_ids=['draco_human'], enemy_skill='剣聖の一閃', accuracy=-30, damage_multiplier=.8)
    base = [sim.simulate(pack, 'draco_battle', c, n=n, seed=seed, checkpoints=cp,
                         preparation='standard', purify=False)['win_rate'] for c in CHARACTERS]
    candidates = [('king', 'specified', None), ('robin', 'specified', None)]
    candidates += [('king', 'round_start_damage', damage) for damage in ('2', '4', '6', '8', '10', '12', '13', '16', '20', '1d6', '2d6')]
    candidates += [('robin', 'sword_only', pair) for pair in ((-60, .5), (-85, .2), (-90, 0))]
    candidates += [('robin', 'all_phase1_attacks', pair) for pair in ((-30, .8), (-60, .5), (-90, 0))]
    rows = []
    for key, variant, value in candidates:
        candidate = deepcopy(pack)
        candidate_modifiers = next(loc for loc in candidate['locations'] if loc['id'] == 'draco_battle')['combat']['encounter_modifiers']
        modifier = next(m for m in candidate_modifiers if m['id'] == key)
        if variant == 'round_start_damage':
            modifier['round_start_attack'] = dict(name='近衛兵', damage=value, accuracy=100, element='physical')
        elif value is not None:
            modifier.update(accuracy=value[0], damage_multiplier=value[1])
            if variant == 'all_phase1_attacks':
                candidate_modifiers.append({**deepcopy(modifier), 'enemy_skill': '氷刃'})
        rates = [sim.simulate(candidate, 'draco_battle', c, n=n, seed=seed, checkpoints=cp,
                              preparation='standard', initial_delta=ch5.SUPPORTS[key], purify=False)['win_rate']
                 for c in CHARACTERS]
        row = dict(support=key, variant=variant, value=value, rates=rates,
                   contribution_pp=round(mean((r - b) * 100 for r, b in zip(rates, base)), 6))
        rows.append(row)
        print(row, flush=True)
    return dict(n=n, seed=seed, characters=CHARACTERS, baseline=base, candidates=rows)


def markdown(result: dict[str, Any]) -> str:
    rows = result['supports']
    lines = ['# 025 决战支援调整报告', '',
             f"离线真实战斗引擎；heuristic；seed={result['seed']}；N={result['n']}/职业/条件。",
             '沿用023的Lv5可达checkpoint、装备、有限背包和单场满HP/MP/SP。击杀准备仅保留1个紅竜の炎核，移除其他火系能力；净化全满移除炎核并启用ignis_purified/ignis_ally，再加入全部支援。',
             '每项贡献为该项单独开启的胜率减去同职业无支援胜率，单位pp；不是留一法，不能相加。イグニス单项为与023一致的击杀准备控制实验；净化全满单独使用purification准备，不混用炎核。',
             'ロビン单项仅添加支援条件标志，不额外添加同行者；火油按已购2瓶计算，不折算80G机会成本。全满指决战支援齐备的单场胜率，不是连续通关率。', '',
             '|条件|勇者|僧侶|魔法使い|盗賊|四职业均值|', '|---|---:|---:|---:|---:|---:|']
    for case in cases():
        values = [next((r for r in rows if r['case'] == case and r['character'] == c), None) for c in CHARACTERS]
        if any(v is None for v in values):
            continue
        rates = [r['win_rate'] * 100 for r in values]
        lines.append('|' + LABELS[case] + '胜率|' + '|'.join(f'{v:.2f}%' for v in [*rates, mean(rates)]) + '|')
        if case in ch5.SUPPORTS:
            contributions = [r['contribution_pp'] for r in values]
            lines.append('|' + LABELS[case] + '贡献pp|' + '|'.join(f'{v:+.2f}' for v in [*contributions, mean(contributions)]) + '|')
    lines += ['', '025只对国王和ロビン的四职业平均贡献检查[3,8]pp；击杀全满按逐职业检查≤95%（026 后设计放宽）。净化全满约100%按设计接受，其他支援逐职业只报告。',
              '使用相同种子配对；支援可能改变行动选择及随机数消费，因此单职业负点估计不直接说明减伤反向生效。JSON保留胜负数、资源消耗、阶段回合、输入哈希和完整支援配置。', '',
              f"验收违规数：{len(result['violations'])}。", *[f'- {v}' for v in result['violations']], '']
    if result.get('selected'):
        lines += ['这是指定条件的部分复核，未覆盖025全部验收项。', '']
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline spec 025 support ablations')
    parser.add_argument('--n', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=20261012)
    parser.add_argument('--cases', nargs='+', choices=list(cases()))
    parser.add_argument('--search', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, default=checkpoints.ROOT / 'eval/reports/balance-2026-10-12-support')
    args = parser.parse_args(argv)
    result = search(args.n, args.seed) if args.search else evaluate(args.n, args.seed, selected=args.cases)
    args.output.with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.search:
        return 0
    args.output.with_suffix('.md').write_text(markdown(result), encoding='utf-8')
    return int(args.check and bool(result['violations']))


if __name__ == '__main__':
    raise SystemExit(main())
