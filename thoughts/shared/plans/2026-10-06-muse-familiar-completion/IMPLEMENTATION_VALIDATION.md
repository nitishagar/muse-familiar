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
