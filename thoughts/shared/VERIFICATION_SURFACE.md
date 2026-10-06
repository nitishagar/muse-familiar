# Verification Surface — muse-familiar

Durable inventory of the feedback loops this repo offers. The verify skills
and every plan phase cite this file; refresh it when commands change.
Source: research 2026-10-06 (`research/2026-10-06-muse-familiar-missing-features.md`).

## Commands

- **test-all (cold clone)**: `uv run --with pytest --with msgpack python -m pytest -q`
  — healthy output: `27 passed, 1 skipped` at HEAD 2cc19c3 (28 collected).
  **The 1 skipped is `tests/test_contract.py`** — the upstream Muse-spec
  oracle. It activates only with `MUSE_SDK_LINUX_DIR=<path-to-muse-gadget-sdk>/linux`
  (`tests/test_contract.py:14-16`); with it set, expect `28 passed`.
  Without msgpack the whole engine module additionally skips cleanly
  (`tests/test_engine.py:19` `pytest.importorskip`), so a bare `pytest` run
  reports ~6 outcomes — that is degradation, not failure.
- **test-all (this NUC's repo venv)**: `~/.local/bin/uv run --python .venv/bin/python
  --with pytest --with msgpack python -m pytest -q`. The venv is uv-made (no pip).
- **test-one**: `uv run --with pytest --with msgpack python -m pytest
  tests/test_engine.py::test_webhook_rate_limit -q` — plain pytest selector
  syntax; nothing repo-specific. pytest config: `pyproject.toml:15-16`
  (`testpaths = ["tests"]`).
- **secrets gate**: `python3 tools/secrets_gate.py` — healthy: `SECRETS GATE: clean`.
  Modes: `SECRETS_GATE_EXTRA=<literal>` re-runs tier (b) against any literal
  (board password, WiFi password, token prefix). Scans git index + every
  history blob (`git cat-file --batch-all-objects`). **Manual-only: nothing
  automates it** (no hook, no CI).
- **landing regen**: `python3 tools/make_landing.py` — healthy: `wrote
  docs/index.html (… KB) + og-image.png (… KB)`. Deterministic: imports
  `familiar/frames.py` via importlib (`tools/make_landing.py:28-33`).
- **flash (BOARD ONLY)**: `firmware/upload.sh` — requires `UNOQ_UPLOAD_PASSWORD`
  env, board-local arduino-cli + `arduino:zephyr:unoq` core, takes exclusive
  flock on `~/.local/state/familiar.lock` (`upload.sh:14-15`).
- **kill test (BOARD ONLY)**: `units/kill_test.sh` — healthy: `KILLTEST-OK`;
  SIGKILLs the engine, asserts restart + unit/socket snapshot diffs.
- **CI**: none exists (no `.github/`) — every command above is run by hand.

## Oracles

- **FakeRouter** (`tests/test_engine.py:99`) — in-process Unix-socket
  msgpack-rpc server speaking the real frame shapes. Confirms the bridge
  client protocol + engine behavior; cannot confirm anything about the
  board's actual router (cap, latency).
- **Contract test** (`tests/test_contract.py`) — pins `muse_integration/`
  spec shape to the SDK's COMMAND_SPECS schema **as hand-copied**; cannot
  catch upstream SDK drift.
- **Landing tests** (`tests/test_landing.py`) — pin hero centering, mood/kind
  control groups, band layout, OG text geometry/font coverage. Do **not**
  verify docs/index.html ↔ familiar/frames.py regen parity.
- **Secrets gate** — the only check over git *history*; can confirm no
  credential shape is reachable in any blob.
- **Web `/health`** (`familiar/webhook.py:98-100`) + `familiar ping` CLI —
  live liveness probes on the board.

## Fixtures & harnesses

- FakeRouter + live-loopback HTTP fixtures in `tests/test_engine.py` —
  realistic (real sockets, real msgpack frames), dev-sized.
- `tests/test_meta.py` — repo-hygiene invariants (no token anywhere, no
  router-socket widening in executable code, msgpack-free import).
- No firmware-side harness; no visual/pixel oracle (human gate per
  `thoughts/shared/plans/2026-10-04-muse-familiar/`).

## Observability

- Engine/webhook/bridge: **zero logging calls**; only `print` in
  `familiar/cli.py:44-64`. Runtime visibility = journal via the systemd unit
  (`units/familiar-engine.service`, Type=simple) + `~/.local/state/`
  (familiar_events.jsonl, familiar_narration.jsonl fallback).
- No metrics/tracing/profiling anywhere.

## Gaps

- **Contract oracle dark by default**: test_contract.py (the only
  Muse-spec check) skips unless MUSE_SDK_LINUX_DIR is set — no documented
  invocation anywhere in the repo made that visible before this file.
- docs/index.html ↔ frames.py sync has **no observing check** (regen parity).
- Sketch-side constants (e.g. `IDLE_TIMEOUT_MS` in FramePlayer.ino) drift
  invisibly to host tests (TEST_VALIDATION residual).
- Upstream SDK spec drift unobservable in the default run (see above).
- No CI: nothing runs tests/gate/regen on push or PR.
- `familiar/cli.py` (incl. `serve` arg duplication) and the engine
  `Narrator` have **zero test references** (grep) — untested seams.
- Docs copy-paste runnability (README/landing/COMMANDS command blocks)
  has no observer — the current violations ($KEY, `sdk-linux/`,
  "after installing the unit") were found manually and could recur.
- Commit-trailer hygiene ("no co-author attribution") has no automated
  check (a manual `git log` grep exists in the trail,
  IMPLEMENTATION_VALIDATION.md:15).
- Webhook rate-limit accounting mutates module-global `_STATE["hits"]`
  from ThreadingHTTPServer handler threads unsynchronized
  (`familiar/webhook.py:24-34`) — correctness under concurrency unobserved.
- Engine unit resolves `uv run --with msgpack` at every service start —
  cold-offline first boot unexamined (uv cache/network dependency).
- Pixel-level visual correctness: human/camera gate only (accepted at release).
