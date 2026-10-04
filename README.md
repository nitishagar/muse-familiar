# muse-familiar

**A pixel creature that lives on your Arduino UNO Q's LED matrix — fed by
your webhooks, seen and heard by [Muse](https://gadgets.muse.ai/).**

The UNO Q is a dual-brain board (Qualcomm QRB2210 running Debian + STM32U585
running your sketches). The Familiar is a tiny being drawn on its 8×13 LED
matrix: it idles and blinks, hops when your CI goes green, sulks when a
deploy fails, gets wide-eyed at incidents, and dozes when the board runs
hot. Feed it from GitHub, Home Assistant, or a curl one-liner. Pair it with
Muse and it becomes a gadget your assistant can see and cheer up — and it
narrates its moods into your Muse chat.

Nobody has shipped a Muse gadget that actuates local hardware on Linux —
this is a first, on a board built for exactly this kind of mischief.

```
 GitHub / HA / curl ──POST /poke──> familiar-engine (Debian side)
                                        │  mood machine + frame art
                                        │  msgpack-RPC (chunked, ~19ms)
                                        ▼
                        FramePlayer sketch (STM32U585 / Zephyr)
                                        │
                                        ▼
                              8×13 LED matrix — the Familiar
 Muse <──send-user-msg── narration ─────┘
  (paired gadget: familiar.status / show / feed commands)
```

## Quickstart (on the UNO Q)

```sh
# 1. flash the frame player (needs the board's own arduino-cli + password)
cd firmware && ./upload.sh

# 2. run the creature (webhook on loopback; FAMILIAR_LAN=1 ./serve for LAN)
mkdir -p ~/.config/familiar && head -c24 /dev/urandom | base64 > ~/.config/familiar/key
systemctl --user enable --now familiar-engine   # after installing the unit

# 3. make it happy
curl -X POST localhost:8123/poke \
     -H "X-Familiar-Key: $(cat ~/.config/familiar/key)" \
     -d '{"kind":"ci_green"}'
```

Webhook kinds → moods: `ci_green`/`deploy_ok`/`merge` → **happy**;
`ci_red`/`deploy_fail` → **sad**; `alert`/`incident` → **alert**;
`mention`/`poke` → **curious**; `hot` → **sleepy**. Unknown kinds are
ignored. One-line test from another machine (LAN mode):
`curl -X POST http://<board-ip>:8123/poke -H "X-Familiar-Key: …" -d '{"kind":"merge"}'`.

## Pairing with Muse

The [Muse gadget SDK](https://github.com/facebookincubator/muse-gadget-sdk)
runs on the board's Debian side (install:
`muse_integration/COMMANDS.md`). Then: `sudo musegadget pair` on the board,
Muse app → Settings → Devices → Developer mode → Add Device →
`MuseGadgetXXXXXX`. Ask Muse *"make the Familiar happy"* or *"how is the
Familiar doing?"* — and mood changes appear in your chat:
**"The Familiar is now sad (event: deploy_fail)."**

## Safety

- The sketch enforces its own bounds: ≤ 4 fps, 3-bit grayscale, ≤ 64
  frames, and a 30-second idle timeout to a dim glyph (a crashed engine
  can never leave the matrix lit or flashing).
- Webhook: shared key, 2 KiB cap, 12 req/min, bounded queue, loopback by
  default.
- Everything runs as user services + one project dir; stock board services
  untouched. The arduino-router socket is used only via its documented
  client API and never re-permissioned or exposed to Muse.
- Teardown: `systemctl --user disable --now familiar-engine`,
  `sudo bash sdk-linux/install.sh --uninstall`, reflash anytime via
  `firmware/upload.sh`.

## Repo map

| Path | What |
|---|---|
| `firmware/FramePlayer/` | the Zephyr sketch (generic frame player, MCU-side clamps) |
| `familiar/` | the engine: frame art, mood machine, webhook, bridge client, CLI |
| `units/` | systemd user unit + NTP gate + display reset + kill-test |
| `muse_integration/` | `familiar.*` command specs (contract-tested) + pairing runbook |
| `tests/` | 19 host-side tests incl. a fake router socket |
| `thoughts/` | full research + plan + validation trail (the honest audit log) |

## GIF / demo shot list

1. Idle blink (5 s), 2. `ci_green` poke → happy hop (loop), 3. `deploy_fail`
→ sad sag, 4. `incident` → alert strobe-eyes, 5. board heating → sleepy z's,
6. phone: Muse chat showing the narration line, 7. Muse command
"familiar.show happy" in action. Shoot in dim light, phone on a stand,
~15 s total.

## Credits & license

MIT (this repo). Built on Meta's muse-gadget-sdk (Apache-2.0), Arduino's
RouterBridge/RPClite (MPL-2.0) and Arduino_LED_Matrix; the bridge client is
an independent implementation of the msgpack-RPC protocol — see NOTICE.md.
