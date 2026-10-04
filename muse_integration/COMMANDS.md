# Giving Muse the Familiar commands

The SDK is installed on the board (`MuseGadget6D5B09`). Two steps remain:
one command on the board, one tap on your phone. Then Muse can see, feed
and animate your creature — and the creature narrates into your Muse chat.

## 1. Pair (board + phone)

```sh
ssh arduino@<board-ip>
sudo musegadget pair        # opens a 10-minute pairing window
```

On your phone: Muse app → Settings → Devices → enable **Developer mode** →
**Add Device** → pick `MuseGadget6D5B09` → accept the community-device
warning → choose your Wi-Fi. Done: `musegadget info` shows `paired: yes`.

## 2. Add the familiar.* commands to the executor

Edit `/opt/musegadget/venv/lib/python3.*/site-packages/musegadget/executor.py`
(or your SDK checkout + `bash install.sh --from .`):

- merge `FAMILIAR_SPECS` from `muse_integration/familiar_specs.py` into
  `COMMAND_SPECS`;
- add VALIDATED branches in `Executor.run` — params are Muse-supplied and
  `system_run` goes through `/bin/bash -c`, so allowlist before building:

```python
from musegadget.executor import error  # module-level helper in executor.py

FAMILIAR_MOODS = ("happy", "sad", "alert", "sleepy", "curious", "idle", "off")

if command == "familiar.status":
    return self.system_run({"command":
        "PYTHONPATH=/home/arduino/muse-familiar "
        "/home/arduino/.local/bin/uv run --with msgpack --directory "
        "/home/arduino/muse-familiar python3 -m familiar.cli ping"})
if command == "familiar.show":
    mood = params.get("mood", "idle")
    if mood not in FAMILIAR_MOODS:
        return error("bad mood")
    return self.system_run({"command":
        "PYTHONPATH=/home/arduino/muse-familiar "
        "/home/arduino/.local/bin/uv run --with msgpack --directory "
        "/home/arduino/muse-familiar python3 -m familiar.cli show " + mood})
if command == "familiar.feed":
    kind = params.get("kind", "poke")
    if len(kind) > 64 or not kind.replace("_", "").isalnum():
        return error("bad kind")
    return self.system_run({"command":
        "curl -s -X POST localhost:8123/poke "
        "-H 'X-Familiar-Key: '$(cat /home/arduino/.config/familiar/key) "
        "-d '{\"kind\": \"" + kind + "\"}'"})
```

Then ask Muse: *"How is the Familiar doing?"* / *"Make the Familiar happy."* /
*"Tell the Familiar there was an incident."*

## 3. Narration into your Muse chat

Already built in: when the engine's mood changes it calls
`musegadget send-user-msg "The Familiar is now happy (event: ci_green)."`
— active automatically once paired (falls back to
`~/.local/state/familiar_narration.jsonl` before pairing). Keep events in
their own side chat by exporting `MUSE_SESSION_ID`.

## Teardown

- `systemctl --user disable --now familiar-engine` (creature)
- `sudo bash ~/muse-familiar/sdk-linux/install.sh --uninstall` (SDK;
  add `--purge` to forget identity/pairing)
- Reflash the MCU sketch any time with `firmware/upload.sh`.
