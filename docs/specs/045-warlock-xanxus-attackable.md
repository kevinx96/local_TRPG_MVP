# 045 ワーロック与ザンザス解除保护

来源：用户（2026-10-19）：「ワーロック和ザンザス都解除吧，直接用现在有的数值和技能……玩家想自己作死应保留玩家可以作死的权利。」

设计全文与全部日文文本见 `docs/design/npc-combat-v1.md` 第 7 节，**文本照抄**。在 041 的 NPC 攻击框架上改，迁移脚本 `scripts/scenario/npc_combat.py` 保持幂等，两份剧本同步。

## 1. ワーロック
- `blue_robed_mage` 与 `warlock` 改为可杀、城镇人物；敌人数据由现有角色 `warlock` 的数值和技能生成（不调数值）。
- 魔法店里攻击ミーナ：去掉固定的"阻止"叙述，改为ワーロック作为守护者参战；他倒下后ミーナ在魔法店可单独被攻击。
- 后果按设计文档：商店关闭与柜台物品（钱箱 50G）、不能招募、所有依赖他的救场选项隐藏（`refuse_xanxus_with_rescue`、`call_warlock`、`warlock_rescue_available` 的来源）。逐一检查最後通告、竜の巣前的剩余选项能继续推进，列进汇报。

## 2. ザンザス
- 改为可杀、非城镇；在 `xanxus_confrontation`、`xanxus_ultimatum`、`xanxus_at_nest` 三处可被攻击，确认后用现有敌人 `xanxus` 战斗，**败北为普通死亡**（区域重来），不套用 `xanxus_battle` 的 scripted_loss。剧本原有选项不变。
- 胜利处理按设计文档：三处各自的去向、`defeated_xanxus` 与 `heard_xanxus_betrayal`、火种移除、之后不再进入ザンザス的场景（各处的进入条件都要检查，包括通往竜の巣前的路线）、尾声替换。

## 3. 模型侧
- 不改提示词。确认这两人出现在 npcs 上下文里时可以被选为 attack 目标。
- `eval/candidates/041-npc-attacks.jsonl` 的 027（「店主を攻撃する」魔法店）引擎结果现在应为 confirmation；新增 3 条候选：魔法店「ワーロックを攻撃する」、燃える街道「ザンザスに斬りかかる」、竜の巣前「ザンザスを攻撃する」，gold 为 attack 对应 ID，`label_status: design_reviewed_041`。不要联网跑评测（设计负责人会跑）。

## 4. 验收
- 单元测试：两人的攻击确认→开战；ワーロック守护ミーナ；他倒下后救场选项消失且最後通告/竜の巣前仍可推进；ザンザス三处胜利各自的去向、火种移除、旗标、尾声文本；败北是死亡而非 scripted_loss；迁移幂等。
- 离线通玩无异常、无非战斗死路（跑完恢复 `eval/reports/playtest-*`，不提交）。
- `python -m unittest discover -s tests -q`、`node --check client/app.js` 通过；冻结 benchmark 重放 194/194。提交（`[工程]` 前缀，只 add 具体文件）。如果沙箱写不了 `tests/` 或提交被拒，把补丁留在 `.tmp-test/045/` 并在汇报里说明。
