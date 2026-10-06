"""familiar.* command specs for the Muse Linux Device SDK.

Follow the COMMAND_SPECS contract in the SDK's
linux/src/musegadget/executor.py — validated against the real upstream
module by tests/test_contract.py. Registered into a live SDK executor by
muse_integration/install.py via register() below (single source: the
dispatch logic lives here, the executor only gains a 3-line hook).
"""

import os

FAMILIAR_SPECS = {
    "familiar.status": {
        "description": (
            "Report the pixel Familiar's state: current mood, bridge ping, "
            "board telemetry (temperatures, memory, disk, load)."
        ),
        "required": {},
        "optional": {},
    },
    "familiar.show": {
        "description": (
            "Play a mood animation on the UNO Q LED matrix (happy, sad, "
            "alert, sleepy, curious, idle, off) for a few seconds."
        ),
        "required": {
            "mood": {
                "type": "string",
                "description": "happy, sad, alert, sleepy, curious, idle or off.",
            },
        },
        "optional": {},
    },
    "familiar.feed": {
        "description": (
            "Feed the Familiar an event kind (ci_green, deploy_fail, merge, "
            "incident, mention, poke...) — same as a webhook poke."
        ),
        "required": {
            "kind": {
                "type": "string",
                "description": "Event kind; unknown kinds are ignored.",
            },
        },
        "optional": {},
    },
}

FAMILIAR_MOODS = ("happy", "sad", "alert", "sleepy", "curious", "idle", "off")


def _cli_cmd(repo: str, uv_bin: str, args: str) -> str:
    return (f"PYTHONPATH={repo} {uv_bin} run --with msgpack "
            f"--directory {repo} python3 -m familiar.cli {args}")


def _valid_kind(kind) -> bool:
    return (isinstance(kind, str) and 0 < len(kind) <= 64
            and kind.replace("_", "").isalnum())


def register(namespace: dict, repo: str | None = None,
             uv_bin: str | None = None) -> None:
    """Merge FAMILIAR_SPECS into an executor module and wrap its
    Executor.run to dispatch the familiar.* commands.

    `namespace` is the executor module's globals() (the hook calls
    register(globals())) — dict updates and Executor-class patching both
    propagate to the live module, and this works whether the module is
    imported as a package or exec'd fresh.

    Everything runs through the SDK's own system_run (bash as the paired
    account) with Muse-supplied params allowlisted BEFORE any command is
    built — the hardening the original runbook spelled out, now enforced
    in one place.
    """
    repo = repo or os.path.expanduser("~/muse-familiar")
    uv_bin = uv_bin or os.path.expanduser("~/.local/bin/uv")
    key_file = os.path.expanduser("~/.config/familiar/key")
    _error = namespace["error"]

    def _status(executor, params):
        return executor.system_run(
            {"command": _cli_cmd(repo, uv_bin, "ping")}, None)

    def _show(executor, params):
        mood = params.get("mood", "idle")
        if mood not in FAMILIAR_MOODS:
            return _error("bad mood")
        return executor.system_run(
            {"command": _cli_cmd(repo, uv_bin, f"show {mood}")}, None)

    def _feed(executor, params):
        kind = params.get("kind", "poke")
        if not _valid_kind(kind):
            return _error("bad kind")
        return executor.system_run({"command":
            f'curl -s -m 5 -X POST localhost:8123/poke '
            f'-H "X-Familiar-Key: $(cat {key_file})" '
            f'-d \'{{"kind": "{kind}"}}\''}, None)

    handlers = {"familiar.status": _status, "familiar.show": _show,
                "familiar.feed": _feed}

    namespace["COMMAND_SPECS"].update(FAMILIAR_SPECS)

    Executor = namespace["Executor"]
    original_run = Executor.run

    def run(self, command, params, timeout_ms=None):
        handler = handlers.get(command)
        if handler is None:
            return original_run(self, command, params, timeout_ms)
        try:
            return handler(self, params)
        except Exception as exc:  # same shape the SDK's own run() uses
            return _error(f"{type(exc).__name__}: {exc}")

    Executor.run = run
