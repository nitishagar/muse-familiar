"""muse-familiar tests — host-side, NO board needed.

The fake router is an in-process Unix-socket msgpack-rpc server speaking the
same frames the real one does; the webhook listener runs on an ephemeral
port. Mutation-friendly: every bound is asserted at its edge.
"""

import json
import queue
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import msgpack
import pytest

REPO = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(REPO))
from familiar import frames as F  # noqa: E402
from familiar import webhook  # noqa: E402
from familiar.bridge_client import RouterClient  # noqa: E402
from familiar.moods import MoodMachine  # noqa: E402
from familiar.engine import Engine  # noqa: E402

# --- frames -------------------------------------------------------------------


def test_all_moods_are_valid_art():
    for name in F.MOODS:
        period, fl = F.mood_frames(name)
        assert F.MIN_PERIOD_MS <= period
        assert 1 <= len(fl) <= F.MAX_MOOD_FRAMES
        for frame in fl:
            assert len(frame) == 104
            assert set(frame) <= set("01234567")


def test_validate_frame_bounds():
    with pytest.raises(ValueError):
        F.validate_frame("0" * 103)
    with pytest.raises(ValueError):
        F.validate_frame("0" * 104 + "1")
    with pytest.raises(ValueError):
        F.validate_frame("8" + "0" * 103)
    with pytest.raises(ValueError):
        F.mood_frames("nonexistent")


def test_period_clamped():
    assert F.validate_period(100) == 250
    assert F.validate_period(1000) == 1000


def test_kind_map_covers_distinct_moods():
    targets = {F.KIND_TO_MOOD[k] for k in F.KIND_TO_MOOD}
    assert {"happy", "sad", "alert", "curious", "sleepy", "idle"} == targets


# --- moods ---------------------------------------------------------------------


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_mood_events_and_expiry():
    clk = FakeClock()
    m = MoodMachine(now=clk)
    assert m.event("ci_green") == "happy"
    assert m.event("ci_green") is None            # same mood: no retrigger
    clk.t = 5.9
    assert m.tick() is None                       # still holding
    clk.t = 6.1
    assert m.tick() == "idle"                     # expired back to idle
    assert m.event("deploy_fail") == "sad"
    with pytest.raises(ValueError):
        m.set("nonexistent")


def test_unknown_kind_ignored():
    m = MoodMachine(now=FakeClock())
    assert m.event("wAT") is None


# --- fake router + client --------------------------------------------------------


class FakeRouter:
    """In-process msgpack-rpc server mirroring arduino-router semantics."""

    def __init__(self, path, delay=0.0, fail_show=False):
        self.path = path
        self.calls = []
        self.delay = delay
        self.fail_show = fail_show
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(path)
        self.sock.listen(4)
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn):
        unpacker = msgpack.Unpacker()
        conn.settimeout(2)
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    return
                unpacker.feed(data)
                for msg in unpacker:
                    if not (isinstance(msg, list) and msg and msg[0] == 0):
                        continue
                    _, msgid, method, args = msg
                    if self.delay:
                        time.sleep(self.delay)
                    self.calls.append((method, args))
                    if method == "familiar.ping":
                        result, error = "pong:fake", None
                    elif method.startswith("familiar.show"):
                        result, error = (1 if not self.fail_show else -1), None
                    elif method == "familiar.clear":
                        result, error = 0, None
                    else:
                        result, error = None, [2, f"method {method} not available"]
                    conn.sendall(msgpack.packb([1, msgid, error, result]))
        except OSError:
            pass
        finally:
            conn.close()

    def close(self):
        self.running = False
        self.sock.close()


@pytest.fixture()
def fake_router(tmp_path):
    router = FakeRouter(str(tmp_path / "router.sock"))
    yield router
    router.close()


def test_client_ping_and_chunked_show(fake_router):
    c = RouterClient(socket_path=fake_router.path, timeout=2)
    assert "pong" in c.ping()
    anim = F.mood_frames("happy")[1]              # 2 frames -> 1 chunk
    assert c.show(anim, period_ms=300) == 1
    methods = [m for m, _ in fake_router.calls]
    assert methods == ["familiar.ping",
                       "familiar.show.begin", "familiar.show.chunk",
                       "familiar.show.play"]
    # period clamp mirrored host-side
    args = dict(fake_router.calls[1])[1] if False else fake_router.calls[1][1]
    assert args == [2, 300]
    c.show(F.mood_frames("curious")[1], period_ms=100)  # 4 frames, clamped
    begin = [call for call in fake_router.calls if call[0] == "familiar.show.begin"]
    assert begin[-1][1] == [4, 250]


def test_client_reconnects_after_socket_death(fake_router):
    c = RouterClient(socket_path=fake_router.path, timeout=2)
    c.ping()
    c._sock.close()                                # simulate router restart
    c._sock = c._sock                              # keep stale ref
    assert "pong" in c.ping()                      # reconnect path works


def test_client_error_and_timeout(tmp_path):
    slow = FakeRouter(str(tmp_path / "slow.sock"), delay=1.5)
    try:
        c = RouterClient(socket_path=slow.path, timeout=0.3)
        with pytest.raises(Exception):
            c.ping()
    finally:
        slow.close()
    missing = FakeRouter(str(tmp_path / "missing.sock"))
    try:
        c = RouterClient(socket_path=missing.path, timeout=2)
        from familiar.bridge_client import BridgeError
        with pytest.raises(BridgeError):
            c.call("familiar.nothing")
    finally:
        missing.close()


# --- webhook ---------------------------------------------------------------------


def post(port, body, key="right-key", path="/poke"):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode() if isinstance(body, dict) else body,
        method="POST")
    if key is not None:
        req.add_header("X-Familiar-Key", key)
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


@pytest.fixture()
def hook(tmp_path):
    webhook._STATE["key"] = "right-key"
    webhook._STATE["hits"] = {}
    events: "queue.Queue[tuple[str, float]]" = queue.Queue(maxsize=8)
    server = webhook.serve(events, key="right-key", port=0)
    port = server.server_address[1]
    yield events, port
    server.shutdown()


def test_webhook_happy_path_and_health(hook):
    events, port = hook
    status, body = post(port, {"kind": "ci_green"})
    assert status == 200 and body["ok"] is True
    kind, _ts = events.get_nowait()
    assert kind == "ci_green"
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
        assert r.status == 200


def test_webhook_auth_oversize_badjson(hook):
    events, port = hook
    assert post(port, {"kind": "x"}, key="wrong")[0] == 401
    assert post(port, None, key=None)[0] == 401
    assert post(port, b"x" * 4096)[0] == 413
    assert post(port, b"{not json")[0] == 400
    assert events.empty()


def test_webhook_rate_limit(hook):
    events, port = hook
    codes = [post(port, {"kind": "poke"})[0] for _ in range(14)]
    assert codes[:12] == [200] * 12
    assert codes[12] == 429 and codes[13] == 429


def test_webhook_queue_drops_oldest(hook):
    events, port = hook
    for i in range(10):                            # queue max 8
        post(port, {"kind": f"poke{i}"})
    kinds = [events.get_nowait()[0] for _ in range(8)]
    assert kinds[0] == "poke2" and kinds[-1] == "poke9"


# --- engine -------------------------------------------------------------------------


def test_engine_events_heartbeat_and_hot():
    class FakeClient:
        def __init__(self):
            self.shows = []
            self.clears = 0

        def show(self, frames, period_ms, count=0):
            self.shows.append((tuple(frames), period_ms))
            return len(frames)

        def clear(self):
            self.clears += 1
            return 0

    class FastClock:
        def __init__(self):
            self.t = 100.0

        def __call__(self):
            return self.t

    clk = FastClock()
    events: "queue.Queue[tuple[str, float]]" = queue.Queue()
    events.put(("ci_green", 0))
    client = FakeClient()
    engine = Engine(client, MoodMachine(now=clk), events,
                    now=clk, temp_fn=lambda: 50.0)
    assert engine.step() == "happy"
    assert client.shows[-1][0] == tuple(F.mood_frames("happy")[1])

    clk.t += 30                                     # mood expires + heartbeat due
    assert engine.step() == "idle"

    clk.t += 100                                    # heartbeat only
    before = len(client.shows)
    engine.step()
    assert len(client.shows) == before + 1

    clk.t += 100                                    # hot board -> sleepy
    hot = Engine(client, MoodMachine(now=clk), queue.Queue(),
                 now=clk, temp_fn=lambda: 85.0)
    hot._last_show = clk.t                          # suppress heartbeat show
    assert hot.step() == "sleepy"

    hot.stop = True
    hot.run()                                       # graceful exit clears
    assert client.clears == 1
