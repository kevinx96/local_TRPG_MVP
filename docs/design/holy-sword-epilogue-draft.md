# 圣剑隐藏线结局与收尾（定稿草案）

来源：Antigravity argon medium 初稿（`.agy-runs/holy-sword-epilogue.md`，dispatch 试用六）。设计负责人决定：采用 E1、E2、V1、V2；**E3（铁匠反应）不采用**，因为它会和现有 `robert` 结局重复出场，铁匠死亡时还要另加屏蔽条件。

全部 `difficulty_only: ["normal"]`，两份剧本同步。

| 编号 | 条件 | 文本 |
|---|---|---|
| E1 | epilogue；`endings: ["draco_defeated", "draco_defeated_with_ignis"]`；`requirements: {"flag": "holy_sword_awakened"}` | 役目を終えた聖剣はまばゆい光を収め、再び質素な佇まいへと戻った。ただその刃には今も、確かな温もりが宿っている。 |
| E2 | epilogue；endings 同上；`requirements: {"all": [{"character_id": "hero"}, {"flag": "accepted_sword_fusion"}]}` | ドラコから取り戻された古びた剣は、異様な光を失い、見慣れた鉄の刃に戻った。今は鞘に収まり、静かに眠りについている。 |
| V1 | draco_battle 人形态被击破、转入竜形态之前的日志；条件同 E2 | 膝をついたドラコの手から、奪われた聖剣が滑り落ち、石床に澄んだ音を響かせた。 |
| V2 | 击败竜形态时，追加在 `result_texts.victory` 和 `draco_defeated` 的 `game_over.reason` 末尾；`requirements: {"flag": "holy_sword_awakened"}` | 盟約を乱す者を討った聖剣は、新たな誓いを見届けるように、澄んだ白光を放っていた。 |

## 设计记录

- V2 和 E1 会在同一个结局画面一前一后出现：V2 写终战当场在发光，E1 写战后光芒收敛。时间线是连贯的。
- V2 用「新たな誓い」，E1 只写剑本身，都没有重复 `draco_defeated` 主结局文和 `king_confession` 里的"盟约""使者"字眼。
- E2 和 `town_blood`（铁匠被杀）不冲突：E2 不写铁匠。
