# AGENTS.md — 共同规则

由 LLM 担任 GM 的单人 TRPG（视觉小说风格的浏览器界面）。定位以学术研究为主：在有限的提示词预算下，让模型更快、更准地担任 GM，结算全部交给确定性引擎。路线图见 `docs/roadmap.md`。

技术栈：Python 3.9+ / FastAPI（`host/`），原生 JS 前端（`client/`），剧本使用 JSON Scenario Pack（`host/prompt/processed/`），LLM 使用 Gemini API，本地对照用 Ollama。测试用 `unittest`。

## 角色

| 角色 | 负责 | 角色文档 |
|---|---|---|
| 设计负责人 | 方向、研究设计、提示词措辞、数值目标、剧本标准与正文、美术风格、验收 | `docs/roles/design.md` |
| 工程负责人 | 代码、脚本、测试、评测与模拟框架、数据录入、生图执行 | `docs/roles/engineering.md` |

开工前你会被告知自己的角色，然后读对应的角色文档。不要因为自己是哪个模型就推断角色；没被告知时先问用户。

## 共同规则

- 和用户交流用中文。游戏内文本（GM 叙述、UI、剧本、benchmark 输入）一律用**日语**。
- 只 `git add` 具体文件，不要 `git add -A` / `git add .`。工程提交的信息加 `[工程]` 前缀。
- 不做任务范围外的改动，也不顺手重构。
- 验证命令（提交前必须通过）：
  ```
  python -m unittest discover -s tests -q
  node --check client/app.js
  ```
- 不提交密钥。个人配置放 `host/local_config.json`（已被 gitignore）。付费 API 调用必须显式开启（例如 `--live`），默认测试不能联网。
- `host/prompt/raw/` 是第三方资料，只在本地保留，**永远不能提交**。
- 平台是 Windows。写给其他工具读的文件用 UTF-8 无 BOM。
- 代码风格沿用周围代码：类型注解、`from __future__ import annotations`、注释少而准。

## 文件归属

| 归设计负责人 | 归工程负责人 |
|---|---|
| `docs/roadmap.md`、`docs/design/`、`docs/specs/`、`docs/roles/` | `host/`、`client/`、`scripts/`、`tests/` 的代码 |
| 提示词措辞（`gm_contract.py`、`free_actions.py` 中的 prompt 字符串）：工程可以按 spec 实现变体，但不改默认措辞 | 评测和模拟框架、trace、缓存 |
| benchmark 的标准答案（`eval/benchmark/`） | benchmark 候选（`eval/candidates/`） |
| 剧本的叙事文本和数值目标 | 按 spec 录入剧本数据、调参 |
| 美术风格文档、最终选图 | 生图执行、素材管线、`assets/manifest.json` |

## 文档地图

- `docs/roadmap.md`：总体计划和已确定的决定
- `docs/specs/NNN-*.md`：任务说明，一次一个
- `docs/roles/`：角色文档
- `docs/api-free-actions.md`：自由行动的现有设计
