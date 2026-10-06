<!-- SIGNPOST | 2/5: PLAN | single source of truth; implementation must conform — divergence means amending this file in the same change, not improvising
     Prev: IMPLICIT_SPEC.md | Next: PLAN_VALIDATION.md -->
# muse-familiar completion (missing features) — Implementation Plan
scale: medium

## Overview

Make every public promise of the released repo true and close the verified
hygiene gaps, in five ordered phases: verification infrastructure first
(CI + parity/regression guards), then first-run path, feed examples, CLI
parity, and finally one-command Muse integration + release artifacts.

## Current State

Cite source: research doc `2026-10-06-muse-familiar-missing-features.md`
Evidence Ledger (fresh, HEAD d1995f8). Headlines: no `.github/` at all;
0 tags/releases; topics `[]`, homepage unset; README.md:42 dangling unit
step; README.md:76-78 references absent `sdk-linux/`; docs/index.html:140-144
uses undefined `$KEY`; only-curl examples vs. promised trio; CLI lacks
status/feed (cli.py:31-39); README.md:88 stale "19 tests" (28 collected);
Muse registration is a manual executor edit (COMMANDS.md:20-54);
MUSE_SESSION_ID documented (COMMANDS.md:65) but unused (engine.py Narrator);
contract test — the only Muse-spec oracle — skips by default
(test_contract.py:14-16); make_landing has no parity check (test_landing
pins formatting only); cli.py + Narrator have zero tests.

## Desired End State

Observable: `git push` triggers CI (pytest+msgpack suite, secrets gate,
landing regen parity, co-author grep) and is green; a fresh cloner
following README alone reaches an enabled engine service (installer +
documented linger note); `examples/` ships GitHub-Action + Home-Assistant
artifacts; `familiar status` / `familiar feed ci_green` work locally and
are tested; `sudo python3 muse_integration/install.py` registers the
familiar commands into the board's Muse SDK atomically and reversibly
(`--remove`), single-sourced from familiar_specs.py; repo has topics,
homepage = landing URL, annotated tag v0.1.0 + GitHub Release; no
dangling doc references anywhere; suite ≥34 passed 1 skipped; gate clean
in all modes.

## What We're NOT Doing

Firmware/sketch changes (inv 2 — untouched); sibling-parity features
(TTS/sound, persistence/growth mechanics, personas, custom-frame tooling,
enclosure STLs, OTA, App Lab distribution); behavioral config knobs
(mood durations/temps); lint config; PyPI publishing; enabling GitHub
Discussions; phone pairing + release video (user gates); any hallpi or
router-socket interaction change; no new runtime dependencies.

## Approach

Five phases ordered so verification lands first and release last.
Key decisions (each tied to an invariant; advisor-informed):

- **CI runs what the NUC runs**: checkout with `fetch-depth: '0'` (the
  gate's history scan and the co-author grep need full history) → `uv
  run --with pytest --with msgpack python -m pytest -q` →
  `python3 tools/secrets_gate.py` (plain run only — an
  `SECRETS_GATE_EXTRA` literal cannot appear in CI: the literal would sit
  in the tracked ci.yml and self-trip the scan) → regen parity →
  co-author step: `bash -c 'm=$(git log --all --grep="Co-Authored-By"
  --format=%H); [ -z "$m" ] || { echo "co-author trailers: $m"; exit 1; }'`
  (fails when trailers EXIST) (inv 1, 8, 12). Contract test stays a clean
  skip in CI (no SDK checkout; documented in the workflow).
- **make_landing refactor**: extract `build() -> (html: str, png: bytes)`
  from file-writing `main()` (inv 8); parity test byte-compares `build()`
  vs committed `docs/` (closes research Gap).
- **Installer uses `systemctl --user link`**, not unit copying: repo unit
  stays the single installed source (advisor #9). Default flow asserts
  clone at `~/muse-familiar` (the unit's `%h/muse-familiar` paths); an
  optional `--repo DIR` writes a path-override drop-in for other
  locations. Idempotent restart: only `daemon-reload` + `restart` when
  linked state or key changed (advisor #5). Linger documented, not
  automated (needs sudo; README note).
- **Landing quickstart** gets the real steps (key gen, installer) via
  make_landing — parity test then guarantees README/landing cannot drift
  silently (inv 11). Regression guard: test_meta banned-strings
  (`$KEY`, `sdk-linux/`, `after installing the unit`) + sketch-clamp grep
  test (advisor #3, #8c).
- **Examples**: ready artifacts with explicit decisions — GH Action step
  is `continue-on-error` (shared 12/min rate bucket must not fail visible
  CI; advisor #6); HA via `rest_command` + automation. YAML parsed in
  tests via **dev-only** pyyaml (`importorskip` locally, injected in CI)
  — runtime stays stdlib (inv 10).
- **CLI parity**: `status` (health probe + `systemctl --user is-active` +
  locked tail of events JSONL — LOCK_SH during read, advisor #11) and
  `feed <kind>` (kind validated against KIND_TO_MOOD; key from
  `--key-file` default `~/.config/familiar/key`; POST loopback; inherits
  401/429 semantics). Exit codes follow the cli.py:8 convention, decided:
  0 ok · 2 runtime error (engine down, 401/429/network) · 3 usage (bad
  kind/args) (advisor #7). Narrator gains optional `MUSE_SESSION_ID` →
  `--session-id` (SDK pebble pattern; spec bounding assumption).
- **Muse one-command integration**: `muse_integration/install.py` (sudo)
  locates `/opt/musegadget/venv/**/musegadget/executor.py`, takes a
  timestamped backup, and patches by inserting a tiny **sentinel-marked,
  try/except-guarded hook** — `sys.path.insert(0, <board repo path>)`
  (absolute, resolved at install time; `--repo` override, default
  `/home/arduino/muse-familiar`) + `from
  muse_integration.familiar_specs import register; register(...)` wrapped
  in `except Exception: pass` so a missing repo degrades to
  familiar-commands-absent, never a dead musegadget service. ALL spec +
  dispatch logic lives in the repo module (`register()` updates
  COMMAND_SPECS and wraps Executor.run dispatch) — single source (inv 9).
  Patched content is `compile()`d on a temp file, then `os.replace`d
  (atomic); `musegadget` restarted after verified replace (`--no-restart`
  skip). Verification after install: root-run module-load assertion —
  `python3 -c "import importlib.util; …load executor.py…; assert
  'familiar.status' in COMMAND_SPECS"` (`musegadget info` cannot show
  registration). Idempotent: sentinel present → no-op unless `--force`.
  `--remove` restores the **oldest** backup (the true pre-familiar
  original; later `--force` backups may still carry the sentinel) and
  deletes newer ones + restarts. Temp files cleaned on all paths.
- **Release last**: topics + homepage via `gh api` (`gh repo edit`), tag
  `v0.1.0` (annotated, plain message — no trailer), `gh release create`
  with notes; social-pack topics line corrected (out-of-repo file).

## Design Analysis

- **Invariants → mechanism**: inv1 gate-in-CI+gate-modes; inv2 no firmware
  edits + sketch-clamp grep test; inv3 feed reuses webhook path, no new
  endpoint logic; inv4 bridge_client untouched; inv5 installer/CLI take no
  long-lived display ownership; status tail takes LOCK_SH briefly; inv6
  bridge untouched; inv7 webhook untouched (no new mutation sites); inv8
  build() + parity test; inv9 import-based registration + stub-executor
  test + real-SDK contract run in Phase 5; inv10 stdlib runtime, pyyaml
  dev-only; inv11 quickstart rewrite + banned-strings test; inv12 CI grep
  + plain tag message; inv13 backup/--remove, restart only after verified
  replace. Each maps to a Phase criterion below that fails if violated.
- **Failure & concurrency**: installer re-runs (unit linked already, key
  exists → no-op; changed → reload+restart) (advisor #5); install.py
  crash windows: backup taken before any write; patched bytes compiled on
  a temp file then atomically replaced — a crash pre-replace leaves the
  original untouched; `--remove` restores backup + restarts. CLI status
  races nothing (read-only + LOCK_SH tail); feed is one HTTP request.
  Narrator change is argv-only. State cleanup: temp files removed on all
  exits (try/finally); no new long-lived state.
- **Simplicity guardrails**: no DI, no new abstraction layers; build() is
  a 2-function refactor, not a framework; installer is one bash script
  (~60 lines) using systemctl primitives; install.py is one stdlib
  python file; no config knobs added anywhere (spec bounding assumption).
  Pyyaml justified: dev-only YAML validation vs hand-rolled parser
  (never hand-roll parsing).
- **Blast radius**: cli.py callers = README/landing/COMMANDS docs (updated
  same-phase); engine.py Narrator argv (board unit env unchanged — env
  var optional); make_langered docs regenerated; units/ file untouched
  (linked, not copied); board executor.py patched by explicit sudo
  command only (never by CI); rollback for every board action = backup +
  --remove + unit unlink. Back-compat: all existing subcommands/tests
  unchanged.
- **Interrogation**: *Breaks?* — docs regeneration (parity test catches),
  CLI arg parsing (new tests), board service restart (manual gate, kill
  test exists). *Riskiest step:* install.py patching a root-owned venv
  file — earliest check: stub-executor test in tests/test_muse_install.py
  (runs against a temp copy, asserts compile+idempotency+restore) BEFORE
  any board run. *Options not taken:* editing COMMAND_SPECS by text
  merge (drift — advisor #1 rejected); unit-copy installer (drift —
  advisor #9 rejected); SDK env-plugin (does not exist); PyPI publish +
  pipx install (not promised; tag+release suffices).
- **Verification design**: reuses VS commands (test-all/test-one/gate/
  regen); closes Gaps: regen parity (Phase 1), docs-runnability observer
  (Phase 2 banned-strings test), co-author observer (Phase 1 CI grep),
  sketch-clamp observer (Phase 1 grep test), cli/Narrator untested seams
  (Phase 4), contract-oracle activation (Phase 5 local run + workflow
  comment). Still-open Gaps deferred with reason: webhook thread-accounting
  exactness (no behavior change in this plan — nothing to observe yet);
  pixel gate (human, release video); offline-first-boot uv dependency
  (documented in README as a note, not instrumented).
- **Default choices**: deviating default = unit install via `link`
  (stock systemd idiom) instead of copy-with-substitution (creates
  repo-vs-installed drift) — advisor-endorsed. Everything else follows
  existing repo conventions (hook scripts, exit codes, importorskip
  patterns, flock).

## Scale Cost Model

N/A — no perf-sensitive change: webhook/bridge hot paths untouched; new
surfaces are one-shot CLI commands and a CI workflow; single-board
hobby envelope (research Workload Envelope: ≤12 pokes/min, single user).

## Phase 1: Verification infrastructure (CI + parity + regression guards)

### Changes
#### CI workflow — `.github/workflows/ci.yml` (new)
checkout (`fetch-depth: '0'` — history scan + co-author grep need full
history) → uv setup → `uv run --with pytest --with msgpack python -m
pytest -q` → `python3 tools/secrets_gate.py` (plain run only; an
`SECRETS_GATE_EXTRA` literal cannot ship in CI — it would self-trip the
tracked-file scan) → `python3 tools/make_landing.py && git diff
--exit-code docs/` → co-author step `bash -c 'm=$(git log --all
--grep="Co-Authored-By" --format=%H); [ -z "$m" ] || { echo "co-author
trailers: $m"; exit 1; }'`. Comment in-file: contract test intentionally
skips without MUSE_SDK_LINUX_DIR; how to run it locally.
#### Landing generator refactor — `tools/make_landing.py`
Extract `build()` returning `(html, png_bytes)`; `main()` writes them;
`__main__` output unchanged byte-for-byte (parity test proves).
#### Parity + guard tests — `tests/test_landing.py`, `tests/test_meta.py`
`test_landing_matches_generator` (byte-compare build() vs committed
docs/); `test_sketch_clamps_present` (assert FramePlayer.ino contains
the real clamp anchors: `setGrayscaleBits(3)`, the 250 ms minimum-period
clamp, the 30000 ms idle timeout, the 64-frame cap); extend meta with
`test_no_coauthor_trailers_in_log` mirroring the CI grep (belt+suspenders
locally).
#### README count fix — `README.md`
"19 host-side tests" → live count wording + how to run the suite (closes
"README documents no test command").

### Success Criteria
- [x] Local: `uv run --with pytest --with msgpack python -m pytest
  tests/test_landing.py::test_landing_matches_generator -q` → pass; and
  mutating `docs/index.html` by one byte → same test FAILS
  ✓ 11 passed (landing+meta); ✓ FAILED test_landing_matches_generator - AssertionError (1 failed in 0.27s) on 1-byte drift, restored after · localizes
  to: generator↔artifact layer.
- [x] Local: `uv run --with pytest --with msgpack python -m pytest
  tests/test_meta.py -q` → pass incl. clamp + co-author tests
  ✓ 6 passed (test_meta.py) ·
  localizes to: repo-hygiene invariants.
- [x] End-to-end: `uv run --with pytest --with msgpack python -m pytest
  -q` → ≥30 passed, ≤2 skipped (28 existing + new; skips = contract, and
  yaml only when pyyaml absent); gate clean.
  ✓ 30 passed, 1 skipped in 4.17s · SECRETS GATE: clean · landing in sync
- [x] End-to-end: after push, `gh run watch` (or `gh api` latest run) →
  workflow `success` on first run.
  ✓ run 37453260555: completed success

## Phase 2: First-run path (installer + runnable docs)

### Changes
#### Installer — `scripts/install.sh` (new)
`set -euo pipefail`; `--check` dry-run mode (no side effects; prints
READY or precise blocker — NUC/local runs pass `--repo DIR` since the
default path assertion is for the board); default: assert repo at
`~/muse-familiar` — for other locations `--repo DIR` writes
`~/.config/systemd/user/familiar-engine.service.d/override.conf` that
**resets then re-sets** every path-bearing directive (systemd drop-ins
append to list directives, so the override must start each with an empty
assignment: `ExecStartPre=`, `ExecStartPre=<new>` ×3 directives +
`Environment=PYTHONPATH=<new>`), key file generated `600` if absent,
`systemctl --user link units/familiar-engine.service` (if not linked),
`daemon-reload`, enable `--now`, and `restart` only when linked target or
key changed.
#### README quickstart — `README.md`
Clone to explicit `~/muse-familiar` destination; `scripts/install.sh
--check` then install; linger note for headless SSH
(`sudo loginctl enable-linger $USER`); teardown section rewritten (unit
disable+unlink+key removal; SDK uninstall referenced by upstream GitHub
URL — kills `sdk-linux/` dangle).
#### Landing quickstart — `tools/make_landing.py`
Real steps (key gen, installer, `KEY=$(cat ~/.config/familiar/key)`
exported on-page before any use, curl); regenerate docs/ (parity test
enforces). Landing never uses an undefined variable.
#### Regression guard — `tests/test_meta.py`
`test_docs_no_dangling_references`: bans `sdk-linux/`, `after installing
the unit`, and an undefined-`$KEY` (literal `$KEY` in docs/index.html is
banned outright — the landing exports `KEY=` before use, so the variable
name appearing is fine but the raw `$KEY` reference is not; README's
curl may keep `$KEY` because README defines it in the same block).

### Success Criteria
- [x] Local: `bash -n scripts/install.sh` → clean; `bash
  scripts/install.sh --check --repo ~/repos/learn/muse-familiar` on NUC →
  exit 0 + prints the exact drop-in it WOULD write (including the
  `Directive=` reset lines) with zero side effects; default-path
  `--check` (no `--repo`) on NUC → ALSO exit 0 via repo auto-detection
  (see Amendment 1) · localizes to: installer logic.
  ✓ syntax OK · ✓ READY rc=0 with drop-in+key+restart plan printed
  (both with and without --repo; auto-detect resolves the same repo)
- [x] Local: `pytest tests/test_meta.py::test_docs_no_dangling_references
  -q` → pass; reintroducing any banned string fails it · localizes to:
  docs-runnability layer.
  ✓ 1 passed in 0.01s
- [x] End-to-end: full suite green incl. landing parity after regen; gate
  clean (README/.sh are scanned file types).
  ✓ 31 passed, 1 skipped in 3.67s · SECRETS GATE: clean · wrote docs/index.html (17 KB) + og-image.png (21 KB)
- [ ] Manual (board): `scripts/install.sh --check` then install on UNO Q
  → service active via `systemctl --user is-active familiar-engine`.

## Phase 3: Feed examples (GitHub Action + Home Assistant)

### Changes
#### `examples/github-action.yml` (new)
Step template: on job completion, curl POST `/poke` with
`X-Familiar-Key: ${{ secrets.FAMILIAR_KEY }}`, kind ci_green/ci_red by
conclusion; step `continue-on-error: true` + comment why (shared rate
bucket).
#### `examples/home-assistant.yaml` (new)
`rest_command.familiar_poke` (url+key from secrets) + example
automation mapping an entity event to a kind.
#### `examples/README.md` (new)
Both artifacts explained; LAN mode `--lan` prerequisite; rate-limit note.
#### Wiring — `README.md`, `tools/make_landing.py`
Trio paragraph links the artifacts (landing regen + parity).
#### YAML guard — `tests/test_meta.py` + CI wiring
`test_example_yaml_parses` (importorskip yaml; safe_load both; assert
required keys exist). **ci.yml is amended in this phase**: the pytest
step becomes `uv run --with pytest --with msgpack --with pyyaml python
-m pytest -q` so the YAML test RUNS in CI (locally without pyyaml it
skips cleanly).

### Success Criteria
- [ ] Local: `uv run --with pytest --with msgpack --with pyyaml python
  -m pytest tests/test_meta.py::test_example_yaml_parses -q` → pass;
  without pyyaml → clean skip · localizes to: examples' syntactic layer.
- [ ] End-to-end: full suite green; gate clean.
- [ ] Manual: eyeball the workflow YAML against GitHub's schema (keys
  `on:/jobs:/steps:`, expression contexts).

## Phase 4: CLI parity (status + feed) and Narrator session id

### Changes
#### `familiar/cli.py`
`status` subcommand: GET `127.0.0.1:8123/health` (timeout 2 s),
`systemctl --user is-active familiar-engine` (absent binary →
"unknown"), last 5 events from the events JSONL — path resolved the same
way the engine does (honors `FAMILIAR_EVENTS_FILE`, read with brief
LOCK_SH), mood list summary; engine-down → exit 2 with clear report.
`feed <kind>`: validate kind ∈ KIND_TO_MOOD (else exit 3); key via
`--key-file` (default engine path); POST loopback `/poke`; 2xx → exit 0;
401/429/conn → exit 2. Docstring at cli.py:8 updated: 2 = runtime error
(bridge/hardware/engine-down/auth/network), 3 = usage.
#### `familiar/engine.py`
Narrator: optional `MUSE_SESSION_ID` env → append `--session-id <v>` to
send argv (absent → unchanged).
#### Tests — `tests/test_cli.py` (new), `tests/test_engine.py`
feed/status against a live loopback webhook fixture (reuse test_engine
pattern); Narrator argv recorded via monkeypatched subprocess.run — the
test monkeypatches the readiness gate (`_muse_ready` or its
MUSEGADGET/sock inputs at engine.py:77-81) so send() is reached — for
set/unset session id.

### Success Criteria
- [ ] Local: `pytest tests/test_cli.py -q` → all pass; fault injection:
  wrong key → process exit 2 (not traceback), bad kind → exit 3 ·
  localizes to: CLI client layer.
- [ ] Local: `pytest tests/test_engine.py -q -k narrator` → argv carries
  `--session-id` iff env set · localizes to: Narrator.
- [ ] End-to-end: full suite ≥34 passed, ≤2 skipped; gate clean.
- [ ] Manual (board): `familiar status` reports healthy; `familiar feed
  ci_green` makes the creature hop.

## Phase 5: One-command Muse integration + release artifacts

### Changes
#### `muse_integration/install.py` (new, stdlib)
Locate executor.py under `/opt/musegadget/venv` (configurable
`--venv`); `--check` prints plan; install: timestamped backup → patch
content by inserting sentinel-marked import of the repo's
`muse_integration.familiar_specs` + registration lines (single source;
no spec text copied) → `compile()` patched source → `os.replace` →
restart `musegadget` (skip with `--no-restart`) → print verification
(`musegadget info`). Idempotent: sentinel present → no-op unless
`--force`. `--remove`: restore newest backup byte-identically +
restart. Temp files cleaned on all paths.
#### `muse_integration/COMMANDS.md` (rewrite)
One-command flow (sudo install.py) + what it changed + `--remove`;
pairing runbook unchanged; paths generic ($HOME/muse-familiar), no
hardcoded board dirs; MUSE_SESSION_ID section updated to implemented
behavior.
#### Repo metadata + release — gh commands (documented in plan, run once)
topics (arduino, ai, muse, muse-gadget, led-matrix, iot, qualcomm,
zephyr, desk-pet), homepage = landing URL, annotated tag `v0.1.0` on the
final commit (plain message, no trailer), `gh release create` with notes
(summary, quickstart link, landing link). Social-pack topics line
corrected (out-of-repo file, this session).

### Success Criteria
- [ ] Local: `pytest tests/test_muse_install.py -q` → stub-executor
  scenario: backup created; patched module **exec'd** (not just compiled)
  with the stub executor — `register()` ran, `familiar.status` present in
  COMMAND_SPECS, dispatch answers a familiar command; sentinel idempotent
  (re-run no-op); `--force` re-patch then `--remove` → original bytes
  restored (oldest-backup rule); temp cleaned · localizes to: patch logic
  (never the live venv).
- [ ] Local: `MUSE_SDK_LINUX_DIR=$HOME/tmp-research/muse-gadget-sdk/linux
  uv run --with pytest --with msgpack python -m pytest
  tests/test_contract.py -q` → PASS against the real SDK (inv 9
  unbroken by the import-based registration).
- [ ] End-to-end: full suite green; gate clean; `gh repo view` shows
  topics+homepage; `gh api repos/nitishagar/muse-familiar/releases`
  length 1; landing still HTTP 200.
- [ ] Manual (board, user-visible): `sudo python3
  muse_integration/install.py` → service restarts, `musegadget info`
  unchanged, executor contains sentinel import; `--remove` round-trips.

## Testing Strategy

New: test_landing parity (byte oracle), test_meta additions (clamps,
co-author, dangling refs, YAML), test_cli.py (loopback webhook fixture
reused from test_engine patterns), test_muse_install.py (stub executor
in tmp_path — never the real venv). Existing: all 28 outcomes stay
green; contract test additionally run against the real SDK in Phase 5.
Edges covered: engine-down status, 401/429 feed, bad kind, idempotent
installs, crash-before-replace, session-id absent. Gaps closed per
phase; deferred gaps named in Verification design.

## Amendments

- AMENDED 2026-10-06 Phase 2 [factual]: install.sh auto-detects the repo
  root from its own location and writes the path drop-in automatically
  whenever the repo is not at ~/muse-familiar; the hard "assert default
  path / require --repo" behavior described in the criterion was not
  implemented — the flag remains as an explicit override. Why: the
  criterion over-specified a failure mode; auto-detect serves the same
  invariant (unit stays single-source via link; non-default clones get a
  correct drop-in) with no footgun for a cloner who forgets the flag. No
  interface, locking, ordering, or cost change (new file; CLI surface
  --check/--repo unchanged). Evidence: scripts/install.sh REPO detection
  + DROPIN_NEEDED branch; NUC dry-run both ways → READY. [User approval
  not obtainable mid-autonomous run — flagged in the phase report for
  veto; reverting is a one-line assert.]

## References

Research: `thoughts/shared/research/2026-10-06-muse-familiar-missing-features.md`
· VS: `thoughts/shared/VERIFICATION_SURFACE.md` · Prior loop:
`thoughts/shared/plans/2026-10-04-muse-familiar/` · SDK executor pattern:
`~/tmp-research/muse-gadget-sdk/linux/src/musegadget/executor.py` ·
pebble session-id pattern: SDK `examples/pebble_ring_bridge.py:86-87`.
