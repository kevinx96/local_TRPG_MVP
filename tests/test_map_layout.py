from __future__ import annotations

import math
import unittest
from copy import deepcopy
from typing import Any

from host import state
from scripts.balance.checkpoints import DEFAULT_SCENARIO, ROOT
from scripts.scenario.tune_ch5 import tune_maps


def edge_node_collisions(map_data: dict[str, Any], width: float, height: float,
                         radius: float) -> list[tuple[str, str, str]]:
    nodes = {n['id']: (n['x'] * width / 100, n['y'] * height / 100) for n in map_data['nodes']}
    collisions = []
    for edge in map_data['edges']:
        start, end = edge['from'], edge['to']
        ax, ay = nodes[start]
        bx, by = nodes[end]
        dx, dy = bx - ax, by - ay
        length_squared = dx * dx + dy * dy
        for identifier, (x, y) in nodes.items():
            if identifier in (start, end):
                continue
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / length_squared)) if length_squared else 0
            if math.hypot(x - ax - t * dx, y - ay - t * dy) <= radius:
                collisions.append((start, end, identifier))
    return collisions


class MapLayoutTests(unittest.TestCase):
    def test_all_edges_clear_other_nodes_in_both_packs(self):
        for filename in ('dragon_rpg.json', 'dragon_rpg_hybrid.json'):
            pack = state.load_scenario_pack(DEFAULT_SCENARIO.with_name(filename))
            for map_data in pack['maps']:
                # Mini-map content box; full map at 320px and 1280px viewport widths.
                for width, height, radius in ((198, 138, 9.5), (268.8, 300, 20), (1152, 600, 20)):
                    with self.subTest(pack=filename, map=map_data['id'], width=width):
                        self.assertEqual(edge_node_collisions(map_data, width, height, radius), [])

    def test_radius_matches_frontend(self):
        css = (ROOT / 'client/styles.css').read_text(encoding='utf-8')
        self.assertRegex(css, r'(?m)^\.map-node \{[^}]*width: 40px; height: 40px;')
        self.assertRegex(css, r'(?m)^\.mini-map \.map-node \{[^}]*width: 19px; height: 19px;')
        self.assertRegex(css, r'(?m)^\.mini-map \{[^}]*width: 200px; height: 140px; border: 1px')

    def test_geometry_detects_radius_not_only_collinearity(self):
        def fixture(x: float, y: float, end: float = 100) -> dict[str, Any]:
            return dict(nodes=[dict(id='a', x=0, y=0), dict(id='b', x=end, y=0), dict(id='c', x=x, y=y)],
                        edges=[{'from': 'a', 'to': 'b'}])
        for map_data in (fixture(50, 0), fixture(50, 9), fixture(50, 10), fixture(3, 4, end=0)):
            self.assertEqual(edge_node_collisions(map_data, 100, 100, 10), [('a', 'b', 'c')])
        for map_data in (fixture(50, 11), fixture(120, 0)):
            self.assertEqual(edge_node_collisions(map_data, 100, 100, 10), [])

    def test_old_layouts_fail_and_tuning_is_idempotent(self):
        pack = state.load_scenario_pack(DEFAULT_SCENARIO)
        for map_data in pack['maps']:
            if map_data['id'] == 'royal_return':
                next(n for n in map_data['nodes'] if n['id'] == 'R5')['y'] = 50
                self.assertIn(('R2', 'R5', 'R4'), edge_node_collisions(map_data, 198, 138, 9.5))
            if map_data['id'] == 'forest':
                for node in map_data['nodes']:
                    if node['id'] in ('F3', 'F4'):
                        node['y'] = 65
                self.assertEqual(edge_node_collisions(map_data, 198, 138, 9.5),
                                 [('F2', 'F5', 'F3'), ('F2', 'F5', 'F4')])
        tune_maps(pack)
        before = deepcopy(pack)
        tune_maps(pack)
        self.assertEqual(pack, before)
        self.assertEqual(pack, state.load_scenario_pack(DEFAULT_SCENARIO))
