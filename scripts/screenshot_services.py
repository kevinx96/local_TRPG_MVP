from __future__ import annotations

import argparse
import json
import mimetypes
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from host import state
from host.shops import ShopError, public_shop, trade, use_item
from scripts.balance import checkpoints


ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client"

BOOT = r"""
(async () => {
  const checks = [];
  function check(ok, label) { if (!ok) throw new Error(label); checks.push(label); }
  try {
    const fixture = await fetchJson('/fixture');
    els.startScreen.style.display = 'none';
    els.gameScreen.style.display = '';
    renderSession(fixture);
    await openShop('sarah_shop');
    check(state.shop.items.find(i => i.item_id === 'herb').stock === 3, 'initial stock');
    state.shopItemId = 'herb'; state.shopQuantity = 2; renderShop();
    await performShopTrade();
    check(state.shop.gold === 80 && state.shop.items[0].stock === 1, 'buy quantity and stock refresh');
    state.shopTab = 'sell'; state.shopQuantity = 1; renderShop();
    check(!state.shop.sell_items.some(i => i.key_item), 'key items excluded');
    await performShopTrade();
    check(state.shop.gold === 84, 'sell refresh');
    state.shopTab = 'buy'; state.shopQuantity = 1; renderShop();
    await performShopTrade();
    check(document.querySelector('.shop-row.sold-out') && document.querySelector('#shopTrade').disabled, 'sold out');
    await useInventoryItem('herb');
    check(state.character.hp === 11, 'inventory use refresh');
    const next = await serviceRequest('fixture-progress', {});
    renderSession(next);
    check(document.querySelector('#notifications').textContent.includes('クエスト更新'), 'quest notification');
    const view = new URLSearchParams(location.search).get('view');
    if (view === 'inventory') {
      closeShop();
      els.menuOverlay.style.display = 'flex';
      document.querySelector('[data-item-id="herb"]')?.classList.add('expanded');
      document.querySelector('#inventory').scrollIntoView({block: 'center'});
    } else if (view === 'quests') {
      closeShop(); els.menuOverlay.style.display = 'flex';
      document.querySelector('#quests').scrollIntoView({block: 'start'});
    } else {
      state.shopItemId = 'ice_charm'; renderShop();
      check(document.querySelector('#shopTrade').disabled, 'insufficient gold button');
      check(document.querySelector('#shopDetail').textContent.includes(state.shop.poor_line), 'disabled reason');
      const list = document.querySelector('#shopItems').getBoundingClientRect();
      const detail = document.querySelector('#shopDetail').getBoundingClientRect();
      check(innerWidth < 768 ? detail.top >= list.bottom : detail.left >= list.right, 'responsive columns');
    }
    check(document.documentElement.scrollWidth <= innerWidth, 'no horizontal overflow');
    await fetch('/result', {method: 'POST', body: JSON.stringify({ok:true, checks})});
  } catch (error) {
    await fetch('/result', {method: 'POST', body: JSON.stringify({ok:false, checks, error:String(error)})});
  }
})();
"""


def fixture() -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    session = checkpoints.fresh_session(pack, "hero")
    state.commit_world_position(session, location_id="item_shop")
    session["character"].update(hp=1, gold=100)
    session["flags"].update(lost_goblin_quest=True, accepted_ian_request=True, frost_trace_seen=True,
                            accepted_robin_goblin_quest=True, cleared_goblin_fort=True)
    for item_id in ("white_dragon_scale", "ice_crystal", "mp_potion"):
        item = next(item for item in pack["items"] if item["id"] == item_id)
        state.apply_state_delta(session, {"inventory_add": [item]})
    session["choices"] = state.fallback_choices_for_session(session)
    session["character"]["hp"] = 1
    session["last_turn_narrated"] = False
    return session


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline services screenshots using installed Chromium; no extra dependencies or LLM")
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / ".codex-runs/services-ui")
    args = parser.parse_args()
    candidates = [args.browser] if args.browser else [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ]
    browser = next((path for path in candidates if path and path.is_file()), None)
    if not browser:
        print("No installed Chromium browser; screenshots skipped.")
        return 0
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    session = fixture()
    results: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: Any) -> None:
            pass

        def send_data(self, value: Any, status: int = 200) -> None:
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/fixture":
                self.send_data(state.public_session(session))
                return
            if path.startswith("/api/sessions/balance/shops/"):
                self.send_data(public_shop(session, path.rsplit("/", 1)[1]))
                return
            target = CLIENT / ("index.html" if path == "/" else path.removeprefix("/static/"))
            target = target.resolve()
            if not target.is_relative_to(CLIENT) or not target.is_file():
                self.send_error(404)
                return
            data = target.read_bytes()
            if target.name == "index.html":
                data = re.sub(rb'<link[^>]+https://[^>]+>', b'', data)
            elif target.name == "app.js":
                data = data.replace(b"init();", BOOT.encode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", (mimetypes.guess_type(target)[0] or "application/octet-stream") + "; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
            path = urlparse(self.path).path
            try:
                if path == "/result":
                    results.append(body)
                    self.send_data({})
                elif path.endswith("/fixture-progress"):
                    state.apply_state_delta(session, {"flags_set": ["reached_village"]})
                    self.send_data(state.public_session(session))
                elif path.endswith("/items/use"):
                    message = use_item(session, body["item_id"])
                    self.send_data({"session": state.public_session(session), "message": message})
                elif "/shops/" in path:
                    shop_id, operation = path.split("/shops/", 1)[1].split("/")
                    trade(session, shop_id, body["item_id"], body["quantity"], selling=operation == "sell")
                    shop = public_shop(session, shop_id)
                    self.send_data({"session": state.public_session(session), "shop": shop,
                                    "message": shop["sell_line" if operation == "sell" else "buy_line"]})
                else:
                    self.send_data({})
            except ShopError as exc:
                self.send_data({"detail": str(exc)}, 422)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for view, size in (("shop", "1280,900"), ("shop-mobile", "480,1000"), ("quests", "1280,900"), ("inventory", "1280,1000")):
            session = fixture()
            before = len(results)
            command = [str(browser), "--headless=new", "--disable-gpu", "--no-first-run", "--disable-background-networking",
                       "--no-default-browser-check", "--hide-scrollbars", "--force-device-scale-factor=1",
                       "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
                       f"--user-data-dir={output / ('profile-' + view)}", f"--window-size={size}",
                       "--virtual-time-budget=1800", f"--screenshot={output / (view + '.png')}",
                       f"http://127.0.0.1:{server.server_port}/?view={view}"]
            completed = subprocess.run(command, capture_output=True, timeout=45,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if completed.returncode or len(results) == before:
                results.append({"ok": False, "error": "Browser failed or did not finish UI checks"})
            results[-1]["view"] = view
            print(json.dumps(results[-1], ensure_ascii=False))
    finally:
        server.shutdown()
        server.server_close()
    (output / "checks.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(not result["ok"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
