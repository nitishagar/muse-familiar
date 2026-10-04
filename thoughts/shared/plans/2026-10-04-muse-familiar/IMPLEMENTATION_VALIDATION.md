<!-- SIGNPOST | 4/5: IMPLEMENTATION_VALIDATION | adversarial review of the built thing | Prev: PLAN_VALIDATION.md -->
# Implementation Validation — muse-familiar

Reviewer: independent adversarial agent (fresh; did not write this). Scope: whole repo at
HEAD `4803de3` (8 commits), re-derived 2026-10-04 against the live board (read-only ssh +
the sanctioned kill-test run). Every item below was re-executed or re-read this session,
not taken from the implementer's claims.

## Evidence re-derived this session

Host (NUC):
- `uv run --with pytest --with msgpack --with . pytest` → **18 passed, 1 skipped** (exact
  match). With `MUSE_SDK_LINUX_DIR=~/tmp-research/muse-gadget-sdk/linux` → **19 passed**
  (contract test runs). `python3 tools/secrets_gate.py` → **clean, exit 0** (scans index +
  every history blob). `git log --format='%B' | grep -ci co-authored` → 0.
  README/LICENSE/NOTICE/SOCIAL all present. Worktree == HEAD (clean).

Board (`ssh -i ~/.ssh/unoq_poc arduino@192.168.0.134`, read-only + kill-test):
- `familiar-engine` **active**, unit file (installed == repo == deployed copy, md5
  `e629ed45…` all three) passes **`--key-file %h/.config/familiar/key`** — Amendment (b)
  verified in the running config, not just the repo.
- Deployed tree matches repo md5-for-md5: engine.py, bridge_client.py, webhook.py,
  frames.py, upload.sh, kill_test.sh, display_reset.sh, familiar-engine.service.
- **Kill-test re-run by this reviewer**: `bash ~/muse-familiar/units/kill_test.sh` →
  `KILLTEST-OK` (exit 0). Journal shows SIGKILL → `Failed with result 'signal'` (09:25:45)
  → 3 s gap = ExecStopPost `display_reset.sh` (uv spin-up, output deliberately silenced)
  → restart 09:25:48 → active; `familiar.cli ping` → `pong:1981` right after. Stock
  units / /etc/systemd / router socket snapshots diffed clean by the script itself.
- No-token demo evidence on board: `~/.local/state/familiar_events.jsonl`
  (`{"kind":"ci_green","mood":"happy",…}`) + `familiar_narration.jsonl`
  (`"The Familiar is now happy (event: ci_green)."` — exactly the Phase 3 gate text),
  musegadget service active with pairing incomplete. (Journal never shows pokes — the
  engine logs only to JSONL; the JSONL is the observable.)
- Note: a concurrent session (192.168.0.39) was touching repo+board around 09:20–09:22
  (transient uncommitted webhook.py variant, several service restarts); final state
  settled consistent (worktree == HEAD == deployed). Observation only, not a finding.

## Checklist verdicts

- **Plan conformance incl. both Amendments — PASS with one mechanism gap (Important #1).**
  (a) Pairing-closed: install used `--yes --no-pair`, `sudo musegadget pair` reopen
  documented (COMMANDS.md §1, README), amendment recorded in PLAN in the same Phase 3
  commit `2a34824` (same-change rule followed). (b) `--key-file`: implemented in
  engine.main, carried by the unit (verified live), poke+narration accepted on board.
  Phase ticks are honest where it matters (Phase 2 e2e and Phase 4 boxes remain unticked).
- **Spec invariants in code — PASS except inv.5's flock half (Important #1).**
  inv.1: no `mgst_`/token in any file or history blob (gate + grep; the only `mgst_`
  strings are the detection regexes themselves). inv.2: kill-test snapshot diff green
  (re-run). inv.3: FLASH_NOTES + double upload recorded. inv.4: router socket opened only
  by `RouterClient` (grep); Muse specs reach only the engine CLI/webhook (COMMANDS.md
  runbook, allowlisted params, injection-safe kind check). inv.5: sketch clamps verified
  by reading FramePlayer.ino — `setGrayscaleBits(3)`, period clamped ≥ 250 ms in
  `show_begin`, values masked `v>7→7` (underflow-safe: any char < '0' masks to 7),
  ≤ 64 frames, 30 s idle timeout → one-pixel dim glyph, wraparound-safe `millis()`
  arithmetic; host mirrors (validate_frame/period, 104-char codec) tested. inv.6: key
  constant-time (`hmac.compare_digest`), 2 KiB→413, 12/min→429, queue 8 drop-oldest,
  auth-before-ratelimit (401s don't consume budget) — all edge-tested. inv.7: no-token
  demo verified on board (above). inv.8: contract test green; faithful copy of the proven
  poc harness (shape compared line-for-line against test_unog.py:254). inv.9: LICENSE MIT,
  NOTICE (Apache-2.0 + MPL-2.0 + explicit no-CC-BY-SA-copy statement), zero co-author
  trailers; flip honestly not yet done.
- **Failure/concurrency — PASS with nits.** Heartbeat: `HEARTBEAT_S=20` re-push vs the
  sketch's 30 s idle timeout — 10 s margin, loop tick 0.25 s, worst-case show ≈ 4 RPCs
  ≈ 80 ms; every `show()` refreshes the MCU heartbeat (begin/chunk/play each stamp
  `lastHeartbeatMs`). Narrator: failures contained (try/except in the loop; subprocess
  failure falls back to JSONL — observed live pre-pairing). Client: calls-not-notify with
  msgid + timeout, single reconnect per call; an outage longer than that crashes the
  engine into `Restart=on-failure` (10 s) which re-establishes — composite recovery
  works (reconnect path unit-tested). Engine graceful stop clears the bridge; ExecStopPost
  + MCU timeout as backstops — demonstrated by the kill-test.
- **Test integrity — PASS with nits.** 18+1 exactly as promised; bounds asserted at
  edges (103/105/8-char frames, period 100→250, 12→13th request 429, queue 9th/10th
  drop-oldest); fake router is a real msgpack server exercising chunking order and
  reconnect; no test peeks at board state. See Nits #2/#3 for the gaps.
- **Common defects — none beyond the findings.** No argv secrets (unit reads key from
  file; upload password claimed env-based but see Important #2), no socket widening
  (grepped + meta-test), no color escape, stdlib-only with lazy msgpack import.
- **Convention fit — PASS.** Unit/hook/kill-test/gate/harness all follow the poc patterns
  they were told to copy; pyproject dep-free; one frozen .ino.

## Findings

### Important

1. **Single-writer flock discipline (inv.5 / research 5b / plan approach #5) is not
   implemented — the engine takes no lock.** `firmware/upload.sh:10-14` flocks
   `~/.local/state/familiar.lock` and comments "Takes the same flock the engine uses
   (engine pauses while we own the MCU)", but nothing in `familiar/engine.py` (or the
   unit) ever opens or flocks that file — the lock excludes nobody. The spec's
   observable "engine pause hook" does not exist, and README/COMMANDS.md invite
   reflashing "any time" with the service running. Latent, not currently harmful (an
   upload under a live engine fails the engine's RPCs → crash → systemd restart →
   recover; sketch clamps bound the damage), but a shipped invariant is unenforced and
   the script's comment is false. Fix: acquire the same flock (non-blocking, or
   pause-and-release) in `Engine.run`, or amend the plan/spec to the weaker discipline
   actually implemented.
2. **`upload.sh` does not carry the upload-auth path it documents and that was actually
   proven.** Its header claims "never puts the board password in argv (read from
   $UNOQ_UPLOAD_PASSWORD env or prompts)" — the script never reads that variable, never
   prompts, and passes no `--upload-field`/`--upload-property`; `BRIDGE_FACTS.md`
   records the working flow as `--upload-field password=<board-pass>`. The Phase 1
   uploads were evidently run with the flag by hand, so "every upload runs through it"
   (plan) is not true of the committed script, and the public README quickstart step 1
   (`cd firmware && ./upload.sh`) is not the proven command path. Fix: wire
   `$UNOQ_UPLOAD_PASSWORD` → `--upload-field password=…` (env only) or amend the docs.

### Nits (5, counted)

1. README quickstart says `FAMILIAR_LAN=1 ./serve` — no `FAMILIAR_LAN` env and no
   `./serve` exist; the real LAN flip is the `--lan` flag (CLI/unit). Release-artifact
   doc error.
2. Phase 2 Changes promise loopback/LAN bind-mode tests; only loopback is ever
   exercised (`serve(..., lan=True)` appears in no test).
3. Ported kill_test.sh drops the poc's physical oracle (poc asserted LED brightness 0
   after the kill; the port could read the `unoq:user-*` brightness files display_reset
   zeroes, and instead just asserts "display reset ran" in prose). Also the /etc/systemd
   snapshot is a file LIST, not content hashes (weakness inherited from the poc), and
   BRIDGE_FACTS' "idle timeout … demonstrated" defers the actual observation to the
   release video while Phase 2's e2e box stays unticked — honest, but "demonstrated"
   overstates it.
4. Dead code and leftovers: `frames._offset_rows` never called;
   `test_engine.py`'s `dict(...)[1] if False else …` and the no-op `c._sock = c._sock`;
   webhook's key-required error still says "(FAMILIAR_KEY)" though the deployed flow is
   `--key-file`.
5. `Narrator.send` runs synchronously in the single-threaded loop with a 100 s subprocess
   timeout — a hung musegadget CLI dims the creature to the idle glyph (heartbeat missed
   at 30 s) until it returns; contained and self-healing, but the code comment promises
   narration can never affect the creature and it can stall it.

## What the implementation got right (verified, not assumed)

The unproven hard core was genuinely proven first (bridge RTT, chunk-cap discovery,
double upload, FLASH_NOTES); the sketch enforces every MCU-side bound exactly as
amended (clamps + mask + idle glyph + re-arm); the token is verifiably absent from every
file and every history blob; the webhook's five hardening properties are each tested at
their edge; the engine's heartbeat cadence (20 s) correctly precedes the sketch timeout
(30 s) with every RPC stamping the MCU heartbeat; narration degrades safely pre-pairing
(observed on board); the kill-test passes re-run by a hostile reviewer with the bridge
answering ping afterward; both plan amendments are real, minimal, recorded in the same
change, and Amendment (b)'s fix is live in the installed unit and accepting pokes.

Two Important findings, both contained to upload-path discipline/artifacts — no running
system, secrecy, or safety invariant is broken. Fix both (or amend the plan) before the
public flip.

VERDICT: MINOR-FAIL

---

# Round 2 — re-verification after the fix commit (same reviewer, fresh pass)

Reviewed HEAD `0825d89` ("Review fixes: flock discipline, upload.sh password wiring, …").
Note for the trail: history was rewritten after the handoff — the cited `a666ee6` no longer
exists; `4803de3`→`54c0c51`, `7cda232`→`c9347f7`, fix commit → `0825d89`. This reviewer's
Round-1 file was committed unmodified (verified byte-for-byte against what was written).
A concurrent session was also cycling the board service during verification (journal
09:31–09:37) — final state settled; deployed tree now matches repo HEAD md5-for-md5
(engine.py `d128320…`, upload.sh `4a8d4a6…`, webhook.py `f6fbe30…`, kill_test.sh `cef2c0…`).

## Round-1 Important findings — both FIXED (verified)

1. **Flock discipline — FIXED and live-verified.** `engine.py` now holds `LOCK_SH` on
   `~/.local/state/familiar.lock` (same `FAMILIAR_LOCK` env as upload.sh) for the whole
   `run()` lifetime, released in `finally` (kernel-released on SIGKILL); `upload.sh` takes
   `flock -w 30 -x` with a stop-the-engine hint; the false comment is gone. On the board,
   with the engine active, a non-blocking EXCLUSIVE probe fails (rc=1) — the shared lock is
   genuinely held; mutual exclusion is real. (CLI one-shots `show`/`clear` remain lockless —
   interactive tools, acceptable.)
2. **Upload password — FIXED.** `upload.sh` fails fast without `UNOQ_UPLOAD_PASSWORD`,
   wires it via `--upload-field "password=…"`; README uses `read -rs … && export` (never in
   shell history) and adds `chmod 600` on the key file. Matches the BRIDGE_FACTS-recorded
   flow.

## Round-2 findings

### Important

1. **The fix commit regressed upload.sh's port auto-detection — the shipped quickstart
   path is broken.** The sed replacement in the port-detection line now contains a literal
   `0x01` control byte where the `\1` backreference must be (pre-fix blob `ce17378…` has
   correct `\1`; HEAD/deployed blob `d9b24c2…` has `\x01`). Verified against the real
   board: the exact pipeline from the deployed script, fed live
   `arduino-cli board list --format json`, emits `\x01\n\x01` — so `PORT` becomes a single
   control byte, passes the `[ -n "$PORT" ]` guard, and `arduino-cli upload -p "\x01"`
   cannot succeed. The handoff's "verified live: upload.sh flashed the corrected sketch"
   cannot have exercised this path (it must have used `FAMILIAR_UPLOAD_PASSWORD`'s sibling
   `FAMILIAR_UPLOAD_PORT`, or a manual upload). README step 1 still fails for a fresh
   user. One-byte fix; add a guard (fail if the detected port does not look like a host
   name/IP) so it can't silently regress again.
2. **SOCIAL.md was deleted from the repo without amending the plan.** The commit message
   cites "astroturf-optics" — a defensible product call — but PLAN.md Phase 4 still
   requires the SOCIAL pack in three places (Desired End State line 14, Changes line 82,
   Local criterion "`test -f` × 4" line 85, plus the Manual gate line 87), and the fix
   commit touches no plan text. That is exactly the divergence-without-amendment the
   plan's own header forbids, and the public repo would ship the contradiction (plan trail
   is tracked in-tree). Fix: amend PLAN Phase 4 in the same change that removes the
   artifact (documenting where the pack now lives), or restore the file.

### Nits (claimed-vs-actual + residues)

- The handoff claims "kill-test now also reads LED brightness" — **not true**:
  `units/kill_test.sh` is byte-identical (md5 `cef2c0…`) in the repo and on the board, no
  LED/brightness read anywhere. (The nit itself was optional; the false fix claim is the
  issue.)
- Residues left in place (acceptable): webhook's key-required error still says
  "(FAMILIAR_KEY)" though the deployed flow is `--key-file`; `frames._offset_rows` remains
  dead code.

## What round 2 also verified as sound (beyond the two Importants)

Suite: 23 passed + 1 skipped; with `MUSE_SDK_LINUX_DIR` → 24 passed; secrets gate clean in
both plain and `SECRETS_GATE_EXTRA` modes. The extra hardening in the fix commit holds up:
webhook rate-limits before auth (failed auth no longer a free channel), Content-Length is
int-parsed with negative/garbage handled, key comparison is byte-wise (non-ASCII safe),
handler never leaks a traceback — all covered by the new tests; the sketch gained a
negative-period guard and was genuinely reflashed (ping uptime consistent with the ~09:33
flash; `pong:335` during this review); the contract test now scans the whole upstream
COMMAND_SPECS contract; new mutation pins (heartbeat < 30 s idle timeout, CHUNK_FRAMES ≤ 2,
inv.4 scoped router-socket grep with the kill_test read-only whitelist) pin the exact
bounds round 1 checked by hand; bind-mode tests close round-1 nit #2; test junk (nit #4)
removed; EVENTS_FILE monkeypatched for isolation. Engine live, serving, and holding the
shared lock while a hostile probe confirms exclusion.

Both round-1 Importants are verifiably closed, but the fix commit introduced one new
user-facing regression (upload.sh port detection) and one unamended plan divergence
(SOCIAL.md removal), plus one fix claim that is not in the tree (kill-test LED oracle).

VERDICT: MINOR-FAIL
