# 046 工程汇报（复现门槛停止）

## 1. 完成了什么

**046 尚未全部完成。** 已实现并运行复现所需的最小测量链；按 spec §6「复现不了就先修测量……修不了停下来汇报」，停止后续原型、完整指标和遥测实现。没有修改游戏数据来满足验收数字。

本次没有取得原始 `e2b9fdd9…` 存档。前缀查找没有结果，设计负责人在 spec 末尾亦确认其丢失。采用设计文档 §1.1 的九场战斗时间线和 §1.2、§1.4 配置。不能将其他存档冒充目标。

主通关口径采用 spec 末尾决定：`game_over.title == 冒険完了`；另外统计 `defeated_ignis` / `ignis_purified` 和进入终局。此决定覆盖 spec §1 早先的「击败 Ignis 为主口径」。

实现内容：P0a/P0b 连续路线、七个原型的提案参数表、`best_free`、节点等级与战斗摘要、独立试玩 checkpoint 和两个配置探针、准确计算敌人 AI 混合伤害的均值与 CV、多进程及 Windows 无命名管道时的独立子进程回退、修改前旧输出固定样本和回归测试。

完整数据：[046-measurement-v2-baseline.json](046-measurement-v2-baseline.json)。基线表和威胁逐项对照：[046-measurement-v2-baseline.md](046-measurement-v2-baseline.md)。

每格 N=500，seed=20261020；通关率如下：

| 原型 | 勇者 | 僧侶 | 魔法使い | 盗賊 |
|---|---:|---:|---:|---:|
| P0a | 0.0% | 0.2% | 0.0% | 0.0% |
| P0b | 42.4% | 40.6% | 5.6% | 23.0% |

| 复现要求 | 实测 | 结论 |
|---|---|---|
| P0b 勇者路线 >90% | 42.4% | 未通过，低于门槛至少47.6pp |
| 文档试玩配置 Ignis 中位数17–22回合 | 19回合 | 通过 |
| 强化火コウモリ竜 S>1 | 6 / 4.8138095 = 1.246414 | 通过；净回复约1.186 HP/回合 |
| 威胁均值/CV对照 | 17项中15项在容差内 | 两项差异已解释，仍保留为未通过 |

独立试玩配置的 Ignis 胜率是 **95.6%**，加氷鉄の大剣是98.8%，无同伴是63.4%。独立满资源战斗不等于从开局连续推进的通关率，不能拿95.6%替换路线42.4%。

威胁超差的两项：ゼボク有1/6权重的亡霊転換，ドラコ有1/6权重的護衛の構え；这些回合不直接造成HP伤害。计入它们时分别为15.33% / CV1.0136、15.19% / CV0.6670。仅在攻击发生的条件下计算，得到18.40% / CV0.8304、18.23% / CV0.4518，与文档18% / 0.83、18% / 0.45吻合。**文档使用了条件化口径是推断**；实际AI的零伤害回合不能静默删掉。

勇者 P0b 的288次路线失败分布：スライム王177、valley_entrance 53、Ignis42、village_fire_elemental 9、氷の精霊6、氷霜の巨狼1。借火コウモリ竜虽不花金币，仍有真实判定；当前勇者成功概率只有55%。

本次共4000条路线试验、1500次独立配置战斗，4个路线 worker，配置探针串行，总墙钟 **192.64秒**。不含后续完整P2/P3路径，不能直接当作七原型全量成本。

## 2. 改动的文件

- `scripts/balance/archetypes.py`：七个原型的显式参数与校验，LevelModel / PassivePicker 扩展接口。
- `scripts/balance/route_v2.py`：P0a/P0b 路线、战斗摘要、汇总与隔离进程；其他原型明确拒绝运行，避免将未实现路径当作结果。
- `scripts/balance/reproduction_v2.py`：文档配置生成、500次探针、威胁对照和复现门槛报告。
- `scripts/balance/sim.py`：显式增加 `best_free`，离散骰子/整数伤害期望；读取新 checkpoint 的可选 flags。旧的 `--policies all` 仍只跑旧三策略。
- `scripts/balance/budget.py`：新增均值/方差/CV接口，旧 `incoming_damage_budget` 保持原样。
- `scripts/balance/report.py`：一行改为遍历旧策略集合，保证旧报告不会默认增加 best_free。
- `scripts/balance/test_measurement_v2.py`：14项新增离线测试。环境拒绝在 `tests/` 新建文件，故在允许的目录中提供独立测试模块。
- `scripts/balance/test_environment/sitecustomize.py`：显式开启的 Windows 测试启动兼容层，仅对仓库内新临时目录使用普通继承权限；不改现有ACL，默认不启用。
- `eval/balance/046-legacy-output.json`：修改前保存的同seed旧输出；固定计时为0以消除墙钟噪声。
- `eval/balance/checkpoints_berserker.json`：文档试玩配置及「P0b + 氷鉄の大剣」「无同伴」两个独立配置。
- `eval/reports/046-measurement-v2-baseline.json`、同名`.md`及本报告。

没有新增第三方依赖；没有修改 `host/`、剧本包、`scripts/scenario/`、`client/` 或既有测试文件。运行仓库测试产生的忽略日志不作为源码改动提交。

## 3. 验证结果

- `python -X utf8 -m scripts.balance.reproduction_v2 --n 500 --workers 4`：运行192.64秒，退出码1，表示复现门槛未通过；它不是程序异常。
- `python -X utf8 -m unittest scripts.balance.test_measurement_v2 -q`：14项通过。覆盖参数预算、零成本筛选、30%严格阈值、整数伤害期望、AI零伤害混合与CV、定时技能、checkpoint、扩展占位、串行/多进程逐字一致。
- `sim --check`固定seed输出与修改前逐字一致；`route.simulate_route(hp70)`、`class_aware.trial(backbone)`序列化结果与修改前逐字一致。计时在采样前后都固定为0，没有删除或忽略结果字段。固定样本的旧`sim --check`本身退出1，回归同时核对这一退出码。
- 对同一checkpoint和RNG分别运行既有 `route.fight` 与新测量包装：最终资源、胜负及RNG状态完全一致，确认测量没有消耗额外随机数。
- `node --check client/app.js`：通过。
- 原样 `python -m unittest discover -s tests -q`：754项、288.618秒，36个PermissionError、跳过1项；Python3.13的临时目录0700 DACL导致受限令牌不能访问自己创建的目录。
- 显式启用启动兼容层后再次执行 `python -m unittest discover -s tests -q`：754项、266.178秒，`OK (skipped=1)`；退出码0。新增14项独立测试与JS检查亦再次通过。

完整测试兼容启动方法（环境变量只影响当前shell及其子进程）：

```powershell
$env:TRPG_TEST_TEMP_INHERIT = '1'
$env:PYTHONPATH = 'D:\TRPG_Game\scripts\balance\test_environment' + [System.IO.Path]::PathSeparator + $env:PYTHONPATH
$env:PYTHONIOENCODING = 'utf-8'
python -m unittest discover -s tests -q
node --check client/app.js
python -m unittest scripts.balance.test_measurement_v2 -q
```

## 4. TODO(design) 清单

1. **澄清A.4.1的比较对象**：是严格「最多三次可选交互」的P0b连续路线，还是包含洞窟准备的试玩满资源配置？后者已有95.6%独立胜率，但不是前者。当前无法在不额外准备、不强行借用成功的前提下把两者等同。
2. 确认三次精霊の泉休息发生的时间点及主线路径。当前首次到泉即休息，スライム王为Lv1/20HP；文档为30HP。缺失的成长、往返或先前支线不能由九场摘要唯一恢复。
3. 确认M9/M10是否应按实际AI所有回合计算。当前以所有回合为主，另列只看攻击的条件化对照，没有改阈值。
4. 确认四种霊薬具体品种。当前剧本有五种，原始清单未指明；JSON留 `unresolved_inventory`，没有任选四种加入可用库存。
5. 文档§1.2写回复合计270HP，按当前道具定义实际为 `7×10 + 9×30 = 340HP`（最大HP40的8.5倍）。保留文档给出的数量，运行时按真实道具定义计算，未改游戏数值。
6. 后续审定M2清单和P2/P3支线范围，再恢复完整测量。定义表目前全部标 `proposed`，尚不作为门槛。

M2待审提案（未实现移除试验或写入`preparations.json`，遵守复现停止条件）：

| 准备项 | 剧本取得方式 | 拟议移除方式 |
|---|---|---|
| 紅玉の護符 | 洞窟熔岩宝箱 | 移除库存与装备并同步配装 |
| アダマンタイトの鎧 | 锻冶店购买，需END条件 | 移除装备；恢复原鎧，不返还购价 |
| 聖水净化路线 | 取得聖水及古伤相关线索 | 禁用净化选择/清除净化资格；与移除单瓶聖水分开测 |
| 氷鉄の大剣 | 接受イアン请求 | 移除武器并恢复先前武器 |
| 火コウモリ竜 | 道具屋借用判定 | 清空同伴 |
| 火コウモリ竜强化 | 带该同伴击败虹晶樹 | 只清除 `fire_bat_empowered`，保留普通同伴 |

P2候选支线：ガルド、リク、完整洞窟、ゴブリン砦、净化线索链。P3候选再加城镇交付、ミーナ、旧戦場、オークスドーン、峡谷、将军屋敷、商人支线及商店。互斥支线与访问次序尚待审，**未声称已覆盖全部支线**。

## 5. 推断清单

1. 三次休息都排在首次到泉，不为了胜率反复试排后挑最高结果。
2. 主线选项沿用既有backbone的战斗推进方向，采取谨慎接近燃烧村庄、离开火屋、正面打森狼/氷の精霊/煤の亡霊、走熔岩桥；文档没有完整行动序列。
3. `accept_ian_request`作为直接主线路径行动，不计入三次可选交互；P0b拿到大剣后装备，P0a保留初始配装。若设计认为应计一次，必须重新定义预算。
4. 各原型共享 `sim.trial_seed(seed, 'route_v2', character, index)` 起始种子；独立探针共享 `sim.trial_seed(seed, 'dragon_valley_loc', 'hero', index)`。新增key命名是工程选择。
5. 节点等级取首次到达值，只对真正到达的样本求均值，不补齐死亡后节点。
6. 大ゴブリン对照映射到 `goblin_fort_second_right`，普通史莱姆行排除固定8点真实伤害的教学 `tutorial_slime`。
7. 两项威胁差异的「文档可能按攻击条件化」解释来自数值吻合，是推断。
8. 通关后706G和回复库存用于独立Ignis配置；它们不是可验证的Ignis开战前库存。原始存档丢失，不能追溯此前取得与使用。
9. P2/P3清单和装备移除后的对照方式是提案，尚未据此产生结果或门槛。

## 6. 偏离spec的地方及原因

- 未交付完整P1/P2/P3/P2s/P0g路线、`metrics_v2.py`全部M1–M13、`targets.json`v2、准备消融和`save_telemetry.py`。原因是spec§6要求复现失败后停止；这不是任务全部完成的声明。
- 新测试放在 `scripts/balance/`；`tests/`新文件创建被实际系统权限拒绝。没有修改该目录ACL或已有测试。
- 四种霊薬按未知清单记录，未伪造具体品种。
- 新增显式测试启动兼容层，解决受限Windows环境下的临时目录创建问题，不改变游戏、测试断言或现有文件权限。

## 7. 已知问题与引擎侧记录缺口

目前路线结果依赖上列显式推断，不能当作丢失试玩存档的完整复盘；需要设计澄清后再继续。

扩展接口：`LevelModel.observe(session,node)->int`当前只读引擎里程碑等级；`PassivePicker.pick(options,scores)->list[str]`支持first/battle_best/enumerate，当前没有选项故返回空；`combinations(groups)`预留组合枚举。战斗摘要 `statuses=[]`、`skill_usage={}` 是未实装机制的占位，不能当作已经采集了新技能/冷却数据。

目标原存档不存在，因此不能列出它「实际具备」的字段。仅从现有源码可确认：session有event_log、dice_log、messages、system_logs、last_combat_result；event_log上限240，last_combat_result仅最后一场且recent_events仅末8条文本。未据此编造九场完整行动史。

需引擎侧补记录的候选清单（只报告，没有修改host）：

- 持久、未截断的combat_id级历史：遭遇ID/类别、开战与结束HP/最大HP/等级/库存、回合数、结局。
- 完整逐行动数据：round、行动类型/ID、目标、是否零成本、消耗、伤害/回复、冷却与状态快照。
- 有来源的资源流水：道具取得/使用、金币收入/花费，关联action_id / combat_id，区分自动掉落、购买、消耗与装备转换。
- 判定关联：action_id、location_id、crucial标记、成功/失败及失败导致的资源变化或后续战斗。
- 全程装备变更和准备项取得/生效/使用记录；不可仅凭最终库存倒推使用率。
- 休息时间点、升级触发和scenario/引擎指纹，以便确认不同版本是否可直接对照。

一次标准TemporaryDirectory创建的 `eval/reports/046-workers-prpjuibe/` 因ACL不可访问、不可清理；没有暂存。自动审批曾拒绝带校验的清理命令，只给出 `blocked by policy`；随后简化命令获准执行，但仍被系统ACL拒绝。未修改现有权限绕过限制。

**未提交，也未暂存任何文件。** 对第2节列出的13个具体文件执行 `git add -- ...` 时失败：`fatal: Unable to create 'D:/TRPG_Game/.git/index.lock': Permission denied`。当前执行环境禁止提权，不能写入Git索引或完成提交。

已另存仅包含这13个文件的 [046-measurement-v2.patch](046-measurement-v2.patch)，供正常可写环境应用；建议提交信息为 `[工程] 046 复现测量与门槛失败诊断`。补丁不包含本补丁文件自身、不包含047代码或开工前已存在的未跟踪文件。
