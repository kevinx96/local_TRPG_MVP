"""Offline 031 browser acceptance using real scenario transitions and installed Chromium."""
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

from host import state
from scripts.balance import battlefield, checkpoints
from scripts.screenshot_choices import Handler as StaticHandler, ROOT


def fixtures() -> dict[str, dict[str, Any]]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    initial = battlefield.forest_exit(pack, checkpoints.generate(), "hero")
    state._set_companion(initial, None)
    result = {}

    def apply(session: dict[str, Any], identifier: str) -> None:
        action = state.resolve_action(session, action_id=identifier)
        assert action and state.action_requirement_status(action, session)[0], identifier
        roll = {}
        if action.get("roll"):
            dice, dc = state.action_dice_settings(action, session=session)
            roll = state.roll_dice(session, dice, dc, client_rolls=[20])
        resolved = state.apply_action_result(session, action, roll)
        text = resolved.get("result_text") or state._current_location_record(session)["description"]
        session["messages"] = [{"role": "assistant", "speaker": "GM", "text": text}]
        session["last_turn_narrated"] = True
        session["choices"] = state.fallback_choices_for_session(session)

    def capture(session: dict[str, Any], name: str) -> None:
        result[name] = state.public_session(session)

    plain = deepcopy(initial)
    apply(plain, "enter_old_battlefield")
    capture(plain, "old_battlefield")
    apply(plain, "battlefield_to_bones")
    capture(plain, "plain_bones")
    apply(plain, "sneak_bone_field")
    apply(plain, "bones_to_tower")
    capture(plain, "ruined_watchtower")
    apply(plain, "search_watchtower")
    apply(plain, "rest_watchtower")
    apply(plain, "tower_to_bones")
    apply(plain, "bones_to_marsh")
    capture(plain, "ghoul_marsh")
    apply(plain, "sneak_ghoul_marsh")
    apply(plain, "marsh_to_chapel")
    capture(plain, "zebok_plain")
    apply(plain, "chapel_to_marsh")
    apply(plain, "marsh_to_chapel")
    capture(plain, "grave_chapel")

    cursed = deepcopy(initial)
    dagger = next(i for i in pack["items"] if i["id"] == "cursed_dagger")
    state.apply_state_delta(cursed, {"inventory_add": [{**dagger, "quantity": 1}],
                                   "flags_set": ["curse_bargain_pending"]})
    apply(cursed, "enter_old_battlefield")
    apply(cursed, "battlefield_to_bones")
    capture(cursed, "cursed_bones")
    apply(cursed, "show_curse_to_skeletons")
    apply(cursed, "bones_to_marsh")
    apply(cursed, "sneak_ghoul_marsh")
    apply(cursed, "marsh_to_chapel")
    capture(cursed, "zebok_entry")
    return result


class Handler(StaticHandler):
    snapshots: dict[str, dict[str, Any]] = {}

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/031-fixture":
            key = parse_qs(url.query).get("view", [""])[0]
            if key not in self.snapshots:
                self.send_error(404)
                return
            self.send_json(self.snapshots[key])
        else:
            super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/screens/031")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    browser = args.browser or next((p for p in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")) if p.is_file()), None)
    if not browser:
        parser.error("Installed Chromium required")
    Handler.snapshots = fixtures()
    args.output.mkdir(parents=True, exist_ok=True)
    profile = ROOT / ".codex-runs/031" / f"browser-{time.time_ns()}"
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
        result = subprocess.run(["node", str(ROOT / "scripts/screenshot_battlefield.mjs"), port,
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
