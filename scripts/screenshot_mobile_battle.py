"""Offline spec 037 phone battle acceptance with installed Chromium."""
from __future__ import annotations

import argparse
import random
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import urlparse

from host import combat, state
from scripts.balance import checkpoints, sim
from scripts.screenshot_battle_fx import fixtures as fx_fixtures
from scripts.screenshot_choices import Handler as StaticHandler, ROOT


def fixtures() -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    result = {}
    for name, location in (("normal", "goblin_fort"), ("draco", "draco_battle")):
        session = sim.prepare_session(pack, location, "hero", cp, companion=False)
        rng = random.Random(37)
        session["combat_start_requested"] = True
        with patch.object(combat, "random", rng):
            assert combat.ensure_combat_started(session)
            for _ in range(3):
                combat.perform_combat_action(session, "defend", rng=rng)
        assert combat.combat_is_active(session)
        result[name] = state.public_session(session)
    examples = fx_fixtures()
    result["effects"] = {key: examples[key] for key in ("normal", "phase", "heal", "knockout")}
    return result


class Handler(StaticHandler):
    snapshots: dict[str, Any] = {}

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/037-fixtures":
            self.send_json(self.snapshots)
        else:
            super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/037")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((p for p in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")) if p.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    Handler.snapshots = fixtures()
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/037" / f"browser-{time.time_ns()}"
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
        port = ""
        while time.monotonic() < deadline and process.poll() is None:
            try:
                lines = port_file.read_text(encoding="utf-8").splitlines()
                if lines and lines[0].isdigit():
                    port = lines[0]
                    break
            except OSError:
                pass
            time.sleep(.1)
        if not port:
            raise RuntimeError("Chromium did not expose its local debugging port")
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_mobile_battle.mjs"), port,
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
