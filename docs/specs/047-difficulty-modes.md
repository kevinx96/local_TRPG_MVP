难度 D4 · 执行方 Codex astra 6 high · 理由：会话格式、引擎、客户端、剧本跨系统改动，并且必须在任何数值改动之前冻结现有数值
# 047 难度模式：baby / normal、数值冻结与覆盖层

来源：用户（2026-10-20，原话摘要见 `docs/design/skills-v2-user-draft.md` 末尾"其他要求"）：目前的数值难度保留为 **baby**，之后修改的数值作为 **normal**；主界面加难度选择，默认 normal。

已定的决定：
- 难度两档：`baby`、`normal`。
- **现在剧本里的全部数值原样冻结为 baby。**normal 目前与 baby 完全相同；之后的平衡 spec（含 051 起的机制与数值改动）**只修改 normal**。
- 开始界面（角色选择处）加难度选择，默认 normal；显示名日文，暂定「やさしい」（baby）、「ふつう」（normal），最终名称与说明文由设计负责人定。
- 难度存进会话；**旧存档一律视为 baby**（它们是按现在的数值玩的）；会话的剧本刷新（`content_revision` 变化触发的 `_refresh_session_scenario_pack`）后难度保持。
- 文本和剧情只有一份；难度只覆盖数值字段。

## 0. 文件边界与顺序
- **可以改**：`host/`、`client/`、`scripts/scenario/`（新增迁移脚本）、`host/prompt/processed/dragon_rpg.json` 与 `dragon_rpg_hybrid.json`（**始终同步**）、`host/prompt/processed/scenario_pack.schema.json`、`tests/`（新增为主）、`scripts/worker_fingerprints.py` 仅当提示词变化时。
- **不得改**：`scripts/balance/`、`scripts/playtest/`、`eval/balance/`（046 线在改，两条线文件不能重叠）。只在引擎侧提供"按难度生成会话"的接口，并在汇报里写清 046 线如何接入（第 6 节）。
- 迁移脚本 `scripts/scenario/difficulty_modes.py` **必须幂等**，测试检查重跑不改变剧本；同时更新 `content_revision`。
- **第一步是冻结，先于一切其它改动**：见第 1 节，冻结快照单独成一次提交（信息写明"仅冻结快照，无行为变化"），之后再做机制。
- 本任务完成前，后续所有平衡 / 机制 spec（048、051 等）不开工。

## 1. 冻结 baby
- 新增 `tests/fixtures/baby_numeric_freeze.json`：对**两份剧本包**，按第 2 节的白名单提取全部数值字段（实体 ID → 字段路径 → 值）。这是 baby 的"真值"，之后任何人改了 baby 的有效数值，测试就会失败。
- 新增测试 `tests/test_difficulty_freeze.py`：
  - 有效 baby 包（`apply_difficulty(pack, "baby")`）的数值字段集合与快照**逐项相等**，字段数也相等（防止新增数值字段而没进快照时被忽略：新增字段必须显式更新快照并在提交里说明）；
  - 当前 normal 与 baby 的有效包完全相同（本 spec 完成时 normal 覆盖层为空）。
- 快照的更新规则写进测试文件的文档字符串：**平衡类 spec 不得更新 baby 快照**，只有明确说明"调整 baby"的任务才可以。

## 2. 数值字段范围（由工程列出，设计负责人在汇报里验收）
白名单按"字段路径模式 + 实体类别"定义（放在 `host/difficulty.py` 的常量里，一处维护），至少覆盖下列类别；**请逐类在剧本里实际找出字段并列表**，找不全的类别在汇报里标出：
- 敌人：HP / MP / SP、属性、基础攻击与技能的伤害骰子、命中、消耗、抗性、`combat.defense` / `evade`、奖励金币、百分比 / 回复类数值；
- 道具：战斗数值（伤害、回复量、命中）、售价与购买价、`effect` 里的数值字段；
- 商店：价格、库存数量；
- 同伴：`round_start_effects` 的伤害 / 回复量；
- 角色模板：HP / MP / SP 上限、属性、基础攻击、里程碑成长（`milestones.gains`）、`level_skills` 里技能的数值（伤害、消耗、命中、倍率）；
- EXP / 等级相关数值（目前是里程碑触发，将来是 EXP 表；字段出现时自动进入白名单）；
- 判定：`roll.dc`、`dc_overrides`、`sneak_dc`、`roll_bonuses` 的数值部分；
- 遭遇：`victory_gold_bonus`、`encounter_class` 以外的战斗修正（`encounter_modifiers`）、特殊行动的 `cost`；
- 引擎侧的难度相关常量（例如 `combat_rules` 里的 `defend_multiplier`、`flee_dc`、`sp_regen_per_round`）：在剧本里的就归入白名单；**写死在 `host/*.py` 里的**列进汇报，不要改成可配置。

**不属于数值的**：文本、选项、剧情分支、flag、物品 / 敌人 / 地点的存在与否。覆盖层不得新增或删除实体，也不得改文本。

另外覆盖层支持第二个通道：**机制开关字段**（例如将来 051 的 `combat_rules.evade_model`）。本任务里这个清单**为空**，但通道要建好：`host/difficulty.py` 里一个 `MECHANIC_FIELDS` 常量，校验逻辑与数值白名单分开，后续 spec 往里加条目即可。

## 3. 覆盖层
- 数据放在剧本包里，两份剧本同步。**基础值 = baby**（现有数值原地不动）；`normal` 的差异写成覆盖层，**初始为空**。理由：之后的平衡只会往 normal 层添加条目，baby 永远不会被误改。
- 建议结构（具体键名工程定，但要满足下面的要求）：
  ```json
  "meta": {"difficulty": {
    "default": "normal",
    "base": "baby",
    "modes": [{"id": "baby", "label": "やさしい"}, {"id": "normal", "label": "ふつう"}]
  }},
  "difficulty_overlays": {"normal": []}
  ```
  覆盖项形如 `{"entity": "enemies", "id": "ignis", "path": "combat.basic_attack.damage", "set": "1d12+str/3"}`，另支持 `add` 与 `mul`（数值）。
- 要求：
  1. **按实体 ID 寻址**，不用数组下标，这样改剧本时覆盖层不会错位；路径无法解析时，加载剧本 / 测试就报错，不能静默忽略：实体必须存在；数值字段必须已存在于基础包；只有列在 `MECHANIC_FIELDS` 里的机制开关字段允许 `set` 新建（其父对象必须存在），因为机制开关通常是在基础包里不存在的新字段。
  2. 校验器拒绝：不在白名单（数值或机制开关）里的路径、文本字段、新增 / 删除实体。
  3. 纯函数 `apply_difficulty(pack, mode) -> pack`：返回深拷贝，不改入参；`mode` 未知时抛错；`baby` 恒等于基础包。
  4. 同一路径在 normal 层出现多次时，按顺序依次应用，并在校验时发警告（测试里当错误处理）。
  5. 写清覆盖层规则：放在 `host/difficulty.py` 的模块文档字符串里（给后续平衡 spec 用）。内容至少包括：基础值即 baby、不得改；"只改 normal"怎么写；白名单在哪；新增数值字段怎么入白名单；快照怎么更新（第 1 节）。
- 剧本编辑器（`client/editor.*`、`ScenarioSaveRequest`）保存时**不得丢失** `meta.difficulty` 与 `difficulty_overlays`；加一个测试覆盖"编辑器保存往返后这两个键保持不变"。

## 4. 会话
- `session["difficulty"]` ∈ {`baby`, `normal`}。
- `create_session(..., difficulty=None)`：`None` → `normal`（产品默认）；非法值抛错。`CreateSessionRequest` 增加可选 `difficulty` 字段，非法值返回 400。
- **新建**时：加载剧本包 → `apply_difficulty(pack, difficulty)` → 存入 `session["scenario_pack"]`（会话里存的仍是**有效包**，和现在一样；这样引擎、`scenario_context`、模型上下文都不用感知难度）。
- **加载旧存档**：没有 `difficulty` 键 → 记为 `baby` 并保存。旧存档里的 `scenario_pack` 是当时的快照，不重新套覆盖层。
- **剧本刷新**：`_refresh_session_scenario_pack` 取到最新包后，必须先按 `session["difficulty"]` 套覆盖层，再用于后续所有对比与写入；该函数中"道具变化对比"用的 `old_items` / `changed_items` 都必须是**同一难度下的有效包**，否则会把难度差异误当成剧本更新。覆盖层改变本身也要触发刷新：`content_revision` 随覆盖层变更而更新，这是后续平衡 spec 的义务，在 `host/difficulty.py` 的规则里写明，并加一个测试保证"覆盖层非空而 `content_revision` 未更新"不会被提交（可以对比 `tests/fixtures` 里记录的覆盖层哈希与 revision，覆盖层哈希变了而 revision 没变则失败）。
- 难度**开局选定，局中不可改**（本 spec 不做切换）。
- `public_session` 返回 `difficulty` 与显示名；存档 / 导出的会话摘要（`scripts/` 以外的现有展示）如果列出角色信息，顺带显示。
- 不改提示词，也不把难度写进模型上下文。冻结 benchmark 重放保持 194/194。

## 5. 客户端
- 开始界面在角色卡下方加难度选择（两个互斥按钮或单选，窄屏也能用），默认 normal；选中状态明显；各档一行简短说明，**说明文写成占位**（例如「（仮）説明文は設計担当が提供」），在汇报里列出，由设计负责人补。
- 创建会话时把所选难度发给后端；会话进行中在设置 / 状态区域显示当前难度（小字即可）。
- 读取旧存档（`difficulty` 为 baby 的）显示 baby 的名称。
- 更新 `?v=` 缓存键；`node --check client/app.js` 通过；截图自查开始界面（桌面与窄屏各一张，放 `eval/reports/screens/047/`）。

## 6. 给 046 线的接入说明（写进汇报，不改 `scripts/balance/`）
汇报里单列一节，写明：
- 按难度得到有效包的函数：`host.difficulty.apply_difficulty(pack, mode)`；
- 按难度生成会话的入口：`state.create_session(..., difficulty=...)`，以及 `scripts/balance/checkpoints.fresh_session` 等现有模拟入口如何能传入难度（给出建议的最小改动，**不要自己改**）；
- `eval/balance/checkpoints.json` 里的 `scenario_sha256` 是对基础包还是有效包校验；现在两档相同，将来 normal 变化后 checkpoint 是否需要按难度各一份，给出你的建议。

## 7. 不做什么
- 不改任何数值、不动任何文本、不新增敌人 / 道具 / 剧情；normal 层保持为空。
- 不做局中切换难度、不做第三档、不做按难度的存档分区。
- 不改 `eval/benchmark/`、`docs/`、`scripts/balance/`、`scripts/playtest/`。
- 不改提示词，不改 Worker。

## 8. 验收与汇报
- 单元测试：
  - 冻结快照（第 1 节）；
  - `apply_difficulty` 的纯度、未知模式、非法路径、白名单拒绝、normal 空层恒等；
  - 用一个**测试专用的假覆盖层**（只在测试里构造，不进剧本）验证覆盖生效、按 ID 寻址、`add`/`mul`、机制开关通道（用测试里临时加入的开关字段）；
  - 新建会话默认 normal；指定 baby；非法值被拒；
  - **旧存档（无 `difficulty`）加载后为 baby**，数值与存档内快照一致；
  - 剧本刷新后难度保持，且有效数值仍按该难度；
  - 编辑器保存往返不丢键；
  - 迁移幂等（重跑不改变两份剧本）。
- 冻结 benchmark 重放 194/194 不变（`--variant guard_rules --split dev`，沿用 041 的做法）。
- 离线通玩（`scripts/playtest/` 现有脚本，只运行）在 baby 和 normal 下各跑一遍，无异常、无死路；两档结果应完全一致。跑完恢复 `eval/reports/playtest-*`，不提交。
- `python -m unittest discover -s tests -q`、`node --check client/app.js` 通过；两份剧本同步；提交（`[工程]` 前缀，只 add 具体文件）。
- 汇报：白名单覆盖的类别与字段数表（含未能归类的）、写死在 `host/*.py` 里的难度相关常量清单、给 046 线的接入说明、占位文本清单（难度说明文）、截图路径、冻结提交的哈希。


## 设计负责人决定（2026-10-20）
- 接受：难度在开局选定，局中不可改；覆盖层改了而 `content_revision` 没有更新时测试失败；显示名「やさしい」（baby）/「ふつう」（normal），说明文先用占位。
- 接受"机制开关"通道，但**只用于会改变难度的规则**：敌人命中统一 100%（G1）、氷の護符只对冰弱点可用（B1）、火コウモリ竜回复与伤害挂钩（B3）、致死保留需冷却（G3）。baby 保持旧规则，normal 打开。
- **新增的内容系统两档共用**，不做开关：状态效果、dex 闪避、技能与被动、等级/EXP、陷阱、新道具。baby 与 normal 的区别只在数值和上面那几条规则。
- 数值字段白名单由工程列出，设计负责人在汇报里验收；写死在 `host/*.py` 里的常量只列清单、不改。
