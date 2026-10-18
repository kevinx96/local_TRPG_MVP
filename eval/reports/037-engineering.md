# 037 工程汇报（第三轮）

## 1. 完成了什么

已落实设计指定参数，并完成全部204组×N=2000离线重跑。核心严格领先通过5/8项，门槛通过=False；准备／诅咒组仅报告，严格领先10/16项。未继续调参。

- 两份剧本同步リーゼ回复20%、聖光の一撃2d6；エリオ水刃2d6、水の帳每4回合。说明、6种招募action和对应6种fallback choice的preview同步；内容版本升为2026-10-18-v037-r3。
- 联合矩阵共408,000条连续路线：364,289胜、43,711败，全部正常结算。第一、二轮完整报告与JSON保留，并在[第三轮联合报告](balance-2026-10-18-ch3-routes.md)逐组对照。
- 未准备、无同行者、无诅咒的魔法使い三路线差距仍为9.95pp（村70.45%、古戦場80.40%、峡谷77.00%）。按设计决定明确记录：来自村路线本身，属于旧内容，本轮不改。
- 路线外复核35场×4职业×8同行条件×N=1000，共1,120,000场；两人各128项上限比较，合计13/256项超出现有最强+3pp，逐项见下表及[完整报告](037-companion-outside.md)。
- 当前剧本重跑32局试玩，16局通关，21局重来一次，最多206步；路线到访={'village': 12, 'battlefield': 10, 'gorge': 7}。异常、非战斗死路、兜底叙述均0。路线、同行者、线索flag、首次死亡、重来、结局与Jaccard见[汇总](playtest-2026-10-18-ch3/summary.md)、[JSON](playtest-2026-10-18-ch3/summary.json)及32份日志。
- 通关局120对：选择Jaccard均值／最小／最大为0.3592／0.1549／0.6000；地点为0.5474／0.2969／0.9737。
- 线索覆盖13/14种；未取得flag：has_assassin_crest。未到地点：merchant_battle, alley_after, xanxus_phantom_battle, inn_night_ambush。
- 手机布局沿用既有实现，重新通过41项浏览器验收并查看375×812的[普通战斗](screens/037/normal.png)、[ドラコ战](screens/037/draco.png)、[展开日志](screens/037/log-expanded.png)。

|职业|路线|对策提升pp|其他最强|其提升pp|领先pp|核心严格领先|
|---|---|---:|---|---:|---:|---|
|hero|battlefield|+10.65|hydromancer_elio|+9.35|+1.30|True|
|cleric|battlefield|+21.75|hydromancer_elio|+20.10|+1.65|True|
|mage|battlefield|+11.45|fire_bat_empowered|+10.75|+0.70|True|
|thief|battlefield|+8.75|hydromancer_elio|+9.05|-0.30|False|
|hero|gorge|+10.20|paladin_liese|+10.20|+0.00|False|
|cleric|gorge|+18.50|paladin_liese|+18.35|+0.15|True|
|mage|gorge|+10.90|fire_bat_empowered|+9.20|+1.70|True|
|thief|gorge|+5.40|fire_bat_empowered|+5.60|-0.20|False|

|同行者|职业|路线外遭遇|本轮胜率|现有最强|对照胜率|超出pp|
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

paladin_liese：越界7/128项，最大超出+9.50pp（mage/valley_ledge）。

hydromancer_elio：越界6/128项，最大超出+4.20pp（thief/draco_battle）。

## 2. 改动的文件

- `host/prompt/processed/dragon_rpg.json`、`dragon_rpg_hybrid.json`：指定参数、说明、招募预览与内容版本。
- `scripts/scenario/oaksdawn.py`、`rumbling_gorge.py`、`ch3_routes_balance.py`：生成及迁移脚本与两份剧本一致。
- `scripts/balance/ch3_routes.py`、`ch3_outside.py`：核心门槛、准备／诅咒仅报告、三轮对照和路线外结果说明。
- `tests/test_ch3_routes.py`、`test_oaksdawn.py`：核心8项覆盖／失败／缺项检查，治疗数值断言同步。
- `eval/balance/checkpoints.json`：仅剧本SHA-256变化。
- `eval/reports/balance-2026-10-18-ch3-routes*.{md,json}`、`037-companion-outside*.{md,json}`、`037-engineering*.md`、`037-round3-checks.json`：第三轮结果、第二轮归档及审计。
- `eval/reports/playtest-2026-10-18-ch3/`：当前32局日志与汇总，第二轮汇总归档；`eval/reports/screens/037/draco.png`：重新截图。其他两张截图和41项检查记录内容未变。

没有新增依赖。保留用户原有四份未跟踪006本地对照报告。

## 3. 验证结果（命令和输出摘要）

|命令／检查|结果|
|---|---|
|`python -m unittest discover -s tests -q`|615项，693.441秒，`OK (skipped=1)`；跳过既有BALANCE_ENFORCE可选检查|
|`node --check client/app.js`|退出码0|
|`python -m unittest tests.test_ch3_routes tests.test_oaksdawn tests.test_rumbling_gorge -q`|43项，2.582秒，OK|
|`python -X utf8 -m scripts.balance.ch3_routes --n 2000 --seed 20261018 --workers 16`|首次保存136组后写文件失败；同种子补跑68组并合并，最终204组、408,000条路线，无异常终态|
|`python -X utf8 -m scripts.balance.ch3_outside --n 1000 --seed 20261018 --workers 8`|1120组、1,120,000场；非终态0|
|`python -X utf8 -m scripts.playtest.explore --workers 2`|32局，最多250步，不变量全0|
|`python -X utf8 -m scripts.screenshot_mobile_battle`|`41 browser checks passed`；三图已查看|
|`git diff --check`、产物审计|通过；[审计记录](037-round3-checks.json)核对完整矩阵、统计、指纹、三轮对照、UTF-8无BOM和截图尺寸|

离线多进程首次受Windows沙箱本地管道权限限制，Chromium首次未能暴露本地调试端口；在允许本地管道／临时目录／无头浏览器的执行权限下重跑。主矩阵随后遇到与第二轮相同的Windows OSError errno22报告写入错误；实际完整保存136组，控制台打印了137组，按JSON条件数恢复。验证所有源文件指纹、起点检查点一致后，使用原ch3_routes._job、相同N和seed、24 workers补跑缺失68组，逐组追加保存并最终合并204组。恢复元数据保留在联合JSON的run_recovery；没有付费API调用。

## 4. TODO(design) 清单

- 核心thief/battlefield未严格领先hydromancer_elio，领先幅度-0.30pp。按指示如实报告，不继续调参。
- 核心hero/gorge未严格领先paladin_liese，领先幅度+0.00pp。按指示如实报告，不继续调参。
- 核心thief/gorge未严格领先fire_bat_empowered，领先幅度-0.20pp。按指示如实报告，不继续调参。
- 路线外上限有13项越界，具体同行者／职业／遭遇见上表；保留指定参数，交设计后续决定。
- 村路线导致的未准备法师9.95pp差距按第三轮决定归为旧内容，本轮不改；其余三路线≤8pp越界保留在联合报告，未额外调整。准备／诅咒同行者比较不再列为本轮门槛。

## 5. 推断清单

1. 沿用前两轮Lv3、240G森出口可达检查点，seed=20261018、51条件／职业、相同休息／行动／消耗策略。前置战斗按检查点回放假定获胜；正式连续路线真实结算至イグニス胜／败，分母包含提前死亡。准备实际花费195G。
2. 核心8项严格领先使用样本点估计，比较所有同行条件（含另一条路线的对策同行者与强化火コウモリ竜）；并列失败，不加统计容差。准备组／诅咒组仍计算相同指标，仅移出门槛。
3. 路线外“重跑”沿用第二轮N=1000、seed=20261018及033／035的逐战满资源检查点和既有对照集合。リーゼ不借后加入的エリオ抬高上限；エリオ对照包含本轮リーゼ。N=2000明确用于204组连续路线。
4. 招募preview沿用现有句式补入设计给定的20%、2d6与4回合信息，同时同步actions与fallback choices；不改招募条件和叙事。
5. 指定参数会影响试玩，因此重跑32局；手机布局无实现变更，仅复跑现有截图与浏览器验收。第二轮逐局日志可从ca7fa8c取回，当前同名日志为第三轮；第一、二轮汇总分别归档。
6. 第一、二轮历史报告原文保留，第三轮联合报告逐组列出两轮通关率及较第二轮变化。报告中的路线外摘要直接取本轮独立逐战JSON，并保存其SHA-256。

## 6. 偏离 spec 的地方及原因

- 按用户第三轮设计决定，将原24项“本路线最强”改为核心8项严格领先；准备组和诅咒组只报告。严格不等式沿用第二轮决定。
- 原始三路线≤8pp目标仍有未达项，村路线旧内容差距按设计明确不改；核心失败和路线外越界均如实保留，不扩大调参范围。
- 没有其他范围偏离；默认提示词、benchmark标准答案、旧敌人、旧路线奖励和其他同行者参数均未改。

## 7. 已知问题

- N=300筛选与N=2000验收共享种子序列，样本扩大可能改变领先关系。所有结论都是固定策略和检查点下的点估计，不等于总体胜率或从新游戏开始的通关率。
- 路线外结果来自每场独立满资源检查，不等于连续路线胜率；不能用其数值替代核心门槛。
- 保留旧行为：村路线ワーロック在森林出口按剧情离队，故该组与无同行者相同；模拟拾取外套时保留已穿防具；诅咒短剑在空武器位自动装备。
- 试玩路线轮换用于覆盖，不能视作无偏玩家分布；原有重复进入已清理village_fire_elemental的边界问题不属于本轮修改范围。
