"""Minimal msgpack-RPC client for the UNO Q arduino-router (stdlib + msgpack).

Independently written for muse-familiar against the msgpack-RPC frame
protocol as implemented by Arduino_RPClite (MPL-2.0): request [0, msgid,
method, [args]], response [1, msgid, error, result]. The Arduino docs'
CC BY-SA tutorial client was NOT copied (see NOTICE.md).

Frames are calls (never notifications) so frame loss cannot be silent; the
client reconnects on socket death (router restarts orphan connections).
"""

from __future__ import annotations

import os
import socket
import time

msgpack = None  # imported lazily: hosts without msgpack can still import this module


def _msgpack():
    global msgpack
    if msgpack is None:
        import msgpack as _m
        msgpack = _m
    return msgpack

DEFAULT_SOCKET = os.environ.get("FAMILIAR_ROUTER_SOCK",
                                "/var/run/arduino-router.sock")
CALL_TIMEOUT_S = float(os.environ.get("FAMILIAR_RPC_TIMEOUT", "5"))


class BridgeError(RuntimeError):
    pass


class BridgeTimeout(BridgeError):
    pass


class RouterClient:
    """Synchronous call/response client. One in-flight call at a time —
    the engine is single-threaded; simplicity wins over pipelining."""

    def __init__(self, socket_path: str = DEFAULT_SOCKET,
                 timeout: float = CALL_TIMEOUT_S):
        self.socket_path = socket_path
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._msgid = 0

    # -- transport ----------------------------------------------------------

    def _connect(self) -> socket.socket:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        return sock

    def _ensure_connected(self) -> socket.socket:
        if self._sock is None:
            self._sock = self._connect()
        return self._sock

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def call(self, method: str, *args):
        """One RPC. Retries exactly once on a dead socket (reconnect),
        then raises BridgeTimeout/BridgeError."""
        for attempt in (0, 1):
            self._msgid += 1
            msgid = self._msgid
            try:
                sock = self._ensure_connected()
                sock.sendall(_msgpack().packb([0, msgid, method, list(args)]))
                unpacker = _msgpack().Unpacker()
                deadline = time.monotonic() + self.timeout
                while time.monotonic() < deadline:
                    try:
                        data = sock.recv(4096)
                    except socket.timeout:
                        break
                    if not data:
                        raise OSError("router closed the connection")
                    unpacker.feed(data)
                    for message in unpacker:
                        if not (isinstance(message, list) and len(message) == 4
                                and message[0] == 1 and message[1] == msgid):
                            continue  # not our response (shouldn't happen)
                        _, _, error, result = message
                        if error is not None:
                            raise BridgeError(f"{method}: {error}")
                        return result
                raise BridgeTimeout(f"{method}: no response in {self.timeout}s")
            except OSError:
                self.close()
                if attempt == 1:
                    raise
        raise BridgeError("unreachable")  # pragma: no cover

    # -- familiar methods ---------------------------------------------------

    def ping(self) -> str:
        return self.call("familiar.ping")

    CHUNK_FRAMES = 2  # router caps messages ~256 B (measured; 2 frames OK)

    def show(self, frames: list[bytes] | list[str], period_ms: int,
             count: int = 0) -> int:
        """Push an animation in <=2-frame chunks (router message cap), then
        play. Frames are 104-char strings of '0'..'7'. Returns frames playing."""
        if period_ms < 250:
            period_ms = 250  # host-side mirror of the MCU clamp
        texts = [f.decode() if isinstance(f, bytes) else f for f in frames]
        for t in texts:
            if len(t) != 104:
                raise ValueError("each frame must be exactly 104 chars")
        total = len(texts)
        self.call("familiar.show.begin", total, int(period_ms))
        staged = 0
        for i in range(0, total, self.CHUNK_FRAMES):
            staged = self.call("familiar.show.chunk",
                               "".join(texts[i:i + self.CHUNK_FRAMES]))
        return self.call("familiar.show.play", int(count))

    def clear(self) -> int:
        return self.call("familiar.clear")
