from __future__ import annotations

import argparse
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def build_proxy_handler(
    target_base_url: str,
    host_header: str | None = None,
    timeout_seconds: int = 1800,
) -> type[BaseHTTPRequestHandler]:
    target_base_url = target_base_url.rstrip("/") + "/"
    target_host = host_header or urlsplit(target_base_url).netloc

    class OllamaTunnelProxyHandler(BaseHTTPRequestHandler):
        server_version = "TRPGOllamaTunnelProxy/0.1"

        # ── Shutdown interception ──────────────────────────────

        def _is_shutdown_post(self) -> bool:
            return self.command == "POST" and self.path.rstrip("/") == "/api/shutdown"

        def _is_shutdown_ping(self) -> bool:
            return self.command == "GET" and self.path.rstrip("/") == "/api/shutdown/ping"

        def _send_json(self, code: int, obj: dict[str, Any]) -> None:
            payload = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)

        def _handle_shutdown(self) -> None:
            body = self._read_body()
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {}
            delay = max(0, min(int(data.get("delay_seconds", 30)), 3600))

            if sys.platform == "win32":
                cmd = ["shutdown", "/s", "/t", str(delay)]
            else:
                cmd = ["shutdown", "-h", f"+{max(1, delay // 60)}"]

            self.log_message("SHUTDOWN requested  delay=%ds  cmd=%s", delay, " ".join(cmd))
            try:
                subprocess.run(cmd, check=True)
            except Exception as exc:
                self._send_json(500, {"status": "error", "message": f"关机命令执行失败: {exc}"})
                return
            self._send_json(200, {
                "status": "ok",
                "message": f"系统将在 {delay} 秒后关机",
                "platform": sys.platform,
            })

        def _handle_shutdown_ping(self) -> None:
            self._send_json(200, {"status": "ok", "platform": sys.platform})

        # ── HTTP method dispatchers ────────────────────────────

        def do_GET(self) -> None:
            if self._is_shutdown_ping():
                self._handle_shutdown_ping()
            else:
                self._proxy()

        def do_POST(self) -> None:
            if self._is_shutdown_post():
                self._handle_shutdown()
            else:
                self._proxy()

        def do_PUT(self) -> None:
            self._proxy()

        def do_DELETE(self) -> None:
            self._proxy()

        def do_OPTIONS(self) -> None:
            # Support CORS preflight for /api/shutdown
            if "/api/shutdown" in self.path:
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
            else:
                self._proxy()

        def log_message(self, format: str, *args: Any) -> None:
            print(f"[OLLAMA-PROXY] {self.address_string()} - {format % args}", file=sys.stderr, flush=True)

        def _proxy(self) -> None:
            target_url = urljoin(target_base_url, self.path.lstrip("/"))
            body = self._read_body()
            headers = self._forward_headers(target_host)

            try:
                upstream = requests.request(
                    self.command,
                    target_url,
                    headers=headers,
                    data=body,
                    timeout=timeout_seconds,
                )
            except requests.RequestException as exc:
                # send_error uses latin-1 for the status line, which crashes
                # on non-ASCII chars (e.g. Chinese Windows error messages).
                safe_msg = str(exc).encode("ascii", "replace").decode("ascii")
                self.send_error(502, f"Ollama proxy upstream error: {safe_msg}")
                return

            self.send_response(upstream.status_code)
            for key, value in upstream.headers.items():
                if key.lower() not in HOP_BY_HOP_HEADERS:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(upstream.content)

        def _read_body(self) -> bytes:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0:
                return b""
            return self.rfile.read(length)

        def _forward_headers(self, target_host: str) -> dict[str, str]:
            headers: dict[str, str] = {}
            for key, value in self.headers.items():
                if key.lower() in HOP_BY_HOP_HEADERS or key.lower() == "host":
                    continue
                headers[key] = value
            headers["Host"] = target_host
            return headers

    return OllamaTunnelProxyHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rewrite Cloudflare Tunnel Host headers for local Ollama.")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=11435)
    parser.add_argument("--target", default="http://127.0.0.1:11434")
    parser.add_argument("--host-header", default="localhost:11434")
    parser.add_argument("--timeout", type=int, default=1800)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    handler = build_proxy_handler(args.target, args.host_header, args.timeout)
    server = ThreadingHTTPServer((args.listen_host, args.listen_port), handler)
    print(
        "[OLLAMA-PROXY] "
        f"listening on http://{args.listen_host}:{args.listen_port} -> {args.target} "
        f"Host={args.host_header}",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
