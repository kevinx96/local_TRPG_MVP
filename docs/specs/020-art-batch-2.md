# 020 美术批量生成 第 2 批（第 3、4 章）

要求、风格基准、产出方式和 016（`docs/specs/016-art-batch.md`）完全相同：用内置 `image_gen` 生成；**只新增图片和更新 `assets/manifest.json`**；每张至少 2 个候选，放进 `assets/candidates/020/<名字>/`；透明背景要干净；尺寸和参考图一致；自查风格一致性。

风格基准另外加上 016 已采用的图：`enemy_heat_lizard.png`、`enemy_draco_dragon.png`、`npc_mina.png`、`bg_lava_cave.png`。

| 文件 | 尺寸 | 内容 | 参考 |
|---|---|---|---|
| `enemy_ash_wraith.png` | 1254×1254，透明 | 煤の亡霊：由煤灰和余烬构成的人形怨灵，脸部是空洞，下半身消散成烟，身上有暗红色的火星 | `enemy_zebok.png`、`enemy_fire_elemental.png` |
| `enemy_lava_drake.png` | 1254×1254，透明 | 溶岩ドレイク：イグニス的小型眷属，红黑熔岩鳞，四肢加双翼，体型如马；一看就和イグニス同族，但更小、更像野兽 | `enemy_ignis.png` |
| `enemy_xanxus_phantom.png` | 1024×1536，透明 | Xanxusの分身：和 `npc_xanxus.png` 是同一个角色（赤红法衣、燃烧的骸骨魔法师），但整个身体是半透明的火焰质感，轮廓有些摇曳 | 以 `npc_xanxus.png` 为参考做编辑 |
| `npc_riku.png` | 1024×1536，透明 | 長老の孫リク：七八岁的男孩，脸上沾着煤灰，衣服有烧焦的痕迹，双手紧握一个小护身符，表情惊魂未定但坚强 | `npc_elder.png`（同一个村子的服饰风格） |
| `bg_lava_bridge.png` | 同 `bg_dragon_valley.png` | 沸腾的熔岩河上，唯一一座破旧的吊桥，木板烧焦、绳索快断，热风扭曲空气 | `bg_dragon_valley.png` |
| `bg_dragon_nest.png` | 同上 | 竜の巣的入口：巨大的洞穴，灼热的风，散落着骸骨和熔化变形的财宝，深处发出红光 | `bg_dragon_valley.png` |
| `bg_burning_house.png` | 同 `bg_burning_village.png` | 燃烧中的民家正面，入口被燃烧的房梁堵住，窗户里透出火光 | `bg_burning_village.png` |
| `bg_hot_spring.png` | 同 `bg_lava_cave.png` | 地底的小温泉：岩石围成的温泉池冒着热气，岩壁上有发光的苔藓，氛围比熔岩洞窟柔和 | `bg_lava_cave.png`、`bg_crystal_cave.png` |

## 汇报
按 `docs/roles/engineering.md` 的格式，附上每张最终图和候选图的路径、提示词，以及自查时发现的风格偏差。
