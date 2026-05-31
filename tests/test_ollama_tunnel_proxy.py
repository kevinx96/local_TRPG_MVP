import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

from host.ollama_tunnel_proxy import build_proxy_handler


class CaptureHandler(BaseHTTPRequestHandler):
    received_host = ""
    received_path = ""
    received_body = b""

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        CaptureHandler.received_host = self.headers.get("Host", "")
        CaptureHandler.received_path = self.path
        CaptureHandler.received_body = self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))

    def log_message(self, format, *args):
        return


class OllamaTunnelProxyTests(unittest.TestCase):
    def test_proxy_rewrites_host_header(self):
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), CaptureHandler)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        upstream_port = upstream.server_address[1]

        proxy_handler = build_proxy_handler(
            f"http://127.0.0.1:{upstream_port}",
            host_header="localhost:11434",
        )
        proxy = ThreadingHTTPServer(("127.0.0.1", 0), proxy_handler)
        proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
        proxy_thread.start()
        proxy_port = proxy.server_address[1]

        try:
            response = requests.post(
                f"http://127.0.0.1:{proxy_port}/v1/chat/completions?x=1",
                headers={"Host": "ollama.example.com"},
                json={"hello": "world"},
                timeout=5,
            )
        finally:
            proxy.shutdown()
            upstream.shutdown()
            proxy.server_close()
            upstream.server_close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CaptureHandler.received_host, "localhost:11434")
        self.assertEqual(CaptureHandler.received_path, "/v1/chat/completions?x=1")
        self.assertEqual(json.loads(CaptureHandler.received_body), {"hello": "world"})


if __name__ == "__main__":
    unittest.main()
