"""familiar.* command specs for the Muse Linux Device SDK.

Follow the COMMAND_SPECS contract in the SDK's
linux/src/musegadget/executor.py — validated against the real upstream
module by tests/test_contract.py. Install: COMMANDS.md runbook.
"""

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
