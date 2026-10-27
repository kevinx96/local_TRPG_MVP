# 相关工作（草稿）

> 草稿（2026-10-27）。供论文新结构的第 2 节使用。所有文献都已在线核实（见文末「核实记录」），BibTeX 见 `docs/research/refs.bib`，引用键写在方括号里。文中提到的本文章节号沿用 `paper-draft.md` v1 的编号（插入本节后需整体顺延）。

---

## 引言用的定位段落（2–3 句）

已有的 LLM GM 研究大多关注叙述质量或给 GM 的辅助，即使引入外部游戏状态，也通常让模型直接调用会改写状态的函数 [song2024labyrinth; zhu2023fireball]；而智能体安全领域虽然已经提出"让 LLM 只做动作选择"的设计模式 [beurerkellner2025patterns; debenedetti2025camel]，却没有在玩家本人就是潜在"攻击者"的游戏场景里，量化"合法但违背玩家意图"的误触发。本文把这两条线放在一起：在一个确定性引擎持有全部状态、LLM 只从引擎枚举的 ID 中做选择的日语 TRPG 里，用按严重度分级的 benchmark 区分"什么都没执行"的安全失败与"执行了玩家没要的动作"的有害失败，并报告约束解码、schema 形状和动作列表设计如何在这两者之间移动错误。

---

## 2 相关工作

### 2.1 交互式小说与 LLM 游戏主持人

**文字游戏环境。** Jericho [hausknecht2020jericho] 把经典交互式小说（IF）游戏包装成强化学习环境，并提供基于模板的动作空间和"有效动作"检测。经典 IF 本来就是"解析器 + 持有状态的引擎"：解析器把玩家文本映射到引擎认识的动词和对象，引擎决定结果。本文的架构在结构上就是这一传统，只是把手写解析器换成了 LLM，并让引擎在每一回合枚举当前合法的候选 ID。因此，"引擎持有状态"本身不是新思路，我们的贡献在于测量 LLM 作为解析器时出错的形态（第 5、6 节）。LIGHT [urbanek2019light] 在众包构建的奇幻文字冒险世界里研究智能体如何同时说话和行动，关注的是让模型学会生成有依据的对话和动作；本文不训练模型，而是用固定的商用模型和本地模型，研究在推理时如何约束其输出。

**D&D 与 LLM GM。** Callison-Burch 等 [callisonburch2022dnd] 把 D&D 表述为对话系统的挑战，提出"生成下一轮对话"和"从对话历史预测游戏状态"两个任务，并检验状态追踪能否提高生成的合理性。FIREBALL [zhu2023fireball] 从 Discord 上用 Avrae 机器人进行的约 2.5 万局游戏中收集了带结构化状态的数据，表明加入状态信息能改善生成，且语言模型（尤其微调后）能生成可执行的 Avrae 命令。这两项工作与本文同样认为"状态应当显式存在于模型之外"；区别在于，它们关心的是模型能否**预测或生成**状态与命令，而本文禁止模型写入状态，只评测它在引擎枚举的候选中**选择**的准确性和危害性。FIREBALL 的"生成可执行命令"与我们的 plan 很接近，但它的命令空间是开放的 Avrae 语法，引擎不对候选做逐回合枚举，也没有区分误触发的严重度。CALYPSO [zhu2023calypso] 让 LLM 作为人类 DM 的助手（理解遭遇、头脑风暴），模型的输出由人类 DM 筛选后才进入游戏；本文面向单人游玩，没有人类 DM 做过滤，这正是需要由引擎承担裁定的原因。

**带外部状态或规则系统的 LLM GM。** 与本文最接近的是三项工作。(1) Song 等 [song2024labyrinth] 在《Labyrinth》TRPG 中把游戏状态放在模型外部的 Python 对象里，给 LLM 提供掷骰函数和状态函数（如 `create_npc`、`add_item`），人类评价和 30 个单元测试显示叙述质量和状态更新的一致性都有提升。与之相比，本文的模型**不能**直接调用改写状态的函数（例如不能"添加物品"），只能选择引擎列出的动作或操作，效果由引擎决定；这也是我们所有实验中 S4（非法状态变化）都为 0 的原因（第 6.6 节）。代价是自由度更低：Song 等的模型可以创造新 NPC，我们的模型不能。(2) PANGeA [buongiorno2024pangea] 在回合制 RPG 中加入一个"验证系统"，用 LLM 根据设计者的规则评估玩家的自由文本，以防内容越出叙事范围。它的守门仍由 LLM 完成，属于提示词层面的约束；本文第 6.3 节的结果（提示词约束 guard_claims 让补充集 S3 从 12% 升到 14%，而从动作列表中隐藏未解锁动作降到 2%）提示，对"玩家自称满足条件"这类输入，把约束放在数据结构上可能比让 LLM 判断更可靠。不过，两者的任务和数据不同，不能直接比较数字。(3) Góngora 等 [gongora2026worldstate] 提出一种神经符号的互动叙事架构：LLM 处理自由文本，但只用来预测规则系统中的状态变化，再由系统触发预先编写的世界状态转换；8 名参与者在两个场景（英语、西班牙语）中的探索性研究显示世界状态保持一致。**这项工作与本文的核心架构高度相似**（LLM 只预测、规则系统执行预定义的转换），且时间更早（2026-05），本文不能声称"引擎裁定架构"本身是新的。本文与它的区别在于：评测对象是日语、486 条按句式家族隔离的审定 benchmark，而不是小规模用户研究；我们按严重度区分安全失败与有害误触发，并考察约束解码、schema 形状和推理后端对这一区分的影响。

**自动化试玩。** 用智能体代替人类做自动化试玩已有较长历史，例如 Holmgård 等 [holmgard2019playtesting] 用进化出的启发式驱动 MCTS，构造具有不同游玩风格的"程序化人格"作为合成试玩者。本文第 6.7 节的离线全流程探索远比这简单（优先选择未尝试的选项，战斗用平衡模拟的启发式），并不是方法上的贡献。我们想说明的只是一个推论：因为裁定完全由引擎完成，基于 LLM 的 GM 游戏也能使用这类零成本、可重复的自动化试玩；如果模型直接改写状态，同样的测试就必须调用模型，结果也不再确定。

### 2.2 结构化生成与约束解码

**约束解码的实现。** Outlines [willard2023outlines] 把正则表达式和上下文无关文法编译成有限状态机，在每一步解码时屏蔽不合法的词元。XGrammar [dong2025xgrammar] 把词元分为可预先检查的"上下文无关"词元和需要运行时检查的词元，从而加速基于 CFG 的约束解码。SGLang [zheng2024sglang] 是结构化 LM 程序的执行系统，其运行时用压缩有限状态机加速结构化输出的解码。llama.cpp 提供 GBNF 文法格式，并能把 JSON Schema 转换成 GBNF [llamacpp]。本文第 5.3 节的本地模型实验通过 llama.cpp 后端使用 JSON Schema 约束；我们没有提出新的解码算法，只是这些工具的用户。值得注意的是，llama.cpp 的文档本身列出了 JSON Schema 转换的已知限制（例如嵌套 `$ref` 不可用、同一类型里混用 `properties` 与 `anyOf`/`oneOf` 不受支持）[llamacpp]，因此"某个 schema 在某后端可用"必须对具体写法逐一确认。

**约束是否有代价。** Geng 等 [geng2023gcd] 表明，文法约束解码（包括依赖输入的文法）可以在不微调的情况下提升信息抽取、实体消歧和成分句法分析等结构化任务的表现，常常优于无约束模型。Tam 等 [tam2024speak] 则发现，要求 LLM 以 JSON、XML 等格式输出会明显降低其推理表现，约束越严，下降越大。Park 等 [park2024gad] 从理论上说明，文法约束解码会扭曲模型的输出分布：输出合乎文法，但其概率与模型在该约束下的条件分布不成比例，并提出了近似纠正的采样算法。本文第 6.1 节的发现与后两项工作的方向一致，但关注的维度不同：Tam 等测量的是**准确率**的下降，而我们关心的是**错误的危害性**。在严格解析下，格式不合法的输出被拒绝、什么都不执行（S2，安全失败）；约束解码消除了这类输出，qwen 系模型的 InvalidPlan 从 100% 降到 0%，S0+S1 升到 33–36%，S3（有害误触发）却从 0% 升到 15–21%。也就是说，约束解码并没有让模型"更懂"，而是把原本会被安全拒绝的错误理解变成了合法、会被执行的动作。Park 等描述的分布扭曲可能是机制之一（模型被迫在自己不倾向的结构里"填满"字段），但本文没有检验这个解释。我们认为本文的增量在于：在有安全后果的场景里，只报告格式合规率或准确率会把这种转移误读为进步，需要一个把"什么都没做"和"做错了"分开的严重度指标。

**不同后端对 JSON Schema 的支持差异。** JSONSchemaBench [geng2025jsonschemabench] 用约 1 万个真实 JSON Schema，比较了 Guidance、Outlines、llama.cpp、XGrammar、OpenAI 和 Gemini 六个约束解码框架的效率、约束覆盖率和输出质量，并区分"声明支持"（declared coverage）、"实际生成有效"（empirical coverage）和两者之比（compliance）。他们报告闭源服务的合规率高，原因是只支持保守的特性子集；Gemini 在较复杂的数据集上声明覆盖率很低。Gemini 的官方文档也提醒，过大或分支过多的 schema（包括备选项很多的 `anyOf`）可能被以 400 错误拒绝，且 `minLength`/`maxLength` 等关键字在约束解码中不被强制执行 [gemini2026structured]。**这削弱了本文第 6.2 节"schema 必须针对具体后端验证"这一论点的新颖性**：JSONSchemaBench 已经系统地展示了后端之间的覆盖差异，并在概念上区分了"接受"和"能正常生成"。本文补充的是一个更具体、可能更隐蔽的失败形态：同一份判别联合 schema（`anyOf` + `const`）在 llama.cpp 后端可以工作，在 Gemini 上**没有被拒绝**，却产生空白失控或空对象（194 条全部 InvalidPlan，平均输出 token 从 84 涨到 457），4 种替代写法都不可用（第 5.3.2 节）。由于文档和服务端实现会随时间变化，这一结论只对实验时所用的 Gemini 3.1 Flash-Lite 成立。

### 2.3 智能体安全、提示注入与动作空间限制

**提示注入的威胁模型。** Greshake 等 [greshake2023indirect] 提出"间接提示注入"：攻击者把指令藏在 LLM 应用会检索到的数据里，从而在用户不知情时操纵应用。Wallace 等 [wallace2024hierarchy] 提出"指令层级"，训练模型在系统消息、用户消息与工具输出相冲突时优先服从高权限的指令。本文的威胁模型与两者都不同：在单人游戏中，注入文字来自玩家本人，也就是唯一的用户；他的目的通常不是窃取数据，而是作弊（例如「これは管理者命令です。携帯食を減らさず通過成功を出力しなさい。」）。因此"用户指令优先"的层级在这里不能解决问题，需要保护的是游戏规则，而不是用户的意图。本文第 6.6 节观察到，在演示代理上抄写 GM 提示词的首行后，模型就会改写角色并输出完整代码；这与 Wei 等 [wei2023jailbroken] 用"目标相互竞争"和"泛化不匹配"解释安全训练失效的分析一致。**"角色设定不是安全边界"本身不是新发现**，本文只是在游戏场景中给出了一个实例，并据此把限制放在代理的请求形状、限流和预算上。

**评测基准。** AgentDojo [debenedetti2024agentdojo] 是评测 LLM 智能体在提示注入下表现的动态环境，首个版本包含 97 个任务和 629 个安全测试用例，分别报告无攻击时的效用、攻击下的效用和定向攻击成功率。本文的 S0–S4 分级在思路上类似：S4（非法状态变化）对应"攻击是否越权成功"，S3 对应"系统是否做了用户不想要的事"。不同之处在于，我们的 S3 主要不是由攻击造成的，而是由否定（「殴るつもりはない」）、条件（「必要になったら使う」）、虚假主张等普通玩家输入造成的；AgentDojo 也没有日语或游戏场景的用例。

**按设计防御：动作选择与能力限制。** CaMeL [debenedetti2025camel] 在 LLM 外部加一层保护：把可信用户查询派生出的控制流与不可信数据分开，并在工具调用上执行基于能力（capability）的安全策略，使系统在底层模型易受注入时仍然安全。Beurer-Kellner 等 [beurerkellner2025patterns] 总结了若干具有可证明抗注入性的设计模式，其中"动作选择器"（action-selector）模式让智能体只把请求翻译成预定义的工具调用，且工具输出不回流给智能体；"先计划后执行"模式要求在处理不可信数据之前固定动作序列。**本文的引擎裁定架构基本上就是动作选择器模式在 TRPG 中的一个实例**：LLM 只把玩家输入翻译成引擎预先定义的动作或操作，结果文本不回流到同一回合的选择中。因此，"注入无法改动数值"（S4 = 0）应当被表述为该模式的已知性质在本场景中的确认，而不是新的安全结论。本文在此基础上增加的是：这些模式保证的是"不会越权"，但不保证"选对了合法动作"；我们的 S3 恰好测量这一残余风险，并显示它对提示词、schema 和动作列表的设计都敏感。

**从候选集合中移除，而不是在提示词里禁止。** 第 6.3 节的发现（把未解锁的秘密动作从 planner 的动作列表中隐藏，比提示词约束更能防止"自称有证据"一类的误触发）与强化学习中的"无效动作屏蔽"相呼应。Huang 与 Ontañón [huang2022masking] 证明，在策略梯度方法中屏蔽无效动作仍然得到有效的策略梯度，并且在无效动作增多时，屏蔽比"对无效动作给负奖励"扩展得更好。它与 CaMeL 的能力限制都体现了同一个原则：让不该发生的选择在结构上不可选，而不是要求模型自觉回避。**这一原则不是本文首创**。本文的增量在于：(1) 在 LLM planner 上给出了直接对照——同一失败类别下，提示词约束（evidence_claim 的 S3 从 5/8 变为 6/8）与从列表中移除（降为 0/8）的效果相反；(2) 指出了 LLM 场景特有的一个机制：即使标为 `enabled: false` 并附上原因，列表中的候选仍会作为与输入语义高度匹配的选项吸引模型；(3) 隐藏还同时解决了剧情泄露问题。需要强调，这一对照只基于 50 条补充集中的 8 条用例、单次采样，证据很弱（第 7 节局限 1）。

**域外请求、澄清与拒答。** Larson 等 [larson2019oos] 构建了同时包含域内意图和域外（out-of-scope）查询的意图分类评测数据集，表明识别域外请求对现有分类器很困难。本文 plan 中的 `unsupported` 与 `clarify` 分别对应"域外/不可执行"和"需要澄清"，E7 的游戏外请求规则也属于域外处理；但我们的候选集合随游戏状态逐回合变化，同一句话在不同快照下可能可执行，也可能不可执行，这与固定意图集合的分类不同。Rahmani 等 [rahmani2023clarification] 综述了对话系统中"提出澄清问题"的数据集和评测方法，Wen 等 [wen2025abstention] 从查询、模型和人类价值三个角度综述了 LLM 的拒答（abstention）。本文的 S2 等级（InvalidPlan、不必要的澄清）可以看作一种"拒答"：它不推进游戏，但也不造成损失。把 InvalidPlan 计为无害、把 S3 单独计数，本质上是在评测中给"拒答"和"答错"不同的代价，这与拒答研究中的选择性预测思路一致，并非本文独创；第 8 节计划的"按置信度阈值转为 clarify"也属于这一方向。

---

## 新颖性风险（供设计负责人判断）

1. **引擎裁定架构本身**：经典 IF 的"解析器 + 引擎"结构、Góngora 等 [gongora2026worldstate] 的"LLM 只预测状态变化、系统执行预定义转换"、Beurer-Kellner 等 [beurerkellner2025patterns] 的动作选择器模式，都已覆盖这一思路。贡献 1 宜改写为"在日语 TRPG 中实现并测量该架构"，不宜写成提出新架构。Góngora 等 2026 是最需要在正文中正面比较的工作。
2. **S4 = 0**：由动作选择器模式的已知性质直接推出，应表述为确认，而不是发现。
3. **第 6.2 节（后端差异）**：JSONSchemaBench [geng2025jsonschemabench] 已系统展示后端差异，并区分声明支持与实际生成；本文只能声称一个具体失败案例（被接受但退化生成）。
4. **第 6.3 节（隐藏动作优于提示词约束）**：原则上与无效动作屏蔽 [huang2022masking]、能力限制 [debenedetti2025camel] 一致；本文的价值在于 LLM 场景下的直接对照和"disabled 候选仍有吸引力"这一观察，但样本只有 8 条。
5. **第 6.6 节（角色设定不是安全边界）**：越狱研究 [wei2023jailbroken] 已有充分讨论，本文只是实例。
6. **第 6.7 节（零 LLM 自动试玩）**：自动化试玩是成熟领域 [holmgard2019playtesting]，只能作为架构的推论来写。
7. **第 6.1 节（约束解码把格式错误变成有害误触发）**：Tam 等 [tam2024speak] 和 Park 等 [park2024gad] 已指出约束解码有代价，但据本次检索，没有找到在"安全失败 vs 有害执行"这一维度上测量该代价的工作。这是相对最站得住的一点，但检索范围有限（主要检索英文文献），不能排除遗漏。
8. **日语意图 benchmark**：本次检索没有找到公开的、带严重度标注的日语 TRPG 意图 benchmark；找到一篇言語処理学会 2025 年年会关于 LLM 多智能体 TRPG GM 的论文，但未能可靠提取其标题和作者，未纳入（见核实记录）。投稿前建议再查一次 NLP 年会和 JSAI 的论文集。

---

## 核实记录

核实日期 2026-10-27。"verified"表示在列出的页面上确认了标题、作者、年份和出处；"corrected"表示审稿人给出的信息或常见引法有误，已按核实结果修正；"dropped"表示未纳入。

### 审稿人建议的文献

| 文献 | 核实的 URL | 状态 |
|---|---|---|
| Hausknecht et al. 2020, Jericho | https://arxiv.org/abs/1909.05398 ; https://ojs.aaai.org/index.php/AAAI/article/view/6297 ; Crossref 10.1609/aaai.v34i05.6297 | verified（补充：论文标题为 "Interactive Fiction Games: A Colossal Adventure"，Jericho 是其中的环境名；AAAI 2020，34(05):7903–7910） |
| Urbanek et al. 2019, LIGHT | https://arxiv.org/abs/1903.03094 ; https://aclanthology.org/D19-1062/ | verified（EMNLP-IJCNLP 2019，pp. 673–683） |
| Zhu et al. 2023, CALYPSO (AIIDE) | https://arxiv.org/abs/2308.07540 ; Crossref 10.1609/aiide.v19i1.27534 | corrected：标题细节。arXiv 版为 "Dungeon Masters' Assistants"，AIIDE 正式版为 "Dungeon Master's Assistants"，按正式版引用；AIIDE 19(1):380–390 |
| Callison-Burch et al. 2022, D&D as a Dialog Challenge | https://arxiv.org/abs/2210.07109 ; https://aclanthology.org/2022.emnlp-main.637/ | verified（EMNLP 2022，pp. 9379–9393） |
| 近年 AIIDE/CoG/FDG 的神经符号或带规则引擎的 LLM GM 工作 | 见下表新增文献 | 部分完成：找到并核实 PANGeA（AIIDE 2024）、FIREBALL（ACL 2023）、Song et al.（ACL 2024 Wordplay 研讨会）、Góngora et al.（ICCC 2026）；**没有找到可核实的 CoG 或 FDG 2023–2025 的同类论文**，未凭印象补充 |
| Willard & Louf 2023, Outlines | https://arxiv.org/abs/2307.09702 | verified（仅 arXiv 预印本，无正式出处，按 @misc 引用） |
| XGrammar (Dong et al. 2024) | https://arxiv.org/abs/2411.15100 ; https://mlsys.org/virtual/2025/3235 | corrected：arXiv 首发于 2024-11，正式发表于 **MLSys 2025**，按 Dong et al. 2025 引用；另外 arXiv v3 与 MLSys 页面的作者顺序不同（Ruihang Lai 分别排第 4 和第 6），按 MLSys 页面 |
| SGLang (Zheng et al. 2024) | https://arxiv.org/abs/2312.07104 ; https://proceedings.neurips.cc/paper_files/paper/2024/hash/724be4472168f31ba1c9ac630f15dec8-Abstract.html | verified（arXiv 首发于 2023-12；正式出处 NeurIPS 2024，pp. 62557–62583；Zheng et al. 2024 正确） |
| llama.cpp GBNF（软件引用） | https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md | verified（作为软件文档引用；仓库所有者为 ggml-org；无对应论文） |
| Tam et al. 2024, "Let Me Speak Freely?" | https://arxiv.org/abs/2408.02442 ; https://aclanthology.org/2024.emnlp-industry.91/ | verified（补充出处：EMNLP 2024 Industry Track，pp. 1218–1236；Anthology 标题的大小写与 arXiv 不同） |
| Geng et al. 2023, grammar-constrained decoding | https://arxiv.org/abs/2305.13971 ; https://aclanthology.org/2023.emnlp-main.674 | verified（EMNLP 2023，pp. 10932–10952） |
| 不同推理后端对 JSON Schema 支持差异的工作 | https://arxiv.org/abs/2501.10868 ; https://arxiv.org/html/2501.10868v3 ; https://ai.google.dev/gemini-api/docs/structured-output | 新增：JSONSchemaBench（Geng et al. 2025，仅 arXiv）和 Gemini 官方文档（注明访问日期） |
| Greshake et al. 2023, indirect prompt injection | https://arxiv.org/abs/2302.12173 ; Crossref 10.1145/3605764.3623985 | verified（补充出处：AISec '23，pp. 79–90） |
| Wallace et al. 2024, Instruction Hierarchy | https://arxiv.org/abs/2404.13208 | verified（仅 arXiv 预印本，未查到正式出处） |
| Debenedetti et al. 2024, AgentDojo | https://arxiv.org/abs/2406.13352 ; https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract.html | verified（NeurIPS 2024 Datasets and Benchmarks Track，pp. 82895–82920） |
| Debenedetti et al. 2025, CaMeL | https://arxiv.org/abs/2503.18813 | verified（论文标题为 "Defeating Prompt Injections by Design"，CaMeL 是系统名；仅 arXiv） |
| Larson et al. 2019, out-of-scope intent | https://aclanthology.org/D19-1131/ | verified（EMNLP-IJCNLP 2019，pp. 1311–1316） |
| 任务型对话中的澄清与拒答 | https://aclanthology.org/2023.acl-long.152/ ; https://aclanthology.org/2025.tacl-1.26/ | 新增：Rahmani et al. 2023（ACL 2023）、Wen et al. 2025（TACL 13） |

### 自行补充的文献

| 文献 | 核实的 URL | 状态 |
|---|---|---|
| Zhu et al. 2023, FIREBALL | https://arxiv.org/abs/2305.01528 ; Crossref 10.18653/v1/2023.acl-long.229 | verified（ACL 2023，pp. 4171–4193） |
| Song, Zhu & Callison-Burch 2024, Labyrinth / function calling | https://arxiv.org/abs/2409.06949 ; https://arxiv.org/html/2409.06949v1 | verified（arXiv；注释为 Wordplay Workshop @ ACL 2024，ACL Anthology 中未查到条目，故按 arXiv 引用） |
| Buongiorno et al. 2024, PANGeA | https://ojs.aaai.org/index.php/AIIDE/article/view/31876 ; Crossref 10.1609/aiide.v20i1.31876 | verified（AIIDE 20(1):156–166） |
| Góngora et al. 2026, World-State Transformations | https://arxiv.org/abs/2605.24719 | verified（arXiv 2026-05；注释为 ICCC'26 待发表，论文集页码未核实） |
| Holmgård et al. 2019, automated playtesting | https://arxiv.org/abs/1802.06881 ; Crossref 10.1109/TG.2018.2808198 | verified（IEEE Transactions on Games 11(4):352–362） |
| Park et al. 2024, Grammar-Aligned Decoding | https://proceedings.neurips.cc/paper_files/paper/2024/hash/2bdc2267c3d7d01523e2e17ac0a754f3-Abstract.html ; Crossref 10.52202/079017-0774 | verified（NeurIPS 2024，pp. 24547–24568） |
| Geng et al. 2025, JSONSchemaBench | https://arxiv.org/abs/2501.10868 | verified（仅 arXiv） |
| Google, Gemini structured output 文档 | https://ai.google.dev/gemini-api/docs/structured-output | verified（官方文档，访问于 2026-10-27；内容可能与实验时不同） |
| Beurer-Kellner et al. 2025, Design Patterns | https://arxiv.org/abs/2506.08837 ; https://arxiv.org/html/2506.08837v3 | verified（仅 arXiv） |
| Wei et al. 2023, Jailbroken | https://neurips.cc/virtual/2023/poster/70702 ; Crossref 10.52202/075280-3508 | verified（NeurIPS 2023，pp. 80079–80110） |
| Huang & Ontañón 2022, invalid action masking | https://arxiv.org/abs/2006.14171 ; Crossref 10.32473/flairs.v35i.130584 | verified（FLAIRS 35, 2022） |
| Côté et al. 2018/2019, TextWorld | https://arxiv.org/abs/1806.11532 ; Crossref 10.1007/978-3-030-24337-1_3 | dropped：已核实，但与 Jericho 作用重复，为控制篇幅未纳入 |
| Fang et al. 2024, LLMs Are Neurosymbolic Reasoners (AAAI) | https://arxiv.org/abs/2401.09334 ; Crossref 10.1609/aaai.v38i16.29754 | dropped：已核实，但研究对象是 LLM 作为玩家智能体，与 GM 相关性弱 |
| Góngora et al. 2023, Skill Check (GALA 2023) | https://arxiv.org/abs/2309.13702 | dropped：只核实了 arXiv 注释中的会议名，未核实正式论文集信息；内容为 GM 模型评测的考量，相关性一般 |
| Beurer-Kellner et al. 2024, DOMINO | https://arxiv.org/abs/2403.06988 | dropped：arXiv 页面未列出正式出处，未能核实会议信息 |
| Liang et al. 2023, Tachikuma | https://arxiv.org/abs/2307.12573 | dropped：初步版本（"preliminary version of an ongoing work"），数据语言未能确认 |
| 言語処理学会第 31 回年次大会 P10-17（LLM 多智能体 TRPG GM） | https://www.anlp.jp/proceedings/annual_meeting/2025/pdf_dir/P10-17.pdf | dropped：PDF 文本抽取乱码，无法可靠确认标题和作者；它是最接近的日语工作，建议人工打开核实后再决定是否引用 |
| Peng et al. 2024, Player-Driven Emergence (CoG 2024) | https://arxiv.org/abs/2404.17027（仅检索结果） | dropped：只在检索结果中看到 "accepted at CoG 2024"，未打开页面核实；且研究的是叙事涌现，与本文相关性弱 |
