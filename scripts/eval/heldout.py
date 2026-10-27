"""E9: preregister before authoring, audit/lock labels, then permit one formal run."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host import free_actions, llm_client, state
from .benchmark_v2 import TAGS, similarity_violations
from .metrics import FIELDS, summarize
from .paper_common import HIGH_RISK, ROOT, V2, digest, estimate, frozen_rules, frozen_sessions, read_rows, sha256, write_json, write_rows
from .requests import evaluation_config
from .run import evaluate_case
from .variants import VARIANTS

DEFAULT_DIR = ROOT / "eval/benchmark/heldout_v3"
LOCKED_FILES = ("preregistration.json", "PREREGISTRATION.md", "slots.jsonl", "cases.jsonl")
PARAMETERS = {"backend": "gemini", "model": "gemini-3.1-flash-lite", "variant": "default",
              "scoring_version": "v1.2", "main_metrics": ["s0_s1_rate", "s3_rate"],
              "split": "test", "temperature": 0.2, "max_tokens": 700,
              "rpm": 14, "timeout": 60, "repetitions": 1, "no_cache": True}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, encoding="utf-8").strip()


def frozen_sha256(path: Path) -> str:
    """SHA-256 of the committed content: text files hash with LF endings, so a CRLF checkout (core.autocrlf) matches."""
    if path.suffix not in {".py", ".md", ".json", ".jsonl", ".txt"}:
        return sha256(path)
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def freeze_files() -> dict[str, Any]:
    # Include transitive engine/context dependencies, not only the top-level scoring function.
    # E9 scores with the default variant through run.evaluate_case; full_llm (E8) is not an input to the formal run.
    modules = ("__init__", "audit", "benchmark_v2", "cache", "generate_candidates", "metrics", "requests",
               "run", "snapshots", "variants", "paper_common", "heldout")
    tracked_host = [ROOT / name for name in git("ls-files", "--", "host").splitlines()
                    if len(Path(name).parts) == 2 and Path(name).suffix == ".py"]
    paths = sorted([*tracked_host, *[ROOT / f"scripts/eval/{name}.py" for name in modules],
                    ROOT / "scripts/evaluate_free_actions.py", ROOT / "eval/benchmark/LABELING.md",
                    ROOT / "eval/prices.json", V2,
                    *[ROOT / "eval/snapshots" / f"{identifier}.json"
                      for identifier in {row["snapshot"] for row in read_rows(V2)}],
                    ROOT / "eval/benchmark/scenario_frozen/dragon_rpg@f41af9d.json"])
    return {p.relative_to(ROOT).as_posix(): {"sha256": frozen_sha256(p),
             "last_commit": git("log", "-1", "--format=%H", "--", p.relative_to(ROOT).as_posix()) or None}
            for p in paths}


def prompt_fingerprints() -> dict[str, str]:
    row = read_rows(V2)[0]
    with frozen_rules():
        session = frozen_sessions([row])[row["snapshot"]]
        messages, configured = VARIANTS["default"].prepare(session, "", {})
    return {"default_system_prompt_sha256": digest(messages[0]["content"]),
            "planner_schema_sha256": digest(configured["response_format"])}


def preregister(directory: Path) -> None:
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Preregistration directory must be empty; refusing overwrite")
    registration = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
                    "commit": git("rev-parse", "HEAD"), "parameters": PARAMETERS,
                    "files": freeze_files(), **prompt_fingerprints(),
                    "commitment": "Generate inputs only after registration. One formal attempt, no relabeling or primary rescoring after results. Errors reported separately.",
                    "provenance": "Input slots only; argon authors Japanese inputs; design reviews labels under LABELING.md.",
                    "workspace_note": "File hashes (text files hashed with LF line endings), including uncommitted workspace files, are authoritative; commit alone is insufficient."}
    write_json(directory / "preregistration.json", registration)
    markdown = ("# E9 heldout_v3 预注册\n\n"
                "本文件和 preregistration.json 在生成槽位之前写入。评分 v1.2 与最终默认提示词固定。\n\n"
                f"Commit: `{registration['commit']}`。逐文件 commit 和 SHA-256 见 `preregistration.json`。\n\n"
                "模型 gemini-3.1-flash-lite；变体 default（冻结 v2 兼容模式）；test；"
                "主指标 S0+S1 比例、S3 比例；temperature=0.2，max_tokens=700。\n\n"
                "只允许一次正式尝试。正式执行开始即占用名额，中断或错误也不得自动重跑；"
                "跑后不得改标签并重算主结果，发现问题只能列于报告。离线预览与 fake 不占正式名额。\n\n"
                "输入由 argon 起草，设计负责人依据 LABELING.md 审定；工具不生成输入和 gold。"
                "相似度检查不能证明语义家族隔离，锁定前必须人工复核。\n\n"
                "完整冻结清单（不得修改）：\n\n```json\n" +
                json.dumps(registration, ensure_ascii=False, indent=2) + "\n```\n")
    (directory / "PREREGISTRATION.md").write_text(markdown, encoding="utf-8")


def verify_registration(directory: Path) -> dict[str, Any]:
    registration = json.loads((directory / "preregistration.json").read_text(encoding="utf-8"))
    if registration["parameters"] != PARAMETERS:
        raise ValueError("Preregistered parameters changed")
    for name, info in registration["files"].items():
        if frozen_sha256(ROOT / name) != info["sha256"]:
            raise ValueError(f"Frozen dependency changed: {name}")
    for name, expected in prompt_fingerprints().items():
        if registration[name] != expected:
            raise ValueError(f"Frozen prompt/schema changed: {name}")
    markdown = (directory / "PREREGISTRATION.md").read_text(encoding="utf-8")
    if json.dumps(registration, ensure_ascii=False, indent=2) not in markdown:
        raise ValueError("Preregistration MD/JSON mismatch")
    return registration


def generate_slots(directory: Path) -> list[dict[str, Any]]:
    verify_registration(directory)
    destination = directory / "slots.jsonl"
    if destination.exists():
        raise ValueError("Slots already generated; refusing overwrite")
    v2 = read_rows(V2)
    slots = []
    for tag in TAGS:
        snapshots = sorted({row["snapshot"] for row in v2 if row["primary_tag"] == tag})
        for i in range(8 if tag in HIGH_RISK else 3):
            identifier = f"v3-{tag}-{i + 1:03d}"
            slots.append({"id": identifier, "primary_tag": tag, "tags": [tag],
                          "snapshot": snapshots[i % len(snapshots)], "split": "test",
                          "family": f"heldout-v3-{tag}-{i + 1:03d}",
                          "family_brief": f"{tag}：v2の言い換え・接頭辞追加・対象置換ではない新しい表現群。家族IDと表現群の説明を執筆者が確認する。",
                          "input": "", "gold": [], "harmful": None,
                          "label_status": "awaiting_author_and_design",
                          "family_isolation_reviewed": False})
    write_rows(destination, slots)
    return slots


def audit_cases(rows: list[dict[str, Any]], slots: list[dict[str, Any]], v2: list[dict[str, Any]]) -> dict[str, Any]:
    errors = []
    if len(rows) != len(slots) or {r["id"] for r in rows} != {r["id"] for r in slots}:
        errors.append("Case IDs/count must equal the slot table (99)")
    if len({r["id"] for r in rows}) != len(rows) or len({r["input"] for r in rows}) != len(rows):
        errors.append("Duplicate IDs/inputs")
    slot_map = {r["id"]: r for r in slots}
    old_families = {r["family"] for r in v2}
    old_inputs = {r["input"] for r in v2}
    for row in rows:
        identifier = row["id"]
        slot = slot_map.get(identifier, {})
        if any(row.get(k) != slot.get(k) for k in ("primary_tag", "snapshot", "split")):
            errors.append(f"{identifier}: tag/snapshot/split differs from slot")
        if not row.get("input", "").strip() or row.get("input") in old_inputs:
            errors.append(f"{identifier}: missing or v2 input")
        if (not row.get("family", "").startswith("heldout-v3-") or row["family"] in old_families
                or row.get("family_isolation_reviewed") is not True):
            errors.append(f"{identifier}: family isolation needs human review")
        if row.get("label_status") not in {"design_approved", "design_policy_v1"}:
            errors.append(f"{identifier}: labels not design approved")
        if row.get("primary_tag") not in row.get("tags", []) or set(row.get("tags", [])) - set(TAGS):
            errors.append(f"{identifier}: invalid tags")
        harmful = row.get("harmful")
        if (not isinstance(harmful, dict) or set(harmful) != {"kind", "operation", "action_id"}
                or any(not isinstance(v, list) or any(not isinstance(s, str) for s in v) for v in harmful.values())):
            errors.append(f"{identifier}: missing/invalid harmful")
        if not row.get("gold"):
            errors.append(f"{identifier}: missing gold")
        for gold in row.get("gold", []):
            try:
                if set(gold) - {*FIELDS, "tier"} or gold.get("tier", "S0") not in {"S0", "S1"}:
                    raise ValueError("invalid gold fields/tier")
                free_actions.parse_plan(json.dumps({**{k: v for k, v in gold.items() if k != "tier"},
                                                     "approach": "", "reply": ""}))
            except (ValueError, free_actions.InvalidPlan) as exc:
                errors.append(f"{identifier}: invalid gold: {exc}")
    # Same character 3-gram Jaccard > .6 rule as benchmark_v2, both within-v3 and cross-v2.
    violations = similarity_violations([*v2, *rows])
    new_ids = {r["id"] for r in rows}
    violations = [v for v in violations if v["left"] in new_ids or v["right"] in new_ids]
    counts = Counter(r.get("primary_tag") for r in rows)
    if any(counts[tag] < 3 for tag in TAGS):
        errors.append("Each primary tag needs >=3 cases")
    return {"errors": errors, "similarity_violations": violations, "counts": dict(counts), "total": len(rows)}


def lock(directory: Path, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("Lock requires --design-approved (labels AND semantic family isolation reviewed)")
    verify_registration(directory)
    path = directory / "LOCK.json"
    if path.exists() or (directory / "formal").exists():
        raise ValueError("Already locked/started; refusing overwrite")
    rows = read_rows(directory / "cases.jsonl")
    with frozen_rules():
        audit = audit_cases(rows, read_rows(directory / "slots.jsonl"), read_rows(V2))
        if audit["errors"] or audit["similarity_violations"]:
            raise ValueError(json.dumps(audit, ensure_ascii=False))
        # Validate every reviewed gold through the engine before allowing paid execution.
        from .full_llm import legal_states
        sessions = frozen_sessions(rows)
        for case in rows:
            legal_states(case, sessions[case["snapshot"]])
    result = {"created_utc": datetime.now(timezone.utc).isoformat(), "design_approved": True,
              "files": {name: sha256(directory / name) for name in LOCKED_FILES},
              "audit": audit}
    write_json(path, result)
    return result


def verify_lock(directory: Path) -> dict[str, Any]:
    registration = verify_registration(directory)
    locked = json.loads((directory / "LOCK.json").read_text(encoding="utf-8"))
    if locked.get("design_approved") is not True:
        raise ValueError("Not design approved")
    if set(locked["files"]) != set(LOCKED_FILES):
        raise ValueError("Incomplete lock manifest")
    for name, expected in locked["files"].items():
        if sha256(directory / name) != expected:
            raise ValueError(f"Locked file changed: {name}")
    return registration


def execute(directory: Path, *, live: bool = False, fake: bool = False) -> dict[str, Any]:
    if live and fake:
        raise ValueError("fake and live are mutually exclusive")
    registration = verify_lock(directory)
    params = registration["parameters"]
    rows = read_rows(directory / "cases.jsonl")
    config = evaluation_config(state.load_config(), params["backend"], params["model"],
                               rpm=params["rpm"], timeout=params["timeout"])
    with frozen_rules():
        sessions = frozen_sessions(rows)
        prediction = estimate([VARIANTS[params["variant"]].prepare(sessions[c["snapshot"]], c["input"], config)[0]
                               for c in rows], params["model"], params["max_tokens"],
                              schema=VARIANTS[params["variant"]].prepare(sessions[rows[0]["snapshot"]], "", config)[1]["response_format"])
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S%fZ")
        output = directory / "formal" if live else directory / "previews" / stamp
        # Atomic reservation: a partial/failed formal attempt also blocks a second run.
        output.mkdir(parents=True, exist_ok=False)
        write_json(output / "STARTED.json", {"live": live, "fake": fake, "lock_sha256": sha256(directory / "LOCK.json"),
                                            "parameters": params, "created_utc": stamp})
        records, failed = [], False
        fake_plan = dict(kind="unsupported", action_id="", operation="", target_id="", item_id="", advance=False,
                         approach="", reply="この行動には対応していない。")
        context = patch.object(llm_client, "chat_completion", return_value=json.dumps(fake_plan)) if fake else nullcontext()
        with context, (output / "cases.jsonl").open("w", encoding="utf-8") as stream:
            for case in rows:
                record = evaluate_case(case, sessions[case["snapshot"]], config, params["backend"], params["model"],
                                       params["variant"], output / "unused_cache", live=(live or fake) and not failed, no_cache=True)
                record["fake"] = fake
                if record["status"] in {"request_error", "quota_exhausted"}:
                    failed = True
                records.append(record)
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
    integrity_error = None
    try:
        verify_lock(directory)
    except (ValueError, OSError) as exc:
        integrity_error = str(exc)
    report = {"suite": "heldout_v3", "run_id": f"{stamp}-heldout-v3", "live": live, "fake": fake,
              "parameters": params, "estimate": prediction, "cases_sha256": sha256(directory / "cases.jsonl"),
              "lock_sha256": sha256(directory / "LOCK.json"), "integrity_error": integrity_error,
              "incomplete": failed or integrity_error is not None or any(r["status"] == "skipped" for r in records),
              "metrics": summarize(records, json.loads((ROOT / "eval/prices.json").read_text(encoding="utf-8"))["models"][params["model"]])}
    write_json(output / "report.json", report)
    return report


def main(argv: list[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preregister", "slots", "audit", "lock", "verify", "run"])
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--design-approved", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--fake", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "preregister":
            preregister(args.directory)
        elif args.command == "slots":
            print(len(generate_slots(args.directory)))
        elif args.command == "audit":
            verify_registration(args.directory)
            with frozen_rules():
                result = audit_cases(read_rows(args.directory / "cases.jsonl"), read_rows(args.directory / "slots.jsonl"), read_rows(V2))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(bool(result["errors"] or result["similarity_violations"]))
        elif args.command == "lock":
            lock(args.directory, args.design_approved)
        elif args.command == "verify":
            verify_lock(args.directory)
        else:
            report = execute(args.directory, live=args.live, fake=args.fake)
            print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
            return int(report["incomplete"] and args.live)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
