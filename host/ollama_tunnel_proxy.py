from __future__ import annotations

import argparse
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

        def do_GET(self) -> None:
            self._proxy()

        def do_POST(self) -> None:
            self._proxy()

        def do_PUT(self) -> None:
            self._proxy()

        def do_DELETE(self) -> None:
            self._proxy()

        def do_OPTIONS(self) -> None:
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
                self.send_error(502, f"Ollama proxy upstream error: {exc}")
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
