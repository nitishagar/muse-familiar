<!-- SIGNPOST | 4/5: IMPLEMENTATION_VALIDATION | adversarial review of 19e3234..7cc35dc
     against PLAN.md (incl. Amendments) + IMPLICIT_SPEC.md -->
# Implementation Validation — muse-familiar completion (19e3234..7cc35dc)

Method: full diff read; every touched file read in full; the suite, secrets
gate, landing parity, contract test (real SDK), `install.sh --check` (both
modes), and `install.py` executed against a **verbatim copy of the real SDK
executor** (`~/tmp-research/muse-gadget-sdk/linux/src/musegadget/executor.py`)
in a simulated venv. Every item defaulted FAIL until earned.

## Checklist verdicts

1. **Plan conformance** — FAIL (one headline mechanism does not work against
   its target; one tick's evidence does not match its criterion; one
   undisclosed restart-semantics deviation — details below). Amendment 1
   itself is honestly written and discloses the auto-detect divergence with a
   veto flag; its "no ordering change" claim is slightly overstated (I4).
   Tick arithmetic verified as consistent: base 27+1skip → 30/31/41/45+1skip
   cumulative counts all add up; per-file counts (11 landing+meta, 6 meta,
   7 cli, 2 narrator, 4 muse_install) match the current files.
2. **Spec invariants** — PASS on 1–4, 6–8, 10–13 (evidence below);
   FAIL-adjacent on 5 and 9 (comment misstates locking reality, N1; the inv-9
   registration mechanism is single-sourced and contract-green but cannot
   complete against the real SDK — I1). Inv 1: no secrets in diff, gate clean
   (ran: `SECRETS GATE: clean`; CI scans full history via `fetch-depth: '0'`).
   Inv 2: no `firmware/` path in the diff; `.ino` only *read* by
   `tests/test_meta.py::test_sketch_clamps_present`. Inv 3: `familiar/webhook.py`
   untouched (not in diff); `feed` reuses the same endpoint/semantics.
   Inv 5: no new long-lived writer; CLI status is a short-lived reader.
   Inv 8: `build()` + `test_landing_matches_generator` byte-compare is real
   (ran: "landing in sync"; `--check` compares bytes directly — cannot
   false-pass). Inv 9: hook contains zero spec text (import +
   `register(globals())` only, `muse_integration/install.py:49-58`);
   contract test re-run against real SDK: 1 passed. Inv 10: runtime stdlib
   (urllib/fcntl/subprocess); pyyaml only in tests (`importorskip`) + CI
   `--with pyyaml`. Inv 11: all README/landing/COMMANDS/examples command
   blocks reference defined files/vars; `$KEY`, `sdk-linux/`, "after
   installing the unit" eliminated (grep-verified + test enforces).
   Inv 12: co-author grep polarity correct in CI and mirrored locally (in
   the 45 passed). Inv 13: backup-first + `--remove` + verification-failure
   restore; restore verified **byte-exact** in live testing.
3. **Failure/concurrency** — mostly PASS: backup taken before any write
   (`install.py:141`); tmp cleaned on all paths incl. `BaseException`
   (`install.py:144-156, 100-107`; tests assert no residue); crash-before-
   replace leaves original (tested); `--remove` with hook-but-zero-backups
   refuses cleanly (`install.py:91-94`); same-second `--force` backups
   counter-suffixed and oldest-wins sorting verified; CLI timeouts bounded
   (2 s health, 5 s feed, 5 s systemctl); no traceback leaks on error paths
   (tested). FAILs: the verification step itself cannot pass on the real SDK
   (I1); restart semantics deviate (I4); the LOCK_SH tail rationale is wrong
   (N1).
4. **Anti-pattern sweep** — PASS. No DI/layers/retained state/config knobs;
   `register(globals())` is justified (fresh-file exec loads don't populate
   `sys.modules[__name__]`; documented in `familiar_specs.py:55-60`; the
   ledger records the mid-phase fix). pyyaml-not-handrolled is the right
   call; HA-tag-aware SafeLoader subclass is tight (`test_meta.py:69-71`).
   install.sh is 127 lines vs the plan's "~60" — comment-heavy, not complex;
   not counted.
5. **Test integrity** — PASS. Zero deleted/modified test lines across
   `tests/` (diff contains only additions besides file headers); the
   110ee29/2cc19c3 landing-overhaul tests are intact; the phase-3 loader fix
   taught the *new* test the `!secret` tag (ledger records it; not a weakened
   pre-existing test).
6. **Common defects** — FAIL on I1 (three real defects invisible to the
   stub), otherwise tight: feed kind validated by membership (stronger than
   regex); YAML loader safe; swallowed exceptions scoped and commented
   (`cli.py:51-52`); hook's `except Exception` covers only its own 4 lines
   and logs rather than silently passing.
7. **Convention fit** — PASS. Module docstrings with exit-code contract
   (`cli.py:10-12`), lazy imports, `__package__` guards preserved, install.py
   follows the repo's one-file-stdlib pattern.

CI sanity: `.github/workflows/ci.yml` is valid YAML (parsed), step order
sane (checkout → uv → tests → gate → parity → co-author), `permissions:
contents: read` added (unrequested but sound). The plan's
`git diff --exit-code docs/` step was replaced by `make_landing.py --check`
— an in-memory byte compare that cannot false-pass (see N2).

## Important findings

**I1 — Phase 5's one-command Muse integration cannot work against the real
SDK executor (three independent defects; proven by executing install.py
against a verbatim copy of the real file).** This breaks the plan's Desired
End State ("`sudo python3 muse_integration/install.py` registers the familiar
commands") and the spec's scope-defining requirement ("Muse command
registration is one command, not a hand-edit runbook").
   a. `install.py:65-71` `load_specs` execs the patched executor under the
      *system* python3 the documented command uses. The real executor's
      module-level `from musegadget import __version__`
      (executor.py:36) is unimportable outside the venv →
      `ModuleNotFoundError` → verification fails → backup restored → exit 1.
      Observed: `patched executor failed to load (ModuleNotFoundError("No
      module named 'musegadget'")) — backup restored`.
   b. Even with musegadget importable (venv python), `load_specs` never
      registers the module in `sys.modules` before `exec_module`
      (`install.py:70-71`). The real executor's `@dataclass(frozen=True)`
      class Account (executor.py:101) makes dataclasses look up
      `sys.modules.get(cls.__module__)` → None → `AttributeError`.
      Observed verbatim.
   c. Even with (a)+(b) fixed (I re-ran with the module registered and the
      package importable: specs register fine), every dispatch fails:
      `familiar_specs.py:83/90/97` call `executor.system_run({...})` with one
      argument, but the real SDK's
      `def system_run(self, params: dict, timeout_ms: int | None)` 
      (executor.py:160) has **no default** for `timeout_ms` → the register
      wrapper's `except` converts it to
      `{'ok': False, 'error': "TypeError: Executor.system_run() missing 1
      required positional argument: 'timeout_ms'"}`. Observed by
      dispatching `familiar.show` on the real Executor.
   The stub executor (`tests/test_muse_install.py:14-36`) shares none of
   these traits (no package import, no dataclass, defaulted `system_run`),
   so the 4 green tests prove nothing about the real target — and the
   plan's board criterion is unticked, so this was never caught. Failure is
   clean (backup restored byte-exactly, exit 1), not a brick. Fix direction
   proven in this review: register the module in `sys.modules`, put the
   venv's site-packages on `sys.path` during verification (or run under the
   venv python), and pass `timeout_ms` through the wrapper into
   `system_run`.

**I2 — Phase 2 tick evidence does not match its criterion.** The criterion
(re-read post-amendment, still present) requires `--check` to print "the
exact drop-in it WOULD write (including the `Directive=` reset lines)". The
actual output (executed, both with and without `--repo`) prints a one-line
summary — `write ~/.config/systemd/user/.../override.conf
resetting+re-setting ExecStartPre/Environment/ExecStart/ExecStopPost to
<repo>` — never the drop-in body nor the literal `ExecStartPre=` reset
lines. The tick's evidence string ("READY rc=0 with drop-in+key+restart
plan printed") silently downgrades the requirement it claims to satisfy.

**I3 — `examples/github-action.yml` is broken in one of its two advertised
consumption modes.** The file is a composite action (`runs: using:
composite`) whose step env references `${{ secrets.FAMILIAR_URL }}` /
`${{ secrets.FAMILIAR_KEY }}` (lines 28-29) and `${{ job.status … }}`
(line 30). GitHub's contexts reference states the `secrets` context "is not
available for composite actions"; the `job` context is likewise a
workflow-file context and is not available inside action files. Wiring it
as the header suggests (`uses: ./.github/actions/familiar-poke`) fails at
workflow-expansion time. The primary documented path ("copy this step into
any workflow") is fine — there `job`/`secrets` are legal. The YAML guard
test checks structure only, so CI cannot catch this.

**I4 — install.sh restart semantics deviate from the plan for non-default
repo locations, undisclosed by Amendment 1.** Plan: "restart only when
linked target or key changed". Implementation: `RESTART=1` whenever
`DROPIN_NEEDED` (`scripts/install.sh:72`), and the drop-in is rewritten
unconditionally on every run (`install.sh:89-108`, no content comparison) —
so any clone outside `~/muse-familiar` gets `daemon-reload + restart` on
*every* installer re-run even when nothing changed (the default-path flow
is correctly change-gated). The bounce is service-safe but interrupts the
current animation, and Amendment 1's "No interface, locking, ordering, or
cost change" does not cover it. (Note the plan's own text under-specified
the --repo restart trigger; the implementation's apply-the-drop-in restart
is the *correct* instinct — what's missing is the change detection, not the
restart.)

## Nits (5 listed)

N1 — `familiar/cli.py:84-88` comment claims "the engine appends under the
same discipline" — false: `engine.py:57-64 _log_event` takes no flock at
all, and the engine's lifetime `LOCK_SH` (`engine.py:157`) is *compatible*
with the CLI's `LOCK_SH`, so the lock excludes nothing on the read path.
Safety actually rests on O_APPEND single-write atomicity (adequate here for
short lines). Harmless but the comment misstates the mechanism.

N2 — The CI parity step ships `python3 tools/make_landing.py --check` where
the plan's Phase 1 text specifies `python3 tools/make_landing.py && git
diff --exit-code docs/`. Same invariant, strictly stronger (in-memory byte
compare; cannot false-pass regardless of git state), README documents it —
but per the plan's own signpost rule the refinement belongs in Amendments.

N3 — The hook's guard logs (`_logging.getLogger(__name__).exception(...)`,
`install.py:54-58`) where the plan literally says `except Exception: pass`.
Same degradation semantics, better observability, documented in
COMMANDS.md — an unrecorded refinement.

N4 — install.sh edges: with the repo at the default location the unit
hardcodes `%h/.local/bin/uv` (`units/familiar-engine.service:9`) while
install.sh accepts uv anywhere on PATH (`install.sh:36-37`) — a system-wide
uv install passes the check but yields a failing unit; `--repo` with a
missing value dies on a cryptic `cd: ''` under `set -e` (`install.sh:30`).

N5 — `install.py --repo X` only steers the hook's import path
(`install.py:110`); `register()`'s built commands always embed
`~/muse-familiar` defaults resolved at *load* time
(`familiar_specs.py:75-77`), so a non-default `--repo` imports specs from
one path while the generated commands point at another. The documented
flow (`cd ~/muse-familiar; sudo python3 …`) is unaffected.

(Also noted, not counted: COMMANDS.md's drop-in example carries a literal
`6f1c2d4e-…` placeholder with an ellipsis character; `load_specs` leaves a
`__pycache__` beside the executor; CI's added `permissions: contents: read`
is unplanned-but-good.)

## Verification evidence (executed during this review)

- `uv run --with pytest --with msgpack --with pyyaml python -m pytest -q`
  → 45 passed, 1 skipped; `python3 tools/secrets_gate.py` → clean;
  `python3 tools/make_landing.py --check` → in sync.
- `MUSE_SDK_LINUX_DIR=~/tmp-research/muse-gadget-sdk/linux … pytest
  tests/test_contract.py -q` → 1 passed.
- `bash -n scripts/install.sh` → OK; `--check` with and without `--repo`
  → rc=0 READY, zero side effects.
- install.py vs real-executor copy: documented flow fails (a), venv-python
  flow fails (b), loader-fixed flow registers but dispatch errors (c);
  restore after each failure verified byte-exact against the SDK original.

VERDICT: MAJOR-FAIL

## Round 2 (fresh reviewer)

Diff under review: `git diff 19e3234..HEAD` (fix commit 1f66d83 on top of the
round-1 range). Fresh read of every touched file, PLAN.md (incl.
Amendments), IMPLICIT_SPEC.md, and the round-1 findings. Every item
defaulted FAIL until earned. Oracles executed by this reviewer (not taken
from the ledger): a verbatim copy of the real SDK executor
(`~/tmp-research/muse-gadget-sdk/linux/src/musegadget/executor.py`, sha256
b3795fc4… + `__init__.py`) in a stub venv layout
(`lib/python3.12/site-packages/musegadget/`), plus a simulated
already-installed install.sh state under a fake `$HOME` traced with
`bash -x`.

### Round-1 finding dispositions

**I1 — FIXED, proven against the real executor.**
- `install.py:64-85 verify_registration` now imports the patched executor
  the way the service does — as a package — via `python -c` with
  site-packages (dirname×2 of the executor, `install.py:71`) inserted on
  sys.path, preferring `<venv>/bin/python` when present (`install.py:76-80`).
  Package-context import supplies both things fresh-file exec could not:
  `musegadget.__version__` at executor.py:36 and
  `sys.modules['musegadget.executor']` for the `@dataclass(frozen=True)`
  Account (executor.py:101).
- `familiar_specs.py:84/91/100` pass `timeout_ms` positionally (`None`)
  into `system_run`, matching the real SDK's no-default signature
  (executor.py:160); the wrapper also forwards `timeout_ms` to
  `original_run` (`familiar_specs.py:110-113`).
- The stub executor mirrors all three real traits
  (`tests/test_muse_install.py:18` module-level package import, `:21-26`
  frozen dataclass, `:41-44` positional `system_run` without default) —
  the unit oracle is now a faithful miniature.
- **Executed oracle**: `python3 muse_integration/install.py --venv <stub>
  --repo <repo abs> --no-restart` → `verified registration: familiar.feed
  familiar.show familiar.status`, rc=0. Dispatch on the real `Executor`
  (instance-stubbed `system_run`): `familiar.show happy` ok with
  `timeout_ms=None` passed positionally; bad mood / `x; reboot` kind
  rejected by allowlist before any command is built; `device.health`
  passthrough intact. `--remove` → rc=0, executor sha restored to
  b3795fc4…, `cmp` byte-identical to the pristine SDK copy, zero
  backup/tmp residue. Re-install → second run no-ops ("hook already
  present"). Repo-gone-at-service-time: rewiring the hook's path to a
  nonexistent dir and importing → module loads fine, familiar specs
  absent, hook logs — degradation as designed.

**I2 — FIXED.** `bash scripts/install.sh --check --repo
~/repos/learn/muse-familiar` → exit 0 and prints the exact drop-in body
(`scripts/install.sh:100-103`) including the literal reset lines
`ExecStartPre=`, `Environment=`, `ExecStart=`, `ExecStopPost=`; zero side
effects (no drop-in/link/key created). Auto-detect mode (no `--repo`)
also exit 0 with the same content.

**I3 — FIXED.** `examples/github-action.yml` is now an inline workflow
step (legal `secrets.*`/`job.status` contexts — valid only in workflow
files, which this now is), with a header explaining why a composite
action would break (`examples/github-action.yml:1-4`); the misleading
`uses: ./.github/actions/familiar-poke` wiring comment is gone.

**I4 — PARTIALLY FIXED; the restart half is still broken (see Important
finding R2-1).** The drop-in rewrite is now change-gated
(`scripts/install.sh:74-76` content compare, `:115-121` writes only when
changed, else "drop-in already current") — that half is genuinely fixed.
The restart is not: `install.sh:85` still folds `DROPIN_NEEDED` into
`LINK_NOW` unconditionally, and `RESTART` keys on `LINK_NOW`
(`install.sh:94`).

### Checklist verdicts (re-derived on the full diff)

1. **Plan conformance** — PASS except R2-1: all five phases' mechanisms
   now exist and work; Phase 2's `--check` criterion is satisfied as
   written (exact drop-in + reset lines, exit 0, both invocation modes —
   executed); Amendment 1 remains an honest, veto-flagged disclosure.
   Round-1 fixes were recorded in ledger+commit, correctly (no PLAN.md
   amendment needed for I1/I2/I3 since the implementation moved toward
   the plan, not away). The restart deviation of R2-1 remains undisclosed
   in Amendments (carried from round 1).
2. **Spec invariants 1-13** — PASS, re-derived: (1) gate executed —
   clean; new file types `.yml/.md/.sh` are all in secrets_gate CODE_EXTS
   (tools/secrets_gate.py:28). (2) no `firmware/` path in the diff; sketch
   only read by `test_sketch_clamps_present`. (3) `familiar/webhook.py`
   absent from diff; `feed` reuses `/poke` (401/429 → exit 2, tested).
   (4) router-socket grep test green. (5) no new long-lived writer; CLI
   status is a short LOCK_SH reader (N1 comment issue persists — nit).
   (6/7) bridge and webhook-thread paths untouched. (8) landing parity
   executed — in sync; `--check` is an in-memory byte compare.
   (9) contract test executed against the real SDK — 1 passed; hook
   carries zero spec text (import + `register(globals())`,
   `install.py:45-56`). (10) runtime stdlib-only; pyyaml dev/CI-only.
   (11) banned-strings test green; `$KEY`/`sdk-linux/`/"after installing
   the unit" gone — but see nit R2-N2 (examples/README misdescribes the
   GH artifact). (12) co-author grep clean here and in CI + local mirror
   test. (13) backup-first (`install.py:160-161`), compile-before-replace
   (`:166`), atomic `os.replace` (`:169`), verification-failure restore —
   executed from a neutral cwd: rc=1, byte-identical restore, no temp
   residue; `--remove` oldest-wins proven against the real executor.
3. **Failure/concurrency** — PASS: temp cleanup on BaseException paths
   (`install.py:170-177`), `--remove` with hook-but-no-backups refuses
   (`:118-120`), crash-before-replace covered by unit test, same-second
   `--force` counter-suffixed backups (`:154-159`), CLI timeouts bounded
   (2 s health / 5 s feed / 5 s systemctl). One FAIL-adjacent item: R2-1
   (restart on no-op re-run at non-default repos).
4. **Anti-patterns** — PASS. `register(globals())` remains justified and
   documented (`familiar_specs.py:64-76`); HA-tag-aware SafeLoader
   subclass is tight; no knobs/layers/DI.
5. **Test integrity** — PASS. Zero deleted lines in `tests/` across the
   whole diff (`git diff 19e3234..HEAD -- tests/` has no `-` hunks). The
   fix commit's edit to `test_example_yaml_parses` adapts a test added
   within this same diff range (phase 3), and is strictly stronger (walks
   to the Poke step, asserts both `continue-on-error` and the secrets
   expression). The stub upgrade strengthens, not weakens.
6. **Common defects** — PASS: feed kind validated by dict membership;
   YAML parsed with safe loaders; swallowed exceptions scoped and
   commented; `--repo` missing-value now guarded (round-1 N4 half).
7. **Convention fit** — PASS: module docstrings with exit-code contract
   (`familiar/cli.py:7-10`), lazy imports, one-file stdlib installer.

CI sanity: `.github/workflows/ci.yml` parses (triggers push[main]/PR;
steps checkout(fetch-depth 0) → setup-uv → tests(+pyyaml) → gate →
parity → co-author; `permissions: contents: read`); the example yml now
parses as a legal workflow file with a real job/steps structure.

### Important findings

**R2-1 — I4's restart half is NOT fixed, despite the fix commit claiming
"writes/restarts only on change" and the ledger recording
"drop-in+restart only on change. CONFIRMED by re-run output".**
`scripts/install.sh:85` computes `LINK_NOW=1` whenever `DROPIN_NEEDED=1`
— unconditionally for any repo outside `~/muse-familiar`, regardless of
link/key/drop-in state — and `RESTART` keys on `LINK_NOW`
(`scripts/install.sh:94`), so the execute path restarts a healthy engine
on every re-run (`install.sh:136-138`) and prints the false message
"restarted familiar-engine (config changed)". Executed proof: simulated
fully-installed no-op state under a fake `$HOME` (drop-in byte-equal to
`dropin_content`, unit link → repo unit, key present) — `bash -x` trace
shows `DROPIN_CHANGED=0`, `KEY_CREATED=0`, yet `LINK_NOW=1` →
`RESTART=1`, and `--check` plans "daemon-reload; enable --now; restart".
(The redundant clause is also the only reason: the other two `LINK_NOW`
conditions were false; `readlink` comparisons never even evaluated.) The
default-location flow is correctly change-gated; the plan's "restart
only when linked target or key changed" is still violated for
non-default clones, and the code's own comment at `install.sh:91-92`
states an intent the code does not implement. Fix is one line: drop the
`[ "$DROPIN_NEEDED" = 1 ] ||` clause from the `LINK_NOW` condition (the
drop-in case is already covered by `DROPIN_CHANGED`; a changed link
target is covered by the readlink compare).

### Nits (6)

- R2-N1 (carried N1): `familiar/cli.py:84-85` comment claims "the engine
  appends under the same discipline" — engine `_log_event` takes no
  flock; safety rests on O_APPEND single-write atomicity. Comment
  misstates the mechanism; behavior is fine.
- R2-N2 (new): `examples/README.md:18` still calls `github-action.yml` a
  "Composite-action step" — stale after the I3 fix; the artifact's own
  header now says the opposite ("inline step (not a composite action)").
- R2-N3 (new): the install.py verification oracle is cwd-sensitive:
  `python -c` puts `''` (cwd) on sys.path, so running the documented
  `cd <repo>; sudo python3 … install.py --repo <typo>` verifies
  successfully by importing `muse_integration` from the cwd even though
  the hook's embedded path is broken — observed (bogus `--repo` passed
  verification from the repo cwd, failed correctly from `/tmp`). The
  service would then degrade to familiar-absent (guarded, logged), not a
  brick; the default auto-`--repo` cannot hit it. An `-I`/`-P` flag or
  `cwd=/` on the subprocess would close it.
- R2-N4 (carried N4 half): `units/familiar-engine.service:9` hardcodes
  `%h/.local/bin/uv` while install.sh accepts uv anywhere on PATH — a
  system-wide uv passes `--check` but yields a failing unit (the `--repo`
  value-guard half of N4 is fixed).
- R2-N5 (carried N5): `--repo` steers only the hook's import path;
  `register()`'s embedded commands still resolve `~/muse-familiar` at
  load time (`familiar_specs.py:77-79`).
- R2-N6 (new, cosmetic): `--check`'s ACTIONS summary always says
  "write $DROPIN …" for non-default repos even when the drop-in is
  already current (the execute path correctly says "drop-in already
  current").

(Not counted: `__pycache__` beside the executor from the package-context
verification import — the service creates it anyway; COMMANDS.md's UUID
placeholder with an ellipsis; round-1 N2/N3 refinements — CI's
`make_landing.py --check` variant and the hook's log-not-pass guard —
remain unrecorded in PLAN Amendments.)

### Verification evidence (executed during this review)

- Real-SDK-executor oracle (verbatim copy in stub venv): install →
  verified registration, rc=0; dispatch allowlists + positional
  `timeout_ms` + `device.health` passthrough; `--remove` → byte-identical
  restore (sha256 + cmp vs pristine), zero residue; idempotent no-op;
  repo-gone degradation import.
- `bash scripts/install.sh --check --repo …` and auto-detect → exit 0,
  exact drop-in with reset lines, zero side effects; `--repo` without a
  value → BLOCKED, exit 1; fake-HOME no-op state + `bash -x` →
  DROPIN_CHANGED=0/KEY_CREATED=0 yet RESTART=1 (R2-1).
- `uv run --with pytest --with msgpack --with pyyaml python -m pytest -q`
  → 45 passed, 1 skipped. `python3 tools/secrets_gate.py` → clean.
  `python3 tools/make_landing.py --check` → in sync.
  `MUSE_SDK_LINUX_DIR=… pytest tests/test_contract.py -q` → 1 passed.
  ci.yml + both example YAMLs parse; co-author grep clean.

VERDICT: MINOR-FAIL
