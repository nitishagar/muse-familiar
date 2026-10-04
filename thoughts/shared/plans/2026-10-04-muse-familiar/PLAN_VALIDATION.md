<!-- SIGNPOST | 3/5: PLAN_VALIDATION | adversarial re-derivation | Prev: PLAN.md | Next: implement+review
     Pipeline: SPEC -> PLAN -> PLAN_VALIDATION -> implement+review -> tests+TEST_VALIDATION -> green -->

# Plan Validation — muse-familiar (scale=medium)

Reviewer: independent adversarial agent (did not author the plan). Every item defaulted FAIL until
evidence earned PASS. Evidence re-derived 2026-10-04 against: the live board (read-only ssh), the
muse-gadget-poc repo, the SDK clone, the installed Arduino_RPClite library, and local gh/uv CLIs.

## Evidence gathered (all commands run this session)

Board (`ssh -i ~/.ssh/unoq_poc arduino@192.168.0.134`, read-only):
- `arduino-cli` 1.5.1; `board list` shows two network ports, FQBN `arduino:zephyr:unoq` — matches Current State.
- `arduino-cli lib list`: Arduino_RouterBridge 0.4.3, Arduino_RPClite 0.3.0, MsgPack 0.4.2, ArduinoGraphics 1.1.5 — installed, as claimed.
- `/var/run/arduino-router.sock`: mode 666, root:root — matches "world-rw, root-owned, never re-permission".
- Disk 2.3 GB free; `~/.arduino15` = 652 MB; `uv` at `~/.local/bin` — matches research numbers exactly.
- SDK ABSENT: no `/opt/musegadget`, no muse units in `/etc/systemd/system` — "SDK tree absent, re-copy is step 0" is correct.
- `~/muse-unoq/` deployed (unoq/, units/, tools/, muse_integration/) — deployed-unog reuse boundary is real.
- Router journal shows `$/version`, `$/serial/open`, `$/serial/close` — the Phase 1 probe's first call targets a real method.
- `ss -tln` shows nothing on 8123 — webhook port free.
- `arduino-cli upload --help` shows `--upload-property stringArray` — "password via env → upload properties" is a real flag; exact property key defensibly deferred to the Phase 1 probe.

Prior repo `/home/nitish/repos/learn/muse-gadget-poc` — every claimed reusable asset EXISTS:
- `unoq/unog/{leds,health,notifier,cli}.py`; `fcntl.flock` single-writer pattern present in `unog/leds.py:90` ("the existing flock" is a copyable real thing, not aspiration).
- `unoq/units/unog-notify.service`: ExecStartPre `ntp_gate.sh` + ExecStopPost `led_reset.sh` — exactly the unit pattern Phase 2 says it copies.
- `unoq/tools/kill_test.sh`: snapshots unit files, /etc/systemd, router socket mode/owner — the inv.2 observable mechanism already exists.
- `tools/secrets_gate.py`: runtime-extra mode via `SECRETS_GATE_EXTRA` ("both modes" is real).
- `tests/test_unog.py:254` / `test_pico_bridge.py:215`: contract test gated on `MUSE_SDK_LINUX_DIR` — Phase 3's copied harness is real.

SDK clone `~/tmp-research/muse-gadget-sdk`:
- Top-level LICENSE = Apache-2.0 — NOTICE attribution basis correct.
- `linux/install.sh` read in full (see finding analysis below). CLI subcommands `pair`, `send-user-msg`, `info`, `unpair` all exist; unit lands at `/etc/systemd/system/musegadget.service` (root service) — `systemctl is-active musegadget` is the right check. `--uninstall` exists (README uninstall doc can cite a real path).

Other:
- `gh` 2.46.0 (this host): `gh repo edit --help` lists `--visibility string` with NO confirmation flag — `gh repo edit --visibility public` is real as cited in this environment (note: some newer gh releases require `--accept-visibility-change-consequences`; if the host CLI is upgraded before Phase 4, add the flag — not a plan defect today).
- NUC `~/.local/bin/uv` 0.12.10 present — Phase 1 Local command runnable as cited.
- Arduino_RPClite installed LICENSE (on board) = **MPL-2.0** (see N4).
- muse-familiar repo currently contains only `thoughts/` — plan-only, consistent with the pipeline stage.
- Web search unavailable this session (tool error) — social handles could not be independently verified (see N3).

## Checklist verdicts

(1) Every spec invariant has a named mechanism — **PASS**. inv.1 token-file flow + gate at two points (mechanism verified implementable, below); inv.2 snapshot diff (pattern exists in kill_test.sh) + uninstall (install.sh `--uninstall` real); inv.3 double upload + FLASH_NOTES; inv.4 engine-only surface + grep; inv.5 sketch clamps + RPC-silence idle timeout + host bounds + flock (pattern verified in unog/leds.py) + upload lock; inv.6 webhook tests incl. flood/oversize/wrong-key + both bind modes; inv.7 Phase 3 exit demo; inv.8 contract test (harness + env var verified); inv.9 release checklist gates the flip. inv.10 bounding assumptions restated.

(2) Failure/concurrency real — **PASS** (with N1 wording gap).
- MCU idle timeout: stated as RPC-silence-based ("no show/heartbeat for ≤ 30 s → dim idle glyph"). Semantics are sound: max sequence is 8 × 250 ms = 2 s, so no legitimate animation is cut; looping moods require host re-push < 30 s, which is the heartbeat. Kill-test criterion (SIGKILL engine without stop hooks → matrix safe ≤ 30 s) actually exercises the orphaned-matrix case. Real, not hand-waved.
- flock across upload.sh + engine: the "existing flock" is a verified pattern in the poc (`unog/leds.py`), and upload.sh taking the same lock is specified with release-in-finally.
- Client reconnect: specified (approach #3) with a fake-socket timeout/reconnect test in Phase 2.
- **Token file flow, read precisely**: `install.sh` documents `--sdk-token TOKEN` as its ONLY token input — argv. HOWEVER, a genuine file-based path exists in the source: pre-place the token at `/var/lib/musegadget/sdk_token` (0600, root) and run install.sh WITHOUT the flag — `save_sdk_token()` (install.sh:255-265) preserves an existing non-empty state file, and the service reads the token from exactly that path (`config.py`: DEFAULT_STATE_DIR=/var/lib/musegadget, SDK_TOKEN_FILE=sdk_token, `sdk_token()` reader; consumed by cli/run_service/pairing). So the plan's "token via root-only file → install.sh (not argv where feasible)" is implementable exactly as worded, argv-free, and the hedge is honest. The one gap: the plan never states the pre-place-the-file-and-omit-the-flag trick, so a stranger working from the usage text alone would default to argv (permitted by the hedge; brief argv exposure on a single-user board, and argv would also land in shell history — the file route avoids both). → N1.

(3) Callers/consumers enumerated — **PASS**. webhook → engine; CLI → engine; Muse specs → engine CLI (allowlist params); mood transitions → `musegadget send-user-msg` (subcommand verified); engine → bridge client → router; upload.sh → flock + arduino-cli. All named.

(4) No correctness-for-simpler trades — **PASS**. Calls-not-notify was chosen FOR correctness (msgid+timeout); frozen sketch removes compile cost without removing safety (sketch-side clamps + idle timeout add redundancy, not risk).

(5) No new patterns where unoq copies fit — **PASS**. Unit, gate, harness, kill-test, hook scripts, flock: all copied from verified assets. Only genuinely new code (bridge client, webhook, codec) is new.

(6) No TBDs / no designs in spec — **PASS**. Spec is requirement-level; observables are checks, not mechanisms.

(7) DENSE criteria — **MINOR-FAIL on one item** (Important #1 below); otherwise PASS. Every phase has Local (command + localization) AND e2e AND manual. Cited commands verified real: uv-on-NUC, curl/X-Familiar-Key shape, `systemctl is-active musegadget` (root unit confirmed), `musegadget info`, `gh repo view --json visibility`, co-author grep, `--upload-property` (flag shape exists; exact key safely deferred to Phase 1's probe — that is Phase 1's job). `gh repo edit --visibility public` needs NO confirmation flag on this host's gh 2.46.0. Gaps (frame-period measurement, LAN-mode test, license verification) are all closed inside phases; deferrals (pixel assertion, pairing) carry reasons. The one defect: Phase 1's Local criterion is not satisfiable from Phase 1's changes (Important #1).

(8) Anti-pattern sweep — **PASS** beyond #1. No test-later, no vague gates, measurements scheduled at the earliest possible point (Phase 1), riskiest step first.

(9) Decomposition / Milestone-1-first — **PASS**. The single novel hard core (bridge forwarding, explicitly UNPROVEN in research) is Phase 1 and nothing is built on it before it is proven; upload discipline is part of that same core, not a second hard problem.

(10) N/A.

(11) Intent open questions closed — **PASS**. Q1→Milestone 1, Q2→inv.3, Q3→inv.7 + Phase 3 criteria, Q4→inv.9 + Phase 4; all ticked in the spec tail.

(12) Stranger-implementable — **MINOR-FAIL** on one item (Important #1) plus N1/N2 friction. Everything else an engineer could execute from the bundle: assets exist at named paths, board facts check out, commands run as cited.

(13) Scale Cost Model N/A — **ACCEPTABLE**. Single board, event-rate workload, hard bounds everywhere (2 KiB payload, queue 8, 12/min, one RPC per sequence); the only real cost — MCU compile iterations (~25-80 s each, disk 652 MB/2.3 GB verified) — is engineered away by freezing the sketch after Phase 1, and Phase 1's measurement criteria substitute for a table.

## Reviewer questions (a)-(d)

(a) **Phase 1 codec criterion**: Confirmed defect — see Important #1. Phase 1 Changes list the probe script, FramePlayer.ino, upload.sh, bridge_client.py; the codec (frames.py, 104-B) is a Phase 2 Changes item. The Phase 1 Local criterion ("codec unit tests for frame packing bounds — fake objects only") tests an artifact the phase never builds. Not satisfiable as written.

(b) **Webhook port 8123**: Specified only implicitly — it appears solely in the Phase 2 e2e curl (`localhost:8123/poke`); neither webhook.py's Changes spec nor Default choices states the port. Derivable, and the port is verified free on the board. → N2.

(c) **SOCIAL.md handles**: `@muse`/`@arduino` are corroborated by the research matrix; `@ArduinoMuse` appears only in the plan and could not be verified this session (web search unavailable). The plan hedges with "per their handles" and Phase 4's manual gate is explicit user review of SOCIAL.md before posting — the residual risk is properly parked with the user, but the bundle itself does not substantiate @ArduinoMuse. → N3.

(d) **LAN-mode bind coherence**: Coherent. Loopback default (inv.6), LAN as one-line env flip (approach #7), BOTH bind modes tested (Phase 2 tests), GIF demo documents the LAN flip (approach #7; Phase 4's demo capture guide/README is where it lands). Minor: the "document the LAN flip in the demo guide" obligation is not restated as a Phase 4 Changes bullet — folded into N5, not a coherence break.

## Findings

### Important
1. **Phase 1 Local criterion is unsatisfiable as written.** The criterion requires "codec unit tests for frame packing bounds — fake objects only", but the codec module (`frames.py`, the 104-B layout) is introduced in Phase 2's Changes; Phase 1 builds probe script, FramePlayer.ino, upload.sh, bridge_client.py — no codec. A stranger must either invent an undeclared codec artifact in Phase 1 or skip the criterion; either path diverges from the plan-as-single-source-of-truth. Fix is one line: move a minimal `frames.py` codec (packing/bounds only) into Phase 1 Changes (the sketch's `show` payload format IS a Phase 1 artifact — the codec tests would then genuinely localize scaffold risk), or rescope Phase 1 Local to bridge_client unit tests (frame assembly vs fake socket) and keep codec tests in Phase 2. Until amended, Phase 1's Local gate cannot honestly be ticked.

### Nits (5, counted)
- **N1 (token mechanics unstated)**: the file-based route works only via the pre-place trick — write `/var/lib/musegadget/sdk_token` (0600 root) BEFORE running install.sh, omit `--sdk-token` (source-verified: `save_sdk_token()` preserves an existing file; the service reads it from there). The plan says "token via root-only file → install.sh" without the trick; a stranger reading install.sh's usage alone would use argv (which the hedge permits, honestly, noting brief argv exposure on a single-user board — argv also risks shell-history capture, which the file route avoids). One sentence in Phase 3 would pin it.
- **N2 (webhook port)**: 8123 appears only in the Phase 2 e2e criterion, not in webhook.py's spec or Default choices. Verified free on the board.
- **N3 (handles)**: `@ArduinoMuse` uncorroborated by the research matrix and unverifiable this session; user-review gate covers it, but SOCIAL.md should cite or re-derive handles at write time.
- **N4 (criterion wording ×2)**: (i) Phase 2 kill-test says "matrix self-clears ≤ 30 s" while approach #2 defines the timeout outcome as a DIM LIT idle glyph, not darkness — a strict tester seeing lit pixels could fail the criterion; align the expected observable. (ii) Phase 1 e2e "RPClite license permissive" — the actual license is MPL-2.0 (weak, file-level copyleft; not classically "permissive"). Immaterial to the plan (the client is independently written from the protocol, so no MPL obligations attach), but the predicate is fuzzy — "license verified and recorded in NOTICE; client copies no RPClite code" would be decidable.
- **N5 (minor unstated semantics)**: `familiar.show` loop-vs-play-once semantics and the engine's re-push/heartbeat cadence for looping moods (idle-blink) are unspecified. Bounded risk: max sequence 2 s, and the Phase 2 kill-test forces the implementer to get the heartbeat right or the criterion fails. Also: the Phase 4 "document the LAN flip" obligation lives only in Approach #7, not in Phase 4's Changes bullets.

## What the plan got right (verified, not assumed)
Every load-bearing factual claim survived independent re-derivation: board libraries/versions, network ports, socket mode/owner, disk/toolchain numbers, SDK absence, deployed unog, the existence and shape of every "reusable" poc asset (including the exact NTP-gate/ExecStopPost unit, flock pattern, snapshot-diff kill-test, MUSE_SDK_LINUX_DIR harness, SECRETS_GATE_EXTRA mode), SDK Apache-2.0, musegadget subcommands, `--upload-property`, router `$/version`, free port 8123, and `gh repo edit --visibility` needing no confirmation flag on this host. The token-file mechanism — the item most likely to be aspirational — is genuinely implementable argv-free in install.sh as shipped.

VERDICT: MINOR-FAIL

---

# Round 2 — re-validation after round-1 fixes (same session)

Re-read the amended PLAN.md in full; verified each claimed fix against the document text itself,
not the transmittal.

## Fix verification

- **Important #1 — FIXED (verified, line 55).** Phase 1 Local criterion is now scaffold-only
  (package layout present, bridge_client importable, secrets gate clean), explicitly defers codec
  tests to Phase 2 with frames.py. Every named artifact is a Phase-1 Changes item; the criterion is
  now satisfiable as written, and Phase 2's tests list carries the codec bounds tests as promised.
  This was the sole Important finding; it is closed.
- **N1 — FIXED (line 71), one stale echo.** Phase 3 now states the exact validator-verified
  mechanism: pre-place root-only `/var/lib/musegadget/sdk_token`, omit `--sdk-token` (install.sh
  preserves it), token transits SSH stdin → root file, never argv/repo. Matches the source-level
  verification of round 1. Residual: Approach #6 (line 29) still carries the old hedge "not argv
  where feasible; single-user board noted" — now under-claiming against Phase 3's definitive
  "WITHOUT argv exposure". Harmless drift, one-line cleanup.
- **N2 — FIXED (line 61).** Port 8123 stated in webhook.py's Changes spec with the verified-free note.
- **N3 — FIXED (line 82).** @ArduinoMuse removed ("no invented handles"); exact Muse handle flagged
  USER-VERIFY; @arduino + hashtags asserted; @muse retained with gadgets.muse.ai corroboration from
  the research matrix. Properly parked with the Phase 4 user-review gate.
- **N4 — PARTIALLY FIXED (lines 49, 51 vs 56, 66).** Changes now state MPL-2.0 with attribution
  (correct, matches the on-board LICENSE), and the Phase 1 NOTE defines "self-clear" = the dim idle
  glyph (not a dark matrix), which binds the Phase 2 kill-test wording by reference. Residuals: the
  Phase 1 e2e criterion (line 56) still says license "permissive" — the fuzzy predicate the Changes
  line just replaced; and the Phase 2 criterion text still reads "self-clears" rather than naming the
  glyph. Both coherent via the cross-reference, but the criterion texts were not themselves updated.
- **N5 — CLAIMED BUT ABSENT.** The transmittal states heartbeat semantics were added ("every
  show() is the heartbeat; engine cadence ≥ 1 show per 20 s while serving"); a full-text grep of the
  amended PLAN.md finds no such statement anywhere (only the unchanged round-1 line 25 MCU-side
  timeout; Amendments section still empty). The fix was not applied to the document. Risk remains
  bounded exactly as argued in round 1 (max sequence 2 s; the Phase 2 kill-test criterion fails if
  the engine's re-push cadence is wrong, forcing the discovery), so this stays a nit — but the
  implementer should add the one-liner to Approach #2 or Phase 2 Changes, and the transmittal
  misreported the document.

## Re-derivation delta

No other text changed in ways that alter round-1 conclusions: Current State, invariants→mechanism
mapping, decomposition (Milestone-1-first), Scale N/A justification, cited commands, and the
reused-asset claims are all unchanged and remain verified. No new defects introduced by the edits.

## Round-2 findings (all nit-level; none block)

1. N5 fix missing from the document despite being claimed — add the engine heartbeat cadence
   (≥ 1 show per 20 s while serving; every show() is the heartbeat) to Approach #2 or Phase 2 Changes.
2. Approach #6 stale hedge vs Phase 3's definitive argv-free mechanism.
3. Phase 1 e2e criterion still says "permissive" where Changes now (correctly) pin MPL-2.0 + attribution.
4. Phase 2 kill-test criterion still reads "self-clears" — resolved only by the Phase 1 NOTE gloss;
   editing the criterion itself would remove the indirection.

The single Important finding of round 1 is verifiably closed; remaining items are cosmetic or a
one-line nit whose absence the success criteria already force at implement time.

VERDICT: PASS
