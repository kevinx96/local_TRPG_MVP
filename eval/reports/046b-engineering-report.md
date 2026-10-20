# 046b 工程汇报

1. **完成了什么**

已完成 046 第二部分：七种原型 × 四职业、完整 M1–M13 接口、准备消融、全部 11 个 Boss × 同伴矩阵、四种策略回合探针、等级 ±1 数值探针、targets v2、真实存档遥测。全部离线，无新增依赖、无 LLM/付费 API 调用。

采用开工版本 `b1b21eda9f24df6b003ee65342478e500b7eb6a4` 的引擎和剧本快照，叠加本任务测量代码。047 正在共享目录修改 host/、剧本和前端，未将这些改动混进基线或补丁。

主口径为 `game_over.title == 冒険完了`；Ignis 击败/净化、终局另报。046b 已接受 Ignis 复现，P0b >90% 不再作为复现门槛。草案数值门槛继续报告，未为了通过目标而调整游戏。

每格 N=500，seed=20261020：

| 原型 | 勇者 | 僧侶 | 魔法使い | 盗賊 |
|---|---:|---:|---:|---:|
| P0a | 0.0% | 3.2% | 0.8% | 0.0% |
| P0b | 50.2% | 58.0% | 14.0% | 33.2% |
| P1 | 52.0% | 58.6% | 26.6% | 45.8% |
| P2 | 16.8% | 17.0% | 2.6% | 12.6% |
| P3 | 2.0% | 9.6% | 0.0% | 0.2% |
| P2s | 20.0% | 18.2% | 2.6% | 13.6% |
| P0g | 50.2% | 58.0% | 14.0% | 33.2% |

P0b 勇者从上一轮的42.4%变为50.2%，原因是按046b决定改成免费休息且HP<70%，不再首次到泉固定休息三次。P0g 与P0b完全相同：现引擎没有能保留收益的重复战斗，也没有战斗EXP；没有清除 defeated flags 伪造刷级。每级资源成本为 not_applicable（待050/051）。

P2/P3 的胜率显著低于草案。这里测的是明确列出的支线与顺序提案，不代表最优准备路线。P2 勇者的主要瓶颈为ゴブリン王战（Lv1进入砦）；没有通过重排路线或强制借同伴成功来抬高结果。P2s 最终只更改 avoid_battles，其余参数与P2相同；四职业通关差依次为3.2、1.2、0、1.0pp，各共同节点等级差均为0，满足≤10pp/≤1。

| 指标 | 状态 | 硬门槛 |
|---|---|---|
| M1 | fail | True |
| M1' | report | False |
| M2 | report | False |
| M3 | fail | True |
| M3' | report | False |
| M4 | fail | True |
| M5 | report | False |
| M6 | report | False |
| M7 | report | False |
| M8 | report | False |
| M9 | fail | True |
| M10 | report | False |
| M11 | report | False |
| M12 | not_applicable | False |
| M13 | report | False |

M1/M3/M4/M9 均未达到草案目标。其他指标的 report 不代表通过；逐配置数值、目标和是否满足条件均保留在基线JSON。M12 为待050/051占位；M13 提供固定技能/装备的数值成长探针，EXP到达等级差验收仍待050/051。

试玩配置已用找回存档校对：Ignis前流水重建为Lv5、STR20、鉄の剣、革の鎧、紅玉の護符、氷の護符和强化火コウモリ竜；薬草×7、治療の巻物×8；金币601G。通关库存才是×7/×9和706G。四种霊薬为剛力、鉄壁、叡智、迅速。アダマンタイトの鎧在Ignis战后才装备，氷鉄の大剣拿到但未装备。满资源配置探针不是开战直接快照。

| 独立配置 | 胜率 | 回合中位数 | S |
|---|---:|---:|---:|
| human_berserker | 95.6% | 19 | 1.2464 |
| P0b + 氷鉄の大剣 | 98.8% | 10 | 1.2464 |
| 无同伴 | 63.4% | 20 | 0.0000 |

Ignis复现仍为95.6%、19回合、S=1.2464；与第一部分一致。威胁表17项有15项在容差内；ゼボク、ドラコ分别因1/6权重的亡霊転換、護衛の構え产生零伤害回合。按实际AI全分布计算为15.33%/CV1.0136及15.19%/CV0.6670；只条件化于攻击回合时与原文18%/0.83、18%/0.45吻合。后者是对原文算法的推断，没有静默删掉零伤害回合。

准备清单均为 proposed，等设计审定；每项独立移除，保留其余配置和金币，成对使用同seed：

| 准备 | 移除方式 |
|---|---|
| 紅玉の護符 | 移除库存与配装 |
| アダマンタイトの鎧 | 移除并恢复革の鎧 |
| 聖水净化路线 | 清净化资格旗标、聖水和白い竜鱗，含僧侶的MP替代路径 |
| 氷鉄の大剣 | 移除并恢复鉄の剣 |
| 火コウモリ竜 | 清除同伴 |
| 火コウモリ竜强化 | 只去掉fire_bat_empowered，保留普通同伴 |

勇者全准备胜率100%；移除上述各项的边际依次为0.8、1.0、0.2、0、1.4、1.0pp，均未达到关键准备≥10pp的草案目标。其他职业数据见JSON；未替设计挑选新的关键项或调整门槛。

P2支线：ガルド、リク、完整洞窟、ゴブリン砦、净化线索。P3再加城镇交付、ミーナ、旧戦場、オークスドーン、峡谷、将军屋敷、商人、ロビン、サラ、三组物资交付、火種の呪い；选择一条可连通的分支（火种接受后净化、商人背叛），不强制互斥分支同时成立。商店按可负担程度，每个店的每个商品最多买1次；未把无限库存当作无限购买。具体动作、失败和未满足条件均能从样本和参数表检查。

找回存档实际有：event_log 240、system_logs 222、messages 155、dice_log 14、last_combat_result，以及8个区域回退快照。完整根字段清单先列在遥测报告。可观察17场战斗结算，其中4场早期结算仅有系统文本，缺回合数；9场文档时间线可对应，炎のウィスプ实在cave_lava_room而非原文cave_crystal_corridor。三次休息均在elf_spring，分别在连战之前、连战之后、虹晶樹之后。判定10/14成功。

金币流水合并去重后为收入806G、支出100G（购买80G、加工20G）、结余706G；最终回复库存340HP，非原文270HP。回复道具完整使用次数无法从截断历史证明，输出null，没有沿用“一个都没用”的无证据结论。装备变更可观察2次。按支线行为最接近P2，属于待审分类，不等同于P0b策略，也没有用这局胜利替换原型通关率。

2. **改动的文件**

- `scripts/balance/archetypes.py`：参数表、侧任务合法性、HP70规则、P2s仅绕战。
- `scripts/balance/route_v2.py`：七原型路线、支线钩子、逐节点等级、成对crucial分支探针、资源和战斗记录；复用Run与确定性战斗引擎。
- `scripts/balance/sim.py`：显式可选回复阈值；默认heuristic仍35%、best_free仍30%，旧输出不变。
- `scripts/balance/metrics_v2.py`：统一试验包的15个归约器（含M1'/M3'），区分硬门槛和报告。
- `scripts/balance/probes_v2.py`：准备、同伴、策略、等级探针，复用economy的区域checkpoint覆盖旧表外Boss。
- `scripts/balance/measurement_v2.py`：完整离线批次、输出、输入指纹及运行中变动检测。
- `scripts/playtest/save_telemetry.py`：存档、可选trace/完成日志，合并去重、来源标记、未知值和记录缺口。
- `eval/balance/{targets.json,preparations.json,checkpoints_berserker.json}`：新增v2目标而保留全部旧键和值，准备提案，真实存档校对配置。
- `eval/reports/046-measurement-v2-baseline.{json,md}`、`046b-save-telemetry.{json,md}`、本报告。
- `tests/test_measurement_v2.py`：三处必要同步：休息策略、已开放全部原型、旧并行测试仍只采P0a/P0b。
- 新测试实际位于 `.tmp-test/046b/tests/test_measurement_v2b.py`，目标为 `tests/test_measurement_v2b.py`；新增24项。`tests.patch`及完整补丁均包含目标文件。

没有修改047的host/、剧本、scripts/scenario/或client/文件；没有修改既有默认提示词、标准答案或游戏数值。没有新增依赖。

3. **验证结果**

- 隔离快照：显式沿用第一部分的临时目录兼容启动层后，`python -m unittest discover -s tests -q`：**792 tests / 316.147s，OK (skipped=1)**，包括新增24项。
- 最新测量代码专项：`python -X utf8 -m unittest discover -s tests -p test_measurement_v2*.py -q`：**38 tests / 2.657s，OK**。覆盖全部指标边界、真实及合成存档、阈值、参数等价、准备移除、trace会话匹配、旧目标哈希、旧命令输出。
- `node --check client/app.js`：共享目录、隔离快照都退出0。
- 开工前重新保存旧命令输出，与第一轮固定样本相同；新旧sim --check、route hp70、class_aware backbone同seed逐字一致（只把计时固定0）。旧sim --check本就退出1，也校验该退出码。串行/多进程逐字一致。
- 完整批次：`python -X utf8 -m scripts.balance.measurement_v2 --n 500 --probe-n 500 --workers 12 --records-output ...`：退出0。28格路线，24格准备、308格同伴、60格等级边际、176格策略。
- 门槛CLI小样本：`python -X utf8 -m scripts.balance.measurement_v2 --n 1 --probe-n 1 --workers 4 --check --output ...`：退出1，JSON为measurement_complete且硬门槛失败，符合契约；没有把数值不达标当程序异常。
- 共享目录原命令：768 tests / 549.628s，1 failure、skipped=1。唯一差异经递归比较确认为 `/scenario_sha256`，源于047改写剧本指纹；其他checkpoint数据完全相同。未改旧checkpoint或测试断言来掩盖该问题。
- 首次隔离测试因归档不含忽略的`.tmp-test/`父目录，26个测试setUp报FileNotFoundError；补建测试要求的父目录后，完整792项通过。

兼容层仅显式启用，不改变产品或断言：

```powershell
$env:TRPG_TEST_TEMP_INHERIT = '1'
$env:PYTHONPATH = '<隔离快照>/scripts/balance/test_environment' + [System.IO.Path]::PathSeparator + $env:PYTHONPATH
$env:PYTHONIOENCODING = 'utf-8'
python -m unittest discover -s tests -q
node --check client/app.js
```

完整主批次墙钟 **1286.67秒（约21.4分钟）**，workers=12；路线463.80秒、准备35.31秒、同伴329.36秒、等级106.88秒、策略196.01秒、初次试玩配置148.57秒。P2s定稿补跑185.80秒，战前库存校对后3个配置并行复核61.51秒。补充批次与主批次有重叠，不相加当墙钟。机器报告28逻辑处理器，单元测试也在同时运行，因此只是重跑成本量级。

4. **TODO(design) 清单**

- 审定P2/P3侧任务集合、进入顺序、P3的每店每品1件购买规则和互斥支线选择。当前全部是提案，特别是Lv1进砦带来的决策梯度倒挂。
- 审定六项准备的关键/非关键标记，补充需要检查≤25pp上限的非关键准备清单。现有起步清单全部标为关键。
- 审定M3'静态赛跑比是否把剩余MP/SP可换得的治疗计入资源池。当前保守按HP+库存回复计算；真实技能使用仍影响实际击杀回合。
- 终局的“任一结局”当前按任何ending字段，包含失败结局；设计若只要剧情终局，应另明确列表。主通关率始终只算冒険完了。
- 审阅真实存档与文档的差异（100G支出、340HP库存、战前8卷轴、较早战斗缺失）和“最接近P2”的行为分类。

上一轮的休息时点、P0b与试玩配置分离、CV全分布口径、四种霊薬已按046b决定落实，不再把这些当作阻塞问题。

5. **推断清单**

- 三次交互预算计国王提示、买氷の護符、尝试借同伴；判定失败仍算一次尝试，不强行成功。接受イアン请求延续第一部分视为主线路径，不额外计预算。
- HP70免费休息规则推广到全部原型；不付费休息，半回复温泉在仍低于阈值时继续。游戏没有三次上限；真实人类的三次独立报告。
- P1使用heuristic，支线固定为ガルド/リク；普通救援和封印选择按成功概率最高的可用判定，其他节点用显式顺序。P2继承并加入准备链；P3顺序和购买数量如上。未用试跑结果搜索最优路线。
- P2s优先尝试潜行/迂回；失败受真实代价，SP不足时不重复无效潜行。其余配置与P2完全相同。
- P0g把可重复获益战斗视为当前空集；不通过区域重试还原状态后保留收益或重置击败旗标。
- 原型共享trial_seed(seed,route_v2,character,index)起始种子；独立配置和消融在对应组共享种子，行动差异仍会改变后续随机数消耗。
- 主线节点记录首次到达等级，只对真正到达的样本求均值；不补齐死亡后节点。终局字面上包含失败ending。
- M1'分别比较P0a→P1及P0b→P1；未自行合并两个P0。
- M3使用未扣过量回复的可持续同伴回复能力；有限消耗品归M3'。M3'用开场净期望伤害、当前HP加库存回复估算耗尽回合；未折算有限MP/SP治疗。只用胜利/净化样本的实际击杀回合，失败样本按右删失标记；净伤害≤0为无限耗尽时间、比值0。
- M5回复使用率按道具件数，金币比例分母包含开局支给；只取到达最终Boss的P1样本。
- M7选择普通成功/普通失败（非暴击）两个因果分支，打完由它们引起的被迫战斗后比较现有resource_score；未假称测了整路线通关差。
- M8对所有同伴做不受招募地点限制的同配置探针；额外列强化火コウモリ竜。旧矩阵外Boss复用已有economy.encounter_checkpoint，不替它们另定等级。
- M13固定技能和装备，只使用现有里程碑的数值成长；等级5没有虚构+1到6级。不是EXP机制验收。
- 存档战斗地点由位置转移前地点与敌人ID匹配，早期系统文本采用位置历史推断；日志去重按event_id。Boss开战HP/库存为前次结算与资源流水重建，明确非直接快照；区域回退快照不冒充Boss开战状态。
- 试玩配置的配装从最终配装反向撤销Ignis后的装备事件，库存按战前流水；以满资源运行独立探针，不代表复刻了全部玩家行动。
- 对原文两个CV差异的攻击条件化解释仍为推断；真实AI零伤害回合计入M9/M10。
- “最接近P2”按可观察到的洞窟/砦与支线行为作提案分类，不从单局胜负倒推策略。
- 原型/准备/指标没有规定逐件库存购买次数、技能固定的等级探针、普通分支还是暴击、删失处理的细节，以上均显式选择并保留数据接口。

6. **偏离 spec 的地方及原因**

- 按046b决定取消旧>90%复现停止条件；保留它的历史汇报，不继续使用旧reproduction_v2命令作为本轮完整入口。正式新入口为measurement_v2。
- 新测试不能在tests/创建，已按brief放`.tmp-test/046b/tests/`并导出tests.patch；现有测试只最小改动三处。
- 为排除047同时写入的源文件，基线和完整验证使用固定HEAD快照，而不混跑共享工作树；工作树的实际失败也单独列出。
- M3'目前是上述静态估计；MP/SP治疗的资源池折算留待设计确认，没有宣称精确模拟穷尽全部资源。
- 提交受`.git`写权限限制；完整补丁按brief交付，具体错误与文件清单见第7节。

7. **已知问题、扩展接口与交付**

原始存档已找到，但event_log是240条截断环；早期4场回合数缺失、完整动作分布缺失。未用叙事文本编造动作次数或道具使用率。需要引擎补记录（只列缺口，未改host）：

- combat_id 关联的完整战斗开始/结束快照、遭遇 ID、类别和等级；event_log 当前会截断。
- 逐回合玩家行动 ID、目标、消耗、伤害/回复，以及状态/冷却；recent_events 只有末尾文本。
- 道具移除的原因（使用、交易或剧情交付）及其 action_id/combat_id；移除不能直接算回复使用。
- 带 action_id 的完整判定和其失败资源变化/后续战斗关联；dice_log 本身没有地点或 action_id。
- 完整配装/同伴/休息流水，以及准备项在具体战斗中生效的记录。
- 存档所用引擎版本及剧本指纹；区域回退快照不是某场 Boss 的开战快照。

扩展接口：`LevelModel.observe(session,node)->int`只读引擎等级，当前为MilestoneLevelModel；`PassivePicker.pick(options,scores)->list[str]`支持first/battle_best/enumerate，`combinations(groups)`枚举完整组合，现无选项返回空。战斗摘要statuses=[]、skill_usage={}是未实装新状态/冷却/被动机制的占位，M12明确not_applicable。M13另报当前实际到达等级差，但EXP验收字段保留null并标待050/051。

新指标输入统一为`{records, targets, preparation_probes, companion_probes, damage_budget_v2, boss_policy_probes, level_probes}`试验包。完整归约输入保存在忽略的`.tmp-test/046b/experiment-records.json`，可用`--records-output`重建；基线JSON保留所有指标细分值、样本、种子、输入与代码指纹。

交付文件：`eval/reports/046-measurement-v2-baseline.json/.md`、`eval/reports/046b-save-telemetry.json/.md`、本报告；准备提案为`eval/balance/preparations.json`。

沙箱不能写Git索引，未完成提交。完整补丁`.tmp-test/046b/046b.patch`含全部17个目标文件（含新测试）；`.tmp-test/046b/tests.patch`单独含新测试，不要在完整补丁后重复应用。建议提交信息：`[工程] 046b 完成玩家原型、决策指标与存档遥测`。补丁不含047、开工前已有未跟踪报告、raw资料、临时快照或密钥。

对第2节的16个实际文件逐项git add失败：`fatal: Unable to create D:/TRPG_Game/.git/index.lock: Permission denied`。未暂存、未提交。完整17文件补丁已在独立的HEAD文件副本通过正向check、实际应用和反向check；新测试单独补丁也已通过git apply --check。
