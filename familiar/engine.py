"""The Familiar engine: webhook events -> moods -> matrix frames.

Loop contract: every show() doubles as the MCU heartbeat, so while serving
we re-push the current mood at least every HEARTBEAT_S (20 s) — the sketch's
30 s idle timeout is the backstop, never the primary. Mood expiry and the
sleepy-when-hot telemetry check tick on the same loop.
"""

from __future__ import annotations

import json
import os
import queue
import signal
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    from familiar import frames as F
    from familiar import webhook
    from familiar.bridge_client import RouterClient
    from familiar.moods import MoodMachine
else:
    from . import frames as F
    from . import webhook
    from .bridge_client import RouterClient
    from .moods import MoodMachine

HEARTBEAT_S = 20.0
HEALTH_POLL_S = 60.0
SLEEPY_TEMP_C = 78.0
EVENTS_FILE = os.environ.get(
    "FAMILIAR_EVENTS_FILE",
    os.path.expanduser("~/.local/state/familiar_events.jsonl"))


def _health_temp_c() -> float | None:
    try:
        import glob
        best = None
        for zone in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
            try:
                with open(zone) as f:
                    milli = int(f.read().strip())
                best = milli / 1000.0 if best is None else max(best, milli / 1000.0)
            except (OSError, ValueError):
                continue
        return best
    except Exception:
        return None


def _log_event(kind: str, mood: str) -> None:
    try:
        os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
        with open(EVENTS_FILE, "a") as f:
            f.write(json.dumps({"kind": kind, "mood": mood,
                                "ts": time.time()}) + "\n")
    except OSError:
        pass


class Engine:
    def __init__(self, client: RouterClient, machine: MoodMachine,
                 events: "queue.Queue[tuple[str, float]]",
                 now=time.monotonic, temp_fn=_health_temp_c):
        self.client = client
        self.machine = machine
        self.events = events
        self._now = now
        self._temp_fn = temp_fn
        self._last_show = 0.0
        self._last_health = 0.0
        self.stop = False

    def _show_mood(self) -> None:
        period, frames_list = F.mood_frames(self.machine.mood)
        self.client.show(frames_list, period_ms=period)
        self._last_show = self._now()

    def step(self) -> str | None:
        """One engine tick: drain one event, tick moods, heartbeat, health."""
        changed = None
        try:
            kind, _ts = self.events.get_nowait()
            changed = self.machine.event(kind)
            _log_event(kind, self.machine.mood)
        except queue.Empty:
            pass
        expired = self.machine.tick()
        changed = changed or expired

        now = self._now()
        if now - self._last_health >= HEALTH_POLL_S:
            self._last_health = now
            temp = self._temp_fn()
            if temp is not None and temp >= SLEEPY_TEMP_C:
                changed = self.machine.set("sleepy") or changed

        if changed or (now - self._last_show) >= HEARTBEAT_S:
            self._show_mood()
        return changed or self.machine.mood

    def run(self) -> int:
        def _stop(*_a):
            self.stop = True

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
        self._show_mood()
        while not self.stop:
            self.step()
            time.sleep(0.25)
        try:
            self.client.clear()   # graceful: dark matrix on exit
        except Exception:
            pass                  # sketch idle timeout is the backstop
        return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=webhook.DEFAULT_PORT)
    ap.add_argument("--lan", action="store_true",
                    help="bind the webhook on 0.0.0.0 (default loopback)")
    ns = ap.parse_args(argv)

    events: "queue.Queue[tuple[str, float]]" = queue.Queue(maxsize=webhook.QUEUE_MAX)
    webhook.serve(events, key="", port=ns.port, lan=ns.lan)
    client = RouterClient()
    engine = Engine(client, MoodMachine(), events)
    return engine.run()


if __name__ == "__main__":
    raise SystemExit(main())
