# 拟定标签下的初步数字

Run: `2026-10-11T124213992341Z-intent-ollama-elyza-jp-8b-local-union_schema`

候选标签尚未审定。无模型响应时指标为 n/a；skipped、连接错误与拦截不进入意图准确率分母。
缓存重放的延迟和 token 来自原始调用。所有引擎判定骰固定为 10（不超过骰面上限）。

总数 194；可评测响应 194；状态 `{"ok": 191, "json_error": 2, "invalid_plan": 1}`。

| 指标 | 值 |
|---|---|
| exact | 0.3093 |
| kind | 0.4124 |
| kind_relaxed | 0.4124 |
| s0_s1_rate | 0.3093 |
| s3_rate | 0.0155 |
| engine_caught | 17 |
| severity | {'S0': 37, 'S1': 23, 'S2': 131, 'S3': 3, 'S4': 0} |
| json_failure_rate | 0.0103 |
| invalid_plan_rate | 0.0155 |
| conflict_count | n/a |
| conflict_rate | n/a |
| cost_per_turn | 0.00000000 |
| cost_currency | USD |
| cost_reported | 194 |
| latency_ms p50 | 4009.2505 |
| latency_ms p95 | 4830.7055 |
| input_tokens mean (194 reported) | 821.6701 |
| output_tokens mean (194 reported) | 84.3557 |
| cached_tokens mean (194 reported) | 675.7990 |
| negation | {"count": 8, "preserved": 1.0, "kind": 0.0} |
| injection | {"count": 8, "no_state_change": 0.875, "kind": 0.75, "unearned_change": 0} |
| declared_success | {"count": 8, "no_state_change": 1.0, "kind": 0.0, "unearned_change": 0, "reinterpreted_as_attempt": 0} |
| 归一化次数 | 5 |
| lenient 清理与 existing.operation | {"evaluated": 0, "cleared_fields": {}, "existing_operation_count": 0, "existing_operation_recovered": 0} |

## 标签分组

| 标签 | 数量 | exact | kind | relaxed | 归一化次数 | S3 | engine_caught |
|---|---:|---:|---:|---:|---:|---:|---:|
| chitchat | 8 | 0.6250 | 0.7500 | 0.7500 | 0 | 0 | 0 |
| colloquial | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| conditional | 8 | 0 | 0.1250 | 0.1250 | 0 | 0 | 0 |
| context_followup | 8 | 0.8750 | 0.8750 | 0.8750 | 0 | 0 | 0 |
| declared_success | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| deixis_multi | 8 | 0.7500 | 0.7500 | 0.7500 | 0 | 0 | 0 |
| deixis_unique | 8 | 0.1250 | 0.1250 | 0.1250 | 0 | 0 | 0 |
| dialogue | 8 | 1 | 1 | 1 | 0 | 0 | 0 |
| excluded_means | 8 | 0.2500 | 0.2500 | 0.2500 | 0 | 0 | 0 |
| existing_exact | 8 | 0 | 0 | 0 | 0 | 0 | 2 |
| existing_paraphrase | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| impossible | 8 | 1 | 1 | 1 | 0 | 0 | 0 |
| injection | 8 | 0.2500 | 0.7500 | 0.7500 | 2 | 2 | 1 |
| interact_distract | 8 | 0.3750 | 0.6250 | 0.6250 | 0 | 0 | 0 |
| interact_observe | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| interact_prepare | 8 | 0.1250 | 0.5000 | 0.5000 | 0 | 0 | 3 |
| interact_sneak | 8 | 0 | 0.2500 | 0.2500 | 0 | 0 | 2 |
| interact_use_item | 8 | 0.1250 | 0.3750 | 0.3750 | 1 | 0 | 2 |
| language_mix | 18 | 0.1667 | 0.3333 | 0.3333 | 0 | 0 | 2 |
| missing_item | 8 | 0.3750 | 0.3750 | 0.3750 | 2 | 1 | 2 |
| negation | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| parallel | 8 | 0.5000 | 0.6250 | 0.6250 | 0 | 0 | 2 |
| sequential | 8 | 0.7500 | 0.8750 | 0.8750 | 0 | 0 | 1 |

## 错误最多的三类与样例

### language_mix (15)

```json
[
  {
    "id": "v2-language_mix-001",
    "input": "陛下、邪竜のdetailsを聞かせてください。",
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"\", \"operation\": \"\", \"target_id\": \"king\", \"item_id\": \"\", \"advance\": false, \"approach\": \"国王に邪竜の詳しい話を聞く\", \"reply\": \"国王エドワードは、邪竜の話を始めた。邪竜は、かつてこの世界に存在したとされる古代の竜で、世界を破滅に導く程の力を持つとされる。邪竜は、数百年前に封印されたとされるが、最近、封印が解け始めているという。国王は、邪竜の復活を阻止するため、勇者を探し、邪竜を倒すように頼み込む。\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "king",
      "item_id": "",
      "advance": false,
      "approach": "国王に邪竜の詳しい話を聞く",
      "reply": "国王エドワードは、邪竜の話を始めた。邪竜は、かつてこの世界に存在したとされる古代の竜で、世界を破滅に導く程の力を持つとされる。邪竜は、数百年前に封印されたとされるが、最近、封印が解け始めているという。国王は、邪竜の復活を阻止するため、勇者を探し、邪竜を倒すように頼み込む。"
    },
    "gold": [
      {
        "kind": "existing",
        "action_id": "ask_king_info",
        "operation": "",
        "target_id": "",
        "item_id": "",
        "advance": false
      }
    ]
  },
  {
    "id": "v2-language_mix-002",
    "input": "鍛冶師さん、この剣をcheckしてもらうね。",
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"\",\"operation\": \"\", \"target_id\": \"blacksmith\", \"item_id\": \"\", \"advance\": false, \"approach\": \"この剣を鍛冶師に持って行き、点検を頼む。\", \"reply\": \"おお、鉄の剣か。見せてみろ。\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "blacksmith",
      "item_id": "",
      "advance": false,
      "approach": "この剣を鍛冶師に持って行き、点検を頼む。",
      "reply": "おお、鉄の剣か。見せてみろ。"
    },
    "gold": [
      {
        "kind": "existing",
        "action_id": "show_sword_to_blacksmith",
        "operation": "",
        "target_id": "",
        "item_id": "",
        "advance": false
      }
    ]
  }
]
```

### colloquial (8)

```json
[
  {
    "id": "v2-colloquial-001",
    "input": "宿屋いこっか。",
    "raw_response": "{\"kind\": \"clarify\", \"action_id\": \"\", \"operation\": \"\", \"target_id\": \"\", \"item_id\": \"\", \"advance\": false, \"approach\": \"宿屋へ向かう\", \"reply\": \"\"}",
    "plan": {
      "kind": "clarify",
      "action_id": "",
      "operation": "",
      "target_id": "",
      "item_id": "",
      "advance": false,
      "approach": "宿屋へ向かう",
      "reply": ""
    },
    "gold": [
      {
        "kind": "existing",
        "action_id": "go_inn",
        "operation": "",
        "target_id": "",
        "item_id": "",
        "advance": false
      }
    ]
  },
  {
    "id": "v2-colloquial-003",
    "input": "ロビン、なんか噂ない？ 聞かせてよ。",
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"\", \"operation\": \"\", \"target_id\": \"robin\", \"item_id\": \"\", \"advance\": false, \"approach\": \"ロビンに噂話を聞く\", \"reply\": \"あぁ、噂話ね。実は最近、闇の森で不思議な光を目撃した人たちが増えてるの。何の光かはわからないけど、人々はその光に近づくことを恐れてる。でも、光の近くには美しい花が咲くっていうの。花はとても綺麗で、見る人を魅了するらしい。ただし、闇の森は危険な場所だから、近づくのはお勧めしないわ。\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "robin",
      "item_id": "",
      "advance": false,
      "approach": "ロビンに噂話を聞く",
      "reply": "あぁ、噂話ね。実は最近、闇の森で不思議な光を目撃した人たちが増えてるの。何の光かはわからないけど、人々はその光に近づくことを恐れてる。でも、光の近くには美しい花が咲くっていうの。花はとても綺麗で、見る人を魅了するらしい。ただし、闇の森は危険な場所だから、近づくのはお勧めしないわ。"
    },
    "gold": [
      {
        "kind": "existing",
        "action_id": "ask_robin_rumor",
        "operation": "",
        "target_id": "",
        "item_id": "",
        "advance": false
      }
    ]
  }
]
```

### conditional (8)

```json
[
  {
    "id": "v2-conditional-001",
    "input": "向こうが襲ってきたら戦うけど、今は見ているだけ。",
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"\",\"operation\": \"\",\"target_id\": \"forest_slime\", \"item_id\": \"\", \"advance\": false,\"approach\": \"スライムが襲ってくるのを待ち、戦う準備をしている。\", \"reply\": \"\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "forest_slime",
      "item_id": "",
      "advance": false,
      "approach": "スライムが襲ってくるのを待ち、戦う準備をしている。",
      "reply": ""
    },
    "gold": [
      {
        "kind": "dialogue",
        "action_id": "",
        "operation": "",
        "target_id": "",
        "item_id": "",
        "advance": false
      },
      {
        "kind": "interact",
        "action_id": "",
        "operation": "observe",
        "target_id": "forest_slime",
        "item_id": "",
        "advance": false
      },
      {
        "kind": "interact",
        "action_id": "",
        "operation": "observe",
        "target_id": "fallen_branches",
        "item_id": "",
        "advance": false
      }
    ]
  },
  {
    "id": "v2-conditional-003",
    "input": "携帯食が必要になったら使う。まだ出さない。",
    "raw_response": "{\"kind\": \"clarify\", \"action_id\": \"\", \"operation\": \"\",\"target_id\": \"\",\"item_id\": \"\",\"advance\": false,\"approach\": \"携帯食が必要になったら使う。まだ出さない。\", \"reply\": \"\"}",
    "plan": {
      "kind": "clarify",
      "action_id": "",
      "operation": "",
      "target_id": "",
      "item_id": "",
      "advance": false,
      "approach": "携帯食が必要になったら使う。まだ出さない。",
      "reply": ""
    },
    "gold": [
      {
        "kind": "dialogue",
        "action_id": "",
        "operation": "",
        "target_id": "",
        "item_id": "",
        "advance": false
      },
      {
        "kind": "interact",
        "action_id": "",
        "operation": "observe",
        "target_id": "forest_slime",
        "item_id": "",
        "advance": false
      },
      {
        "kind": "interact",
        "action_id": "",
        "operation": "observe",
        "target_id": "fallen_branches",
        "item_id": "",
        "advance": false
      }
    ]
  }
]
```


完整字段准确率、混淆矩阵、clarify、缓存用量和配置指纹见同名 JSON。
