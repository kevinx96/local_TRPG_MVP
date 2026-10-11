# 002 评测修复 + 战斗数值模拟器

分两部分，**A 做完先单独提交一次**，再做 B。

## A. 评测运行器修复（001 实跑时发现的问题）

设计负责人在沙箱外实跑 001 时遇到以下问题：

1. **Gemini 429**：大约 15 次请求后返回 `429 Too Many Requests`，运行器在第一个错误就停了。
   - 加 `--rpm N` 限速（默认读配置 `eval.rpm.<backend>`；gemini 默认 14，ollama 默认不限）。
   - 429 和 503 按指数退避重试（优先使用 `Retry-After` 头或 Gemini 错误体里的 `RetryInfo.retryDelay`），最多 5 次；超过次数才记为 request_error。其他错误仍按现有方式停止。
2. **本地 Ollama 超时**：`qwen3-swallow-8b-rl-local` 默认先输出很长的 reasoning，15 秒读超时内答不完。设计负责人实测：
   - OpenAI 兼容接口加 `"reasoning_effort": "none"` → 不输出 reasoning，约 2.6 秒
   - 原生 `/api/chat` 加 `"think": false` → 约 2.4 秒
   - 只加 `"think": false` 到兼容接口 → 仍有少量 reasoning
   请在 ollama 请求里加入可配置的思考开关（配置键 `disable_thinking`，评测默认 true；游戏默认行为不变），兼容接口用 `reasoning_effort: "none"`，原生回退用 `think: false`。
   - 加 `--timeout` 参数（ollama 默认 60 秒）。
   - 第一次 live 请求前先发一次预热请求，不计入结果。
3. **运行器无法直接指定地址**：本机配置里 ollama 的 `base_url` 是远程隧道地址。加 `--base-url` 参数，只对本次评测生效。
   - **安全**：配置里 ollama 后端带有 Cloudflare Access 的 `headers`。`--base-url` 的 host 和配置里的 host 不同时，**不要发送这些 headers**。为此写测试。
4. **观察到的契约问题，只记录不修**：Gemini 对 `existing` 动作返回了 `advance: true`，`parse_plan` 直接判为 InvalidPlan，整回合失败。不要修改 `parse_plan`。在报告的 InvalidPlan 部分按原因分类统计，以便设计负责人决定怎么处理。

A 的验收：离线测试覆盖限速、429 重试（伪造响应）、思考开关参数、headers 不外泄；然后提交。

## B. 战斗数值模拟器

背景：`docs/roadmap.md` 的 P4。设计负责人之前做过一个粗略模拟（初始装备、只普攻），结果是：从 hobgoblin 往后几乎全部 0% 胜率，职业间差距极大。现在要一个正式、可重复的工具，为调参提供数据。**这次不改剧本数值，也不改引擎的默认行为。**

### B1 遭遇分类
在 `dragon_rpg.json` 和 `dragon_rpg_hybrid.json` 每个战斗地点的 `combat` 里加上 `encounter_class` 字段，取值按 `eval/balance/targets.json` 的 `encounters` 表（设计负责人已写好）。schema 里补上这个字段（可选，枚举 trash/elite/boss/scripted_loss/guest）。引擎暂时不读这个字段。

### B2 防御公式选项
`combat_rules` 支持 `defense_mode`：
- `flat`（默认，等于现状）：`max(1, round(raw*mult) - def)`
- `floor`：`max(ceil(raw*mult*floor_ratio), round(raw*mult) - def)`，`floor_ratio` 默认 0.25
- `ratio`：`round(raw*mult * k/(k+def))`，最低 1，`k` 默认 10

不设 `defense_mode` 时行为和现在完全一致（现有测试必须全部原样通过）。

### B3 模拟器 `scripts/balance/sim.py`
- 用真实战斗引擎（`combat.ensure_combat_started` / `perform_combat_action` / `combat_actions`），每个遭遇单独构造会话。可以参考的思路：复制剧本，只保留一个包含该遭遇的地点，保留角色、物品、同伴、combat_rules 不变。
- 参数：剧本、遭遇（可多个或 all）、角色（可多个或 all selectable；guest 遭遇使用 `player_character_id`）、checkpoint、策略、N（默认 500）、seed、`defense_mode` 覆盖、`stat_scaling` 覆盖。
- 策略只能使用 `combat_actions(session)` 返回的、玩家看得到的动作：
  - `attack_only`：只普攻
  - `greedy`：每回合选期望伤害最高且付得起的攻击（技能、道具、普攻）
  - `heuristic`：HP < 35% 且有回复手段时先回复；遇到 boss 时在前两回合使用增益或护盾类技能（如果有）；其余按 greedy；不使用逃跑
  - 期望伤害由公式计算（骰子期望 + 属性 + 命中率 + 抗性），不要用试算偷看随机结果
- 输出每个（遭遇 × 角色 × 策略）：胜率、回合数中位数、胜利时剩余 HP 比例均值、消耗的回复道具和 MP/SP、战败回合分布。
- `stat_scaling`（只给模拟用，用来探索成长曲线）：`{"hp_mult": 1.0, "attr_add": {"str": 0, ...}, "skill_unlocks": []}` 作用在角色上。

### B4 checkpoint（拟定）
`eval/balance/checkpoints.json`：每个遭遇对应"一个正常推进的玩家此时大致拥有什么"——背包、装备、同伴、金币。
- 从剧本数据推导：按场景顺序和地点之间的跳转，收集遭遇之前能拿到的 `inventory_add`、`equip_item`、`set_companion` 等效果。推导不出来的地方写进 `notes`，不要编造。
- 每条标 `"status": "proposed"`，由设计负责人审定。

### B5 检查
- `python -m scripts.balance.sim --check`：按 `targets.json` 判定每个遭遇是否落在区间内，输出越界列表；有越界时返回非零。
- 加一个测试：用小的 N 跑 `--check`。只有环境变量 `BALANCE_ENFORCE=1` 时才执行，否则 skip（目前数值肯定不达标）。
- 模拟器本身的单元测试照常执行，例如：同一 seed 结果一致、策略只用可见动作、`defense_mode` 公式计算正确。

### B6 报告
`eval/reports/balance-<日期>.md` 加同名 CSV：
1. 现状矩阵：每个遭遇 × 可选职业 × 三种策略，用 checkpoint 装备，`defense_mode=flat`。
2. 同一矩阵在 `floor` 和 `ratio` 下各跑一遍，只列 heuristic 策略。
3. **缩放搜索**：对每个 elite/boss 遭遇，在 heuristic 策略下，用网格搜索找到让胜率进入目标区间的最小 `hp_mult`（1.0–3.0，步长 0.25）和统一 `attr_add`（0–6）组合，三种 defense_mode 各搜一遍。结果用来设计里程碑升级曲线。
4. 职业差距：每个遭遇里各职业胜率的最大差值，标出超过 0.15 的遭遇。
5. 现状下各遭遇胜率最差的职业，以及最常见的战败原因（被哪个技能或攻击打死、在第几回合）。

## 不做
- 不改剧本里的任何数值，也不改敌人和技能。
- 不实现等级或升级系统（等报告出来，由设计负责人决定曲线后另开 spec）。
- 不改默认提示词。

## 验收
- 两条验证命令通过；A、B 分别提交。
- 报告 B6 的 5 部分齐全；对 N=500 的结果给出运行时间。

## 汇报要回答
1. 现状（flat）下，每个遭遇类别有多少遭遇达标、多少越界。
2. 三种 defense_mode 中，哪种在不改敌人数值的前提下最接近目标？代价是什么（例如某类遭遇变得太简单）？
3. 缩放搜索的结果是否能拟合成一条单调曲线（按剧情顺序）？有没有明显的异常遭遇？
4. checkpoint 推导里不确定的地方。
5. 同伴在战斗中实际起了多大作用（有/无同伴的胜率差）。
6. 其余按 `docs/roles/engineering.md` 的汇报格式。
