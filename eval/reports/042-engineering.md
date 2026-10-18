# 042 工程汇报

1. **完成了什么**

已实现手绘 d20、托盘、衬线数字叠加、两次递减弹跳、随高度变化的椭圆阴影、等待服务器时持续翻滚、从当前角度落定，以及自然 20 光晕／自然 1 裂纹替换。优势／劣势沿用服务器提供的点数与 selected_index；未采用的骰子变暗并缩小。critical_enabled: false 时不触发极值效果。

使用内置 image_gen，完成 6 张正常候选、3 张裂纹变体和 1 张托盘。原图、规范 PNG、运行 WebP 共 27 条新增 manifest 登记，全部 approved: false。默认装入 spec 指定的 A01；B01／C01 另备压缩运行版，供 CSS 变量切换预览。真实提示词和编辑参照见 [generation.json](../../assets/candidates/042/generation.json)，未使用 CLI/API 回退。

总览：[dice-sheet.png](screens/042/dice-sheet.png)。每列包含一个材质的候选 01、02、裂纹版和使用游戏实际 CSS 叠加数字 17 的示意。另有桌面／手机 falling、result、critical-success、critical-failure，以及 reduced-motion-mobile，共 9 张截图；[浏览器检查记录](screens/042/checks.json)。

时长表中的 T：普通判定为 max(请求返回时刻, 起始时刻＋900ms)，短版为起始时刻＋600ms。短版从服务器返回后才开始。

| 阶段 | 时长／时点 |
|---|---|
| 托盘淡入 | 0–100ms |
| 从上方落下 | 约 108–240ms；最初 102ms 隐藏骰子 |
| 第一次弹跳 | 240–438ms；348ms 达到 23px 高点 |
| 第二次弹跳 | 438–600ms；510ms 达到 9px 高点 |
| 等待翻滚 | 600ms 起，每圈 720ms，无响应时无限循环 |
| 落定与摇晃 | T 至 T＋120ms，承接当前旋转矩阵、高度和阴影 |
| 自然点数淡入 | T＋120 至 T＋200ms；此前隐藏数字 |
| 修正／合计 | T＋200ms |
| DC／成败、极值效果 | T＋400ms；光晕扩散 650ms，裂纹震动 300ms |
| 结果停留 | 1200ms，T＋1600ms 收起 |
| 跳过 | 有响应时立即显结果；无响应时不伪造点数；再点击可收起 |
| 减少动态效果 | 响应后直接显结果，所有动画关闭，保留 1200ms 停留 |

快速普通判定合计 2500ms，短版 2200ms；慢响应返回后仍为 1600ms。落定 120ms＋淡入 80ms 共用 039 原有的第一段 200ms，没有增加总时长。

以下参数集中在 client/styles.css 的 .dice-check-card。120／80ms 两项由 app.js 同步设置，调整时须仍合计 200ms。

| CSS 变量 | 当前值／作用 |
|---|---|
| --dice-image、--dice-cracked-image | 正常／裂纹图 |
| --dice-ink | A：--red 与 --bg 混合暗红；B：--gold；C：--text |
| --dice-number-inset、--dice-number-highlight | 内凹感阴影和细高光，沿用已有配色 |
| --dice-size | 112px |
| --dice-drop-height | −64px |
| --dice-bounce-height、--dice-second-bounce-height | −23px、−9px |
| --dice-roll-height | −8px |
| --dice-drop-turn、--dice-roll-turn | −540deg、360deg |
| --dice-roll-period、--dice-entry-duration、--dice-tray-duration | 720ms、600ms、100ms |
| --dice-fast-blur | 1.1px |
| --dice-shadow-scale-air、--dice-shadow-scale-ground | 1.35、1 |
| --dice-shadow-opacity-air、--dice-shadow-opacity-ground | 0.12、0.55 |
| --dice-shadow-blur | 4px |
| --dice-settle-duration、--dice-number-duration | 120ms、80ms |

将判定卡 data-dice-material 设为 ruby 或 iron 可预览其变量组；默认是 A01。材质选择器只覆盖图片与颜色变量，没有新增游戏设置菜单。

2. **改动的文件**

| 文件 | 内容 |
|---|---|
| client/app.js | 隐藏翻滚数字、承接当前运动状态、落定／淡入；沿用原有跳过和停留 |
| client/index.html | 替换两颗 SVG，增加图片与阴影层；预加载默认三张图；CSS／JS 缓存键 20261019-dice-visual |
| client/styles.css | 材质、数字、托盘、弹跳、翻滚、阴影、双骰、极值与减少动态效果 |
| client/images/dice_*.webp | 7 张运行素材，共 **400,094 字节** |
| assets/candidates/042/ | 10 张规范 PNG、10 张原图和 generation.json |
| assets/manifest.json | 追加 042 登记与批次；旧数据逐字段比较不变 |
| scripts/dice_visual_assets.py | 离线缩放、压缩、alpha／容量检查与登记 |
| scripts/screenshot_dice_visual.py、.mjs | 离线截图、总览和实际 CSS 验证 |
| tests/player_dice_roll.test.js | 20 项流程测试，覆盖新阶段和时长 |
| tests/test_dice_visual_assets.py | 3 项素材测试，覆盖尺寸、alpha 格式、容量、引用、登记和哈希 |
| eval/reports/screens/042/、本文件 | 总览、截图、验收记录与汇报 |

下表 PNG 位于 assets/candidates/042/，原图位于该目录 originals/ 下的**同名文件**，WebP 位于 client/images/。9 张骰子 PNG 为 512×512，托盘为 800×400；原图分别为 1254×1254 和 1774×887。

| PNG 文件 | 规范 PNG（字节） | 原图 PNG（字节） | 运行 WebP 文件 | WebP（字节） |
|---|---:|---:|---|---:|
| `dice_bone_01.png` | 301,570 | 1,678,856 | `dice_bone.webp` | 50,100 |
| `dice_bone_02.png` | 308,024 | 1,774,813 | — | — |
| `dice_bone_cracked.png` | 330,181 | 1,800,364 | `dice_bone_cracked.webp` | 52,508 |
| `dice_ruby_01.png` | 318,898 | 1,719,975 | `dice_ruby.webp` | 58,768 |
| `dice_ruby_02.png` | 302,479 | 1,635,601 | — | — |
| `dice_ruby_cracked.png` | 343,385 | 1,803,196 | `dice_ruby_cracked.webp` | 62,342 |
| `dice_iron_01.png` | 340,507 | 2,093,442 | `dice_iron.webp` | 62,362 |
| `dice_iron_02.png` | 348,229 | 2,085,416 | — | — |
| `dice_iron_cracked.png` | 353,233 | 2,134,634 | `dice_iron_cracked.webp` | 59,706 |
| `dice_tray.png` | 400,251 | 2,132,972 | `dice_tray.webp` | 54,308 |

规范 PNG 共 3,346,757 字节，原图共 18,859,269 字节。所有图片 alpha 极值均为 [0,255]；WebP 保留透明 alpha。

没有新增游戏或默认测试依赖。素材工具使用已有 Pillow 11.2.1，延迟导入；缺少 Pillow 时，游戏和默认测试仍能运行。浏览器工具复用本机 Chromium、Node 和既有离线 HTTP handler。

3. **验证结果**

| 命令／检查 | 结果 |
|---|---|
| python -m unittest discover -s tests -q | **660 项，242.906 秒，OK (skipped=1)**，退出码 0 |
| node --check client/app.js | 退出码 0 |
| node tests/player_dice_roll.test.js | 20 项全部通过 |
| python -m unittest tests.test_dice_visual_assets tests.test_player_dice_roll -q | 12 项通过，0.597 秒，包含 JS 流程测试包装 |
| node --check scripts/screenshot_dice_visual.mjs | 退出码 0 |
| python -m scripts.dice_visual_assets | 10 candidates; 7 runtime sprites; 400094 bytes; PNG originals preserved |
| python -X utf8 -m scripts.screenshot_dice_visual --output .codex-runs/042/screens-final-2 | **30 项浏览器检查通过**，9 张截图及总览，已复制至要求目录 |
| git diff --check | 通过 |
| manifest 旧数据比较 | 排除本次追加项后与 HEAD 完全相同 |

浏览器覆盖 1280×800 和 390×844：托盘先出现、两次递减弹跳、离地阴影变淡、持续等待、落定角度连续、两骰落点分离、弃用骰变暗缩小、仅采用骰触发极值、critical_enabled: false、减少动态效果、无横向溢出。没有浏览器异常。默认测试与截图未调用真实游戏模型 API；quota_exhausted 等输出来自既有模拟用例。唯一跳过项是已有的 BALANCE_ENFORCE=1 专用检查。

4. **TODO(design) 清单**

- TODO(design): 决定最终材质与候选，验收裂纹、托盘和数字；当前全部未批准，A01 仅按 spec 临时装入。
- TODO(design): 在浏览器验收弹跳、转速、阴影、80ms 数字淡入和极值效果；参数已集中。
- TODO(design): 裂纹版均以候选 01 编辑；若选候选 02，确认是否需要重新生成匹配的裂纹版。
- TODO(design): 确认生成稿具体裂纹、磨损、木框与绒布细节，工程没有把它们定为新风格标准。

5. **推断清单**

- 1.5MB 按十进制 1,500,000 字节计算全部运行素材；保留的原图、规范 PNG 和评审截图不计入加载预算。
- 工具原生尺寸较大，保留原图并以 Lanczos 缩放；WebP 使用 quality=88、method=6。
- 裂纹版以各材质候选 01 直接编辑；B01／C01 同时提供运行版，便于只改变量预览。
- 圆盘按从上方看的透视投影画成横向椭圆，适配 800×400；具体深蓝绒布和暖棕木框由模型按“深色绒布＋木框”形成，待设计验收。
- 数字按正面三角重心在图片中心定位；选用本机 Georgia／Times New Roman 衬线体、粗体 900 和现有主题色。
- 原有第一段 200ms 分给落定 120ms、淡入 80ms；点数比旧实现晚出现 120ms，但修正、DC 和收起时点不变。极值效果沿用在 DC／成败出现时启动。
- 弹跳高度、转速、挤压比例、模糊、阴影范围、弃用骰缩至 0.86 倍等量值为工程首版参数，等待设计视觉验收。
- 选择 spec 允许的“翻滚隐藏数字”；无限等待翻滚不生成随机数，最终点数均来自服务器。
- 桌面／手机尺寸、三列总览和合成判定数据是验收工具选择；截图不是一次真实游戏流程记录。

6. **偏离 spec 的地方及原因**

没有判定规则、流程时长上限或交付范围上的偏离。生成尺寸经离线工具规范化，未经缩放的 PNG 原图一并保留。除默认 A01 外提供 B01／C01 运行版供变量预览，全部仍未批准。

7. **已知问题**

- 最终选图和视觉验收待设计负责人，工程不代替批准。
- Windows 沙箱内 Chromium 无法启动，经获准的本地环境完成。一次覆盖旧截图返回 Windows UNKNOWN 写入错误，改用新的仓库临时目录生成，再复制到交付目录解决，未跳过检查。
- 开工前已有 assets/candidates/argon-trial/ 和四份 006 本地模型报告，原样保留，不在本次提交中。
