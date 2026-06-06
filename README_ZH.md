# Local LLM TRPG

使用本地LLM作为GM的TRPG客户端最小实现。Host端基于FastAPI管理游戏状态、存档、骰子和OpenAI兼容的LLM调用，Client端在浏览器中运行，采用视觉小说风格（Galgame）UI。

> **Python**: 需要3.9或更高版本。已在FastAPI/Pydantic下测试通过。arm64用户建议使用原生arm64 Python/Conda环境。

📖 **语言**: [English](README.md) · [日本語](README_JA.md) · [中文](#)

---

## 目录

- [安装](#安装)
- [LLM配置](#llm配置)
- [远程Ollama](#远程ollama)
- [剧本格式](#剧本格式)
- [剧本编辑器](#剧本编辑器)
- [游戏功能](#游戏功能)
  - [角色](#角色)
  - [属性与判定](#属性与判定)
  - [技能](#技能)
  - [敌人与战斗](#敌人与战斗)
- [剧本转换](#剧本转换)
- [API概览](#api概览)
- [测试](#测试)
- [许可证](#许可证)

---

## 安装

```powershell
python -m pip install -r requirements.txt
python -m host.run_server
```

浏览器会自动打开 `http://127.0.0.1:8000/`。跳过自动打开：

```powershell
python -m host.run_server --no-browser
```

开发时使用热重载：

```powershell
python -m host.run_server --reload
```

创建新会话时，GM会自动生成开场场景。玩家根据GM的叙述输入第一个行动。GM响应会在生成完成后全文显示。

## LLM配置

编辑 `host/config.json` 中的 `active_backend` 和 `backends`。

- Ollama（默认）: `http://localhost:11434/v1`
- Koboldcpp: `http://localhost:5001/v1`

两者均使用OpenAI兼容的 `/chat/completions` 端点。当前默认模型优先级为 qwen3，随后 fallback 到 qwen2.5 和 ELYZA JP 8B。

```json
{
  "active_backend": "ollama",
  "backends": {
    "ollama": {
      "base_url": "http://localhost:11434/v1",
      "model": "qwen3-swallow-8b-rl-local",
      "fallback_models": [
        "qwen2.5-7b-instruct-local",
        "elyza-jp-8b-local"
      ],
      "api_key": "ollama"
    }
  },
  "temperature": 0.8,
  "max_tokens": 2048,
  "request_timeout_seconds": 1800,
  "response_format": "json_object",
  "prompting": {
    "history_messages": 4,
    "memory_max_chars": 1200,
    "action_history_max": 40,
    "action_history_item_chars": 80
  },
  "debug_llm": true,
  "demo_fallback_on_error": true
}
```

### 提示参数

| 参数 | 默认值 | 说明 |
|-----------|---------|------|
| `history_messages` | 4 | 发送给LLM的最近消息数量 |
| `memory_max_chars` | 1200 | 对话记忆摘要的最大字符数 |
| `action_history_max` | 40 | 玩家行动历史的最大条目数 |
| `action_history_item_chars` | 80 | 每条行动历史的最大字符数 |

## 远程Ollama

对于性能较弱的笔记本，可以将游戏主机/客户端保留在本地，仅将LLM调用指向主力PC。不要直接编辑 `host/config.json`，应创建 `host/local_config.json`。该文件已被git忽略，适合保存每台机器自己的URL、token和模型名。

```json
{
  "backends": {
    "ollama": {
      "base_url": "https://ollama.your-domain.com/v1",
      "model": "qwen3-swallow-8b-rl-local",
      "fallback_models": [
        "qwen2.5-7b-instruct-local",
        "elyza-jp-8b-local"
      ],
      "api_key": "ollama"
    }
  }
}
```

也可以通过环境变量覆盖配置，而不修改文件：

```powershell
$env:TRPG_OLLAMA_BASE_URL = "https://ollama.your-domain.com"
$env:TRPG_OLLAMA_MODEL = "qwen3-swallow-8b-rl-local"
python -m host.run_server
```

### 远程设置步骤

1. 在主力PC上，如果作为Cloudflare Tunnel的本地目标，设置 `OLLAMA_HOST=127.0.0.1:11434`；如果通过Tailscale等私有VPN使用，设置 `OLLAMA_HOST=0.0.0.0:11434`。
2. 用你的Cloudflare域名创建指向主力PC `http://127.0.0.1:11434` 的Cloudflare Tunnel。
3. 使用Cloudflare Access或服务令牌保护。不要在没有访问控制的情况下公开Ollama。
4. 在性能较弱的客户端上，将 `host/local_config.json` 或 `TRPG_OLLAMA_BASE_URL` 指向Cloudflare Tunnel URL。

如果收到空 `403` 响应，说明Ollama拒绝了公开域名的 `Host` 头。可在Cloudflare设置 `HTTP Host Header` 为 `localhost:11434`，或运行内置代理：

```powershell
python -m host.ollama_tunnel_proxy
```

然后将Cloudflare Tunnel的服务URL改为：

```text
http://localhost:11435
```

公开侧游戏客户端仍然使用 `https://ollama.your-domain.com/v1`；只需要修改Cloudflare的origin service URL。

### 注册GGUF模型

```powershell
python -m host.setup_ollama_models
ollama list
```

如果看到 `model not found`，请先注册GGUF模型，或者把配置中的 `model` / `fallback_models` 更新为与 `ollama list` 输出一致的名称。

### 调试日志

默认启用（`"debug_llm": true`）。日志带 `[TRPG-DEBUG]` 前缀输出。绝不记录API密钥。

---

## 剧本格式

剧本使用 [`scenario_pack.schema.json`](host/prompt/processed/scenario_pack.schema.json) 定义的 **Scenario Pack** JSON格式。

```
meta              → 标题、摘要、语言、起始场景
rules[]           → GM行为规则
scenes[]          → id、标题、描述、目标、关键词、location_ids、next_scene_ids、fallback_choices
locations[]       → id、标题、描述、关键词、npc_ids、item_ids、clue_ids、enemy_ids
npcs[]            → id、名称、描述、关键词
items[]           → id、名称、描述、效果、关键词
clues[]           → id、标题、描述、关键词
enemies[]         → id、名称、描述、图像、HP/最大HP、MP/最大MP、SP/最大SP、属性、技能[]
attribute_defs[]  → id、名称、初始数值
characters[]      → id、名称、预设名、描述、图像、女性图像、HP/MP/SP、金币、属性{}、背包[]、装备[]、技能[]
combat_choices[]  → 全局战斗行动选项
fallback_choices[]→ 全局默认选项
```

实体（NPC、道具、线索、敌人）绑定到 **地点（Locations）** 上，而非场景。每个地点通过 `npc_ids`、`item_ids`、`clue_ids`、`enemy_ids` 声明存在的实体。场景通过 `location_ids` 引用地点，通过 `next_scene_ids` 表示可转移的场景。

完整示例见 [`dragon_rpg.json`](host/prompt/processed/dragon_rpg.json)。

---

## 剧本编辑器

通过 `http://127.0.0.1:8000/editor` 访问可视化编辑器。所有JSON字段均可通过UI编辑：

| 板块 | 内容 |
|---------|------|
| 基本信息 | 标题、语言、摘要、起始场景 |
| 规则 | GM行为规则 |
| 场景 | 场景定义、目标、地点绑定、后续场景 |
| Hybrid | Full模式的预准备GM回合（含草稿、骰子、选项、修正说明） |
| 地点 | 带NPC/道具/线索/敌人绑定的地点 |
| NPC | 非玩家角色定义 |
| 道具 | 带效果的道具 |
| 线索 | 故事线索 |
| 敌人 | 敌人属性、能力值、技能 |
| 属性定义 | 自定义属性定义（如力量、敏捷等） |
| 角色 | 可玩角色（HP/MP/SP、属性、背包、装备、技能） |
| 全局选项 | 默认选项 |
| 战斗选项 | 战斗时的行动选项 |
| JSON | 原始JSON编辑（高级） |

---

## 游戏功能

### 角色

玩家在开始前从剧本的角色列表中选择角色。每个角色定义：

- **基础属性**: HP、MP、SP（含最大值）
- **初始金币**和**背包**（名称、描述、效果、数量）
- **装备**（已装备物品名称）
- **能力值**（见下文）
- **技能**（见下文）

`dragon_rpg.json` 中的角色示例：勇者（平衡型）、僧侣（治疗者）、魔法师（攻击魔法）、盗贼（敏捷型）。

### 属性与判定

属性按剧本自定义。`dragon_rpg` 示例定义：

| ID | 名称 | 说明 |
|----|------|------|
| `str` | 筋力 | 物理力量 |
| `dex` | 敏捷 | 速度和灵巧 |
| `int` | 知力 | 魔法与知识 |
| `wis` | 感知 | 感知与洞察 |
| `con` | 耐久 | 耐力与韧性 |

**属性判定**: GM可设置带属性修正的 `dice_type`，如 `"1d20+str"`。角色属性值会自动加算到d20结果上。例如：筋力8、DC=10时，投出2+8=10即成功。

**属性变化**: GM可通过 `state_delta.attribute_changes` 在游戏进行中修改属性值：
```json
{ "attribute_changes": { "str": -2, "dex": +1 } }
```

### 技能

角色和敌人可拥有技能，包含：
- **名称**、**描述**、**效果**（叙述性描述）
- **dice_type**（可选，如 `"1d20+int"` 表示魔法类技能）
- **消耗**和**消耗类型**（`"mp"` 或 `"sp"`）

示例：僧侣的"治癒の祈り"（治愈祈祷）— `dice_type: "1d6+int"`, `消耗: 4 MP`，恢复HP。

### 敌人与战斗

敌人在剧本中以完整属性、能力值、技能定义。通过 `enemy_ids` 绑定到地点。

当场景当前地点存在敌人时，GM自动使用**战斗选项**（攻击、使用技能、防御、使用道具、逃跑）替代常规探索选项。

敌人示例（`dragon_rpg.json`）：
- **史莱姆**（HP 5, 力量 4）— 暗之森的教学敌人
- **邪龙伊格尼斯**（HP 30, 力量 18, 技能: 火焰吐息、尾巴攻击）

---

## GM模式

| 模式 | 说明 |
|------|------|
| **Semi**（默认） | LLM接收场景上下文（地点、NPC、道具、敌人、线索）并自由即兴发挥。 |
| **Full** | LLM接收通过Gemini生成的预准备回合，仅对当前状态进行最小限度的改写。使用 `*_hybrid.json` 剧本包。 |

在开始界面的设置面板中选择模式。

---

## 骰子系统

标准TRPG骰子表达式（`1d20`、`2d6`、`1d100`）。骰子结果包含：

- `rolls[]` — 每次掷骰的值
- `total` — 掷骰总和 + 属性修正（如有）
- `base_total` / `attr_mod` / `attr_key` — 属性判定时附加

空的或null的 `dice_type` 默认为 `1d20`。

---

## 剧本转换

```powershell
python -m host.scenario_converter "host\prompt\raw\your_scenario.docx"
```

支持 `.txt`、`.docx`、`.pdf`、`.doc`（`.doc` 需要Windows COM）。

Gemini API密钥从环境变量 `GEMINI_API_KEY` 或 `host/gemini_api_key.txt` / `host/gemini_api_key.py` / `host/auto_tagger.py` 中读取。这些secret文件已通过 `.gitignore` 排除。

---

## API概览

| 端点 | 方法 | 说明 |
|----------|--------|------|
| `/api/sessions` | POST | 创建新游戏会话 |
| `/api/sessions/{id}` | GET | 获取会话状态 |
| `/api/sessions/{id}/turn` | POST | 提交玩家行动 |
| `/api/scenarios` | GET/POST | 列出/创建剧本 |
| `/api/scenarios/{filename}` | GET/PUT | 读取/更新剧本 |
| `/api/config` | GET/PUT | 读取/更新后端配置 |
| `/api/ollama/shutdown` | POST | 远程关机（通过代理） |

### 会话创建

```json
{
  "scenario_path": "host/prompt/processed/dragon_rpg.json",
  "gm_mode": "semi",
  "character_id": "hero",
  "character": {
    "name": "アルス",
    "character_image": "/static/images/char_male_hero.png"
  }
}
```

---

## 测试

```powershell
python -m unittest discover -s tests
```

---

## 许可证

详见 [LICENSE](LICENSE)。
