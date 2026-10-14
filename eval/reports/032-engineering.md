# 032 工程完成汇报

日期：2026-10-15。角色：工程负责人。基线：`c27b97f`。按 `docs/specs/032-equipment-slots-and-robin.md` 实现，未调整任务外数值。

## 1. 完成了什么

- 两份剧本同步添加显式 `weapon` / `armor` / `accessory` 部位，覆盖目录、角色初始背包和剧情奖励副本。无部位道具不能装备；原战斗使用和持有即生效行为保留。
- 背包、`equip_on_buy` 和剧情 `equip_item` 共用替换逻辑。同部位旧装备留在背包，装备事件与日文日志只写一次；防御、抗性、技能、消耗、治疗、追击、额外行动及基础攻击只读取当前装备。
- 旧存档按装备列表最后一件保留各部位，补齐旧物品部位并持久化；区域重来快照和战斗原角色副本同样规整。换回杖或书时恢复角色模板的基础攻击，避免残留已卸武器效果。
- 背包名称旁显示「武器 / 防具 / 装飾品」，已有同部位装备时显示「装備する（◯◯と入れ替え）」，复用既有样式。
- 仅鍛冶屋的アダマンタイトの鎧改为60G。开局100G无法同时购买它与50G的氷の護符，两种购买顺序都已验证。
- 执行设计侧 `design_031`，写入ロビン的 `2d4+1` 与 `highest_hp`。最高当前HP、存活筛选、同值取列表最前均已实现；原 `random_target` 保留。旧存档同行者效果和说明同步到已撰写的新数据。
- 修复ロビン开场直接击杀最后敌人时的结算遗漏：无需玩家行动即可兑现奖励与出口，而且只兑现一次。离线试玩中发现此路径，否则会留在砦宝箱战斗地点而没有出口。
- 完成职业路线、最终战、031奖励复核及三项独立机制对照；保留历史报告比较与任务前引擎配对结果。报告如实列出超限项。

## 2. 改动的文件

- 引擎与界面：`host/item_mechanics.py`、`host/state.py`、`host/shops.py`、`host/combat.py`、`host/app.py`、`client/app.js`。
- 剧本与迁移：两份 `host/prompt/processed/dragon_rpg*.json`、`scripts/scenario/equipment_slots.py`、`scripts/scenario/rewards_battlefield.py`。`scripts/scenario/design_031.py` 仅执行，未修改设计侧内容。
- 平衡：`scripts/balance/sim.py`、`slots.py`、`slots_report.py`、`eval/balance/checkpoints.json`；[平衡报告](balance-2026-10-15-slots.md) 和八份 `slots-*.json`。
- 测试：新增 `tests/test_equipment_slots.py`；更新 `tests/test_combat.py`、`test_state.py`、`test_prism_claim_guard.py` 中的显式部位与价格预期。
- 验收产物：`scripts/screenshot_equipment.py` / `.mjs`、[试玩报告](032-playtest.md)、对应JSON和八份逐步记录、`screens/032/` 的两张截图及 `checks.json`、本报告。

没有新增依赖。截图沿用项目已有的本地HTTP、已安装Chromium与Node方式；模拟使用Python标准库进程池。没有修改提示词默认措辞、benchmark标准答案或设计文档。

## 3. 验证结果（命令和输出摘要）

|命令|结果|
|---|---|
|`python -m scripts.scenario.design_031`|两份剧本更新成功，ロビン数据与设计源一致|
|`python -m scripts.scenario.equipment_slots`|两份剧本更新成功；单元测试检查幂等、部位与60G|
|`python -m scripts.balance.checkpoints`|刷新现行检查点，与当前剧本及装备机制一致|
|`python -m unittest tests.test_equipment_slots -q`|10项通过，退出码0|
|`python -m unittest discover -s tests -q`|最终版本552项，181.961秒，`OK (skipped=1)`，退出码0|
|`node --check client/app.js`|通过，退出码0|
|`node --check scripts/screenshot_equipment.mjs`|通过，退出码0|
|`python -X utf8 -m scripts.playtest.explore --output eval/reports/032-playtest.md`|4职业×2种子，异常、非战斗死路及兜底叙述不变量0项；7/8局走过古戦場并经礼拝堂到村后门，退出码0|
|`python -X utf8 -m scripts.screenshot_equipment`|10项浏览器检查通过，实际点击换装；两张截图已目视检查，退出码0|
|`python -m scripts.balance.slots_report`|生成要求的三项影响分列报告|
|`git diff --check`|通过；Git仅提示已有autocrlf换行转换|

新增测试覆盖三部位替换、全部实际自动装备商店、各部位剧情装备、卸下后的全部相关效果、无部位道具、旧存档持久化与快照、60G预算、ロビン目标选择及开场胜利只结算一次。测试和模拟没有调用真实模型或付费API；浏览器验收仅使用回环地址。

平衡运行命令如下；每套新旧引擎都已实际运行并成功退出。职业路线N=500，其他每条件N=2000，seed=20261012。旧引擎从 `c27b97f` 提取到忽略目录，既不改当前工作树，也不改历史报告。

```powershell
python -m scripts.balance.slots_report --prepare-baseline
python -X utf8 -m scripts.balance.slots --suite routes --workers 6 --output eval/reports/slots-routes.json
python -X utf8 -m scripts.balance.slots --suite finals --workers 4 --output eval/reports/slots-finals.json
python -X utf8 -m scripts.balance.slots --suite rewards --workers 4 --output eval/reports/slots-rewards.json
python -X utf8 -m scripts.balance.slots --suite controls --workers 4 --output eval/reports/slots-controls.json
```

旧引擎工作目录为 `.tmp-test/032-baseline`，四套同样运行并加 `--legacy`，输出到主仓库的 `slots-<suite>-baseline.json`；workers依次6、4、4、2。并行度不影响固定种子的结果。

截图：[部位标签与三个替换按钮](screens/032/inventory-slots.png)、[替换后的装备与日文日志](screens/032/inventory-after-swap.png)、[检查记录](screens/032/checks.json)。

## 4. TODO(design) 清单

- TODO(design): 审阅僧侶固定职业路线。class_aware通关率由上一报告53.60%降到25.60%（−28.00pp；相对任务前引擎复跑−27.40pp），距55%下限29.40pp。其他四种僧侶策略下降27.00–31.00pp。新规则下杖占据武器部位，既有策略取得イアン赠剑后没有主动换装；工程未改策略或数值来补齐。
- TODO(design): 主线四职业差距36.60pp，超20pp目标16.60pp；盗賊51.40%，低于55%下限3.60pp，也列出供审阅。
- TODO(design): 031魔法使い全探索最终战胜率93.85%，奖励配对提升20.15pp，相对原历史基准提升20.25pp；原上限15pp，最大超限5.25pp。此既有问题仍未消失。
- TODO(design): ロビン独立机制对照中，盗賊的砦第四战77.75%→83.20%，增加5.45pp。它是历史变化审阅项，没有另行发明目标。

最终战现行目标检查无违规；王国支援和ロビン支援旗标平均贡献分别4.97pp、7.13pp。该旗标与同行者援護射撃是不同机制。

## 5. 推断清单

1. 保留原引擎在武器部位空缺时从背包寻找显式weapon部位且`kind: weapon`物品的兜底；部位已有杖或书时不再自动挤入另一件武器。普通获得道具不等于换装，明确的`equip_item`、商店自动装备或背包操作才替换。
2. 剣融合原先依赖移除旧武器后的隐式兜底，故给`accept_sword_fusion`补显式`equip_item`，使它进入相同剧情装备流程；不改叙事正文或物品数值。
3. 杖/书没有独立的`kind: weapon`攻击定义；换回它们时恢复当前职业模板原有基础攻击。新增保存`base_attack`，旧存档从模板补齐，没有设计新的徒手攻击数值。
4. 旧列表按现有顺序“最后一个”判定，兼容名称和ID；无部位、无所有权或数量不足的条目不保留。背包数量不变，不给读档规整虚构主动换装日志。
5. 区域重来和战斗原角色副本也可能携带旧叠装，因此与当前角色一同规整，避免恢复后回到旧规则；规整结果保存，重复读档幂等。
6. 全部装备效果统一使用显式部位过滤。无部位且未要求装备的被动道具仍按持有效果处理；非法部位值不构成第四个部位。
7. 目标配置并存时沿用现有`all_targets`、`random_target`优先级，只有未启用它们时处理`highest_hp`；同HP利用原敌人列表稳定顺序。
8. 同行者读档刷新时复用最新剧本已撰写的说明文字，使旧ロビン存档的显示与效果一致，没有另写叙事措辞。
9. “现行报告”取仓库中最后的职业路线、support3最终战和031 regional-plus3奖励报告。既比较历史值，也用任务前精确提交复跑，区分历史差与本次机制差。
10. 031奖励复核保持历史冻结的奖励、装备、属性及支援条件，只补当前目录的部位元数据并执行规整。它与032重新走路线形成的装备准备可能不同，报告明确区分；不把全探索条件上界当连续生存率。
11. 现行固定路线/最终战准备不购买鎧、也不携带ロビン，故补实际商店预算、减伤和同行射击控制组。没有自行制定新的玩家购买策略或以之推导全程胜率。
12. 截图用真实100G开局购买鎧，额外放入演示武器及饰品以同时展示三个替换按钮；换装经过真实引擎。该演示背包不用于平衡模拟。
13. ロビン开场胜利也必须兑现既有战斗奖励与出口；把待应用delta的消费补到统一结算入口，并用重复请求测试保证只执行一次。

## 6. 偏离 spec 的地方及原因

无功能要求省略，无未经授权的数值改动。为满足032验收，补了两处关联行为：剣融合改为显式装备入口；ロビン开场击杀时统一兑现战斗结果。前者用于覆盖全部装备入口，后者用于消除本次离线试玩暴露的非战斗死路。

除指定的三类平衡复核，新增精确旧引擎重放与三项机制控制，便于分开解释原因。新试玩产物的标题日期改成032验收日，固定种子仍沿用原脚本；未改旧报告或其生成脚本。

## 7. 已知问题

- 第4节平衡偏离待设计决定，不能把测试通过表述成平衡目标全部达成；工程未自行调参。
- 试玩8局有2局达到150步上限；存在正常战斗/剧情失败结局。零不变量违规不表示每局通关或证明不存在所有路径问题。
- 固定启发式策略不会主动搜索最优换装和购买方案。价格机会成本只验证实际预算约束，不能由现有未购鎧策略直接估算人类选择后的胜率。
- 模拟JSON保留结果落盘时的指纹；后续补丁涉及旧存档读取、同行者说明同步及仅供旧引擎使用的`--legacy`开关，不改变这些模拟的战斗调用路径和采样策略。没有事后替换指纹来伪装全文件相同。
- Windows沙箱限制临时目录、进程池和无头浏览器，因此验证在获准的提升权限进程中完成。一次PowerShell重定向曾将unittest的stderr误计为外层失败；最终完整测试直接执行，已确认真实退出码0。
