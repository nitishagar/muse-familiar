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
