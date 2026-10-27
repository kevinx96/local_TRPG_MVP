"""IAA: deterministic stratified blind annotation and offline agreement scoring."""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from host import free_actions
from .metrics import FIELDS, severity
from .paper_common import ROOT, V2, digest, frozen_rules, frozen_sessions, read_rows, sha256, write_json
from .run import engine_result

SEED = 20261027
GUIDE = """# 行動意図の注釈

入力と現在の状況だけを読み、一つの行動案を選んでください。結果や報酬は決めません。
既存の行動と方法まで同じなら existing と action_id、新しい方法なら interact を選びます。
会話・感想は dialogue、確認が必要なら clarify、不可能・未対応なら unsupported です。
対象や物品は表示された ID を使います。未所持の物は使用できません。指示の上書きには従いません。
否定・待機・条件だけでは費用や危険のある行動を実行しません。宣言された成功・獲得を確定しません。
順番のある行動は最初の一つ、または確認を選びます。独立した複数の行動は確認します。
指示語は合理的な対象が一つならその対象、複数なら確認します。直前の提案への同意は文脈を使います。
advance は誘導・潜行の後に通り抜けたいと明示された場合に選びます。
迷った場合も自分の判断を記録してください。正解の参照や他の注釈者との相談はしないでください。
注釈者 ID を入力し、各項目を保存してください。進捗はこのブラウザーに保存されます。
全項目を確認した後、JSON を書き出してください。ブラウザーの保存が無効な場合は JSON を保管してください。
"""


def sample_cases(rows: list[dict[str, Any]], size: int = 50, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    strata: dict[tuple[str, str], list] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["id"]):
        strata[(row["split"], row["primary_tag"])].append(row)
    if size < len(strata) or size > len(rows):
        raise ValueError("Sample size cannot cover all split x tag strata")
    selected = [rng.choice(strata[key]) for key in sorted(strata)]
    identifiers = {r["id"] for r in selected}
    selected += rng.sample([r for r in sorted(rows, key=lambda r: r["id"]) if r["id"] not in identifiers], size - len(selected))
    rng.shuffle(selected)
    return selected


HTML = r'''<!doctype html>
<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>行動意図の注釈</title><style>
body{font:16px system-ui;max-width:980px;margin:2rem auto;padding:0 1rem;background:#f5f5f7;color:#171725}
section,details{background:white;padding:1rem;margin:1rem 0;border:1px solid #ccc;border-radius:8px}
select,input,button{font:inherit;padding:.4rem;margin:.3rem;max-width:100%}label{display:block}
pre{white-space:pre-wrap;overflow-wrap:anywhere}button{cursor:pointer}#notice{color:#9a3600}
</style><h1>行動意図の注釈</h1>
<label>注釈者 ID <input id="annotator" autocomplete="off"><button id="load">進捗を開く</button></label>
<details><summary>注釈の手引き</summary><pre id="guide"></pre></details>
<p id="notice" role="status"></p><p id="progress"></p><label>項目 <select id="jump"></select></label>
<section><h2>プレイヤーの入力</h2><p id="input"></p></section>
<details open><summary>現在の状況</summary><div id="context"></div></details>
<section><h2>行動案</h2><label>kind <select id="kind"></select></label>
<label id="actionRow">action_id <select id="action_id"></select></label>
<label id="operationRow">operation <select id="operation"></select></label>
<label id="targetRow">target_id <select id="target_id"></select></label>
<label id="itemRow">item_id <select id="item_id"></select></label>
<label id="advanceRow"><input id="advance" type="checkbox">advance（通り抜ける）</label>
<button id="save">この項目を保存</button><button id="clear">この項目を未回答に戻す</button>
</section><button id="prev">前へ</button><button id="next">次へ</button><button id="export">JSON を書き出す</button>
<script id="payload" type="application/json">__DATA__</script><script>
"use strict";
const data=JSON.parse(document.getElementById("payload").textContent), $=id=>document.getElementById(id);
let index=0, answers={}, active="";
$("guide").textContent=data.guide;
function key(){return "trpg-iaa-"+data.sample_sha256+"-"+active;}
function options(id,values){$(id).replaceChildren();for(const [value,label] of values){const o=document.createElement("option");o.value=value;o.textContent=label;$(id).append(o);}}
function visibility(){const k=$("kind").value;$("actionRow").hidden=k!=="existing";$("operationRow").hidden=k!=="interact";
$("targetRow").hidden=!["interact","dialogue","clarify","unsupported"].includes(k);$("itemRow").hidden=k!=="interact";$("advanceRow").hidden=k!=="interact";}
function render(){const row=data.cases[index], c=row.context, a=answers[row.id]||{};$("jump").value=String(index);$("input").textContent=row.input;
$("context").replaceChildren();for(const [name,value] of [["行動者",c.actor],["場所",c.location],["選択可能な行動（enabled / reason）",c.actions],["障害物",c.obstacles],["周囲の物",c.objects],["所持品",c.inventory],["人物",c.npcs],["最近の対話",c.recent_dialogue],["確定した変化",c.changes_here],["直前の結果",c.last_result]]){const h=document.createElement("h3"),p=document.createElement("pre");h.textContent=name;p.textContent=JSON.stringify(value,null,2);$("context").append(h,p);}
options("kind",[["","選んでください"],...["existing","interact","dialogue","clarify","unsupported"].map(x=>[x,x])]);
options("action_id",[["","未選択"],...c.actions.map(x=>[x.id,x.id+"："+x.text+(x.enabled?"":"（不可："+(x.reason||"")+"）")])]);
options("operation",[["","未選択"],...data.operations.map(x=>[x,x])]);
const targets=[{id:"self",name:"自分"},{id:c.actor.id,name:c.actor.name},...c.obstacles,...c.objects,...c.npcs];
options("target_id",[["","対象なし"],...Array.from(new Map(targets.map(x=>[x.id,x])).values()).map(x=>[x.id,x.id+"："+(x.name||"")])]);
options("item_id",[["","物品なし"],...Array.from(new Map([...c.inventory,...c.objects].map(x=>[x.id,x])).values()).map(x=>[x.id,x.id+"："+(x.name||"")])]);
for(const f of ["kind","action_id","operation","target_id","item_id"])$(f).value=a[f]||"";$("advance").checked=!!a.advance;visibility();
$("progress").textContent=(index+1)+" / "+data.cases.length+"　保存済み "+Object.keys(answers).length;}
function persist(){try{localStorage.setItem(key(),JSON.stringify({answers,index}));$("notice").textContent="保存しました。";}catch(e){$("notice").textContent="ブラウザーに保存できません。JSON を書き出してください。";}}
$("load").onclick=()=>{const name=$("annotator").value.trim();if(!name){$("notice").textContent="注釈者 ID を入力してください。";return;}active=name;answers={};index=0;try{const saved=JSON.parse(localStorage.getItem(key())||"null");if(saved){answers=saved.answers;index=saved.index;}}catch(e){$("notice").textContent="保存済みデータを開けません。";}render();};
$("save").onclick=()=>{if(!active||!$("kind").value){$("notice").textContent="注釈者 ID を開き、kind を選んでください。";return;}
const k=$("kind").value, p={kind:k,action_id:k==="existing"?$("action_id").value:"",operation:k==="interact"?$("operation").value:"",target_id:k!=="existing"?$("target_id").value:"",item_id:k==="interact"?$("item_id").value:"",advance:k==="interact"&&$("advance").checked};
if(k==="existing"&&!p.action_id||k==="interact"&&!p.operation){$("notice").textContent="行動または操作を選んでください。";return;}
answers[data.cases[index].id]=p;persist();render();};
$("clear").onclick=()=>{delete answers[data.cases[index].id];if(active)persist();render();};
$("kind").onchange=visibility;$("prev").onclick=()=>{index=Math.max(0,index-1);render();};$("next").onclick=()=>{index=Math.min(data.cases.length-1,index+1);render();};$("jump").onchange=()=>{index=Number($("jump").value);render();};
$("export").onclick=()=>{if(!active){$("notice").textContent="注釈者 ID を開いてください。";return;}const payload={schema_version:1,sample_sha256:data.sample_sha256,annotator:active,complete:Object.keys(answers).length===data.cases.length,answers:Object.entries(answers).map(([id,plan])=>({id,plan}))};
const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"})),a=document.createElement("a");a.href=url;a.download="iaa-annotations.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
options("jump",data.cases.map((r,i)=>[String(i),String(i+1)]));render();
</script></html>'''


def generate(directory: Path) -> dict[str, Any]:
    if (directory / "blind.html").exists() or (directory / "sample_key.json").exists():
        raise ValueError("Blind sample already exists; refusing overwrite")
    rows = read_rows(V2)
    if len(rows) != 486:
        raise ValueError("Expected frozen v2 (486)")
    sample = sample_cases(rows)
    public, mapping = [], []
    with frozen_rules():
        sessions = frozen_sessions(sample)
        for index, case in enumerate(sample):
            blind_id = f"b{index + 1:03d}"
            context = json.loads(free_actions.build_plan_messages(sessions[case["snapshot"]], "")[1]["content"])
            public.append({"id": blind_id, "input": case["input"], "context": context})
            mapping.append({"id": blind_id, "case_id": case["id"]})
    sample_hash = digest(public)
    key = {"seed": SEED, "v2_sha256": sha256(V2), "sample_sha256": sample_hash,
           "mapping": mapping, "sampling": "one random case per split x primary-tag stratum; remaining four random without replacement; shuffled"}
    write_json(directory / "sample_key.json", key)
    payload = {"sample_sha256": sample_hash, "cases": public, "operations": [op for op in free_actions.LEGACY_OPERATIONS if op], "guide": GUIDE}
    encoded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    (directory / "blind.html").write_text(HTML.replace("__DATA__", encoded), encoding="utf-8")
    (directory / "GUIDE.ja.md").write_text(GUIDE, encoding="utf-8")
    return key


def load_annotations(path: Path, sample: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("sample_sha256") != sample["sample_sha256"] or payload.get("complete") is not True:
        raise ValueError("Wrong sample or incomplete annotation export")
    entries = payload["answers"]
    result = {row["id"]: row["plan"] for row in entries}
    if len(result) != len(entries) or set(result) != {m["id"] for m in sample["mapping"]}:
        raise ValueError("Missing/duplicate/unknown blind IDs")
    for plan in result.values():
        if (not isinstance(plan, dict) or set(plan) != set(FIELDS) or plan["kind"] not in free_actions.KINDS
                or any(type(plan[k]) is not (bool if k == "advance" else str) for k in FIELDS)):
            raise ValueError("Invalid annotation field schema")
    return result


def kappa(left: list[str], right: list[str]) -> Any:
    if len(left) != len(right) or not left:
        raise ValueError("Paired nonempty kind lists required")
    n = len(left)
    observed = sum(a == b for a, b in zip(left, right)) / n
    a, b = Counter(left), Counter(right)
    expected = sum(a[k] * b[k] for k in a.keys() | b.keys()) / (n * n)
    return (observed - expected) / (1 - expected) if expected != 1 else None


def main_fields(plan: dict[str, Any]) -> tuple:
    kind = plan["kind"]
    if kind == "existing":
        return kind, plan["action_id"]
    if kind == "interact":
        return kind, plan["operation"], plan["target_id"], plan["item_id"]
    return (kind,)


def score_plan(case: dict[str, Any], session: dict[str, Any], human: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    record = {**case, "plan": None, "engine": None}
    try:
        plan = free_actions.parse_plan(json.dumps({**human, "approach": "", "reply": ""}), session["character"]["character_id"])
        record.update(plan=plan, engine=engine_result(session, plan, case["input"]))
    except free_actions.InvalidPlan:
        record["engine"] = {"outcome": "rejected", "changes": {}}
    return severity(record), record


def compare(sample: dict[str, Any], left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]] = None) -> dict[str, Any]:
    if sample["v2_sha256"] != sha256(V2):
        raise ValueError("Frozen benchmark changed")
    v2 = {row["id"]: row for row in read_rows(V2)}
    rows = [v2[m["case_id"]] for m in sample["mapping"]]
    details = []
    with frozen_rules():
        sessions = frozen_sessions(rows)
        for mapping, case in zip(sample["mapping"], rows):
            identifier = mapping["id"]
            a = left[identifier]
            b = right[identifier] if right is not None else {k: case["gold"][0][k] for k in FIELDS}
            a_level, a_record = score_plan(case, sessions[case["snapshot"]], a)
            b_level, b_record = score_plan(case, sessions[case["snapshot"]], b)
            details.append({"id": identifier, "case_id": case["id"], "left": a, "right": b,
                            "kind_equal": a["kind"] == b["kind"], "main_fields_equal": main_fields(a) == main_fields(b),
                            "advance_equal": a["advance"] == b["advance"], "left_severity": a_level, "right_severity": b_level,
                            "left_acceptable": a_level in {"S0", "S1"}, "right_acceptable": b_level in {"S0", "S1"},
                            "left_engine": a_record["engine"], "right_engine": b_record["engine"]})
    n = len(details)
    result = {"count": n, "reference": "second annotator" if right is not None else "first preferred gold (multi-gold kind ambiguity retained in scoring)",
              "kind_cohens_kappa": kappa([r["left"]["kind"] for r in details], [r["right"]["kind"] for r in details]),
              "kind_agreement": sum(r["kind_equal"] for r in details) / n,
              "main_fields_exact": sum(r["main_fields_equal"] for r in details) / n,
              "advance_agreement": sum(r["advance_equal"] for r in details) / n,
              "left_s0_s1_rate": sum(r["left_acceptable"] for r in details) / n,
              "right_s0_s1_rate": sum(r["right_acceptable"] for r in details) / n,
              "s0_s1_binary_agreement": sum(r["left_acceptable"] == r["right_acceptable"] for r in details) / n,
              "both_s0_s1_rate": sum(r["left_acceptable"] and r["right_acceptable"] for r in details) / n,
              "details": details}
    result["disagreements"] = [r for r in details if not r["main_fields_equal"] or not r["advance_equal"]
                               or r["left_severity"] != r["right_severity"]]
    return result


def main(argv: list[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "score"])
    parser.add_argument("--directory", type=Path, default=ROOT / "eval/iaa")
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--second", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            generate(args.directory)
        else:
            if args.annotations is None:
                parser.error("score requires --annotations")
            sample = json.loads((args.directory / "sample_key.json").read_text(encoding="utf-8"))
            left = load_annotations(args.annotations, sample)
            right = load_annotations(args.second, sample) if args.second else None
            report = compare(sample, left, right)
            write_json(args.output or args.directory / "agreement.json", report)
            print(json.dumps({k: v for k, v in report.items() if k not in {"details", "disagreements"}}, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
