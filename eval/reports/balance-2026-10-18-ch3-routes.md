# 037 第三章三条路线连续平衡

N=2000／职业／条件；seed=20261018；204组，共408,000条连续路线。完全离线。

## 口径与推断

- 起点为第2章结束的森の出口。复用可达检查点回放，先完成ゴブリン砦并归还箱子，再通过森林、回城支付10G休息后返回出口；Lv3、240G，四职业具体背包和全部前置动作见JSON。前置战斗假定获胜、不估算消耗，结论条件于这个检查点，不是从新游戏开始的通关率。
- 原主线Lv2起点只有125G，不能支付195G整套准备；为避免凭空补钱，所有组统一采用上述砦后检查点。准备组实际购买聖銀120G、锻造30G、鎖帷子40G、礼拝堂休息5G；未准备组不购买。墓守外套仍按原剧情替换防具。
- 同行者和诅咒采用031/033/035既有的机制对照：起点指定同行者，诅咒组只携带呪われた短剣、不装备；不计招募费用、获取诅咒代价，不能当成这些条件的完整招募路线。火コウモリ竜普通／虹晶强化分别列出；其他同行者控制包括ロビン、ミーナ、ワーロック及另一条路线的同行者。
- 保留剧情中的同行者离队；村路线的ワーロック在森林出口离队，所以该组不会强行留住他。
- 村路线慎重接近、离开民家；古戦場骨野潜行（诅咒放行）、塔取外套并休息、沼地潜行、骑士战（诅咒放行）；峡谷潜行、搜营地并休息、查爪痕、巨人潜行、ワーム潜行（エリオ绕过）。
- 三路都汇入避難所。共同后程采用现行hp70付费休息策略、竜の谷亡霊潜行、过桥、イグニス战；不额外走冰元素／Xanxus支线，不净化。所有判定投真实d20、失败实战，HP/MP/SP、金币、背包跨战继承，永久品立即使用，无重来。
- 分母始终是全部起点样本，包含提前死亡；同时列出到Boss的样本数与条件胜率。每组共享初始随机种子，同行者耗骰不同，不代表逐骰配对。判据采用样本点估计，不把抽样误差当成设计容差。
- ‘三路相差≤8pp’对未准备／已准备分别比较（村路线均为未准备），主比较无诅咒；诅咒单列。同率并列最优也计入四职业共同最优。

## 无同行者、无诅咒

|职业|城塞准备|村|古戦場|峡谷|最大差pp|≤8pp|
|---|---|---:|---:|---:|---:|---|
|hero|False|84.20%|88.30%|85.00%|4.10|True|
|cleric|False|73.70%|88.85%|74.95%|15.15|False|
|mage|False|70.45%|89.00%|77.00%|18.55|False|
|thief|False|85.40%|92.40%|92.10%|7.00|True|
|hero|True|84.20%|88.85%|85.50%|4.65|True|
|cleric|True|73.70%|89.80%|86.50%|16.10|False|
|mage|True|70.45%|86.65%|83.40%|16.20|False|
|thief|True|85.40%|94.40%|94.55%|9.15|False|

## 本路线对策同行者

|职业|路线|准备|诅咒|对策提升pp|其他最强|其提升pp|达标|
|---|---|---|---|---:|---|---:|---|
|hero|battlefield|False|False|+7.35|robin|+7.10|True|
|cleric|battlefield|False|False|+7.85|hydromancer_elio|+6.15|True|
|mage|battlefield|False|False|+5.45|hydromancer_elio|+4.70|True|
|thief|battlefield|False|False|+6.55|fire_bat_empowered|+5.90|True|
|hero|battlefield|False|True|+9.10|robin|+7.00|True|
|cleric|battlefield|False|True|+10.75|hydromancer_elio|+6.75|True|
|mage|battlefield|False|True|+10.50|fire_bat_empowered|+10.70|False|
|thief|battlefield|False|True|+5.55|fire_bat_empowered|+6.95|False|
|hero|battlefield|True|False|+7.40|robin|+7.00|True|
|cleric|battlefield|True|False|+6.90|hydromancer_elio|+5.25|True|
|mage|battlefield|True|False|+7.55|hydromancer_elio|+6.05|True|
|thief|battlefield|True|False|+4.60|fire_bat_empowered|+3.75|True|
|hero|battlefield|True|True|+9.75|robin|+6.75|True|
|cleric|battlefield|True|True|+10.45|hydromancer_elio|+6.70|True|
|mage|battlefield|True|True|+11.70|fire_bat_empowered|+10.90|True|
|thief|battlefield|True|True|+4.95|fire_bat_empowered|+6.40|False|
|hero|gorge|False|False|+7.25|paladin_liese|+10.65|False|
|cleric|gorge|False|False|+14.25|paladin_liese|+19.30|False|
|mage|gorge|False|False|+8.20|fire_bat_empowered|+9.20|False|
|thief|gorge|False|False|+4.35|fire_bat_empowered|+5.60|False|
|hero|gorge|True|False|+7.00|paladin_liese|+10.90|False|
|cleric|gorge|True|False|+7.75|paladin_liese|+10.70|False|
|mage|gorge|True|False|+6.25|paladin_liese|+8.95|False|
|thief|gorge|True|False|+3.50|paladin_liese|+3.95|False|

## 各组原始统计

|职业|路线|准备|诅咒|同行者|胜/N|通关率|到达Boss|Boss条件胜率|首次败北地点|
|---|---|---|---|---|---:|---:|---:|---:|---|
|hero|village|False|False|none|1684/2000|84.20%|1750|96.23%|{"valley_entrance": 249, "dragon_valley_loc": 66, "village_fire_elemental": 1}|
|hero|village|False|False|blue_robed_mage|1684/2000|84.20%|1750|96.23%|{"valley_entrance": 249, "dragon_valley_loc": 66, "village_fire_elemental": 1}|
|hero|village|False|False|fire_bat_dragon|1756/2000|87.80%|1787|98.27%|{"valley_entrance": 213, "dragon_valley_loc": 31}|
|hero|battlefield|False|False|none|1766/2000|88.30%|1774|99.55%|{"valley_entrance": 222, "dragon_valley_loc": 8, "grave_chapel": 4}|
|hero|battlefield|False|False|robin|1908/2000|95.40%|1911|99.84%|{"valley_entrance": 89, "dragon_valley_loc": 3}|
|hero|battlefield|False|False|blue_robed_mage|1784/2000|89.20%|1785|99.94%|{"valley_entrance": 211, "grave_chapel": 4, "dragon_valley_loc": 1}|
|hero|battlefield|False|False|fire_bat_dragon|1798/2000|89.90%|1799|99.94%|{"valley_entrance": 201, "dragon_valley_loc": 1}|
|hero|battlefield|False|False|fire_bat_empowered|1802/2000|90.10%|1802|100.00%|{"valley_entrance": 198}|
|hero|battlefield|False|False|mina|1781/2000|89.05%|1784|99.83%|{"valley_entrance": 213, "grave_chapel": 3, "dragon_valley_loc": 3}|
|hero|battlefield|False|False|paladin_liese|1913/2000|95.65%|1913|100.00%|{"valley_entrance": 87}|
|hero|battlefield|False|False|hydromancer_elio|1875/2000|93.75%|1879|99.79%|{"valley_entrance": 121, "dragon_valley_loc": 4}|
|hero|battlefield|False|True|none|1709/2000|85.45%|1753|97.49%|{"valley_entrance": 247, "dragon_valley_loc": 44}|
|hero|battlefield|False|True|robin|1849/2000|92.45%|1881|98.30%|{"dragon_valley_loc": 32, "valley_entrance": 119}|
|hero|battlefield|False|True|blue_robed_mage|1752/2000|87.60%|1759|99.60%|{"valley_entrance": 241, "dragon_valley_loc": 7}|
|hero|battlefield|False|True|fire_bat_dragon|1745/2000|87.25%|1756|99.37%|{"dragon_valley_loc": 11, "valley_entrance": 244}|
|hero|battlefield|False|True|fire_bat_empowered|1753/2000|87.65%|1757|99.77%|{"valley_entrance": 243, "dragon_valley_loc": 4}|
|hero|battlefield|False|True|mina|1733/2000|86.65%|1759|98.52%|{"valley_entrance": 241, "dragon_valley_loc": 26}|
|hero|battlefield|False|True|paladin_liese|1891/2000|94.55%|1897|99.68%|{"valley_entrance": 103, "dragon_valley_loc": 6}|
|hero|battlefield|False|True|hydromancer_elio|1842/2000|92.10%|1860|99.03%|{"valley_entrance": 140, "dragon_valley_loc": 18}|
|hero|battlefield|True|False|none|1777/2000|88.85%|1792|99.16%|{"valley_entrance": 204, "grave_chapel": 4, "dragon_valley_loc": 15}|
|hero|battlefield|True|False|robin|1917/2000|95.85%|1924|99.64%|{"valley_entrance": 76, "dragon_valley_loc": 7}|
|hero|battlefield|True|False|blue_robed_mage|1797/2000|89.85%|1799|99.89%|{"valley_entrance": 197, "grave_chapel": 4, "dragon_valley_loc": 2}|
|hero|battlefield|True|False|fire_bat_dragon|1805/2000|90.25%|1811|99.67%|{"valley_entrance": 189, "dragon_valley_loc": 6}|
|hero|battlefield|True|False|fire_bat_empowered|1811/2000|90.55%|1812|99.94%|{"valley_entrance": 188, "dragon_valley_loc": 1}|
|hero|battlefield|True|False|mina|1777/2000|88.85%|1783|99.66%|{"valley_entrance": 211, "grave_chapel": 6, "dragon_valley_loc": 6}|
|hero|battlefield|True|False|paladin_liese|1925/2000|96.25%|1925|100.00%|{"valley_entrance": 75}|
|hero|battlefield|True|False|hydromancer_elio|1882/2000|94.10%|1887|99.74%|{"valley_entrance": 113, "dragon_valley_loc": 5}|
|hero|battlefield|True|True|none|1688/2000|84.40%|1770|95.37%|{"valley_entrance": 230, "dragon_valley_loc": 82}|
|hero|battlefield|True|True|robin|1823/2000|91.15%|1882|96.87%|{"dragon_valley_loc": 59, "valley_entrance": 118}|
|hero|battlefield|True|True|blue_robed_mage|1756/2000|87.80%|1773|99.04%|{"valley_entrance": 227, "dragon_valley_loc": 17}|
|hero|battlefield|True|True|fire_bat_dragon|1742/2000|87.10%|1763|98.81%|{"valley_entrance": 237, "dragon_valley_loc": 21}|
|hero|battlefield|True|True|fire_bat_empowered|1758/2000|87.90%|1764|99.66%|{"valley_entrance": 236, "dragon_valley_loc": 6}|
|hero|battlefield|True|True|mina|1713/2000|85.65%|1770|96.78%|{"valley_entrance": 230, "dragon_valley_loc": 57}|
|hero|battlefield|True|True|paladin_liese|1883/2000|94.15%|1898|99.21%|{"valley_entrance": 102, "dragon_valley_loc": 15}|
|hero|battlefield|True|True|hydromancer_elio|1816/2000|90.80%|1859|97.69%|{"valley_entrance": 141, "dragon_valley_loc": 43}|
|hero|gorge|False|False|none|1700/2000|85.00%|1737|97.87%|{"valley_entrance": 263, "dragon_valley_loc": 37}|
|hero|gorge|False|False|robin|1865/2000|93.25%|1907|97.80%|{"valley_entrance": 93, "dragon_valley_loc": 42}|
|hero|gorge|False|False|blue_robed_mage|1716/2000|85.80%|1731|99.13%|{"valley_entrance": 269, "dragon_valley_loc": 15}|
|hero|gorge|False|False|fire_bat_dragon|1769/2000|88.45%|1784|99.16%|{"valley_entrance": 216, "dragon_valley_loc": 15}|
|hero|gorge|False|False|fire_bat_empowered|1780/2000|89.00%|1783|99.83%|{"valley_entrance": 217, "dragon_valley_loc": 3}|
|hero|gorge|False|False|mina|1728/2000|86.40%|1768|97.74%|{"valley_entrance": 232, "dragon_valley_loc": 40}|
|hero|gorge|False|False|paladin_liese|1913/2000|95.65%|1919|99.69%|{"valley_entrance": 81, "dragon_valley_loc": 6}|
|hero|gorge|False|False|hydromancer_elio|1845/2000|92.25%|1870|98.66%|{"dragon_valley_loc": 25, "valley_entrance": 130}|
|hero|gorge|True|False|none|1710/2000|85.50%|1754|97.49%|{"valley_entrance": 246, "dragon_valley_loc": 44}|
|hero|gorge|True|False|robin|1883/2000|94.15%|1905|98.85%|{"valley_entrance": 95, "dragon_valley_loc": 22}|
|hero|gorge|True|False|blue_robed_mage|1751/2000|87.55%|1757|99.66%|{"valley_entrance": 243, "dragon_valley_loc": 6}|
|hero|gorge|True|False|fire_bat_dragon|1799/2000|89.95%|1809|99.45%|{"valley_entrance": 191, "dragon_valley_loc": 10}|
|hero|gorge|True|False|fire_bat_empowered|1812/2000|90.60%|1812|100.00%|{"valley_entrance": 188}|
|hero|gorge|True|False|mina|1751/2000|87.55%|1775|98.65%|{"valley_entrance": 225, "dragon_valley_loc": 24}|
|hero|gorge|True|False|paladin_liese|1928/2000|96.40%|1930|99.90%|{"valley_entrance": 70, "dragon_valley_loc": 2}|
|hero|gorge|True|False|hydromancer_elio|1850/2000|92.50%|1866|99.14%|{"valley_entrance": 134, "dragon_valley_loc": 16}|
|cleric|village|False|False|none|1474/2000|73.70%|1798|81.98%|{"dragon_valley_loc": 324, "village_fire_elemental": 6, "valley_entrance": 196}|
|cleric|village|False|False|blue_robed_mage|1474/2000|73.70%|1798|81.98%|{"dragon_valley_loc": 324, "village_fire_elemental": 6, "valley_entrance": 196}|
|cleric|village|False|False|fire_bat_dragon|1692/2000|84.60%|1850|91.46%|{"valley_entrance": 149, "dragon_valley_loc": 158, "village_fire_elemental": 1}|
|cleric|battlefield|False|False|none|1777/2000|88.85%|1845|96.31%|{"dragon_valley_loc": 68, "valley_entrance": 151, "grave_chapel": 4}|
|cleric|battlefield|False|False|robin|1878/2000|93.90%|1923|97.66%|{"valley_entrance": 77, "dragon_valley_loc": 45}|
|cleric|battlefield|False|False|blue_robed_mage|1832/2000|91.60%|1849|99.08%|{"valley_entrance": 147, "dragon_valley_loc": 17, "grave_chapel": 4}|
|cleric|battlefield|False|False|fire_bat_dragon|1863/2000|93.15%|1883|98.94%|{"valley_entrance": 117, "dragon_valley_loc": 20}|
|cleric|battlefield|False|False|fire_bat_empowered|1876/2000|93.80%|1882|99.68%|{"dragon_valley_loc": 6, "valley_entrance": 118}|
|cleric|battlefield|False|False|mina|1815/2000|90.75%|1856|97.79%|{"dragon_valley_loc": 41, "valley_entrance": 142, "grave_chapel": 2}|
|cleric|battlefield|False|False|paladin_liese|1934/2000|96.70%|1939|99.74%|{"dragon_valley_loc": 5, "valley_entrance": 61}|
|cleric|battlefield|False|False|hydromancer_elio|1900/2000|95.00%|1926|98.65%|{"dragon_valley_loc": 26, "valley_entrance": 74}|
|cleric|battlefield|False|True|none|1701/2000|85.05%|1847|92.10%|{"dragon_valley_loc": 146, "valley_entrance": 153}|
|cleric|battlefield|False|True|robin|1819/2000|90.95%|1930|94.25%|{"dragon_valley_loc": 111, "valley_entrance": 70}|
|cleric|battlefield|False|True|blue_robed_mage|1799/2000|89.95%|1849|97.30%|{"dragon_valley_loc": 50, "valley_entrance": 151}|
|cleric|battlefield|False|True|fire_bat_dragon|1783/2000|89.15%|1850|96.38%|{"valley_entrance": 150, "dragon_valley_loc": 67}|
|cleric|battlefield|False|True|fire_bat_empowered|1829/2000|91.45%|1851|98.81%|{"valley_entrance": 149, "dragon_valley_loc": 22}|
|cleric|battlefield|False|True|mina|1754/2000|87.70%|1850|94.81%|{"dragon_valley_loc": 96, "valley_entrance": 150}|
|cleric|battlefield|False|True|paladin_liese|1916/2000|95.80%|1946|98.46%|{"dragon_valley_loc": 30, "valley_entrance": 54}|
|cleric|battlefield|False|True|hydromancer_elio|1836/2000|91.80%|1924|95.43%|{"dragon_valley_loc": 88, "valley_entrance": 76}|
|cleric|battlefield|True|False|none|1796/2000|89.80%|1845|97.34%|{"valley_entrance": 151, "dragon_valley_loc": 49, "grave_chapel": 4}|
|cleric|battlefield|True|False|robin|1885/2000|94.25%|1923|98.02%|{"valley_entrance": 77, "dragon_valley_loc": 38}|
|cleric|battlefield|True|False|blue_robed_mage|1838/2000|91.90%|1849|99.41%|{"valley_entrance": 147, "grave_chapel": 4, "dragon_valley_loc": 11}|
|cleric|battlefield|True|False|fire_bat_dragon|1868/2000|93.40%|1883|99.20%|{"valley_entrance": 117, "dragon_valley_loc": 15}|
|cleric|battlefield|True|False|fire_bat_empowered|1879/2000|93.95%|1882|99.84%|{"dragon_valley_loc": 3, "valley_entrance": 118}|
|cleric|battlefield|True|False|mina|1820/2000|91.00%|1856|98.06%|{"dragon_valley_loc": 36, "valley_entrance": 142, "grave_chapel": 2}|
|cleric|battlefield|True|False|paladin_liese|1934/2000|96.70%|1939|99.74%|{"dragon_valley_loc": 5, "valley_entrance": 61}|
|cleric|battlefield|True|False|hydromancer_elio|1901/2000|95.05%|1926|98.70%|{"dragon_valley_loc": 25, "valley_entrance": 74}|
|cleric|battlefield|True|True|none|1707/2000|85.35%|1847|92.42%|{"valley_entrance": 153, "dragon_valley_loc": 140}|
|cleric|battlefield|True|True|robin|1824/2000|91.20%|1930|94.51%|{"dragon_valley_loc": 106, "valley_entrance": 70}|
|cleric|battlefield|True|True|blue_robed_mage|1804/2000|90.20%|1849|97.57%|{"dragon_valley_loc": 45, "valley_entrance": 151}|
|cleric|battlefield|True|True|fire_bat_dragon|1789/2000|89.45%|1850|96.70%|{"valley_entrance": 150, "dragon_valley_loc": 61}|
|cleric|battlefield|True|True|fire_bat_empowered|1833/2000|91.65%|1851|99.03%|{"valley_entrance": 149, "dragon_valley_loc": 18}|
|cleric|battlefield|True|True|mina|1759/2000|87.95%|1850|95.08%|{"dragon_valley_loc": 91, "valley_entrance": 150}|
|cleric|battlefield|True|True|paladin_liese|1916/2000|95.80%|1946|98.46%|{"dragon_valley_loc": 30, "valley_entrance": 54}|
|cleric|battlefield|True|True|hydromancer_elio|1841/2000|92.05%|1924|95.69%|{"valley_entrance": 76, "dragon_valley_loc": 83}|
|cleric|gorge|False|False|none|1499/2000|74.95%|1840|81.47%|{"valley_entrance": 159, "dragon_valley_loc": 341, "gorge_giant_path": 1}|
|cleric|gorge|False|False|robin|1741/2000|87.05%|1938|89.83%|{"dragon_valley_loc": 197, "valley_entrance": 60, "gorge_worm_lair": 2}|
|cleric|gorge|False|False|blue_robed_mage|1693/2000|84.65%|1829|92.56%|{"valley_entrance": 171, "dragon_valley_loc": 136}|
|cleric|gorge|False|False|fire_bat_dragon|1713/2000|85.65%|1845|92.85%|{"dragon_valley_loc": 132, "valley_entrance": 155}|
|cleric|gorge|False|False|fire_bat_empowered|1795/2000|89.75%|1847|97.18%|{"valley_entrance": 153, "dragon_valley_loc": 52}|
|cleric|gorge|False|False|mina|1604/2000|80.20%|1833|87.51%|{"valley_entrance": 165, "dragon_valley_loc": 229, "gorge_worm_lair": 1, "gorge_rockfall_path": 1}|
|cleric|gorge|False|False|paladin_liese|1885/2000|94.25%|1947|96.82%|{"dragon_valley_loc": 62, "valley_entrance": 53}|
|cleric|gorge|False|False|hydromancer_elio|1784/2000|89.20%|1918|93.01%|{"valley_entrance": 82, "dragon_valley_loc": 134}|
|cleric|gorge|True|False|none|1730/2000|86.50%|1838|94.12%|{"dragon_valley_loc": 108, "valley_entrance": 162}|
|cleric|gorge|True|False|robin|1876/2000|93.80%|1939|96.75%|{"dragon_valley_loc": 63, "valley_entrance": 61}|
|cleric|gorge|True|False|blue_robed_mage|1805/2000|90.25%|1833|98.47%|{"valley_entrance": 167, "dragon_valley_loc": 28}|
|cleric|gorge|True|False|fire_bat_dragon|1854/2000|92.70%|1874|98.93%|{"valley_entrance": 126, "dragon_valley_loc": 20}|
|cleric|gorge|True|False|fire_bat_empowered|1871/2000|93.55%|1875|99.79%|{"valley_entrance": 125, "dragon_valley_loc": 4}|
|cleric|gorge|True|False|mina|1788/2000|89.40%|1859|96.18%|{"valley_entrance": 141, "dragon_valley_loc": 71}|
|cleric|gorge|True|False|paladin_liese|1944/2000|97.20%|1955|99.44%|{"valley_entrance": 45, "dragon_valley_loc": 11}|
|cleric|gorge|True|False|hydromancer_elio|1885/2000|94.25%|1924|97.97%|{"valley_entrance": 76, "dragon_valley_loc": 39}|
|mage|village|False|False|none|1409/2000|70.45%|1778|79.25%|{"valley_entrance": 210, "dragon_valley_loc": 369, "village_fire_elemental": 12}|
|mage|village|False|False|blue_robed_mage|1409/2000|70.45%|1778|79.25%|{"valley_entrance": 210, "dragon_valley_loc": 369, "village_fire_elemental": 12}|
|mage|village|False|False|fire_bat_dragon|1510/2000|75.50%|1788|84.45%|{"valley_entrance": 208, "dragon_valley_loc": 278, "village_fire_elemental": 4}|
|mage|battlefield|False|False|none|1780/2000|89.00%|1860|95.70%|{"valley_entrance": 132, "dragon_valley_loc": 80, "grave_chapel": 8}|
|mage|battlefield|False|False|robin|1868/2000|93.40%|1943|96.14%|{"valley_entrance": 57, "dragon_valley_loc": 75}|
|mage|battlefield|False|False|blue_robed_mage|1804/2000|90.20%|1861|96.94%|{"valley_entrance": 131, "dragon_valley_loc": 57, "grave_chapel": 8}|
|mage|battlefield|False|False|fire_bat_dragon|1843/2000|92.15%|1877|98.19%|{"valley_entrance": 123, "dragon_valley_loc": 34}|
|mage|battlefield|False|False|fire_bat_empowered|1858/2000|92.90%|1876|99.04%|{"valley_entrance": 124, "dragon_valley_loc": 18}|
|mage|battlefield|False|False|mina|1814/2000|90.70%|1883|96.34%|{"dragon_valley_loc": 69, "valley_entrance": 110, "grave_chapel": 7}|
|mage|battlefield|False|False|paladin_liese|1889/2000|94.45%|1928|97.98%|{"dragon_valley_loc": 39, "valley_entrance": 71, "grave_chapel": 1}|
|mage|battlefield|False|False|hydromancer_elio|1874/2000|93.70%|1908|98.22%|{"valley_entrance": 91, "dragon_valley_loc": 34, "grave_chapel": 1}|
|mage|battlefield|False|True|none|1531/2000|76.55%|1810|84.59%|{"valley_entrance": 190, "dragon_valley_loc": 279}|
|mage|battlefield|False|True|robin|1660/2000|83.00%|1908|87.00%|{"dragon_valley_loc": 248, "valley_entrance": 92}|
|mage|battlefield|False|True|blue_robed_mage|1655/2000|82.75%|1811|91.39%|{"valley_entrance": 189, "dragon_valley_loc": 156}|
|mage|battlefield|False|True|fire_bat_dragon|1682/2000|84.10%|1794|93.76%|{"valley_entrance": 206, "dragon_valley_loc": 112}|
|mage|battlefield|False|True|fire_bat_empowered|1745/2000|87.25%|1794|97.27%|{"valley_entrance": 206, "dragon_valley_loc": 49}|
|mage|battlefield|False|True|mina|1590/2000|79.50%|1812|87.75%|{"dragon_valley_loc": 222, "valley_entrance": 188}|
|mage|battlefield|False|True|paladin_liese|1741/2000|87.05%|1900|91.63%|{"dragon_valley_loc": 159, "valley_entrance": 100}|
|mage|battlefield|False|True|hydromancer_elio|1720/2000|86.00%|1872|91.88%|{"dragon_valley_loc": 152, "valley_entrance": 128}|
|mage|battlefield|True|False|none|1733/2000|86.65%|1808|95.85%|{"valley_entrance": 184, "dragon_valley_loc": 75, "grave_chapel": 8}|
|mage|battlefield|True|False|robin|1851/2000|92.55%|1929|95.96%|{"valley_entrance": 71, "dragon_valley_loc": 78}|
|mage|battlefield|True|False|blue_robed_mage|1757/2000|87.85%|1810|97.07%|{"valley_entrance": 182, "dragon_valley_loc": 53, "grave_chapel": 8}|
|mage|battlefield|True|False|fire_bat_dragon|1788/2000|89.40%|1823|98.08%|{"valley_entrance": 177, "dragon_valley_loc": 35}|
|mage|battlefield|True|False|fire_bat_empowered|1808/2000|90.40%|1825|99.07%|{"valley_entrance": 175, "dragon_valley_loc": 17}|
|mage|battlefield|True|False|mina|1766/2000|88.30%|1831|96.45%|{"dragon_valley_loc": 65, "valley_entrance": 162, "grave_chapel": 7}|
|mage|battlefield|True|False|paladin_liese|1884/2000|94.20%|1920|98.12%|{"dragon_valley_loc": 36, "valley_entrance": 79, "grave_chapel": 1}|
|mage|battlefield|True|False|hydromancer_elio|1854/2000|92.70%|1892|97.99%|{"dragon_valley_loc": 38, "valley_entrance": 107, "grave_chapel": 1}|
|mage|battlefield|True|True|none|1512/2000|75.60%|1784|84.75%|{"valley_entrance": 216, "dragon_valley_loc": 272}|
|mage|battlefield|True|True|robin|1656/2000|82.80%|1906|86.88%|{"dragon_valley_loc": 250, "valley_entrance": 94}|
|mage|battlefield|True|True|blue_robed_mage|1633/2000|81.65%|1786|91.43%|{"valley_entrance": 214, "dragon_valley_loc": 153}|
|mage|battlefield|True|True|fire_bat_dragon|1667/2000|83.35%|1775|93.92%|{"valley_entrance": 225, "dragon_valley_loc": 108}|
|mage|battlefield|True|True|fire_bat_empowered|1730/2000|86.50%|1775|97.46%|{"valley_entrance": 225, "dragon_valley_loc": 45}|
|mage|battlefield|True|True|mina|1559/2000|77.95%|1786|87.29%|{"dragon_valley_loc": 227, "valley_entrance": 214}|
|mage|battlefield|True|True|paladin_liese|1746/2000|87.30%|1901|91.85%|{"dragon_valley_loc": 155, "valley_entrance": 99}|
|mage|battlefield|True|True|hydromancer_elio|1712/2000|85.60%|1866|91.75%|{"dragon_valley_loc": 154, "valley_entrance": 134}|
|mage|gorge|False|False|none|1540/2000|77.00%|1836|83.88%|{"dragon_valley_loc": 296, "valley_entrance": 154, "gorge_worm_lair": 10}|
|mage|gorge|False|False|robin|1636/2000|81.80%|1893|86.42%|{"valley_entrance": 94, "dragon_valley_loc": 257, "gorge_worm_lair": 13}|
|mage|gorge|False|False|blue_robed_mage|1655/2000|82.75%|1839|89.99%|{"dragon_valley_loc": 184, "valley_entrance": 155, "gorge_worm_lair": 6}|
|mage|gorge|False|False|fire_bat_dragon|1652/2000|82.60%|1814|91.07%|{"valley_entrance": 180, "dragon_valley_loc": 162, "gorge_worm_lair": 6}|
|mage|gorge|False|False|fire_bat_empowered|1724/2000|86.20%|1819|94.78%|{"valley_entrance": 180, "dragon_valley_loc": 95, "gorge_worm_lair": 1}|
|mage|gorge|False|False|mina|1557/2000|77.85%|1828|85.18%|{"valley_entrance": 164, "dragon_valley_loc": 271, "gorge_worm_lair": 8}|
|mage|gorge|False|False|paladin_liese|1722/2000|86.10%|1907|90.30%|{"valley_entrance": 86, "dragon_valley_loc": 185, "gorge_worm_lair": 7}|
|mage|gorge|False|False|hydromancer_elio|1704/2000|85.20%|1895|89.92%|{"valley_entrance": 105, "dragon_valley_loc": 191}|
|mage|gorge|True|False|none|1668/2000|83.40%|1816|91.85%|{"dragon_valley_loc": 148, "valley_entrance": 183, "gorge_worm_lair": 1}|
|mage|gorge|True|False|robin|1747/2000|87.35%|1908|91.56%|{"valley_entrance": 90, "dragon_valley_loc": 161, "gorge_worm_lair": 2}|
|mage|gorge|True|False|blue_robed_mage|1732/2000|86.60%|1818|95.27%|{"valley_entrance": 182, "dragon_valley_loc": 86}|
|mage|gorge|True|False|fire_bat_dragon|1735/2000|86.75%|1812|95.75%|{"dragon_valley_loc": 77, "valley_entrance": 188}|
|mage|gorge|True|False|fire_bat_empowered|1797/2000|89.85%|1815|99.01%|{"valley_entrance": 185, "dragon_valley_loc": 18}|
|mage|gorge|True|False|mina|1689/2000|84.45%|1819|92.85%|{"valley_entrance": 181, "dragon_valley_loc": 130}|
|mage|gorge|True|False|paladin_liese|1847/2000|92.35%|1920|96.20%|{"dragon_valley_loc": 73, "valley_entrance": 80}|
|mage|gorge|True|False|hydromancer_elio|1793/2000|89.65%|1898|94.47%|{"valley_entrance": 102, "dragon_valley_loc": 105}|
|thief|village|False|False|none|1708/2000|85.40%|1931|88.45%|{"dragon_valley_loc": 223, "village_fire_elemental": 35, "valley_entrance": 34}|
|thief|village|False|False|blue_robed_mage|1708/2000|85.40%|1931|88.45%|{"dragon_valley_loc": 223, "village_fire_elemental": 35, "valley_entrance": 34}|
|thief|village|False|False|fire_bat_dragon|1864/2000|93.20%|1953|95.44%|{"dragon_valley_loc": 89, "village_fire_elemental": 24, "valley_entrance": 23}|
|thief|battlefield|False|False|none|1848/2000|92.40%|1967|93.95%|{"dragon_valley_loc": 119, "valley_entrance": 28, "grave_chapel": 5}|
|thief|battlefield|False|False|robin|1942/2000|97.10%|1993|97.44%|{"dragon_valley_loc": 51, "valley_entrance": 7}|
|thief|battlefield|False|False|blue_robed_mage|1914/2000|95.70%|1967|97.31%|{"dragon_valley_loc": 53, "valley_entrance": 28, "grave_chapel": 5}|
|thief|battlefield|False|False|fire_bat_dragon|1937/2000|96.85%|1973|98.18%|{"dragon_valley_loc": 36, "valley_entrance": 27}|
|thief|battlefield|False|False|fire_bat_empowered|1966/2000|98.30%|1973|99.65%|{"valley_entrance": 27, "dragon_valley_loc": 7}|
|thief|battlefield|False|False|mina|1918/2000|95.90%|1972|97.26%|{"dragon_valley_loc": 54, "valley_entrance": 28}|
|thief|battlefield|False|False|paladin_liese|1979/2000|98.95%|1991|99.40%|{"valley_entrance": 9, "dragon_valley_loc": 12}|
|thief|battlefield|False|False|hydromancer_elio|1952/2000|97.60%|1986|98.29%|{"dragon_valley_loc": 34, "valley_entrance": 14}|
|thief|battlefield|False|True|none|1815/2000|90.75%|1973|91.99%|{"dragon_valley_loc": 158, "valley_entrance": 27}|
|thief|battlefield|False|True|robin|1880/2000|94.00%|1991|94.42%|{"dragon_valley_loc": 111, "valley_entrance": 9}|
|thief|battlefield|False|True|blue_robed_mage|1898/2000|94.90%|1973|96.20%|{"dragon_valley_loc": 75, "valley_entrance": 27}|
|thief|battlefield|False|True|fire_bat_dragon|1915/2000|95.75%|1982|96.62%|{"dragon_valley_loc": 67, "valley_entrance": 18}|
|thief|battlefield|False|True|fire_bat_empowered|1954/2000|97.70%|1982|98.59%|{"valley_entrance": 18, "dragon_valley_loc": 28}|
|thief|battlefield|False|True|mina|1880/2000|94.00%|1976|95.14%|{"dragon_valley_loc": 96, "valley_entrance": 24}|
|thief|battlefield|False|True|paladin_liese|1926/2000|96.30%|1990|96.78%|{"dragon_valley_loc": 64, "valley_entrance": 10}|
|thief|battlefield|False|True|hydromancer_elio|1933/2000|96.65%|1989|97.18%|{"dragon_valley_loc": 56, "valley_entrance": 11}|
|thief|battlefield|True|False|none|1888/2000|94.40%|1970|95.84%|{"dragon_valley_loc": 82, "valley_entrance": 29, "grave_chapel": 1}|
|thief|battlefield|True|False|robin|1951/2000|97.55%|1995|97.79%|{"dragon_valley_loc": 44, "valley_entrance": 5}|
|thief|battlefield|True|False|blue_robed_mage|1931/2000|96.55%|1971|97.97%|{"dragon_valley_loc": 40, "valley_entrance": 28, "grave_chapel": 1}|
|thief|battlefield|True|False|fire_bat_dragon|1941/2000|97.05%|1970|98.53%|{"dragon_valley_loc": 29, "valley_entrance": 30}|
|thief|battlefield|True|False|fire_bat_empowered|1963/2000|98.15%|1970|99.64%|{"valley_entrance": 30, "dragon_valley_loc": 7}|
|thief|battlefield|True|False|mina|1932/2000|96.60%|1978|97.67%|{"valley_entrance": 22, "dragon_valley_loc": 46}|
|thief|battlefield|True|False|paladin_liese|1980/2000|99.00%|1991|99.45%|{"valley_entrance": 9, "dragon_valley_loc": 11}|
|thief|battlefield|True|False|hydromancer_elio|1957/2000|97.85%|1986|98.54%|{"dragon_valley_loc": 29, "valley_entrance": 14}|
|thief|battlefield|True|True|none|1827/2000|91.35%|1975|92.51%|{"dragon_valley_loc": 148, "valley_entrance": 25}|
|thief|battlefield|True|True|robin|1881/2000|94.05%|1991|94.48%|{"dragon_valley_loc": 110, "valley_entrance": 9}|
|thief|battlefield|True|True|blue_robed_mage|1907/2000|95.35%|1975|96.56%|{"dragon_valley_loc": 68, "valley_entrance": 25}|
|thief|battlefield|True|True|fire_bat_dragon|1922/2000|96.10%|1982|96.97%|{"dragon_valley_loc": 60, "valley_entrance": 18}|
|thief|battlefield|True|True|fire_bat_empowered|1955/2000|97.75%|1982|98.64%|{"valley_entrance": 18, "dragon_valley_loc": 27}|
|thief|battlefield|True|True|mina|1881/2000|94.05%|1976|95.19%|{"dragon_valley_loc": 95, "valley_entrance": 24}|
|thief|battlefield|True|True|paladin_liese|1926/2000|96.30%|1990|96.78%|{"dragon_valley_loc": 64, "valley_entrance": 10}|
|thief|battlefield|True|True|hydromancer_elio|1933/2000|96.65%|1988|97.23%|{"dragon_valley_loc": 55, "valley_entrance": 12}|
|thief|gorge|False|False|none|1842/2000|92.10%|1972|93.41%|{"dragon_valley_loc": 130, "valley_entrance": 28}|
|thief|gorge|False|False|robin|1879/2000|93.95%|1985|94.66%|{"dragon_valley_loc": 106, "valley_entrance": 15}|
|thief|gorge|False|False|blue_robed_mage|1922/2000|96.10%|1973|97.42%|{"valley_entrance": 26, "dragon_valley_loc": 51, "gorge_rockfall_path": 1}|
|thief|gorge|False|False|fire_bat_dragon|1909/2000|95.45%|1969|96.95%|{"dragon_valley_loc": 60, "valley_entrance": 31}|
|thief|gorge|False|False|fire_bat_empowered|1954/2000|97.70%|1969|99.24%|{"valley_entrance": 31, "dragon_valley_loc": 15}|
|thief|gorge|False|False|mina|1860/2000|93.00%|1967|94.56%|{"dragon_valley_loc": 107, "valley_entrance": 30, "gorge_rockfall_path": 2, "gorge_giant_path": 1}|
|thief|gorge|False|False|paladin_liese|1944/2000|97.20%|1988|97.79%|{"dragon_valley_loc": 44, "valley_entrance": 12}|
|thief|gorge|False|False|hydromancer_elio|1929/2000|96.45%|1989|96.98%|{"dragon_valley_loc": 60, "valley_entrance": 11}|
|thief|gorge|True|False|none|1891/2000|94.55%|1974|95.80%|{"dragon_valley_loc": 83, "valley_entrance": 26}|
|thief|gorge|True|False|robin|1928/2000|96.40%|1984|97.18%|{"dragon_valley_loc": 56, "valley_entrance": 16}|
|thief|gorge|True|False|blue_robed_mage|1941/2000|97.05%|1974|98.33%|{"dragon_valley_loc": 33, "valley_entrance": 26}|
|thief|gorge|True|False|fire_bat_dragon|1944/2000|97.20%|1973|98.53%|{"dragon_valley_loc": 29, "valley_entrance": 27}|
|thief|gorge|True|False|fire_bat_empowered|1967/2000|98.35%|1974|99.65%|{"valley_entrance": 26, "dragon_valley_loc": 7}|
|thief|gorge|True|False|mina|1904/2000|95.20%|1971|96.60%|{"dragon_valley_loc": 67, "valley_entrance": 29}|
|thief|gorge|True|False|paladin_liese|1970/2000|98.50%|1988|99.09%|{"dragon_valley_loc": 18, "valley_entrance": 12}|
|thief|gorge|True|False|hydromancer_elio|1961/2000|98.05%|1989|98.59%|{"dragon_valley_loc": 28, "valley_entrance": 11}|

## 结论与设计待办

- 准备=False，四职业共同最优路线：battlefield；达标=False。
- 准备=True，四职业共同最优路线：无；达标=True。
- 未通过的比较：17项。
- TODO(design): 联合目标未全部达到，停止数值修改并交由设计负责人决定；具体越界见上表与JSON。031古戦場敌人、既有村庄与竜の谷敌人均不在033–035允许调参范围。
- 本轮未改任何剧本数值、叙事或提示词。

### 停止调参原因（评测后分析）

无同行者、无诅咒、未准备时，僧侶的村路线为1474/2000（73.70%），古戦場为1777/2000（88.85%），差15.15pp；魔法使い分别为1409/2000（70.45%）与1780/2000（89.00%），差18.55pp。两者都超过8pp目标。

这两条未准备路线没有使用033–035新增的敌人、DC、同行者、装备或奖励金币。古戦場的敌人与墓守外套属于031；034追加的聖銀材料只留在背包，没有锻造或出售；共同后程也是既有内容。因此仅修改037允许的数值，无法改变这两对比较。没有开展不能消除该阻碍的局部数值搜索。

- TODO(design): 决定如何处理上述固定差距，以及未准备时古戦場在四职业中均为样本最优的问题；是否调整范围、起点或目标属于设计决定。
- TODO(design): 对策同行者共11/24项未达标：古戦場3项（有诅咒的魔法使い未准备、盗賊两种准备状态），峡谷8项。完整提升幅度及最强对照见上表；联合目标的阻碍解决后再决定同行者参数。
- TODO(design): 村路线的ワーロック按既有剧情在入口离队，结果与无同行者相同；若本项原意是全程同行，需要设计明确例外或不同的路线口径。

以上是每组2000次的固定种子样本比较，不能把细小领先直接解释为总体概率严格更高。完整矩阵已结束，408,000条路线全部落在胜／败终态，无步数耗尽或未结算样本。

## 复现

```powershell
python -m scripts.balance.ch3_routes --n 2000 --seed 20261018 --workers 24
```

原始JSON包含前置回放、每种条件的准备交易与起点、各失败地点和胜利的首个完整样本、资源继承、消耗、源文件SHA-256。
