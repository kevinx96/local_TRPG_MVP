"""Offline spec 042 browser checks, contact sheet and animation snapshots."""
from __future__ import annotations

import argparse
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import patch

from host import app, state
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session
from scripts.screenshot_choices import Handler as StaticHandler, ROOT


class Handler(StaticHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/042-crucial-fixture":
            session = fresh_session(state.load_scenario_pack(DEFAULT_SCENARIO), "hero")
            accepted, reason = state.commit_world_position(session, location_id="goblin_fort")
            if not accepted:
                raise ValueError(reason)
            session["choices"] = state.fallback_choices_for_session(session)
            initial = state.public_session(session)
            choice = next(c for c in initial["choices"] if c.get("id") == "fort_first_bypass")
            with patch.object(state.random, "randint", return_value=3), patch.object(app, "save_session"):
                result = app._run_turn(session, app.TurnRequest(text=choice["text"], action_id=choice["id"]),
                                       allow_narration=False)
            self.send_json({"initial": initial, "choice": choice, "result": result})
        elif path.startswith("/042-candidates/"):
            base = ROOT / "assets/candidates/042"
            target = (base / path.removeprefix("/042-candidates/")).resolve()
            if not target.is_relative_to(base) or not target.is_file():
                self.send_error(404)
                return
            self.send_body(target.read_bytes(), "image/png")
        else:
            super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/042")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((path for path in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")) if path.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/042" / f"browser-{time.time_ns()}"
    profile.mkdir(parents=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    process = subprocess.Popen([str(browser), "--headless=new", "--disable-gpu", "--no-first-run",
        "--disable-background-networking", "--no-default-browser-check", "--remote-debugging-port=0",
        f"--user-data-dir={profile}", "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        deadline = time.monotonic() + 20
        port_file = profile / "DevToolsActivePort"
        while not port_file.exists() and time.monotonic() < deadline and process.poll() is None:
            time.sleep(.1)
        if not port_file.exists():
            raise RuntimeError("Chromium did not expose its local debugging port")
        port = port_file.read_text(encoding="utf-8").splitlines()[0]
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_dice_visual.mjs"), port,
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
