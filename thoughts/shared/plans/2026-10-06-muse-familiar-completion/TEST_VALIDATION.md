<!-- SIGNPOST | 4/5: TEST_VALIDATION | adversarial review of the tests themselves | Next: RELEASE (out of repo) -->
# Test Validation — muse-familiar completion

Reviewer: adversarial (independent of implementation). Scope: `git diff
19e3234..HEAD` tests (test_meta.py, test_landing.py, test_cli.py NEW,
test_muse_install.py NEW, narrator tests appended to test_engine.py)
against IMPLICIT_SPEC.md invariants/edges and PLAN.md Phases 1-5 criteria.

## 1. Suite runs (executed by reviewer, not trusted from evidence)

- `uv run --with pytest --with msgpack --with pyyaml python -m pytest -q`
  → **45 passed, 1 skipped in 7.46s** (matches expectation exactly; skip =
  contract test, MUSE_SDK_LINUX_DIR unset).
- `uv run --with pytest --with msgpack python -m pytest tests/test_meta.py -q`
  → **7 passed, 1 skipped**; `test_example_yaml_parses SKIPPED (could not
  import 'yaml')` — clean skip, inv 10 (stdlib runtime) holds.
- CI on HEAD: run 37456312264 `completed success` (checked via `gh run list`)
  — Phase 1's push-green criterion observably true, still.

## 2. Invariant / edge coverage (checklist item 1)

| Invariant / edge | Automated check | Verdict |
|---|---|---|
| Regen parity (inv 8) | `test_landing_matches_generator` byte-compares html+png | **Mutation-verified**: 1-byte flip in docs/index.html → FAIL (scratch copy) |
| Sketch clamps (inv 2) | `test_sketch_clamps_present` — anchors incl. values (`MIN_PERIOD_MS = 250` etc.), confirmed present in .ino | FAILs if any clamp value changes |
| Co-author grep (inv 12) | `test_no_coauthor_trailers_in_log` + CI step (fetch-depth 0) | 0 hits here; CI pins full history |
| Docs banned strings (inv 11) | `test_docs_no_dangling_references` (`sdk-linux/`, `after installing the unit`, `$KEY` in landing) | FAILs on reintroduction (string `in` checks); README now inlines `$(cat ~/.config/familiar/key)` so no `$KEY` anywhere |
| YAML validity | `test_example_yaml_parses` (HA-tag-aware loader; asserts continue-on-error + secrets context + rest_command keys) | Real parse, real key assertions |
| CLI exit codes 0/2/3 | happy→0; 401→2; conn-refused→2; bad kind→3; missing key file→3 | 401 branch **mutation-verified** (return 0 → FAIL) |
| CLI 429 | **No test** | See finding F3 — indirect only |
| Narrator session-id present/absent | both branches in one test, exact argv asserted | **Mutation-verified** (drop the flag → FAIL) |
| Installer idempotency | `test_install_is_idempotent` (bytes untouched, 1 backup, "already present") | FAILs if re-patch happens |
| --remove oldest-backup byte-restore after --force | round-trip test: 2 backups → original bytes, no residue, no familiar specs after load | **Mutation-verified** (restore newest → FAIL) |
| Crash-before-replace leaves original | `test_crash_before_replace_leaves_original` (os.replace boom → original bytes) | Pins the invariant; see nit N4 on its second half |
| Verification-failure restores backup | **No test** | See finding F1 — mutation survived |
| Failure paths / state released | servers shutdown+closed in fixtures; port=0 everywhere; sys.path removed in finally; tmp residue globbed | Nits N1/N2 remain |
| Rate-limit inherited by feed (spec edge) | server-side 429 pinned by pre-existing `test_webhook_rate_limit`; CLI side only via shared HTTPError branch | F3 |

## 3. Criteria coverage (checklist item 2)

- Phase 1: all four criteria automated and re-verified above (incl. live CI
  green). PASS.
- Phase 2: banned-strings criterion automated. **The install.sh criterion
  (`bash -n` clean; `--check` prints the exact drop-in with reset lines;
  auto-detect) has NO automated check** — see finding F2. The board
  criterion is marked Manual. PARTIAL.
- Phase 3: YAML criterion automated (pass + clean skip). The E2E checkbox
  is unticked in PLAN.md but is superseded by Phase 4/5 runs (41/45
  passed recorded) — bookkeeping nit only (N6). Manual eyeball criterion
  marked Manual. PASS-with-nit.
- Phase 4: CLI + narrator criteria automated and mutation-verified. The
  status events-tail sub-promise (`FAMILIAR_EVENTS_FILE` honoring +
  LOCK_SH read) is stubbed away in the only fixture that exercises status
  (`monkeypatch cli._recent_events → []`) — F4. Board criterion marked
  Manual. PARTIAL.
- Phase 5: stub-executor criterion fully automated (backup, exec'd module,
  dispatch + allowlists incl. `kind: "x; reboot"` rejected, idempotent,
  force+remove round-trip, crash window, temp residue). Contract-vs-real-
  SDK criterion is env-gated (author ran it; CI skip documented in-file) —
  acceptable. Repo metadata/release criteria are out-of-repo gh-observable,
  not pytest-testable; release deliberately deferred to post-review per
  HANDOFF_LEDGER. PASS-with-note.

## 4. Real assertions (checklist item 3)

No tautologies found. Strongest oracles: byte-identity (landing parity,
backup restore), exact-argv (Narrator), queue delivery (feed happy path
asserts the event actually reached the webhook's queue, not just rc 0),
command-capture (stub executor records what system_run was asked to run —
pins the allowlist against injection-shaped input). `assert rc == 0,
capsys.readouterr().out` is lazy-safe (assert msg evaluates only on
failure; the later read gets full output).

## 5. Test integrity (checklist item 4)

- Diffs to test_meta.py / test_landing.py / test_engine.py are strictly
  append-only (verified via `git diff 19e3234..HEAD -- tests/`); the
  landing tests from 110ee29/2cc19c3 (hero centering, control groups,
  bands, OG text/font) are intact and unmodified. No deletions anywhere
  in tests/. No pre-existing test weakened.
- Fail-ability proven by mutation on 4 tests (parity, remove-oldest,
  session-id, 401-exit-2) — all failed as desired; one mutation
  deliberately survived (F1). Scratch copies deleted; repo tree clean.

## 6. Over-mocking (checklist item 5)

- CLI fixture is a **real** `webhook.serve()` ThreadingHTTPServer on an
  ephemeral port + the real urllib client path — not a mock. Only
  `_recent_events` is stubbed (justified for feed tests; leaves F4).
- muse-install stub mirrors the real SDK executor, confirmed against
  `~/tmp-research/muse-gadget-sdk/linux/src/musegadget/executor.py`:
  module-level `from musegadget import __version__` (executor.py:36),
  `@dataclass(frozen=True)` (:101), `system_run(self, params, timeout_ms)`
  with positional timeout (:160), `run(self, command, params,
  timeout_ms=None)` (:131). `register()` calls `system_run({...}, None)`
  positionally — matches. The tests exec the REAL install.py and REAL
  familiar_specs.py against the stub; the verification step even runs a
  real subprocess import. Not over-mocked.

## 7. Determinism (checklist item 6)

- Ports: all ephemeral (`port=0`); down-tests use port 1 (instant refuse).
  No timing sleeps. Backup same-second collisions suffix-proofed (`-N`),
  and lexicographic sort = chronological. suite passes under both
  `python -m pytest` and bare `pytest` (project installed by uv).
- `test_no_coauthor_trailers_in_log` is vacuous in a shallow clone —
  acknowledged in-comment; CI pins it with fetch-depth 0. Acceptable.
- systemctl/loginctl absence tolerated (`except Exception` → "unknown";
  install.sh guards with `|| echo no`). install.sh is never executed by
  tests, so systemd availability is moot for the suite.
- N1: `test_status_engine_down` runs the real `_recent_events` against
  real HOME paths — `open(~/.local/state/familiar.lock, "a+")` CREATES
  the lock file on machines that lack it (side effect outside tmp; brief
  LOCK_SH, harmless, deterministic).
- N2: test_muse_install leaks `"musegadget"`, `"muse_integration.familiar_specs"`
  and per-test executor modules into sys.modules (benign: identical stub
  content, unique names — but cross-test cache reuse is real).

## Findings

- **F1 (Important)** — install.py verification-failure restore path
  (install.py:179-188) is untested: reviewer deleted the
  `shutil.copy2(backup, executor)` restores in BOTH the
  verification-exception and empty-registered branches and all 4
  test_muse_install tests still passed. The path is reachable and
  currently correct (probe: `--repo /nonexistent` → SystemExit "specs
  missing — backup restored", original bytes restored) — a stub test
  pointing `--repo` at a missing dir would pin it. inv 13 (reversible)
  coverage hole; not among Phase 5's promised test list, so beyond-plan
  rather than a missed promise.
- **F2 (Important)** — scripts/install.sh (143 lines: drop-in
  reset-then-set generation, link/restart-only-on-change logic,
  auto-detect, `--check` output) has ZERO automated coverage. Its Phase 2
  criterion is author-run "Local" evidence only; `bash -n` and a
  `--check` output assertion are side-effect-free and trivially
  automatable. Under this review's rule (untested non-Manual criteria =
  FAIL) this is the one outright criteria gap.
- **F3 (Finding)** — no test pins that CLI feed on a 429 exits 2. Indirect
  coverage exists (the 401 test exercises the identical HTTPError branch;
  `test_webhook_rate_limit` pins the server side), and a reviewer probe
  confirms 429 → exit 2 today, but a regression that treated 429
  differently from 401 in cli.py would slip through.
- **F4 (Finding)** — `status`'s events tail (honors FAMILIAR_EVENTS_FILE,
  LOCK_SH read, last-5) is never asserted: the live_engine fixture
  stubs `_recent_events` to `[]` and the down-test reads real HOME files.
  A test redirecting EVENTS_FILE to tmp and asserting tail output would
  close it.

### Nits

- N1: HOME side-effect of test_status_engine_down (lock-file creation).
- N2: sys.modules pollution in test_muse_install (see above).
- N3: argparse usage errors (missing kind/subcommand) exit 2 via
  SystemExit, not the documented 3 for "bad usage value"; untested and
  inconsistent with cli.py's docstring — pre-existing parser behavior
  extended to the new subcommands.
- N4: the second half of test_crash_before_replace (module loads without
  familiar specs) cannot distinguish "restore ran" from "replace never
  ran" — redundant but harmless; the bytes-equality oracle is the real pin.
- N5: contract-vs-real-SDK oracle stays env-gated; CI skip documented.
- N6: Phase 3 E2E checkbox unticked in PLAN.md (superseded by later
  full-suite evidence — bookkeeping only).
- N7: release/topics criteria out-of-repo, deferred per HANDOFF_LEDGER —
  correctly not pytest-testable.

## Verdict rationale

The suite is honest and largely earned: strictly additive, real fixtures
(not mocks) on the CLI and installer seams, byte/exact-argv/queue-delivery
oracles, four mutation-verified fail-able tests, clean dependency-gated
skips, and live CI green. What keeps it from PASS: one genuine untested
safety path in the root-run patcher (F1, proven by surviving mutation),
one whole automatable surface with no automated check backing its
criterion (F2), and two small pinning gaps (F3, F4). None indicate
assert-nothing tests or weakened coverage; all are additive follow-ups.

VERDICT: MINOR-FAIL
