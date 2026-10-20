# 046b 人类试玩遥测

存档：`e2b9fdd9631c441298685da5d75d6cfb`。原始字段先列如下；缺失量保留 null。

| 字段 | 类型 | 条目数 |
|---|---|---:|
| id | str | None |
| scenario_path | str | None |
| scenario_title | str | None |
| gm_mode | str | None |
| scenario_pack | dict | 24 |
| world_state | dict | 2 |
| character | dict | 18 |
| messages | list | 155 |
| system_logs | list | 222 |
| event_log | list | 240 |
| dice_log | list | 14 |
| choices | list | 0 |
| flags | dict | 98 |
| companion | dict | 9 |
| game_over | dict | 5 |
| last_action_result | dict | 11 |
| last_turn_narrated | bool | None |
| combat | NoneType | None |
| area_snapshots | dict | 8 |
| retry_count | int | None |
| last_combat_result | dict | 11 |
| next_dice_type | str | None |
| next_dice_dc | int | None |
| needs_opening | bool | None |
| created_at | str | None |
| updated_at | str | None |
| visited_locations | list | 43 |
| known_item_names | list | 36 |
| completed_milestones | list | 4 |
| llm_worker_key_slot | dict | 1 |
| opening_effects_applied | bool | None |
| last_intent_resolution | dict | 8 |
| shop_stock | dict | 1 |
| scene_changes | dict | 2 |

| 遭遇 | 类别 | 回合 | 结束 HP | 行动记录 |
|---|---|---:|---|---|
| dark_forest_loc | trash | None | 17/20 | missing |
| goblin_fort | trash | None | 20/20 | missing |
| goblin_fort_second_right | elite | None | 20/20 | missing |
| goblin_fort_fourth | boss | None | 30/30 | missing |
| slime_ambush_one | trash | 2 | 30/30 | missing |
| slime_ambush_two | trash | 3 | 28/30 | missing |
| slime_king_battle | boss | 9 | 20/30 | missing |
| cave_heat_corridor | elite | 5 | 18/30 | missing |
| cave_lava_room | elite | 5 | 11/30 | missing |
| cave_prism_tree | boss | 26 | 26/30 | missing |
| forest_wolves | elite | 2 | 30/30 | missing |
| village_fire_slime | trash | 4 | 35/35 | missing |
| ice_elemental_encounter | elite | 2 | 27/35 | missing |
| frost_wolf_battle | boss | 3 | 35/35 | missing |
| valley_entrance | elite | 2 | 35/35 | missing |
| dragon_valley_loc | boss | 20 | 29/40 | missing |
| mansion_corridor | elite | 4 | 40/40 | missing |

判定：10/14；失败代价无法完整关联。
金币：可观察收入 806G，支出 100G，最终 706G。
回复：{"obtained_observed": {"薬草": 9, "治療の巻物": 9}, "removed_observed": {}, "used": null, "reason": "移除不等于使用，且日志可能截断。", "final_healing_hp": 340.0}
配装变更可观察到 2 次。
休息：[{"action": "rest_at_elf_spring", "created_at": "2026-10-20T07:00:05.839213+00:00", "evidence": "exact_user_choice", "location": "elf_spring"}, {"action": "rest_at_elf_spring", "created_at": "2026-10-20T07:00:57.490326+00:00", "evidence": "action_resolved", "location": "elf_spring"}, {"action": "rest_at_elf_spring", "created_at": "2026-10-20T07:04:44.470807+00:00", "evidence": "action_resolved", "location": "elf_spring"}]

| 准备 | 全程已获得 | 目标战前持有 | 可观察使用（全程） | 目标战使用 |
|---|---|---|---|---|
| ruby_charm | True | True | True | True |
| adamantite_armor | True | False | True | False |
| purification | True | False | None | None |
| ice_iron_greatsword | True | True | False | False |
| fire_bat_dragon | True | None | None | None |
| fire_bat_empowered | True | None | True | None |

Boss 开战 HP/库存回复/等级：

{
  "goblin_fort_fourth": {
    "hp": 20,
    "max_hp": 20,
    "healing_hp": null,
    "level": null,
    "inventory": null,
    "evidence": "reconstructed_from_previous_resolution_and_resource_events",
    "reason": "非开战直接快照；按可观察流水重建，未记录的变化不可排除。"
  },
  "slime_king_battle": {
    "hp": 28,
    "max_hp": 30,
    "healing_hp": 288.0,
    "level": 3,
    "inventory": [
      {
        "name": "鉄の剣",
        "quantity": 1
      },
      {
        "name": "革の鎧",
        "quantity": 1
      },
      {
        "name": "薬草",
        "quantity": 10
      },
      {
        "name": "携帯食",
        "quantity": 2
      },
      {
        "name": "聖水",
        "quantity": 1
      },
      {
        "name": "氷の護符",
        "quantity": 1
      },
      {
        "name": "旅の治療薬",
        "quantity": 1
      },
      {
        "name": "治療の巻物",
        "quantity": 6
      },
      {
        "name": "スライムの核",
        "quantity": 3
      },
      {
        "name": "ゴブリンの飾り物",
        "quantity": 5
      },
      {
        "name": "生命の果実",
        "quantity": 1
      },
      {
        "name": "刻印のハンマー",
        "quantity": 1
      },
      {
        "name": "剛力の霊薬",
        "quantity": 1
      }
    ],
    "evidence": "reconstructed_from_previous_resolution_and_resource_events",
    "reason": "非开战直接快照；按可观察流水重建，未记录的变化不可排除。"
  },
  "cave_prism_tree": {
    "hp": 11,
    "max_hp": 30,
    "healing_hp": 278.0,
    "level": 3,
    "inventory": [
      {
        "name": "鉄の剣",
        "quantity": 1
      },
      {
        "name": "革の鎧",
        "quantity": 1
      },
      {
        "name": "薬草",
        "quantity": 9
      },
      {
        "name": "携帯食",
        "quantity": 2
      },
      {
        "name": "氷の護符",
        "quantity": 1
      },
      {
        "name": "旅の治療薬",
        "quantity": 1
      },
      {
        "name": "治療の巻物",
        "quantity": 6
      },
      {
        "name": "スライムの核",
        "quantity": 5
      },
      {
        "name": "ゴブリンの飾り物",
        "quantity": 5
      },
      {
        "name": "生命の果実",
        "quantity": 2
      },
      {
        "name": "刻印のハンマー",
        "quantity": 1
      },
      {
        "name": "剛力の霊薬",
        "quantity": 1
      },
      {
        "name": "錆びた王冠",
        "quantity": 1
      },
      {
        "name": "鉄壁の霊薬",
        "quantity": 1
      },
      {
        "name": "光苔",
        "quantity": 1
      },
      {
        "name": "残り火の欠片",
        "quantity": 5
      },
      {
        "name": "焼けた溶岩石",
        "quantity": 1
      },
      {
        "name": "火球術の巻物",
        "quantity": 2
      },
      {
        "name": "紅玉の護符",
        "quantity": 1
      }
    ],
    "evidence": "reconstructed_from_previous_resolution_and_resource_events",
    "reason": "非开战直接快照；按可观察流水重建，未记录的变化不可排除。"
  },
  "frost_wolf_battle": {
    "hp": 27,
    "max_hp": 35,
    "healing_hp": 310.0,
    "level": 4,
    "inventory": [
      {
        "name": "鉄の剣",
        "quantity": 1
      },
      {
        "name": "革の鎧",
        "quantity": 1
      },
      {
        "name": "薬草",
        "quantity": 7
      },
      {
        "name": "携帯食",
        "quantity": 2
      },
      {
        "name": "氷の護符",
        "quantity": 1
      },
      {
        "name": "治療の巻物",
        "quantity": 8
      },
      {
        "name": "スライムの核",
        "quantity": 5
      },
      {
        "name": "ゴブリンの飾り物",
        "quantity": 5
      },
      {
        "name": "生命の果実",
        "quantity": 3
      },
      {
        "name": "刻印のハンマー",
        "quantity": 1
      },
      {
        "name": "剛力の霊薬",
        "quantity": 1
      },
      {
        "name": "錆びた王冠",
        "quantity": 1
      },
      {
        "name": "鉄壁の霊薬",
        "quantity": 1
      },
      {
        "name": "光苔",
        "quantity": 1
      },
      {
        "name": "残り火の欠片",
        "quantity": 6
      },
      {
        "name": "焼けた溶岩石",
        "quantity": 1
      },
      {
        "name": "火球術の巻物",
        "quantity": 1
      },
      {
        "name": "紅玉の護符",
        "quantity": 1
      },
      {
        "name": "虹晶の欠片",
        "quantity": 1
      },
      {
        "name": "叡智の霊薬",
        "quantity": 1
      },
      {
        "name": "色水晶の欠片",
        "quantity": 2
      },
      {
        "name": "精霊の泉の水",
        "quantity": 1
      },
      {
        "name": "獣の毛皮",
        "quantity": 1
      },
      {
        "name": "氷の結晶",
        "quantity": 1
      },
      {
        "name": "魔力の果実",
        "quantity": 1
      },
      {
        "name": "霜の欠片",
        "quantity": 1
      }
    ],
    "evidence": "reconstructed_from_previous_resolution_and_resource_events",
    "reason": "非开战直接快照；按可观察流水重建，未记录的变化不可排除。"
  },
  "dragon_valley_loc": {
    "hp": 40,
    "max_hp": 40,
    "healing_hp": 310.0,
    "level": 5,
    "inventory": [
      {
        "name": "鉄の剣",
        "quantity": 1
      },
      {
        "name": "革の鎧",
        "quantity": 1
      },
      {
        "name": "薬草",
        "quantity": 7
      },
      {
        "name": "携帯食",
        "quantity": 2
      },
      {
        "name": "氷の護符",
        "quantity": 1
      },
      {
        "name": "治療の巻物",
        "quantity": 8
      },
      {
        "name": "スライムの核",
        "quantity": 5
      },
      {
        "name": "ゴブリンの飾り物",
        "quantity": 5
      },
      {
        "name": "生命の果実",
        "quantity": 3
      },
      {
        "name": "刻印のハンマー",
        "quantity": 1
      },
      {
        "name": "剛力の霊薬",
        "quantity": 1
      },
      {
        "name": "錆びた王冠",
        "quantity": 1
      },
      {
        "name": "鉄壁の霊薬",
        "quantity": 1
      },
      {
        "name": "光苔",
        "quantity": 1
      },
      {
        "name": "残り火の欠片",
        "quantity": 6
      },
      {
        "name": "焼けた溶岩石",
        "quantity": 1
      },
      {
        "name": "火球術の巻物",
        "quantity": 1
      },
      {
        "name": "紅玉の護符",
        "quantity": 1
      },
      {
        "name": "虹晶の欠片",
        "quantity": 1
      },
      {
        "name": "叡智の霊薬",
        "quantity": 1
      },
      {
        "name": "色水晶の欠片",
        "quantity": 2
      },
      {
        "name": "精霊の泉の水",
        "quantity": 1
      },
      {
        "name": "獣の毛皮",
        "quantity": 1
      },
      {
        "name": "氷の結晶",
        "quantity": 1
      },
      {
        "name": "魔力の果実",
        "quantity": 2
      },
      {
        "name": "霜の欠片",
        "quantity": 3
      },
      {
        "name": "白い竜鱗",
        "quantity": 1
      },
      {
        "name": "迅速の霊薬",
        "quantity": 1
      },
      {
        "name": "氷鉄の大剣",
        "quantity": 1
      },
      {
        "name": "煤の精",
        "quantity": 2
      }
    ],
    "evidence": "reconstructed_from_previous_resolution_and_resource_events",
    "reason": "非开战直接快照；按可观察流水重建，未记录的变化不可排除。"
  }
}

| 原型 | 职业 | 通关率 |
|---|---|---:|
| P0a | hero | 0.0% |
| P0b | hero | 50.2% |
| P1 | hero | 52.0% |
| P2 | hero | 16.8% |
| P3 | hero | 2.0% |
| P2s | hero | 20.0% |
| P0g | hero | 50.2% |

最接近 P2（提案）：按可观察支线行为归类；洞窟/砦超过 P0b 的三次交互预算，未完成全部准备链。
这只比较行为，不能把这一局的胜利替代原型的抽样通关率。

需要引擎侧补记录：

- combat_id 关联的完整战斗开始/结束快照、遭遇 ID、类别和等级；event_log 当前会截断。
- 逐回合玩家行动 ID、目标、消耗、伤害/回复，以及状态/冷却；recent_events 只有末尾文本。
- 道具移除的原因（使用、交易或剧情交付）及其 action_id/combat_id；移除不能直接算回复使用。
- 带 action_id 的完整判定和其失败资源变化/后续战斗关联；dice_log 本身没有地点或 action_id。
- 完整配装/同伴/休息流水，以及准备项在具体战斗中生效的记录。
- 存档所用引擎版本及剧本指纹；区域回退快照不是某场 Boss 的开战快照。
