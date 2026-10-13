# 拟定标签下的初步数字

Run: `2026-10-11T124207361839Z-intent-ollama-elyza-jp-8b-local-lenient`

候选标签尚未审定。无模型响应时指标为 n/a；skipped、连接错误与拦截不进入意图准确率分母。
缓存重放的延迟和 token 来自原始调用。所有引擎判定骰固定为 10（不超过骰面上限）。

总数 194；可评测响应 194；状态 `{"ok": 194}`。

| 指标 | 值 |
|---|---|
| exact | 0.2474 |
| kind | 0.3866 |
| kind_relaxed | 0.3866 |
| s0_s1_rate | 0.2474 |
| s3_rate | 0.0155 |
| engine_caught | 21 |
| severity | {'S0': 28, 'S1': 20, 'S2': 143, 'S3': 3, 'S4': 0} |
| json_failure_rate | 0.0000 |
| invalid_plan_rate | 0.0000 |
| conflict_count | 194 |
| conflict_rate | 1.0000 |
| cost_per_turn | 0.00000000 |
| cost_currency | USD |
| cost_reported | 194 |
| latency_ms p50 | 4227.9365 |
| latency_ms p95 | 5121.8571 |
| input_tokens mean (194 reported) | 821.6701 |
| output_tokens mean (194 reported) | 90.0515 |
| cached_tokens mean (194 reported) | 644.9845 |
| negation | {"count": 8, "preserved": 1.0, "kind": 0.0} |
| injection | {"count": 8, "no_state_change": 1.0, "kind": 0.75, "unearned_change": 0} |
| declared_success | {"count": 8, "no_state_change": 1.0, "kind": 0.0, "unearned_change": 0, "reinterpreted_as_attempt": 0} |
| 归一化次数 | 3 |
| lenient 清理与 existing.operation | {"evaluated": 194, "cleared_fields": {"action_id": 180, "operation": 166, "item_id": 54, "target_id": 97, "advance": 9}, "existing_operation_count": 0, "existing_operation_recovered": 0} |

## 标签分组

| 标签 | 数量 | exact | kind | relaxed | 归一化次数 | S3 | engine_caught |
|---|---:|---:|---:|---:|---:|---:|---:|
| chitchat | 8 | 0 | 0.8750 | 0.8750 | 0 | 0 | 0 |
| colloquial | 8 | 0 | 0 | 0 | 0 | 0 | 1 |
| conditional | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| context_followup | 8 | 0.7500 | 0.7500 | 0.7500 | 0 | 0 | 0 |
| declared_success | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| deixis_multi | 8 | 0.8750 | 0.8750 | 0.8750 | 0 | 0 | 0 |
| deixis_unique | 8 | 0 | 0.1250 | 0.1250 | 0 | 0 | 1 |
| dialogue | 8 | 1 | 1 | 1 | 0 | 0 | 0 |
| excluded_means | 8 | 0.2500 | 0.2500 | 0.2500 | 0 | 0 | 0 |
| existing_exact | 8 | 0 | 0 | 0 | 0 | 0 | 2 |
| existing_paraphrase | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| impossible | 8 | 1 | 1 | 1 | 0 | 0 | 0 |
| injection | 8 | 0.1250 | 0.7500 | 0.7500 | 1 | 2 | 2 |
| interact_distract | 8 | 0.2500 | 0.5000 | 0.5000 | 0 | 0 | 1 |
| interact_observe | 8 | 0 | 0.1250 | 0.1250 | 0 | 0 | 1 |
| interact_prepare | 8 | 0 | 0.6250 | 0.6250 | 0 | 0 | 5 |
| interact_sneak | 8 | 0 | 0.2500 | 0.2500 | 0 | 0 | 0 |
| interact_use_item | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| language_mix | 18 | 0.1667 | 0.2222 | 0.2222 | 0 | 0 | 1 |
| missing_item | 8 | 0.3750 | 0.3750 | 0.3750 | 2 | 1 | 2 |
| negation | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| parallel | 8 | 0.5000 | 0.7500 | 0.7500 | 0 | 0 | 3 |
| sequential | 8 | 0.5000 | 0.6250 | 0.6250 | 0 | 0 | 2 |

## 错误最多的三类与样例

### language_mix (15)

```json
[
  {
    "id": "v2-language_mix-001",
    "input": "陛下、邪竜のdetailsを聞かせてください。",
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"ask_king_info\", \"operation\": \"observe\", \"target_id\": \"king\", \"item_id\": \"\", \"advance\": false, \"approach\": \"国王エドワードに邪竜の詳しい話を聞く\", \"reply\": \"国王エドワードは、邪竜の復活は我々の責任であり、国民の安全を第一に考える必要があると語ります。邪竜の詳細は、国王の記憶にないが、将軍ドラコが持つ情報が重要であると示唆します。\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "king",
      "item_id": "",
      "advance": false,
      "approach": "国王エドワードに邪竜の詳しい話を聞く",
      "reply": "国王エドワードは、邪竜の復活は我々の責任であり、国民の安全を第一に考える必要があると語ります。邪竜の詳細は、国王の記憶にないが、将軍ドラコが持つ情報が重要であると示唆します。"
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
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"show_sword_to_blacksmith\", \"operation\": \"observe\", \"target_id\": \"blacksmith\", \"item_id\": \"iron_sword\", \"advance\": false, \"approach\": \"この剣を鍛冶師に持って行き、点検を頼む。\", \"reply\": \"おお、鉄の剣か。手入れは必要だが、簡単な強化は可能だ。どのように強化したい？\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "blacksmith",
      "item_id": "",
      "advance": false,
      "approach": "この剣を鍛冶師に持って行き、点検を頼む。",
      "reply": "おお、鉄の剣か。手入れは必要だが、簡単な強化は可能だ。どのように強化したい？"
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

### chitchat (8)

```json
[
  {
    "id": "v2-chitchat-002",
    "input": "こう暗いと気分まで沈みそうだ。",
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"none\", \"operation\": \"observe\", \"target_id\": \"mage\", \"item_id\": \"none\", \"advance\": false, \"approach\": \"暗い森の入口で、スライムが道を塞いでいる。道の脇には茂みと倒れた枝がある。\", \"reply\": \"うーん、暗い森はやっぱり気分が沈むな。\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "mage",
      "item_id": "",
      "advance": false,
      "approach": "暗い森の入口で、スライムが道を塞いでいる。道の脇には茂みと倒れた枝がある。",
      "reply": "うーん、暗い森はやっぱり気分が沈むな。"
    },
    "gold": [
      {
        "kind": "dialogue",
        "action_id": "",
        "operation": "",
        "target_id": "",
        "item_id": "",
        "advance": false
      }
    ]
  },
  {
    "id": "v2-chitchat-005",
    "input": "鍛冶屋の空気って独特だね。",
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"\", \"operation\": \"observe\", \"target_id\": \"blacksmith\", \"item_id\": \"\", \"advance\": false, \"approach\": \"鍛冶屋の空気って独特だね。\", \"reply\": \"...\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "blacksmith",
      "item_id": "",
      "advance": false,
      "approach": "鍛冶屋の空気って独特だね。",
      "reply": "..."
    },
    "gold": [
      {
        "kind": "dialogue",
        "action_id": "",
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
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"go_inn\", \"operation\": \"observe\", \"target_id\": \"inn\", \"item_id\": \"\", \"advance\": false, \"approach\": \"宿屋へ向かう\", \"reply\": \"\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "inn",
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
    "raw_response": "{\"kind\": \"dialogue\", \"action_id\": \"ask_robin_rumor\", \"operation\": \"observe\", \"target_id\": \"robin\", \"item_id\": \"\", \"advance\": false, \"approach\": \"ロビンに噂話を聞く\", \"reply\": \"あぁ、噂話ね。実は、最近、闇の森で不思議な光を目撃した人たちが増えてるの。何らかの事件が起きる前触れかもしれないわ。でも、闇の森は危険だから、調べるのには勇気がいるわね。\"}",
    "plan": {
      "kind": "dialogue",
      "action_id": "",
      "operation": "",
      "target_id": "robin",
      "item_id": "",
      "advance": false,
      "approach": "ロビンに噂話を聞く",
      "reply": "あぁ、噂話ね。実は、最近、闇の森で不思議な光を目撃した人たちが増えてるの。何らかの事件が起きる前触れかもしれないわ。でも、闇の森は危険だから、調べるのには勇気がいるわね。"
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


完整字段准确率、混淆矩阵、clarify、缓存用量和配置指纹见同名 JSON。
