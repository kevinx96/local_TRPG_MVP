from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the local TRPG host and open the browser.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--graceful-shutdown-timeout",
        type=int,
        default=1,
        help="Seconds to wait for in-flight requests during shutdown.",
    )
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/"
    if not args.no_browser:
        timer = threading.Timer(1.0, _open_browser, args=(url,))
        timer.daemon = True
        timer.start()
    print(f"[TRPG] Host starting at {url}", flush=True)
    uvicorn.run(
        "host.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        timeout_graceful_shutdown=args.graceful_shutdown_timeout,
    )


def _open_browser(url: str) -> None:
    print(f"[TRPG] Opening browser: {url}", flush=True)
    webbrowser.open(url)


if __name__ == "__main__":
    main()
