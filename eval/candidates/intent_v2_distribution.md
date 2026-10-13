# intent_v2 候选分布（离线）

由 `python -m scripts.eval.benchmark_v2 --assemble` 重建。标签尚未审定。
输入句均保存在 intent_v2_authored.txt 中；组装器只展开标注，不生成或改写句子。

总数 486；快照 38；上下文快照 9；字符 3-gram Jaccard > 0.6 的跨 family 违规 0。
句式家族 381；dev/test：{'dev': 194, 'test': 292}。

| 代号 | primary_tag | 数量 | dev | test |
|---|---|---:|---:|---:|
| T01 | existing_exact | 20 | 8 | 12 |
| T02 | existing_paraphrase | 20 | 8 | 12 |
| T03 | negation | 20 | 8 | 12 |
| T04 | conditional | 20 | 8 | 12 |
| T05 | interact_observe | 20 | 8 | 12 |
| T06 | interact_distract | 20 | 8 | 12 |
| T07 | interact_sneak | 20 | 8 | 12 |
| T08 | interact_prepare | 20 | 8 | 12 |
| T09 | interact_use_item | 20 | 8 | 12 |
| T10 | missing_item | 20 | 8 | 12 |
| T11 | dialogue | 20 | 8 | 12 |
| T12 | chitchat | 20 | 8 | 12 |
| T13 | impossible | 20 | 8 | 12 |
| T14 | declared_success | 20 | 8 | 12 |
| T15 | injection | 20 | 8 | 12 |
| T16 | colloquial | 20 | 8 | 12 |
| T17 | language_mix | 46 | 18 | 28 |
| T18 | context_followup | 20 | 8 | 12 |
| T19 | deixis_unique | 20 | 8 | 12 |
| T20 | deixis_multi | 20 | 8 | 12 |
| T21 | sequential | 20 | 8 | 12 |
| T22 | parallel | 20 | 8 | 12 |
| T23 | excluded_means | 20 | 8 | 12 |

标签一条一个；下表为完整快照 × 标签非零计数，未列出的组合均为 0。

| 快照 | 职业 | 场景 | 数量 | dev | test | 标签：数量 |
|---|---|---|---:|---:|---:|---|
| v2_alley_after_thief | thief | throne_room | 5 | 0 | 5 | T01:1, T02:1, T10:1, T16:1, T17:1 |
| v2_alley_night_mage | mage | throne_room | 15 | 5 | 10 | T01:1, T02:1, T04:1, T10:1, T11:2, T12:1, T13:1, T15:1, T16:1, T17:2, T19:1, T21:1, T22:1 |
| v2_alley_thief | thief | throne_room | 10 | 2 | 8 | T01:1, T02:1, T04:1, T10:1, T12:1, T13:1, T15:1, T16:1, T17:2 |
| v2_castle_hero | hero | throne_room | 21 | 9 | 12 | T01:1, T02:1, T03:1, T04:1, T09:1, T10:1, T11:2, T12:1, T13:1, T14:1, T15:1, T16:1, T17:2, T20:3, T21:1, T22:1, T23:1 |
| v2_context_cc | hero | throne_room | 2 | 1 | 1 | T18:2 |
| v2_context_cd | mage | village | 2 | 1 | 1 | T18:2 |
| v2_context_cf | hero | throne_room | 2 | 1 | 1 | T18:2 |
| v2_context_ch | hero | dark_forest | 4 | 2 | 2 | T17:1, T18:3 |
| v2_context_ci | mage | throne_room | 4 | 0 | 4 | T09:1, T17:1, T18:2 |
| v2_context_cj | hero | dark_forest | 2 | 2 | 0 | T18:2 |
| v2_context_cp | mage | dark_forest | 2 | 0 | 2 | T18:2 |
| v2_context_cr | hero | dark_forest | 2 | 2 | 0 | T18:2 |
| v2_context_cw | mage | dark_forest | 4 | 0 | 4 | T09:1, T18:3 |
| v2_dark_forest_loc_hero | hero | dark_forest | 45 | 21 | 24 | T03:1, T04:1, T05:7, T06:7, T07:7, T08:7, T09:1, T10:1, T12:1, T13:1, T14:1, T15:1, T17:2, T19:1, T20:2, T21:1, T22:1, T23:2 |
| v2_dark_forest_loc_mage | mage | dark_forest | 45 | 22 | 23 | T03:1, T04:1, T05:7, T06:7, T07:6, T08:7, T09:1, T10:1, T12:1, T13:1, T14:1, T15:1, T17:2, T19:2, T20:2, T21:1, T22:1, T23:2 |
| v2_dark_forest_loc_thief | thief | dark_forest | 41 | 16 | 25 | T03:1, T04:1, T05:6, T06:6, T07:7, T08:6, T10:1, T12:1, T13:1, T14:1, T15:1, T17:2, T19:2, T20:1, T21:1, T22:1, T23:2 |
| v2_dragon_valley_loc_hero | hero | dragon_valley | 16 | 8 | 8 | T01:1, T02:1, T03:1, T04:1, T09:1, T10:1, T12:1, T13:1, T14:1, T15:1, T17:2, T19:1, T21:1, T22:1, T23:1 |
| v2_elf_spring_mage | mage | dark_forest | 16 | 5 | 11 | T01:1, T02:1, T03:1, T04:1, T09:1, T10:1, T12:1, T13:1, T14:1, T15:1, T16:1, T17:2, T21:1, T22:1, T23:1 |
| v2_forest_exit_hero | hero | dark_forest | 8 | 0 | 8 | T01:1, T02:1, T04:1, T09:1, T12:1, T16:1, T17:1, T21:1 |
| v2_forge_hero | hero | throne_room | 21 | 13 | 8 | T01:1, T02:1, T03:1, T04:1, T09:1, T10:1, T11:2, T12:1, T13:1, T14:1, T15:1, T16:1, T17:2, T19:1, T20:2, T21:1, T22:1, T23:1 |
| v2_goblin_fort_chest_choice_thief | thief | dark_forest | 10 | 4 | 6 | T01:1, T02:1, T04:1, T10:1, T11:1, T14:1, T15:1, T16:1, T17:1, T19:1 |
| v2_goblin_fort_first_second_mage | mage | dark_forest | 11 | 4 | 7 | T01:1, T02:1, T03:1, T09:1, T13:1, T14:1, T16:1, T17:1, T19:1, T21:1, T23:1 |
| v2_goblin_fort_healing_circle_mage | mage | dark_forest | 10 | 3 | 7 | T01:1, T02:1, T09:1, T12:1, T14:1, T16:1, T17:1, T19:1, T22:1, T23:1 |
| v2_goblin_fort_second_choice_hero | hero | dark_forest | 16 | 2 | 14 | T01:1, T02:1, T03:1, T04:1, T09:1, T12:1, T13:1, T15:1, T16:1, T17:2, T20:2, T21:1, T22:1, T23:1 |
| v2_goblin_fort_second_right_thief | thief | dark_forest | 10 | 1 | 9 | T01:1, T02:1, T03:1, T10:1, T14:1, T16:1, T17:2, T19:1, T23:1 |
| v2_goblin_fort_thief | thief | dark_forest | 14 | 4 | 10 | T01:1, T02:1, T03:1, T04:1, T10:1, T12:1, T13:1, T14:1, T15:1, T16:1, T17:2, T19:1, T23:1 |
| v2_goblin_fort_third_gate_hero | hero | dark_forest | 10 | 7 | 3 | T01:1, T02:1, T03:1, T09:1, T13:1, T15:1, T16:1, T17:1, T21:1, T22:1 |
| v2_ian_ice_katana_aftermath_hero | hero | village | 6 | 3 | 3 | T09:1, T11:2, T17:1, T19:1, T22:1 |
| v2_ice_elemental_encounter_mage | mage | village | 12 | 6 | 6 | T03:1, T04:1, T09:1, T10:1, T12:1, T13:1, T14:1, T15:1, T17:1, T19:1, T21:1, T23:1 |
| v2_inn_mage | mage | throne_room | 21 | 7 | 14 | T01:1, T02:1, T03:1, T04:1, T09:1, T10:1, T11:2, T12:1, T13:1, T14:1, T15:1, T16:1, T17:2, T20:3, T21:1, T22:1, T23:1 |
| v2_item_shop_thief | thief | throne_room | 20 | 11 | 9 | T01:1, T02:1, T03:1, T04:1, T10:1, T11:2, T12:1, T13:1, T14:1, T15:1, T16:1, T17:2, T20:3, T21:1, T22:1, T23:1 |
| v2_lost_goblin_crossroads_thief | thief | dark_forest | 16 | 8 | 8 | T01:1, T02:1, T03:1, T04:1, T10:1, T11:1, T12:1, T13:1, T14:1, T15:1, T16:1, T17:2, T19:1, T21:1, T22:1 |
| v2_magic_shop_mage | mage | throne_room | 21 | 6 | 15 | T01:1, T02:1, T03:1, T04:1, T09:1, T10:1, T11:2, T12:1, T13:1, T14:1, T15:1, T16:1, T17:2, T19:1, T20:2, T21:1, T22:1, T23:1 |
| v2_village_approach_thief | thief | village | 9 | 5 | 4 | T03:1, T04:1, T10:1, T12:1, T13:1, T14:1, T15:1, T16:1, T17:1 |
| v2_village_frozen_clue_thief | thief | village | 7 | 3 | 4 | T03:1, T10:1, T12:1, T14:1, T16:1, T17:1, T22:1 |
| v2_village_mage | mage | village | 9 | 4 | 5 | T01:1, T02:1, T09:1, T11:2, T17:1, T19:1, T21:1, T22:1 |
| v2_xanxus_confrontation_hero | hero | village | 12 | 3 | 9 | T03:1, T04:1, T09:1, T11:1, T13:1, T14:1, T15:1, T17:1, T19:1, T21:1, T22:1, T23:1 |
| v2_xanxus_ultimatum_mage | mage | village | 5 | 3 | 2 | T09:1, T11:1, T19:1, T21:1, T22:1 |

| 职业 | 数量 |
|---|---:|
| hero | 167 |
| mage | 177 |
| thief | 142 |

| 场景 | 数量 |
|---|---:|
| throne_room | 142 |
| dark_forest | 266 |
| village | 62 |
| dragon_valley | 16 |

| split | 数量 |
|---|---:|
| dev | 194 |
| test | 292 |
