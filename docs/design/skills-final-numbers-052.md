# 052c3 normal 技能与被动实际数值

从最终 normal 有效包导出。仅供写作线核对；本轮未修改说明文字。数值字段保留引擎名称，倍率均为实际总倍率。

| 职业 | 类型 / 等级或阶 | 名称 / ID | 实际结算参数 |
|---|---|---|---|
| hero | 初期技能 1 | 渾身斬り / power_slash | `{"id":"power_slash","kind":"attack","damage":"1d10+str/2","dice_type":"1d10+str/2","accuracy":85,"element":"physical","cost":3,"cost_type":"sp"}` |
| hero | 初期技能 1 | 神聖の庇護 / divine_guard | `{"id":"divine_guard","kind":"defend","guard_multiplier":0.5,"survive_at_one":true,"cost":0,"cooldown":1}` |
| cleric | 初期技能 1 | 治癒の祈り / healing_prayer | `{"id":"healing_prayer","kind":"heal","healing":"1d6+int/4","dice_type":"1d6+int/4","cost":4,"cost_type":"mp"}` |
| cleric | 初期技能 1 | 聖なる守護 / holy_guard | `{"id":"holy_guard","kind":"defend","guard_multiplier":0.5,"survive_at_one":true,"cost":6,"cost_type":"mp"}` |
| mage | 初期技能 1 | 火球 / fireball | `{"id":"fireball","kind":"attack","damage":"1d6+int/2","dice_type":"1d6+int/2","accuracy":90,"element":"fire","cost":5,"cost_type":"mp","conditional_bonus":[{"if":"target_hp_full","damage":"1d6"}],"spell_tier":"basic"}` |
| mage | 初期技能 1 | 氷の矢 / ice_arrow | `{"id":"ice_arrow","kind":"attack","damage":"1d6+int/2","dice_type":"1d6+int/2","accuracy":92,"element":"ice","cost":3,"cost_type":"mp","conditional_bonus":[{"if":"target_hp_ratio_lte","ratio":0.5,"damage":"1d6"}],"spell_tier":"basic"}` |
| thief | 初期技能 1 | 影隠れ / hide_in_shadow | `{"id":"hide_in_shadow","kind":"defend","guard_multiplier":0.25,"dice_type":"1d20+dex","cost":2,"cost_type":"sp","cooldown":1}` |
| thief | 初期技能 1 | 急所突き / vital_strike | `{"id":"vital_strike","kind":"attack","damage":"3d6","dice_type":"3d6","accuracy":82,"element":"physical","cost":4,"cost_type":"sp"}` |
| warlock | 初期技能 1 | 元素克制 / element_counter | `{"id":"element_counter","kind":"attack","damage":"int+10d20","accuracy":100,"element":"counter"}` |
| warlock | 初期技能 1 | 元素切替 / element_switch | `{"id":"element_switch","kind":"stance","immunity_from_target_element":true}` |
| warlock | 初期技能 1 | 元素祈喚 / element_prayer | `{"id":"element_prayer","kind":"attack","damage":"3d24","accuracy":100,"multi_elements":["wind","fire","water","lightning","ice","earth","light","dark"],"hits_per_element":3}` |
| hero | 主动 3 | 聖光の剣技 / holy_sword_art | `{"id":"holy_sword_art","cost":2,"cost_type":"mp","kind":"attack","damage":"1d6+str/4","accuracy":92,"multi_elements":["physical","holy"],"hits_per_element":1,"self_status":"holy_blessing"}` |
| hero | 主动 5 | 薙ぎ払い / sweep | `{"id":"sweep","cost":3,"cost_type":"sp","kind":"attack","damage":"1d6+str/4","accuracy":90,"element":"physical","all_targets":true,"conditional_multipliers":[{"if":"single_enemy","x":1.8}]}` |
| hero | 主动 7 | 竜断ちの一太刀 / dragon_slash | `{"id":"dragon_slash","cost":0,"cost_type":"mp","costs":{"sp":7,"mp":5},"kind":"attack","damage":"2d10+str/2+5","accuracy":100,"element":"physical","ignores_defense":true,"ignores_resistance":true,"conditional_multipliers":[{"if":"any","conditions":[{"if":"target_boss"},{"if":"target_id_in","ids":["ignis","draco_dragon","dragon_knight_mounted","lava_drake"]},{"if":"target_max_hp_gte","value":80}],"x":1.35}]}` |
| hero | 被动 1 | 旅立ちの気概 / departure_spirit | `{"opening_rounds":1,"opening_sp":3}` |
| hero | 被动 2 | 旅立ちの気概 / departure_spirit | `{"opening_rounds":2,"opening_sp":3}` |
| hero | 被动 1 | 重装の心得 / heavy_armor_lore | `{"armor_min":1,"armor_bonus":1}` |
| hero | 被动 1 | 不沈の盾 / unsinkable_shield | `{"skill_overrides":{"divine_guard":{"free_action":true,"cooldown":2}}}` |
| hero | 被动 1 | 追い打ちの剣 / sword_followup | `{"hit_followup":{"name":"追い打ちの剣","weapon_half_dice":true,"element":"physical","accuracy":100,"skills":["power_slash","holy_sword_art","dragon_slash"],"basic":true}}` |
| hero | 被动 1 | 逆境の焔 / adversity_flame | `{"low_hp":{"ratio":0.5,"cost_multiplier":0.5,"damage_multiplier":1.3}}` |
| hero | 被动 1 | 剣聖の境地 / sword_saint | `{"physical_penetration":0.4}` |
| hero | 被动 1 | 竜殺しの宿命 / dragon_destiny | `{"taken_elements":{"fire":0.8,"ice":0.8,"wind":0.8,"dark":0.8},"weakness_followup":{"name":"竜殺しの宿命","element":"weakness","damage":"1d4+str/6","accuracy":100}}` |
| cleric | 主动 3 | 贖罪の印 / atonement_mark | `{"id":"atonement_mark","cost":2,"cost_type":"sp","kind":"attack","damage":"0","accuracy":95,"element":"holy","status_on_hit":true,"on_hit_status":{"id":"holy_mark","duration":3}}` |
| cleric | 主动 5 | 大いなる癒し・浄化 / great_heal_cleanse | `{"id":"great_heal_cleanse","cost":14,"cost_type":"mp","kind":"heal","healing":"2d6+wis/2","replaces":"大いなる癒し","cleanse":{"tags":["debuff"],"count":"all"},"overflow_shield":{"id":"holy_afterglow","max_hp_ratio":0.25}}` |
| cleric | 主动 7 | セラフィムの福音 / seraphim_gospel | `{"id":"seraphim_gospel","cost":12,"cost_type":"mp","kind":"status","max_uses_per_battle":1,"self_status":{"id":"gospel","duration":3,"modifiers":{"max_hp_multiplier":2,"heal_after_attack_ratio":0.08,"heal_limit_per_round":2}}}` |
| cleric | 被动 1 | 敬虔なる心 / pious_heart | `{"regen_ratio":0.03}` |
| cleric | 被动 2 | 敬虔なる心 / pious_heart | `{"regen_ratio":0.05}` |
| cleric | 被动 3 | 敬虔なる心 / pious_heart | `{"regen_ratio":0.07}` |
| cleric | 被动 1 | 溢れる慈愛 / overflow_mercy | `{"overflow_ratio":0.75}` |
| cleric | 被动 2 | 溢れる慈愛 / overflow_mercy | `{"overflow_ratio":1.25}` |
| cleric | 被动 1 | 苦行の悟り / ascetic_wisdom | `{"sp_for_mp":{"rate":2,"max_ratio":0.5}}` |
| cleric | 被动 1 | 光輪の加護 / holy_halo | `{"round_attack":{"name":"光輪の加護","hp_ratio_gt":0.6,"damage":"1d4+wis/8","element":"holy","accuracy":100,"target":"random_enemy"}}` |
| cleric | 被动 1 | 不滅の聖域 / immortal_sanctuary | `{"free_skills":["healing_prayer"]}` |
| mage | 主动 3 | 魔力凝縮 / mana_condense | `{"id":"mana_condense","cost":3,"cost_type":"sp","kind":"restore","resource":"mp","amount":"int/3+2","self_status":[{"id":"magic_focus","modifiers":{"next_spell_damage_multiplier":1.3}},{"id":"mana_veil","modifiers":{"received_damage_multiplier":0.5}}]}` |
| mage | 主动 5 | 氷炎の双嵐 / twin_storm | `{"id":"twin_storm","cost":7,"cost_type":"mp","kind":"attack","damage":"1d6+int/6","accuracy":92,"spell_tier":"advanced","multi_elements":["fire","ice"],"hits_per_element":1,"conditional_multipliers":[{"if":"target_hp_full","element":"fire","x":2},{"if":"target_hp_ratio_lte","ratio":0.5,"element":"ice","x":2}]}` |
| mage | 主动 7 | 元素崩壊 / elemental_collapse | `{"id":"elemental_collapse","cost":18,"cost_type":"mp","kind":"attack","damage":"1d4+int/5","accuracy":95,"spell_tier":"advanced","learned_elements":true,"max_hits":4,"resonance_exempt":true}` |
| mage | 被动 1 | 魔力循環 / mana_cycle | `{"mana_cycle":{"amount":2,"cap_ratio":0.3}}` |
| mage | 被动 2 | 魔力循環 / mana_cycle | `{"mana_cycle":{"amount":3,"cap_ratio":0.4}}` |
| mage | 被动 3 | 魔力循環 / mana_cycle | `{"mana_cycle":{"amount":3,"cap_ratio":0.4}}` |
| mage | 被动 1 | 魔導の盾 / arcane_guard | `{"battle_shield":{"id":"arcane_shield"}}` |
| mage | 被动 2 | 魔導の盾 / arcane_guard | `{"battle_shield":{"id":"arcane_shield"},"shield_regain":{"every":3,"max":2,"status":{"id":"arcane_shield","modifiers":{"shield":{"block_one_attack":true,"max_hp_ratio":0.2}}}}}` |
| mage | 被动 1 | 元素共鳴 / element_resonance | `{"resonance":{"multiplier":1.15,"refund":1}}` |
| mage | 被动 1 | マナ・アーマー / mana_armor | `{"mana_armor":0.2,"mana_armor_cap_ratio":0.5}` |
| mage | 被动 1 | 万象の支配者 / omni_master | `{"basic_element":"weakness","fallback_element":"arcane","weak_multiplier":1.25}` |
| thief | 主动 3 | 目潰し投げ / blinding_throw | `{"id":"blinding_throw","cost":2,"cost_type":"mp","kind":"attack","damage":"1d4+dex/4","accuracy":95,"element":"physical","on_hit_status":{"id":"blind","duration":2}}` |
| thief | 主动 5 | 刃の乱舞 / blade_dance | `{"id":"blade_dance","cost":4,"cost_type":"sp","kind":"attack","damage":"1d4+dex/4","accuracy":95,"element":"physical","all_targets":true,"on_hit_status":{"id":"poison","stacks":1}}` |
| thief | 主动 7 | 神速の影分身 / shadow_haste | `{"id":"shadow_haste","cost":0,"cost_type":"mp","costs":{"sp":8,"mp":4},"kind":"status","cooldown":5,"self_status":{"id":"haste","duration":3}}` |
| thief | 被动 1 | 軽業の身のこなし / acrobatics | `{"evade_bonus":5,"miss_sp":1,"miss_sp_cap":2}` |
| thief | 被动 2 | 軽業の身のこなし / acrobatics | `{"evade_bonus":8,"miss_sp":1,"miss_sp_cap":3}` |
| thief | 被动 3 | 軽業の身のこなし / acrobatics | `{"evade_bonus":10,"miss_sp":2,"miss_sp_cap":4}` |
| thief | 被动 1 | 毒使いの技 / poison_craft | `{"hit_status":{"id":"poison","stacks":1,"max_stacks":3}}` |
| thief | 被动 2 | 毒使いの技 / poison_craft | `{"hit_status":{"id":"poison","stacks":1,"max_stacks":5}}` |
| thief | 被动 1 | 暗器の達人 / hidden_weapon_master | `{"free_item_uses":1}` |
| thief | 被动 1 | 見切り反撃 / counter_sight | `{"counter_attack":{"name":"見切り反撃","damage":"1d6","element":"physical","accuracy":100}}` |
| thief | 被动 1 | 無明の暗殺者 / unseen_assassin | `{"encounter_damage":{"elite":1.15,"boss":1.15}}` |
| mage | 魔法书  | 雷撃 / lightning | `{"id":"lightning","cost":5,"cost_type":"mp","kind":"attack","damage":"1d4+int/4","accuracy":90,"element":"lightning","all_targets":true,"spell_tier":"basic"}` |
| mage | 魔法书  | 魔力の槍 / arcane_lance | `{"id":"arcane_lance","cost":4,"cost_type":"mp","kind":"attack","damage":"1d6+int/2","accuracy":95,"element":"arcane","ignores_defense":true,"spell_tier":"basic"}` |
