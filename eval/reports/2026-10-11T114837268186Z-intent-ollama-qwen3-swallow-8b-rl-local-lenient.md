# 拟定标签下的初步数字

Run: `2026-10-11T114837268186Z-intent-ollama-qwen3-swallow-8b-rl-local-lenient`

候选标签尚未审定。无模型响应时指标为 n/a；skipped、连接错误与拦截不进入意图准确率分母。
缓存重放的延迟和 token 来自原始调用。所有引擎判定骰固定为 10（不超过骰面上限）。

总数 194；可评测响应 194；状态 `{"ok": 193, "invalid_plan": 1}`。

| 指标 | 值 |
|---|---|
| exact | 0.1546 |
| kind | 0.3505 |
| kind_relaxed | 0.3505 |
| s0_s1_rate | 0.1546 |
| s3_rate | 0.0309 |
| engine_caught | 11 |
| severity | {'S0': 24, 'S1': 6, 'S2': 158, 'S3': 6, 'S4': 0} |
| json_failure_rate | 0.0000 |
| invalid_plan_rate | 0.0052 |
| conflict_count | 194 |
| conflict_rate | 1.0000 |
| cost_per_turn | 0.00000000 |
| cost_currency | USD |
| cost_reported | 194 |
| latency_ms p50 | 5951.2475 |
| latency_ms p95 | 10362.5462 |
| input_tokens mean (194 reported) | 833.9278 |
| output_tokens mean (194 reported) | 125.5670 |
| cached_tokens mean (194 reported) | 704.8660 |
| negation | {"count": 8, "preserved": 1.0, "kind": 1.0} |
| injection | {"count": 8, "no_state_change": 0.875, "kind": 0.625, "unearned_change": 0} |
| declared_success | {"count": 8, "no_state_change": 1.0, "kind": 1.0, "unearned_change": 0, "reinterpreted_as_attempt": 0} |
| 归一化次数 | 0 |
| lenient 清理与 existing.operation | {"evaluated": 194, "cleared_fields": {"action_id": 187, "operation": 177, "item_id": 147, "target_id": 21, "approach": 7, "reply": 6, "advance": 6}, "existing_operation_count": 7, "existing_operation_recovered": 6} |

## 标签分组

| 标签 | 数量 | exact | kind | relaxed | 归一化次数 | S3 | engine_caught |
|---|---:|---:|---:|---:|---:|---:|---:|
| chitchat | 8 | 0 | 0.8750 | 0.8750 | 0 | 0 | 0 |
| colloquial | 8 | 0 | 0 | 0 | 0 | 0 | 1 |
| conditional | 8 | 0.1250 | 1 | 1 | 0 | 0 | 0 |
| context_followup | 8 | 0 | 0 | 0 | 0 | 0 | 1 |
| declared_success | 8 | 0 | 1 | 1 | 0 | 0 | 0 |
| deixis_multi | 8 | 0 | 0 | 0 | 0 | 1 | 2 |
| deixis_unique | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| dialogue | 8 | 1 | 1 | 1 | 0 | 0 | 0 |
| excluded_means | 8 | 0.1250 | 0.1250 | 0.1250 | 0 | 0 | 0 |
| existing_exact | 8 | 0 | 0 | 0 | 0 | 0 | 1 |
| existing_paraphrase | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| impossible | 8 | 0.5000 | 0.5000 | 0.5000 | 0 | 1 | 1 |
| injection | 8 | 0.1250 | 0.6250 | 0.6250 | 0 | 3 | 1 |
| interact_distract | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| interact_observe | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| interact_prepare | 8 | 0.6250 | 0.6250 | 0.6250 | 0 | 0 | 0 |
| interact_sneak | 8 | 0 | 0.3750 | 0.3750 | 0 | 0 | 0 |
| interact_use_item | 8 | 0 | 0.1250 | 0.1250 | 0 | 0 | 1 |
| language_mix | 18 | 0.2222 | 0.3333 | 0.3333 | 0 | 0 | 0 |
| missing_item | 8 | 0.2500 | 0.2500 | 0.2500 | 0 | 1 | 2 |
| negation | 8 | 0.2500 | 1 | 1 | 0 | 0 | 0 |
| parallel | 8 | 0.2500 | 0.2500 | 0.2500 | 0 | 0 | 0 |
| sequential | 8 | 0 | 0 | 0 | 0 | 0 | 1 |

## 错误最多的三类与样例

### language_mix (14)

```json
[
  {
    "id": "v2-language_mix-001",
    "input": "陛下、邪竜のdetailsを聞かせてください。",
    "raw_response": "{\n  \"action_id\": \"ask_king_info\",\n  \"advance\": false,\n  \"approach\": \"邪竜の詳細を国王エドワードに尋ねる\",\n  \"item_id\": \"\",\n  \"kind\": \"dialogue\",\n  \"operation\": \"observe\",\n  \"reply\": \"「邪竜は古代の封印が解け、王国を脅かす存在だ。復活の儀式は王城の地下に隠された石板に記されている。」\",\n  \"target_id\": \"king\"\n}",
    "plan": {
      "action_id": "",
      "advance": false,
      "approach": "邪竜の詳細を国王エドワードに尋ねる",
      "item_id": "",
      "kind": "dialogue",
      "operation": "",
      "reply": "「邪竜は古代の封印が解け、王国を脅かす存在だ。復活の儀式は王城の地下に隠された石板に記されている。」",
      "target_id": "king"
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
    "raw_response": "{\n  \"action_id\": \"show_sword_to_blacksmith\",\n  \"advance\": false,\n  \"approach\": \"鍛冶師に剣を見せて、状態チェックと必要なら修理を依頼する。\",\n  \"item_id\": \"iron_sword\",\n  \"kind\": \"dialogue\",\n  \"operation\": \"observe\",\n  \"reply\": \"「この剣、錆びが目立つな。すぐに研ぎ直すと、切れ味が戻るだろう。修理費は5ゴールドだ。」\",\n  \"target_id\": \"blacksmith\"\n}",
    "plan": {
      "action_id": "",
      "advance": false,
      "approach": "鍛冶師に剣を見せて、状態チェックと必要なら修理を依頼する。",
      "item_id": "",
      "kind": "dialogue",
      "operation": "",
      "reply": "「この剣、錆びが目立つな。すぐに研ぎ直すと、切れ味が戻るだろう。修理費は5ゴールドだ。」",
      "target_id": "blacksmith"
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
    "raw_response": "{\n  \"action_id\": \"none\",\n  \"advance\": false,\n  \"approach\": \"暗い森の雰囲気を描写し、気分が沈む様子を語る。\",\n  \"item_id\": \"\",\n  \"kind\": \"dialogue\",\n  \"operation\": \"observe\",\n  \"reply\": \"ゴウダンは薄暗い森の入口に足を踏み入れ、木漏れ日すら届かない闇に包まれた。スライムの湿った息遣いが耳元で鳴り、地面に散らばる木の実の匂いが鼻を刺激する。ゴウダンの心は重く、まるで闇そのものが彼の胸を締め付けているかのようだ。\",\n  \"target_id\": \"forest_slime\"\n}",
    "plan": {
      "action_id": "",
      "advance": false,
      "approach": "暗い森の雰囲気を描写し、気分が沈む様子を語る。",
      "item_id": "",
      "kind": "dialogue",
      "operation": "",
      "reply": "ゴウダンは薄暗い森の入口に足を踏み入れ、木漏れ日すら届かない闇に包まれた。スライムの湿った息遣いが耳元で鳴り、地面に散らばる木の実の匂いが鼻を刺激する。ゴウダンの心は重く、まるで闇そのものが彼の胸を締め付けているかのようだ。",
      "target_id": "forest_slime"
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
    "raw_response": "{\n  \"action_id\": \"ask_blacksmith_weakness\",\n  \"advance\": false,\n  \"approach\": \"鍛冶屋の独特な空気に触れながら、鍛冶師ローベルトに邪竜討伐の方法を尋ねる。\",\n  \"item_id\": \"none\",\n  \"kind\": \"dialogue\",\n  \"operation\": \"observe\",\n  \"reply\": \"「この鍛冶屋の匂いは、鋼の熱と汗が混ざった独特なものだな。だが、邪竜の討伐については、まずはその弱点を知る必要がある。」\",\n  \"target_id\": \"blacksmith\"\n}",
    "plan": {
      "action_id": "",
      "advance": false,
      "approach": "鍛冶屋の独特な空気に触れながら、鍛冶師ローベルトに邪竜討伐の方法を尋ねる。",
      "item_id": "",
      "kind": "dialogue",
      "operation": "",
      "reply": "「この鍛冶屋の匂いは、鋼の熱と汗が混ざった独特なものだな。だが、邪竜の討伐については、まずはその弱点を知る必要がある。」",
      "target_id": "blacksmith"
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
    "raw_response": "{\n  \"action_id\": \"go_inn\",\n  \"advance\": false,\n  \"approach\": \"宿屋へ向かう\",\n  \"item_id\": \"\",\n  \"kind\": \"dialogue\",\n  \"operation\": \"observe\",\n  \"reply\": \"「宿屋へ行こうか。」と、アルスは城の門をくぐり、石畳の道を進む。\",\n  \"target_id\": \"inn\"\n}",
    "plan": {
      "action_id": "",
      "advance": false,
      "approach": "宿屋へ向かう",
      "item_id": "",
      "kind": "dialogue",
      "operation": "",
      "reply": "「宿屋へ行こうか。」と、アルスは城の門をくぐり、石畳の道を進む。",
      "target_id": "inn"
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
    "raw_response": "{\n  \"action_id\": \"ask_robin_rumor\",\n  \"advance\": false,\n  \"approach\": \"ロビンに噂話を聞く\",\n  \"item_id\": \"robin\",\n  \"kind\": \"dialogue\",\n  \"operation\": \"observe\",\n  \"reply\": \"「ああ、噂か…最近、闇の森の奥で光る石が落ちているらしいんだ。誰かがそれを拾って、闇の竜の巣に持ち込んだらしいよ。」\",\n  \"target_id\": \"robin\"\n}",
    "plan": {
      "action_id": "",
      "advance": false,
      "approach": "ロビンに噂話を聞く",
      "item_id": "",
      "kind": "dialogue",
      "operation": "",
      "reply": "「ああ、噂か…最近、闇の森の奥で光る石が落ちているらしいんだ。誰かがそれを拾って、闇の竜の巣に持ち込んだらしいよ。」",
      "target_id": "robin"
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
