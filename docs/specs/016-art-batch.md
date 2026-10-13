# 016 美术批量生成（取代 014）

用 Codex 内置的 `imagegen`（`image_gen` 工具）生成。**只新增图片文件和 `assets/manifest.json`，不修改剧本 JSON 和代码**。接线由设计负责人另行处理。

## 风格基准（开始前必须先看）
- 敌人：`client/images/enemy_ignis.png`、`enemy_frost_dire_wolf.png`、`enemy_forest_wolf.png`、`enemy_fire_elemental.png`——精细的厚涂奇幻插画，透明背景，全身，1254×1254，戏剧性姿态，强烈的边缘光。
- NPC：`client/images/npc_general.png`、`npc_warlock.png`、`npc_sarah.png`——1024×1536，透明背景，全身立绘，动漫风格的半写实厚涂。
- 背景：`client/images/bg_elf_spring.png`、`bg_dark_forest.png`、`bg_goblin_fort.png`——尺寸和画风与这些一致（先读出它们的尺寸）。

## 产出清单
| 文件 | 尺寸 | 内容 | 参考 |
|---|---|---|---|
| `enemy_draco_human.png` | 1024×1536 | 将军ドラコ拔剑迎战：剑身是冰一样的青白色，脚下和披风下摆结霜，双眼泛着淡淡的白光，表情冷漠、居高临下。必须是 `npc_general.png` 中**同一个人**（脸、发型、盔甲、红披风一致） | 以 `npc_general.png` 为参考做编辑 |
| `enemy_draco_dragon.png` | 1254×1254 | 白竜ヴァイス：体型、气势与イグニス对等，是它的"对立面"。雪原般的白色鳞片，翼膜半透明并带冰蓝色脉络，角像冰晶，胸口是冰蓝色发光纹路（对应イグニス胸口的熔岩纹），眼睛冰蓝色发光；比イグニス更冷静、更有压迫感 | `enemy_ignis.png`、`enemy_frost_dire_wolf.png`（配色必须属于霜之巨狼的同一家族） |
| `npc_ignis_calm.png` | 1254×1254 | 净化后的イグニス：同一条龙，熔岩纹的亮度变柔和，眼睛从狂暴的红光变成平静的金色，姿态放松（翅膀半收、头微低） | 以 `enemy_ignis.png` 为参考做编辑 |
| `enemy_heat_lizard.png` | 1254×1254 | 熱岩トカゲ：背上覆盖冷却中的溶岩甲壳、缝隙透出橙光的大蜥蜴 | `enemy_fire_elemental.png` |
| `enemy_fire_wisp.png` | 1254×1254 | 炎のウィスプ：小而灵动的火焰精灵，有简单的眼睛，周围飘着火星（单只） | `enemy_fire_elemental.png` |
| `enemy_ruby_golem.png` | 1254×1254 | 紅晶ゴーレム：由红色水晶块堆成的魁梧巨人，关节处透出内部的熔光 | 水晶质感统一（以下 4 张同） |
| `enemy_sapphire_moth.png` | 1254×1254 | 蒼晶の蝶：翅膀是薄片状的蓝色水晶，洒落冷光鳞粉，体长约人的一半 | |
| `enemy_emerald_spider.png` | 1254×1254 | 翠晶の蜘蛛：腿是尖锐的绿色水晶，腹部有毒性的绿光 | |
| `enemy_prism_tree.png` | 1254×1254 | 虹晶樹（Boss）：七色水晶构成的大树，树干扭曲，枝头是棱柱状的结晶，根部缠着破碎的水晶魔物。光从内部折射出彩虹，气势和イグニス同等 | 以上 3 张水晶怪的质感 |
| `npc_mina.png` | 1024×1536 | 見習い魔法使いミーナ：十四五岁的少女，见习法师的蓝色系长袍（和 `npc_warlock.png` 的蓝袍同一系），抱着一本书，表情好奇又有点怯 | `npc_warlock.png` |
| `npc_gald.png` | 1024×1536 | 行商人ガルド：四十来岁、晒黑、笑容爽朗的壮汉，背着大大的行商背架，腰间挂着各种小袋子 | `npc_ian.png` |
| `bg_sealed_cave.png` | 同 `bg_elf_spring.png` | 泉的背后，长满青苔的岩壁上刻着七色摇曳的巨大魔法阵，魔法阵后面透出微弱的热光 | `bg_elf_spring.png` |
| `bg_lava_cave.png` | 同上 | 炙热的岩石回廊，红光的熔岩流，空气热得扭曲 | |
| `bg_crystal_cave.png` | 同上 | 墙上长满红、蓝、绿水晶的洞窟深处，远处隐约可见七色发光的大树轮廓 | |

## 要求
- 透明背景要干净，不能有白边或灰边（检查 alpha 通道）；背景图不透明。尺寸必须和上表一致（必要时按比例缩放和填充）。
- 每张至少生成 2 个候选。候选全部放进 `assets/candidates/016/<文件名去掉扩展名>/`，选定的放进 `client/images/`。选择理由写进汇报。
- 新建或更新 `assets/manifest.json`：每张图记录文件、用途、提示词全文、参考图、生成日期、`"approved": false`。
- 不画文字、logo 和水印。
- 选图时自己做一遍对比检查：和参考图放在一起是否像同一部作品（笔触、光源方向、饱和度）。差得明显的重画。

## 验收
设计负责人用 Read 逐张看图验收，不合格的会给出修改意见，再开下一轮。

## 汇报
按 `docs/roles/engineering.md` 的格式，附上每张最终图和候选图的路径、使用的提示词，以及自查时发现的风格偏差。
