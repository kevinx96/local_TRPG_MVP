# 030 工程汇报（UTF-8 重建）

本文件按031第5节重新生成。原文件中的中文已被替换为问号，无法恢复原字节；以下依据030的提交、任务说明和已保存的机器产物重建，不冒充原文逐字恢复。历史验证结果与031本次验证分开记录。

## 1. 完成了什么

展开父选项时立即切换NPC立绘，收起或返回时恢复；同一NPC的子选项继承父级立绘。两份剧本补齐宿屋的イアン昔话、ロビン被盗物以及村中长老盟约对话，共3处，无立绘例外。

目的地风险由访问历史控制：第1章城下町以外，未访问目的地显示「不明」；当前动作判定和可见敌人的战斗保留真实标签。每份剧本分类为96个目的地风险、104个动作风险。逐项分类见[030-data.json](030-data.json)。

统一7个地点的enemy_ids，按combat.enemy_ids修正描述侧名单，未修改战斗敌人：

|地点|修正前数量|修正后数量|
|---|---:|---:|
|forest_wolves|2|1|
|slime_ambush_one|3|1|
|slime_ambush_two|3|1|
|goblin_fort_first_second|3|2|
|goblin_fort_second_left|5|1|
|goblin_fort_third_guards|3|1|
|goblin_fort_fourth|3|2|

战斗事件由引擎输出目标、伤害/回复、属性、击倒和阶段切换信息；前端按事件播放CSS/Web Animations，并同步日志、HP/MP条和无障碍播报。支持点击或空格跳过以及reduced-motion。事件序号避免80行日志截断丢失本次动画。

## 2. 改动的文件

030提交：`fb1c6ef`（[工程] 完成030立绘切换、未知风险与战斗事件动画）。

- 前端：`client/app.js`、`client/battle-fx.js`、`client/styles.css`、`client/index.html`。
- 引擎：`host/combat.py`、`host/state.py`；两份processed剧本。
- 数据脚本：`scripts/scenario/risk_labels.py`、`scripts/scenario/portraits_risk_fx.py`。
- 测试：`tests/test_scenario_invariants.py`、`tests/test_combat_events.py`。
- 截图：`scripts/screenshot_battle_fx.py`、`scripts/screenshot_battle_fx.mjs`。
- 产物：`eval/balance/checkpoints.json`、`eval/reports/030-data.json`、`030-playtest.*`、`030-playtest/`、`screens/030/`。

没有新增运行时依赖。截图使用现有Chromium、Node WebSocket及Pillow；Pillow用于拼图/GIF，PNG帧仍是浏览器截图。

## 3. 验证结果

以下为030保存的历史记录，本次重建未重新执行030截图和试玩：

- `python -m unittest discover -s tests -q`：原报告可辨认记录为527 tests、232.176s、OK（skipped=1）；这是历史报告记录，未保留独立终端输出。跳过的是需显式开启BALANCE_ENFORCE的平衡门槛。
- `node --check client/app.js`：原报告记录退出码0；另记录battle-fx.js语法检查通过。
- `python -m scripts.playtest.explore --output eval/reports/030-playtest.md`：[8局结果](030-playtest.md)，不变量0项。2局达到步数上限、1局竜の谷战败、3局净化、2局讨伐；未证明全部路线可通关。
- `python -X utf8 -m scripts.screenshot_battle_fx`：[checks.json](screens/030/checks.json)中98项检查通过，errors为空；覆盖动画结束状态与直接渲染状态的一致性、可读按钮、实时播报、跳过动画和reduced-motion。
- [关键帧](screens/030/normal.png)等13张对比图；[见张り戦GIF](screens/030/goblin-fort.gif)约9.85秒、81帧。帧数及时间来自原报告可辨认记录，文件本身仍在仓库。

## 4. TODO(design) 清单

030当时记录的暴击规则、青色及额外属性颜色已由后续设计提交`4e72c60`处理：无暴击机制是设计决定，青色/土色变量与全部属性命中特效颜色已定稿。重建报告不重新打开这些设计项。

## 5. 推断清单

- 风险按location_id访问历史判断；capital地图作为第1章城下町的豁免。
- 有roll/free_action的动作以及休息遭袭、背叛、拒绝、告发、净化等明确引发事件的动作归为动作风险。详尽名单见数据报告与risk_labels.py。
- 混合分支若有未访问目的地则显示「不明」；已击败目的地全部敌人后可显示「判定不要」。
- 日志播放采用结构化事件的真实目标ID，不从叙述文字推算目标。
- 动画预算按整次行动限制在1.4秒内；截图检查允许50ms浏览器调度误差。伤害数字700ms、HP条400ms、延迟条再延后300ms。
- 暴击关键帧使用合成事件验证展示，不代表引擎存在随机暴击。其余截图也包含为复现单类动画而构造的状态，不能代替真实战斗平衡测试。
- 风险标签只改变展示；效果结算仍由引擎执行。
- 中文已损坏的原汇报不能逐字恢复。本文件以可复核数据和代码重建，未推测无法证明的历史操作。

## 6. 偏离 spec 的地方及原因

030没有增加游戏位图素材，也没有修改提示词和战斗数值。战斗时缺少的设计规则及颜色在030曾留TODO，后续设计提交已解决。重建只修复报告，不重复进行030功能开发。

## 7. 已知问题

自动截图中的合成事件仅验证表现；8局离线探索不能覆盖全部剧情路径。原报告编码损坏使部分历史说明无法恢复，无法证明的内容未补写成事实。
