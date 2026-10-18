"""Offline spec 032 inventory acceptance using the real shop and equipment engine."""
from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from host import shops, state
from scripts.balance import checkpoints
from scripts.screenshot_choices import Handler as StaticHandler, ROOT


def fixture() -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    session = checkpoints.fresh_session(pack, "hero")
    for step in ("@opening", "go_castle_town", "go_forge"):
        checkpoints.replay_step(session, step)
    shops.trade(session, "forge_shop", "adamantite_armor", 1)
    for identifier in ("ice_iron_greatsword", "activated_ice_charm", "ruby_charm", "ice_charm"):
        item = next(item for item in pack["items"] if item["id"] == identifier)
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": 1}]})
    shops.use_item(session, "activated_ice_charm")
    session["messages"] = [{"role": "assistant", "speaker": "GM", "text": state._current_location_record(session)["description"]}]
    session["choices"] = state.fallback_choices_for_session(session)
    return session


class Handler(StaticHandler):
    session: dict[str, Any] = {}

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/032-fixture":
            self.send_json(state.public_session(self.session))
        else:
            super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/sessions/balance/items/use":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            message = shops.use_item(self.session, body["item_id"])
            self.send_json({"session": state.public_session(self.session), "message": message})
        else:
            super().do_POST()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/032")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((p for p in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")) if p.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    Handler.session = fixture()
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/032" / f"browser-{time.time_ns()}"
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
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_equipment.mjs"), port,
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
