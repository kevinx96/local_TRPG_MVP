from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

from host import state
from . import checkpoints, ch5, sim, support


def search(n: int, seed: int) -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    modifier = next(m for loc in pack['locations'] if loc['id'] == 'draco_battle'
                    for m in loc['combat']['encounter_modifiers'] if m['id'] == 'robin_dragon')
    baseline = [sim.simulate(pack, 'draco_battle', c, n=n, seed=seed, checkpoints=cp,
                             preparation='standard', purify=False) for c in ch5.CHARACTERS]
    candidates = []
    for percent in range(90, 74, -1):
        modifier['enemy_hp_multiplier'] = percent / 100
        rows = [sim.simulate(pack, 'draco_battle', c, n=n, seed=seed, checkpoints=cp,
                             preparation='standard', initial_delta=ch5.SUPPORTS['robin'], purify=False)
                for c in ch5.CHARACTERS]
        contributions = [(row['win_rate'] - base['win_rate']) * 100 for row, base in zip(rows, baseline)]
        candidate = dict(multiplier=percent / 100, supports=rows, contribution_pp=contributions,
                         mean_contribution_pp=round(mean(contributions), 6))
        candidates.append(candidate)
        print(f"HP x{percent / 100:.2f}: {candidate['mean_contribution_pp']:+.3f}pp", flush=True)
    paths = [checkpoints.DEFAULT_SCENARIO, Path(__file__), Path(sim.__file__),
             Path(checkpoints.__file__), checkpoints.ROOT / 'host/combat.py']
    return dict(n=n, seed=seed, characters=ch5.CHARACTERS, baseline=baseline, candidates=candidates,
                fingerprints={p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in paths})


def markdown(result: dict[str, Any]) -> str:
    text = support.markdown(result).replace('# 025 决战支援调整报告', '# 026 ロビン二阶段支援报告')
    text = text.replace('025只对国王和ロビン', '沿用025对国王和ロビン')
    text = text.replace('未覆盖025全部验收项', '未覆盖全部支援回归条件')
    modifier = next(m for m in result['encounter']['encounter_modifiers'] if m['id'] == 'robin_dragon')
    return text + f"\nロビン：一阶段仅剧情提示；二阶段最大和当前HP×{modifier['enemy_hp_multiplier']:.2f}，只施加一次。\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline spec 026 phase-two HP support ablations')
    parser.add_argument('--n', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=20261012)
    parser.add_argument('--search', action='store_true')
    parser.add_argument('--cases', nargs='+', choices=list(support.cases()))
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, default=checkpoints.ROOT / 'eval/reports/balance-2026-10-12-support2')
    args = parser.parse_args(argv)
    result = search(args.n, args.seed) if args.search else support.evaluate(args.n, args.seed, selected=args.cases)
    result['fingerprints']['scripts/balance/support2.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.search:
        return 0
    args.output.with_suffix('.md').write_text(markdown(result), encoding='utf-8')
    return int(args.check and bool(result['violations']))


if __name__ == '__main__':
    raise SystemExit(main())
