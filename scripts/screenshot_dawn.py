"""Offline spec 034 UI fixtures and screenshots with installed Chromium."""
from __future__ import annotations

import argparse
import subprocess
import threading
import time
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from host import shops, state
from scripts.balance import checkpoints
from scripts.screenshot_choices import Handler as StaticHandler, ROOT


def fixtures() -> dict[str, dict[str, Any]]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    session = checkpoints.fresh_session(pack, "hero")
    # Isolated screenshot setup; gameplay reachability and reward guards are covered by unittest.
    session["character"]["gold"] = 500
    result = {}

    def move(location: str) -> None:
        state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)

    def resolve(identifier: str) -> None:
        action = state.resolve_action(session, action_id=identifier)
        assert action and state.action_requirement_status(action, session)[0], identifier
        state.apply_action_result(session, action, {})

    def capture(name: str) -> None:
        session["messages"] = [{"role": "assistant", "speaker": "GM", "text": state._current_location_record(session)["description"]}]
        session["last_turn_narrated"] = True
        session["choices"] = state.fallback_choices_for_session(session)
        result[name] = state.public_session(session)

    move("cave_hot_spring")
    resolve("follow_hot_spring_water")
    capture("waterway")
    resolve("waterway_to_gate")
    capture("water_gate")
    resolve("open_oaksdawn_gate")
    resolve("square_to_wall")
    capture("wall")
    resolve("wall_to_square")
    resolve("square_to_workshop")
    resolve("talk_brigitte")
    resolve("ask_workshop_hearth")
    shops.trade(session, "oaksdawn_workshop_shop", "holy_silver", 2)
    capture("workshop")
    resolve("forge_dawn_weapon")
    move("cave_lava_room")
    resolve("pick_baked_lava_stone")
    move("grave_chapel")
    state.apply_state_delta(session, {"flags_set": ["passed_grave_chapel"]})
    resolve("ring_battlefield_bell")
    move("oaksdawn_hq")
    resolve("report_battlefield_bell_hq")
    move("oaksdawn_workshop")
    capture("inventory")
    result["inventory_mobile"] = deepcopy(result["inventory"])
    return result


class Handler(StaticHandler):
    snapshots: dict[str, dict[str, Any]] = {}

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/034-fixture":
            key = parse_qs(url.query).get("view", [""])[0]
            if key not in self.snapshots:
                self.send_error(404)
                return
            self.send_json(self.snapshots[key])
        else:
            super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/034")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((p for p in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")) if p.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    Handler.snapshots = fixtures()
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/034" / f"browser-{time.time_ns()}"
    profile.mkdir(parents=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    command = [str(browser), "--headless=new", "--disable-gpu", "--no-first-run", "--disable-background-networking",
               "--no-default-browser-check", "--remote-debugging-port=0", f"--user-data-dir={profile}",
               "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1", "about:blank"]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        deadline = time.monotonic() + 20
        port_file = profile / "DevToolsActivePort"
        while not port_file.exists() and time.monotonic() < deadline and process.poll() is None:
            time.sleep(.1)
        if not port_file.exists():
            raise RuntimeError("Chromium did not expose its local debugging port")
        port = port_file.read_text(encoding="utf-8").splitlines()[0]
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_dawn.mjs"), port,
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
