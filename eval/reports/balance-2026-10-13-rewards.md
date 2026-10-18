> 历史停点产物：保留上轮全量发放 +5 的结果，已被本轮 [区域 +5](balance-2026-10-13-regional-plus5.md) 与 [区域 +3](balance-2026-10-13-regional-plus3.md) 复核取代；不代表最终提交参数。

# 031 永久奖励：最终战配对检查

注意：本报告的准备条件与上一报告不同，不能据此判定任务第1.3节未触发。停止阈值结论以 balance-2026-10-13-rewards-gate.md 的旧口径复核为准。

N=500/职业/条件，seed=20261012；离线真实引擎、heuristic、关闭净化。
修改前为提交 `b653265` 的剧本，修改后为本次剧本。每场HP/MP/SP补满；前序战斗假定获胜，继承真实动作产生的等级、装备和有限背包。
这是到达最终战后的条件胜率，不是从开局连续通关率。每种玩家的前后使用相同路线和准备规则。

- 主线：只打入口史莱姆和村庄成功判定分支的火史莱姆；十字路直接前进，携帯食引狼，结冰处取证，经历原有Xanxus剧情战和ワーロック操控战，潜行穿过煤の亡霊。判定按检查点惯例取成功，未取得可选战斗掉落。潜行成功按031拿一枚魔力果实并使用。
- 全探索：沿用015/017实际砦、洞窟、交付与虹晶武器路线；在已获得奖励之外补齐所有可选遭遇的胜利掉落。イグニス前排除第5章掉落；ドラコ前加入已有全部击杀路线支援。保留自然火系技能，不使用旧报告的去火标准准备。新外套自动装备，永久品全部使用。
- 全探索补齐部分是奖励条件上界，部分路线互斥/回访或取得前的消耗与死亡没有建模；不会把这些条件胜率标成全探索连续通关率。同行者取原检查点路线，不额外指定火コウモリ竜。

|玩家|最终战|职业|修改前|031|增幅pp|上限pp|
|---|---|---|---:|---:|---:|---:|
|main|dragon_valley_loc|hero|88.00%|88.00%|+0.00|5|
|main|dragon_valley_loc|cleric|61.20%|65.80%|+4.60|5|
|main|dragon_valley_loc|mage|72.80%|72.80%|+0.00|5|
|main|dragon_valley_loc|thief|81.20%|81.20%|+0.00|5|
|main|draco_battle|hero|58.60%|58.60%|+0.00|5|
|main|draco_battle|cleric|57.20%|57.40%|+0.20|5|
|main|draco_battle|mage|66.20%|66.20%|+0.00|5|
|main|draco_battle|thief|63.20%|63.20%|+0.00|5|
|explore|dragon_valley_loc|hero|99.60%|100.00%|+0.40|15|
|explore|dragon_valley_loc|cleric|98.80%|100.00%|+1.20|15|
|explore|dragon_valley_loc|mage|93.60%|100.00%|+6.40|15|
|explore|dragon_valley_loc|thief|99.00%|100.00%|+1.00|15|
|explore|draco_battle|hero|100.00%|100.00%|+0.00|15|
|explore|draco_battle|cleric|99.60%|100.00%|+0.40|15|
|explore|draco_battle|mage|98.00%|100.00%|+2.00|15|
|explore|draco_battle|thief|99.60%|100.00%|+0.40|15|

## 与上一份单场报告的差（口径有变化）

イグニス参照017的原装备/虹晶武器，ドラコ参照026的none/all_kill。旧报告不含031全探索掉落池，且026剔除了其他火系手段，故下表不是纯数值因果差；需按旧准备条件另行复核停止阈值。最新029报告只到イグニス，统计连续路线通关率，不能直接冒充两场Boss的单场胜率。

|玩家|最终战|职业|上一报告|031|差pp|
|---|---|---|---:|---:|---:|
|main|dragon_valley_loc|hero|88.00%|88.00%|+0.00|
|main|dragon_valley_loc|cleric|76.00%|65.80%|-10.20|
|main|dragon_valley_loc|mage|73.20%|72.80%|-0.40|
|main|dragon_valley_loc|thief|81.20%|81.20%|+0.00|
|main|draco_battle|hero|60.05%|58.60%|-1.45|
|main|draco_battle|cleric|57.60%|57.40%|-0.20|
|main|draco_battle|mage|56.30%|66.20%|+9.90|
|main|draco_battle|thief|64.50%|63.20%|-1.30|
|explore|dragon_valley_loc|hero|98.80%|100.00%|+1.20|
|explore|dragon_valley_loc|cleric|87.80%|100.00%|+12.20|
|explore|dragon_valley_loc|mage|87.00%|100.00%|+13.00|
|explore|dragon_valley_loc|thief|93.00%|100.00%|+7.00|
|explore|draco_battle|hero|93.50%|100.00%|+6.50|
|explore|draco_battle|cleric|90.90%|100.00%|+9.10|
|explore|draco_battle|mage|73.60%|100.00%|+26.40|
|explore|draco_battle|thief|91.60%|100.00%|+8.40|

本报告配对差超过数值上限的组数：0；不代表任务停止阈值通过。

JSON包含全部输入快照、路线、物品数量、旗标、消耗、败因及文件SHA-256。数值保持+2/+5；未自动改成+1/+3。

```powershell
python -X utf8 -m scripts.balance.rewards --n 500 --seed 20261012
```
