"""Offline spec 030 browser assertions, keyframes and a complete guard-battle GIF."""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import threading
import time
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from host import combat, state
from scripts.balance.checkpoints import fresh_session
from scripts.screenshot_choices import Handler as StaticHandler, ROOT


def battle(location="goblin_fort", character="hero") -> dict[str, Any]:
    session = fresh_session(state.load_scenario_pack(state.DEFAULT_SCENARIO), character)
    session["world_state"] = {"location_id": location}
    session["combat_start_requested"] = True
    combat.ensure_combat_started(session)
    return session


def fixtures() -> dict[str, Any]:
    result = {}
    for name in ("normal", "critical", "miss", "fire", "ice", "holy", "rainbow", "heavy", "heal", "buff", "knockout", "phase", "reduced"):
        session = battle("draco_battle" if name == "phase" else "goblin_fort", "cleric" if name == "heal" else "hero")
        enemy = session["combat"]["enemies"][0]
        player = session["character"]
        # Isolated visual fixtures keep a durable target; production scenario values are untouched.
        if name not in {"knockout", "phase"}:
            enemy.update(hp=100, max_hp=100)
        if name == "heal":
            player["hp"] = max(1, player["hp"] - 12)
        if name in {"knockout", "phase"}:
            enemy["hp"] = 1
        before = state.public_session(session)
        session["combat"]["action_events"] = []
        if name == "heal":
            combat._player_skill(session, "healing_prayer", "", random.Random(1))
        elif name == "buff":
            combat._player_defend(session)
        elif name == "heavy":
            combat._resolve_attack(session, enemy, player, {"name": "攻撃", "accuracy": 100, "damage": str(player["max_hp"] // 2)}, enemy["id"], random.Random(1))
        else:
            element = name if name in {"fire", "ice", "holy"} else "physical"
            ability = {"name": "攻撃", "damage": "1d6", "accuracy": 5 if name == "miss" else 100, "element": element}
            combat._resolve_attack(session, player, enemy, ability, "player", random.Random(5 if name == "miss" else 1))
            if name == "phase":
                combat._check_victory_or_defeat(session)
        after = state.public_session(session)
        if name in {"critical", "rainbow"}:
            for entry in [*after["combat"]["events"], *after["combat"]["log"]]:
                if entry.get("visual", {}).get("kind") == "damage":
                    entry["visual"]["critical" if name == "critical" else "weakness"] = True
        result[name] = {"before": before, "after": after,
                        "synthetic_visual_flag": name if name in {"critical", "rainbow"} else None}

    session = battle()
    turns = []
    rng = random.Random(30)
    for action in ("defend", "defend", "attack", "attack", "attack"):
        before = state.public_session(session)
        combat.perform_combat_action(session, action, rng=rng)
        after = state.public_session(session)
        turns.append({"before": before, "after": after, "action": action})
        if not combat.combat_is_active(session):
            break
    assert session["combat"]["status"] == "victory"
    result["guard_battle"] = turns
    session = battle(character="warlock")
    session["combat"]["enemies"][0].update(hp=10000, max_hp=10000)
    before = state.public_session(session)
    combat.perform_combat_action(session, "skill", "element_prayer", rng=random.Random(30))
    result["long_response"] = {"before": before, "after": state.public_session(session)}
    session = battle()
    session["character"]["hp"] = 1
    before = state.public_session(session)
    combat.perform_combat_action(session, "defend", rng=random.Random(1))
    assert session["combat"]["status"] == "defeat"
    result["defeat"] = {"before": before, "after": state.public_session(session)}
    inn = fresh_session(state.load_scenario_pack(state.DEFAULT_SCENARIO), "hero")
    inn["world_state"] = {"location_id": "inn"}
    inn["last_action_result"] = {"action_id": "ask_robin_rumor"}
    result["inn"] = state.public_session(inn)
    return result


class Handler(StaticHandler):
    examples: dict[str, Any] = {}
    guard_session: dict[str, Any] = {}
    guard_rng = random.Random(30)

    def send_body(self, body: bytes, content_type: str) -> None:
        try:
            super().send_body(body, content_type)
        except (ConnectionAbortedError, BrokenPipeError):
            pass  # Browser navigation may cancel an obsolete image request.

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/fixtures-030":
            self.send_json(self.examples)
        elif urlparse(self.path).path == "/guard-session":
            Handler.guard_session = battle()
            Handler.guard_rng = random.Random(30)
            self.send_json(state.public_session(Handler.guard_session))
        else:
            super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/sessions/balance/combat/actions":
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            combat.perform_combat_action(self.guard_session, data["action_type"], data.get("action_id", ""),
                                         data.get("target_id", ""), rng=self.guard_rng)
            delta = combat.consume_combat_state_delta(self.guard_session)
            if delta:
                state.apply_state_delta(self.guard_session, delta, allow_world_transition=True)
            self.send_json(state.public_session(self.guard_session))
        else:
            super().do_POST()


def compose(work: Path, output: Path) -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print(f"Pillow unavailable: raw PNGs and browser checks remain in {work}; montage/GIF composition skipped.")
        return
    for folder in sorted((work / "frames").iterdir()):
        if not folder.is_dir():
            continue
        images = [Image.open(path).convert("RGB") for path in sorted(folder.glob("*.png"))]
        if not images:
            continue
        width, height = images[0].size
        sheet = Image.new("RGB", (width * 2, (height + 34) * 2), "#141618")
        draw = ImageDraw.Draw(sheet)
        for index, frame in enumerate(images):
            x, y = (index % 2) * width, (index // 2) * (height + 34)
            sheet.paste(frame, (x, y + 34))
            draw.text((x + 12, y + 10), f"{folder.name} / {index + 1}: {['start', 'peak', 'settle', 'end'][index]}", fill="#ede9e0")
        sheet.save(output / f"{folder.name}.png")
    video = json.loads((work / "video-frames.json").read_text(encoding="utf-8"))
    frames = [Image.open(work / frame["file"]).convert("RGB").resize((800, 500)) for frame in video]
    durations = [max(20, round((video[i + 1]["ms"] - item["ms"]) / 10) * 10) if i + 1 < len(video) else 500
                 for i, item in enumerate(video)]
    frames[0].save(output / "goblin-fort.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(f"GIF: {sum(durations) / 1000:.2f}s, {len(frames)} frames")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/030")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((path for path in [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")] if path.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/030" / f"browser-{time.time_ns()}"
    profile.mkdir(parents=True)
    work = profile.parent / f"capture-{time.time_ns()}"
    work.mkdir(parents=True)
    Handler.examples = fixtures()
    # Avoid OS-assigned low ports such as 6669 that Chromium refuses to navigate.
    server = None
    for port in range(18760, 18860):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise RuntimeError("No free local capture port in 18760..18859")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    process = subprocess.Popen([str(browser), "--headless=new", "--disable-gpu", "--no-first-run",
                                "--disable-background-networking", "--no-default-browser-check", "--remote-debugging-port=0",
                                f"--user-data-dir={profile}", "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1", "about:blank"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        deadline = time.monotonic() + 20
        port_file = profile / "DevToolsActivePort"
        while not port_file.exists() and time.monotonic() < deadline and process.poll() is None:
            time.sleep(.1)
        if not port_file.exists():
            raise RuntimeError("Chromium did not expose its local debugging port")
        port = port_file.read_text(encoding="utf-8").splitlines()[0]
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_battle_fx.mjs"), port,
                                 f"http://127.0.0.1:{server.server_port}", str(work)],
                                capture_output=True, text=True, encoding="utf-8", timeout=240,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        print(result.stdout, end="")
        print(result.stderr, end="")
        if (work / "checks.json").is_file():
            (args.output / "checks.json").write_text((work / "checks.json").read_text(encoding="utf-8"), encoding="utf-8")
        if result.returncode == 0:
            compose(work, args.output)
        else:
            print(f"Capture diagnostics: {work}")
        return result.returncode
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
