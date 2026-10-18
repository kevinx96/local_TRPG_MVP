# 034 暁光の武器平衡评测

每组合 N=500，seed=20261017；四职业、真实确定性战斗引擎、离线 heuristic 策略。

## 方法与推断

- 古戦場沿用033的森出口Lv2可达检查点；三个固定战斗分别补满HP/MP/SP后测试，不预取墓守外套，不潜行。
- 最终战沿用现有逐战可达检查点，draco_battle包含ドラコ与ヴァイス完整形态流程；イグニス关闭净化分支。
- 所有组合均无同行者，其他装备、技能与有限消耗品相同；仅替换weapon部位，保留原武器在背包。
- 暁光武器通过控制变量加入，未模拟购买/任务的时间和经济成本；不是从游戏开局的路线胜率。冰武器同时列氷鉄の大剣与氷の太刀，避免任意指定唯一对照。
- HP损失为开战至战斗结束的净损失，包含死亡、技能/道具回复；不应用战后奖励。相同初始随机种子，行动数改变后骰序列不再逐次相同。
- spec未给“明显变容易”的数值阈值；下表直接报告胜率、净损失与回合数，不自设验收线。胜率为抽样估计。

## 古戦場：现有武器 / 暁光

|职业|战斗|现有胜率|暁光胜率|变化pp|现有HP损失|暁光HP损失|现有回合|暁光回合|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|hero|bone_field|100.0%|100.0%|+0.0|7.58|3.81|3.40|2.17|
|hero|ghoul_marsh|100.0%|100.0%|+0.0|5.09|3.50|2.64|2.10|
|hero|grave_chapel|88.4%|88.4%|+0.0|12.22|12.22|4.29|4.29|
|cleric|bone_field|99.4%|100.0%|+0.6|7.86|5.36|3.64|2.56|
|cleric|ghoul_marsh|100.0%|100.0%|+0.0|5.97|4.57|2.71|2.22|
|cleric|grave_chapel|70.6%|70.8%|+0.2|14.11|14.08|4.24|4.23|
|mage|bone_field|100.0%|100.0%|+0.0|0.59|0.59|1.15|1.15|
|mage|ghoul_marsh|100.0%|100.0%|+0.0|3.90|3.90|2.11|2.11|
|mage|grave_chapel|77.6%|77.6%|+0.0|6.45|6.45|2.43|2.43|
|thief|bone_field|98.4%|100.0%|+1.6|6.60|3.27|4.36|2.08|
|thief|ghoul_marsh|100.0%|100.0%|+0.0|4.76|2.80|2.98|2.04|
|thief|grave_chapel|84.8%|84.8%|+0.0|8.02|8.02|4.29|4.29|

## 最终战：冰武器 / 暁光

|职业|战斗|武器|胜率|HP损失|回合|
|---|---|---|---:|---:|---:|
|hero|dragon_valley_loc|ice_iron_greatsword|90.0%|16.26|9.42|
|hero|dragon_valley_loc|ice_katana|92.4%|14.69|7.09|
|hero|dragon_valley_loc|dawn|82.2%|18.71|12.16|
|hero|draco_battle|ice_iron_greatsword|58.2%|26.09|7.59|
|hero|draco_battle|ice_katana|60.4%|25.59|7.37|
|hero|draco_battle|dawn|58.8%|25.92|7.38|
|cleric|dragon_valley_loc|ice_iron_greatsword|79.2%|17.28|9.78|
|cleric|dragon_valley_loc|ice_katana|87.6%|14.89|6.67|
|cleric|dragon_valley_loc|dawn|66.8%|20.68|12.33|
|cleric|draco_battle|ice_iron_greatsword|59.0%|23.85|7.03|
|cleric|draco_battle|ice_katana|61.0%|23.44|6.89|
|cleric|draco_battle|dawn|58.8%|23.92|6.94|
|mage|dragon_valley_loc|ice_iron_greatsword|69.4%|11.84|5.51|
|mage|dragon_valley_loc|ice_katana|69.4%|11.84|5.51|
|mage|dragon_valley_loc|dawn|69.4%|11.84|5.51|
|mage|draco_battle|ice_iron_greatsword|70.6%|12.33|3.27|
|mage|draco_battle|ice_katana|70.6%|12.33|3.27|
|mage|draco_battle|dawn|70.6%|12.33|3.27|
|thief|dragon_valley_loc|ice_iron_greatsword|78.2%|13.42|6.62|
|thief|dragon_valley_loc|ice_katana|79.0%|12.77|6.53|
|thief|dragon_valley_loc|dawn|78.2%|13.48|6.64|
|thief|draco_battle|ice_iron_greatsword|65.0%|17.05|5.59|
|thief|draco_battle|ice_katana|65.0%|17.05|5.59|
|thief|draco_battle|dawn|65.0%|17.05|5.59|

## 普通攻击对照与策略影响

伤害列复用现有heuristic的期望伤害估算（骰子均值、命中、抗性、减伤及补助追击），不是完整骰子分布的精确数学期望，也不含战中状态。
平均普通攻击次数来自上面的实际模拟。普通攻击次数很少或为零时，强技能/道具会掩盖武器差异。

|职业|战斗|武器|平均普通攻击次数|每次普通攻击伤害估算（敌人）|
|---|---|---|---:|---|
|hero|bone_field|baseline|0.03|skeleton_soldier: 8.80|
|hero|bone_field|dawn|2.17|skeleton_soldier: 18.40|
|hero|ghoul_marsh|baseline|0.00|ghoul: 8.80；wraith: 8.80|
|hero|ghoul_marsh|dawn|1.10|ghoul: 18.40；wraith: 18.40|
|hero|grave_chapel|baseline|0.00|grave_knight: 8.80|
|hero|grave_chapel|dawn|0.00|grave_knight: 18.40|
|hero|dragon_valley_loc|ice_iron_greatsword|6.42|ignis: 16.80|
|hero|dragon_valley_loc|ice_katana|4.44|ignis: 26.40|
|hero|dragon_valley_loc|dawn|8.68|ignis: 11.44|
|hero|draco_battle|ice_iron_greatsword|0.02|draco_human: 8.80；draco_dragon: 0.88|
|hero|draco_battle|ice_katana|1.50|draco_human: 14.72；draco_dragon: 1.84|
|hero|draco_battle|dawn|1.53|draco_human: 11.96；draco_dragon: 1.84|
|cleric|bone_field|baseline|3.37|skeleton_soldier: 9.68|
|cleric|bone_field|dawn|2.49|skeleton_soldier: 14.72|
|cleric|ghoul_marsh|baseline|1.69|ghoul: 9.68；wraith: 9.68|
|cleric|ghoul_marsh|dawn|1.21|ghoul: 14.72；wraith: 14.72|
|cleric|grave_chapel|baseline|0.00|grave_knight: 9.68|
|cleric|grave_chapel|dawn|0.00|grave_knight: 14.72|
|cleric|dragon_valley_loc|ice_iron_greatsword|6.49|ignis: 15.12|
|cleric|dragon_valley_loc|ice_katana|3.95|ignis: 27.28|
|cleric|dragon_valley_loc|dawn|2.23|ignis: 8.80|
|cleric|draco_battle|ice_iron_greatsword|0.40|draco_human: 8.80；draco_dragon: 0.88|
|cleric|draco_battle|ice_katana|1.07|draco_human: 15.64；draco_dragon: 2.76|
|cleric|draco_battle|dawn|0.36|draco_human: 9.20；draco_dragon: 0.92|
|mage|bone_field|baseline|0.00|skeleton_soldier: 5.40|
|mage|bone_field|dawn|0.14|skeleton_soldier: 20.24|
|mage|ghoul_marsh|baseline|0.00|ghoul: 5.40；wraith: 5.40|
|mage|ghoul_marsh|dawn|1.09|ghoul: 20.24；wraith: 20.24|
|mage|grave_chapel|baseline|0.00|grave_knight: 5.40|
|mage|grave_chapel|dawn|0.00|grave_knight: 20.24|
|mage|dragon_valley_loc|ice_iron_greatsword|0.00|ignis: 16.80|
|mage|dragon_valley_loc|ice_katana|0.00|ignis: 29.04|
|mage|dragon_valley_loc|dawn|0.00|ignis: 12.32|
|mage|draco_battle|ice_iron_greatsword|0.00|draco_human: 8.80；draco_dragon: 0.88|
|mage|draco_battle|ice_katana|0.00|draco_human: 16.56；draco_dragon: 2.76|
|mage|draco_battle|dawn|0.00|draco_human: 12.88；draco_dragon: 1.84|
|thief|bone_field|baseline|0.12|skeleton_soldier: 7.60|
|thief|bone_field|dawn|2.07|skeleton_soldier: 17.28|
|thief|ghoul_marsh|baseline|0.00|ghoul: 7.60；wraith: 7.60|
|thief|ghoul_marsh|dawn|1.04|ghoul: 17.28；wraith: 17.28|
|thief|grave_chapel|baseline|0.00|grave_knight: 7.60|
|thief|grave_chapel|dawn|0.00|grave_knight: 17.28|
|thief|dragon_valley_loc|ice_iron_greatsword|0.16|ignis: 15.12|
|thief|dragon_valley_loc|ice_katana|3.98|ignis: 26.40|
|thief|dragon_valley_loc|dawn|0.18|ignis: 11.04|
|thief|draco_battle|ice_iron_greatsword|0.00|draco_human: 8.80；draco_dragon: 0.88|
|thief|draco_battle|ice_katana|0.00|draco_human: 14.72；draco_dragon: 1.84|
|thief|draco_battle|dawn|0.00|draco_human: 11.52；draco_dragon: 1.92|

## 目标偏离

- TODO(design): hero/grave_chapel：三项指标均未改善。
- TODO(design): mage/bone_field：三项指标均未改善。
- TODO(design): mage/ghoul_marsh：三项指标均未改善。
- TODO(design): mage/grave_chapel：三项指标均未改善。
- TODO(design): thief/grave_chapel：三项指标均未改善。
- TODO(design): hero/draco_battle：暁光胜率比ice_iron_greatsword高0.6pp，未满足“不能更好”。

未调整任何既有敌人强度或spec武器数值。原始统计、装备与等级见同名JSON。
非终局样本：0。

## 复现

```powershell
python -m scripts.balance.dawn --n 500 --seed 20261017
```

代码与数据指纹：

- scripts\balance\dawn.py: `c83b59237c33b92740b8c6139a4b25975c444cf2d6162051416b6f94ea52691e`
- host\prompt\processed\dragon_rpg.json: `f194d53eaedad791006efb2aa0b9d2db0fcfbe1c21f49765ce27381a7cc58a14`
- host\combat.py: `c1998d92976990214dbac2a2859aa7a37db269dbc586efeedd5f5aa0d2bf7929`
- host\state.py: `5283aa41f4c712db51ce15bbcf17dc1cc4cba634f0f38ba60537d33607f3d1e1`
- host\item_mechanics.py: `9114c15157e52402de2481306ff4cce5782b207390aabfdef6a30a8e257fdf42`
- scripts\balance\sim.py: `dc0596c91bdcfb1f2a60b9d40b6a251df451e6d77213fba5d0bdbcae3edc1b8e`
- scripts\balance\liese.py: `a82f8680a353f07384ca41257d1880d9bae20798d129cc92d9ec1e7e0505fffb`
- scripts\balance\checkpoints.py: `69f80add42f9ff019014566e77abc1f25f422d23fbf03076a36652e9f80543f5`
