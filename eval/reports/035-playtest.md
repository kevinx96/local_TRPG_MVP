# 离线试玩回归（035-playtest）

4 职业 × 2 固定种子（20261013、20261014），每局最多 150 步；战斗每个指令和结算各占一步。
首次战斗死亡后重来一次，选择次数及随机流继续累计。选项、判定和战斗的随机数均固定。
031：奇数种子首次到森林出口时优先古戦場；进入后依次潜行骨野、访问塔、取外套休息、潜行沼地、通过礼拝堂。诅咒持有者使用专属放行，至少2局通过新地图。
033：首次到温泉或古戦場入口时优先城塞支路；按本営取得推薦状、礼拝堂招募、工房、宿屋、见张台的顺序访问，再南下古戦場。仅调整行动优先度，不注入状态或强制判定成功。
035：奇数种子在本営请求开峠、宿屋尝试三种エリオ招募，再走峡谷；依次潜行、营地补给与休息、查爪痕、通过巨人与ワーム，汇入避難所。偶数种子保留古戦場优先度。
LLM 配置指向 127.0.0.1:1，并在请求适配器直接模拟连接失败；禁止真实网络。

| 职业 | 种子 | 首次死亡 | 重来后结果 / 最终结果 | 最远地点 | 步数 |
|---|---:|---|---|---|---:|
| hero | 20261013 | 无 | ignis_purified @ castle_report | castle_report | 115 |
| hero | 20261014 | 无 | step_limit @ dragon_valley_loc | dragon_valley_loc | 150 |
| cleric | 20261013 | 无 | draco_defeated_with_ignis @ draco_battle | draco_battle | 130 |
| cleric | 20261014 | 无 | step_limit @ valley_nest_gate | xanxus_at_nest | 150 |
| mage | 20261013 | goblin_fort_fourth | goblin_fort_fourth_defeat @ goblin_fort_fourth | goblin_fort_fourth | 86 |
| mage | 20261014 | lost_goblin_crossroads | goblin_fort_fourth_defeat @ goblin_fort_fourth | goblin_fort_fourth | 75 |
| thief | 20261013 | goblin_fort_fourth | goblin_fort_fourth_defeat @ goblin_fort_fourth | goblin_fort_fourth | 95 |
| thief | 20261014 | 无 | ignis_defeated @ castle_report | castle_report | 148 |

最远地点口径：按主线章节、地图节点顺序取最大值；砦/洞窟归森林章、屋敷归王城归还章。同级支线没有唯一剧情顺序，完整到访记录见逐步日志。

最终分布：{"ignis_purified": 1, "step_limit": 2, "draco_defeated_with_ignis": 1, "goblin_fort_fourth_defeat": 3, "ignis_defeated": 1}

首次死亡地点：{"goblin_fort_fourth": 2, "lost_goblin_crossroads": 1}

重来后分布：{"goblin_fort_fourth_defeat": 3}

## 不变量检查

- 异常、非战斗死路及兜底叙述：0 项。
- 古戦場到访：2/8局。
- 城塞到访：4/8局。
- 峡谷到访：2/8局；完成峡谷：2局。
- 经礼拝堂到村后门：2/8局。
- 同一地点重来后再次死亡（仅作为循环候选，不能据此证明必死）：mage/20261013 @ goblin_fort_fourth, thief/20261013 @ goblin_fort_fourth

## 逐步记录

- [hero-20261013.md](035-playtest/hero-20261013.md)
- [hero-20261014.md](035-playtest/hero-20261014.md)
- [cleric-20261013.md](035-playtest/cleric-20261013.md)
- [cleric-20261014.md](035-playtest/cleric-20261014.md)
- [mage-20261013.md](035-playtest/mage-20261013.md)
- [mage-20261014.md](035-playtest/mage-20261014.md)
- [thief-20261013.md](035-playtest/thief-20261013.md)
- [thief-20261014.md](035-playtest/thief-20261014.md)

## 复现

```powershell
python -m scripts.playtest.explore --output "eval/reports/035-playtest.md"
```

剧本 SHA-256：

- dragon_rpg.json: `d823c57193a71af13a9e8a2de5ae4b29f00fec403d3bbe3d1b792edf770c22f4`
- dragon_rpg_hybrid.json: `e20bc13512b41a15fbb0a98393082c0f164977cadcee3698515cee40eb37772d`
