"""Offline 035 UI acceptance using real engine transitions and installed Chromium."""
from __future__ import annotations

import argparse
import random
import subprocess
import threading
import time
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from host import combat, state
from scripts.balance import checkpoints, rewards, sim
from scripts.screenshot_choices import Handler as StaticHandler, ROOT


def fixtures() -> dict[str, dict[str, Any]]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    session = checkpoints.fresh_session(pack, "hero")
    sources = cp["encounters"]["forest_wolves"]["characters"]["hero"]["sources"]
    for step in [*[source["step"] for source in sources], "@victory"]:
        checkpoints.replay_step(session, step)
        rewards.consume_boosts(session)
        if state.current_location_id(session) == "elf_spring":
            action = state.resolve_action(session, action_id="draw_spirit_spring_water")
            state.apply_action_result(session, action, {})
    for resource in ("hp", "mp", "sp"):
        session["character"][resource] = session["character"][f"max_{resource}"]
    state._set_companion(session, None)
    result = {}

    def resolve(identifier: str) -> None:
        action = state.resolve_action(session, action_id=identifier)
        assert action and state.action_requirement_status(action, session)[0], identifier
        roll = {}
        if action.get("roll"):
            dice, dc = state.action_dice_settings(action, session=session)
            roll = state.roll_dice(session, dice, dc, client_rolls=[20])
        state.apply_action_result(session, action, roll)

    def capture(name: str, snapshot: dict[str, Any] | None = None) -> None:
        current = snapshot if snapshot is not None else session
        location = state._current_location_record(current)
        description = location["description"]
        for variant in location.get("description_variants", []):
            if state._session_requirement_passes(variant.get("requirements"), current):
                description = variant["text"]
                break
        current["messages"] = [{"role": "assistant", "speaker": "GM", "text": description}]
        current["last_turn_narrated"] = True
        current["choices"] = state.fallback_choices_for_session(current)
        result[name] = state.public_session(current)

    for identifier in ("enter_old_battlefield", "battlefield_to_oaksdawn", "square_to_hq", "greet_walter", "open_gorge_path",
                       "hq_to_square", "square_to_inn", "talk_elio"):
        resolve(identifier)
    capture("inn_elio")
    for identifier in ("recruit_elio_persuade", "inn_to_square", "square_to_wall"):
        resolve(identifier)
    capture("wall_open")
    resolve("oaksdawn_east_pass_open")
    capture("entrance")
    resolve("gorge_to_rockfall")
    capture("rockfall")
    resolve("fight_gorge_rockfall_path")
    rng = random.Random(35)
    with patch.object(combat, "random", rng):
        assert combat.ensure_combat_started(session)
        capture("battle_elio")
        while combat.combat_is_active(session):
            action, target = sim.choose_action(session, "heuristic")
            combat.perform_combat_action(session, action["type"], action["id"], target, rng=rng)
    assert session["combat"]["status"] == "victory"
    state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
    combat.clear_combat_after_resolution(session)
    resolve("rockfall_to_camp")
    capture("camp")
    for identifier in ("search_miner_camp", "rest_miner_camp", "camp_to_rockfall", "rockfall_to_cliff"):
        resolve(identifier)
    capture("cliff")
    resolve("inspect_white_claw")
    resolve("cliff_to_giant")
    capture("giant")
    resolve("sneak_gorge_giant_path")
    resolve("giant_to_worm")
    no_elio = deepcopy(session)
    state._set_companion(no_elio, None)
    capture("worm", no_elio)
    capture("worm_bypass")
    resolve("elio_flood_worm")
    resolve("gorge_to_village")
    capture("village")
    return result


class Handler(StaticHandler):
    snapshots: dict[str, dict[str, Any]] = {}

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/035-fixture":
            key = parse_qs(url.query).get("view", [""])[0]
            if key not in self.snapshots:
                self.send_error(404)
                return
            self.send_json(self.snapshots[key])
        else:
            super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/035")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((p for p in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")) if p.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    Handler.snapshots = fixtures()
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/035" / f"browser-{time.time_ns()}"
    profile.mkdir(parents=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    process = subprocess.Popen([str(browser), "--headless=new", "--disable-gpu", "--no-first-run", "--disable-background-networking",
        "--no-default-browser-check", "--remote-debugging-port=0", f"--user-data-dir={profile}",
        "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        deadline = time.monotonic() + 20
        port_file = profile / "DevToolsActivePort"
        while not port_file.exists() and time.monotonic() < deadline and process.poll() is None:
            time.sleep(.1)
        if not port_file.exists():
            raise RuntimeError("Chromium did not expose its local debugging port")
        port = port_file.read_text(encoding="utf-8").splitlines()[0]
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_gorge.mjs"), port,
            f"http://127.0.0.1:{server.server_port}", str(args.output.resolve())],
            capture_output=True, text=True, encoding="utf-8", timeout=180,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        print(result.stdout, end="")
        print(result.stderr, end="")
        return result.returncode
    finally:
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
