# E9 heldout_v3 登记的工具修正记录

本文件记录登记（preregistration）在工具阶段被重做的经过。所有重做都发生在 **任何 held-out 输入、标签、gold、模型结果出现之前**：99 个槽位始终是空槽位（input 为空、gold 为空），没有 cases.jsonl、LOCK.json、formal/ 或 previews/。评分版本 v1.2、默认系统提示词指纹、planner schema 指纹和运行参数在三次登记中完全相同。

## 第 0 次登记（工具验证期，已作废）

首次登记误把与 E9 无关的个人忽略脚本 host/auto_tagger.py（被 .gitignore 忽略、不在 git 里）纳入冻结清单。清单修正后重新登记。旧记录已在当时保留；其 preregistration.json 的 SHA-256 为
`e1b5775ee48f5ac24244f30201e301f7e2ae872aa1559a4223940387db8678fd`。

## 第 1 次登记（已被取代）

- 登记时 HEAD：`f9e35927696e5008b7f6babcd11f9934039e5bb5`；创建时间 2026-10-27T12:08:39Z
- preregistration.json 的 SHA-256（磁盘字节，CRLF）：`2949cbbe5a619357e15a419d9f0dd2439f1fe89a99c6d9eee7d6925fe31e47d1`；LF 归一化后 `9c65bab4885722683ae73ed7dcbe9e922a5c5c08e2f7dba06130794299a5a4e9`
- PREREGISTRATION.md 的 SHA-256（磁盘字节）：`357f5288d283ee08f9f4de6dacff0c7355983771d3e7115dd5b647a6d2a26878`；LF 归一化后 `83bef7ea68f9e57582ed38bbb001690474d10fdecf44fe07676203eeeb8be291`
- slots.jsonl 的 SHA-256（磁盘字节）：`3be51ff4f3f8437db138b6a6b011b3c46bb1558bed51879573bceedd9ce0026d`；LF 归一化后 `dcf830a7e484d1317253ec1d6609a18a13e9369a6bbcffeec00d6b87b3af68b3`
- 文件保存在 `.tmp-test/056/prereg-v1-superseded/`（本地，不入库），未删除。

## 第 2 次登记（本目录当前内容）

- 登记所依据的代码 commit：`0a1fdae10ee5e0b49166d2df59834fab8d640526`（`[工程] 056 paper experiment tools (E8 full-LLM baseline, E9 held-out, IAA)`）。冻结文件的哈希取自该 commit 的内容，登记时工作区与该 commit 一致（在干净的 worktree 里生成）。代码 commit 曾两次因 dev 前进而变基，登记随之在最终的 commit 上重新生成，变基前的登记从未推送。第二次变基纳入了 dev 上 052d 对 host/combat.py 的提交，因此 host/combat.py 的冻结哈希是 052d 提交后的版本（最后 commit a72e4dba，哈希 `50a386e1054a…`）。
- preregistration.json 的 SHA-256（LF 归一化）：`d8b9ea35a1344b693ef975bded09558c3b691abda444327d35044d46542d3e9f`
- PREREGISTRATION.md 的 SHA-256（LF 归一化）：`8f2010811edb7f7bd8f71fe6409a12e860b97c1815b047267782f04b71668d4d`
- slots.jsonl 的 SHA-256（LF 归一化，与第 1 次相同，仍是 99 个空槽位）：`dcf830a7e484d1317253ec1d6609a18a13e9369a6bbcffeec00d6b87b3af68b3`

## 为什么重做

1. E8 工具的公平性修正（scripts/eval/full_llm.py）：去掉提示词的【仮】前缀；给全状态 GM 加入动作效果；invalid_output 不计 S4；S4 拆为 unauthorized_change 和 magnitude_error。
2. 冻结清单更正：E9 正式运行（default 变体，经 run.evaluate_case）并不依赖 full_llm，把它从冻结清单中移除，使清单只含 E9 实际依赖的文件。（lock 阶段仍用 full_llm.legal_states 校验 gold 能被引擎接受，不参与评分。）
3. 哈希口径：文本文件按 LF 归一化后计算。第 1 次登记按磁盘字节计算，其中 18 个文件在 Windows CRLF 检出与仓库内容之间会得出不同哈希，这些文件的差异仅是换行符。
4. 第 1 次登记当时记录的是含 052d 未提交改动的 host/combat.py（`50a386e1054a…`）；第 2 次登记记录的是 dev 上已提交的版本（见上）；两者的哈希相同，因为 052d 随后把同一份改动提交了。另外 scripts/eval/heldout.py 本身因上述修改而变化。

评分 v1.2、默认系统提示词指纹（`0223af080e40…`）、planner schema 指纹（`51d05dc24701…`）、参数、槽位内容均未变。

## 之后的注意事项

- 冻结清单包含 host/ 下被 git 跟踪的 Python 文件。以后任何 host/*.py 的提交（例如 052d 对 host/combat.py 的提交，已纳入本次登记）都会让登记校验失败；若发生在 E9 输入／标签／结果出现之前，可由设计负责人批准重新登记；之后不得再改。
- 正式执行前跑 `python -m scripts.eval.heldout verify`（需先 lock），或用 `verify_registration` 检查登记。

## 预先声明的敏感性分析（2026-10-28，锁定前写入，此时尚无任何 E9 模型结果）

本节写于 cases.jsonl 审定之后、`lock` 和正式执行之前。写入时不存在 LOCK.json、formal/ 或 previews/，没有任何 held-out 模型输出。

1. **主结果**：E9 的主结果仍然报告全部 99 条（S0+S1 比例、S3 比例），不因本节改变。
2. **敏感性分析**：另外报告去掉 `v3-existing_exact-001` 和 `v3-existing_exact-003` 后 97 条的同一组指标。原因是这两条与 v2 不能做到语义家族隔离：它们的快照（v2_alley_after_thief、v2_alley_thief）各只有一个动作，其 UI 文本「城へ戻る」「城に戻る」就是 v2-existing_exact-008 和 v2-existing_exact-006 的输入，existing_exact 的任何写法都只能在同一文本外加包装。保留这两条是因为删除后 existing_exact 会低于预注册的每标签最少 3 条。97 条结果由正式运行的记录离线重算，不再调用模型。
3. **已知局限**：alley_after 和 alley_thief 两个快照都只有一个“回城”动作，因此 existing_paraphrase、colloquial、language_mix 在这两个快照上的 6 条目标是同一个动作，动作多样性偏低。这不是隔离失败，但在解读这些标签的分数时应注意。
