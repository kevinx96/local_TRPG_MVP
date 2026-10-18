# 037 第三章三条路线连续平衡（第三轮）

N=2000／职业／条件；seed=20261018；204组，共408,000条连续路线。完全离线。

按设计负责人第三轮决定，采用第二轮筛选中唯一核心8项全通过的组合：リーゼ回复20%、聖光の一撃2d6；エリオ水刃2d6、水の帳每4回合。两份剧本的说明与招募preview同步。未继续搜索或调参。

本轮对策同行者门槛：未准备、无诅咒的4职业×2路线严格领先，共5/8项通过；完整覆盖=True，门槛通过=False。准备组和诅咒组仅报告，不作为这一门槛。

24项全部严格领先在第二轮授权范围内无法满足；设计据大多数玩家处境改用核心8项。第二轮N=300筛选用于选定参数，本轮N=2000独立复核，核心若失败也只报告。

## 口径与推断

- 起点为第2章结束的森の出口。复用可达检查点回放，先完成ゴブリン砦并归还箱子，再通过森林、回城支付10G休息后返回出口；Lv3、240G，四职业具体背包和全部前置动作见JSON。前置战斗假定获胜、不估算消耗，结论条件于这个检查点，不是从新游戏开始的通关率。
- 原主线Lv2起点只有125G，不能支付195G整套准备；为避免凭空补钱，所有组统一采用上述砦后检查点。准备组实际购买聖銀120G、锻造30G、鎖帷子40G、礼拝堂休息5G；未准备组不购买。第二轮墓守外套仅在防具部位为空时自动装备；本轮不额外加入手动换装策略，保留原有ローブ／革の鎧或准备组鎖帷子。
- 同行者和诅咒采用031/033/035既有的机制对照：起点指定同行者，诅咒组给予呪われた短剣；武器位为空的僧侶／魔法使い会自动装备，勇者／盗賊保留原武器；准备组再由锻造替换武器。第一轮‘只携带、不装备’的文字描述不准确，但三轮实际代码均为上述行为，原始JSON可核对。不计招募费用、获取诅咒代价，不能当成完整招募路线。火コウモリ竜普通／虹晶强化分别列出；其他控制包括ロビン、ミーナ、ワーロック及另一条路线的同行者。
- 保留剧情中的同行者离队；村路线的ワーロック在森林出口离队，所以该组不会强行留住他。
- 村路线慎重接近、离开民家；古戦場骨野潜行（诅咒放行）、塔取外套并休息、沼地潜行、骑士战（诅咒放行）；峡谷潜行、搜营地并休息、查爪痕、巨人潜行、ワーム潜行（エリオ绕过）。
- 三路都汇入避難所。共同后程采用现行hp70付费休息策略、竜の谷亡霊潜行、过桥、イグニス战；不额外走冰元素／Xanxus支线，不净化。所有判定投真实d20、失败实战，HP/MP/SP、金币、背包跨战继承，永久品立即使用，无重来。
- 分母始终是全部起点样本，包含提前死亡；同时列出到Boss的样本数与条件胜率。每组共享初始随机种子，同行者耗骰不同，不代表逐骰配对。判据采用样本点估计，不把抽样误差当成设计容差。
- ‘三路相差≤8pp’对未准备／已准备分别比较（村路线均为未准备），主比较无诅咒；诅咒单列。同率并列最优也计入四职业共同最优。第三轮对策同行者仅核心8项要求严格领先所有其他同行者，相同基线下比较提升等价于比较通关率；并列判为未通过。其他16项沿用严格比较展示结果，但不计入门槛。

## 无同行者、无诅咒

|职业|城塞准备|村|古戦場|峡谷|最大差pp|≤8pp|
|---|---|---:|---:|---:|---:|---|
|hero|False|84.20%|85.60%|85.00%|1.40|True|
|cleric|False|73.70%|73.80%|74.95%|1.25|True|
|mage|False|70.45%|80.40%|77.00%|9.95|False|
|thief|False|85.40%|89.35%|92.10%|6.70|True|
|hero|True|84.20%|87.95%|85.50%|3.75|True|
|cleric|True|73.70%|88.75%|86.50%|15.05|False|
|mage|True|70.45%|86.45%|83.40%|16.00|False|
|thief|True|85.40%|94.30%|94.55%|9.15|False|

## 本路线对策同行者——核心8项：未准备、无诅咒（验收门槛）

|职业|路线|准备|诅咒|对策提升pp|其他最强|其提升pp|领先pp|严格领先|
|---|---|---|---|---:|---|---:|---:|---|
|hero|battlefield|False|False|+10.65|hydromancer_elio|+9.35|+1.30|True|
|cleric|battlefield|False|False|+21.75|hydromancer_elio|+20.10|+1.65|True|
|mage|battlefield|False|False|+11.45|fire_bat_empowered|+10.75|+0.70|True|
|thief|battlefield|False|False|+8.75|hydromancer_elio|+9.05|-0.30|False|
|hero|gorge|False|False|+10.20|paladin_liese|+10.20|+0.00|False|
|cleric|gorge|False|False|+18.50|paladin_liese|+18.35|+0.15|True|
|mage|gorge|False|False|+10.90|fire_bat_empowered|+9.20|+1.70|True|
|thief|gorge|False|False|+5.40|fire_bat_empowered|+5.60|-0.20|False|

## 本路线对策同行者——准备组／诅咒组（仅报告）

|职业|路线|准备|诅咒|对策提升pp|其他最强|其提升pp|领先pp|严格领先|
|---|---|---|---|---:|---|---:|---:|---|
|hero|battlefield|False|True|+9.65|hydromancer_elio|+8.60|+1.05|True|
|cleric|battlefield|False|True|+17.40|hydromancer_elio|+15.85|+1.55|True|
|mage|battlefield|False|True|+7.85|hydromancer_elio|+11.90|-4.05|False|
|thief|battlefield|False|True|+7.60|fire_bat_empowered|+8.95|-1.35|False|
|hero|battlefield|True|False|+8.90|hydromancer_elio|+8.00|+0.90|True|
|cleric|battlefield|True|False|+8.80|hydromancer_elio|+7.85|+0.95|True|
|mage|battlefield|True|False|+8.35|hydromancer_elio|+7.85|+0.50|True|
|thief|battlefield|True|False|+4.90|hydromancer_elio|+4.60|+0.30|True|
|hero|battlefield|True|True|+10.15|hydromancer_elio|+8.95|+1.20|True|
|cleric|battlefield|True|True|+10.60|hydromancer_elio|+9.25|+1.35|True|
|mage|battlefield|True|True|+12.80|hydromancer_elio|+12.65|+0.15|True|
|thief|battlefield|True|True|+5.45|hydromancer_elio|+6.50|-1.05|False|
|hero|gorge|True|False|+9.25|paladin_liese|+10.50|-1.25|False|
|cleric|gorge|True|False|+10.00|paladin_liese|+10.75|-0.75|False|
|mage|gorge|True|False|+8.65|paladin_liese|+9.25|-0.60|False|
|thief|gorge|True|False|+4.20|fire_bat_empowered|+3.80|+0.40|True|

## 第一、二轮对照

第一轮：[报告](balance-2026-10-18-ch3-routes-round1.md)、[JSON](balance-2026-10-18-ch3-routes-round1.json)；第二轮：[报告](balance-2026-10-18-ch3-routes-round2.md)、[JSON](balance-2026-10-18-ch3-routes-round2.json)。204组起点、策略、种子和N不变；本轮仅改变两名同行者的指定参数。

|职业|准备|第一轮最大差pp|第二轮最大差pp|第三轮最大差pp|
|---|---|---:|---:|---:|
|hero|False|4.10|1.40|1.40|
|cleric|False|15.15|1.25|1.25|
|mage|False|18.55|9.95|9.95|
|thief|False|7.00|6.70|6.70|
|hero|True|4.65|3.75|3.75|
|cleric|True|16.10|15.05|15.05|
|mage|True|16.20|16.00|16.00|
|thief|True|9.15|9.15|9.15|

## 各组原始统计

|职业|路线|准备|诅咒|同行者|胜/N|第三轮通关率|第一轮|第二轮|较第二轮变化pp|到达Boss|Boss条件胜率|首次败北地点|
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
|hero|village|False|False|none|1684/2000|84.20%|84.20%|84.20%|+0.00|1750|96.23%|{"valley_entrance": 249, "dragon_valley_loc": 66, "village_fire_elemental": 1}|
|hero|village|False|False|blue_robed_mage|1684/2000|84.20%|84.20%|84.20%|+0.00|1750|96.23%|{"valley_entrance": 249, "dragon_valley_loc": 66, "village_fire_elemental": 1}|
|hero|village|False|False|fire_bat_dragon|1756/2000|87.80%|87.80%|87.80%|+0.00|1787|98.27%|{"valley_entrance": 213, "dragon_valley_loc": 31}|
|hero|battlefield|False|False|none|1712/2000|85.60%|88.30%|85.60%|+0.00|1728|99.07%|{"valley_entrance": 231, "grave_chapel": 41, "dragon_valley_loc": 16}|
|hero|battlefield|False|False|robin|1882/2000|94.10%|95.40%|94.10%|+0.00|1908|98.64%|{"valley_entrance": 92, "dragon_valley_loc": 26}|
|hero|battlefield|False|False|blue_robed_mage|1731/2000|86.55%|89.20%|86.55%|+0.00|1740|99.48%|{"valley_entrance": 219, "grave_chapel": 41, "dragon_valley_loc": 9}|
|hero|battlefield|False|False|fire_bat_dragon|1785/2000|89.25%|89.90%|89.25%|+0.00|1792|99.61%|{"valley_entrance": 208, "dragon_valley_loc": 7}|
|hero|battlefield|False|False|fire_bat_empowered|1792/2000|89.60%|90.10%|89.60%|+0.00|1796|99.78%|{"valley_entrance": 204, "dragon_valley_loc": 4}|
|hero|battlefield|False|False|mina|1733/2000|86.65%|89.05%|86.65%|+0.00|1750|99.03%|{"valley_entrance": 212, "grave_chapel": 38, "dragon_valley_loc": 17}|
|hero|battlefield|False|False|paladin_liese|1925/2000|96.25%|95.65%|95.60%|+0.65|1927|99.90%|{"valley_entrance": 73, "dragon_valley_loc": 2}|
|hero|battlefield|False|False|hydromancer_elio|1899/2000|94.95%|93.75%|93.15%|+1.80|1910|99.42%|{"valley_entrance": 90, "dragon_valley_loc": 11}|
|hero|battlefield|False|True|none|1688/2000|84.40%|85.45%|84.40%|+0.00|1746|96.68%|{"valley_entrance": 254, "dragon_valley_loc": 58}|
|hero|battlefield|False|True|robin|1808/2000|90.40%|92.45%|90.40%|+0.00|1877|96.32%|{"dragon_valley_loc": 69, "valley_entrance": 123}|
|hero|battlefield|False|True|blue_robed_mage|1724/2000|86.20%|87.60%|86.20%|+0.00|1751|98.46%|{"valley_entrance": 249, "dragon_valley_loc": 27}|
|hero|battlefield|False|True|fire_bat_dragon|1712/2000|85.60%|87.25%|85.60%|+0.00|1743|98.22%|{"valley_entrance": 257, "dragon_valley_loc": 31}|
|hero|battlefield|False|True|fire_bat_empowered|1736/2000|86.80%|87.65%|86.80%|+0.00|1744|99.54%|{"valley_entrance": 256, "dragon_valley_loc": 8}|
|hero|battlefield|False|True|mina|1703/2000|85.15%|86.65%|85.15%|+0.00|1752|97.20%|{"valley_entrance": 248, "dragon_valley_loc": 49}|
|hero|battlefield|False|True|paladin_liese|1881/2000|94.05%|94.55%|94.25%|-0.20|1909|98.53%|{"valley_entrance": 91, "dragon_valley_loc": 28}|
|hero|battlefield|False|True|hydromancer_elio|1860/2000|93.00%|92.10%|90.40%|+2.60|1894|98.20%|{"valley_entrance": 106, "dragon_valley_loc": 34}|
|hero|battlefield|True|False|none|1759/2000|87.95%|88.85%|87.95%|+0.00|1775|99.10%|{"valley_entrance": 209, "grave_chapel": 16, "dragon_valley_loc": 16}|
|hero|battlefield|True|False|robin|1917/2000|95.85%|95.85%|95.85%|+0.00|1924|99.64%|{"valley_entrance": 76, "dragon_valley_loc": 7}|
|hero|battlefield|True|False|blue_robed_mage|1780/2000|89.00%|89.85%|89.00%|+0.00|1782|99.89%|{"valley_entrance": 202, "grave_chapel": 16, "dragon_valley_loc": 2}|
|hero|battlefield|True|False|fire_bat_dragon|1805/2000|90.25%|90.25%|90.25%|+0.00|1811|99.67%|{"valley_entrance": 189, "dragon_valley_loc": 6}|
|hero|battlefield|True|False|fire_bat_empowered|1811/2000|90.55%|90.55%|90.55%|+0.00|1812|99.94%|{"valley_entrance": 188, "dragon_valley_loc": 1}|
|hero|battlefield|True|False|mina|1772/2000|88.60%|88.85%|88.60%|+0.00|1778|99.66%|{"valley_entrance": 209, "grave_chapel": 13, "dragon_valley_loc": 6}|
|hero|battlefield|True|False|paladin_liese|1937/2000|96.85%|96.25%|96.35%|+0.50|1937|100.00%|{"valley_entrance": 63}|
|hero|battlefield|True|False|hydromancer_elio|1919/2000|95.95%|94.10%|94.10%|+1.85|1923|99.79%|{"valley_entrance": 77, "dragon_valley_loc": 4}|
|hero|battlefield|True|True|none|1688/2000|84.40%|84.40%|84.40%|+0.00|1770|95.37%|{"valley_entrance": 230, "dragon_valley_loc": 82}|
|hero|battlefield|True|True|robin|1823/2000|91.15%|91.15%|91.15%|+0.00|1882|96.87%|{"dragon_valley_loc": 59, "valley_entrance": 118}|
|hero|battlefield|True|True|blue_robed_mage|1756/2000|87.80%|87.80%|87.80%|+0.00|1773|99.04%|{"valley_entrance": 227, "dragon_valley_loc": 17}|
|hero|battlefield|True|True|fire_bat_dragon|1742/2000|87.10%|87.10%|87.10%|+0.00|1763|98.81%|{"valley_entrance": 237, "dragon_valley_loc": 21}|
|hero|battlefield|True|True|fire_bat_empowered|1758/2000|87.90%|87.90%|87.90%|+0.00|1764|99.66%|{"valley_entrance": 236, "dragon_valley_loc": 6}|
|hero|battlefield|True|True|mina|1713/2000|85.65%|85.65%|85.65%|+0.00|1770|96.78%|{"valley_entrance": 230, "dragon_valley_loc": 57}|
|hero|battlefield|True|True|paladin_liese|1891/2000|94.55%|94.15%|94.15%|+0.40|1910|99.01%|{"valley_entrance": 90, "dragon_valley_loc": 19}|
|hero|battlefield|True|True|hydromancer_elio|1867/2000|93.35%|90.80%|90.80%|+2.55|1899|98.31%|{"valley_entrance": 101, "dragon_valley_loc": 32}|
|hero|gorge|False|False|none|1700/2000|85.00%|85.00%|85.00%|+0.00|1737|97.87%|{"valley_entrance": 263, "dragon_valley_loc": 37}|
|hero|gorge|False|False|robin|1865/2000|93.25%|93.25%|93.25%|+0.00|1907|97.80%|{"valley_entrance": 93, "dragon_valley_loc": 42}|
|hero|gorge|False|False|blue_robed_mage|1716/2000|85.80%|85.80%|85.80%|+0.00|1731|99.13%|{"valley_entrance": 269, "dragon_valley_loc": 15}|
|hero|gorge|False|False|fire_bat_dragon|1769/2000|88.45%|88.45%|88.45%|+0.00|1784|99.16%|{"valley_entrance": 216, "dragon_valley_loc": 15}|
|hero|gorge|False|False|fire_bat_empowered|1780/2000|89.00%|89.00%|89.00%|+0.00|1783|99.83%|{"valley_entrance": 217, "dragon_valley_loc": 3}|
|hero|gorge|False|False|mina|1728/2000|86.40%|86.40%|86.40%|+0.00|1768|97.74%|{"valley_entrance": 232, "dragon_valley_loc": 40}|
|hero|gorge|False|False|paladin_liese|1904/2000|95.20%|95.65%|95.65%|-0.45|1915|99.43%|{"valley_entrance": 85, "dragon_valley_loc": 11}|
|hero|gorge|False|False|hydromancer_elio|1904/2000|95.20%|92.25%|92.25%|+2.95|1920|99.17%|{"valley_entrance": 80, "dragon_valley_loc": 16}|
|hero|gorge|True|False|none|1710/2000|85.50%|85.50%|85.50%|+0.00|1754|97.49%|{"valley_entrance": 246, "dragon_valley_loc": 44}|
|hero|gorge|True|False|robin|1883/2000|94.15%|94.15%|94.15%|+0.00|1905|98.85%|{"valley_entrance": 95, "dragon_valley_loc": 22}|
|hero|gorge|True|False|blue_robed_mage|1751/2000|87.55%|87.55%|87.55%|+0.00|1757|99.66%|{"valley_entrance": 243, "dragon_valley_loc": 6}|
|hero|gorge|True|False|fire_bat_dragon|1799/2000|89.95%|89.95%|89.95%|+0.00|1809|99.45%|{"valley_entrance": 191, "dragon_valley_loc": 10}|
|hero|gorge|True|False|fire_bat_empowered|1812/2000|90.60%|90.60%|90.60%|+0.00|1812|100.00%|{"valley_entrance": 188}|
|hero|gorge|True|False|mina|1751/2000|87.55%|87.55%|87.55%|+0.00|1775|98.65%|{"valley_entrance": 225, "dragon_valley_loc": 24}|
|hero|gorge|True|False|paladin_liese|1920/2000|96.00%|96.40%|96.40%|-0.40|1923|99.84%|{"valley_entrance": 77, "dragon_valley_loc": 3}|
|hero|gorge|True|False|hydromancer_elio|1895/2000|94.75%|92.50%|92.50%|+2.25|1910|99.21%|{"valley_entrance": 90, "dragon_valley_loc": 15}|
|cleric|village|False|False|none|1474/2000|73.70%|73.70%|73.70%|+0.00|1798|81.98%|{"dragon_valley_loc": 324, "village_fire_elemental": 6, "valley_entrance": 196}|
|cleric|village|False|False|blue_robed_mage|1474/2000|73.70%|73.70%|73.70%|+0.00|1798|81.98%|{"dragon_valley_loc": 324, "village_fire_elemental": 6, "valley_entrance": 196}|
|cleric|village|False|False|fire_bat_dragon|1692/2000|84.60%|84.60%|84.60%|+0.00|1850|91.46%|{"valley_entrance": 149, "dragon_valley_loc": 158, "village_fire_elemental": 1}|
|cleric|battlefield|False|False|none|1476/2000|73.80%|88.85%|73.80%|+0.00|1727|85.47%|{"dragon_valley_loc": 251, "grave_chapel": 126, "valley_entrance": 147}|
|cleric|battlefield|False|False|robin|1735/2000|86.75%|93.90%|86.75%|+0.00|1920|90.36%|{"dragon_valley_loc": 185, "valley_entrance": 80}|
|cleric|battlefield|False|False|blue_robed_mage|1627/2000|81.35%|91.60%|81.35%|+0.00|1732|93.94%|{"grave_chapel": 126, "dragon_valley_loc": 105, "valley_entrance": 142}|
|cleric|battlefield|False|False|fire_bat_dragon|1775/2000|88.75%|93.15%|88.75%|+0.00|1873|94.77%|{"dragon_valley_loc": 98, "valley_entrance": 127}|
|cleric|battlefield|False|False|fire_bat_empowered|1817/2000|90.85%|93.80%|90.85%|+0.00|1872|97.06%|{"dragon_valley_loc": 55, "valley_entrance": 128}|
|cleric|battlefield|False|False|mina|1614/2000|80.70%|90.75%|80.70%|+0.00|1772|91.08%|{"valley_entrance": 144, "dragon_valley_loc": 158, "grave_chapel": 84}|
|cleric|battlefield|False|False|paladin_liese|1911/2000|95.55%|96.70%|94.95%|+0.60|1956|97.70%|{"dragon_valley_loc": 45, "valley_entrance": 44}|
|cleric|battlefield|False|False|hydromancer_elio|1878/2000|93.90%|95.00%|90.45%|+3.45|1944|96.60%|{"dragon_valley_loc": 66, "valley_entrance": 56}|
|cleric|battlefield|False|True|none|1496/2000|74.80%|85.05%|74.80%|+0.00|1838|81.39%|{"dragon_valley_loc": 342, "valley_entrance": 162}|
|cleric|battlefield|False|True|robin|1632/2000|81.60%|90.95%|81.60%|+0.00|1925|84.78%|{"dragon_valley_loc": 293, "valley_entrance": 75}|
|cleric|battlefield|False|True|blue_robed_mage|1678/2000|83.90%|89.95%|83.90%|+0.00|1842|91.10%|{"valley_entrance": 158, "dragon_valley_loc": 164}|
|cleric|battlefield|False|True|fire_bat_dragon|1665/2000|83.25%|89.15%|83.25%|+0.00|1845|90.24%|{"dragon_valley_loc": 180, "valley_entrance": 155}|
|cleric|battlefield|False|True|fire_bat_empowered|1762/2000|88.10%|91.45%|88.10%|+0.00|1846|95.45%|{"valley_entrance": 154, "dragon_valley_loc": 84}|
|cleric|battlefield|False|True|mina|1601/2000|80.05%|87.70%|80.05%|+0.00|1842|86.92%|{"dragon_valley_loc": 241, "valley_entrance": 158}|
|cleric|battlefield|False|True|paladin_liese|1844/2000|92.20%|95.80%|91.35%|+0.85|1955|94.32%|{"dragon_valley_loc": 111, "valley_entrance": 45}|
|cleric|battlefield|False|True|hydromancer_elio|1813/2000|90.65%|91.80%|87.00%|+3.65|1942|93.36%|{"dragon_valley_loc": 129, "valley_entrance": 58}|
|cleric|battlefield|True|False|none|1775/2000|88.75%|89.80%|88.75%|+0.00|1827|97.15%|{"valley_entrance": 150, "dragon_valley_loc": 52, "grave_chapel": 23}|
|cleric|battlefield|True|False|robin|1885/2000|94.25%|94.25%|94.25%|+0.00|1923|98.02%|{"valley_entrance": 77, "dragon_valley_loc": 38}|
|cleric|battlefield|True|False|blue_robed_mage|1818/2000|90.90%|91.90%|90.90%|+0.00|1832|99.24%|{"valley_entrance": 145, "grave_chapel": 23, "dragon_valley_loc": 14}|
|cleric|battlefield|True|False|fire_bat_dragon|1868/2000|93.40%|93.40%|93.40%|+0.00|1883|99.20%|{"valley_entrance": 117, "dragon_valley_loc": 15}|
|cleric|battlefield|True|False|fire_bat_empowered|1879/2000|93.95%|93.95%|93.95%|+0.00|1882|99.84%|{"dragon_valley_loc": 3, "valley_entrance": 118}|
|cleric|battlefield|True|False|mina|1805/2000|90.25%|91.00%|90.25%|+0.00|1842|97.99%|{"dragon_valley_loc": 37, "valley_entrance": 141, "grave_chapel": 17}|
|cleric|battlefield|True|False|paladin_liese|1951/2000|97.55%|96.70%|96.75%|+0.80|1958|99.64%|{"valley_entrance": 42, "dragon_valley_loc": 7}|
|cleric|battlefield|True|False|hydromancer_elio|1932/2000|96.60%|95.05%|95.05%|+1.55|1946|99.28%|{"valley_entrance": 54, "dragon_valley_loc": 14}|
|cleric|battlefield|True|True|none|1707/2000|85.35%|85.35%|85.35%|+0.00|1847|92.42%|{"valley_entrance": 153, "dragon_valley_loc": 140}|
|cleric|battlefield|True|True|robin|1824/2000|91.20%|91.20%|91.20%|+0.00|1930|94.51%|{"dragon_valley_loc": 106, "valley_entrance": 70}|
|cleric|battlefield|True|True|blue_robed_mage|1804/2000|90.20%|90.20%|90.20%|+0.00|1849|97.57%|{"dragon_valley_loc": 45, "valley_entrance": 151}|
|cleric|battlefield|True|True|fire_bat_dragon|1789/2000|89.45%|89.45%|89.45%|+0.00|1850|96.70%|{"valley_entrance": 150, "dragon_valley_loc": 61}|
|cleric|battlefield|True|True|fire_bat_empowered|1833/2000|91.65%|91.65%|91.65%|+0.00|1851|99.03%|{"valley_entrance": 149, "dragon_valley_loc": 18}|
|cleric|battlefield|True|True|mina|1759/2000|87.95%|87.95%|87.95%|+0.00|1850|95.08%|{"dragon_valley_loc": 91, "valley_entrance": 150}|
|cleric|battlefield|True|True|paladin_liese|1919/2000|95.95%|95.80%|95.80%|+0.15|1957|98.06%|{"dragon_valley_loc": 38, "valley_entrance": 43}|
|cleric|battlefield|True|True|hydromancer_elio|1892/2000|94.60%|92.05%|92.05%|+2.55|1947|97.18%|{"dragon_valley_loc": 55, "valley_entrance": 53}|
|cleric|gorge|False|False|none|1499/2000|74.95%|74.95%|74.95%|+0.00|1840|81.47%|{"valley_entrance": 159, "dragon_valley_loc": 341, "gorge_giant_path": 1}|
|cleric|gorge|False|False|robin|1741/2000|87.05%|87.05%|87.05%|+0.00|1938|89.83%|{"dragon_valley_loc": 197, "valley_entrance": 60, "gorge_worm_lair": 2}|
|cleric|gorge|False|False|blue_robed_mage|1693/2000|84.65%|84.65%|84.65%|+0.00|1829|92.56%|{"valley_entrance": 171, "dragon_valley_loc": 136}|
|cleric|gorge|False|False|fire_bat_dragon|1713/2000|85.65%|85.65%|85.65%|+0.00|1845|92.85%|{"dragon_valley_loc": 132, "valley_entrance": 155}|
|cleric|gorge|False|False|fire_bat_empowered|1795/2000|89.75%|89.75%|89.75%|+0.00|1847|97.18%|{"valley_entrance": 153, "dragon_valley_loc": 52}|
|cleric|gorge|False|False|mina|1604/2000|80.20%|80.20%|80.20%|+0.00|1833|87.51%|{"valley_entrance": 165, "dragon_valley_loc": 229, "gorge_worm_lair": 1, "gorge_rockfall_path": 1}|
|cleric|gorge|False|False|paladin_liese|1866/2000|93.30%|94.25%|94.25%|-0.95|1951|95.64%|{"dragon_valley_loc": 85, "valley_entrance": 49}|
|cleric|gorge|False|False|hydromancer_elio|1869/2000|93.45%|89.20%|89.20%|+4.25|1946|96.04%|{"valley_entrance": 54, "dragon_valley_loc": 77}|
|cleric|gorge|True|False|none|1730/2000|86.50%|86.50%|86.50%|+0.00|1838|94.12%|{"dragon_valley_loc": 108, "valley_entrance": 162}|
|cleric|gorge|True|False|robin|1876/2000|93.80%|93.80%|93.80%|+0.00|1939|96.75%|{"dragon_valley_loc": 63, "valley_entrance": 61}|
|cleric|gorge|True|False|blue_robed_mage|1805/2000|90.25%|90.25%|90.25%|+0.00|1833|98.47%|{"valley_entrance": 167, "dragon_valley_loc": 28}|
|cleric|gorge|True|False|fire_bat_dragon|1854/2000|92.70%|92.70%|92.70%|+0.00|1874|98.93%|{"valley_entrance": 126, "dragon_valley_loc": 20}|
|cleric|gorge|True|False|fire_bat_empowered|1871/2000|93.55%|93.55%|93.55%|+0.00|1875|99.79%|{"valley_entrance": 125, "dragon_valley_loc": 4}|
|cleric|gorge|True|False|mina|1788/2000|89.40%|89.40%|89.40%|+0.00|1859|96.18%|{"valley_entrance": 141, "dragon_valley_loc": 71}|
|cleric|gorge|True|False|paladin_liese|1945/2000|97.25%|97.20%|97.20%|+0.05|1960|99.23%|{"dragon_valley_loc": 15, "valley_entrance": 40}|
|cleric|gorge|True|False|hydromancer_elio|1930/2000|96.50%|94.25%|94.25%|+2.25|1949|99.03%|{"valley_entrance": 51, "dragon_valley_loc": 19}|
|mage|village|False|False|none|1409/2000|70.45%|70.45%|70.45%|+0.00|1778|79.25%|{"valley_entrance": 210, "dragon_valley_loc": 369, "village_fire_elemental": 12}|
|mage|village|False|False|blue_robed_mage|1409/2000|70.45%|70.45%|70.45%|+0.00|1778|79.25%|{"valley_entrance": 210, "dragon_valley_loc": 369, "village_fire_elemental": 12}|
|mage|village|False|False|fire_bat_dragon|1510/2000|75.50%|75.50%|75.50%|+0.00|1788|84.45%|{"valley_entrance": 208, "dragon_valley_loc": 278, "village_fire_elemental": 4}|
|mage|battlefield|False|False|none|1608/2000|80.40%|89.00%|80.40%|+0.00|1808|88.94%|{"dragon_valley_loc": 200, "valley_entrance": 137, "grave_chapel": 55}|
|mage|battlefield|False|False|robin|1757/2000|87.85%|93.40%|87.85%|+0.00|1923|91.37%|{"dragon_valley_loc": 166, "valley_entrance": 64, "grave_chapel": 13}|
|mage|battlefield|False|False|blue_robed_mage|1691/2000|84.55%|90.20%|84.55%|+0.00|1807|93.58%|{"valley_entrance": 138, "grave_chapel": 55, "dragon_valley_loc": 116}|
|mage|battlefield|False|False|fire_bat_dragon|1759/2000|87.95%|92.15%|87.95%|+0.00|1862|94.47%|{"valley_entrance": 136, "dragon_valley_loc": 103, "grave_chapel": 2}|
|mage|battlefield|False|False|fire_bat_empowered|1823/2000|91.15%|92.90%|91.15%|+0.00|1865|97.75%|{"valley_entrance": 135, "dragon_valley_loc": 42}|
|mage|battlefield|False|False|mina|1651/2000|82.55%|90.70%|82.55%|+0.00|1823|90.57%|{"dragon_valley_loc": 172, "grave_chapel": 60, "valley_entrance": 117}|
|mage|battlefield|False|False|paladin_liese|1837/2000|91.85%|94.45%|91.50%|+0.35|1928|95.28%|{"dragon_valley_loc": 91, "valley_entrance": 68, "grave_chapel": 4}|
|mage|battlefield|False|False|hydromancer_elio|1809/2000|90.45%|93.70%|86.90%|+3.55|1919|94.27%|{"dragon_valley_loc": 110, "valley_entrance": 72, "grave_chapel": 9}|
|mage|battlefield|False|True|none|1438/2000|71.90%|76.55%|71.90%|+0.00|1804|79.71%|{"dragon_valley_loc": 366, "valley_entrance": 196}|
|mage|battlefield|False|True|robin|1540/2000|77.00%|83.00%|77.00%|+0.00|1904|80.88%|{"dragon_valley_loc": 364, "valley_entrance": 96}|
|mage|battlefield|False|True|blue_robed_mage|1528/2000|76.40%|82.75%|76.40%|+0.00|1807|84.56%|{"valley_entrance": 193, "dragon_valley_loc": 279}|
|mage|battlefield|False|True|fire_bat_dragon|1526/2000|76.30%|84.10%|76.30%|+0.00|1788|85.35%|{"dragon_valley_loc": 262, "valley_entrance": 212}|
|mage|battlefield|False|True|fire_bat_empowered|1638/2000|81.90%|87.25%|81.90%|+0.00|1788|91.61%|{"dragon_valley_loc": 150, "valley_entrance": 212}|
|mage|battlefield|False|True|mina|1478/2000|73.90%|79.50%|73.90%|+0.00|1806|81.84%|{"dragon_valley_loc": 328, "valley_entrance": 194}|
|mage|battlefield|False|True|paladin_liese|1595/2000|79.75%|87.05%|79.05%|+0.70|1910|83.51%|{"dragon_valley_loc": 315, "valley_entrance": 90}|
|mage|battlefield|False|True|hydromancer_elio|1676/2000|83.80%|86.00%|81.55%|+2.25|1904|88.03%|{"dragon_valley_loc": 228, "valley_entrance": 96}|
|mage|battlefield|True|False|none|1729/2000|86.45%|86.65%|86.45%|+0.00|1801|96.00%|{"valley_entrance": 186, "grave_chapel": 13, "dragon_valley_loc": 72}|
|mage|battlefield|True|False|robin|1851/2000|92.55%|92.55%|92.55%|+0.00|1929|95.96%|{"valley_entrance": 71, "dragon_valley_loc": 78}|
|mage|battlefield|True|False|blue_robed_mage|1752/2000|87.60%|87.85%|87.60%|+0.00|1804|97.12%|{"valley_entrance": 183, "grave_chapel": 13, "dragon_valley_loc": 52}|
|mage|battlefield|True|False|fire_bat_dragon|1788/2000|89.40%|89.40%|89.40%|+0.00|1823|98.08%|{"valley_entrance": 177, "dragon_valley_loc": 35}|
|mage|battlefield|True|False|fire_bat_empowered|1808/2000|90.40%|90.40%|90.40%|+0.00|1825|99.07%|{"valley_entrance": 175, "dragon_valley_loc": 17}|
|mage|battlefield|True|False|mina|1754/2000|87.70%|88.30%|87.70%|+0.00|1822|96.27%|{"dragon_valley_loc": 68, "valley_entrance": 165, "grave_chapel": 13}|
|mage|battlefield|True|False|paladin_liese|1896/2000|94.80%|94.20%|94.30%|+0.50|1935|97.98%|{"dragon_valley_loc": 39, "valley_entrance": 64, "grave_chapel": 1}|
|mage|battlefield|True|False|hydromancer_elio|1886/2000|94.30%|92.70%|92.40%|+1.90|1923|98.08%|{"valley_entrance": 76, "dragon_valley_loc": 37, "grave_chapel": 1}|
|mage|battlefield|True|True|none|1512/2000|75.60%|75.60%|75.60%|+0.00|1784|84.75%|{"valley_entrance": 216, "dragon_valley_loc": 272}|
|mage|battlefield|True|True|robin|1656/2000|82.80%|82.80%|82.80%|+0.00|1906|86.88%|{"dragon_valley_loc": 250, "valley_entrance": 94}|
|mage|battlefield|True|True|blue_robed_mage|1633/2000|81.65%|81.65%|81.65%|+0.00|1786|91.43%|{"valley_entrance": 214, "dragon_valley_loc": 153}|
|mage|battlefield|True|True|fire_bat_dragon|1667/2000|83.35%|83.35%|83.35%|+0.00|1775|93.92%|{"valley_entrance": 225, "dragon_valley_loc": 108}|
|mage|battlefield|True|True|fire_bat_empowered|1730/2000|86.50%|86.50%|86.50%|+0.00|1775|97.46%|{"valley_entrance": 225, "dragon_valley_loc": 45}|
|mage|battlefield|True|True|mina|1559/2000|77.95%|77.95%|77.95%|+0.00|1786|87.29%|{"dragon_valley_loc": 227, "valley_entrance": 214}|
|mage|battlefield|True|True|paladin_liese|1768/2000|88.40%|87.30%|87.30%|+1.10|1912|92.47%|{"valley_entrance": 88, "dragon_valley_loc": 144}|
|mage|battlefield|True|True|hydromancer_elio|1765/2000|88.25%|85.60%|85.60%|+2.65|1907|92.55%|{"dragon_valley_loc": 142, "valley_entrance": 93}|
|mage|gorge|False|False|none|1540/2000|77.00%|77.00%|77.00%|+0.00|1836|83.88%|{"dragon_valley_loc": 296, "valley_entrance": 154, "gorge_worm_lair": 10}|
|mage|gorge|False|False|robin|1636/2000|81.80%|81.80%|81.80%|+0.00|1893|86.42%|{"valley_entrance": 94, "dragon_valley_loc": 257, "gorge_worm_lair": 13}|
|mage|gorge|False|False|blue_robed_mage|1655/2000|82.75%|82.75%|82.75%|+0.00|1839|89.99%|{"dragon_valley_loc": 184, "valley_entrance": 155, "gorge_worm_lair": 6}|
|mage|gorge|False|False|fire_bat_dragon|1652/2000|82.60%|82.60%|82.60%|+0.00|1814|91.07%|{"valley_entrance": 180, "dragon_valley_loc": 162, "gorge_worm_lair": 6}|
|mage|gorge|False|False|fire_bat_empowered|1724/2000|86.20%|86.20%|86.20%|+0.00|1819|94.78%|{"valley_entrance": 180, "dragon_valley_loc": 95, "gorge_worm_lair": 1}|
|mage|gorge|False|False|mina|1557/2000|77.85%|77.85%|77.85%|+0.00|1828|85.18%|{"valley_entrance": 164, "dragon_valley_loc": 271, "gorge_worm_lair": 8}|
|mage|gorge|False|False|paladin_liese|1714/2000|85.70%|86.10%|86.10%|-0.40|1907|89.88%|{"valley_entrance": 88, "dragon_valley_loc": 193, "gorge_worm_lair": 5}|
|mage|gorge|False|False|hydromancer_elio|1758/2000|87.90%|85.20%|85.20%|+2.70|1926|91.28%|{"valley_entrance": 74, "dragon_valley_loc": 168}|
|mage|gorge|True|False|none|1668/2000|83.40%|83.40%|83.40%|+0.00|1816|91.85%|{"dragon_valley_loc": 148, "valley_entrance": 183, "gorge_worm_lair": 1}|
|mage|gorge|True|False|robin|1747/2000|87.35%|87.35%|87.35%|+0.00|1908|91.56%|{"valley_entrance": 90, "dragon_valley_loc": 161, "gorge_worm_lair": 2}|
|mage|gorge|True|False|blue_robed_mage|1732/2000|86.60%|86.60%|86.60%|+0.00|1818|95.27%|{"valley_entrance": 182, "dragon_valley_loc": 86}|
|mage|gorge|True|False|fire_bat_dragon|1735/2000|86.75%|86.75%|86.75%|+0.00|1812|95.75%|{"dragon_valley_loc": 77, "valley_entrance": 188}|
|mage|gorge|True|False|fire_bat_empowered|1797/2000|89.85%|89.85%|89.85%|+0.00|1815|99.01%|{"valley_entrance": 185, "dragon_valley_loc": 18}|
|mage|gorge|True|False|mina|1689/2000|84.45%|84.45%|84.45%|+0.00|1819|92.85%|{"valley_entrance": 181, "dragon_valley_loc": 130}|
|mage|gorge|True|False|paladin_liese|1853/2000|92.65%|92.35%|92.35%|+0.30|1919|96.56%|{"dragon_valley_loc": 66, "valley_entrance": 81}|
|mage|gorge|True|False|hydromancer_elio|1841/2000|92.05%|89.65%|89.65%|+2.40|1928|95.49%|{"valley_entrance": 72, "dragon_valley_loc": 87}|
|thief|village|False|False|none|1708/2000|85.40%|85.40%|85.40%|+0.00|1931|88.45%|{"dragon_valley_loc": 223, "village_fire_elemental": 35, "valley_entrance": 34}|
|thief|village|False|False|blue_robed_mage|1708/2000|85.40%|85.40%|85.40%|+0.00|1931|88.45%|{"dragon_valley_loc": 223, "village_fire_elemental": 35, "valley_entrance": 34}|
|thief|village|False|False|fire_bat_dragon|1864/2000|93.20%|93.20%|93.20%|+0.00|1953|95.44%|{"dragon_valley_loc": 89, "village_fire_elemental": 24, "valley_entrance": 23}|
|thief|battlefield|False|False|none|1787/2000|89.35%|92.40%|89.35%|+0.00|1959|91.22%|{"dragon_valley_loc": 172, "grave_chapel": 13, "valley_entrance": 28}|
|thief|battlefield|False|False|robin|1922/2000|96.10%|97.10%|96.10%|+0.00|1993|96.44%|{"dragon_valley_loc": 71, "valley_entrance": 7}|
|thief|battlefield|False|False|blue_robed_mage|1882/2000|94.10%|95.70%|94.10%|+0.00|1959|96.07%|{"dragon_valley_loc": 77, "grave_chapel": 13, "valley_entrance": 28}|
|thief|battlefield|False|False|fire_bat_dragon|1916/2000|95.80%|96.85%|95.80%|+0.00|1971|97.21%|{"dragon_valley_loc": 55, "valley_entrance": 29}|
|thief|battlefield|False|False|fire_bat_empowered|1950/2000|97.50%|98.30%|97.50%|+0.00|1972|98.88%|{"dragon_valley_loc": 22, "valley_entrance": 28}|
|thief|battlefield|False|False|mina|1874/2000|93.70%|95.90%|93.70%|+0.00|1971|95.08%|{"dragon_valley_loc": 97, "grave_chapel": 3, "valley_entrance": 26}|
|thief|battlefield|False|False|paladin_liese|1962/2000|98.10%|98.95%|98.45%|-0.35|1994|98.40%|{"dragon_valley_loc": 32, "valley_entrance": 6}|
|thief|battlefield|False|False|hydromancer_elio|1968/2000|98.40%|97.60%|96.95%|+1.45|1990|98.89%|{"dragon_valley_loc": 22, "valley_entrance": 10}|
|thief|battlefield|False|True|none|1752/2000|87.60%|90.75%|87.60%|+0.00|1972|88.84%|{"dragon_valley_loc": 220, "valley_entrance": 28}|
|thief|battlefield|False|True|robin|1828/2000|91.40%|94.00%|91.40%|+0.00|1990|91.86%|{"dragon_valley_loc": 162, "valley_entrance": 10}|
|thief|battlefield|False|True|blue_robed_mage|1859/2000|92.95%|94.90%|92.95%|+0.00|1973|94.22%|{"dragon_valley_loc": 114, "valley_entrance": 27}|
|thief|battlefield|False|True|fire_bat_dragon|1895/2000|94.75%|95.75%|94.75%|+0.00|1978|95.80%|{"dragon_valley_loc": 83, "valley_entrance": 22}|
|thief|battlefield|False|True|fire_bat_empowered|1931/2000|96.55%|97.70%|96.55%|+0.00|1978|97.62%|{"valley_entrance": 22, "dragon_valley_loc": 47}|
|thief|battlefield|False|True|mina|1821/2000|91.05%|94.00%|91.05%|+0.00|1975|92.20%|{"dragon_valley_loc": 154, "valley_entrance": 25}|
|thief|battlefield|False|True|paladin_liese|1904/2000|95.20%|96.30%|93.95%|+1.25|1991|95.63%|{"dragon_valley_loc": 87, "valley_entrance": 9}|
|thief|battlefield|False|True|hydromancer_elio|1918/2000|95.90%|96.65%|94.50%|+1.40|1990|96.38%|{"dragon_valley_loc": 72, "valley_entrance": 10}|
|thief|battlefield|True|False|none|1886/2000|94.30%|94.40%|94.30%|+0.00|1967|95.88%|{"dragon_valley_loc": 81, "grave_chapel": 2, "valley_entrance": 31}|
|thief|battlefield|True|False|robin|1951/2000|97.55%|97.55%|97.55%|+0.00|1995|97.79%|{"dragon_valley_loc": 44, "valley_entrance": 5}|
|thief|battlefield|True|False|blue_robed_mage|1929/2000|96.45%|96.55%|96.45%|+0.00|1968|98.02%|{"dragon_valley_loc": 39, "grave_chapel": 2, "valley_entrance": 30}|
|thief|battlefield|True|False|fire_bat_dragon|1941/2000|97.05%|97.05%|97.05%|+0.00|1970|98.53%|{"dragon_valley_loc": 29, "valley_entrance": 30}|
|thief|battlefield|True|False|fire_bat_empowered|1963/2000|98.15%|98.15%|98.15%|+0.00|1970|99.64%|{"valley_entrance": 30, "dragon_valley_loc": 7}|
|thief|battlefield|True|False|mina|1931/2000|96.55%|96.60%|96.55%|+0.00|1977|97.67%|{"valley_entrance": 22, "grave_chapel": 1, "dragon_valley_loc": 46}|
|thief|battlefield|True|False|paladin_liese|1984/2000|99.20%|99.00%|99.00%|+0.20|1995|99.45%|{"dragon_valley_loc": 11, "valley_entrance": 5}|
|thief|battlefield|True|False|hydromancer_elio|1978/2000|98.90%|97.85%|97.85%|+1.05|1992|99.30%|{"dragon_valley_loc": 14, "valley_entrance": 8}|
|thief|battlefield|True|True|none|1827/2000|91.35%|91.35%|91.35%|+0.00|1975|92.51%|{"dragon_valley_loc": 148, "valley_entrance": 25}|
|thief|battlefield|True|True|robin|1881/2000|94.05%|94.05%|94.05%|+0.00|1991|94.48%|{"dragon_valley_loc": 110, "valley_entrance": 9}|
|thief|battlefield|True|True|blue_robed_mage|1907/2000|95.35%|95.35%|95.35%|+0.00|1975|96.56%|{"dragon_valley_loc": 68, "valley_entrance": 25}|
|thief|battlefield|True|True|fire_bat_dragon|1922/2000|96.10%|96.10%|96.10%|+0.00|1982|96.97%|{"dragon_valley_loc": 60, "valley_entrance": 18}|
|thief|battlefield|True|True|fire_bat_empowered|1955/2000|97.75%|97.75%|97.75%|+0.00|1982|98.64%|{"valley_entrance": 18, "dragon_valley_loc": 27}|
|thief|battlefield|True|True|mina|1881/2000|94.05%|94.05%|94.05%|+0.00|1976|95.19%|{"dragon_valley_loc": 95, "valley_entrance": 24}|
|thief|battlefield|True|True|paladin_liese|1936/2000|96.80%|96.30%|96.30%|+0.50|1991|97.24%|{"dragon_valley_loc": 55, "valley_entrance": 9}|
|thief|battlefield|True|True|hydromancer_elio|1957/2000|97.85%|96.65%|96.65%|+1.20|1990|98.34%|{"dragon_valley_loc": 33, "valley_entrance": 10}|
|thief|gorge|False|False|none|1842/2000|92.10%|92.10%|92.10%|+0.00|1972|93.41%|{"dragon_valley_loc": 130, "valley_entrance": 28}|
|thief|gorge|False|False|robin|1879/2000|93.95%|93.95%|93.95%|+0.00|1985|94.66%|{"dragon_valley_loc": 106, "valley_entrance": 15}|
|thief|gorge|False|False|blue_robed_mage|1922/2000|96.10%|96.10%|96.10%|+0.00|1973|97.42%|{"valley_entrance": 26, "dragon_valley_loc": 51, "gorge_rockfall_path": 1}|
|thief|gorge|False|False|fire_bat_dragon|1909/2000|95.45%|95.45%|95.45%|+0.00|1969|96.95%|{"dragon_valley_loc": 60, "valley_entrance": 31}|
|thief|gorge|False|False|fire_bat_empowered|1954/2000|97.70%|97.70%|97.70%|+0.00|1969|99.24%|{"valley_entrance": 31, "dragon_valley_loc": 15}|
|thief|gorge|False|False|mina|1860/2000|93.00%|93.00%|93.00%|+0.00|1967|94.56%|{"dragon_valley_loc": 107, "valley_entrance": 30, "gorge_rockfall_path": 2, "gorge_giant_path": 1}|
|thief|gorge|False|False|paladin_liese|1945/2000|97.25%|97.20%|97.20%|+0.05|1988|97.84%|{"valley_entrance": 12, "dragon_valley_loc": 43}|
|thief|gorge|False|False|hydromancer_elio|1950/2000|97.50%|96.45%|96.45%|+1.05|1990|97.99%|{"dragon_valley_loc": 40, "valley_entrance": 10}|
|thief|gorge|True|False|none|1891/2000|94.55%|94.55%|94.55%|+0.00|1974|95.80%|{"dragon_valley_loc": 83, "valley_entrance": 26}|
|thief|gorge|True|False|robin|1928/2000|96.40%|96.40%|96.40%|+0.00|1984|97.18%|{"dragon_valley_loc": 56, "valley_entrance": 16}|
|thief|gorge|True|False|blue_robed_mage|1941/2000|97.05%|97.05%|97.05%|+0.00|1974|98.33%|{"dragon_valley_loc": 33, "valley_entrance": 26}|
|thief|gorge|True|False|fire_bat_dragon|1944/2000|97.20%|97.20%|97.20%|+0.00|1973|98.53%|{"dragon_valley_loc": 29, "valley_entrance": 27}|
|thief|gorge|True|False|fire_bat_empowered|1967/2000|98.35%|98.35%|98.35%|+0.00|1974|99.65%|{"valley_entrance": 26, "dragon_valley_loc": 7}|
|thief|gorge|True|False|mina|1904/2000|95.20%|95.20%|95.20%|+0.00|1971|96.60%|{"dragon_valley_loc": 67, "valley_entrance": 29}|
|thief|gorge|True|False|paladin_liese|1963/2000|98.15%|98.50%|98.50%|-0.35|1989|98.69%|{"dragon_valley_loc": 26, "valley_entrance": 11}|
|thief|gorge|True|False|hydromancer_elio|1975/2000|98.75%|98.05%|98.05%|+0.70|1990|99.25%|{"dragon_valley_loc": 15, "valley_entrance": 10}|

## 结论与设计待办

- 准备=False，四职业共同最优路线：无；达标=True。
- 准备=True，四职业共同最优路线：无；达标=True。
- 核心门槛通过=False；核心未严格领先3项。准备／诅咒仅报告组未严格领先6/16项，不阻止核心门槛通过。
- 三路线≤8pp仍有4/8项越界；保留全部结果，按设计决定不修改旧内容。
- TODO(design): 核心thief/battlefield未严格领先hydromancer_elio（-0.30pp）；如实报告，不继续调参。
- TODO(design): 核心hero/gorge未严格领先paladin_liese（+0.00pp）；如实报告，不继续调参。
- TODO(design): 核心thief/gorge未严格领先fire_bat_empowered（-0.20pp）；如实报告，不继续调参。
- 墓守外套沿用第二轮决定；两人的正式参数采用第三轮指定组合。第二轮完整筛选与24项边界证据见[调参报告](037-companion-tuning.md)。未改旧路线敌人、DC、奖励或提示词。

## 两名同行者路线外复核

每人排除各自本路线的三场遭遇，仍按现有最强同行者+3pp逐职业逐场比较。リーゼ沿用033对照集合，エリオ沿用035（包含本轮リーゼ）；独立满资源逐战检查，不混同连续路线通关率。完整结果见[第三轮路线外报告](037-companion-outside.md)、[JSON](037-companion-outside.json)；[第二轮对照](037-companion-outside-round2.md)保留。

N=1000；共256项上限比较，越界13项。

|同行者|职业|遭遇|本轮胜率|现有最强|对照胜率|超出pp|
|---|---|---|---:|---|---:|---:|
|hydromancer_elio|mage|dragon_valley_loc|82.30%|fire_bat_empowered|79.00%|+3.30|
|paladin_liese|thief|merchant_battle|73.90%|mina|66.90%|+7.00|
|paladin_liese|thief|goblin_fort_fourth|87.70%|robin|82.60%|+5.10|
|hydromancer_elio|thief|village_fire_elemental|96.80%|fire_bat_empowered|93.50%|+3.30|
|hydromancer_elio|cleric|draco_battle|86.60%|fire_bat_empowered|83.10%|+3.50|
|hydromancer_elio|mage|draco_battle|79.30%|fire_bat_empowered|76.20%|+3.10|
|hydromancer_elio|thief|draco_battle|86.10%|fire_bat_empowered|81.90%|+4.20|
|hydromancer_elio|cleric|cave_crystal_corridor|97.80%|paladin_liese|94.00%|+3.80|
|paladin_liese|mage|valley_entrance|99.60%|robin|96.20%|+3.40|
|paladin_liese|hero|valley_ledge|93.50%|robin|87.90%|+5.60|
|paladin_liese|cleric|valley_ledge|94.80%|robin|86.40%|+8.40|
|paladin_liese|mage|valley_ledge|91.70%|robin|82.20%|+9.50|
|paladin_liese|thief|valley_ledge|93.10%|robin|88.00%|+5.10|

TODO(design): 上表超出+3pp的项目如实保留，本轮不再调参。

## 路线差距定位

|职业|路线|准备|通关率|路线段死亡|煤の亡霊死亡|イグニス死亡|
|---|---|---|---:|---:|---:|---:|
|hero|village|False|84.20%|1|249|66|
|hero|battlefield|False|85.60%|41|231|16|
|hero|battlefield|True|87.95%|16|209|16|
|hero|gorge|False|85.00%|0|263|37|
|hero|gorge|True|85.50%|0|246|44|
|cleric|village|False|73.70%|6|196|324|
|cleric|battlefield|False|73.80%|126|147|251|
|cleric|battlefield|True|88.75%|23|150|52|
|cleric|gorge|False|74.95%|1|159|341|
|cleric|gorge|True|86.50%|0|162|108|
|mage|village|False|70.45%|12|210|369|
|mage|battlefield|False|80.40%|55|137|200|
|mage|battlefield|True|86.45%|13|186|72|
|mage|gorge|False|77.00%|10|154|296|
|mage|gorge|True|83.40%|1|183|148|
|thief|village|False|85.40%|35|34|223|
|thief|battlefield|False|89.35%|13|28|172|
|thief|battlefield|True|94.30%|2|31|81|
|thief|gorge|False|92.10%|0|28|130|
|thief|gorge|True|94.55%|0|26|83|

设计负责人已明确：未准备、无同行者、无诅咒的三路线差距中，魔法使い的9.95pp（村70.45%、古戦場80.40%、峡谷77.00%）来自村路线本身，属于旧内容，本轮不改。该比较不使用033–035新增的可调敌人、DC、同行者、装备或奖励金币；034聖銀只入背包，古戦場两颗生命の果実来自031墓守骑士。

上述死亡地点是差异定位，不是单因素因果实验。不同路线的永久增益、装备与消耗品进入共同后程时不同；保留的逐战样本提供资源证据。村路线及共同后程属于旧内容，不通过修改这些数值来达成8pp。

## 复现

```powershell
python -m scripts.balance.ch3_routes --n 2000 --seed 20261018 --workers 16
```

原始JSON包含前置回放、每种条件的准备交易与起点、各失败地点和胜利的首个完整样本、资源继承、消耗、源文件SHA-256。

## 运行恢复记录

首次运行在增量报告写入时发生Windows OSError errno22；已保存136组。核对源文件指纹和重建检查点一致后，用同一模拟函数、N=2000及seed=20261018补跑缺失68组（24 workers），按原顺序合并成完整204组。补跑逐组追加保存，最终统一写入报告。JSON的run_recovery保留缺失条件、原始片段指纹及恢复口径。
