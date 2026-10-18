"""Offline spec 036 browser acceptance using real inventory, shop and combat data."""
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

from host import combat, shops, state
from scripts.balance import checkpoints
from scripts.screenshot_choices import Handler as StaticHandler, ROOT


def fixtures() -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    session = checkpoints.fresh_session(pack, "hero")
    for step in ("@opening", "go_castle_town", "go_item_shop"):
        checkpoints.replay_step(session, step)
    for identifier in ("mp_potion", "holy_water", "magic_scroll", "ice_charm", "dawn_sword", "spirit_spring_water"):
        state.apply_state_delta(session, {"inventory_add": [{"id": identifier, "quantity": 1,
            "name": next(i["name"] for i in pack["items"] if i["id"] == identifier)}]})
    shops.use_item(session, "dawn_sword")

    def public(current: dict[str, Any]) -> dict[str, Any]:
        current["messages"] = [{"role": "assistant", "speaker": "GM", "text": state._current_location_record(current)["description"]}]
        current["last_turn_narrated"] = True
        current["choices"] = state.fallback_choices_for_session(current)
        return state.public_session(current)

    result = {"inventory": public(session), "shop": shops.public_shop(session, "sarah_shop")}
    battle = deepcopy(session)
    location = next(loc for loc in pack["locations"] if loc["id"] == "dark_forest_loc")
    battle["world_state"] = dict(scene_id=location["scene_id"], location_id=location["id"])
    battle["combat_start_requested"] = True
    with patch.object(combat, "random", random.Random(36)):
        assert combat.ensure_combat_started(battle)
    result["combat"] = public(battle)
    return result


class Handler(StaticHandler):
    snapshots: dict[str, Any] = {}

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/036-fixture":
            key = parse_qs(url.query).get("view", [""])[0]
            if key not in self.snapshots:
                self.send_error(404)
                return
            self.send_json(self.snapshots[key])
        else:
            super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/036")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((p for p in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")) if p.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    Handler.snapshots = fixtures()
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/036" / f"browser-{time.time_ns()}"
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
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_item_icons.mjs"), port,
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
