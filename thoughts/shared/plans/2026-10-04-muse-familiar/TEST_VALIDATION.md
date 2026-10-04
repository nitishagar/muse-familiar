<!-- SIGNPOST | 4/5: TEST_VALIDATION | adversarial review of the tests themselves | Prev: PLAN_VALIDATION.md -->
# Test Validation — muse-familiar (adversarial, fresh reviewer)

Reviewer did not write these tests. Board untouched (read-only constraint honored;
all findings host-side). Baselines reproduced exactly as briefed:
`uv run --with pytest --with msgpack --with . pytest` → **18 passed, 1 skipped**;
bare (no `--with msgpack`) → **4 passed, 2 skipped** (module-level importorskip);
with `MUSE_SDK_LINUX_DIR=~/tmp-research/muse-gadget-sdk/linux` → **19 passed**.
Working tree left clean; no commits made.

## 1. Invariant coverage (IMPLICIT_SPEC 1–9)

| Inv | Automated evidence | Executed evidence | Verdict |
|-----|--------------------|-------------------|---------|
| 1 token secrecy | `test_no_token_anywhere` (git grep `mgst_…`; tracked files only) | Phase 1/3 ticks: gate clean both repos; Phase 4 gate runs pending (phase honestly unchecked) | covered |
| 2 board safety scoped | — (not host-testable) | Phase 3 snapshot diff tick; `units/kill_test.sh` asserts system units, /etc/systemd, router socket unchanged; commit 48562ab "kill-tested" | covered (executed) |
| 3 MCU flash safety | — | double upload + ping-after-reflash recorded in `firmware/BRIDGE_FACTS.md`; recovery notes in FLASH_NOTES.md | covered (executed) |
| 4 no raw router passthrough | **NONE** — `test_no_router_socket_widening…` greps only `familiar/` + `firmware/upload.sh`, and only for chmod/chown; `muse_integration/` is scanned by no test | plan says "grep + review"; **no recorded artifact of that grep anywhere**. Re-performed in this review: `familiar_specs.py` is pure spec data; COMMANDS.md executor branches route only through the engine CLI and `curl localhost:8123` — no router RPC reaches Muse. Passes today, but the invariant has no durable check. | **gap — named** |
| 5 effects bounded / crash-safe | codec bounds (values ≤ 7, len 104, ≤ 8 frames, period clamp host+`begin` args), clear-on-stop, heartbeat-existence | sketch clamps + 30 s idle-timeout demo (BRIDGE_FACTS: "demonstrated"); kill-test | mostly covered — heartbeat *cadence* bound unpinned (see Important 3) |
| 6 webhook hardened | wrong-key 401, missing key 401, oversize 413, bad JSON 400, exact flood boundary, drop-oldest, health | Phase 3 exit gate (poke → 200 → happy) | mostly covered — **loopback-default bind unpinned** (see Important 1) |
| 7 no-token demo | — | Phase 3 EXIT GATE tick: full poke→animation→JSONL→narration chain with `paired: no` | covered (executed) |
| 8 spec-contract fidelity | `test_contract.py` vs real upstream executor (verified green with clone) | same | covered (shape-fidelity only — nit 5) |
| 9 release hygiene | — | Phase 4 unchecked — artifacts exist (LICENSE/NOTICE/README/SOCIAL), gates/flip not yet run; honestly open | pending phase, not a gap |

**Named per instruction: invariant 4 is the only one with neither an automated
check nor a recorded executed check.** Invariants 1–3, 5–8 have real evidence;
9 is Phase 4 work still open (unchecked boxes are truthful).

## 2. Criteria coverage (PLAN ticks vs what the outputs prove)

- Phase 1 local "4 passed; SECRETS GATE: clean" — reproduces (the 4 meta tests
  predate the engine suite). Phase 1 e2e tick's specifics (pong RTT 19 ms,
  re-upload, ~256 B cap) are board facts recorded in BRIDGE_FACTS.md; the
  **cap is the justification for chunking — yet no test pins the chunk size** (Important 2).
- Phase 2 local tick quotes "18 passed (codec bounds, mood machine, fake-router
  client incl. reconnect/timeout/error, webhook auth/oversize/flood/queue-drop,
  engine heartbeat+hot)" — every listed item is genuinely asserted, **but the
  Phase 2 Changes line also promised "loopback/LAN bind modes" tests and the
  tick's quoted list silently omits them because they do not exist**
  (Important 1). Mutation-confirmed: `bind = "0.0.0.0"` unconditionally →
  suite still 14/14 green.
- Phase 2 e2e + Manual boxes remain unchecked while Phase 3's are checked; the
  overlapping evidence (kill-test, poke demo, idle-timeout demo) exists in
  BRIDGE_FACTS/commits — bookkeeping inconsistency, not missing work.
- Phase 3 ticks check out (contract test verified with the clone; exit-gate
  chain quoted matches the code paths tested host-side).
- Phase 4 honestly unchecked.

## 3. Assertion strength (targeted questions)

- **FakeRouter vs one-call frames**: for the 2-frame `happy` show the test
  asserts exact method-sequence equality `["familiar.ping", "familiar.show.begin",
  "familiar.show.chunk", "familiar.show.play"]` — a client collapsing to a single
  `familiar.show` call IS caught. But a client sending **all frames in one fat
  `chunk`** is not: mutation `CHUNK_FRAMES = 4` survives (the 4-frame `curious`
  case asserts only `begin`'s `[4, 250]`, never the chunk count/payload size).
- **Heartbeat vs idle**: the test does disambiguate — a show fires at t+100 with
  no event and no mood change (pure heartbeat), and the hot-board show fires
  with the heartbeat suppressed via `_last_show`. But the **cadence bound is
  unpinned**: `HEARTBEAT_S = 45` passes, which on the real board lets the 30 s
  sketch idle-timeout orphan the matrix between heartbeats — the exact failure
  the heartbeat exists to prevent.
- **Flood boundary**: exact — `codes[:12] == [200]*12` and `codes[12] ==
  codes[13] == 429`. Mutation `RATE_LIMIT_PER_MIN = 13` is killed. Correct
  12-ok/13th-rejected edge.

## 4. Mutation testing (15 mutants: apply → focused run → revert)

Killed (10): rate limit 12→13; MAX_BODY 2048→4096; drop-oldest→drop-newest;
host period clamp removed; MIN_PERIOD_MS 250→200; `run()` clear removed;
heartbeat condition removed; reconnect retry removed; SLEEPY_TEMP 78→200;
`begin` total lie.
**Survived (5):**

1. `CHUNK_FRAMES = 2 → 4` — **Important** (protocol bound from the measured
   ~256 B router cap; test file's own docstring claims "every bound is asserted
   at its edge" — this one is not).
2. `HEARTBEAT_S = 20 → 45` — **Important** (breaks the < 30 s MCU-timeout
   margin; nothing fails).
3. loopback-default → always-LAN bind — **Important** (inv.6 "loopback bind by
   default"; PLAN-promised test missing; suite green on a security regression).
4. mood `tick()` `>=` → `>` — Nit-level boundary nuance (expiry still tested at
   5.9/6.1 around the 6.0 edge).
5. `hmac.compare_digest` → `==` — inherent: constant-time-ness is not
   assertable host-side; accepted limit, auth *behavior* is tested.

## 5. Over-mocking / determinism / threading

- FakeRouter threads: `calls.append` happens before the response is sent, and
  the client's call returns only after the response → readback is
  well-ordered; accept-loop + per-conn daemon threads shut down cleanly.
- Webhook: ThreadingHTTPServer + sequential urllib posts; the handler enqueues
  before replying → queue/rate assertions deterministic (no sleeps, no races).
  14-post flood and 10-post drop-oldest runs were stable across repeats.
- Engine test: clock, temp, and events are injected fakes — deterministic;
  layering is right (engine→FakeClient, client→FakeRouter; the real
  RouterClient IS exercised against a msgpack server, not mocked away).
- One real isolation defect: the engine test constructs `Engine(...)` without
  a narrator and without redirecting `EVENTS_FILE`, so every run **appends to
  the host's real `~/.local/state/familiar_events.jsonl` and
  `familiar_narration.jsonl`** (verified: created by this review's runs).
- `test_client_error_and_timeout` uses real 1.5 s delay vs 0.3 s timeout (5×
  margin — fine) but `pytest.raises(Exception)` is loose (see nit 3).

## 6. Test integrity / skips

- History: only post-Phase-2 change to tests is adding the module-level
  importorskip (48562ab → 4803de3) — **no assertion was weakened**; nothing
  skips conditionally-on-failure; no `xfail`/try-except-swallow in assertions.
- Skip 1: `test_engine.py` without msgpack → module-level
  `pytest.importorskip("msgpack")` — RIGHT reason (15 tests genuinely need the
  msgpack server/client); corroborated by
  `test_bridge_client_imports_without_msgpack` passing in that same env.
- Skip 2: `test_contract.py` without `MUSE_SDK_LINUX_DIR` — RIGHT reason
  (upstream clone unavailable); with the env var set it runs and passes (19/19).
  Nit-grade: skips on env-var *presence*, so a bogus path errors rather than skips.

## Findings

**Important**
1. No loopback/LAN bind-mode test (PLAN Phase 2 promised it; mutation survivor;
   inv.6 default-bind property unpinned). Fix: assert
   `serve(...)…server_address[0] == "127.0.0.1"` default and `"0.0.0.0"` with
   `lan=True`.
2. Chunk-size bound unpinned: assert per-`chunk` payload ≤ 208 chars / ≤ 2
   frames (and chunk count == ceil(total/2)) for the 4-frame mood —
   `CHUNK_FRAMES = 4` currently passes.
3. Heartbeat cadence unpinned: pin `HEARTBEAT_S < 30` against the sketch's
   IDLE_TIMEOUT_MS (import both constants or assert `Engine.HEARTBEAT_S <= 20`)
   — `HEARTBEAT_S = 45` currently passes.
4. Invariant 4 has no automated or recorded check (named per instruction);
   a one-line grep test over `muse_integration/` for router-socket/RPC use
   (mirroring the existing widening grep, which also skips that dir) would
   close it. Substance verified manually in this review: pass.

**Nits (5)**
1. Dead-code noise in tests: `dict(...)[1] if False else …` (test_engine.py:173)
   and the no-op `c._sock = c._sock` (:184) — delete.
2. Engine test writes to the real `~/.local/state/` — patch `EVENTS_FILE` /
   inject a tmp narrator.
3. `pytest.raises(Exception)` for the timeout case — pin `BridgeTimeout`; the
   `missing` FakeRouter variable is actually an unknown-method server (rename;
   optionally also test connect-to-nonexistent-socket).
4. `hook` fixture hardcodes `maxsize=8` instead of `webhook.QUEUE_MAX` — the
   bound is duplicated, a QUEUE_MAX change wouldn't surface.
5. Contract test's upstream sanity loop `break`s after the FIRST
   COMMAND_SPECS entry (verbatim port of the poc harness) — check all specs or
   drop the guard's pretense; it also validates FAMILIAR_SPECS against a
   hand-copied shape, not upstream's own validation.

## Verdict rationale

The suite is real, deterministic, honest, and kills 10/15 mutants including
every behavioral boundary it claims (flood 12/13, drop-oldest, period clamps,
clear-on-stop, reconnect). But three mutation-confirmed survivors are exactly
the kind of false confidence an adversarial pass exists to find — one
plan-promised test silently missing (bind modes), one protocol bound (chunk
size) whose violation breaks the physical board while the suite stays green,
one safety cadence (heartbeat vs 30 s MCU timeout) — plus invariant 4's
evidence gap. All are one-assertion fixes; none indicates deception or
structural rot. Not PASS (Importants exist), nowhere near MAJOR-FAIL.

VERDICT: MINOR-FAIL
