# 紅き邪竜イグニス — AI GM TRPG

📖 **语言**: [English](README.md) · [日本語](README_JA.md) · [中文](#)

一款视觉小说风格的浏览器单人日语 TRPG。LLM（Gemini）担任游戏主持人（GM），但它从不决定结果：它只把玩家的自由输入解释成一个受约束的「行动案」，HP、道具、剧情标记、位置、骰子、战斗和奖励等所有数值都由确定性的游戏引擎掌管。

这个项目同时也是一个研究平台，研究的问题是：把裁定交给引擎之后，在有限的提示词预算下，LLM 能多准确、多安全地担任 GM。见[论文草稿](docs/research/paper-draft.md)。

> **Python** 3.9 以上。游戏内文本全部为日语。

---

## 目录

- [特点](#特点)
- [快速开始](#快速开始)
- [配置](#配置)
- [游戏内容](#游戏内容)
- [项目结构](#项目结构)
- [研究与评测](#研究与评测)
- [开发](#开发)
- [API 概览](#api-概览)
- [许可证](#许可证)

---

## 特点

- **引擎裁定型 GM**：模型填写的行动案，每个字段只能取引擎列出的 ID；引擎在会话副本上结算，只提交合法的结果。所有实验中非法状态变化（S4）都是 0。
- **用测量说话**：486 条经过审定的日语意图 benchmark，冻结剧本加缓存重放。在冻结 test 集上，Gemini 3.1 Flash-Lite 的可接受行动案比例为 97.3%，有害误触发率为 0.68%。
- **不调用模型也能玩通**：因为裁定是确定性的，整局游戏可以离线通玩；自动探索脚本跑 32 局，作为软锁、状态矛盾和文本泄露的回归测试。
- **一段完整的冒险**：4 个职业、5 章、一座城塞都市、3 条属性和对策同伴各不相同的第三章路线、6 名同伴、带尾声的多结局。

## 快速开始

### 从源码运行

```powershell
python -m pip install -r requirements.txt
python -m host.run_server
```

浏览器会自动打开 `http://127.0.0.1:8000/`。不想自动打开用 `--no-browser`，换端口用 `--port 8010`，开发时用 `--reload`。剧本编辑器在 `/editor`。

### Windows 可执行文件

在本地构建。API key 不会被打包进去，构建时会解开所有打包的模块做审计确认。

```powershell
python -m scripts.build_exe                     # dist/LocalTRPG/LocalTRPG.exe 和 zip
python -m scripts.build_exe --with-local-config # 同时复制你的 host/local_config.json（仅限个人使用）
```

### 可分发的演示版

想把游戏发给别人又不带 key，先部署 [`workers/gemini-proxy`](workers/gemini-proxy/README.md) 里的 Cloudflare Worker 代理。它持有 key，只放行本游戏的请求，并用每 IP 和每天的上限封顶费用。然后：

```powershell
$env:DEMO_TOKEN = "<Worker 的 demo token>"   # 只有 Worker 设置了 DEMO_TOKEN 时才需要
python -m scripts.build_exe --demo-endpoint https://<your-worker>.workers.dev
```

## 配置

默认模型是 Gemini 3.1 Flash-Lite。个人配置写在 `host/local_config.json`（不进 git；打包版放在 `LocalTRPG.exe` 同一目录）。永远不要提交 key。

```json
{
  "active_backend": "gemini",
  "backends": {
    "gemini": {
      "model": "gemini-3.1-flash-lite",
      "fallback_models": ["gemini-3.5-flash-lite", "gemini-3.6-flash"],
      "api_keys": ["YOUR_FIRST_GEMINI_KEY", "YOUR_SECOND_GEMINI_KEY"]
    }
  }
}
```

key 按顺序尝试；因额度或认证失败的 key 在本会话内跳过，新会话从第一个重新尝试。旧的 `api_key` 仍受支持，`api_keys` 优先；未配置 `api_keys` 列表时，可用逗号分隔的 `GEMINI_API_KEYS`，优先于单个 key。

环境变量覆盖：`GEMINI_API_KEYS`、`GEMINI_API_KEY`、`TRPG_LLM_BASE_URL`、`TRPG_LLM_MODEL`、`TRPG_LLM_API_KEY`、`TRPG_ACTIVE_BACKEND`、`TRPG_LOCAL_CONFIG`。

- 正常游玩时依次尝试主模型和一个备用模型，各 15 秒超时；自由行动的解释只尝试一次。
- 连不上模型时游戏照样能继续：选项和战斗由引擎结算，准备好的叙述照常显示，其余情况显示一行如实的提示。
- 通过 Ollama 运行的本地模型只保留作研究对照，游戏设置里不显示。

## 游戏内容

### 职业

| 职业 | HP / MP | 特点 |
|---|---|---|
| 勇者 | 20 / 8 | 均衡；可以在铁匠铺融合出氷鉄の大剣 |
| 僧侶 | 18 / 14 | 回复与神圣魔法 |
| 魔法使い | 12 / 20 | 攻击魔法 |
| 盗賊 | 14 / 6 | 潜行判定与速度 |

### 故事结构

```
王都 ─ 闇の森 ─┬─ 炎上する麓の村 ─────────────────────┐
               ├─ 霧の古戦場 ─(村の裏手)──────────────┤
               └─ 洞窟の水路 ─ 城塞都市オークスドーン ─┬─ 霧の古戦場
                                                      └─ 地鳴りの峡谷 ─(避難所の裏手)─┘
                                                                    └→ 竜の谷 → 王都に凱旋
```

| 第三章路线 | 属性 | 对策同伴 |
|---|---|---|
| 麓の村 | 火＋冰 | 火コウモリ竜／ミーナ |
| 霧の古戦場 | 不死（怕光） | 聖騎士リーゼ |
| 地鳴りの峡谷 | 土（抗物理、怕水） | 水術士エリオ |

可选路线最后都汇入麓の村，主线事件不会错过。凑够证据揭穿将军ドラコ的真面目，就能进入真结局。路线、线索和最终战助力的详细说明见[攻略书](docs/design/walkthrough-2026-10-18.md)（有剧透）。

### 系统

- **选项与自由输入**：可以点选项，也可以输入任何行动。选项会标出风险；需要某样你还没见过的东西才能选的选项显示为「？？？」，文字内容连浏览器都收不到。
- **回合制战斗**：完全由引擎结算，有动画和伤害数字，每次行动的演出不超过 1.4 秒，可以跳过。
- **装备部位**：武器、防具、补助各一件。之后拿到的装备会自动装进空着的部位。
- **同伴**（同时一名）：ロビン（每回合射击 HP 最高的敌人）、ワーロック（每 2 回合回复）、火コウモリ竜（火属性伤害并回复）、ミーナ（冰魔法）、リーゼ（HP 低于一半时回复，否则优先对不死系造成光属性伤害）、エリオ（水刃，以及让伤害减半的水の帳）。
- **经济**：怪物掉可以卖钱的战利品；精英和可选 Boss 掉永久提升能力的霊薬和果実，潜行绕过时也能顺手偷到；每个据点都有收集委托。
- **区域重来**：战败后可以从死亡所在区域的入口重来。
- **地图、任务、商店、休息**，以及反映你选择的**尾声**。

## 项目结构

| 路径 | 内容 |
|---|---|
| `host/` | FastAPI 服务器、引擎（`state.py`、`combat.py`、`free_actions.py`、`shops.py`、`maps.py`）、LLM 客户端与 GM 契约 |
| `client/` | 原生 JS 的视觉小说界面、战斗演出、道具图标 |
| `host/prompt/processed/` | 剧本包 `dragon_rpg.json` 和 `dragon_rpg_hybrid.json`（总是同时修改）、schema |
| `scripts/scenario/` | 生成内容的幂等剧本迁移脚本 |
| `scripts/balance/`、`scripts/playtest/` | 平衡模拟与离线探索 |
| `eval/` | benchmark、候选集、报告 |
| `workers/gemini-proxy/` | 演示版用的 Cloudflare Worker key 代理 |

**自由行动的流程**：引擎构建一份精简的上下文（可选动作、障碍、可交互对象、背包、最近的变化）→ 用严格的 JSON schema 调用一次模型 → 严格解析 → 在会话副本上裁定 → 根据引擎的结果叙述。模型的输出永远不能直接写入状态。

**GM 模式**：*Semi*（默认）轻度改写 hybrid 剧本包里准备好的回合；*Full* 根据场景上下文更自由地叙述。两种模式的结果都由引擎决定。

## 研究与评测

- 论文草稿：[`docs/research/paper-draft.md`](docs/research/paper-draft.md)；每一次提示词修改及其测量结果：[`docs/design/prompt-log.md`](docs/design/prompt-log.md)。
- Benchmark v2：486 条审定用例（dev 194／test 292，按句式家族划分），严重度 S0–S4，冻结剧本 `f41af9d` 加缓存重放。见 [`eval/benchmark/README.md`](eval/benchmark/README.md)。

```powershell
# 只重放缓存，不产生 API 费用；要在缓存未命中时调用 API，加 --live。
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split test
```

只有显式加上 `--live` 才会产生付费 API 调用。

## 开发

角色与共同规则见 [`AGENTS.md`](AGENTS.md)：设计负责人（方向、提示词、剧情文本、美术选定、验收）和工程负责人（代码、测试、评测、数据录入）。任务写成 `docs/specs/` 下的 spec。

每次提交前必须通过：

```powershell
python -m unittest discover -s tests -q
node --check client/app.js
```

常用工具：

```powershell
python -m scripts.playtest.explore      # 离线通玩回归（不调用 LLM）
python -m scripts.balance.checkpoints   # 改剧本后重新生成平衡检查点
python -m scripts.worker_fingerprints   # 检查代理的提示词指纹是否最新
```

美术候选与批准状态记录在 `assets/manifest.json`。

## API 概览

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/sessions` | POST | 创建会话（同时生成开场） |
| `/api/sessions/{id}` | GET | 会话状态 |
| `/api/sessions/{id}/turn` | POST | 选项或自由输入的行动 |
| `/api/sessions/{id}/combat/actions` | POST | 一次由引擎结算的战斗行动 |
| `/api/sessions/{id}/combat/resolve` | POST | 战斗结束后叙述一次 |
| `/api/sessions/{id}/retry` | POST | 战败后从区域入口重来 |
| `/api/sessions/{id}/map/move` | POST | 点击地图节点移动 |
| `/api/sessions/{id}/items/use` | POST | 使用或装备背包里的道具 |
| `/api/sessions/{id}/shops/{shop}` | GET | 商店的商品与价格 |
| `/api/sessions/{id}/shops/{shop}/buy` · `/sell` | POST | 买卖 |
| `/api/scenarios`、`/api/scenarios/{file}` | GET/POST/PUT | 剧本包的列表、创建、读取、更新 |
| `/api/config` | GET/PUT | 后端配置 |

## 许可证

见 [LICENSE](LICENSE)。
