<!-- SIGNPOST | 2/5: PLAN | single source of truth; implementation must conform — divergence means amending this file in the same change, not improvising
     Prev: IMPLICIT_SPEC.md | Next: PLAN_VALIDATION.md -->
# muse-familiar Implementation Plan
scale: medium

## Overview
The Familiar: a pixel creature on the UNO Q's 8×13 LED matrix — fed by webhooks, narrated into and driven by Muse once paired — built, hardened, and released open-source (private repo → gates → public flip) with a social pack.

## Current State
Facts verified in `thoughts/shared/research/2026-10-04-muse-familiar-matrix.md` (audit-corrected): matrix API + RouterBridge/RPClite/MsgPack on-board; on-board compile works (94,928 B / 12% flash; warm ~25 s, fresh ~80 s; toolchain 652 MB, 2.3 GB free); network upload ports visible (auth = board Linux password); **router→sketch forwarding UNPROVEN** (Milestone 1 proves it); SDK tree absent from board (re-copy from the clean NUC clone is step 0); tutorial client CC BY-SA → own client from the RPClite protocol; a real SDK token is held out-of-band for Phase 3's install. Reusable (copy 1:1 from muse-gadget-poc): `unoq/unog/*` (leds/health/notifier), `unoq/units/*.sh` hooks, kill-test pattern, `tests/` mock-server + contract-test harness, `tools/secrets_gate.py`.

## Desired End State
- Board: `~/muse-familiar/` engine + `familiar-engine` user unit; MCU running the **FramePlayer sketch** (generic, frozen after Phase 1) with ping/show/clear methods, MCU-side idle timeout and grayscale/fps clamps; Muse SDK installed with the user's token, pairing OPEN (user's phone step documented); webhook feeding animations; mood narration prepared.
- Repo: MIT + NOTICE, README (quickstart, GIF shot list, safety/uninstall), SOCIAL.md pack (tagging Muse + Arduino UNO Q), tests green host-side and on-board, secrets gate green on both repos — pushed private, then **public flip**.
- Evidence: bridge round-trip + measured latency + frame period; re-upload proof; kill-test; snapshot diffs; no-token demo as the Phase 3 EXIT gate.

## What We're NOT Doing
- No color matrix (mono hardware), no GitHub App integration (generic webhook + curl demo), no Discord/HN posting by us (pack only), no reverse-engineering stock MCU firmware, no touching muse-gadget-poc's deployed unog beyond reuse, no hallpi, no router socket re-permissioning, no per-frame RPC.

## Approach
Four phases; Milestone 1 de-risks the only novel hard core (bridge) before anything is built on it.

Key decisions (each tied to an invariant):
1. **FramePlayer sketch, frozen early** (advisor #11): the .ino is a GENERIC frame player — `familiar.ping`, `familiar.show(frames, period_ms)`, `familiar.clear()` — with ALL mood logic host-side, so Phases 2–3 iterate at zero compile cost. Uploaded TWICE in Phase 1 (re-upload proof, inv.3).
2. **Sketch-side safety** (advisor #3/#5): `setGrayscaleBits(3)`; drop sequences with period < 250 ms (≤ 4 fps, inv.5) at the MCU; **MCU idle timeout** — if no `show`/heartbeat for ≤ 30 s, auto-clear to a dim 1-frame idle glyph (engine crash can orphan the matrix; ExecStopPost cannot reach MCU-side pixels). **Heartbeat cadence: every `show()` doubles as the heartbeat; the engine sends ≥ 1 show per 20 s while serving.** Host-side caps remain defense-in-depth.
3. **Client = calls, never notify** (advisor #7): frames pushed via msgpack-rpc CALLs with msgid + timeout (silent loss impossible); client has a reconnect loop (router restarts orphan sockets, advisor #4). Written from the RPClite protocol after **Phase 1 step 0 verifies Arduino_RPClite's license** (advisor #9) — CC BY-SA tutorial code is never copied (inv.9).
4. **Probe-first client** (advisor #4): Phase 1 probes method discovery/registration semantics (anonymous call vs handshake) with a throwaway script BEFORE the client's final shape.
5. **Upload discipline** (advisor #1/#2): an `upload.sh` takes the SAME flock the engine uses (engine pauses uploads-are-sole-MCU-writer, inv.5b); every upload runs through it; pre-flash state + EDL/BOOTESL recovery notes recorded in Phase 1.
6. **Token path** (advisor #6): token reaches the board argv-free: pre-placed root-only at /var/lib/musegadget/sdk_token (install.sh preserves it when --sdk-token is omitted); secrets gate runs on BOTH repos IMMEDIATELY after Phase 3's install and again pre-flip; SDK tree re-copied only from the verified clean NUC clone.
7. **Webhook modes** (advisor #8): loopback default with the LAN mode as a one-line env flip; BOTH modes tested; the Phase 4 GIF demo documents the LAN flip.
8. **Phase 3 exit = no-token demo gate** (advisor #12): full animation demo + criteria run BEFORE pairing is expected; frame-period measurement (≤ 250 ms enforcement evidence) happens in Phase 1's probe.
9. Snapshot diff around the Phase 3 SDK install (advisor #10) — the ONLY sanctioned system change (inv.2).

## Design Analysis
- **Invariants → mechanism**: inv.1 → token-file flow + gate at two points; inv.2 → snapshot diff + uninstall doc; inv.3 → double upload + recovery notes; inv.4 → engine-only Muse surface (grep + review); inv.5 → sketch clamps + idle timeout + host codec bounds + flock + upload lock; inv.6 → webhook tests (flood/oversize/wrong-key/loopback+LAN); inv.7 → Phase 3 exit demo + contract test; inv.8 → copied harness observed with clone; inv.9 → release checklist gates the flip.
- **Failure & concurrency**: engine crash → MCU idle timeout (≤ 30 s) + host kill-test; router restart → client reconnect; upload vs engine → flock in upload.sh; token install failure → install.sh's own diagnostics + journal, no silent retry; webhook flood → rate cap + payload cap, animation queue bounded (drop-oldest, ≤ 8 pending).
- **State cleanup on every exit path**: engine stop clears matrix (bridge `clear`) + LEDs (hook script) with MCU timeout as backstop; lockfiles kernel-released; upload.sh releases lock in finally.
- **Simplicity guardrails**: stdlib-only Python; copy unoq assets rather than re-porting; no DI; no config files (env + CLI); one .ino, frozen.
- **Blast radius**: board — ~/muse-familiar + user units + MCU sketch + (Phase 3 only) SDK install; repos — muse-familiar additive, muse-gadget-poc untouched except gate runs; upstream clone read-only.
- **Interrogation**: *What could break?* The unproven bridge forwarding (Milestone 1 answers in the first hour); upload bricking Bridge (double-upload + recovery notes; worst case EDL reflash); BLE pairing quirks (user gate + `musegadget pair` reopen). *Riskiest step + earliest check:* Phase 1's probe→ping round-trip — everything else sits on it. *Options not taken:* copying the tutorial client (license), notify-based frames (silent loss), logic-on-MCU (compile cost, fragility), webhook on 0.0.0.0 default (attack surface).
- **Verification design**: oracles — bridge round-trip + measured latency/frame-period; codec round-trip host tests; fake-router-socket client tests (msgpack server in-process); mood machine scripted tests; contract test vs upstream executor; snapshot diffs; kill-test port; secrets gate both repos. Gaps closed: frame-period on-device measurement (Phase 1), LAN-mode webhook test, RPClite license verification. Deferred: pixel-level visual assertion (manual gate + video), pairing completion (user).
- **Default choices**: unix socket path default `/var/run/arduino-router.sock`; msgid timeout 2 s; idle timeout 30 s; rate cap 12 pokes/min; queue 8; grayscale default 7 (sketch clamps display levels via setGrayscaleBits(3)… NOTE: setGrayscaleBits sets display depth — final value chosen in Phase 1 with visual check, bounded ≤ 7 per inv.5).

## Scale Cost Model
N/A — single-board, event-rate workload; bounded by design (payload ≤ 2 KiB, queue 8, rate cap 12/min, one RPC per sequence ≈ ≤ 1 KiB). The only real budget — compile iterations — is engineered away by freezing the sketch (Phases 2–3: zero compiles). Verified operationally by Phase 1 measurements, not a table.

## Phase 1: Milestone — bridge proof (the novel hard core, FIRST)
### Changes
- Step 0: verify Arduino_RPClite license (MPL-2.0 per validator — compatible with our MIT client given attribution; record the exact license + attribution in NOTICE); re-copy SDK tree board-ward (from clean NUC clone, tar-over-ssh).
- Probe script (throwaway, /tmp on board): msgpack-rpc `$/version` call, then anonymous call to a nonexistent device method — observe router error semantics (registration needed?).
- `firmware/FramePlayer/FramePlayer.ino`: Bridge.begin; provide `familiar.ping()`→"pong", `familiar.show(frames, period_ms)` (clamps: period ≥ 250 ms, ≤ 64 frames, values masked to 3 bits; plays on timer; **idle timeout 30 s → dim idle glyph (NOTE: 'self-clear' in the kill-test criterion means this glyph, not a dark matrix — observable wording aligned)**), `familiar.clear()`.
- `upload.sh` (board-side runner): takes engine flock, runs `arduino-cli compile` + network `upload` (password via env → upload properties, never argv in repo scripts), releases lock; records pre-flash state + recovery notes (docs: EDL 05c6:9008 / boot recovery) in `firmware/FLASH_NOTES.md`.
- `familiar/bridge_client.py`: own minimal msgpack-rpc client (calls + msgid + timeout + reconnect), protocol-compatible with RPClite, independently written.
### Success Criteria
- [x] Local (NUC): scaffold tests green (layout, client imports msgpack-free, no token, no socket widening) + gate clean. ✓ `4 passed`; `SECRETS GATE: clean` (commit f150cf5→)
- [x] End-to-end (board): ✓ MPL-2.0 verified; uploaded TWICE (re-upload over running sketch, ~16 s, Bridge alive — ping 5 s later); `familiar.ping` → `pong:28` RTT 19 ms via our client; chunked show renders a 4-frame column-chase (visible; video at release); measurements in BRIDGE_FACTS.md (message cap ~256 B discovered → chunked ≤2-frame protocol — recorded as design fact, not plan deviation: the show API's semantics are unchanged)
- [ ] Manual: test pattern visible on the matrix — pattern RAN (4 frames playing, confirmed by RPC return + timing); visual confirmation folds into the release video (human gate, Phase 4).

## Phase 2: Familiar engine (host-side)
### Changes
- `familiar/` package: `frames.py` (104-B codec + mood animations: idle-blink, happy-hop, sad, alert, sleepy, curious, off — each ≤ 8 frames), `moods.py` (state machine + transitions incl. telemetry-driven sleepiness reusing unoq health), `webhook.py` (stdlib listener on port 8123 — verified free on the board: shared key constant-time, 2 KiB cap, 12/min rate cap, queue ≤ 8 drop-oldest, loopback default + LAN env flip, mapping payload kinds → moods), `cli.py` (`familiar ping|show <mood>|serve|mood`), RGB accents via copied `unog/leds.py`.
- Tests (host): codec bounds (values ≤ 7, 104 length, period clamp), mood transitions, webhook (wrong-key 401, oversize 413, flood → 429 + queue bound, loopback/LAN bind modes), client against an in-process FAKE router socket (msgpack server: ping/show/clear + timeout behavior).
- Deploy via tar-over-ssh; `familiar-engine.service` (user unit) copied from unoq pattern: NTP gate, ExecStopPost = bridge clear + LED reset hook.
### Success Criteria
- [x] Local: full suite green with NO board attached (fake router socket + fake trees) · miss localizes to: engine/client/webhook layer. ✓ `18 passed` (codec bounds, mood machine, fake-router client incl. reconnect/timeout/error, webhook auth/oversize/flood/queue-drop, engine heartbeat+hot)
- [ ] End-to-end (board): `familiar show happy` → animation on matrix; `familiar serve` + `curl -X POST localhost:8123/poke -H "X-Familiar-Key: …" -d '{"kind":"ci_green"}'` → happy animation + event JSONL line; kill-test port green (stop → matrix+LEDs clear; MCU idle timeout backstop demonstrated by killing the engine WITHOUT stop hooks once — matrix falls to the dim idle glyph ≤ 30 s (the MCU idle timeout)).
- [ ] Manual: watch one full mood animation (video for release assets — creature visibly animating confirmed via RPC/timing; eyes-on confirmation folds into the Phase 4 video).

## Phase 3: Muse wiring + the no-token exit gate
### Changes
- SDK install on board with the real token WITHOUT argv exposure: pre-place the token as root at `/var/lib/musegadget/sdk_token` (validator-verified: install.sh preserves a pre-placed token when `--sdk-token` is omitted) — the token transits SSH stdin → root-only file, never argv, never repo; sudo via stdin; system-wide = the one sanctioned change; snapshot diff before/after; uninstall documented.
- `muse_integration/familiar_specs.py` (`familiar.status`, `familiar.show <mood>`, `familiar.feed <kind>`) + COMMANDS.md runbook (allowlist-validated params into engine CLI — carried injection-safe pattern) + contract test copied from the proven harness.
- Narration: mood-transition → `musegadget send-user-msg` sender (edge-trigger port; FileSender default pre-pairing).
- Pairing left OPEN; `sudo musegadget pair` reopen documented; user phone step = manual gate (explicitly theirs).
### Success Criteria
- [ ] Local: contract test green with `MUSE_SDK_LINUX_DIR` (observed); full suite green.
- [ ] End-to-end (board): `systemctl is-active musegadget` (root service); `musegadget info` shows pairing state/open; snapshot diff shows ONLY SDK-attributed changes; **EXIT GATE: full no-token demo** — webhook poke → animation → narration JSONL (FileSender) → `familiar.status` via CLI — all green with pairing incomplete; secrets gate BOTH repos both modes green (token absent everywhere).
- [ ] Manual: user completes phone pairing when ready (outside this plan's automated scope; runbook steps).

## Phase 4: Release + social pack
### Changes
- `README.md` (hero concept, quickstart, safety, troubleshooting, uninstall, GIF/video shot list), `LICENSE` (MIT), `NOTICE.md` (SDK Apache-2.0; RPClite protocol attribution + license; Arduino docs reference; no CC BY-SA content), `SOCIAL.md` (X/Twitter + LinkedIn + Reddit r/arduino + Discord #projects templates — tagging @muse (gadgets.muse.ai) + @arduino — exact Muse handle flagged USER-VERIFY in the pack (unverifiable offline); no invented handles + #ArduinoUNOQ #MuseGadget #AI; media checklist; 30-s demo video script), demo asset capture guide.
- Gates: secrets gate both repos (both modes) → private push `nitishagar/muse-familiar` → **public flip** (`gh repo edit --visibility public`) → post-flip verification.
### Success Criteria
- [ ] Local: `python3 tools/secrets_gate.py` exit 0 (+ runtime-extra mode with token + board password values) on BOTH repos; full suite green; LICENSE/NOTICE/SOCIAL/README present (`test -f` × 4).
- [ ] End-to-end: `gh repo view nitishagar/muse-familiar --json visibility --jq .visibility` → first `PRIVATE` (after push) then `PUBLIC` (after flip); `git log --format='%B' origin/main | grep -ci co-authored` → 0; no `mgst_` in any pushed blob (gate + `git grep` post-flip).
- [ ] Manual: user reviews SOCIAL.md and posts (we never post); user reviews README wording before flip if they wish (flip proceeds per ticket's open-source instruction unless they say otherwise).

## Testing Strategy
Unit (host, no hardware): codec bounds, mood machine, webhook auth/caps/modes, client vs fake router socket (incl. timeout + reconnect), contract test vs upstream executor, repo meta. Integration (board): Phase 1 bridge proofs + measurements; Phase 2 animation/webhook/kill-test; Phase 3 SDK install state + no-token exit demo; Phase 4 gates. IMPLICIT_SPEC coverage: inv.1 (gate ×2 points + post-flip grep), inv.2 (snapshot diff), inv.3 (double upload + notes), inv.4 (grep+review), inv.5 (sketch clamps + idle-timeout demo + tests), inv.6 (webhook tests), inv.7 (Phase 3 exit demo), inv.8 (contract test), inv.9 (checklist + flip criteria). Deferred: visual pixel assertion (manual+video), pairing completion (user).

## Amendments
[Empty at authoring.]

## References
- Research: `thoughts/shared/research/2026-10-04-muse-familiar-matrix.md` (audit-corrected).
- Reused assets: `~/repos/learn/muse-gadget-poc/unoq/` + `tests/` + `tools/secrets_gate.py` (adversarially reviewed hours ago).
- Upstream: SDK clone `~/tmp-research/muse-gadget-sdk`; Arduino_RPClite/RouterBridge GitHub; arduino docs UNO Q tutorials.
- Advisor round: 12 findings folded (frozen sketch, sketch-side clamps+idle timeout, calls-not-notify+reconnect, probe-first, upload lock+double-upload, token-file+gate timing, webhook LAN mode, Phase-3 exit gate, RPClite license step 0, snapshot scheduling, copy-don't-port, frame-period measurement).
