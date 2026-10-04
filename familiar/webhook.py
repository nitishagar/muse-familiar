"""Webhook listener feeding the Familiar (stdlib only).

Hardened (IMPLICIT_SPEC inv.6): shared-key header compared constant-time,
payload cap 2 KiB, rate cap 12 pokes/min per source, bounded queue
(≤ 8, drop-oldest), loopback bind by default — LAN bind is a conscious
one-line env flip (needed for LAN webhooks / demos), tested both ways.
"""

from __future__ import annotations

import hmac
import json
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 2048
RATE_LIMIT_PER_MIN = 12
QUEUE_MAX = 8
DEFAULT_PORT = 8123

_STATE = {"key": "", "queue": None, "hits": {}, "accepted": 0, "rejected": 0}


def _rate_ok(peer: str, now: float) -> bool:
    window = now - 60.0
    recent = [t for t in _STATE["hits"].get(peer, []) if t > window]
    if len(recent) >= RATE_LIMIT_PER_MIN:
        _STATE["hits"][peer] = recent
        return False
    recent.append(now)
    _STATE["hits"][peer] = recent
    return True


def make_handler(queue_: "queue.Queue[tuple[str, float]]",
                 now=time.time) -> type:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                self._do_post(now)
            except Exception:            # never leak a traceback to peers
                try:
                    self._reply(500, {"ok": False, "error": "internal"})
                except Exception:
                    pass
                _STATE["rejected"] += 1

        def _do_post(self, now):
            if self.path.split("?", 1)[0] != "/poke":
                self._reply(404, {"ok": False, "error": "not found"})
                return
            # rate-limit FIRST: failures must not be a free channel
            if not _rate_ok(self.client_address[0], now()):
                self._reply(429, {"ok": False, "error": "rate limited"})
                _STATE["rejected"] += 1
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = MAX_BODY + 1
            if length < 0 or length > MAX_BODY:
                self._reply(413, {"ok": False, "error": "too large"})
                _STATE["rejected"] += 1
                return
            presented = self.headers.get("X-Familiar-Key", "") or ""
            if not hmac.compare_digest(presented.encode("utf-8", "ignore"),
                                       _STATE["key"].encode("utf-8", "ignore")):
                self._reply(401, {"ok": False, "error": "bad key"})
                _STATE["rejected"] += 1
                return
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(payload, dict):
                    raise ValueError
            except ValueError:
                self._reply(400, {"ok": False, "error": "bad json"})
                _STATE["rejected"] += 1
                return
            kind = str(payload.get("kind", "poke"))
            if len(kind) > 64:
                kind = kind[:64]
            try:
                queue_.put_nowait((kind, now()))
                _STATE["accepted"] += 1
            except queue.Full:
                try:
                    queue_.get_nowait()  # drop-oldest
                    queue_.put_nowait((kind, now()))
                    _STATE["accepted"] += 1
                except (queue.Empty, queue.Full):
                    self._reply(503, {"ok": False, "error": "queue full"})
                    return
            self._reply(200, {"ok": True, "kind": kind})

        def do_GET(self):
            if self.path.split("?", 1)[0] == "/health":
                self._reply(200, {"ok": True})
            else:
                self._reply(404, {"ok": False, "error": "not found"})

        def _reply(self, status: int, body: dict):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    return Handler


def serve(queue_: "queue.Queue[tuple[str, float]]", key: str,
          port: int = DEFAULT_PORT, lan: bool = False,
          key_from_env: str = "FAMILIAR_KEY") -> ThreadingHTTPServer:
    _STATE["key"] = key or os.environ.get(key_from_env, "")
    if not _STATE["key"]:
        raise RuntimeError("shared key required")
    bind = "0.0.0.0" if lan else "127.0.0.1"
    server = ThreadingHTTPServer((bind, port), make_handler(queue_))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
