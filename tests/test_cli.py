"""CLI tests: status/feed against a live loopback webhook, exit-code edges."""
import queue
import sys

import pytest

from familiar import cli
from familiar import webhook

pytest.importorskip("msgpack", reason="cli shares the engine's msgpack-rpc client module")


@pytest.fixture
def live_engine(monkeypatch, tmp_path):
    """Webhook on an ephemeral port with a known key + redirected state files."""
    key_file = tmp_path / "key"
    key_file.write_text("k-test-cli\n")
    events: "queue.Queue[tuple[str, float]]" = queue.Queue(maxsize=webhook.QUEUE_MAX)
    webhook._STATE["hits"] = {}   # rate window is process-global; isolate tests
    server = webhook.serve(events, key="k-test-cli", port=0)
    port = server.server_address[1]
    monkeypatch.setattr(cli, "_recent_events", lambda n: [])
    yield server, port, events, key_file
    server.shutdown()
    server.server_close()


def test_feed_happy_path(live_engine, capsys):
    server, port, events, key_file = live_engine
    rc = cli.main(["feed", "ci_green", "--port", str(port),
                   "--key-file", str(key_file)])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "happy" in out
    kind, ts = events.get_nowait()      # the event actually reached the queue
    assert kind == "ci_green"


def test_feed_wrong_key_is_exit_2(live_engine, tmp_path, capsys):
    server, port, events, key_file = live_engine
    bad = tmp_path / "bad"
    bad.write_text("nope\n")
    rc = cli.main(["feed", "ci_green", "--port", str(port), "--key-file", str(bad)])
    assert rc == 2
    assert "401" in capsys.readouterr().err


def test_feed_unknown_kind_is_exit_3(live_engine):
    server, port, events, key_file = live_engine
    rc = cli.main(["feed", "not_a_kind", "--port", str(port),
                   "--key-file", str(key_file)])
    assert rc == 3


def test_feed_missing_key_file_is_exit_3(live_engine, tmp_path, capsys):
    server, port, events, _ = live_engine
    rc = cli.main(["feed", "poke", "--port", str(port),
                   "--key-file", str(tmp_path / "absent")])
    assert rc == 3
    assert "install.sh" in capsys.readouterr().err


def test_feed_engine_down_is_exit_2(live_engine, tmp_path, capsys):
    server, _port, events, key_file = live_engine
    server.shutdown()  # nothing listens anymore
    rc = cli.main(["feed", "poke", "--port", "1", "--key-file", str(key_file)])
    assert rc == 2
    assert "unreachable" in capsys.readouterr().err


def test_status_healthy(live_engine, capsys):
    server, port, events, key_file = live_engine
    rc = cli.main(["status", "--port", str(port)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "up (True)" in out
    assert "moods:" in out and "idle" in out


def test_status_engine_down_is_exit_2(capsys):
    # nothing serves on port 1; systemd may be absent on a dev box (unknown)
    rc = cli.main(["status", "--port", "1"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "unreachable" in err
    assert "Traceback" not in err


def test_feed_rate_limited_is_exit_2(live_engine, capsys):
    # feed inherits the webhook's shared rate bucket: the 13th poke in a
    # minute gets 429 and must surface as exit 2, not a traceback.
    server, port, events, key_file = live_engine
    codes = [cli.main(["feed", "poke", "--port", str(port),
                       "--key-file", str(key_file)])
             for _ in range(13)]
    err = capsys.readouterr().err
    assert codes[:12] == [0] * 12
    assert codes[12] == 2
    assert "429" in err or "rate-limited" in err


def test_status_tails_events_file(monkeypatch, tmp_path, capsys):
    # status reports the engine's event journal: honors the engine's
    # EVENTS_FILE resolution and shows only the last 5 lines.
    import threading
    from familiar import engine as engine_mod
    events: "queue.Queue[tuple[str, float]]" = queue.Queue()
    server = webhook.serve(events, key="k", port=0)
    port = server.server_address[1]
    monkeypatch.setattr(engine_mod, "EVENTS_FILE", str(tmp_path / "e.jsonl"))
    monkeypatch.setattr(engine_mod, "LOCK_PATH", str(tmp_path / "e.lock"))
    (tmp_path / "e.jsonl").write_text(
        "".join(f'{{"kind": "k{i}", "mood": "idle", "ts": {i}}}\n'
                for i in range(7)))
    try:
        rc = cli.main(["status", "--port", str(port)])
    finally:
        server.shutdown()
        server.server_close()
    out = capsys.readouterr().out
    assert rc == 0
    assert '"kind": "k2"' in out and '"kind": "k6"' in out   # last 5
    assert '"kind": "k1"' not in out and '"kind": "k0"' not in out
    assert str(tmp_path / "e.jsonl") in out                  # path surfaced
