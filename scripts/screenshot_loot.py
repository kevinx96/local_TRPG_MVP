"""Offline spec 038 browser acceptance using real loot, shop and fort-gate data."""
from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from host import shops, state
from scripts.balance import checkpoints
from scripts.scenario.loot_economy import LOOT
from scripts.screenshot_choices import Handler as StaticHandler, ROOT


def fixtures() -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    session = checkpoints.fresh_session(pack, "hero")
    session["world_state"] = dict(scene_id="oaksdawn", location_id="oaksdawn_workshop")
    session["character"]["gold"] = 100
    for identifier in LOOT:
        item = next(i for i in pack["items"] if i["id"] == identifier)
        state.apply_state_delta(session, {"inventory_add": [dict(item, quantity=3)]})
    Handler.shop_session = session

    def public(current: dict[str, Any]) -> dict[str, Any]:
        current["messages"] = [{"role": "assistant", "speaker": "GM", "text": state._current_location_record(current)["description"]}]
        current["last_turn_narrated"] = True
        current["choices"] = state.fallback_choices_for_session(current)
        return state.public_session(current)

    gate = checkpoints.fresh_session(pack, "hero")
    sources = checkpoints.generate()["encounters"]["goblin_fort_third_guards"]["characters"]["hero"]["sources"]
    for entry in sources[:-1]:
        checkpoints.replay_step(gate, entry["step"])
    assert state.current_location_id(gate) == "goblin_fort_third_gate"
    return {"inventory": public(session), "shop": shops.public_shop(session, "oaksdawn_workshop_shop"), "gate": public(gate)}


class Handler(StaticHandler):
    snapshots: dict[str, Any] = {}
    shop_session: dict[str, Any] = {}

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/038-fixture":
            key = parse_qs(url.query).get("view", [""])[0]
            if key not in self.snapshots:
                self.send_error(404)
                return
            self.send_json(self.snapshots[key])
        else:
            super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/sessions/balance/shops/oaksdawn_workshop_shop/sell":
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            shops.trade(self.shop_session, "oaksdawn_workshop_shop", request["item_id"], request["quantity"], selling=True)
            shop = shops.public_shop(self.shop_session, "oaksdawn_workshop_shop")
            self.send_json(dict(session=state.public_session(self.shop_session), shop=shop, message=shop["sell_line"]))
        else:
            super().do_POST()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/038")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((p for p in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")) if p.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    Handler.snapshots = fixtures()
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/038" / f"browser-{time.time_ns()}"
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
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_loot.mjs"), port,
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
