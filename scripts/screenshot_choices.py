"""Offline 028 UI checks and screenshots, using installed Chromium and Node's WebSocket."""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from host import state
from scripts.balance import checkpoints

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client"


def fixture(location: str) -> dict[str, Any]:
    session = checkpoints.fresh_session(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO), "hero")
    for step in ("@opening", "go_castle_town", *(["go_magic_shop"] if location == "magic_shop" else [])):
        checkpoints.replay_step(session, step)
    session["messages"] = [{"role": "assistant", "speaker": "GM", "text": state._current_location_record(session)["description"]}]
    session["choices"] = state.fallback_choices_for_session(session)
    session["last_turn_narrated"] = False
    return state.public_session(session)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args: Any) -> None:
        pass

    def send_json(self, value: Any) -> None:
        self.send_body(json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json")

    def send_body(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        path = url.path
        if path == "/api/config":
            self.send_json(dict(active_backend="gemini", model="gemini-3.1-flash-lite",
                                backends={"gemini": {"model": "gemini-3.1-flash-lite"}}))
        elif path == "/api/scenarios":
            self.send_json({"scenarios": [{"filename": f, "title": state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(f))["meta"]["title"]}
                                          for f in ("dragon_rpg.json", "dragon_rpg_hybrid.json")]})
        elif path.startswith("/api/scenarios/"):
            filename = path.rsplit("/", 1)[1]
            if filename not in {"dragon_rpg.json", "dragon_rpg_hybrid.json"}:
                self.send_error(404)
                return
            self.send_json({"scenario": state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename))})
        elif path == "/fixture":
            self.send_json(fixture(parse_qs(url.query).get("location", ["castle_town"])[0]))
        else:
            target = (CLIENT / ("index.html" if path == "/" else path.removeprefix("/static/"))).resolve()
            if not target.is_relative_to(CLIENT) or not target.is_file():
                self.send_error(404)
                return
            body = target.read_bytes()
            if target.name == "index.html":
                body = re.sub(rb'<link[^>]+https://[^>]+>', b'', body)
            self.send_body(body, mimetypes.guess_type(target)[0] or "application/octet-stream")

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/api/client-debug":
            self.send_json({})
        else:
            self.send_error(404)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/028")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((path for path in [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")]
        if path.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/028" / f"browser-{time.time_ns()}"
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
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_choices.mjs"), port,
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
