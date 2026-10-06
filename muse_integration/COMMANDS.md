# Giving Muse the Familiar commands

The SDK is installed on the board (`MuseGadgetXXXXXX`). Two steps remain:
one command on the board, one tap on your phone. Then Muse can see, feed
and animate your creature — and the creature narrates into your Muse chat.

## 1. Pair (board + phone)

```sh
ssh arduino@<board-ip>
sudo musegadget pair        # opens a 10-minute pairing window
```

On your phone: Muse app → Settings → Devices → enable **Developer mode** →
**Add Device** → pick `MuseGadget…` → accept the community-device warning →
choose your Wi-Fi. Done: `musegadget info` shows `paired: yes`.

## 2. Register the familiar.* commands (one command)

```sh
cd ~/muse-familiar
sudo python3 muse_integration/install.py          # --check to preview
```

What it does: backs up the SDK's `executor.py` (timestamped, kept beside
it), appends a 3-line guarded hook that imports
`muse_integration/familiar_specs.py` from this repo (single source — specs
and the allowlisted dispatch live there, not in the venv), compiles the
result, atomically swaps it in, restarts `musegadget`, and verifies the
`familiar.status` / `familiar.show` / `familiar.feed` specs registered. If
the repo is ever missing at load time the hook logs and skips — the gadget
service keeps working without the familiar commands.

Undo at any time:

```sh
sudo python3 muse_integration/install.py --remove   # restores the original executor
```

Then ask Muse: *"How is the Familiar doing?"* / *"Make the Familiar
happy."* / *"Tell the Familiar there was an incident."*

Trust boundary: `install.py` runs as root and verifies the patch by
importing the repo's stdlib-only `familiar_specs.py` — i.e. it executes
code from the repo checkout as root, once, exactly like `sudo pip install
<local dir>` would. Only run it on a checkout you control; the running
service itself imports it as the paired account at every start.

Params are Muse-supplied and commands run via the SDK's own bash
`system.run` — moods and event kinds are allowlisted before anything is
executed (see `familiar_specs.py: register`).

## 3. Narration into your Muse chat

Already built in: when the engine's mood changes it calls
`musegadget send-user-msg "The Familiar is now happy (event: ci_green)."`
— active automatically once paired (falls back to
`~/.local/state/familiar_narration.jsonl` before pairing). Keep events in
their own side chat by exporting `MUSE_SESSION_ID` in the engine's
environment (e.g. a systemd drop-in), e.g.
`~/.config/systemd/user/familiar-engine.service.d/narration.conf`:

```ini
[Service]
Environment=MUSE_SESSION_ID=6f1c2d4e-…
```

## Teardown

- `systemctl --user disable --now familiar-engine` (creature; then
  `systemctl --user unlink familiar-engine`)
- `sudo python3 muse_integration/install.py --remove` (familiar commands)
- SDK: from a [muse-gadget-sdk](https://github.com/facebookincubator/muse-gadget-sdk)
  checkout, `sudo bash linux/install.sh --uninstall` (add `--purge` to
  forget identity/pairing)
- Reflash the MCU sketch any time with `firmware/upload.sh`.
