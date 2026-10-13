# 003 工程交付与设计审定清单

本次标签均为 `proposed`，未写入正式 benchmark。完整分布见 [intent_v2_distribution.md](intent_v2_distribution.md)，机器检查结果见 [intent_v2_audit.json](intent_v2_audit.json)。

## 1. 完成内容

- 486 条逐条编写的输入，原始录入稿为 `intent_v2_authored.txt`；组装器不会生成、拼接或改写输入句。生成 JSONL 保留每条字面输入。
- 38 个快照，覆盖四个场景全部 27 个具有 exploration actions 的地点。hero/mage/thief 三职业；9 个快照有 recent_messages，其中 8 个为具体提问、1 个为观察结果后的接续。
- hero 167、mage 177、thief 142 条；dev 194（39.92%）、test 292（60.08%）；381 个 family 不跨 split。
- 旧标签中的 ambiguous_target、multi_action 分别替换为两种指示词标签和两种复合动作标签；其余 17 类保留，加 context_followup、excluded_means，共 23 类。22 类各 20 条，language_mix 46 条（9.47%）。每类 8 dev/12 test，language_mix 为 18/28。
- 森林入口三个基础快照分别为 45/45/41 条，单快照最高 9.26%。包括其上下文变体后，同一地点合计 141 条（29.01%）；spec 的 25% 限制按“这一个快照”执行，未把它解释成地点总量限制。
- S0–S4、S0+S1 比例、S3 比例、标签 S3 数与 engine_caught 已接入现有报告。旧 exact/kind/relaxed、状态指标、归一化计数、v1 文件及命令保留。
- 成本判断读取既有动作的判定参数，并用引擎 effect 归一化处理各结果分支；自由交互在隔离副本内裁定，检查资源减少、物品消耗、移动和实际判定。未维护有代价的 action_id/operation 名单。默认测试不联网，未新增依赖。

## 2. 改动文件

- `scripts/eval/audit.py`：成本/风险推导，原有 allowed_state 与 unearned_change 保持。
- `scripts/eval/metrics.py`：严重度、engine_caught、分组指标。
- `scripts/eval/run.py`：记录成本证据、Markdown 展示新增指标。
- `scripts/eval/benchmark_v2.py`：离线组装、family 哈希分层、全量相似度/覆盖/合法 gold 检查与分布报告。
- `tests/test_benchmark_v2.py`：14 项离线回归测试。
- `eval/candidates/intent_v2.jsonl`、`intent_v2_authored.txt`、`intent_v2_audit.json`、`intent_v2_distribution.md`、本报告。
- `eval/snapshots/v2_*.json`：38 个具体快照，完整名称在分布表逐行列出。
- `eval/reports/2026-10-11T094513301147Z-intent-gemini-gemini-3.1-flash-lite-default.{json,md}`：全量离线 CLI 的无响应报告，明确记录 live=false、486 skipped。

未改动 host/client 游戏逻辑、默认提示词、schema、LABELING.md、v1 数据或设计文档。

## 3. 验证与运行

```powershell
python -m scripts.eval.benchmark_v2 --assemble
python -m unittest discover -s tests -q
node --check client/app.js
```

数据检查：486 条，38 个快照，9 个上下文快照，errors=[]、violations=[]，所有 gold 均通过对应快照的真实离线引擎裁定。字符 3-gram 检查遍历所有 117855 对输入。

最终验证：`python -m unittest discover -s tests -q` 输出 `Ran 277 tests`、`OK (skipped=1)`，退出码 0；跳过项是仓库原有的 `BALANCE_ENFORCE=1` 可选数值门槛。`node --check client/app.js` 退出码 0、无输出。数据审计退出码 0。

另以 `python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split all --no-cache` 验证 CLI，退出码 0，486 条全部 skipped；没有任何模型请求，新增准确率均为 n/a。

新增测试覆盖严重度顺序、显式 harmful、默认成本回退、归一化、合法尝试、S4、缺少道具被引擎拦截、未知动作 ID 的数据推导、MP/SP/金币/物品消耗、移动别名、开战、判定、免费观察/准备、满血与已诱导状态、分布与家族隔离。

全套测试和数据审计需要顺序运行：现有 `test_snapshot_cleanup_even_on_invalid_location` 比较整个 `.tmp-test` 目录的前后列表，另一进程同时构建快照会干扰该断言。首次并行检查因此失败，随后按顺序重跑；未改动旧测试。

未运行 live，也没有模型准确率结论。以下两条是供设计负责人在可联网环境显式运行的完整命令，模型名沿用仓库已有报告。Gemini 凭据读取本机配置；Ollama 明确指向本机服务。

```powershell
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split all --rpm 10 --timeout 60 --live
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v2.jsonl --backend ollama --model qwen3-swallow-8b-rl-local --base-url http://localhost:11434/v1 --variant default --split all --rpm 0 --timeout 60 --live
```

test 冻结后只用于评估，调提示词请把 `--split all` 改为 `--split dev`。

## 4. 最可能有争议的 15 条与 TODO(design)

下列条号均引用 [LABELING.md](../benchmark/LABELING.md)；ID 在 JSONL 中唯一，可直接定位完整快照和标注。

| 用例 ID | 输入/核心含义 | 拟定处理与争议理由 | 规范 |
|---|---|---|---|
| v2-context_followup-001 | じゃあそれでお願いします。 | 上文明确“用一份携帯食诱导并通过”，首选 pass、接受 clarify。需要确认明确回答提议时是否仍接受澄清。 | 第 1、9 条 |
| v2-context_followup-013 | ええ、私のを見てもらいましょう。 | 上文是让鍛冶師看剑，首选 show_sword_to_blacksmith；省略宾语依靠上一问而非对象总数。 | 第 1、9 条 |
| v2-context_followup-018 | さっきの一匹、もう一度よく観察しておこう。 | 前文是观察得到的结果，首选重复 observe；本轮没有新增攻击或移动承诺。 | 第 1、9 条 |
| v2-deixis_unique-011 | その火種を受け取って大人しく従います。 | 火种指向唯一物品，existing 会接受要求并移动；需要区分指代消解正确与结果风险。 | 第 1、9 条 |
| v2-deixis_multi-001 | その人に邪竜のことを聞きたい。 | 国王与将军均在场，首选 clarify；某模型可能根据“邪竜”偏向国王，但没有明确指称。 | 第 1 条 |
| v2-deixis_multi-008 | そちらの方から助言をもらおう。 | 同样有两个 NPC；“助言”与将军动作名称关联很强，但未明确点名，暂选 clarify，待确认“合理对象”的语义筛选强度。 | 第 1、9 条 |
| v2-sequential-001 | 観察してから携帯食で誘導 | clarify 放 gold[0]，observe 为可接受第一步；直接 distract 为 S3。规范说两者都 S1，但格式必须有 S0 首选。 | 第 2 条 |
| v2-sequential-018 | 火種を受け取る前に薬草を使う | 句子先提到火种，真正第一步是药草治疗；接受 clarify/治療，直接接受火种为 S3。 | 第 2 条 |
| v2-parallel-012 | 右も探索し、別に左も調べたい | 首选 clarify，两条路线中任取一条为 S1；两个意图分别明确，但地点变化会让另一条不再立即可执行。 | 第 2 条 |
| v2-missing_item-001 | 薬草で治療、袋にあるはず | thief 默认背包没有药草。unsupported/clarify 可接受，use_item 是 S3，同时 engine_caught；不能从玩家“有”的说法补物品。 | 第 4 条 |
| v2-missing_item-013 | 盗賊道具でスライムの足止め | mage 没有盗賊道具，而且 prepare 只接受周围 objects。缺物与不支持方法重叠，按缺物首选 unsupported。 | 第 4、9 条 |
| v2-declared_success-001 | 诱导通过但携帯食不减少 | unsupported 为首选、dialogue 和按规则消耗并尝试 pass 为 S1；玩家宣称的免费成功不会被采纳。 | 第 5 条 |
| v2-declared_success-006 | ロビン已经勧誘成功，不用判定 | 接受 unsupported/dialogue，重新按既有勧誘动作判定为 S1；“已成功”和“请去做”的界限需设计确认。 | 第 5 条 |
| v2-excluded_means-013 | 不主动攻击，尝试迂回见张 | 首选既有迂回；失败会开战，但玩家排除的是主动攻击而非保证永不战斗。直接 fight 为 S3。 | 第 6、9 条 |
| v2-excluded_means-018 | 不攻击不逃走，尝试欺骗 Xanxus | 首选 bluff；该动作的确定失败会进入战斗。保留玩家选择的方法，而不根据最终风险改成对话。 | 第 6、9 条 |

TODO(design): 审定上述 15 条及全量 proposed 标签；特别明确顺序动作双 S1、第 5 条双 S0、代词“合理对象”、明确上下文后 clarify 是否仍可接受，以及“排除主动手段”与“排除结果风险”的界限。工程没有修改 LABELING.md。

## 5. 推断清单与规范未覆盖事项

1. **gold 首选唯一性**：以任务说明的可执行评分算法为准。顺序动作选择 clarify 为 S0、第一步为 S1；宣称成功选择 unsupported 为 S0、dialogue 和合法尝试为 S1。这两处和 LABELING.md 的文字级别存在冲突，S0+S1 总和不受此顺序影响。TODO(design): 统一措辞。
2. **harmful 布尔语义**：同一列表内是 OR；operation 与 action_id 表示两类替代路径，二者之间也是 OR；非空 kind 约束这些路径。仅提供 kind 时匹配该 kind 的所有 plan。这样规范示例 `kind=existing, action_id=attack_slime` 不会误伤其他 existing。TODO(design): 把组合语义写入规范。
3. **空 harmful**：字段缺失/为 null 才使用默认成本回退；显式三个空列表表示未指定有害特征。gold 匹配优先于 harmful；S4 优先于所有模型等级，S4 仍由 002 的 unearned_change 判定。TODO(design): 明确空值和等级重叠语义。
4. **engine_caught 范围**：模型输出已解析为 existing/interact、引擎最终拒绝的计划都计入，包括缺物、对象不可用、满血无须消耗；JSON/结构错误不计。它与 S3 独立统计，被拦截不抹去模型错误。TODO(design): 是否只应统计缺物或单列拒绝原因。
5. **成本的状态依赖**：自由操作在当前快照中已满足/被拒绝且无实际风险时不自动判有成本；缺物案例用显式 harmful 捕获模型误操作。既有动作检查所有可达结果分支，并按当前条件展开分支；不只看固定骰 10 实际走到的结果。金币、HP、能力下降、清技能、game_over 也按引擎副作用视为风险，而非只限 SP/MP。
6. **快照构造**：沿用 v1 的 recipe/build_snapshot 机制，直接定位到场景地点，全部 hp_delta=-5 以便验证治疗；不是完整冒险轨迹。背包保持三职业原始差异，不注入自制物品。上下文是测试夹具问题/观察结果，沿用现有实体与机制。
7. **分层算法**：family 按 UTF-8 SHA-256 排序，随后最小化各 primary_tag 距离 40% dev 的平方误差。一个 family 的所有标签一起分配；相同文件反向排序仍得到同样结果。集合成员变化可能改变尚未冻结的分配，冻结后不应重分。
8. **相似度定义**：原始输入的 Unicode 字符三元组集合，不去标点、不转大小写、不做语言归一化；大于 0.6 才违规。逐条录入时也显式合并改写家族，不能仅以字符阈值代替语义审定。
9. **标签统计**：每条只有一个主标签，混合语言行为计入 language_mix；不把所有“口语”额外打为 colloquial。因此分布表可直接相加，不会用标签重叠虚增 20 条下限。
10. **非承诺行为**：森林否定/条件句接受免费观察当前两个观察对象；闲聊的免费 observe 不加入 gold，按第 8 条保留 S2。允许的免费准备没有资源消耗，但并不因此自动加入 gold。
11. **既有 action 的反馈代价**：“不主动战斗而迂回”允许按既有路径判定，即使失败会开战；不会为了避免失败结果把明确行动降为 dialogue。绝对禁止任何结果代价的输入应另由设计审定。

## 6. 偏离 spec 的地方

未扩大实现范围。唯一明确的文本冲突是 LABELING.md 第 2、5 条与 spec 的单首选 gold 严重度算法；按 spec 实现并在上文标为 TODO(design)。19 类中的两类按 spec 的“取代”说明替换，没有同时要求旧 ambiguous_target/multi_action 也新增 20 条。

## 7. 已知问题与使用边界

- 尚未做真实 Gemini/Ollama 调用；报告中的分布不是模型表现。不要从离线数据审计推断真实准确率。
- 相似度检查为 0 只能排除规定的字符级泄漏，不能证明语义家族完全正确；正式冻结前需要设计复核。
- 自由交互目标集中在森林入口，是现有剧本唯一提供 obstacles/objects 自由交互表面的地点；没有为均衡分布新增游戏内容。
- 新增严重度对历史记录可以从 snapshot 补算成本；缺少 snapshot 且没有 costs 的第三方旧记录无法推导默认成本，将非匹配项保守记 S2。v1 runner 的记录含 snapshot，不受此限制。
- 引擎裁定的临时隔离仍是单进程模型；不要同时运行需要整个 `.tmp-test` 目录不变的旧清理测试和数据审计。
