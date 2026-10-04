---
date: 2026-10-04T14:30:00+05:30
researcher: ZCode agent (session goal: muse-familiar open-source first-to-market)
git_commit: (added in this commit)
branch: main
repository: muse-familiar (local; push private to nitishagar, flip public at release)
topic: "The Familiar: a pixel creature on the UNO Q LED matrix driven by Muse + webhooks — feasibility research for the open-source first-to-market build"
tags: [research, muse, gadgets, arduino-uno-q, led-matrix, routerbridge, msgpack-rpc, webhook]
scale: medium
status: complete
last_updated: 2026-10-04
last_updated_by: ZCode agent
---

# Research: the Familiar (UNO Q LED-matrix Muse gadget)

## Research Question
> "Get on to working [on] the idea using LEDs, and open-source the implementation… be the first to market with muse running on uno Q doing something nice and quirky." (with a real SDK token now supplied for pairing)

## Intent
- **Problem**: Build and open-source one quirky idea — Muse on the UNO Q driving the board's LEDs (8×13 matrix + user RGB) — first to market; pair the board with the user's real token; deliver a social pack.
- **Proposed outcome**: A public repo with a working Familiar (pixel creature on the matrix, fed by webhooks, seen/heard by Muse when paired), a social pack tagging Muse + Arduino UNO Q.
- **Constraints**: v2.7 loop; repo under ~/repos/learn, push **private** to nitishagar first, open-source (public) at release; **no co-author**; the SDK token is a root-only secret — never in any repo/log/artifact; hallpi untouched; router socket used ONLY via the documented client API (no widening, no raw passthrough to Muse).
- **Open questions**:
  1. Can the LED matrix actually be driven end-to-end from Linux (API + bridge + upload), on-board?
  2. Does uploading a sketch clobber anything the user needs (stock MCU firmware/Cloud features)? Can it be backed up?
  3. What can be verified before the user completes phone-side BLE pairing?
  4. What exactly goes in the open-source + social release (assets, licensing, attribution)?

## Summary
Every element of the critical path is now **verified on the board**: the `Arduino_LED_Matrix` API exists in the installed Zephyr core (`draw()` takes a 104-byte grayscale framebuffer — 8×13, 8 levels); `Arduino_RouterBridge` 0.4.3 + `Arduino_RPClite` 0.3.0 + `MsgPack` libraries are **already installed** on the board; the official tutorial's Python `ArduinoBridge` client (msgpack-RPC over the router's Unix socket) was extracted and the board runs `msgpack` under uv; and — decisive — **a matrix sketch compiles ON the board in ~25 s (12% flash, 11% RAM)** with the network upload ports visible via the board's own arduino-cli. The Muse Linux SDK installs with the user's token (system-wide, user-approved direction given); actual pairing needs the user's phone app (10-minute window) — everything else is verifiable without it. Survey position (from the prior audited research): no Linux Muse gadget actuates local hardware or has a display — the Familiar is first in both.

## Detailed Findings

### MCU tier — LED matrix (all [V] on-board unless noted)
- `Arduino_LED_Matrix` library ships in the zephyr core (0.90.0): `begin`, `draw(const uint8_t*)` (104 px grayscale), `loadFrame(uint32_t[4])`, `playVideo`, `setGrayscaleBits(bits)`, `clear`, text/scroll via `ArduinoGraphics` (dependency, now installed v1.1.5). Basic/Video examples present. [V — core files read]
- **On-board compile works**: Basic.ino compiled on the board: 94,928 B flash (12%), 30,848 B RAM (11%). AUDIT CORRECTION on timing: warm-cache compile ~25 s, fresh-cache ~80 s — budget ~1.5 min per iteration; `~/.arduino15` now 652 MB total (packages/arduino 134 MB, zephyr toolchain 405 MB, others ~110 MB) against 2.3 GB free. [V — executed twice, timed by auditor]
- Toolchain is compact (packages 134 MB + tools: zephyr-sketch-tool, bossac, remoteocd, bin2uf2…). Library index needed `lib update-index` + `lib install ArduinoGraphics` (name has no underscore; `Arduino_Graphics` does not exist). [V]
- Network upload: `arduino-cli board list` shows two network ports for FQBN `arduino:zephyr:unoq`. AUDIT ADDITION (credential seam): the network upload authenticates with the **board's Linux password** (held out-of-band, same credential as SSH; passed via upload properties at invocation, never committed). Upload not yet exercised (first implementation milestone); BLE controller has zero bonds but is currently Pairable:no/Discoverable:no — the SDK installer configures BlueZ for pairing, so pairing preconditions are only meaningful post-install. [V ports/journal; R auth semantics]
- Zephyr core on board = 0.90.0; board's index serves 1.0.0 — pin 0.90.0 to avoid mid-project drift (prior audited finding). [V]

### Bridge tier — Linux↔MCU (RouterBridge)
- `Bridge` API (sketch side): `begin()`, `.provide(name, cb)`, `.call()`, `.notify()`; nested `call()` inside callbacks can deadlock (documented). [R — Arduino_RouterBridge GitHub; lib installed on board [V]]
- Linux side: msgpack-RPC over `/var/run/arduino-router.sock` (world-rw, root-owned — client use only, never re-permission, never expose to Muse raw); `msgpack` runs on the board via uv env [V]. AUDIT CORRECTION: the tutorial's Python client was NOT successfully extracted (first URL 404'd; the code lives only inside the tutorial markdown at /tmp/tutorial.md L656+) — AND arduino/docs-content is **CC BY-SA 4.0**, so a copied client cannot ship MIT in our repo. Mandatory: write our own minimal client from the msgpack-rpc frame protocol (Arduino_RPClite's spec; check that repo's license at implement time) — protocol-compatible, independently authored, attributed in NOTICE.
- Router registers internal methods (`$/version`, `$/serial/*`, `hci/*`, `mon/*`) [V — journal]. Device-method forwarding (a sketch's `provide()`s reachable from a Linux client) is **UNPROVEN on this board** — no sketch has ever been uploaded and no round-trip attempted; treat as [R — library docs] and de-risk it as the FIRST implementation milestone.

### Muse tier
- The user supplied a real SDK token (value redacted; held out-of-band for install only — root-only at `/var/lib/musegadget/sdk_token` per SDK). AUDIT CORRECTION: the SDK tree is NOT currently on the board (the prior POC's clean-removal proof deleted `~/muse-unoq`; only `unoq/` was redeployed) — all SDK facts below cite the verified clone at `~/tmp-research/muse-gadget-sdk` on the NUC and must be re-established on the board as implementation step 0 (tar-over-ssh copy, proven flow). [V — NUC clone; board state corrected]
- Pairing: BLE from the Muse phone app, Developer mode > Add Device, device `MuseGadgetXXXXXX`, 10-min window (`sudo musegadget pair` reopens). **Only the user can complete the phone side** — a manual gate by design. Everything else (service running, pairing open, gadget code, command specs) is verifiable pre-pairing. [V — SDK README]
- Inbound: Muse runs commands (specs/`system.run`); outbound: `musegadget send-user-msg` (the Familiar "speaks" into a side chat). Webhook feeding uses the official pebble pattern (stdlib HTTP listener → engine), independent of Muse. [V — SDK + prior validated POC]

### Board baseline (carried, [V])
Debian 13/aarch64, BLE hci0 up, user `arduino` (sudo, gpiod), user RGB LEDs sysfs-writable (binary), 6+ thermal zones, no RTC (NTP gate pattern proven), uv at ~/.local/bin, prior `unog` core deployed at ~/muse-unoq (reusable: leds/health/notifier + validated spec-contract harness in the muse-gadget-poc repo), 2.3 GB disk free.

### Release/social context [R — prior audited survey]
Ecosystem ~3 days old; no Linux hardware gadget exists; Discord #projects requires photo/video + README + GitHub repo; gadgets.muse.ai features community builds; HN/reception warm (946★ SDK in 2 days). Tag targets: Muse (gadgets.muse.ai / @muse), Arduino UNO Q (@arduino, docs.arduino.cc/hardware/uno-q). License choice: MIT for ours; SDK Apache-2.0 attributed; NOTICE required.

## Implicit Spec — invariants any implementation must uphold
1. **Token secrecy**: the SDK token appears in NO repo file, doc, log, social artifact, or command captured in shell history — it is passed once to `install.sh` on the board and lives root-only. Observable: secrets gate (mgst_ tier) green in both modes across ALL repos before any push/flip.
2. **Board safety (scoped)**: system-wide change limited to the Muse SDK install (user-approved); POC code = user units + ~/muse-familiar dir; stock arduino-* services untouched; router socket perms never modified. Observable: snapshot diff (unit files, /etc/systemd, socket mode/owner) + uninstall path documented.
3. **MCU flash safety**: before first upload, snapshot what the flash path touches (documented risk: upload replaces the running sketch; stock MCU functionality that depends on a stock sketch degrades until reflash); upload only via the documented arduino-cli network flow; the Familiar sketch keeps the Bridge alive so uploads remain possible. Observable: pre/post notes + re-upload proven.
4. **No raw router passthrough to Muse**: Muse commands drive the Familiar through OUR validated methods (engine CLI), never by exposing router RPC. Observable: grep (executable code) + review.
5. **Familiar effects bounded & crash-safe** (carried, proven patterns): matrix/LED effects revert or idle-loop; service stop resets LEDs (ExecStopPost hook-script pattern); flock serialization where two writers exist. **Photosensitivity/brightness bound**: animation frame rate ≤ 4 fps and grayscale ≤ 7 by default (product emits flashing light — cap it). Observable: kill-test port + codec bounds in tests.
5a. **Webhook listener hardened**: shared-key header (constant-time compare), payload cap ≤ 2 KiB, per-minute rate cap with flood test, bind loopback by default (LAN exposure is a conscious config). Observable: unit tests incl. flood case.
5b. **Upload concurrency**: MCU uploads never run concurrently with the engine (engine pauses via the same flock before upload; arduino-cli is the only writer). Observable: engine pause hook + upload script takes the lock.
6. **No-token demo mode**: every automated criterion passes pre-pairing; webhook-fed animations + CLI work with no Muse at all. Observable: criteria run before pairing completes.
7. **Open-source hygiene**: MIT LICENSE, NOTICE (SDK Apache-2.0 + tutorial-derived client attribution), no secrets, no co-author trailers, README with GIF-ready demo instructions, `SOCIAL.md` pack tagging Muse + Arduino UNO Q. Repo created **private** first, secrets-gated, then flipped public at release.
8. **Bounding assumptions**: board at 192.168.0.134 (key auth); user completes phone pairing during a 10-min window when they choose (implementation leaves pairing OPEN and hands over); demo webhook source = curl/GitHub-style JSON (no real GitHub app needed); matrix = 8×13 grayscale (no color); the prior muse-gadget-poc repo stays private as the engineering trail.

## Workload & Scale Envelope
- Hot ops: webhook pokes (event-rate; rate-capped by invariant 5a), animation pushed as one RPC per sequence (NOT per-frame; MCU-side timer plays it), Muse commands (human-rate), notify messages (edge-triggered). RPC payload ≈ 104 B/frame × ≤ 8 frames + overhead ≈ ≤ 1 KiB per sequence [design budget]. poke→first-frame latency target < 500 ms is a TARGET to measure at milestone 1, not an observed fact. [R]
- Resources: RAM 2.9 GB avail vs engine < 30 MB; MCU 11% RAM headroom proven by compile; disk 2.3 GB free. Latency target: poke→first frame < 500 ms on LAN. [R-assumption]

## Verification Surface
- **Commands (board)**: compile check (proven); upload via network port (to prove); bridge round-trip `familiar.ping` (to prove); matrix visual check via a test pattern + camera/eyes (manual gate); `systemctl status musegadget` + `musegadget info` post-install; snapshot diffs.
- **Oracles**: matrix frame codec unit-tested host-side (104-byte layout); bridge client tested against a FAKE router socket (msgpack-rpc server in tests); mood machine scripted-state tests (ported edge-trigger harness); spec-contract test vs upstream executor (harness exists in muse-gadget-poc — copy).
- **Observability**: journalctl (user units + musegadget), router journal, engine JSONL events, MCU serial via router `$/serial` if needed.
- **Gaps**: no automated pixel-level assertion (human/camera gate); pairing completion itself (user phone); public-flip consequences (irreversible visibility — user-approved by the open-source instruction; content gate = secrets scan of final tree).

## Hard Cores
1. **MCU bridge tier**: Familiar.ino (matrix render + `provide()`d RPC methods) + upload safety + python client round-trip — the never-before-done part.
2. **Familiar engine + Muse wiring**: mood/animation engine, webhook listener, `familiar.*` specs + send-user-msg narration, service hygiene.
(Social pack + public flip + install runbook = ordinary work with strict gates.)

## Evidence Ledger
| Claim | Evidence | Trust | Load-bearing |
|---|---|---|---|
| Matrix API: draw(104 B grayscale), setGrayscaleBits, in-core | core files on board | V | yes |
| On-board compile of matrix sketch succeeds (12%/11%) | executed 2026-10-04 | V | yes |
| RouterBridge+RPClite+MsgPack installed on board | arduino-cli lib list | V | yes |
| Python ArduinoBridge client (socket+msgpack+rx thread) | official tutorial extracted | V | yes |
| msgpack runs on board (uv env) | import test | V | yes |
| Router: unix socket, world-rw, internal methods; device methods via sketch provide() | ss/journal + lib docs | V/R | yes |
| Network upload ports visible for unoq | board list | V | yes |
| Upload replaces running sketch (stock MCU features degrade) | Arduino upload semantics | R | yes |
| SDK install system-wide; token root-only; pairing needs phone app | SDK README (on board) | V | yes |
| No Linux hardware Muse gadget exists; Discord needs repo+media | prior audited survey | R | yes |
| User supplied a real token (redacted here) | ticket | V | yes |

## Architecture Insights
- Push-once-render-locally: send a whole animation (few frames) per RPC call; the sketch plays it on its own timer — avoids per-frame RPC chatter and router load. Applicability: any frame-rate-sensitive bridge use.
- Reuse the proven unog patterns wholesale (edge-trigger notifier, hook-script units, flock, spec-contract harness, secrets gate) — they were adversarially reviewed hours ago; the Familiar engine is a new front-end on the same skeleton.
- The tutorial's Python client is Apache-2.0-ish Arduino docs content (CC BY-SA? verify file header at implement time; else rewrite minimal client from the msgpack-rpc spec — the extracted file includes full protocol handling to mirror).

## Historical Context (from thoughts/)
Two prior audited research docs in muse-gadget-poc cover the platform, survey, and UNO Q POC (unog). This doc adds the matrix/bridge tier + real-token pairing + release scope, and supersedes the "matrix = out of scope" bounding assumption of the prior plan (user direction now puts LEDs at the center).

## Coverage & Open Questions
- Searched: on-board core libs/APIs/examples, lib index, compile path, router journal + protocol client, toolchain sizes, SDK install prerequisites; carried the audited platform/survey facts.
- Deliberately bounded: actual upload not yet run (first implementation milestone, with backup note); no reverse-engineering of the stock sketch; no GitHub App integration (generic webhook + curl demo); no color matrix (hardware is blue-mono); social pack copy drafted for user review (we post nothing ourselves); SDK tree must be re-copied to the board (audit correction); our bridge client is written from the protocol spec, not copied from the CC BY-SA tutorial (licensing correction); pairing re-open path documented (`sudo musegadget pair`) for window expiry mid-demo.
- Residual risks: (a) upload could brick the MCU side into a state needing BOOTSEL/EDL recovery — mitigate: only documented flows, verify Bridge survives, keep recovery notes (docs mention EDL 05c6:9008); (b) pairing may fail on BLE/MTU quirks — `musegadget pair` reopen + journal diagnosis; (c) tutorial client licensing — verify/rewrite at implement; (d) public flip is irreversible-visibility — content gate before flip; (e) matrix visual quality unverifiable by CI — manual gate + video.
- Intent open questions → disposition: Q1 answered (verified above); Q2 = risk note + backup/recovery steps in plan; Q3 = pre-pairing verification list (install state, pairing-open, engine demo, specs); Q4 = release checklist (LICENSE/NOTICE/README/SOCIAL.md/tags, flip procedure).
