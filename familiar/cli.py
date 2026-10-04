"""familiar — CLI for the creature.

    python3 -m familiar.cli ping
    python3 -m familiar.cli show happy
    python3 -m familiar.cli serve [--lan]
    python3 -m familiar.cli moods

Exit codes: 0 ok · 2 bridge/hardware error · 3 bad usage value.
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

    ns = ap.parse_args(argv)
    try:
        if ns.cmd == "moods":
            print(" ".join(sorted(F.MOODS)))
            return 0
        if ns.cmd == "serve":
            return engine_mod.main(["--port", str(ns.port)] + (["--lan"] if ns.lan else []))
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
