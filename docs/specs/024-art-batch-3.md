# 024 美术批量生成 第 3 批（第 5 章）

要求、风格基准、产出方式和 016、020 完全相同：用内置 `image_gen` 生成；**只新增图片和更新 `assets/manifest.json`**；每张至少 2 个候选，放进 `assets/candidates/024/<名字>/`；透明背景要干净；尺寸和参考图一致；自查风格一致性。

风格基准另外加上已采用的图：`enemy_draco_dragon.png`、`enemy_draco_human.png`、`bg_inn.png`、`bg_dragon_rpg.png`。

| 文件 | 尺寸 | 内容 | 参考 |
|---|---|---|---|
| `enemy_ice_sentinel.png` | 1254×1254，透明 | 氷の番兵：冰制的全身铠甲守卫，头盔里只有冰蓝色的冷光，手持冰锤，动作沉重。配色和质感属于白竜家族 | `enemy_draco_dragon.png`、`enemy_frost_dire_wolf.png` |
| `enemy_ice_assassin.png` | 1024×1536，透明 | 氷の刺客：白色装束、蒙面的刺客，双手各持一把冰刃，姿态敏捷低伏；胸前有白竜纹章 | `enemy_draco_human.png`（冰的质感） |
| `bg_royal_gate.png` | 同 `bg_dragon_rpg.png` | 凱旋の城門：迎接凯旋的王城城门，花瓣飞舞，人群挥手，阳光明亮 | `bg_dragon_rpg.png` |
| `bg_festival_town.png` | 同上 | 凱旋の城下町：节日装饰的城下町街道，彩旗、花环、摊位和人群 | `bg_dragon_rpg.png`、`bg_item_shop.png` |
| `bg_mansion_garden.png` | 同上 | 将軍の屋敷・夜の庭：月夜下的贵族宅邸庭院，中央的喷泉完全冻结，地面结着薄霜 | |
| `bg_mansion_corridor.png` | 同上 | 将軍の屋敷・凍てつく回廊：豪华的宅邸走廊，墙壁和地板都覆盖着薄冰，尽头是一扇门 | |
| `bg_mansion_study.png` | 同上 | 将軍の屋敷・書斎：堆满古书的书斋，桌上摊开一本日志，角落里有一个用白鳞装饰的小箱，窗外月光 | |
| `bg_king_room.png` | 同上 | 王の私室：月光照进的王的寝室，豪华但寂静，窗边 | `bg_dragon_rpg.png` |
| `bg_inn_night.png` | 同 `bg_inn.png` | 宿屋・深夜：`bg_inn.png` 里的客房在深夜，窗户结冰后碎裂，冷气涌入 | 以 `bg_inn.png` 为参考做编辑 |

## 汇报
按 `docs/roles/engineering.md` 的格式，附上每张最终图和候选图的路径、提示词，以及自查时发现的风格偏差。**这个 worktree 里只有图片改动，不需要跑全量测试，直接提交即可。**
