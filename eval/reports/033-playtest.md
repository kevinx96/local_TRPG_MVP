# 离线试玩回归（033）

4 职业 × 2 固定种子（20261013、20261014），每局最多 150 步；战斗每个指令和结算各占一步。
首次战斗死亡后重来一次，选择次数及随机流继续累计。选项、判定和战斗的随机数均固定。
031：奇数种子首次到森林出口时优先古戦場；进入后依次潜行骨野、访问塔、取外套休息、潜行沼地、通过礼拝堂。诅咒持有者使用专属放行，至少2局通过新地图。
033：首次到温泉或古戦場入口时优先城塞支路；按本営取得推薦状、礼拝堂招募、工房、宿屋、见张台的顺序访问，再南下古戦場。仅调整行动优先度，不注入状态或强制判定成功。
LLM 配置指向 127.0.0.1:1，并在请求适配器直接模拟连接失败；禁止真实网络。

| 职业 | 种子 | 首次死亡 | 重来后结果 / 最终结果 | 最远地点 | 步数 |
|---|---:|---|---|---|---:|
| hero | 20261013 | 无 | step_limit @ village_frozen_clue | oaksdawn_wall | 150 |
| hero | 20261014 | 无 | step_limit @ valley_entrance | valley_entrance | 150 |
| cleric | 20261013 | 无 | defied_xanxus @ xanxus_ultimatum | village | 117 |
| cleric | 20261014 | draco_battle | ignis_purified @ castle_report | draco_battle | 144 |
| mage | 20261013 | draco_battle | ignis_defeated @ castle_report | draco_battle | 145 |
| mage | 20261014 | frost_wolf_battle | draco_victory @ draco_battle | draco_battle | 123 |
| thief | 20261013 | dragon_valley_loc | dragon_valley_defeat @ dragon_valley_loc | dragon_valley_loc | 115 |
| thief | 20261014 | ice_elemental_encounter | draco_victory @ draco_battle | draco_battle | 130 |

最远地点口径：按主线章节、地图节点顺序取最大值；砦/洞窟归森林章、屋敷归王城归还章。同级支线没有唯一剧情顺序，完整到访记录见逐步日志。

最终分布：{"step_limit": 2, "defied_xanxus": 1, "ignis_purified": 1, "ignis_defeated": 1, "draco_victory": 2, "dragon_valley_defeat": 1}

首次死亡地点：{"draco_battle": 2, "frost_wolf_battle": 1, "dragon_valley_loc": 1, "ice_elemental_encounter": 1}

重来后分布：{"ignis_purified": 1, "ignis_defeated": 1, "draco_victory": 2, "dragon_valley_defeat": 1}

## 不变量检查

- 异常、非战斗死路及兜底叙述：0 项。
- 古戦場到访：8/8局。
- 城塞到访：8/8局。
- 经礼拝堂到村后门：7/8局。
- 同一地点重来后再次死亡（仅作为循环候选，不能据此证明必死）：thief/20261013 @ dragon_valley_loc

## 逐步记录

- [hero-20261013.md](033-playtest/hero-20261013.md)
- [hero-20261014.md](033-playtest/hero-20261014.md)
- [cleric-20261013.md](033-playtest/cleric-20261013.md)
- [cleric-20261014.md](033-playtest/cleric-20261014.md)
- [mage-20261013.md](033-playtest/mage-20261013.md)
- [mage-20261014.md](033-playtest/mage-20261014.md)
- [thief-20261013.md](033-playtest/thief-20261013.md)
- [thief-20261014.md](033-playtest/thief-20261014.md)

## 复现

```powershell
python -m scripts.playtest.explore
```

剧本 SHA-256：

- dragon_rpg.json: `2e50142ec0692038bd0a3c5fa92f53be10ba32c5ff60272577616337b97099da`
- dragon_rpg_hybrid.json: `ba1d018ff83fd8a10e34714c76283e7955beb682c7fc5022768b202dea7007dd`
