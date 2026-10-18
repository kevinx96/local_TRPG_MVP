# 042b 工程汇报

依据 `.codex-runs/042b-brief.md`，延续 [042 spec](../../docs/specs/042-dice-visual.md) 与 [上一轮工程汇报](042-engineering.md)。

1. **完成了什么**

默认骰子改为设计负责人选定的 B01 深红宝石，使用金色数字和对应裂纹图。manifest 中 B01 与 B 裂纹版的原图、规范 PNG、运行 WebP 共 6 条记录标为 `approved: true`，`selection_reason` 均为「设计负责人定稿」；其余 21 条 042 记录保持 false。批次默认路径和页面预加载同步更新。重新运行素材打包工具会保留批准状态、批准理由和默认路径。

数字按各材质正面三角形重心定位，字号约为三角形高度的 45%，两位数再乘 0.85，字距为 −0.06em，不透明度为 0.9。使用上缘暗影与下缘细高光降低浮起感；自然 20 的发光继续保留。三个材质各有独立位置、字号、颜色、阴影和高光变量组。

| 材质 | 图片坐标中的重心百分比 X / Y | 112px 骰子的单字字号 | 两位数字号 | 暗影 / 高光深度 |
|---|---|---:|---:|---|
| A 骨 | 50.1% / 50.7% | 23.436px | 19.921px | 0.55px / 0.35px |
| B 宝石，默认 | 49.4% / 47.6% | 21.370px | 18.164px | 0.65px / 0.40px |
| C 黑铁 | 49.7% / 50.2% | 22.075px | 18.764px | 0.65px / 0.40px |

调节入口在 `client/styles.css`：`--dice-number-x/y`、`--dice-number-size`（相对骰子尺寸的比例）、`--dice-number-opacity`、`--dice-number-inset/highlight`、`--dice-number-shadow-depth/highlight-depth`，以及共用的 `--dice-number-two-digit-scale`、`--dice-number-spacing`。A / B / C 的暗影颜色分别使用现有背景色的 65% / 75% / 85%，细高光分别使用现有文字色 18% / 金色 22% / 文字色 20%，其余为透明。

引擎为关键判定的公开 `check` 增加 `crucial: true` 和 `crucial_reason: "combat" | "game_over"`。同一元数据在结算前写入骰子日志，因此切换地点、设置旗标或结束游戏后仍能正确展示结果。无关键风险的公开判定结构保持原样。自由观察的短版掷骰也传递该元数据。

判定卡在掷骰前显示「失敗すると戦闘」或「失敗すると危険」。关键判定失败时采用裂纹图并震动，普通失败不显示「大失敗」；该字样仍只用于启用极值规则的自然 1。成功不裂开，双骰只处理被采用的骰子。`critical_enabled: false` 禁用自然 1 / 20 效果，但关键失败仍展示裂纹。

原来直接进入战斗的响应会跳过判定演出；现对引擎标记的关键判定先完成结果停留，再进入原有战斗界面。战斗内的回合演出不变。

| 阶段 | 042b 时长 |
|---|---|
| 普通掷骰 / 无预览短版 | 最少 900ms / 600ms |
| 落定 / 数字淡入 | 120ms / 80ms |
| 合计出现至成败出现 | 200ms |
| 结果停留 | 1200ms |
| 自然 1 或关键失败震动 | 300ms，与结果停留重叠 |
| 快速普通 / 短版总时长 | 2500ms / 2200ms |
| 慢响应返回后的演出 | 1600ms |

托盘、两次弹跳、持续等待翻滚、跳过和减少动态效果沿用原有规则；没有增加原有时长上限。

所有位图内容与上一轮相同，没有生图或新依赖。7 张运行素材仍共 **400,094 字节**，默认预加载的 B01、B 裂纹和托盘合计 **175,418 字节**。

| 用途 | 路径 | 字节 |
|---|---|---:|
| B01 原图 | `assets/candidates/042/originals/dice_ruby_01.png` | 1,719,975 |
| B01 规范 PNG | `assets/candidates/042/dice_ruby_01.png` | 318,898 |
| 默认骰子 | `client/images/dice_ruby.webp` | 58,768 |
| B 裂纹原图 | `assets/candidates/042/originals/dice_ruby_cracked.png` | 1,803,196 |
| B 裂纹规范 PNG | `assets/candidates/042/dice_ruby_cracked.png` | 343,385 |
| 裂纹骰子 | `client/images/dice_ruby_cracked.webp` | 62,342 |
| 托盘 | `client/images/dice_tray.webp` | 54,308 |

验收目录已更新为 19 张 PNG 与 [checks.json](screens/042/checks.json)。包含桌面 / 手机的结果、优势双骰、自然 20、自然 1、关键判定确认卡、普通关键失败、结束游戏风险、下落阶段，以及减少动态效果、真实引擎战斗转场和三材质总览。

重点入口：[单骰](screens/042/result.png)、[优势双骰](screens/042/advantage.png)、[大成功](screens/042/critical-success.png)、[大失败](screens/042/critical-failure.png)、[普通关键失败](screens/042/crucial-failure.png)、[真实战斗转场](screens/042/crucial-combat-transition-mobile.png)、[三材质总览](screens/042/dice-sheet.png)。手机版本为相应的 `-mobile.png`。

2. **改动的文件**

| 文件 | 改动 |
|---|---|
| `assets/manifest.json` | B01 / B 裂纹批准与默认路径 |
| `client/app.js` | 风险提示、两位数字、关键失败类、战斗转场前保留结果 |
| `client/index.html` | 风险提示元素和可访问说明、B 图片预加载、缓存键 `20261019-dice-visual-b` |
| `client/styles.css` | 三材质数字参数、默认 B、关键失败裂纹与震动 |
| `host/state.py` | 由失败效果推导关键性，写入公开 check 和实际骰子结果 |
| `host/free_actions.py` | 自由观察判定传递关键性；未改 prompt 字符串 |
| `scripts/dice_visual_assets.py` | 重打包保留设计批准与默认选择 |
| `scripts/screenshot_dice_visual.py`、`.mjs` | 数字几何检查、新结果截图和真实引擎转场夹具 |
| `tests/test_player_dice_roll.py`、`tests/test_checks_v2.py` | 引擎风险、条件分支、目的地、实际失败转场、结束游戏、自由观察回归 |
| `tests/player_dice_roll.test.js` | 风险提示、普通关键失败、双骰、禁用极值、跳过、减少动态效果与原时长 |
| `tests/test_dice_visual_assets.py` | 精确核验批准记录与默认路径 |
| `eval/reports/screens/042/`、本报告 | 更新截图和验收记录 |

3. **验证结果**

| 命令 / 检查 | 输出摘要 |
|---|---|
| `python -m unittest discover -s tests -q` | **Ran 666 tests in 239.306s；OK (skipped=1)**，退出码 0 |
| `node --check client/app.js` | 通过，退出码 0 |
| `node tests/player_dice_roll.test.js` | **25 项通过，0 失败** |
| `python -X utf8 -m unittest tests.test_player_dice_roll tests.test_dice_visual_assets tests.test_checks_v2 -q` | **29 项通过** |
| `node --check scripts/screenshot_dice_visual.mjs` | 通过 |
| `python -X utf8 -m scripts.screenshot_dice_visual --output .codex-runs/042b/screens-final` | **44 项浏览器检查通过，19 张截图，browserErrors 为空**；已复制到要求目录 |
| 调用 `scripts.dice_visual_assets.main()`，比较运行前后 manifest、catalog 与全部素材哈希 | **10 candidates; 7 runtime sprites; 400094 bytes; PNG originals preserved**；批准、理由、默认路径、catalog 与全部 27 个素材哈希均不变 |
| 与 HEAD 比较 manifest 非 042 的图片记录和批次 | 完全一致 |
| `git diff --check` | 通过 |

浏览器检查使用 1280×800 和 390×844。三种材质各在 112px 与 160px 骰子上检查全部 1–20 点，共 120 组数字边界：四角均落在正面三角形内，中心与三角形重心误差不超过 0.3px，字号比例符合要求。另验证选中骰的震动、弃用骰无裂纹、自然极值禁用、真实引擎返回战斗后先停留结果再切屏。已目视复核主要桌面、手机结果与总览。

默认测试没有调用真实模型或付费 API；日志中的 quota_exhausted 等来自既有模拟用例。唯一跳过项仍为既有 `BALANCE_ENFORCE=1` 专用检查。Chromium 在沙箱内未能启动，随后通过获准的本地执行完成，截图脚本禁用外网，仅访问离线回环服务。

4. **TODO(design) 清单**

- TODO(design): 复核更新截图中的三种材质数字凹刻观感，以及 B 默认材质的普通 / 双骰 / 极值结果。
- TODO(design): 复核新增风险小字、普通关键失败裂纹与轻微震动。B01 和 B 裂纹选图已按明确决定批准，无需再次选图。

5. **推断清单**

- 同一选图的原图、规范 PNG 和运行 WebP 同步批准；批次中仍有未选图，批次整体 `approved` 继续为 false。
- 三角形顶点按现有 512px PNG 测量：A 为 (259,101)、(123,338)、(387,339)；B 为 (254,99)、(126,316)、(379,316)；C 为 (255,108)、(123,332)、(385,331)。重心百分比四舍五入到一位小数，字号按各面高度计算。阴影深度、透明比例和字距是落实 brief 的工程参数，视觉效果待复核。
- 除指定的 `crucial` 外增加 `crucial_reason` 区分两种已指定文案；同值写入骰子日志以支持无预览短版和结算后的场景变化，不公开失败效果或结局标识。
- 关键性按当前状态实际选中的普通失败分支计算；同时考虑失败时照常执行的公共 `effects`。仅成功分支或仅自然 1 专属分支的效果，不把普通判定标为关键。
- 同时存在战斗和 game_over 时优先显示「失敗すると危険」。目的地判定复用现有世界迁移和遭遇配置，包括地点 / 场景别名、失败效果设置的旗标、敌人变体、自动开战、已击败敌人和当前战斗阻止标记；不会仅因地点名称或叙事出现战斗字样就标记。
- `critical_enabled: false` 只禁用自然极值效果。brief 新增的关键失败裂纹独立执行，并保留原有跳过 / 减少动态效果规则。
- 延续上一轮的 300ms 裂纹震动，和 1200ms 结果停留重叠；关键判定引发的战斗界面等演出结束再呈现，后端结算不延迟。
- 保留并更新三材质总览和原有下落截图，额外提供风险确认卡、结束游戏风险和真实引擎战斗转场截图，以便设计验收。除真实转场夹具外，视觉截图使用合成判定结果。

6. **偏离 spec 的地方及原因**

没有偏离 042b brief。相对原 042 的“只换外观”和“自然 1 使用裂纹”，本次引擎公开关键性及扩大裂纹触发条件来自 042b 的明确要求。素材打包保留批准状态用于避免再次执行原工具时撤销此次定稿。

7. **已知问题**

- 新数字与风险演出的最终视觉验收仍由设计负责人完成；当前没有已知功能失败。
- 浏览器验收覆盖本机 Chromium；截图是指定采样时点，连续动效另由浏览器阶段检查和可控时钟测试验证。
- 开工前已有 `assets/candidates/argon-trial/` 和四份 006 本地模型报告，原样保留，未纳入本次提交。
