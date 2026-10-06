"""familiar — CLI for the creature.

    python3 -m familiar.cli ping
    python3 -m familiar.cli show happy
    python3 -m familiar.cli serve [--lan]
    python3 -m familiar.cli moods
    python3 -m familiar.cli status
    python3 -m familiar.cli feed ci_green

Exit codes: 0 ok · 2 runtime error (bridge/hardware, engine down, auth,
rate-limit, network) · 3 bad usage value (unknown kind, unreadable key
file, bad option).
"""

from __future__ import annotations

import argparse
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    from familiar import engine as engine_mod
    from familiar import frames as F
    from familiar.bridge_client import BridgeError, RouterClient
else:
    from . import engine as engine_mod
    from . import frames as F
    from .bridge_client import BridgeError, RouterClient


def _cmd_status(port: int) -> int:
    import json
    import subprocess
    import urllib.request

    problems = []

    health = "down"
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=2) as r:
            health = f"up ({json.loads(r.read()).get('ok')})"
    except Exception as exc:
        problems.append(f"webhook /health unreachable on port {port}: {exc}")

    unit = "unknown"
    try:
        unit = subprocess.run(
            ["systemctl", "--user", "is-active", "familiar-engine"],
            capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
    except Exception:
        pass  # no systemd here (dev machine) — reported as unknown

    events = _recent_events(5)
    print(f"webhook: {health}")
    print(f"unit:    {unit}")
    print(f"moods:   {' '.join(sorted(F.MOODS))}")
    print(f"recent events ({engine_mod.EVENTS_FILE}):")
    if events:
        for line in events:
            print(f"  {line.rstrip()}")
    else:
        print("  (none yet)")

    # Exit 2 is driven by engine liveness (the /health probe); the unit
    # state is context — a dev box running `serve` by hand is healthy
    # with an inactive unit.
    if problems:
        for p in problems:
            print(f"familiar status: {p}", file=sys.stderr)
        if unit == "inactive":
            print("hint: start the service with scripts/install.sh "
                  "(or systemctl --user start familiar-engine)",
                  file=sys.stderr)
        return 2
    return 0


def _recent_events(n: int) -> list[str]:
    import fcntl

    path = engine_mod.EVENTS_FILE
    try:
        # Brief SHARED lock: the engine appends under the same discipline,
        # so we never read a half-written line.
        lock_fd = open(engine_mod.LOCK_PATH, "a+")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_SH)
            with open(path) as f:
                return f.readlines()[-n:]
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
    except OSError:
        return []


def _cmd_feed(kind: str, port: int, key_file: str) -> int:
    import json
    import urllib.error
    import urllib.request

    if kind not in F.KIND_TO_MOOD:
        print(f"familiar: unknown kind {kind!r} "
              f"(known: {' '.join(sorted(F.KIND_TO_MOOD))})", file=sys.stderr)
        return 3
    try:
        with open(key_file) as f:
            key = f.read().strip()
    except OSError as exc:
        print(f"familiar: cannot read key file {key_file} ({exc}); "
              f"run scripts/install.sh or pass --key-file", file=sys.stderr)
        return 3

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/poke",
        data=json.dumps({"kind": kind}).encode(),
        headers={"Content-Type": "application/json", "X-Familiar-Key": key},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        print(f"familiar: feed rejected: HTTP {exc.code} "
              f"({'auth' if exc.code == 401 else 'rate-limited' if exc.code == 429 else exc.code})",
              file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"familiar: engine unreachable on port {port}: {exc}",
              file=sys.stderr)
        return 2
    print(f"fed {kind} -> {F.KIND_TO_MOOD[kind]} ({body.get('kind', '')})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="familiar", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ping", help="bridge round-trip check")
    show = sub.add_parser("show", help="play a mood animation once")
    show.add_argument("mood", choices=sorted(F.MOODS))
    sub.add_parser("clear", help="dark matrix")
    sub.add_parser("moods", help="list moods")

    serve = sub.add_parser("serve", help="run the engine (webhook + heartbeats)")
    serve.add_argument("--port", type=int, default=8123)
    serve.add_argument("--lan", action="store_true")

    status = sub.add_parser("status", help="engine health, unit state, recent events")
    status.add_argument("--port", type=int, default=8123)

    feed = sub.add_parser("feed", help="send one event to the local engine")
    feed.add_argument("kind", help=f"event kind: {' '.join(sorted(F.KIND_TO_MOOD))}")
    feed.add_argument("--port", type=int, default=8123)
    feed.add_argument("--key-file", default=str(
        __import__("pathlib").Path.home() / ".config/familiar/key"))

    ns = ap.parse_args(argv)
    try:
        if ns.cmd == "moods":
            print(" ".join(sorted(F.MOODS)))
            return 0
        if ns.cmd == "serve":
            return engine_mod.main(["--port", str(ns.port)] + (["--lan"] if ns.lan else []))
        if ns.cmd == "status":
            return _cmd_status(ns.port)
        if ns.cmd == "feed":
            return _cmd_feed(ns.kind, ns.port, ns.key_file)
        client = RouterClient()
        if ns.cmd == "ping":
            print(client.ping())
            return 0
        if ns.cmd == "show":
            period, frames_list = F.mood_frames(ns.mood)
            n = client.show(frames_list, period_ms=period)
            print(f"showing {ns.mood}: {n} frames @ {period} ms")
            return 0
        if ns.cmd == "clear":
            print("clear:", client.clear())
            return 0
    except BridgeError as exc:
        print(f"familiar error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"familiar: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
